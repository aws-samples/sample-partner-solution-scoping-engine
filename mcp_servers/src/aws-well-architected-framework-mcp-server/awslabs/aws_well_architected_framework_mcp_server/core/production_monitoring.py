"""
Production-ready logging and monitoring system for WAFR MCP Server.

This module provides comprehensive logging, metrics collection, and monitoring
capabilities for production deployment of the WAFR document access system.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from collections import defaultdict, deque
import threading
from enum import Enum


class LogLevel(Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """Event types for monitoring."""
    DOCUMENT_ACCESS_START = "document_access_start"
    DOCUMENT_ACCESS_SUCCESS = "document_access_success"
    DOCUMENT_ACCESS_FAILURE = "document_access_failure"
    S3_OPERATION = "s3_operation"
    CREDENTIAL_VALIDATION = "credential_validation"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_RECOVERY = "error_recovery"
    ASSESSMENT_WORKFLOW = "assessment_workflow"


@dataclass
class CorrelationContext:
    """Context information for correlation tracking."""
    correlation_id: str
    chat_id: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    operation: str
    start_time: datetime
    metadata: Dict[str, Any]


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    metric_name: str
    value: Union[int, float]
    unit: str
    timestamp: datetime
    correlation_id: str
    tags: Dict[str, str]


@dataclass
class ErrorEvent:
    """Error event data structure."""
    error_type: str
    error_message: str
    error_code: Optional[str]
    correlation_id: str
    operation: str
    timestamp: datetime
    stack_trace: Optional[str]
    recovery_action: Optional[str]
    user_impact: str


class StructuredLogger:
    """
    Structured logger with correlation ID tracking and production-ready formatting.
    """
    
    def __init__(self, name: str, log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Configure structured logging format - use stderr to avoid interfering with MCP JSON-RPC on stdout
        if not self.logger.handlers:
            import sys
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self._correlation_context = threading.local()
    
    def set_correlation_context(self, context: CorrelationContext) -> None:
        """Set correlation context for current thread."""
        self._correlation_context.context = context
    
    def get_correlation_context(self) -> Optional[CorrelationContext]:
        """Get correlation context for current thread."""
        return getattr(self._correlation_context, 'context', None)
    
    def _create_log_entry(self, level: LogLevel, message: str, **kwargs) -> Dict[str, Any]:
        """Create structured log entry."""
        
        context = self.get_correlation_context()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
            "logger": self.logger.name
        }
        
        # Add correlation information if available
        if context:
            log_entry.update({
                "correlation_id": context.correlation_id,
                "chat_id": context.chat_id,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "operation": context.operation,
                "operation_duration_ms": (datetime.utcnow() - context.start_time).total_seconds() * 1000
            })
            
            # Add context metadata
            if context.metadata:
                log_entry["context"] = context.metadata
        
        # Add additional fields
        log_entry.update(kwargs)
        
        return log_entry
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured format."""
        log_entry = self._create_log_entry(LogLevel.DEBUG, message, **kwargs)
        self.logger.debug(json.dumps(log_entry, default=str))
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured format."""
        log_entry = self._create_log_entry(LogLevel.INFO, message, **kwargs)
        self.logger.info(json.dumps(log_entry, default=str))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured format."""
        log_entry = self._create_log_entry(LogLevel.WARNING, message, **kwargs)
        self.logger.warning(json.dumps(log_entry, default=str))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured format."""
        log_entry = self._create_log_entry(LogLevel.ERROR, message, **kwargs)
        self.logger.error(json.dumps(log_entry, default=str))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with structured format."""
        log_entry = self._create_log_entry(LogLevel.CRITICAL, message, **kwargs)
        self.logger.critical(json.dumps(log_entry, default=str))
    
    def log_event(self, event_type: EventType, **kwargs) -> None:
        """Log structured event."""
        log_entry = self._create_log_entry(LogLevel.INFO, f"Event: {event_type.value}", **kwargs)
        log_entry["event_type"] = event_type.value
        self.logger.info(json.dumps(log_entry, default=str))
    
    def log_performance_metric(self, metric: PerformanceMetric) -> None:
        """Log performance metric."""
        log_entry = self._create_log_entry(
            LogLevel.INFO, 
            f"Performance Metric: {metric.metric_name}",
            metric_name=metric.metric_name,
            metric_value=metric.value,
            metric_unit=metric.unit,
            metric_tags=metric.tags
        )
        self.logger.info(json.dumps(log_entry, default=str))
    
    def log_error_event(self, error_event: ErrorEvent) -> None:
        """Log error event with full context."""
        log_entry = self._create_log_entry(
            LogLevel.ERROR,
            f"Error Event: {error_event.error_type}",
            error_type=error_event.error_type,
            error_message=error_event.error_message,
            error_code=error_event.error_code,
            operation=error_event.operation,
            recovery_action=error_event.recovery_action,
            user_impact=error_event.user_impact,
            stack_trace=error_event.stack_trace
        )
        self.logger.error(json.dumps(log_entry, default=str))


