#!/usr/bin/env python3
import gzip
import sys

def examine_file(filename, num_lines=10):
    """Examine the structure of a gzipped file"""
    print(f"\n{'='*60}")
    print(f"Examining: {filename}")
    print(f"{'='*60}")
    
    try:
        with gzip.open(filename, 'rt') as f:
            print(f"\nFirst {num_lines} lines:")
            for i, line in enumerate(f):
                if i >= num_lines:
                    break
                print(f"{i+1}: {line.strip()}")
                
                # Analyze the structure
                if i == 0:
                    parts = line.strip().split('\t')
                    print(f"   → Number of columns: {len(parts)}")
                    print(f"   → Column values: {parts}")
    except Exception as e:
        print(f"Error reading {filename}: {e}")

def count_lines(filename):
    """Count total lines in a gzipped file"""
    print(f"\nCounting lines in {filename}...")
    try:
        with gzip.open(filename, 'rt') as f:
            count = sum(1 for _ in f)
        print(f"Total lines: {count:,}")
        return count
    except Exception as e:
        print(f"Error counting lines: {e}")
        return 0

def find_water_example(filename, search_cids=['962', '22247451']):
    """Find specific CIDs in the files"""
    print(f"\nSearching for CIDs {search_cids} in {filename}...")
    found = []
    try:
        with gzip.open(filename, 'rt') as f:
            for line in f:
                parts = line.strip().split('\t')
                for cid in search_cids:
                    if cid in parts:
                        found.append(line.strip())
                        print(f"Found CID {cid}: {line.strip()}")
        return found
    except Exception as e:
        print(f"Error searching: {e}")
        return []

# Main execution
print("PubChem CID Mapping Files Structure Analysis")
print("=" * 60)

# Examine each file
files = ['CID-InChI-Key.gz', 'CID-Parent.gz', 'CID-Preferred.gz']

for filename in files:
    examine_file(filename, num_lines=5)
    
    # Quick line count (commented out for large files)
    # count_lines(filename)
    
    # Search for water examples
    if filename == 'CID-InChI-Key.gz':
        # Search for water InChIKey
        print("\nSearching for water InChIKey (XLYOFNOQVPJJNP-UHFFFAOYSA-N)...")
        with gzip.open(filename, 'rt') as f:
            for line in f:
                if 'XLYOFNOQVPJJNP-UHFFFAOYSA-N' in line:
                    print(f"Found: {line.strip()}")
                    
    # Search for specific CIDs
    find_water_example(filename, ['962', '22247451'])

print("\n" + "="*60)
print("Analysis complete!")