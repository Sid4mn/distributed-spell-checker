"""
Simple Cache Manager for Spell Checker
LRU Cache with TTL for performance optimization
"""

import time
from collections import OrderedDict

class SpellCheckCache:
    def __init__(self, max_size=100, ttl=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.hits = 0
        self.misses = 0
        
    def get(self, text):
        """Get corrected text from cache if exists and not expired"""
        if text in self.cache:
            timestamp, corrected_text = self.cache[text]
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self.cache[text]
                self.misses += 1
                return None
                
            # Move to end (most recently used)
            self.cache.move_to_end(text)
            self.hits += 1
            return corrected_text
            
        self.misses += 1
        return None
        
    def put(self, text, corrected_text):
        """Store corrected text in cache"""
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
            
        self.cache[text] = (time.time(), corrected_text)
        
    def get_stats(self):
        """Get simple cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'size': len(self.cache),
            'max_size': self.max_size
        }
        
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0