class MetricsCollector:
    """
    Collects and aggregates performance metrics for monitoring.
    """
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics = deque(maxlen=max_metrics)
        self.aggregated_metrics = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        with self._lock:
            self.metrics.append(metric)
            self.aggregated_metrics[metric.metric_name].append(metric)
    
    def record_duration(self, 
                       metric_name: str, 
                       duration_ms: float, 
                       correlation_id: str,
                       tags: Optional[Dict[str, str]] = None) -> None:
        """Record a duration metric."""
        metric = PerformanceMetric(
            metric_name=metric_name,
            value=duration_ms,
            unit="milliseconds",
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def record_counter(self, 
                      metric_name: str, 
                      count: int, 
                      correlation_id: str,
                      tags: Optional[Dict[str, str]] = None) -> None:
        """Record a counter metric."""
        metric = PerformanceMetric(
            metric_name=metric_name,
            value=count,
            unit="count",
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            tags=tags or {}
        )
        self.record_metric(metric)
    
    def get_metric_summary(self, metric_name: str, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric within a time window."""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        with self._lock:
            recent_metrics = [
                m for m in self.aggregated_metrics[metric_name]
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {
                "metric_name": metric_name,
                "time_window_minutes": time_window_minutes,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "p50": None,
                "p95": None,
                "p99": None
            }
        
        values = [m.value for m in recent_metrics]
        values.sort()
        
        count = len(values)
        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / count
        
        # Calculate percentiles
        p50_idx = int(count * 0.5)
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        
        return {
            "metric_name": metric_name,
            "time_window_minutes": time_window_minutes,
            "count": count,
            "min": min_val,
            "max": max_val,
            "avg": round(avg_val, 2),
            "p50": values[p50_idx] if p50_idx < count else max_val,
            "p95": values[p95_idx] if p95_idx < count else max_val,
            "p99": values[p99_idx] if p99_idx < count else max_val,
            "unit": recent_metrics[0].unit if recent_metrics else "unknown"
        }
    
    def get_all_metrics_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary for all metrics."""
        
        with self._lock:
            metric_names = list(self.aggregated_metrics.keys())
        
        summaries = {}
        for metric_name in metric_names:
            summaries[metric_name] = self.get_metric_summary(metric_name, time_window_minutes)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_window_minutes": time_window_minutes,
            "metrics": summaries
        }


class DocumentAccessMonitor:
    """
    Specialized monitor for document access operations.
    """
    
    def __init__(self, logger: StructuredLogger, metrics_collector: MetricsCollector):
        self.logger = logger
        self.metrics = metrics_collector
        self.active_operations = {}
        self._lock = threading.Lock()
    
    def start_document_access(self, 
                            correlation_id: str, 
                            document_url: str,
                            operation_type: str = "document_access") -> None:
        """Start monitoring a document access operation."""
        
        start_time = datetime.utcnow()
        
        with self._lock:
            self.active_operations[correlation_id] = {
                "document_url": document_url,
                "operation_type": operation_type,
                "start_time": start_time
            }
        
        self.logger.log_event(
            EventType.DOCUMENT_ACCESS_START,
            document_url=document_url,
            operation_type=operation_type
        )
        
        self.metrics.record_counter(
            "document_access_attempts",
            1,
            correlation_id,
            {"operation_type": operation_type}
        )
    
    def complete_document_access(self, 
                               correlation_id: str, 
                               success: bool,
                               error_type: Optional[str] = None,
                               bytes_processed: Optional[int] = None) -> None:
        """Complete monitoring a document access operation."""
        
        end_time = datetime.utcnow()
        
        with self._lock:
            operation_info = self.active_operations.pop(correlation_id, None)
        
        if not operation_info:
            self.logger.warning(f"No active operation found for correlation_id: {correlation_id}")
            return
        
        duration_ms = (end_time - operation_info["start_time"]).total_seconds() * 1000
        
        # Log completion event
        if success:
            self.logger.log_event(
                EventType.DOCUMENT_ACCESS_SUCCESS,
                document_url=operation_info["document_url"],
                operation_type=operation_info["operation_type"],
                duration_ms=duration_ms,
                bytes_processed=bytes_processed
            )
            
            # Record success metrics
            self.metrics.record_counter(
                "document_access_success",
                1,
                correlation_id,
                {"operation_type": operation_info["operation_type"]}
            )
            
            if bytes_processed:
                self.metrics.record_counter(
                    "document_bytes_processed",
                    bytes_processed,
                    correlation_id,
                    {"operation_type": operation_info["operation_type"]}
                )
        else:
            self.logger.log_event(
                EventType.DOCUMENT_ACCESS_FAILURE,
                document_url=operation_info["document_url"],
                operation_type=operation_info["operation_type"],
                duration_ms=duration_ms,
                error_type=error_type
            )
            
            # Record failure metrics
            self.metrics.record_counter(
                "document_access_failures",
                1,
                correlation_id,
                {
                    "operation_type": operation_info["operation_type"],
                    "error_type": error_type or "unknown"
                }
            )
        
        # Record duration metric
        self.metrics.record_duration(
            "document_access_duration",
            duration_ms,
            correlation_id,
            {
                "operation_type": operation_info["operation_type"],
                "success": str(success)
            }
        )
    
    def log_s3_operation(self, 
                        correlation_id: str,
                        operation: str,
                        bucket: str,
                        key: Optional[str] = None,
                        success: bool = True,
                        duration_ms: Optional[float] = None,
                        error_code: Optional[str] = None) -> None:
        """Log S3 operation details."""
        
        self.logger.log_event(
            EventType.S3_OPERATION,
            s3_operation=operation,
            s3_bucket=bucket,
            s3_key=key,
            success=success,
            duration_ms=duration_ms,
            error_code=error_code
        )
        
        # Record S3 operation metrics
        self.metrics.record_counter(
            f"s3_operations_{operation}",
            1,
            correlation_id,
            {
                "bucket": bucket,
                "success": str(success),
                "error_code": error_code or "none"
            }
        )
        
        if duration_ms:
            self.metrics.record_duration(
                f"s3_operation_duration_{operation}",
                duration_ms,
                correlation_id,
                {"bucket": bucket, "success": str(success)}
            )
    
    def get_operation_status(self) -> Dict[str, Any]:
        """Get status of active operations."""
        
        current_time = datetime.utcnow()
        
        with self._lock:
            active_ops = []
            for correlation_id, op_info in self.active_operations.items():
                duration_ms = (current_time - op_info["start_time"]).total_seconds() * 1000
                active_ops.append({
                    "correlation_id": correlation_id,
                    "document_url": op_info["document_url"],
                    "operation_type": op_info["operation_type"],
                    "duration_ms": duration_ms,
                    "start_time": op_info["start_time"].isoformat()
                })
        
        return {
            "timestamp": current_time.isoformat(),
            "active_operations_count": len(active_ops),
            "active_operations": active_ops
        }


class HealthCheckMonitor:
    """
    Health check monitor for system status.
    """
    
    def __init__(self, logger: StructuredLogger, metrics_collector: MetricsCollector):
        self.logger = logger
        self.metrics = metrics_collector
        self.health_checks = {}
        self._lock = threading.Lock()
    
    def register_health_check(self, name: str, check_function, interval_seconds: int = 60) -> None:
        """Register a health check function."""
        
        with self._lock:
            self.health_checks[name] = {
                "function": check_function,
                "interval_seconds": interval_seconds,
                "last_check": None,
                "last_result": None
            }
    
    def run_health_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        
        with self._lock:
            check_info = self.health_checks.get(name)
        
        if not check_info:
            return {
                "name": name,
                "status": "unknown",
                "error": "Health check not registered"
            }
        
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        try:
            result = check_info["function"]()
            duration_ms = (time.time() - start_time) * 1000
            
            health_result = {
                "name": name,
                "status": "healthy" if result.get("healthy", False) else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "duration_ms": duration_ms,
                "details": result
            }
            
            # Update stored result
            with self._lock:
                self.health_checks[name]["last_check"] = datetime.utcnow()
                self.health_checks[name]["last_result"] = health_result
            
            # Log health check result
            self.logger.info(
                f"Health check completed: {name}",
                health_check_name=name,
                health_status=health_result["status"],
                duration_ms=duration_ms
            )
            
            # Record metrics
            self.metrics.record_duration(
                "health_check_duration",
                duration_ms,
                correlation_id,
                {"check_name": name, "status": health_result["status"]}
            )
            
            return health_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            health_result = {
                "name": name,
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "duration_ms": duration_ms,
                "error": str(e)
            }
            
            # Update stored result
            with self._lock:
                self.health_checks[name]["last_check"] = datetime.utcnow()
                self.health_checks[name]["last_result"] = health_result
            
            # Log health check error
            self.logger.error(
                f"Health check failed: {name}",
                health_check_name=name,
                error=str(e),
                duration_ms=duration_ms
            )
            
            return health_result
    
    def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        
        results = {}
        overall_healthy = True
        
        with self._lock:
            check_names = list(self.health_checks.keys())
        
        for name in check_names:
            result = self.run_health_check(name)
            results[name] = result
            
            if result["status"] != "healthy":
                overall_healthy = False
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "checks": results
        }


