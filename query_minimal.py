#!/usr/bin/env python3
import lmdb
import json

def check_minimal_db():
    env = lmdb.open("molecule_2d_minimal.lmdb", readonly=True)
    
    with env.begin() as txn:
        stats = txn.stat()
        print(f"Total molecules in minimal database: {stats['entries']:,}")
        
        # Show sample data
        cursor = txn.cursor()
        count = 0
        for key, value in cursor:
            if count >= 3:
                break
            
            inchikey = key.decode()
            data = json.loads(value.decode())
            
            print(f"\nSample {count + 1}: {inchikey}")
            print(f"  Atoms: {len(data['a'])}")
            print(f"  Bonds: {len(data['b'])}")
            print(f"  Size: {len(value)} bytes")
            
            count += 1

if __name__ == "__main__":
    try:
        check_minimal_db()
    except Exception as e:
        print(f"Error: {e}")
        print("Database may not exist yet")