#!/usr/bin/env python3
import requests
import json

print("Testing Minimal 2D Molecule Database System")
print("=" * 50)

# Test API health
try:
    response = requests.get("http://127.0.0.1:5000/api/health")
    print(f"✓ API Health: {response.json()}")
except Exception as e:
    print(f"✗ API Health failed: {e}")

# Test getting a molecule
test_inchikey = "RDHQFKQIGNGIED-UHFFFAOYSA-N"
try:
    response = requests.get(f"http://127.0.0.1:5000/api/molecule/{test_inchikey}")
    data = response.json()
    print(f"\n✓ Retrieved minimal molecule data: {test_inchikey}")
    print(f"  Atoms: {len(data.get('a', []))}")
    print(f"  Bonds: {len(data.get('b', []))}")
    print(f"  Response size: {len(response.content)} bytes")
    print(f"  First atom: {data['a'][0] if data['a'] else 'None'}")
    print(f"  First bond: {data['b'][0] if data['b'] else 'None'}")
except Exception as e:
    print(f"\n✗ Molecule retrieval failed: {e}")

# Compare database sizes
import os
try:
    if os.path.exists("molecule_2d.lmdb"):
        full_size = sum(os.path.getsize(os.path.join("molecule_2d.lmdb", f)) 
                       for f in os.listdir("molecule_2d.lmdb"))
        print(f"\n📊 Full MOL database size: {full_size / (1024*1024):.1f} MB")
    
    if os.path.exists("molecule_2d_minimal.lmdb"):
        minimal_size = sum(os.path.getsize(os.path.join("molecule_2d_minimal.lmdb", f)) 
                          for f in os.listdir("molecule_2d_minimal.lmdb"))
        print(f"📊 Minimal 2D database size: {minimal_size / (1024*1024):.1f} MB")
        
        if os.path.exists("molecule_2d.lmdb"):
            savings = ((full_size - minimal_size) / full_size) * 100
            print(f"💾 Space savings: {savings:.1f}%")
    
except Exception as e:
    print(f"\n⚠️  Could not compare database sizes: {e}")

print("\n" + "=" * 50)
print("Web Interface: http://localhost:3000")
print(f"\nExample InChIKey to try: {test_inchikey}")
print("\nThe system now stores only:")
print("- 2D atom coordinates (x, y)")
print("- Element symbols")
print("- Bond connectivity and types")
print("- No formulas, SMILES, or other computed data")