@contextmanager
def correlation_context(logger: StructuredLogger, 
                       correlation_id: str,
                       operation: str,
                       chat_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       **metadata):
    """Context manager for correlation tracking."""
    
    context = CorrelationContext(
        correlation_id=correlation_id,
        chat_id=chat_id,
        user_id=user_id,
        session_id=None,
        operation=operation,
        start_time=datetime.utcnow(),
        metadata=metadata
    )
    
    logger.set_correlation_context(context)
    
    try:
        yield context
    finally:
        # Clear context
        logger.set_correlation_context(None)


# Global instances for production monitoring
production_logger = StructuredLogger("wafr-mcp-server", "INFO")
metrics_collector = MetricsCollector()
document_access_monitor = DocumentAccessMonitor(production_logger, metrics_collector)
health_check_monitor = HealthCheckMonitor(production_logger, metrics_collector)


def setup_production_monitoring() -> Dict[str, Any]:
    """Setup production monitoring with default health checks."""
    
    def s3_connectivity_check():
        """Check S3 connectivity."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client('s3')
            # Try to list buckets as a connectivity test
            s3_client.list_buckets()
            
            return {"healthy": True, "message": "S3 connectivity OK"}
        except Exception as e:
            return {"healthy": False, "message": f"S3 connectivity failed: {e}"}
    
    def aws_credentials_check():
        """Check AWS credentials validity."""
        try:
            import boto3
            
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            
            return {
                "healthy": True, 
                "message": "AWS credentials valid",
                "account": identity.get("Account"),
                "user_arn": identity.get("Arn")
            }
        except Exception as e:
            return {"healthy": False, "message": f"AWS credentials invalid: {e}"}
    
    def memory_usage_check():
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            return {
                "healthy": memory_percent < 90,
                "message": f"Memory usage: {memory_percent}%",
                "memory_percent": memory_percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
        except ImportError:
            return {"healthy": True, "message": "psutil not available for memory monitoring"}
        except Exception as e:
            return {"healthy": False, "message": f"Memory check failed: {e}"}
    
    # Register health checks
    health_check_monitor.register_health_check("s3_connectivity", s3_connectivity_check, 300)  # 5 minutes
    health_check_monitor.register_health_check("aws_credentials", aws_credentials_check, 600)  # 10 minutes
    health_check_monitor.register_health_check("memory_usage", memory_usage_check, 60)  # 1 minute
    
    production_logger.info("Production monitoring setup completed")
    
    return {
        "status": "initialized",
        "health_checks_registered": len(health_check_monitor.health_checks),
        "logger": "structured_logger_active",
        "metrics_collector": "active"
    }


def get_monitoring_status() -> Dict[str, Any]:
    """Get comprehensive monitoring status."""
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "logger_status": "active",
        "metrics_summary": metrics_collector.get_all_metrics_summary(60),
        "document_access_status": document_access_monitor.get_operation_status(),
        "health_checks": health_check_monitor.run_all_health_checks()
    }