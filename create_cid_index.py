#!/usr/bin/env python3
"""
Create indexed CID mapping files for fast binary search lookups

This script converts the large PubChem mapping files into sorted binary index files
that enable O(log n) lookups instead of O(n) file scanning.
"""

import gzip
import struct
import os
import logging
from tqdm import tqdm
import bisect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CIDIndexBuilder:
    """Build binary index files for fast CID lookups"""
    
    def __init__(self):
        self.index_dir = "cid_indexes"
        os.makedirs(self.index_dir, exist_ok=True)
    
    def create_preferred_index(self, source_file='CID-Preferred.gz'):
        """Create binary index for CID-Preferred.gz"""
        logger.info(f"Creating preferred CID index from {source_file}")
        
        # Read and sort the mappings
        mappings = []
        with gzip.open(source_file, 'rt') as f:
            for line_num, line in enumerate(tqdm(f, desc="Reading preferred mappings")):
                if line_num % 100000 == 0 and line_num > 0:
                    logger.info(f"Processed {line_num:,} lines")
                
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    try:
                        non_preferred_cid = int(parts[0])
                        preferred_cid = int(parts[1])
                        mappings.append((non_preferred_cid, preferred_cid))
                    except ValueError:
                        continue
        
        logger.info(f"Read {len(mappings):,} preferred mappings")
        
        # Sort by non_preferred_cid for binary search
        mappings.sort(key=lambda x: x[0])
        logger.info("Sorted mappings")
        
        # Write binary index file
        index_file = os.path.join(self.index_dir, "preferred.idx")
        with open(index_file, 'wb') as f:
            # Write header: number of entries
            f.write(struct.pack('<I', len(mappings)))
            
            # Write mappings: non_preferred_cid (4 bytes) -> preferred_cid (4 bytes)
            for non_preferred, preferred in tqdm(mappings, desc="Writing index"):
                f.write(struct.pack('<II', non_preferred, preferred))
        
        logger.info(f"Created index file: {index_file} ({os.path.getsize(index_file):,} bytes)")
        return index_file
    
    def create_parent_index(self, source_file='CID-Parent.gz'):
        """Create binary index for CID-Parent.gz"""
        logger.info(f"Creating parent CID index from {source_file}")
        
        # Read and filter parent mappings (only where CID != parent)
        mappings = []
        with gzip.open(source_file, 'rt') as f:
            for line_num, line in enumerate(tqdm(f, desc="Reading parent mappings")):
                if line_num % 100000 == 0 and line_num > 0:
                    logger.info(f"Processed {line_num:,} lines")
                
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    try:
                        cid = int(parts[0])
                        parent_cid = int(parts[1])
                        # Only store if CID != parent (saves space)
                        if cid != parent_cid:
                            mappings.append((cid, parent_cid))
                    except ValueError:
                        continue
        
        logger.info(f"Read {len(mappings):,} parent mappings (where CID != parent)")
        
        # Sort by cid for binary search
        mappings.sort(key=lambda x: x[0])
        logger.info("Sorted mappings")
        
        # Write binary index file
        index_file = os.path.join(self.index_dir, "parent.idx")
        with open(index_file, 'wb') as f:
            # Write header: number of entries
            f.write(struct.pack('<I', len(mappings)))
            
            # Write mappings: cid (4 bytes) -> parent_cid (4 bytes)
            for cid, parent in tqdm(mappings, desc="Writing index"):
                f.write(struct.pack('<II', cid, parent))
        
        logger.info(f"Created index file: {index_file} ({os.path.getsize(index_file):,} bytes)")
        return index_file
    
    def create_inchikey_sample_index(self, source_file='CID-InChI-Key.gz', max_entries=1000000):
        """Create sample InChIKey index for testing (limited size for memory)"""
        logger.info(f"Creating sample InChIKey index from {source_file}")
        
        # Read sample of InChIKey mappings
        mappings = []
        with gzip.open(source_file, 'rt') as f:
            for line_num, line in enumerate(tqdm(f, desc="Reading InChIKey mappings")):
                if line_num >= max_entries:
                    break
                
                if line_num % 100000 == 0 and line_num > 0:
                    logger.info(f"Processed {line_num:,} lines")
                
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    try:
                        cid = int(parts[0])
                        inchikey = parts[2]
                        mappings.append((cid, inchikey))
                    except ValueError:
                        continue
        
        logger.info(f"Read {len(mappings):,} InChIKey mappings")
        
        # Sort by CID for binary search
        mappings.sort(key=lambda x: x[0])
        logger.info("Sorted mappings")
        
        # Write binary index file
        index_file = os.path.join(self.index_dir, "inchikey_sample.idx")
        with open(index_file, 'wb') as f:
            # Write header: number of entries
            f.write(struct.pack('<I', len(mappings)))
            
            # Write mappings: cid (4 bytes) + inchikey_length (1 byte) + inchikey (variable)
            for cid, inchikey in tqdm(mappings, desc="Writing index"):
                inchikey_bytes = inchikey.encode('utf-8')
                f.write(struct.pack('<IB', cid, len(inchikey_bytes)))
                f.write(inchikey_bytes)
        
        logger.info(f"Created index file: {index_file} ({os.path.getsize(index_file):,} bytes)")
        return index_file

