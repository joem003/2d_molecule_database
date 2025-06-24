#!/usr/bin/env python3
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MinimalMoleculeDB:
    def __init__(self, db_path="molecule_2d_minimal.lmdb", download_dir="downloads"):
        self.db_path = db_path
        self.download_dir = download_dir
        self.base_url = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/SDF/"
        
        os.makedirs(download_dir, exist_ok=True)
        
        # 50GB should be enough for minimal 2D data
        self.env = lmdb.open(db_path, map_size=50 * 1024 * 1024 * 1024)
        
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
        """Process a single SDF file and add molecules to database"""
        logger.info(f"Processing {os.path.basename(filepath)}...")
        
        molecules_added = 0
        molecules_skipped = 0
        
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
                
                try:
                    # Get InChIKey
                    if mol.HasProp('PUBCHEM_IUPAC_INCHIKEY'):
                        inchikey = mol.GetProp('PUBCHEM_IUPAC_INCHIKEY')
                    else:
                        inchi = Chem.MolToInchi(mol)
                        if not inchi:
                            molecules_skipped += 1
                            continue
                        inchikey = Chem.InchiToInchiKey(inchi)
                    
                    # Extract minimal 2D structure
                    structure_data = self.extract_2d_structure(mol)
                    if structure_data:
                        batch_data.append((inchikey.encode(), structure_data.encode()))
                    else:
                        molecules_skipped += 1
                        continue
                    
                    # Commit batch when full
                    if len(batch_data) >= batch_size:
                        with self.env.begin(write=True) as txn:
                            for key, value in batch_data:
                                if not txn.get(key):
                                    txn.put(key, value)
                                    molecules_added += 1
                                else:
                                    molecules_skipped += 1
                        batch_data = []
                    
                except Exception as e:
                    logger.debug(f"Error processing molecule: {e}")
                    molecules_skipped += 1
                    continue
            
            # Commit remaining molecules
            if batch_data:
                with self.env.begin(write=True) as txn:
                    for key, value in batch_data:
                        if not txn.get(key):
                            txn.put(key, value)
                            molecules_added += 1
                        else:
                            molecules_skipped += 1
            
            logger.info(f"Added {molecules_added} molecules, skipped {molecules_skipped}")
            inf.close()
                
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
    
    def build_database(self, max_files=None):
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
                
                if not self.keep_downloads:
                    os.remove(filepath)
                    logger.info(f"Deleted {filename}")
            
            time.sleep(1)
    
    def get_molecule_count(self):
        """Get total number of molecules in database"""
        with self.env.begin() as txn:
            return txn.stat()['entries']
    
    def get_molecule(self, inchikey):
        """Retrieve a molecule by InChIKey"""
        with self.env.begin() as txn:
            mol_data = txn.get(inchikey.encode())
            if mol_data:
                return mol_data.decode()
            return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build minimal 2D molecule database from PubChem SDF files")
    parser.add_argument("--db-path", default="molecule_2d_minimal.lmdb", help="Path to LMDB database")
    parser.add_argument("--download-dir", default="downloads", help="Directory for downloads")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--keep-downloads", action="store_true", help="Keep downloaded files")
    
    args = parser.parse_args()
    
    db = MinimalMoleculeDB(args.db_path, args.download_dir)
    db.keep_downloads = args.keep_downloads
    
    try:
        db.build_database(args.max_files)
        logger.info(f"Database built successfully with {db.get_molecule_count()} molecules")
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()