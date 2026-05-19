#!/usr/bin/env python3
"""
Performance Optimized S3 Document Loader
Implements connection pooling, caching, and large file optimization for production environments
Requirements: 5.3, 5.4, 5.5
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
import json

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .consts import get_aws_region


@dataclass
class CacheEntry:
    """Cache entry for document content"""
    content: bytes
    size_mb: float
    access_time: datetime
    access_count: int
    document_url: str


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    cache_hits: int = 0
    cache_misses: int = 0
    total_download_time: float = 0.0
    total_documents_processed: int = 0
    connection_reuses: int = 0
    average_download_speed_mbps: float = 0.0


class S3ConnectionPool:
    """Connection pool for S3 clients with reuse optimization"""
    
    def __init__(self, max_connections: int = 10, region_name: str = None):
        self.max_connections = max_connections
        self.region_name = region_name or get_aws_region()
        self.active_connections: List[Any] = []
        self.available_connections: List[Any] = []
        self.connection_reuse_count = 0
        self.logger = logging.getLogger(__name__)
        
        # S3 client configuration optimized for performance
        self.s3_config = Config(
            region_name=region_name,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=max_connections,
            read_timeout=45,  # 45 seconds for large files
            connect_timeout=15,  # 15 seconds for connection
            tcp_keepalive=True
        )
    
    def get_connection(self):
        """Get S3 client connection from pool"""
        if self.available_connections:
            # Reuse existing connection
            connection = self.available_connections.pop()
            self.connection_reuse_count += 1
            self.logger.debug(f"Reusing S3 connection (reuse count: {self.connection_reuse_count})")
            return connection
        
        elif len(self.active_connections) < self.max_connections:
            # Create new connection
            if BOTO3_AVAILABLE:
                connection = boto3.client('s3', config=self.s3_config)
            else:
                # Mock connection for testing
                connection = MockS3Client()
            
            self.active_connections.append(connection)
            self.logger.debug(f"Created new S3 connection (total: {len(self.active_connections)})")
            return connection
        
        else:
            # Pool exhausted, wait and reuse
            self.logger.warning("S3 connection pool exhausted, reusing oldest connection")
            return self.active_connections[0]
    
    def release_connection(self, connection):
        """Release connection back to pool"""
        if connection in self.active_connections and connection not in self.available_connections:
            self.available_connections.append(connection)
            self.logger.debug("Released S3 connection back to pool")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'max_connections': self.max_connections,
            'active_connections': len(self.active_connections),
            'available_connections': len(self.available_connections),
            'connection_reuses': self.connection_reuse_count,
            'pool_utilization': len(self.active_connections) / self.max_connections * 100
        }


class DocumentCache:
    """LRU cache for frequently accessed documents"""
    
    def __init__(self, max_size_mb: float = 100.0, max_entries: int = 50):
        self.max_size_mb = max_size_mb
        self.max_entries = max_entries
        self.cache: Dict[str, CacheEntry] = {}
        self.current_size_mb = 0.0
        self.logger = logging.getLogger(__name__)
    
    def _generate_cache_key(self, document_url: str) -> str:
        """Generate cache key from document URL"""
        return hashlib.md5(document_url.encode()).hexdigest()
    
    def get(self, document_url: str) -> Optional[bytes]:
        """Get document from cache"""
        cache_key = self._generate_cache_key(document_url)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            entry.access_time = datetime.now()
            entry.access_count += 1
            
            self.logger.debug(f"Cache HIT for {document_url} (access count: {entry.access_count})")
            return entry.content
        
        self.logger.debug(f"Cache MISS for {document_url}")
        return None
    
    def put(self, document_url: str, content: bytes) -> bool:
        """Put document in cache"""
        size_mb = len(content) / (1024 * 1024)
        
        # Check if document is too large for cache
        if size_mb > self.max_size_mb * 0.5:  # Don't cache files larger than 50% of cache size
            self.logger.debug(f"Document too large for cache: {size_mb:.1f}MB")
            return False
        
        # Make room if necessary
        while (self.current_size_mb + size_mb > self.max_size_mb or 
               len(self.cache) >= self.max_entries):
            if not self._evict_lru():
                break
        
        # Add to cache if there's room
        if self.current_size_mb + size_mb <= self.max_size_mb:
            cache_key = self._generate_cache_key(document_url)
            
            entry = CacheEntry(
                content=content,
                size_mb=size_mb,
                access_time=datetime.now(),
                access_count=1,
                document_url=document_url
            )
            
            self.cache[cache_key] = entry
            self.current_size_mb += size_mb
            
            self.logger.debug(f"Cached document: {document_url} ({size_mb:.1f}MB)")
            return True
        
        return False
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry"""
        if not self.cache:
            return False
        
        # Find LRU entry
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k].access_time, self.cache[k].access_count))
        
        entry = self.cache[lru_key]
        self.current_size_mb -= entry.size_mb
        del self.cache[lru_key]
        
        self.logger.debug(f"Evicted LRU entry: {entry.document_url} ({entry.size_mb:.1f}MB)")
        return True
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        
        return {
            'entries': len(self.cache),
            'max_entries': self.max_entries,
            'current_size_mb': round(self.current_size_mb, 2),
            'max_size_mb': self.max_size_mb,
            'utilization_percent': round(self.current_size_mb / self.max_size_mb * 100, 1),
            'total_accesses': total_accesses,
            'average_accesses_per_entry': round(total_accesses / len(self.cache), 1) if self.cache else 0
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.current_size_mb = 0.0
        self.logger.info("Document cache cleared")


class PerformanceOptimizedS3Loader:
    """Performance optimized S3 document loader with caching and connection pooling"""
    
    def __init__(self, 
                 region_name: str = None,
                 max_connections: int = 10,
                 cache_size_mb: float = 100.0,
                 chunk_size_mb: float = 5.0):
        
        self.region_name = region_name or get_aws_region()
        self.chunk_size_mb = chunk_size_mb
        self.chunk_size_bytes = int(chunk_size_mb * 1024 * 1024)
        
        # Initialize components
        self.connection_pool = S3ConnectionPool(max_connections, region_name)
        self.document_cache = DocumentCache(cache_size_mb)
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(__name__)
        
        # Retry configuration
        self.retry_config = {
            'max_attempts': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'backoff_multiplier': 2.0
        }
    
    async def load_document_optimized(self, document_url: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Load document with performance optimizations
        
        Returns:
            Tuple of (document_content, performance_info)
        """
        start_time = time.time()
        
        # Check cache first
        cached_content = self.document_cache.get(document_url)
        if cached_content is not None:
            self.performance_metrics.cache_hits += 1
            
            load_time = time.time() - start_time
            
            performance_info = {
                'cache_hit': True,
                'load_time_seconds': load_time,
                'document_size_mb': len(cached_content) / (1024 * 1024),
                'source': 'cache'
            }
            
            self.logger.info(f"Document loaded from cache in {load_time:.3f}s: {document_url}")
            return cached_content, performance_info
        
        # Cache miss - load from S3
        self.performance_metrics.cache_misses += 1
        
        try:
            content, s3_performance = await self._load_from_s3_with_retry(document_url)
            
            # Cache the document for future use
            cache_success = self.document_cache.put(document_url, content)
            
            total_load_time = time.time() - start_time
            
            performance_info = {
                'cache_hit': False,
                'load_time_seconds': total_load_time,
                'document_size_mb': len(content) / (1024 * 1024),
                'source': 's3',
                'cached_for_future': cache_success,
                's3_performance': s3_performance
            }
            
            # Update metrics
            self.performance_metrics.total_documents_processed += 1
            self.performance_metrics.total_download_time += total_load_time
            
            if performance_info['document_size_mb'] > 0:
                speed_mbps = performance_info['document_size_mb'] / total_load_time
                self.performance_metrics.average_download_speed_mbps = (
                    (self.performance_metrics.average_download_speed_mbps * 
                     (self.performance_metrics.total_documents_processed - 1) + speed_mbps) /
                    self.performance_metrics.total_documents_processed
                )
            
            self.logger.info(f"Document loaded from S3 in {total_load_time:.3f}s: {document_url}")
            return content, performance_info
            
        except Exception as e:
            self.logger.error(f"Failed to load document {document_url}: {e}")
            raise
    
    async def _load_from_s3_with_retry(self, document_url: str) -> Tuple[bytes, Dict[str, Any]]:
        """Load document from S3 with retry logic"""
        
        last_exception = None
        
        for attempt in range(1, self.retry_config['max_attempts'] + 1):
            try:
                return await self._load_from_s3(document_url)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.retry_config['max_attempts']:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(f"S3 load attempt {attempt} failed, retrying in {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All S3 load attempts failed for {document_url}")
                    raise last_exception
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.retry_config['base_delay'] * (self.retry_config['backoff_multiplier'] ** (attempt - 1))
        return min(delay, self.retry_config['max_delay'])
    
    async def _load_from_s3(self, document_url: str) -> Tuple[bytes, Dict[str, Any]]:
        """Load document from S3 with chunked download for large files"""
        from urllib.parse import parse_qs, unquote
        
        # Parse S3 URL
        if not document_url.startswith('s3://'):
            raise ValueError(f"Invalid S3 URL format: {document_url}")
        
        s3_path = document_url[5:]  # Remove 's3://'
        
        # Handle version ID query parameter properly
        version_id = None
        if '?' in s3_path:
            path_part, query_string = s3_path.split('?', 1)
            query_params = parse_qs(query_string)
            if 'versionId' in query_params:
                version_id = unquote(query_params['versionId'][0])
            s3_path = path_part
        
        if '/' not in s3_path:
            raise ValueError(f"Invalid S3 URL format, missing key: {document_url}")
        
        bucket, key = s3_path.split('/', 1)
        
        # Get S3 client from pool
        s3_client = self.connection_pool.get_connection()
        
        try:
            start_time = time.time()
            used_version_id = version_id  # Track if we actually used versionId
            
            # Get object metadata first (include versionId if available)
            if BOTO3_AVAILABLE:
                head_params = {'Bucket': bucket, 'Key': key}
                if version_id:
                    head_params['VersionId'] = version_id
                
                try:
                    head_response = s3_client.head_object(**head_params)
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    # If 403/AccessDenied with versionId, retry without it
                    if version_id and error_code in ('403', 'AccessDenied', 'Forbidden'):
                        self.logger.warning(
                            f"s3:GetObjectVersion denied for {key}, falling back to latest version"
                        )
                        head_params = {'Bucket': bucket, 'Key': key}
                        head_response = s3_client.head_object(**head_params)
                        used_version_id = None  # Mark that we're not using versionId
                    else:
                        raise
                
                content_length = head_response.get('ContentLength', 0)
            else:
                # Mock response for testing
                content_length = 1024 * 1024  # 1MB mock size
                used_version_id = version_id
            
            content_length_mb = content_length / (1024 * 1024)
            
            # Choose download strategy based on file size
            if content_length_mb > self.chunk_size_mb:
                content, download_info = await self._download_large_file_chunked(s3_client, bucket, key, content_length, used_version_id)
            else:
                content, download_info = await self._download_small_file(s3_client, bucket, key, used_version_id)
            
            download_time = time.time() - start_time
            
            performance_info = {
                'download_time_seconds': download_time,
                'file_size_mb': content_length_mb,
                'download_strategy': download_info['strategy'],
                'chunks_downloaded': download_info.get('chunks', 1),
                'download_speed_mbps': content_length_mb / download_time if download_time > 0 else 0,
                'version_id_used': used_version_id is not None,
                'version_id_fallback': version_id is not None and used_version_id is None
            }
            
            return content, performance_info
            
        finally:
            # Release connection back to pool
            self.connection_pool.release_connection(s3_client)
    
    async def _download_large_file_chunked(self, s3_client, bucket: str, key: str, content_length: int, version_id: str = None) -> Tuple[bytes, Dict[str, Any]]:
        """Download large file in chunks to optimize memory usage"""
        
        chunks = []
        chunks_downloaded = 0
        
        for start in range(0, content_length, self.chunk_size_bytes):
            end = min(start + self.chunk_size_bytes - 1, content_length - 1)
            
            if BOTO3_AVAILABLE:
                get_params = {
                    'Bucket': bucket,
                    'Key': key,
                    'Range': f'bytes={start}-{end}'
                }
                if version_id:
                    get_params['VersionId'] = version_id
                response = s3_client.get_object(**get_params)
                chunk_data = response['Body'].read()
            else:
                # Mock chunk data for testing
                chunk_size = min(self.chunk_size_bytes, content_length - start)
                chunk_data = b'x' * chunk_size
            
            chunks.append(chunk_data)
            chunks_downloaded += 1
            
            # Small delay to prevent overwhelming S3
            if chunks_downloaded % 10 == 0:
                await asyncio.sleep(0.01)
        
        content = b''.join(chunks)
        
        return content, {
            'strategy': 'chunked',
            'chunks': chunks_downloaded,
            'chunk_size_mb': self.chunk_size_mb
        }
    
    async def _download_small_file(self, s3_client, bucket: str, key: str, version_id: str = None) -> Tuple[bytes, Dict[str, Any]]:
        """Download small file in single request"""
        
        if BOTO3_AVAILABLE:
            get_params = {'Bucket': bucket, 'Key': key}
            if version_id:
                get_params['VersionId'] = version_id
            response = s3_client.get_object(**get_params)
            content = response['Body'].read()
        else:
            # Mock content for testing
            content = b'Mock document content for testing'
        
        return content, {
            'strategy': 'single_request'
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        
        cache_stats = self.document_cache.get_cache_stats()
        pool_stats = self.connection_pool.get_pool_stats()
        
        total_requests = self.performance_metrics.cache_hits + self.performance_metrics.cache_misses
        cache_hit_rate = (self.performance_metrics.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_performance': {
                'hit_rate_percent': round(cache_hit_rate, 1),
                'total_hits': self.performance_metrics.cache_hits,
                'total_misses': self.performance_metrics.cache_misses,
                'cache_stats': cache_stats
            },
            'connection_pool': pool_stats,
            'download_performance': {
                'total_documents_processed': self.performance_metrics.total_documents_processed,
                'total_download_time_seconds': round(self.performance_metrics.total_download_time, 2),
                'average_download_speed_mbps': round(self.performance_metrics.average_download_speed_mbps, 2),
                'average_time_per_document': round(
                    self.performance_metrics.total_download_time / max(1, self.performance_metrics.total_documents_processed), 3
                )
            }
        }
    
    def clear_cache(self):
        """Clear document cache"""
        self.document_cache.clear()
    
    def optimize_for_production(self):
        """Apply production-specific optimizations"""
        
        # Increase connection pool for production load
        if self.connection_pool.max_connections < 20:
            self.connection_pool.max_connections = 20
            self.logger.info("Increased connection pool size for production")
        
        # Increase cache size for production
        if self.document_cache.max_size_mb < 200:
            self.document_cache.max_size_mb = 200.0
            self.logger.info("Increased cache size for production")
        
        # Optimize chunk size for production network
        if self.chunk_size_mb < 10:
            self.chunk_size_mb = 10.0
            self.chunk_size_bytes = int(self.chunk_size_mb * 1024 * 1024)
            self.logger.info("Increased chunk size for production network")


class MockS3Client:
    """Mock S3 client for testing without AWS dependencies"""
    
    def head_object(self, Bucket: str, Key: str):
        return {
            'ContentLength': 1024 * 1024,  # 1MB
            'LastModified': datetime.now(),
            'ContentType': 'application/pdf'
        }
    
    def get_object(self, Bucket: str, Key: str, Range: str = None):
        class MockBody:
            def read(self):
                if Range:
                    # Parse range for chunk size
                    range_parts = Range.replace('bytes=', '').split('-')
                    start = int(range_parts[0])
                    end = int(range_parts[1])
                    size = end - start + 1
                else:
                    size = 1024 * 1024  # 1MB
                
                return b'x' * size
        
        return {'Body': MockBody()}


# Factory function for easy instantiation
def create_optimized_s3_loader(
    region_name: str = None,
    max_connections: int = 10,
    cache_size_mb: float = 100.0,
    chunk_size_mb: float = 5.0,
    production_mode: bool = False
) -> PerformanceOptimizedS3Loader:
    """
    Create performance optimized S3 loader with appropriate settings
    
    Args:
        region_name: AWS region for S3 operations (defaults to environment variable)
        max_connections: Maximum S3 connections in pool
        cache_size_mb: Maximum cache size in MB
        chunk_size_mb: Chunk size for large file downloads
        production_mode: Apply production optimizations
    
    Returns:
        Configured PerformanceOptimizedS3Loader instance
    """
    
    loader = PerformanceOptimizedS3Loader(
        region_name=region_name or get_aws_region(),
        max_connections=max_connections,
        cache_size_mb=cache_size_mb,
        chunk_size_mb=chunk_size_mb
    )
    
    if production_mode:
        loader.optimize_for_production()
    
    return loader