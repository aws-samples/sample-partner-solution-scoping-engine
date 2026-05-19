"""
Performance Monitoring for Enhanced Scoring System

Tracks performance metrics for capability detection, scoring calculation,
pattern adjustments, and recommendation generation.

Requirements: 10.1, 10.2
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import json


@dataclass
class PerformanceMetric:
    """Performance metric for scoring operations"""
    operation: str
    pillar: Optional[str]
    duration_ms: float
    timestamp: datetime
    correlation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Aggregated performance statistics"""
    operation: str
    total_executions: int
    total_duration_ms: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    last_updated: datetime


class ScoringPerformanceMonitor:
    """
    Performance monitor for enhanced scoring operations.
    
    Tracks timing for:
    - Capability detection per pillar
    - Score calculation per pillar
    - Pattern adjustments
    - Recommendation generation
    - Total assessment time
    """
    
    def __init__(self, max_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.operation_stats: Dict[str, PerformanceStats] = {}
        self.active_operations: Dict[str, float] = {}
        
        # Performance targets (in milliseconds)
        self.performance_targets = {
            'capability_detection': 500,  # Per pillar
            'score_calculation': 100,     # Per pillar
            'pattern_adjustment': 200,    # All patterns
            'recommendation_generation': 3000,  # All recommendations
            'total_assessment': 5000      # Complete assessment
        }
    
    @contextmanager
    def track_operation(self,
                       operation: str,
                       pillar: Optional[str] = None,
                       correlation_id: Optional[str] = None,
                       **metadata):
        """Context manager for tracking operation performance"""
        operation_key = f"{operation}_{pillar}" if pillar else operation
        start_time = time.time()
        self.active_operations[operation_key] = start_time
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metric
            metric = PerformanceMetric(
                operation=operation,
                pillar=pillar,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id or "unknown",
                metadata=metadata
            )
            
            self.record_metric(metric)
            
            # Remove from active operations
            if operation_key in self.active_operations:
                del self.active_operations[operation_key]
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        self.metrics_history.append(metric)
        self._update_stats(metric)
        self._check_performance_target(metric)
        
        self.logger.debug(
            f"Performance: {metric.operation} "
            f"{'(' + metric.pillar + ')' if metric.pillar else ''} "
            f"took {metric.duration_ms:.2f}ms"
        )
    
    def _update_stats(self, metric: PerformanceMetric):
        """Update aggregated statistics for operation"""
        operation_key = f"{metric.operation}_{metric.pillar}" if metric.pillar else metric.operation
        
        if operation_key not in self.operation_stats:
            self.operation_stats[operation_key] = PerformanceStats(
                operation=operation_key,
                total_executions=0,
                total_duration_ms=0.0,
                avg_duration_ms=0.0,
                min_duration_ms=float('inf'),
                max_duration_ms=0.0,
                p50_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                last_updated=datetime.utcnow()
            )
        
        stats = self.operation_stats[operation_key]
        stats.total_executions += 1
        stats.total_duration_ms += metric.duration_ms
        stats.avg_duration_ms = stats.total_duration_ms / stats.total_executions
        stats.min_duration_ms = min(stats.min_duration_ms, metric.duration_ms)
        stats.max_duration_ms = max(stats.max_duration_ms, metric.duration_ms)
        stats.last_updated = datetime.utcnow()
        
        # Calculate percentiles from recent history
        self._calculate_percentiles(operation_key)
    
    def _calculate_percentiles(self, operation_key: str):
        """Calculate percentile metrics from recent history"""
        # Get recent metrics for this operation
        recent_metrics = [
            m for m in self.metrics_history
            if (f"{m.operation}_{m.pillar}" if m.pillar else m.operation) == operation_key
        ]
        
        if len(recent_metrics) < 10:
            return  # Need sufficient data for percentiles
        
        durations = sorted([m.duration_ms for m in recent_metrics])
        count = len(durations)
        
        stats = self.operation_stats[operation_key]
        stats.p50_duration_ms = durations[int(count * 0.50)]
        stats.p95_duration_ms = durations[int(count * 0.95)]
        stats.p99_duration_ms = durations[int(count * 0.99)]
    
    def _check_performance_target(self, metric: PerformanceMetric):
        """Check if metric meets performance target"""
        target = self.performance_targets.get(metric.operation)
        
        if target and metric.duration_ms > target:
            self.logger.warning(
                f"Performance target exceeded: {metric.operation} "
                f"{'(' + metric.pillar + ')' if metric.pillar else ''} "
                f"took {metric.duration_ms:.2f}ms (target: {target}ms)"
            )
    
    def get_operation_stats(self, operation: str, pillar: Optional[str] = None) -> Optional[PerformanceStats]:
        """Get performance statistics for an operation"""
        operation_key = f"{operation}_{pillar}" if pillar else operation
        return self.operation_stats.get(operation_key)
    
    def get_all_stats(self) -> Dict[str, PerformanceStats]:
        """Get all performance statistics"""
        return self.operation_stats.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.metrics_history:
            return {
                'total_operations': 0,
                'monitoring_active': True
            }
        
        # Overall statistics
        all_durations = [m.duration_ms for m in self.metrics_history]
        
        # Group by operation type
        by_operation = defaultdict(list)
        for metric in self.metrics_history:
            by_operation[metric.operation].append(metric.duration_ms)
        
        operation_summaries = {}
        for operation, durations in by_operation.items():
            target = self.performance_targets.get(operation, 0)
            avg_duration = sum(durations) / len(durations)
            
            operation_summaries[operation] = {
                'count': len(durations),
                'avg_duration_ms': round(avg_duration, 2),
                'min_duration_ms': round(min(durations), 2),
                'max_duration_ms': round(max(durations), 2),
                'target_ms': target,
                'meets_target': avg_duration <= target if target > 0 else True,
                'performance_ratio': round(target / avg_duration, 2) if avg_duration > 0 and target > 0 else 1.0
            }
        
        # Recent performance (last 100 operations)
        recent_metrics = list(self.metrics_history)[-100:]
        recent_avg = sum(m.duration_ms for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
        
        return {
            'total_operations': len(self.metrics_history),
            'overall_avg_duration_ms': round(sum(all_durations) / len(all_durations), 2),
            'recent_avg_duration_ms': round(recent_avg, 2),
            'by_operation': operation_summaries,
            'performance_targets': self.performance_targets,
            'active_operations': len(self.active_operations),
            'monitoring_active': True
        }
    
    def get_pillar_performance_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown by pillar"""
        pillar_metrics = defaultdict(lambda: defaultdict(list))
        
        for metric in self.metrics_history:
            if metric.pillar:
                pillar_metrics[metric.pillar][metric.operation].append(metric.duration_ms)
        
        breakdown = {}
        for pillar, operations in pillar_metrics.items():
            pillar_summary = {}
            for operation, durations in operations.items():
                pillar_summary[operation] = {
                    'count': len(durations),
                    'avg_duration_ms': round(sum(durations) / len(durations), 2),
                    'min_duration_ms': round(min(durations), 2),
                    'max_duration_ms': round(max(durations), 2)
                }
            breakdown[pillar] = pillar_summary
        
        return breakdown
    
    def log_performance_metrics(self):
        """Log current performance metrics"""
        summary = self.get_performance_summary()
        
        self.logger.info("=== Performance Metrics Summary ===")
        self.logger.info(f"Total operations tracked: {summary['total_operations']}")
        self.logger.info(f"Overall average duration: {summary['overall_avg_duration_ms']:.2f}ms")
        self.logger.info(f"Recent average duration: {summary['recent_avg_duration_ms']:.2f}ms")
        
        self.logger.info("\nBy Operation:")
        for operation, stats in summary['by_operation'].items():
            target_status = "✓" if stats['meets_target'] else "✗"
            self.logger.info(
                f"  {target_status} {operation}: {stats['avg_duration_ms']:.2f}ms "
                f"(target: {stats['target_ms']}ms, count: {stats['count']})"
            )
        
        if summary['active_operations'] > 0:
            self.logger.info(f"\nActive operations: {summary['active_operations']}")
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        metrics_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'summary': self.get_performance_summary(),
            'pillar_breakdown': self.get_pillar_performance_breakdown(),
            'detailed_stats': {
                key: {
                    'operation': stats.operation,
                    'total_executions': stats.total_executions,
                    'avg_duration_ms': stats.avg_duration_ms,
                    'min_duration_ms': stats.min_duration_ms,
                    'max_duration_ms': stats.max_duration_ms,
                    'p50_duration_ms': stats.p50_duration_ms,
                    'p95_duration_ms': stats.p95_duration_ms,
                    'p99_duration_ms': stats.p99_duration_ms,
                    'last_updated': stats.last_updated.isoformat()
                }
                for key, stats in self.operation_stats.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        self.logger.info(f"Performance metrics exported to {filepath}")
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        self.metrics_history.clear()
        self.operation_stats.clear()
        self.active_operations.clear()
        self.logger.info("Performance metrics reset")


# Global performance monitor instance
scoring_performance_monitor = ScoringPerformanceMonitor()
