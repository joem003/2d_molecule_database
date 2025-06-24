#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import os
import lmdb
import json

def get_pubchem_file_stats():
    """Get statistics about PubChem SDF files"""
    print("Fetching PubChem file information...")
    
    base_url = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/SDF/"
    
    try:
        response = requests.get(base_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        sdf_files = []
        
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.endswith('.sdf.gz'):
                sdf_files.append(href)
        
        return sorted(sdf_files)
    except Exception as e:
        print(f"Error fetching file list: {e}")
        return []

def analyze_current_database():
    """Analyze current minimal database"""
    print("\n" + "="*60)
    print("CURRENT DATABASE ANALYSIS")
    print("="*60)
    
    db_path = "molecule_2d_minimal.lmdb"
    
    if not os.path.exists(db_path):
        print("❌ Minimal database not found")
        return None, None, None
    
    try:
        env = lmdb.open(db_path, readonly=True)
        
        with env.begin() as txn:
            stats = txn.stat()
            total_molecules = stats['entries']
            
            # Sample molecules to get average size
            cursor = txn.cursor()
            sample_sizes = []
            sample_atoms = []
            sample_bonds = []
            
            count = 0
            for key, value in cursor:
                if count >= 1000:  # Sample 1000 molecules
                    break
                    
                try:
                    data = json.loads(value.decode())
                    sample_sizes.append(len(value))
                    sample_atoms.append(len(data.get('a', [])))
                    sample_bonds.append(len(data.get('b', [])))
                    count += 1
                except:
                    continue
            
            if sample_sizes:
                avg_size = sum(sample_sizes) / len(sample_sizes)
                avg_atoms = sum(sample_atoms) / len(sample_atoms)
                avg_bonds = sum(sample_bonds) / len(sample_bonds)
                
                # Calculate actual database size
                actual_size = sum(os.path.getsize(os.path.join(db_path, f)) 
                                for f in os.listdir(db_path))
                
                print(f"📊 Current molecules: {total_molecules:,}")
                print(f"📊 Average molecule size: {avg_size:.0f} bytes")
                print(f"📊 Average atoms per molecule: {avg_atoms:.1f}")
                print(f"📊 Average bonds per molecule: {avg_bonds:.1f}")
                print(f"📊 Current database size: {actual_size / (1024*1024):.1f} MB")
                print(f"📊 Data efficiency: {(total_molecules * avg_size) / actual_size * 100:.1f}% (rest is LMDB overhead)")
                
                return total_molecules, avg_size, actual_size
            else:
                print("❌ Could not sample molecules")
                return None, None, None
                
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")
        return None, None, None

def estimate_full_database_size():
    """Estimate size for complete PubChem database"""
    print("\n" + "="*60)
    print("FULL DATABASE SIZE ESTIMATION")
    print("="*60)
    
    # Get file list
    sdf_files = get_pubchem_file_stats()
    
    if not sdf_files:
        print("❌ Could not fetch file list")
        return
    
    print(f"📈 Total SDF files available: {len(sdf_files)}")
    
    # Get current stats
    current_molecules, avg_size, current_db_size = analyze_current_database()
    
    if not current_molecules:
        print("❌ Cannot estimate without current database stats")
        return
    
    # Estimate based on first file
    # PubChem files contain roughly 500k molecules each (as per their documentation)
    # But let's use our actual data from the first file
    molecules_per_file = current_molecules  # From first file
    
    # Estimate total molecules
    estimated_total_molecules = len(sdf_files) * molecules_per_file
    
    # Estimate total size
    estimated_data_size = estimated_total_molecules * avg_size
    
    # Add LMDB overhead (approximately 40% based on current analysis)
    overhead_factor = current_db_size / (current_molecules * avg_size)
    estimated_total_size = estimated_data_size * overhead_factor
    
    print(f"\n🔮 PROJECTIONS FOR COMPLETE DATABASE:")
    print(f"   Total molecules: {estimated_total_molecules:,}")
    print(f"   Raw data size: {estimated_data_size / (1024**3):.1f} GB")
    print(f"   With LMDB overhead: {estimated_total_size / (1024**3):.1f} GB")
    print(f"   Processing time estimate: {len(sdf_files) * 2:.0f} hours")
    
    # Show file progress
    print(f"\n📁 FILE PROGRESS:")
    print(f"   Processed: 1 / {len(sdf_files)} files ({1/len(sdf_files)*100:.1f}%)")
    print(f"   Remaining: {len(sdf_files) - 1} files")
    
    # Show size comparisons
    print(f"\n💾 SIZE COMPARISONS:")
    print(f"   Current minimal DB: {current_db_size / (1024**2):.0f} MB")
    print(f"   Estimated full minimal DB: {estimated_total_size / (1024**3):.0f} GB")
    
    # If full MOL database exists, compare
    full_db_path = "molecule_2d.lmdb"
    if os.path.exists(full_db_path):
        try:
            full_size = sum(os.path.getsize(os.path.join(full_db_path, f)) 
                           for f in os.listdir(full_db_path))
            estimated_full_mol_size = full_size * len(sdf_files)
            savings = (estimated_full_mol_size - estimated_total_size) / estimated_full_mol_size * 100
            
            print(f"   Estimated full MOL DB: {estimated_full_mol_size / (1024**3):.0f} GB")
            print(f"   💰 Space savings: {savings:.0f}% ({(estimated_full_mol_size - estimated_total_size) / (1024**3):.0f} GB)")
        except:
            pass

def check_download_requirements():
    """Check what's needed for full download"""
    print("\n" + "="*60)
    print("DOWNLOAD REQUIREMENTS")
    print("="*60)
    
    sdf_files = get_pubchem_file_stats()
    
    if not sdf_files:
        return
    
    # Check if first file exists
    first_file = "downloads/Compound_000000001_000500000.sdf.gz"
    if os.path.exists(first_file):
        file_size = os.path.getsize(first_file)
        total_download_size = file_size * len(sdf_files)
        
        print(f"📥 DOWNLOAD ESTIMATES:")
        print(f"   First file size: {file_size / (1024**2):.0f} MB")
        print(f"   Total download size: {total_download_size / (1024**3):.0f} GB")
        print(f"   Download time (10 Mbps): {total_download_size / (10 * 1024**2 / 8) / 3600:.1f} hours")
        print(f"   Download time (100 Mbps): {total_download_size / (100 * 1024**2 / 8) / 3600:.1f} hours")

def main():
    print("🧬 PubChem 2D Molecule Database Size Estimator")
    print("=" * 60)
    
    analyze_current_database()
    estimate_full_database_size()
    check_download_requirements()
    
    print("\n" + "="*60)
    print("📋 RECOMMENDATIONS:")
    print("   • Current minimal format is very efficient")
    print("   • Full database will be large but manageable")
    print("   • Consider processing in batches if storage is limited")
    print("   • Use --keep-downloads flag only if you have extra space")

if __name__ == "__main__":
    main()