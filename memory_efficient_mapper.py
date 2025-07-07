#!/usr/bin/env python3
"""
Memory-Efficient CID Mapper with LRU Cache

This module provides fast CID preference lookups using binary search on indexed files
with minimal memory usage through LRU caching.
"""

import os
import struct
import bisect
import logging
from functools import lru_cache
from typing import Dict, Set, Optional, Tuple
from collections import defaultdict, OrderedDict

logger = logging.getLogger(__name__)

class LRUCache:
    """Simple LRU cache implementation"""
    
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def get(self, key):
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key, value):
        if key in self.cache:
            # Update existing
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
            self.cache[key] = value
    
    def size(self):
        return len(self.cache)
    
    def clear(self):
        self.cache.clear()

class MemoryEfficientCIDMapper:
    """Memory-efficient CID mapper using indexed files and LRU cache"""
    
    def __init__(self, index_dir="cid_indexes", cache_size=10000):
        self.index_dir = index_dir
        self.preferred_file = os.path.join(index_dir, "preferred.idx")
        self.parent_file = os.path.join(index_dir, "parent.idx")
        
        # LRU caches for lookups
        self.preferred_cache = LRUCache(cache_size)
        self.parent_cache = LRUCache(cache_size)
        
        # In-memory conflict tracking (limited size)
        self.inchikey_conflicts = defaultdict(set)
        self.max_conflicts = 50000  # Limit memory usage
        
        # Index metadata (loaded once)
        self._preferred_count = None
        self._parent_count = None
        
        # File handles (opened once)
        self._preferred_file = None
        self._parent_file = None
        
        self._load_index_metadata()
    
    def _load_index_metadata(self):
        """Load index file metadata"""
        try:
            if os.path.exists(self.preferred_file):
                with open(self.preferred_file, 'rb') as f:
                    self._preferred_count = struct.unpack('<I', f.read(4))[0]
                logger.info(f"Preferred index: {self._preferred_count:,} entries")
            else:
                logger.warning(f"Preferred index not found: {self.preferred_file}")
                self._preferred_count = 0
            
            if os.path.exists(self.parent_file):
                with open(self.parent_file, 'rb') as f:
                    self._parent_count = struct.unpack('<I', f.read(4))[0]
                logger.info(f"Parent index: {self._parent_count:,} entries")
            else:
                logger.warning(f"Parent index not found: {self.parent_file}")
                self._parent_count = 0
                
        except Exception as e:
            logger.error(f"Error loading index metadata: {e}")
            self._preferred_count = 0
            self._parent_count = 0
    
    def _open_files(self):
        """Open index files for reading"""
        if self._preferred_file is None and os.path.exists(self.preferred_file):
            self._preferred_file = open(self.preferred_file, 'rb')
            self._preferred_file.seek(4)  # Skip header
        
        if self._parent_file is None and os.path.exists(self.parent_file):
            self._parent_file = open(self.parent_file, 'rb')
            self._parent_file.seek(4)  # Skip header
    
    def close(self):
        """Close file handles"""
        if self._preferred_file:
            self._preferred_file.close()
            self._preferred_file = None
        if self._parent_file:
            self._parent_file.close()
            self._parent_file = None
    
    def _binary_search_preferred(self, cid_int):
        """Binary search in preferred index file"""
        if self._preferred_count == 0:
            return None
        
        self._open_files()
        if not self._preferred_file:
            return None
        
        left, right = 0, self._preferred_count - 1
        
        while left <= right:
            mid = (left + right) // 2
            
            # Seek to position
            pos = 4 + mid * 8  # header + (mid * 8 bytes per entry)
            self._preferred_file.seek(pos)
            
            # Read entry
            data = self._preferred_file.read(8)
            if len(data) != 8:
                break
            
            non_preferred, preferred = struct.unpack('<II', data)
            
            if non_preferred == cid_int:
                return preferred
            elif non_preferred < cid_int:
                left = mid + 1
            else:
                right = mid - 1
        
        return None
    
    def _binary_search_parent(self, cid_int):
        """Binary search in parent index file"""
        if self._parent_count == 0:
            return None
        
        self._open_files()
        if not self._parent_file:
            return None
        
        left, right = 0, self._parent_count - 1
        
        while left <= right:
            mid = (left + right) // 2
            
            # Seek to position
            pos = 4 + mid * 8  # header + (mid * 8 bytes per entry)
            self._parent_file.seek(pos)
            
            # Read entry
            data = self._parent_file.read(8)
            if len(data) != 8:
                break
            
            cid, parent = struct.unpack('<II', data)
            
            if cid == cid_int:
                return parent
            elif cid < cid_int:
                left = mid + 1
            else:
                right = mid - 1
        
        return None
    
    def get_preferred_cid(self, cid):
        """Get preferred CID with LRU caching"""
        # Check cache first
        cached = self.preferred_cache.get(cid)
        if cached is not None:
            return cached
        
        try:
            cid_int = int(cid)
        except ValueError:
            return cid
        
        # Binary search in index
        preferred_int = self._binary_search_preferred(cid_int)
        
        if preferred_int is not None:
            result = str(preferred_int)
        else:
            # Not found, CID is its own preferred
            result = cid
        
        # Cache result
        self.preferred_cache.put(cid, result)
        return result
    
    def get_parent_cid(self, cid):
        """Get parent CID with LRU caching"""
        # Check cache first
        cached = self.parent_cache.get(cid)
        if cached is not None:
            return cached
        
        try:
            cid_int = int(cid)
        except ValueError:
            return cid
        
        # Binary search in index
        parent_int = self._binary_search_parent(cid_int)
        
        if parent_int is not None:
            result = str(parent_int)
        else:
            # Not found, CID is its own parent
            result = cid
        
        # Cache result
        self.parent_cache.put(cid, result)
        return result
    
    def get_canonical_cid(self, cid):
        """Get canonical CID (preferred then parent)"""
        preferred = self.get_preferred_cid(cid)
        canonical = self.get_parent_cid(preferred)
        return canonical
    
    def register_inchikey_conflict(self, inchikey, cid):
        """Register InChIKey conflict with memory limit"""
        # Limit memory usage
        if len(self.inchikey_conflicts) >= self.max_conflicts:
            # Remove some old conflicts
            keys_to_remove = list(self.inchikey_conflicts.keys())[:1000]
            for key in keys_to_remove:
                del self.inchikey_conflicts[key]
        
        self.inchikey_conflicts[inchikey].add(cid)
    
    def resolve_inchikey_conflict(self, inchikey):
        """Resolve InChIKey conflict by preferring canonical CIDs"""
        cids = self.inchikey_conflicts.get(inchikey, set())
        
        if len(cids) <= 1:
            return next(iter(cids)) if cids else None
        
        # Find the most canonical CID
        canonical_pairs = []
        for cid in cids:
            canonical = self.get_canonical_cid(cid)
            canonical_pairs.append((cid, canonical))
        
        # Prefer CIDs that are their own canonical form
        for cid, canonical in canonical_pairs:
            if cid == canonical:
                logger.debug(f"Resolved InChIKey {inchikey}: CID {cid} is canonical")
                return cid
        
        # Fallback: use the canonical form of the first CID
        first_cid = sorted(cids)[0]
        canonical = self.get_canonical_cid(first_cid)
        logger.debug(f"Resolved InChIKey {inchikey}: Using canonical {canonical} for CID {first_cid}")
        return canonical
    
    def clear_conflicts(self):
        """Clear conflict tracking to free memory"""
        self.inchikey_conflicts.clear()
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return {
            'preferred_cache_size': self.preferred_cache.size(),
            'parent_cache_size': self.parent_cache.size(),
            'conflicts_tracked': len(self.inchikey_conflicts),
            'max_conflicts': self.max_conflicts
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def test_memory_efficient_mapper():
    """Test the memory-efficient mapper"""
    print("Testing Memory-Efficient CID Mapper")
    print("=" * 40)
    
    with MemoryEfficientCIDMapper(cache_size=1000) as mapper:
        # Test with known values
        test_cids = ['962', '22247451', '1', '10']
        
        print("Testing CID mappings:")
        for cid in test_cids:
            preferred = mapper.get_preferred_cid(cid)
            parent = mapper.get_parent_cid(preferred)
            canonical = mapper.get_canonical_cid(cid)
            
            print(f"  CID {cid}: preferred={preferred}, parent={parent}, canonical={canonical}")
        
        # Test cache performance
        print("\nTesting cache performance (repeated lookups):")
        import time
        
        start = time.time()
        for _ in range(1000):
            for cid in test_cids:
                mapper.get_canonical_cid(cid)
        end = time.time()
        
        print(f"  1000 lookups x {len(test_cids)} CIDs: {(end-start)*1000:.2f}ms")
        
        # Test conflict resolution
        water_inchikey = "XLYOFNOQVPJJNP-UHFFFAOYSA-N"
        mapper.register_inchikey_conflict(water_inchikey, '962')
        mapper.register_inchikey_conflict(water_inchikey, '22247451')
        
        preferred = mapper.resolve_inchikey_conflict(water_inchikey)
        print(f"\nWater conflict resolution: {preferred}")
        
        # Show cache stats
        stats = mapper.get_cache_stats()
        print(f"\nCache stats: {stats}")

if __name__ == "__main__":
    test_memory_efficient_mapper()