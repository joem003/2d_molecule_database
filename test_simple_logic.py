#!/usr/bin/env python3
"""
Simple test to verify CID preference logic works correctly
"""

from build_molecule_db_enhanced import CIDMapper

def test_cid_logic():
    """Test the CID preference logic with mock data"""
    print("Testing CID Preference Logic")
    print("=" * 30)
    
    # Create mapper
    mapper = CIDMapper()
    
    # Mock data for testing
    # Simulate: CID 22247451 -> preferred CID 962
    mapper.preferred_cache['22247451'] = '962'
    mapper.preferred_cache['962'] = '962'  # 962 is its own preferred
    
    # Simulate: both are their own parents  
    mapper.parent_cache['22247451'] = '22247451'
    mapper.parent_cache['962'] = '962'
    
    # Test InChIKey conflict
    water_inchikey = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
    
    # Register both CIDs for same InChIKey
    mapper.register_inchikey_conflict(water_inchikey, '962')
    mapper.register_inchikey_conflict(water_inchikey, '22247451')
    
    print(f"Water InChIKey: {water_inchikey}")
    print(f"Registered CIDs: {mapper.inchikey_conflicts[water_inchikey]}")
    
    # Test individual CID resolution
    print("\nTesting CID resolution:")
    for cid in ['962', '22247451']:
        preferred = mapper.get_preferred_cid(cid)
        parent = mapper.get_parent_cid(preferred)
        canonical = mapper.get_canonical_cid(cid)
        
        print(f"  CID {cid}: preferred={preferred}, parent={parent}, canonical={canonical}")
    
    # Test conflict resolution
    print("\nTesting conflict resolution:")
    preferred_cid = mapper.resolve_inchikey_conflict(water_inchikey)
    print(f"Preferred CID for water: {preferred_cid}")
    
    # Expected: CID 962 should be preferred because it's canonical (962 == 962)
    # vs CID 22247451 which resolves to 962 but is not itself 962
    if preferred_cid == '962':
        print("✅ SUCCESS: CID 962 correctly identified as preferred")
        print("   Reason: 962 is canonical (itself), 22247451 resolves to 962 but is not canonical")
    else:
        print(f"❌ UNEXPECTED: Expected CID 962, got {preferred_cid}")
    
    return preferred_cid == '962'

if __name__ == "__main__":
    success = test_cid_logic()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")