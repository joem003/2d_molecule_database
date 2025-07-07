#!/usr/bin/env python3
"""
Memory-Efficient Minimal Molecule Database Builder

This version uses indexed CID files and LRU caching to minimize memory usage
while still providing CID preference resolution and InChIKey deduplication.

Designed to work efficiently with 16GB RAM systems.
"""

import os
import gzip
import lmdb
import requests
from bs4 import BeautifulSoup
from rdkit import Chem
from tqdm import tqdm
import logging
from urllib.parse import urljoin
import time
import sys
import json
import psutil
from typing import Dict, Set, Optional, Tuple

from memory_efficient_mapper import MemoryEfficientCIDMapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Monitor memory usage during processing"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_mb()
    
    def get_memory_mb(self):
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_memory_percent(self):
        """Get memory usage as percentage of system RAM"""
        return self.process.memory_percent()
    
    def log_memory_usage(self, context=""):
        """Log current memory usage"""
        current_mb = self.get_memory_mb()
        percent = self.get_memory_percent()
        delta_mb = current_mb - self.initial_memory
        
        logger.info(f"Memory {context}: {current_mb:.1f}MB ({percent:.1f}% of system, +{delta_mb:.1f}MB from start)")

class MemoryEfficientMoleculeDB:
    """Memory-efficient minimal molecule database builder"""
    
    def __init__(self, 
                 db_path="molecule_2d_minimal.lmdb", 
                 download_dir="downloads",
                 batch_size=500,  # Smaller batch size for memory efficiency
                 cache_size=5000,  # Smaller cache size
                 max_memory_percent=80):  # Stop if memory usage exceeds this
        
        self.db_path = db_path
        self.download_dir = download_dir
        self.base_url = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/SDF/"
        self.batch_size = batch_size
        self.max_memory_percent = max_memory_percent
        
        os.makedirs(download_dir, exist_ok=True)
        
        # 50GB should be enough for minimal 2D data
        self.env = lmdb.open(db_path, map_size=50 * 1024 * 1024 * 1024)
        
        # Memory-efficient CID mapper
        self.cid_mapper = MemoryEfficientCIDMapper(cache_size=cache_size)
        
        # Memory monitor
        self.memory_monitor = MemoryMonitor()
        
        # Statistics
        self.stats = {
            'molecules_processed': 0,
            'molecules_added': 0,
            'molecules_skipped': 0,
            'inchikey_conflicts': 0,
            'cid_remappings': 0,
            'memory_warnings': 0,
            'batch_clears': 0
        }
    
    def check_memory_usage(self):
        """Check if memory usage is getting too high"""
        memory_percent = self.memory_monitor.get_memory_percent()
        
        if memory_percent > self.max_memory_percent:
            logger.warning(f"High memory usage: {memory_percent:.1f}% - clearing caches")
            
            # Clear CID mapper conflicts and caches
            self.cid_mapper.clear_conflicts()
            self.cid_mapper.preferred_cache.clear()
            self.cid_mapper.parent_cache.clear()
            
            self.stats['memory_warnings'] += 1
            return True
        
        return False
    
    def get_sdf_file_list(self):
        """Get list of SDF files from PubChem FTP"""
        logger.info("Fetching SDF file list from PubChem...")
        try:
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            sdf_files = []
            
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and href.endswith('.sdf.gz'):
                    sdf_files.append(href)
            
            logger.info(f"Found {len(sdf_files)} SDF files")
            return sorted(sdf_files)
        except Exception as e:
            logger.error(f"Error fetching file list: {e}")
            return []
    
    def download_file(self, filename):
        """Download a single SDF file"""
        url = urljoin(self.base_url, filename)
        filepath = os.path.join(self.download_dir, filename)
        
        if os.path.exists(filepath):
            logger.info(f"File {filename} already exists, skipping download")
            return filepath
        
        logger.info(f"Downloading {filename}...")
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            return filepath
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
    
    def extract_2d_structure(self, mol):
        """Extract only the 2D structure data needed for rendering"""
        if not mol:
            return None
            
        try:
            # Get atom positions and elements
            atoms = []
            conf = mol.GetConformer()
            for i in range(mol.GetNumAtoms()):
                atom = mol.GetAtomWithIdx(i)
                pos = conf.GetAtomPosition(i)
                atoms.append({
                    'x': round(pos.x, 4),  # Round to save space
                    'y': round(pos.y, 4),
                    'e': atom.GetSymbol()  # Element symbol
                })
            
            # Get bonds
            bonds = []
            for bond in mol.GetBonds():
                bonds.append({
                    'f': bond.GetBeginAtomIdx(),  # from
                    't': bond.GetEndAtomIdx(),    # to
                    'o': int(bond.GetBondTypeAsDouble())  # order (1=single, 2=double, etc)
                })
            
            return json.dumps({'a': atoms, 'b': bonds}, separators=(',', ':'))
        except Exception as e:
            logger.debug(f"Error extracting structure: {e}")
            return None
    
    def process_sdf_file(self, filepath):
        """Process a single SDF file with memory-efficient CID preference logic"""
        logger.info(f"Processing {os.path.basename(filepath)}...")
        self.memory_monitor.log_memory_usage("before processing file")
        
        molecules_added = 0
        molecules_skipped = 0
        conflicts_resolved = 0
        
        try:
            logger.info("Opening SDF file...")
            inf = gzip.open(filepath, 'rb')
            supplier = Chem.ForwardSDMolSupplier(inf)
            
            batch_data = []
            
            for i, mol in enumerate(tqdm(supplier, desc="Processing molecules")):
                if mol is None:
                    molecules_skipped += 1
                    continue
                
                # Check memory usage periodically
                if i % 1000 == 0 and i > 0:
                    if self.check_memory_usage():
                        self.stats['batch_clears'] += 1
                
                self.stats['molecules_processed'] += 1
                
                try:
                    # Get CID from molecule
                    cid = None
                    if mol.HasProp('PUBCHEM_COMPOUND_CID'):
                        cid = mol.GetProp('PUBCHEM_COMPOUND_CID')
                    
                    # Get InChIKey
                    inchikey = None
                    if mol.HasProp('PUBCHEM_IUPAC_INCHIKEY'):
                        inchikey = mol.GetProp('PUBCHEM_IUPAC_INCHIKEY')
                    else:
                        inchi = Chem.MolToInchi(mol)
                        if inchi:
                            inchikey = Chem.InchiToInchiKey(inchi)
                    
                    if not inchikey:
                        molecules_skipped += 1
                        continue
                    
                    # Extract minimal 2D structure
                    structure_data = self.extract_2d_structure(mol)
                    if not structure_data:
                        molecules_skipped += 1
                        continue
                    
                    # Check if InChIKey already exists in database
                    with self.env.begin(write=False) as txn:
                        existing = txn.get(inchikey.encode())
                    
                    should_add = True
                    
                    if existing and cid:
                        # InChIKey conflict - resolve using CID preference
                        self.cid_mapper.register_inchikey_conflict(inchikey, cid)
                        
                        canonical_cid = self.cid_mapper.get_canonical_cid(cid)
                        if canonical_cid != cid:
                            logger.debug(f"CID {cid} -> canonical {canonical_cid}")
                            self.stats['cid_remappings'] += 1
                        
                        # Check if we should replace existing entry
                        preferred_cid = self.cid_mapper.resolve_inchikey_conflict(inchikey)
                        if preferred_cid and preferred_cid == canonical_cid:
                            # Replace with preferred structure
                            conflicts_resolved += 1
                            self.stats['inchikey_conflicts'] += 1
                            should_add = True
                        else:
                            should_add = False
                    elif existing and not cid:
                        # Existing entry and no CID info, skip
                        should_add = False
                    
                    if should_add:
                        batch_data.append((inchikey.encode(), structure_data.encode()))
                    else:
                        molecules_skipped += 1
                    
                    # Commit batch when full
                    if len(batch_data) >= self.batch_size:
                        with self.env.begin(write=True) as txn:
                            for key, value in batch_data:
                                txn.put(key, value, overwrite=True)
                                molecules_added += 1
                        batch_data = []
                        
                        # Log progress periodically
                        if molecules_added % 10000 == 0:
                            self.memory_monitor.log_memory_usage(f"after {molecules_added} molecules")
                            cache_stats = self.cid_mapper.get_cache_stats()
                            logger.info(f"Cache stats: {cache_stats}")
                    
                except Exception as e:
                    logger.debug(f"Error processing molecule: {e}")
                    molecules_skipped += 1
                    continue
            
            # Commit remaining molecules
            if batch_data:
                with self.env.begin(write=True) as txn:
                    for key, value in batch_data:
                        txn.put(key, value, overwrite=True)
                        molecules_added += 1
            
            logger.info(f"Added {molecules_added} molecules, skipped {molecules_skipped}, resolved {conflicts_resolved} conflicts")
            inf.close()
            
            # Update global stats
            self.stats['molecules_added'] += molecules_added
            self.stats['molecules_skipped'] += molecules_skipped
            
            self.memory_monitor.log_memory_usage("after processing file")
                
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
    
    def build_database(self, max_files=None, keep_downloads=False):
        """Main method to build the database"""
        logger.info("Starting memory-efficient database build")
        self.memory_monitor.log_memory_usage("at start")
        
        # Check if CID indexes exist
        if not os.path.exists("cid_indexes/preferred.idx"):
            logger.error("CID indexes not found. Please run: python create_cid_index.py")
            return
        
        sdf_files = self.get_sdf_file_list()
        
        if not sdf_files:
            logger.error("No SDF files found")
            return
        
        if max_files:
            sdf_files = sdf_files[:max_files]
            logger.info(f"Processing first {max_files} files")
        
        for i, filename in enumerate(sdf_files, 1):
            logger.info(f"Processing file {i}/{len(sdf_files)}: {filename}")
            
            filepath = self.download_file(filename)
            if filepath:
                self.process_sdf_file(filepath)
                
                # Clear conflicts after each file to save memory
                self.cid_mapper.clear_conflicts()
                
                # Clean up download if not keeping
                if not keep_downloads:
                    try:
                        os.remove(filepath)
                        logger.info(f"Removed {filename}")
                    except:
                        pass
        
        # Close CID mapper
        self.cid_mapper.close()
        
        # Print final statistics
        logger.info("="*60)
        logger.info("FINAL STATISTICS")
        logger.info("="*60)
        for key, value in self.stats.items():
            logger.info(f"{key}: {value:,}")
        
        self.memory_monitor.log_memory_usage("at completion")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build memory-efficient minimal molecule database')
    parser.add_argument('--db-path', default='data/molecule_2d_minimal.lmdb', help='Database path')
    parser.add_argument('--download-dir', default='data/downloads', help='Download directory')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    parser.add_argument('--keep-downloads', action='store_true', help='Keep downloaded files')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size for processing')
    parser.add_argument('--cache-size', type=int, default=5000, help='LRU cache size')
    parser.add_argument('--max-memory', type=int, default=80, help='Max memory usage percent')
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
    
    # Check available system memory
    total_memory_gb = psutil.virtual_memory().total / (1024**3)
    logger.info(f"System memory: {total_memory_gb:.1f} GB")
    
    if total_memory_gb < 8:
        logger.warning("Low system memory detected. Consider reducing batch and cache sizes.")
    
    db = MemoryEfficientMoleculeDB(
        args.db_path, 
        args.download_dir,
        batch_size=args.batch_size,
        cache_size=args.cache_size,
        max_memory_percent=args.max_memory
    )
    
    try:
        db.build_database(args.max_files, args.keep_downloads)
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
    except Exception as e:
        logger.error(f"Build failed: {e}")
        raise

if __name__ == "__main__":
    main()