class CIDIndexReader:
    """Fast binary search reader for CID index files"""
    
    def __init__(self, index_dir="cid_indexes"):
        self.index_dir = index_dir
        self.preferred_file = os.path.join(index_dir, "preferred.idx")
        self.parent_file = os.path.join(index_dir, "parent.idx")
        
        # Cache for loaded indexes
        self._preferred_data = None
        self._parent_data = None
    
    def _load_preferred_index(self):
        """Load preferred index into memory for binary search"""
        if self._preferred_data is not None:
            return
        
        if not os.path.exists(self.preferred_file):
            logger.warning(f"Preferred index file not found: {self.preferred_file}")
            self._preferred_data = []
            return
        
        logger.info("Loading preferred CID index...")
        with open(self.preferred_file, 'rb') as f:
            # Read header
            count = struct.unpack('<I', f.read(4))[0]
            
            # Read all mappings
            self._preferred_data = []
            for _ in range(count):
                non_preferred, preferred = struct.unpack('<II', f.read(8))
                self._preferred_data.append((non_preferred, preferred))
        
        logger.info(f"Loaded {len(self._preferred_data):,} preferred mappings")
    
    def _load_parent_index(self):
        """Load parent index into memory for binary search"""
        if self._parent_data is not None:
            return
        
        if not os.path.exists(self.parent_file):
            logger.warning(f"Parent index file not found: {self.parent_file}")
            self._parent_data = []
            return
        
        logger.info("Loading parent CID index...")
        with open(self.parent_file, 'rb') as f:
            # Read header
            count = struct.unpack('<I', f.read(4))[0]
            
            # Read all mappings
            self._parent_data = []
            for _ in range(count):
                cid, parent = struct.unpack('<II', f.read(8))
                self._parent_data.append((cid, parent))
        
        logger.info(f"Loaded {len(self._parent_data):,} parent mappings")
    
    def get_preferred_cid(self, cid):
        """Fast binary search for preferred CID"""
        self._load_preferred_index()
        
        # Binary search for CID
        cid_int = int(cid)
        idx = bisect.bisect_left(self._preferred_data, (cid_int, 0))
        
        if idx < len(self._preferred_data) and self._preferred_data[idx][0] == cid_int:
            return str(self._preferred_data[idx][1])
        
        # Not found, CID is its own preferred
        return cid
    
    def get_parent_cid(self, cid):
        """Fast binary search for parent CID"""
        self._load_parent_index()
        
        # Binary search for CID
        cid_int = int(cid)
        idx = bisect.bisect_left(self._parent_data, (cid_int, 0))
        
        if idx < len(self._parent_data) and self._parent_data[idx][0] == cid_int:
            return str(self._parent_data[idx][1])
        
        # Not found, CID is its own parent
        return cid
    
    def get_canonical_cid(self, cid):
        """Get canonical CID (preferred then parent)"""
        preferred = self.get_preferred_cid(cid)
        canonical = self.get_parent_cid(preferred)
        return canonical

def main():
    """Create all CID index files"""
    builder = CIDIndexBuilder()
    
    # Check source files exist
    source_files = ['CID-Preferred.gz', 'CID-Parent.gz', 'CID-InChI-Key.gz']
    for filename in source_files:
        if not os.path.exists(filename):
            logger.error(f"Source file not found: {filename}")
            return
    
    logger.info("Creating CID index files...")
    
    # Create indexes
    builder.create_preferred_index()
    builder.create_parent_index()
    builder.create_inchikey_sample_index()
    
    logger.info("Index creation complete!")
    
    # Test the indexes
    logger.info("Testing indexes...")
    reader = CIDIndexReader()
    
    # Test with known values
    test_cids = ['962', '22247451', '1', '10']
    for cid in test_cids:
        preferred = reader.get_preferred_cid(cid)
        parent = reader.get_parent_cid(preferred)
        canonical = reader.get_canonical_cid(cid)
        print(f"CID {cid}: preferred={preferred}, parent={parent}, canonical={canonical}")

if __name__ == "__main__":
    main()