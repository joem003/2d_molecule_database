#!/usr/bin/env python3
"""
CID Preference Mapper for PubChem Database

This module handles the mapping of non-preferred CIDs to their preferred/canonical forms
and resolves InChIKey conflicts by preferring canonical CIDs.

File formats:
- CID-Preferred.gz: non_preferred_cid -> preferred_cid
- CID-Parent.gz: cid -> parent_cid (parent is the main compound)
- CID-InChI-Key.gz: cid -> inchi -> inchikey
"""

import gzip
import logging
from typing import Dict, Set, Optional, Tuple
from tqdm import tqdm

logger = logging.getLogger(__name__)

class CIDPreferenceMapper:
    def __init__(self, 
                 preferred_file='CID-Preferred.gz',
                 parent_file='CID-Parent.gz', 
                 inchikey_file='CID-InChI-Key.gz'):
        """
        Initialize the CID preference mapper
        
        Args:
            preferred_file: Path to CID-Preferred.gz file
            parent_file: Path to CID-Parent.gz file  
            inchikey_file: Path to CID-InChI-Key.gz file
        """
        self.preferred_file = preferred_file
        self.parent_file = parent_file
        self.inchikey_file = inchikey_file
        
        # Mapping dictionaries
        self.preferred_map: Dict[str, str] = {}  # non_preferred -> preferred
        self.parent_map: Dict[str, str] = {}     # cid -> parent
        self.inchikey_to_cids: Dict[str, Set[str]] = {}  # inchikey -> set of cids
        self.cid_to_inchikey: Dict[str, str] = {}  # cid -> inchikey
        
        self.loaded = False
    
    def load_mappings(self):
        """Load all mapping files"""
        if self.loaded:
            return
            
        logger.info("Loading CID preference mappings...")
        
        # Load preferred mappings
        self._load_preferred_mappings()
        
        # Load parent mappings
        self._load_parent_mappings()
        
        # Load InChIKey mappings
        self._load_inchikey_mappings()
        
        logger.info(f"Loaded {len(self.preferred_map)} preferred mappings, "
                   f"{len(self.parent_map)} parent mappings, "
                   f"{len(self.inchikey_to_cids)} unique InChIKeys")
        
        self.loaded = True
    
    def _load_preferred_mappings(self):
        """Load CID-Preferred.gz: non_preferred_cid -> preferred_cid"""
        logger.info("Loading preferred CID mappings...")
        
        with gzip.open(self.preferred_file, 'rt') as f:
            for line in tqdm(f, desc="Loading preferred mappings"):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    non_preferred_cid = parts[0]
                    preferred_cid = parts[1]
                    self.preferred_map[non_preferred_cid] = preferred_cid
    
    def _load_parent_mappings(self):
        """Load CID-Parent.gz: cid -> parent_cid"""
        logger.info("Loading parent CID mappings...")
        
        with gzip.open(self.parent_file, 'rt') as f:
            for line in tqdm(f, desc="Loading parent mappings"):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    cid = parts[0]
                    parent_cid = parts[1]
                    self.parent_map[cid] = parent_cid
    
    def _load_inchikey_mappings(self):
        """Load CID-InChI-Key.gz: cid -> inchi -> inchikey"""
        logger.info("Loading InChIKey mappings...")
        
        with gzip.open(self.inchikey_file, 'rt') as f:
            for line in tqdm(f, desc="Loading InChIKey mappings"):
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    cid = parts[0]
                    inchi = parts[1]
                    inchikey = parts[2]
                    
                    # Store CID to InChIKey mapping
                    self.cid_to_inchikey[cid] = inchikey
                    
                    # Store InChIKey to CIDs mapping (for deduplication)
                    if inchikey not in self.inchikey_to_cids:
                        self.inchikey_to_cids[inchikey] = set()
                    self.inchikey_to_cids[inchikey].add(cid)
    
    def get_canonical_cid(self, cid: str) -> str:
        """
        Get the canonical CID for a given CID
        
        Resolution steps:
        1. Check if CID has a preferred mapping
        2. Check if the result (or original) has a parent compound
        3. Return the most canonical form
        
        Args:
            cid: Input CID as string
            
        Returns:
            Canonical CID as string
        """
        if not self.loaded:
            self.load_mappings()
        
        # Step 1: Check preferred mapping
        preferred_cid = self.preferred_map.get(cid, cid)
        
        # Step 2: Check parent mapping
        canonical_cid = self.parent_map.get(preferred_cid, preferred_cid)
        
        return canonical_cid
    
    def get_preferred_cid_for_inchikey(self, inchikey: str) -> Optional[str]:
        """
        Get the preferred CID for an InChIKey when multiple CIDs exist
        
        Logic:
        1. Get all CIDs that map to this InChIKey
        2. For each CID, get its canonical form
        3. Prefer the CID that IS its own canonical form (not one that resolves TO canonical)
        
        Args:
            inchikey: InChIKey string
            
        Returns:
            Preferred CID or None if InChIKey not found
        """
        if not self.loaded:
            self.load_mappings()
        
        # Get all CIDs for this InChIKey
        cids = self.inchikey_to_cids.get(inchikey, set())
        
        if not cids:
            return None
        
        if len(cids) == 1:
            return next(iter(cids))
        
        # Multiple CIDs for same InChIKey - find the canonical one
        canonical_cids = []
        for cid in cids:
            canonical = self.get_canonical_cid(cid)
            
            # Prefer the CID that IS its own canonical form
            if cid == canonical:
                canonical_cids.append(cid)
        
        if canonical_cids:
            # Return the first canonical CID (should be unique)
            return sorted(canonical_cids)[0]
        
        # Fallback: return the canonical form of the first CID
        return self.get_canonical_cid(sorted(cids)[0])
    
    def resolve_cid_conflict(self, inchikey: str, current_cid: str) -> Tuple[str, bool]:
        """
        Resolve CID conflict for an InChIKey
        
        Args:
            inchikey: InChIKey string
            current_cid: Currently stored CID
            
        Returns:
            Tuple of (preferred_cid, should_replace)
        """
        if not self.loaded:
            self.load_mappings()
        
        preferred_cid = self.get_preferred_cid_for_inchikey(inchikey)
        
        if preferred_cid is None:
            return current_cid, False
        
        # Check if we should replace the current CID
        current_canonical = self.get_canonical_cid(current_cid)
        preferred_canonical = self.get_canonical_cid(preferred_cid)
        
        # Replace if the preferred CID is more canonical
        should_replace = preferred_canonical != current_canonical and preferred_cid == preferred_canonical
        
        return preferred_cid, should_replace

# Example usage and testing
if __name__ == "__main__":
    # Test with water example
    mapper = CIDPreferenceMapper()
    mapper.load_mappings()
    
    # Test water InChIKey
    water_inchikey = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
    
    print(f"Testing water InChIKey: {water_inchikey}")
    
    # Get all CIDs for water
    cids = mapper.inchikey_to_cids.get(water_inchikey, set())
    print(f"CIDs for water: {sorted(cids)}")
    
    # Test CID resolution
    for cid in ['962', '22247451']:
        if cid in mapper.cid_to_inchikey:
            canonical = mapper.get_canonical_cid(cid)
            print(f"CID {cid} -> canonical: {canonical}")
            
    # Test preferred CID selection
    preferred = mapper.get_preferred_cid_for_inchikey(water_inchikey)
    print(f"Preferred CID for water: {preferred}")