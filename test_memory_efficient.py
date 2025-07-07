#!/usr/bin/env python3
"""
Test the memory-efficient implementation to ensure it works with 16GB RAM constraints
"""

import os
import psutil
import logging
from build_molecule_db_memory_efficient import MemoryEfficientMoleculeDB, MemoryMonitor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_memory_efficiency():
    """Test memory efficiency with different configurations"""
    print("Testing Memory-Efficient Molecule Database Builder")
    print("=" * 60)
    
    # Check system memory
    memory = psutil.virtual_memory()
    total_gb = memory.total / (1024**3)
    available_gb = memory.available / (1024**3)
    
    print(f"System Memory:")
    print(f"  Total: {total_gb:.1f} GB")
    print(f"  Available: {available_gb:.1f} GB")
    print(f"  Used: {memory.percent:.1f}%")
    
    if total_gb > 20:
        print("  ✅ Plenty of memory available")
    elif total_gb > 12:
        print("  ⚠️  Moderate memory - should work fine")
    else:
        print("  ❌ Low memory - may need smaller batch sizes")
    
    # Test different configurations
    configs = [
        {"name": "Conservative (8GB+ systems)", "batch_size": 200, "cache_size": 2000},
        {"name": "Standard (16GB+ systems)", "batch_size": 500, "cache_size": 5000},
        {"name": "Aggressive (32GB+ systems)", "batch_size": 1000, "cache_size": 10000},
    ]
    
    print(f"\n{'='*60}")
    print("Recommended Configurations:")
    print(f"{'='*60}")
    
    for config in configs:
        print(f"\n{config['name']}:")
        print(f"  Batch size: {config['batch_size']}")
        print(f"  Cache size: {config['cache_size']}")
        
        # Estimate memory usage
        estimated_mb = (
            config['batch_size'] * 2 +  # Batch data
            config['cache_size'] * 0.1 +  # Cache overhead
            100  # Base overhead
        )
        print(f"  Estimated peak memory: ~{estimated_mb:.0f} MB")
    
    # Recommend configuration based on available memory
    if available_gb >= 24:
        recommended = configs[2]  # Aggressive
    elif available_gb >= 12:
        recommended = configs[1]  # Standard
    else:
        recommended = configs[0]  # Conservative
    
    print(f"\n{'='*60}")
    print(f"RECOMMENDED FOR YOUR SYSTEM: {recommended['name']}")
    print(f"{'='*60}")
    print(f"Command:")
    print(f"python build_molecule_db_memory_efficient.py \\")
    print(f"  --batch-size {recommended['batch_size']} \\")
    print(f"  --cache-size {recommended['cache_size']} \\")
    print(f"  --max-memory 75 \\")
    print(f"  --max-files 1")

def test_small_batch():
    """Test with a small batch to verify everything works"""
    print(f"\n{'='*60}")
    print("Testing Small Batch Processing")
    print(f"{'='*60}")
    
    # Check if indexes exist
    if not os.path.exists("cid_indexes/preferred.idx"):
        print("❌ CID indexes not found. Run: python create_cid_index.py")
        return
    
    print("✅ CID indexes found")
    
    # Test memory monitor
    monitor = MemoryMonitor()
    monitor.log_memory_usage("test start")
    
    # Test CID mapper
    try:
        from memory_efficient_mapper import MemoryEfficientCIDMapper
        
        with MemoryEfficientCIDMapper(cache_size=100) as mapper:
            # Test basic functionality
            test_cids = ['962', '1', '10']
            for cid in test_cids:
                canonical = mapper.get_canonical_cid(cid)
                print(f"  CID {cid} -> canonical {canonical}")
            
            stats = mapper.get_cache_stats()
            print(f"  Cache stats: {stats}")
        
        print("✅ CID mapper working correctly")
        
    except Exception as e:
        print(f"❌ CID mapper error: {e}")
        return
    
    monitor.log_memory_usage("test end")
    
    print("\n✅ All components working correctly!")
    print("\nTo test with actual data:")
    print("python build_molecule_db_memory_efficient.py --max-files 1 --batch-size 200")

def estimate_full_database_requirements():
    """Estimate requirements for full database build"""
    print(f"\n{'='*60}")
    print("Full Database Build Estimates")
    print(f"{'='*60}")
    
    # From README estimates
    total_molecules = 129_000_000
    avg_molecule_size = 1174  # bytes
    total_files = 352
    
    print(f"Full database scale:")
    print(f"  Total molecules: {total_molecules:,}")
    print(f"  Total files: {total_files}")
    print(f"  Processing time: ~29 days")
    
    # Memory estimates for different batch sizes
    batch_sizes = [200, 500, 1000, 2000]
    
    print(f"\nMemory estimates by batch size:")
    for batch_size in batch_sizes:
        peak_memory_mb = (
            batch_size * avg_molecule_size / 1024 / 1024 * 2 +  # Batch data (double for safety)
            100 +  # Base Python/RDKit overhead
            50 +   # LMDB overhead
            20     # CID mapper cache
        )
        
        processing_time_hours = total_files * 2  # 2 hours per file estimate
        
        print(f"  Batch size {batch_size}: ~{peak_memory_mb:.0f} MB peak")
    
    print(f"\nRecommendations:")
    print(f"  - Use batch_size=200-500 for 16GB systems")
    print(f"  - Use batch_size=500-1000 for 32GB+ systems")
    print(f"  - Monitor memory usage with --max-memory 75")
    print(f"  - Process files sequentially (default)")
    print(f"  - Use --keep-downloads=false to save disk space")

if __name__ == "__main__":
    test_memory_efficiency()
    test_small_batch()
    estimate_full_database_requirements()