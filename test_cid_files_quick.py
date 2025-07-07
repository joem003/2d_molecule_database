#!/usr/bin/env python3
import gzip

# Just examine first few lines of each file
files = {
    'CID-InChI-Key.gz': 'CID to InChIKey mapping',
    'CID-Parent.gz': 'CID to parent compound mapping', 
    'CID-Preferred.gz': 'Non-preferred to preferred CID mapping'
}

for filename, description in files.items():
    print(f"\n{'='*60}")
    print(f"File: {filename} - {description}")
    print(f"{'='*60}")
    
    with gzip.open(filename, 'rt') as f:
        for i in range(5):
            line = f.readline()
            if not line:
                break
            parts = line.strip().split('\t')
            print(f"Line {i+1}: {parts}")
        print(f"Format: {len(parts)} columns")

# Specific water example search
print(f"\n{'='*60}")
print("Searching for water examples (CID 962 and 22247451)...")
print(f"{'='*60}")

# Search in CID-Preferred.gz
print("\nSearching CID-Preferred.gz for 22247451...")
with gzip.open('CID-Preferred.gz', 'rt') as f:
    for line in f:
        if line.startswith('22247451\t'):
            print(f"Found: {line.strip()}")
            break

# Search in CID-InChI-Key.gz for both CIDs
print("\nSearching CID-InChI-Key.gz for water InChIKey...")
water_inchikey = 'XLYOFNOQVPJJNP-UHFFFAOYSA-N'
with gzip.open('CID-InChI-Key.gz', 'rt') as f:
    count = 0
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 2 and parts[1] == water_inchikey:
            print(f"Found CID {parts[0]} → {parts[1]}")
            count += 1
            if count >= 5:  # Limit output
                print("(showing first 5 matches)")
                break