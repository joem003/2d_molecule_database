#!/usr/bin/env python3
"""
Example usage of the enhanced database builder with CID preference logic
"""

import os
from build_molecule_db_enhanced import EnhancedMinimalMoleculeDB

def example_usage():
    """Example of how to use the enhanced database builder"""
    print("Enhanced Minimal Molecule Database Builder")
    print("=" * 50)
    
    # Example 1: Build database with CID preference logic
    print("\n1. Building database with CID preference logic:")
    print("   Command: python build_molecule_db_enhanced.py --max-files 1")
    print("   This will:")
    print("   - Download the first PubChem SDF file")
    print("   - Process molecules with CID preference resolution")
    print("   - Resolve InChIKey conflicts using canonical CIDs")
    print("   - Store only the preferred molecular structures")
    
    # Example 2: Water example resolution
    print("\n2. Water example resolution:")
    print("   InChIKey: XLYOFNOQVPJJNP-UHFFFAOYSA-N")
    print("   CID 962: Canonical water molecule")
    print("   CID 22247451: Non-preferred form (hydron;hydroxide)")
    print("   Resolution: CID 962 is stored (canonical)")
    
    # Example 3: File structure
    print("\n3. Required files:")
    print("   - CID-Preferred.gz: Non-preferred → Preferred CID mapping")
    print("   - CID-Parent.gz: CID → Parent compound mapping")
    print("   - CID-InChI-Key.gz: CID → InChI → InChIKey mapping")
    print("   (These files should be in the same directory)")
    
    # Example 4: Database benefits
    print("\n4. Benefits of CID preference logic:")
    print("   - Eliminates duplicate InChIKeys")
    print("   - Prefers canonical molecular forms")
    print("   - Reduces database size by removing redundant entries")
    print("   - Ensures consistent molecular representation")
    
    # Example 5: Statistics
    print("\n5. Processing statistics tracked:")
    print("   - molecules_processed: Total molecules examined")
    print("   - molecules_added: Molecules stored in database")
    print("   - inchikey_conflicts: Conflicts resolved")
    print("   - cid_remappings: CIDs mapped to canonical forms")
    
    # Check if mapping files exist
    print("\n6. File availability check:")
    mapping_files = ['CID-Preferred.gz', 'CID-Parent.gz', 'CID-InChI-Key.gz']
    for filename in mapping_files:
        exists = os.path.exists(filename)
        status = "✅ Available" if exists else "❌ Missing"
        print(f"   {filename}: {status}")
    
    print("\n" + "=" * 50)
    print("Ready to build enhanced database!")

if __name__ == "__main__":
    example_usage()