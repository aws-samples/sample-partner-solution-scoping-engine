"""
Performance Optimization and Monitoring for Enhanced WAFR
Implements stage-specific performance monitoring, caching, and optimization
Requirements: 9.4, 9.5
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    operation: str
    duration_ms: float
    timestamp: datetime
    stage: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StagePerformanceStats:
    """Performance statistics for a conversation stage"""
    stage_name: str
    total_executions: int
    average_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p95_duration_ms: float
    success_rate: float
    last_updated: datetime


class PerformanceMonitor:
    """Stage-specific performance monitoring and optimization"""
    
    def __init__(self, max_metrics_history: int = 1000):
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.stage_stats: Dict[str, StagePerformanceStats] = {}
        self.operation_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.performance_targets = self._initialize_performance_targets()
        
        # Optimization settings
        self.cache_enabled = True
        self.cache_default_ttl = timedelta(minutes=5)
        self.monitoring_enabled = True
        
        logger.info("🚀 Performance monitor initialized")
    
    def _initialize_performance_targets(self) -> Dict[str, float]:
        """Initialize performance targets for each stage (in milliseconds)"""
        return {
            'solution_proposed': 5000,      # Document upload and validation
            'initial_analysis': 8000,       # Service detection and analysis
            'pattern_recognition': 3000,    # Architecture pattern identification
            'question_selection': 2000,     # Contextual question filtering
            'assessment_execution': 10000,  # Assessment logic execution
            'scoring_calculation': 2000,    # Score calculation with weights
            'benchmark_comparison': 1500,   # Industry benchmark comparison
            'recommendation_generation': 3000,  # Recommendation generation
            'solution_finalized': 15000,    # Final report generation
            
            # Operation-specific targets
            'document_analysis': 5000,
            'question_retrieval': 2000,
            'docx_generation': 10000,
            'api_call': 1000
        }
    
    async def monitor_operation(self, operation: str, stage: Optional[str] = None, 
                              correlation_id: Optional[str] = None):
        """Context manager for monitoring operation performance"""
        return PerformanceContext(self, operation, stage, correlation_id)
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        if not self.monitoring_enabled:
            return
        
        self.metrics_history.append(metric)
        
        # Update stage statistics
        if metric.stage:
            self._update_stage_stats(metric)
        
        # Check performance against targets
        self._check_performance_target(metric)
        
        logger.debug(f"📊 Recorded metric: {metric.operation} - {metric.duration_ms:.2f}ms")
    
    def _update_stage_stats(self, metric: PerformanceMetric):
        """Update performance statistics for a stage"""
        stage = metric.stage
        
        if stage not in self.stage_stats:
            self.stage_stats[stage] = StagePerformanceStats(
                stage_name=stage,
                total_executions=0,
                average_duration_ms=0.0,
                min_duration_ms=float('inf'),
                max_duration_ms=0.0,
                p95_duration_ms=0.0,
                success_rate=100.0,
                last_updated=datetime.now()
            )
        
        stats = self.stage_stats[stage]
        
        # Update basic stats
        stats.total_executions += 1
        stats.min_duration_ms = min(stats.min_duration_ms, metric.duration_ms)
        stats.max_duration_ms = max(stats.max_duration_ms, metric.duration_ms)
        
        # Calculate running average
        old_avg = stats.average_duration_ms
        stats.average_duration_ms = (old_avg * (stats.total_executions - 1) + metric.duration_ms) / stats.total_executions
        
        # Calculate P95 (simplified - would need more sophisticated calculation for accuracy)
        stage_metrics = [m for m in self.metrics_history if m.stage == stage]
        if len(stage_metrics) >= 20:  # Need sufficient data for P95
            durations = sorted([m.duration_ms for m in stage_metrics])
            p95_index = int(0.95 * len(durations))
            stats.p95_duration_ms = durations[p95_index]
        
        stats.last_updated = datetime.now()
    
    def _check_performance_target(self, metric: PerformanceMetric):
        """Check if metric meets performance targets"""
        target_key = metric.stage or metric.operation
        target = self.performance_targets.get(target_key)
        
        if target and metric.duration_ms > target:
            logger.warning(f"⚠️ Performance target exceeded: {metric.operation} took {metric.duration_ms:.2f}ms (target: {target}ms)")
    
    def get_stage_performance(self, stage: str) -> Optional[StagePerformanceStats]:
        """Get performance statistics for a specific stage"""
        return self.stage_stats.get(stage)
    
    def get_overall_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        total_metrics = len(self.metrics_history)
        
        if total_metrics == 0:
            return {
                'total_operations': 0,
                'monitoring_enabled': self.monitoring_enabled,
                'cache_enabled': self.cache_enabled
            }
        
        # Calculate overall statistics
        all_durations = [m.duration_ms for m in self.metrics_history]
        avg_duration = sum(all_durations) / len(all_durations)
        
        # Performance by stage
        stage_performance = {}
        for stage, stats in self.stage_stats.items():
            target = self.performance_targets.get(stage, 0)
            performance_ratio = (target / stats.average_duration_ms) if stats.average_duration_ms > 0 else 1.0
            
            stage_performance[stage] = {
                'executions': stats.total_executions,
                'avg_duration_ms': stats.average_duration_ms,
                'target_ms': target,
                'performance_ratio': performance_ratio,
                'meets_target': stats.average_duration_ms <= target if target > 0 else True
            }
        
        # Recent performance trend (last 100 operations)
        recent_metrics = list(self.metrics_history)[-100:]
        recent_avg = sum(m.duration_ms for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
        
        return {
            'total_operations': total_metrics,
            'overall_avg_duration_ms': avg_duration,
            'recent_avg_duration_ms': recent_avg,
            'stage_performance': stage_performance,
            'monitoring_enabled': self.monitoring_enabled,
            'cache_enabled': self.cache_enabled,
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'performance_targets_met': sum(1 for s in stage_performance.values() if s['meets_target']),
            'total_stages_monitored': len(stage_performance)
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from recent operations"""
        # Simplified cache hit rate calculation
        # In a real implementation, this would track actual cache hits/misses
        cache_operations = [m for m in self.metrics_history if 'cache' in m.metadata]
        if not cache_operations:
            return 0.0
        
        hits = sum(1 for m in cache_operations if m.metadata.get('cache_hit', False))
        return (hits / len(cache_operations)) * 100
    
    # Caching functionality
    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache with TTL check"""
        if not self.cache_enabled:
            return None
        
        if key not in self.operation_cache:
            return None
        
        # Check TTL
        if key in self.cache_ttl and datetime.now() > self.cache_ttl[key]:
            del self.operation_cache[key]
            del self.cache_ttl[key]
            return None
        
        return self.operation_cache[key]
    
    def cache_set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """Set value in cache with TTL"""
        if not self.cache_enabled:
            return
        
        self.operation_cache[key] = value
        
        if ttl is None:
            ttl = self.cache_default_ttl
        
        self.cache_ttl[key] = datetime.now() + ttl
    
    def cache_clear(self):
        """Clear all cached data"""
        self.operation_cache.clear()
        self.cache_ttl.clear()
        logger.info("🗑️ Performance cache cleared")
    
    def optimize_for_large_architectures(self, service_count: int) -> Dict[str, Any]:
        """Apply optimizations for large architectures"""
        optimizations = {}
        
        if service_count > 50:
            # Very large architecture - aggressive optimizations
            optimizations['cache_ttl_multiplier'] = 2.0
            optimizations['batch_processing'] = True
            optimizations['parallel_analysis'] = True
            optimizations['memory_optimization'] = 'aggressive'
            
            # Increase cache TTL for large architectures
            self.cache_default_ttl = timedelta(minutes=10)
            
        elif service_count > 20:
            # Large architecture - moderate optimizations
            optimizations['cache_ttl_multiplier'] = 1.5
            optimizations['batch_processing'] = True
            optimizations['parallel_analysis'] = False
            optimizations['memory_optimization'] = 'moderate'
            
            self.cache_default_ttl = timedelta(minutes=7)
            
        else:
            # Standard architecture - default settings
            optimizations['cache_ttl_multiplier'] = 1.0
            optimizations['batch_processing'] = False
            optimizations['parallel_analysis'] = False
            optimizations['memory_optimization'] = 'standard'
        
        logger.info(f"🔧 Applied optimizations for {service_count} services: {optimizations}")
        return optimizations
    
    def get_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze stage performance
        for stage, stats in self.stage_stats.items():
            target = self.performance_targets.get(stage, 0)
            
            if target > 0 and stats.average_duration_ms > target * 1.2:  # 20% over target
                recommendations.append(
                    f"Optimize {stage} stage: averaging {stats.average_duration_ms:.0f}ms "
                    f"(target: {target}ms)"
                )
        
        # Cache recommendations
        if not self.cache_enabled:
            recommendations.append("Enable caching to improve performance")
        
        # Memory optimization
        if len(self.metrics_history) > 800:
            recommendations.append("Consider reducing metrics history size for memory optimization")
        
        return recommendations


class PerformanceContext:
    """Context manager for performance monitoring"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, 
                 stage: Optional[str] = None, correlation_id: Optional[str] = None):
        self.monitor = monitor
        self.operation = operation
        self.stage = stage
        self.correlation_id = correlation_id
        self.start_time = None
        self.metadata = {}
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            
            # Add error information if exception occurred
            if exc_type is not None:
                self.metadata['error'] = True
                self.metadata['error_type'] = exc_type.__name__
            
            metric = PerformanceMetric(
                operation=self.operation,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                stage=self.stage,
                correlation_id=self.correlation_id,
                metadata=self.metadata
            )
            
            self.monitor.record_metric(metric)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the performance metric"""
        self.metadata[key] = value


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Convenience functions
async def monitor_stage_performance(stage: str, operation: str, correlation_id: Optional[str] = None):
    """Convenience function for monitoring stage performance"""
    return await performance_monitor.monitor_operation(operation, stage, correlation_id)


def get_performance_summary() -> Dict[str, Any]:
    """Get overall performance summary"""
    return performance_monitor.get_overall_performance_summary()


def optimize_for_architecture_size(service_count: int) -> Dict[str, Any]:
    """Apply performance optimizations based on architecture size"""
    return performance_monitor.optimize_for_large_architectures(service_count)


def cache_operation_result(key: str, value: Any, ttl_minutes: int = 5):
    """Cache operation result with TTL"""
    performance_monitor.cache_set(key, value, timedelta(minutes=ttl_minutes))


def get_cached_result(key: str) -> Optional[Any]:
    """Get cached operation result"""
    return performance_monitor.cache_get(key)