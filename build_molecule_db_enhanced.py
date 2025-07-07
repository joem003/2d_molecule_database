#!/usr/bin/env python3
"""
Enhanced Minimal Molecule Database Builder with CID Preference Logic

This enhanced version handles:
1. InChIKey deduplication using preferred CIDs
2. CID preference mapping (non-preferred -> preferred)
3. Parent compound resolution
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
from collections import defaultdict
from typing import Dict, Set, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CIDMapper:
    """Lightweight CID mapping for specific CIDs encountered during processing"""
    
    def __init__(self, 
                 preferred_file='CID-Preferred.gz',
                 parent_file='CID-Parent.gz', 
                 inchikey_file='CID-InChI-Key.gz'):
        self.preferred_file = preferred_file
        self.parent_file = parent_file
        self.inchikey_file = inchikey_file
        
        # Only load mappings for CIDs we actually encounter
        self.preferred_cache: Dict[str, str] = {}
        self.parent_cache: Dict[str, str] = {}
        self.inchikey_conflicts: Dict[str, Set[str]] = defaultdict(set)
        
    def get_preferred_cid(self, cid: str) -> str:
        """Get preferred CID, loading from file if needed"""
        if cid in self.preferred_cache:
            return self.preferred_cache[cid]
        
        # Search in preferred file
        try:
            with gzip.open(self.preferred_file, 'rt') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2 and parts[0] == cid:
                        preferred = parts[1]
                        self.preferred_cache[cid] = preferred
                        return preferred
        except Exception as e:
            logger.debug(f"Error reading preferred file: {e}")
        
        # Not found, CID is its own preferred
        self.preferred_cache[cid] = cid
        return cid
    
    def get_parent_cid(self, cid: str) -> str:
        """Get parent CID, loading from file if needed"""
        if cid in self.parent_cache:
            return self.parent_cache[cid]
        
        # Search in parent file
        try:
            with gzip.open(self.parent_file, 'rt') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2 and parts[0] == cid:
                        parent = parts[1]
                        self.parent_cache[cid] = parent
                        return parent
        except Exception as e:
            logger.debug(f"Error reading parent file: {e}")
        
        # Not found, CID is its own parent
        self.parent_cache[cid] = cid
        return cid
    
    def get_canonical_cid(self, cid: str) -> str:
        """Get the most canonical CID"""
        # First get preferred
        preferred = self.get_preferred_cid(cid)
        # Then get parent
        canonical = self.get_parent_cid(preferred)
        return canonical
    
    def register_inchikey_conflict(self, inchikey: str, cid: str):
        """Register that a CID maps to this InChIKey"""
        self.inchikey_conflicts[inchikey].add(cid)
    
    def resolve_inchikey_conflict(self, inchikey: str) -> Optional[str]:
        """Resolve InChIKey conflict by preferring canonical CIDs"""
        cids = self.inchikey_conflicts.get(inchikey, set())
        
        if len(cids) <= 1:
            return next(iter(cids)) if cids else None
        
        # Find the most canonical CID
        canonical_pairs = []
        for cid in cids:
            canonical = self.get_canonical_cid(cid)
            canonical_pairs.append((cid, canonical))
        
        # Prefer CIDs that are their own canonical form
        for cid, canonical in canonical_pairs:
            if cid == canonical:
                logger.info(f"Resolved InChIKey {inchikey}: CID {cid} is canonical")
                return cid
        
        # Fallback: use the canonical form of the first CID
        first_cid = sorted(cids)[0]
        canonical = self.get_canonical_cid(first_cid)
        logger.info(f"Resolved InChIKey {inchikey}: Using canonical {canonical} for CID {first_cid}")
        return canonical

class EnhancedMinimalMoleculeDB:
    def __init__(self, db_path="molecule_2d_minimal.lmdb", download_dir="downloads"):
        self.db_path = db_path
        self.download_dir = download_dir
        self.base_url = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/SDF/"
        
        os.makedirs(download_dir, exist_ok=True)
        
        # 50GB should be enough for minimal 2D data
        self.env = lmdb.open(db_path, map_size=50 * 1024 * 1024 * 1024)
        
        # CID mapper for preference resolution
        self.cid_mapper = CIDMapper()
        
        # Statistics
        self.stats = {
            'molecules_processed': 0,
            'molecules_added': 0,
            'molecules_skipped': 0,
            'inchikey_conflicts': 0,
            'cid_remappings': 0
        }
    
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
        """Process a single SDF file with enhanced CID preference logic"""
        logger.info(f"Processing {os.path.basename(filepath)}...")
        
        molecules_added = 0
        molecules_skipped = 0
        conflicts_resolved = 0
        
        try:
            logger.info("Opening SDF file...")
            inf = gzip.open(filepath, 'rb')
            supplier = Chem.ForwardSDMolSupplier(inf)
            
            batch_size = 1000
            batch_data = []
            
            for i, mol in enumerate(tqdm(supplier, desc="Processing molecules")):
                if mol is None:
                    molecules_skipped += 1
                    continue
                
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
                    
                    # Register this CID->InChIKey mapping
                    if cid:
                        self.cid_mapper.register_inchikey_conflict(inchikey, cid)
                    
                    # Extract minimal 2D structure
                    structure_data = self.extract_2d_structure(mol)
                    if not structure_data:
                        molecules_skipped += 1
                        continue
                    
                    # Check if InChIKey already exists in database
                    with self.env.begin(write=False) as txn:
                        existing = txn.get(inchikey.encode())
                    
                    if existing:
                        # InChIKey conflict - resolve using CID preference
                        if cid:
                            canonical_cid = self.cid_mapper.get_canonical_cid(cid)
                            if canonical_cid != cid:
                                logger.debug(f"CID {cid} -> canonical {canonical_cid}")
                                self.stats['cid_remappings'] += 1
                            
                            # Check if we should replace existing entry
                            preferred_cid = self.cid_mapper.resolve_inchikey_conflict(inchikey)
                            if preferred_cid and preferred_cid == canonical_cid:
                                # Replace with preferred structure
                                batch_data.append((inchikey.encode(), structure_data.encode()))
                                conflicts_resolved += 1
                                self.stats['inchikey_conflicts'] += 1
                        else:
                            # No CID info, skip
                            molecules_skipped += 1
                            continue
                    else:
                        # New InChIKey, add to database
                        batch_data.append((inchikey.encode(), structure_data.encode()))
                    
                    # Commit batch when full
                    if len(batch_data) >= batch_size:
                        with self.env.begin(write=True) as txn:
                            for key, value in batch_data:
                                txn.put(key, value, overwrite=True)
                                molecules_added += 1
                        batch_data = []
                    
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
                
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
    
    def build_database(self, max_files=None, keep_downloads=False):
        """Main method to build the database"""
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
                
                # Clean up download if not keeping
                if not keep_downloads:
                    try:
                        os.remove(filepath)
                        logger.info(f"Removed {filename}")
                    except:
                        pass
        
        # Print final statistics
        logger.info("="*60)
        logger.info("FINAL STATISTICS")
        logger.info("="*60)
        for key, value in self.stats.items():
            logger.info(f"{key}: {value:,}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Build enhanced minimal molecule database')
    parser.add_argument('--db-path', default='data/molecule_2d_minimal.lmdb', help='Database path')
    parser.add_argument('--download-dir', default='data/downloads', help='Download directory')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    parser.add_argument('--keep-downloads', action='store_true', help='Keep downloaded files')
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
    
    db = EnhancedMinimalMoleculeDB(args.db_path, args.download_dir)
    db.build_database(args.max_files, args.keep_downloads)

if __name__ == "__main__":
    main()