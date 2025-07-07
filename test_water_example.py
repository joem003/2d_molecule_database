#!/usr/bin/env python3
"""
Test script to verify the water example (CID 962 vs 22247451) works correctly
"""

import gzip
import logging
from build_molecule_db_enhanced import CIDMapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_water_example():
    """Test the water example with CID 962 (preferred) vs 22247451 (non-preferred)"""
    print("Testing Water Example: CID 962 vs 22247451")
    print("=" * 50)
    
    # Initialize CID mapper
    mapper = CIDMapper()
    
    # Water InChIKey
    water_inchikey = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
    
    # Test CID mappings
    cids_to_test = ['962', '22247451']
    
    print(f"Water InChIKey: {water_inchikey}")
    print()
    
    # Find these CIDs in the mapping files
    print("Searching for CIDs in mapping files...")
    
    # Check CID-Preferred.gz
    print("\nChecking CID-Preferred.gz:")
    with gzip.open('CID-Preferred.gz', 'rt') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2 and parts[0] in cids_to_test:
                print(f"  Found: {parts[0]} -> {parts[1]} (non-preferred -> preferred)")
    
    # Check CID-Parent.gz
    print("\nChecking CID-Parent.gz:")
    with gzip.open('CID-Parent.gz', 'rt') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2 and parts[0] in cids_to_test:
                print(f"  Found: {parts[0]} -> {parts[1]} (CID -> parent)")
    
    # Check CID-InChI-Key.gz for water InChIKey
    print(f"\nChecking CID-InChI-Key.gz for water InChIKey:")
    water_cids = []
    with gzip.open('CID-InChI-Key.gz', 'rt') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3 and parts[2] == water_inchikey:
                water_cids.append(parts[0])
                print(f"  Found: CID {parts[0]} -> {parts[2]}")
                if len(water_cids) >= 10:  # Limit output
                    print("  (showing first 10 matches)")
                    break
    
    print(f"\nTotal CIDs found for water: {len(water_cids)}")
    
    # Test the mapping logic
    print("\nTesting CID mapping logic:")
    for cid in cids_to_test:
        preferred = mapper.get_preferred_cid(cid)
        parent = mapper.get_parent_cid(preferred)
        canonical = mapper.get_canonical_cid(cid)
        
        print(f"  CID {cid}:")
        print(f"    Preferred: {preferred}")
        print(f"    Parent: {parent}")
        print(f"    Canonical: {canonical}")
        print()
    
    # Test conflict resolution
    print("Testing InChIKey conflict resolution:")
    
    # Register the CIDs as conflicts
    for cid in water_cids[:5]:  # Test with first 5 CIDs
        mapper.register_inchikey_conflict(water_inchikey, cid)
    
    # Resolve the conflict
    preferred_cid = mapper.resolve_inchikey_conflict(water_inchikey)
    print(f"Preferred CID for water: {preferred_cid}")
    
    # Expected result: CID 962 should be preferred over 22247451
    if preferred_cid == '962':
        print("✅ SUCCESS: CID 962 correctly identified as preferred")
    else:
        print(f"❌ UNEXPECTED: Expected CID 962, got {preferred_cid}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_water_example()