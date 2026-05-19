"""
Caching Manager for WAFR Enterprise Scoring.

Implements comprehensive caching strategies for:
- Capability definitions
- Service-to-capability mappings
- Pattern definitions
- Configuration files

Supports cache invalidation on configuration reload for hot-reload capability.
"""

import json
import os
import time
import hashlib
from functools import lru_cache, wraps
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import threading

from ..core.logger import WAFRLogger


class CacheEntry:
    """
    Represents a cached entry with metadata.
    """
    
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None):
        """
        Initialize cache entry.
        
        Args:
            value: The cached value
            ttl_seconds: Time-to-live in seconds (None for no expiration)
        """
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def access(self) -> Any:
        """Access the cached value and update metadata."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value


class CachingManager:
    """
    Centralized caching manager for WAFR scoring components.
    
    Features:
    - Multi-level caching (memory, LRU)
    - TTL support for time-based expiration
    - Cache invalidation on configuration reload
    - Thread-safe operations
    - Performance metrics and monitoring
    """
    
    def __init__(self, default_ttl: Optional[int] = None):
        """
        Initialize CachingManager.
        
        Args:
            default_ttl: Default time-to-live in seconds (None for no expiration)
        """
        self.logger = WAFRLogger(__name__)
        self.default_ttl = default_ttl
        
        # Thread-safe cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.RLock()
        
        # Cache metrics
        self._metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0
        }
        
        # Configuration file hashes for change detection
        self._config_hashes: Dict[str, str] = {}
        
        self.logger.info(f"CachingManager initialized (TTL: {default_ttl}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._metrics['misses'] += 1
                return None
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._metrics['evictions'] += 1
                self._metrics['misses'] += 1
                return None
            
            self._metrics['hits'] += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default)
        """
        with self._cache_lock:
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            self._cache[key] = CacheEntry(value, ttl_to_use)
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was found and removed
        """
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                self._metrics['invalidations'] += 1
                return True
            return False
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports wildcards)
        """
        with self._cache_lock:
            keys_to_remove = []
            
            for key in self._cache.keys():
                if self._matches_pattern(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
                self._metrics['invalidations'] += 1
            
            if keys_to_remove:
                self.logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """
        Check if key matches pattern.
        
        Args:
            key: Cache key
            pattern: Pattern with wildcards (*)
            
        Returns:
            True if key matches pattern
        """
        import re
        regex_pattern = pattern.replace('*', '.*')
        return re.match(f"^{regex_pattern}$", key) is not None
    
    def clear(self):
        """Clear all cache entries."""
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            self._metrics['invalidations'] += count
            self.logger.info(f"Cleared {count} cache entries")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.
        
        Returns:
            Dictionary with cache metrics
        """
        with self._cache_lock:
            total_requests = self._metrics['hits'] + self._metrics['misses']
            hit_rate = self._metrics['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'hits': self._metrics['hits'],
                'misses': self._metrics['misses'],
                'hit_rate': hit_rate,
                'evictions': self._metrics['evictions'],
                'invalidations': self._metrics['invalidations'],
                'current_size': len(self._cache),
                'total_requests': total_requests
            }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Dictionary with cache details
        """
        with self._cache_lock:
            entries_info = []
            
            for key, entry in self._cache.items():
                entries_info.append({
                    'key': key,
                    'created_at': entry.created_at.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'ttl_seconds': entry.ttl_seconds,
                    'is_expired': entry.is_expired()
                })
            
            return {
                'metrics': self.get_metrics(),
                'entries': entries_info
            }


class ConfigurationCache:
    """
    Specialized cache for configuration files with change detection.
    
    Automatically invalidates cache when configuration files change.
    """
    
    def __init__(self, config_dir: str):
        """
        Initialize ConfigurationCache.
        
        Args:
            config_dir: Path to configuration directory
        """
        self.logger = WAFRLogger(__name__)
        self.config_dir = config_dir
        
        # Use CachingManager for storage
        self.cache_manager = CachingManager(default_ttl=None)  # No TTL for config
        
        # Track file modification times
        self._file_mtimes: Dict[str, float] = {}
        
        self.logger.info(f"ConfigurationCache initialized for {config_dir}")
    
    def get_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration from cache or load from file.
        
        Automatically reloads if file has changed.
        
        Args:
            config_path: Relative path to config file
            
        Returns:
            Configuration dictionary or None if not found
        """
        full_path = os.path.join(self.config_dir, config_path)
        
        # Check if file has changed
        if self._has_file_changed(full_path):
            self.logger.info(f"Configuration file changed, reloading: {config_path}")
            self.cache_manager.invalidate(config_path)
        
        # Try to get from cache
        cached_config = self.cache_manager.get(config_path)
        if cached_config is not None:
            return cached_config
        
        # Load from file
        config = self._load_config_file(full_path)
        if config is not None:
            self.cache_manager.set(config_path, config)
            self._update_file_mtime(full_path)
        
        return config
    
    def _load_config_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Full path to config file
            
        Returns:
            Configuration dictionary or None if error
        """
        if not os.path.exists(filepath):
            self.logger.warning(f"Configuration file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
                self.logger.debug(f"Loaded configuration from {filepath}")
                return config
        except Exception as e:
            self.logger.error(f"Error loading configuration from {filepath}: {e}")
            return None
    
    def _has_file_changed(self, filepath: str) -> bool:
        """
        Check if file has been modified since last load.
        
        Args:
            filepath: Full path to file
            
        Returns:
            True if file has changed
        """
        if not os.path.exists(filepath):
            return False
        
        current_mtime = os.path.getmtime(filepath)
        last_mtime = self._file_mtimes.get(filepath)
        
        return last_mtime is None or current_mtime > last_mtime
    
    def _update_file_mtime(self, filepath: str):
        """
        Update stored modification time for file.
        
        Args:
            filepath: Full path to file
        """
        if os.path.exists(filepath):
            self._file_mtimes[filepath] = os.path.getmtime(filepath)
    
    def invalidate_all(self):
        """Invalidate all cached configurations."""
        self.cache_manager.clear()
        self._file_mtimes.clear()
        self.logger.info("All configuration caches invalidated")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        return self.cache_manager.get_metrics()


def cached_method(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator for caching method results.
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from args
        
    Example:
        @cached_method(ttl=300)
        def expensive_operation(self, param1, param2):
            # ... expensive computation
            return result
    """
    def decorator(func):
        cache = CachingManager(default_ttl=ttl)
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and args
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = cache.get_metrics
        
        return wrapper
    
    return decorator


class ServiceMappingCache:
    """
    Specialized cache for service-to-capability mappings.
    
    Optimizes repeated lookups of which capabilities a service provides.
    """
    
    def __init__(self, capability_definitions: Dict[str, Dict[str, Any]]):
        """
        Initialize ServiceMappingCache.
        
        Args:
            capability_definitions: Capability definitions to build mappings from
        """
        self.logger = WAFRLogger(__name__)
        self.capability_definitions = capability_definitions
        
        # Pre-compute service-to-capability mappings
        self._service_to_capabilities: Dict[str, List[str]] = {}
        self._build_service_mappings()
        
        self.logger.info(f"ServiceMappingCache initialized with {len(self._service_to_capabilities)} service mappings")
    
    def _build_service_mappings(self):
        """
        Build reverse mapping from services to capabilities.
        
        Pre-computes which capabilities each service can provide.
        """
        for capability_name, capability_def in self.capability_definitions.items():
            services = capability_def.get('services', {})
            
            for service_name in services.keys():
                if service_name not in self._service_to_capabilities:
                    self._service_to_capabilities[service_name] = []
                
                self._service_to_capabilities[service_name].append(capability_name)
    
    def get_service_capabilities(self, service_name: str) -> List[str]:
        """
        Get list of capabilities a service can provide.
        
        Args:
            service_name: AWS service name
            
        Returns:
            List of capability names
        """
        return self._service_to_capabilities.get(service_name, [])
    
    def get_all_services(self) -> List[str]:
        """
        Get list of all services in the mapping.
        
        Returns:
            List of service names
        """
        return list(self._service_to_capabilities.keys())
    
    def rebuild(self, capability_definitions: Dict[str, Dict[str, Any]]):
        """
        Rebuild mappings with new capability definitions.
        
        Call this after configuration reload.
        
        Args:
            capability_definitions: New capability definitions
        """
        self.capability_definitions = capability_definitions
        self._service_to_capabilities.clear()
        self._build_service_mappings()
        self.logger.info("Service mappings rebuilt")


class PatternDefinitionCache:
    """
    Cache for architecture pattern definitions.
    
    Optimizes pattern detection and adjustment lookups.
    """
    
    def __init__(self, config_dir: str):
        """
        Initialize PatternDefinitionCache.
        
        Args:
            config_dir: Path to configuration directory
        """
        self.logger = WAFRLogger(__name__)
        self.config_dir = config_dir
        
        # Use ConfigurationCache for storage
        self.config_cache = ConfigurationCache(config_dir)
        
        # Cache pattern definitions
        self._patterns: Optional[Dict[str, Dict[str, Any]]] = None
        
        self.logger.info("PatternDefinitionCache initialized")
    
    def get_pattern_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all pattern definitions.
        
        Returns:
            Dictionary of pattern definitions
        """
        if self._patterns is None:
            self._patterns = self.config_cache.get_config('patterns/architecture_patterns.json')
            
            if self._patterns is None:
                self.logger.warning("Pattern definitions not found, using empty dict")
                self._patterns = {}
        
        return self._patterns
    
    def get_pattern(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific pattern definition.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Pattern definition or None if not found
        """
        patterns = self.get_pattern_definitions()
        return patterns.get(pattern_name)
    
    def invalidate(self):
        """Invalidate pattern cache."""
        self._patterns = None
        self.config_cache.invalidate_all()
        self.logger.info("Pattern cache invalidated")


class CacheCoordinator:
    """
    Coordinates all caching components for WAFR scoring.
    
    Provides unified interface for cache management and invalidation.
    """
    
    def __init__(self, config_dir: str):
        """
        Initialize CacheCoordinator.
        
        Args:
            config_dir: Path to configuration directory
        """
        self.logger = WAFRLogger(__name__)
        
        # Initialize all cache components
        self.config_cache = ConfigurationCache(config_dir)
        self.general_cache = CachingManager(default_ttl=3600)  # 1 hour TTL
        
        # Pattern cache will be initialized when needed
        self.pattern_cache = PatternDefinitionCache(config_dir)
        
        # Service mapping cache will be initialized with capability definitions
        self._service_mapping_cache: Optional[ServiceMappingCache] = None
        
        self.logger.info("CacheCoordinator initialized")
    
    def get_service_mapping_cache(
        self,
        capability_definitions: Dict[str, Dict[str, Any]]
    ) -> ServiceMappingCache:
        """
        Get or create service mapping cache.
        
        Args:
            capability_definitions: Capability definitions
            
        Returns:
            ServiceMappingCache instance
        """
        if self._service_mapping_cache is None:
            self._service_mapping_cache = ServiceMappingCache(capability_definitions)
        
        return self._service_mapping_cache
    
    def invalidate_all(self):
        """Invalidate all caches."""
        self.config_cache.invalidate_all()
        self.general_cache.clear()
        self.pattern_cache.invalidate()
        
        if self._service_mapping_cache is not None:
            # Service mapping cache will be rebuilt on next access
            self._service_mapping_cache = None
        
        self.logger.info("All caches invalidated")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from all cache components.
        
        Returns:
            Dictionary with all cache metrics
        """
        return {
            'config_cache': self.config_cache.get_metrics(),
            'general_cache': self.general_cache.get_metrics(),
            'service_mapping_cache': {
                'initialized': self._service_mapping_cache is not None,
                'service_count': len(self._service_mapping_cache.get_all_services()) if self._service_mapping_cache else 0
            }
        }
