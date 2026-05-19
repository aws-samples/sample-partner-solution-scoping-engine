"""
Performance Optimizer for WAFR Enterprise Scoring.

Implements parallel processing, caching, and optimization strategies to achieve:
- <500ms capability detection for small architectures (1-5 services)
- <2s capability detection for large architectures (16-30 services)
- <100ms score calculation per pillar
- <5s total assessment time

Follows MCP server patterns with comprehensive logging and error handling.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import threading

from ..core.logger import WAFRLogger
from ..models.capability import DetectedCapability, CapabilityMatrix
from ..models.scoring import PillarScore


class PerformanceOptimizer:
    """
    Performance optimization layer for WAFR scoring.
    
    Features:
    - Parallel capability detection across all pillars
    - LRU caching for capability definitions and mappings
    - Batch processing for multiple services
    - Performance monitoring and metrics
    """
    
    def __init__(self, max_workers: int = 6):
        """
        Initialize PerformanceOptimizer.
        
        Args:
            max_workers: Maximum number of parallel workers (default: 6 for 6 pillars)
        """
        self.logger = WAFRLogger(__name__)
        self.max_workers = max_workers
        
        # Thread-safe cache locks
        self._cache_lock = threading.Lock()
        
        # Performance metrics
        self._metrics = {
            'capability_detection_times': [],
            'score_calculation_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        self.logger.info(f"PerformanceOptimizer initialized with {max_workers} workers")
    
    def parallel_capability_detection(
        self,
        capability_mapper,
        detected_services: List[str],
        service_configurations: Dict[str, Any],
        pillars: Optional[List[str]] = None
    ) -> CapabilityMatrix:
        """
        Detect capabilities for all pillars in parallel.
        
        Uses ThreadPoolExecutor to parallelize capability detection across pillars,
        significantly reducing total detection time.
        
        Args:
            capability_mapper: CapabilityMapper instance
            detected_services: List of detected AWS services
            service_configurations: Service configuration data
            pillars: Optional list of pillars to process (defaults to all 6)
            
        Returns:
            CapabilityMatrix with all detected capabilities
        """
        start_time = time.time()
        
        if pillars is None:
            pillars = [
                'security',
                'reliability',
                'performance',
                'cost_optimization',
                'operational_excellence',
                'sustainability'
            ]
        
        self.logger.info(f"🚀 Starting parallel capability detection for {len(pillars)} pillars")
        
        # Initialize result matrix
        matrix = CapabilityMatrix(
            total_services_analyzed=len(detected_services),
            detection_timestamp=datetime.utcnow().isoformat()
        )
        
        # Parallel detection using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit detection tasks for each pillar
            future_to_pillar = {
                executor.submit(
                    self._detect_pillar_capabilities,
                    capability_mapper,
                    pillar,
                    detected_services,
                    service_configurations
                ): pillar
                for pillar in pillars
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pillar):
                pillar = future_to_pillar[future]
                try:
                    pillar_capabilities = future.result()
                    
                    # Add capabilities to matrix
                    for capability in pillar_capabilities:
                        self._add_capability_to_matrix(matrix, capability, pillar)
                    
                    self.logger.debug(f"✅ {pillar}: {len(pillar_capabilities)} capabilities detected")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error detecting capabilities for {pillar}: {e}")
        
        # Calculate overall confidence
        all_capabilities = matrix.get_all_capabilities()
        if all_capabilities:
            matrix.overall_confidence = sum(c.confidence for c in all_capabilities) / len(all_capabilities)
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        self._metrics['capability_detection_times'].append(elapsed_time)
        
        self.logger.info(
            f"✅ Parallel capability detection complete in {elapsed_time:.0f}ms: "
            f"{matrix.get_capability_count()} capabilities detected"
        )
        
        return matrix
    
    def _detect_pillar_capabilities(
        self,
        capability_mapper,
        pillar: str,
        detected_services: List[str],
        service_configurations: Dict[str, Any]
    ) -> List[DetectedCapability]:
        """
        Detect capabilities for a single pillar.
        
        This method is called in parallel for each pillar.
        
        Args:
            capability_mapper: CapabilityMapper instance
            pillar: Pillar name
            detected_services: List of detected services
            service_configurations: Service configuration data
            
        Returns:
            List of DetectedCapability objects for this pillar
        """
        capabilities = []
        
        # Get capability definitions for this pillar
        pillar_capability_defs = self._get_pillar_capability_definitions(
            capability_mapper,
            pillar
        )
        
        # Detect each capability
        for capability_name, capability_def in pillar_capability_defs.items():
            detected_capability = capability_mapper._detect_capability(
                capability_name,
                capability_def,
                detected_services,
                service_configurations
            )
            
            if detected_capability:
                capabilities.append(detected_capability)
        
        return capabilities
    
    def _get_pillar_capability_definitions(
        self,
        capability_mapper,
        pillar: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get capability definitions for a specific pillar.
        
        Filters capability definitions to only those belonging to the specified pillar.
        
        Args:
            capability_mapper: CapabilityMapper instance
            pillar: Pillar name
            
        Returns:
            Dictionary of capability definitions for this pillar
        """
        pillar_capabilities = {}
        
        for capability_name, capability_def in capability_mapper.capability_definitions.items():
            if capability_def.get('pillar') == pillar:
                pillar_capabilities[capability_name] = capability_def
        
        return pillar_capabilities
    
    def _add_capability_to_matrix(
        self,
        matrix: CapabilityMatrix,
        capability: DetectedCapability,
        pillar: str
    ):
        """
        Add a capability to the appropriate pillar in the matrix.
        
        Thread-safe operation for parallel capability detection.
        
        Args:
            matrix: CapabilityMatrix to update
            capability: DetectedCapability to add
            pillar: Pillar name
        """
        with self._cache_lock:
            if pillar == 'security':
                matrix.security_capabilities.append(capability)
            elif pillar == 'reliability':
                matrix.reliability_capabilities.append(capability)
            elif pillar == 'performance':
                matrix.performance_capabilities.append(capability)
            elif pillar == 'cost_optimization':
                matrix.cost_capabilities.append(capability)
            elif pillar == 'operational_excellence':
                matrix.operational_capabilities.append(capability)
            elif pillar == 'sustainability':
                matrix.sustainability_capabilities.append(capability)
    
    def parallel_score_calculation(
        self,
        capability_scorer,
        capability_matrix: CapabilityMatrix,
        architecture_complexity: int,
        pillars: Optional[List[str]] = None
    ) -> Dict[str, PillarScore]:
        """
        Calculate scores for all pillars in parallel.
        
        Uses ThreadPoolExecutor to parallelize score calculation across pillars.
        
        Args:
            capability_scorer: CapabilityScorer instance
            capability_matrix: CapabilityMatrix with detected capabilities
            architecture_complexity: Number of services
            pillars: Optional list of pillars to process (defaults to all 6)
            
        Returns:
            Dictionary mapping pillar names to PillarScore objects
        """
        start_time = time.time()
        
        if pillars is None:
            pillars = [
                'security',
                'reliability',
                'performance',
                'cost_optimization',
                'operational_excellence',
                'sustainability'
            ]
        
        self.logger.info(f"🚀 Starting parallel score calculation for {len(pillars)} pillars")
        
        scores = {}
        
        # Parallel scoring using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit scoring tasks for each pillar
            future_to_pillar = {
                executor.submit(
                    self._calculate_pillar_score,
                    capability_scorer,
                    pillar,
                    capability_matrix,
                    architecture_complexity
                ): pillar
                for pillar in pillars
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pillar):
                pillar = future_to_pillar[future]
                try:
                    pillar_score = future.result()
                    scores[pillar] = pillar_score
                    
                    self.logger.debug(f"✅ {pillar}: {pillar_score.final_score:.1f}%")
                    
                except Exception as e:
                    self.logger.error(f"❌ Error calculating score for {pillar}: {e}")
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        self._metrics['score_calculation_times'].append(elapsed_time)
        
        avg_score = sum(s.final_score for s in scores.values()) / len(scores) if scores else 0
        
        self.logger.info(
            f"✅ Parallel score calculation complete in {elapsed_time:.0f}ms: "
            f"Average score {avg_score:.1f}%"
        )
        
        return scores
    
    def _calculate_pillar_score(
        self,
        capability_scorer,
        pillar: str,
        capability_matrix: CapabilityMatrix,
        architecture_complexity: int
    ) -> PillarScore:
        """
        Calculate score for a single pillar.
        
        This method is called in parallel for each pillar.
        
        Args:
            capability_scorer: CapabilityScorer instance
            pillar: Pillar name
            capability_matrix: CapabilityMatrix with capabilities
            architecture_complexity: Number of services
            
        Returns:
            PillarScore for this pillar
        """
        capabilities = capability_matrix.get_capabilities_for_pillar(pillar)
        return capability_scorer.calculate_pillar_score(
            pillar,
            capabilities,
            architecture_complexity
        )
    
    def batch_service_analysis(
        self,
        services: List[str],
        batch_size: int = 10
    ) -> List[List[str]]:
        """
        Split services into batches for parallel processing.
        
        Args:
            services: List of services to batch
            batch_size: Size of each batch
            
        Returns:
            List of service batches
        """
        batches = []
        for i in range(0, len(services), batch_size):
            batch = services[i:i + batch_size]
            batches.append(batch)
        
        self.logger.debug(f"Split {len(services)} services into {len(batches)} batches")
        return batches
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for monitoring.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = {
            'capability_detection': {
                'count': len(self._metrics['capability_detection_times']),
                'avg_ms': sum(self._metrics['capability_detection_times']) / len(self._metrics['capability_detection_times']) if self._metrics['capability_detection_times'] else 0,
                'min_ms': min(self._metrics['capability_detection_times']) if self._metrics['capability_detection_times'] else 0,
                'max_ms': max(self._metrics['capability_detection_times']) if self._metrics['capability_detection_times'] else 0
            },
            'score_calculation': {
                'count': len(self._metrics['score_calculation_times']),
                'avg_ms': sum(self._metrics['score_calculation_times']) / len(self._metrics['score_calculation_times']) if self._metrics['score_calculation_times'] else 0,
                'min_ms': min(self._metrics['score_calculation_times']) if self._metrics['score_calculation_times'] else 0,
                'max_ms': max(self._metrics['score_calculation_times']) if self._metrics['score_calculation_times'] else 0
            },
            'cache': {
                'hits': self._metrics['cache_hits'],
                'misses': self._metrics['cache_misses'],
                'hit_rate': self._metrics['cache_hits'] / (self._metrics['cache_hits'] + self._metrics['cache_misses']) if (self._metrics['cache_hits'] + self._metrics['cache_misses']) > 0 else 0
            }
        }
        
        return metrics
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self._metrics = {
            'capability_detection_times': [],
            'score_calculation_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.logger.info("Performance metrics reset")


class CachedCapabilityMapper:
    """
    Wrapper around CapabilityMapper with caching support.
    
    Implements LRU caching for:
    - Capability definitions
    - Service-to-capability mappings
    - Pattern definitions
    """
    
    def __init__(self, capability_mapper, cache_size: int = 128):
        """
        Initialize CachedCapabilityMapper.
        
        Args:
            capability_mapper: CapabilityMapper instance to wrap
            cache_size: Maximum cache size for LRU cache
        """
        self.mapper = capability_mapper
        self.logger = WAFRLogger(__name__)
        self.cache_size = cache_size
        
        # Initialize caches
        self._capability_def_cache = {}
        self._service_mapping_cache = {}
        
        self.logger.info(f"CachedCapabilityMapper initialized with cache size {cache_size}")
    
    @lru_cache(maxsize=128)
    def get_capability_definition(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """
        Get capability definition with caching.
        
        Args:
            capability_name: Name of the capability
            
        Returns:
            Capability definition dictionary
        """
        return self.mapper.capability_definitions.get(capability_name)
    
    @lru_cache(maxsize=256)
    def get_service_capabilities(self, service_name: str) -> List[str]:
        """
        Get list of capabilities a service can provide (cached).
        
        Args:
            service_name: AWS service name
            
        Returns:
            List of capability names this service can provide
        """
        capabilities = []
        
        for capability_name, capability_def in self.mapper.capability_definitions.items():
            services = capability_def.get('services', {})
            if service_name in services:
                capabilities.append(capability_name)
        
        return capabilities
    
    def invalidate_cache(self):
        """
        Invalidate all caches.
        
        Call this after configuration reload.
        """
        self.get_capability_definition.cache_clear()
        self.get_service_capabilities.cache_clear()
        self._capability_def_cache.clear()
        self._service_mapping_cache.clear()
        
        self.logger.info("All caches invalidated")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'capability_definition_cache': self.get_capability_definition.cache_info()._asdict(),
            'service_capabilities_cache': self.get_service_capabilities.cache_info()._asdict()
        }


class OptimizedScoringEngine:
    """
    Optimized scoring engine that combines parallel processing and caching.
    
    Provides a high-level interface for optimized capability detection and scoring.
    """
    
    def __init__(
        self,
        capability_mapper,
        capability_scorer,
        pattern_adjuster=None,
        max_workers: int = 6
    ):
        """
        Initialize OptimizedScoringEngine.
        
        Args:
            capability_mapper: CapabilityMapper instance
            capability_scorer: CapabilityScorer instance
            pattern_adjuster: Optional PatternAdjuster instance
            max_workers: Maximum number of parallel workers
        """
        self.logger = WAFRLogger(__name__)
        
        # Wrap mapper with caching
        self.cached_mapper = CachedCapabilityMapper(capability_mapper)
        self.scorer = capability_scorer
        self.pattern_adjuster = pattern_adjuster
        
        # Initialize performance optimizer
        self.optimizer = PerformanceOptimizer(max_workers=max_workers)
        
        self.logger.info("OptimizedScoringEngine initialized")
    
    def calculate_optimized_scores(
        self,
        detected_services: List[str],
        service_configurations: Dict[str, Any],
        detected_patterns: Optional[List[Any]] = None
    ) -> Tuple[Dict[str, PillarScore], CapabilityMatrix, Dict[str, Any]]:
        """
        Calculate scores with full optimization (parallel + caching).
        
        Args:
            detected_services: List of detected AWS services
            service_configurations: Service configuration data
            detected_patterns: Optional list of detected architecture patterns
            
        Returns:
            Tuple of (pillar_scores, capability_matrix, performance_metrics)
        """
        total_start_time = time.time()
        
        self.logger.info(f"🚀 Starting optimized scoring for {len(detected_services)} services")
        
        # Step 1: Parallel capability detection
        capability_matrix = self.optimizer.parallel_capability_detection(
            self.cached_mapper.mapper,
            detected_services,
            service_configurations
        )
        
        # Step 2: Parallel score calculation
        pillar_scores = self.optimizer.parallel_score_calculation(
            self.scorer,
            capability_matrix,
            len(detected_services)
        )
        
        # Step 3: Apply pattern adjustments (if available)
        if self.pattern_adjuster and detected_patterns:
            pillar_scores = self.pattern_adjuster.apply_pattern_adjustments(
                pillar_scores,
                detected_patterns
            )
        
        total_elapsed = (time.time() - total_start_time) * 1000  # Convert to ms
        
        # Get performance metrics
        metrics = self.optimizer.get_performance_metrics()
        metrics['total_assessment_time_ms'] = total_elapsed
        metrics['cache_info'] = self.cached_mapper.get_cache_info()
        
        self.logger.info(
            f"✅ Optimized scoring complete in {total_elapsed:.0f}ms "
            f"(target: <5000ms)"
        )
        
        return pillar_scores, capability_matrix, metrics
    
    def reload_configuration(self):
        """
        Reload configuration and invalidate caches.
        """
        self.logger.info("Reloading configuration")
        
        # Reload scorer configuration
        self.scorer.reload_configuration()
        
        # Reload mapper configuration
        self.cached_mapper.mapper.capability_definitions = \
            self.cached_mapper.mapper._load_capability_definitions()
        
        # Invalidate caches
        self.cached_mapper.invalidate_cache()
        
        self.logger.info("Configuration reloaded and caches invalidated")
