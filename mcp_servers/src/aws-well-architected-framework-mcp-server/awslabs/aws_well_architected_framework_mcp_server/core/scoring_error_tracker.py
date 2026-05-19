"""
Error Tracking for Enhanced Scoring System

Tracks and monitors errors in capability detection, scoring calculation,
configuration loading, and recommendation generation.

Requirements: 9.1, 9.2, 9.5
"""

import logging
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for tracking"""
    CAPABILITY_DETECTION = "capability_detection"
    SCORE_CALCULATION = "score_calculation"
    PATTERN_ADJUSTMENT = "pattern_adjustment"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    CONFIGURATION_LOADING = "configuration_loading"
    DATA_VALIDATION = "data_validation"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


@dataclass
class ErrorEvent:
    """Error event data structure"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    pillar: Optional[str]
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    correlation_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_action: Optional[str] = None


@dataclass
class ErrorStats:
    """Aggregated error statistics"""
    category: str
    total_errors: int
    errors_by_severity: Dict[str, int]
    errors_by_type: Dict[str, int]
    last_error_time: datetime
    error_rate_per_hour: float
    recovery_success_rate: float


class ScoringErrorTracker:
    """
    Error tracker for enhanced scoring operations.
    
    Tracks errors in:
    - Capability detection failures
    - Scoring calculation errors
    - Configuration loading errors
    - Pattern adjustment failures
    - Recommendation generation errors
    """
    
    def __init__(self, max_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        self.error_history: deque = deque(maxlen=max_history)
        self.error_stats: Dict[str, ErrorStats] = {}
        self.error_count_by_category: Dict[ErrorCategory, int] = defaultdict(int)
        self.error_count_by_severity: Dict[ErrorSeverity, int] = defaultdict(int)
        
        # Error rate thresholds (errors per hour)
        self.error_rate_thresholds = {
            ErrorSeverity.LOW: 10,
            ErrorSeverity.MEDIUM: 5,
            ErrorSeverity.HIGH: 2,
            ErrorSeverity.CRITICAL: 1
        }
    
    def track_error(self,
                   category: ErrorCategory,
                   severity: ErrorSeverity,
                   operation: str,
                   error: Exception,
                   pillar: Optional[str] = None,
                   correlation_id: Optional[str] = None,
                   **context) -> ErrorEvent:
        """Track an error event"""
        error_id = f"{category.value}_{datetime.utcnow().timestamp()}"
        
        error_event = ErrorEvent(
            error_id=error_id,
            timestamp=datetime.utcnow(),
            category=category,
            severity=severity,
            operation=operation,
            pillar=pillar,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            correlation_id=correlation_id or "unknown",
            context=context
        )
        
        self.error_history.append(error_event)
        self.error_count_by_category[category] += 1
        self.error_count_by_severity[severity] += 1
        
        self._update_error_stats(error_event)
        self._check_error_rate_threshold(category, severity)
        
        # Log error
        log_level = self._get_log_level(severity)
        self.logger.log(
            log_level,
            f"Error tracked: {category.value} - {operation} - {error_event.error_message}",
            extra={
                'error_id': error_id,
                'category': category.value,
                'severity': severity.value,
                'pillar': pillar,
                'correlation_id': correlation_id
            }
        )
        
        return error_event
    
    def track_capability_detection_error(self,
                                        pillar: str,
                                        error: Exception,
                                        correlation_id: Optional[str] = None,
                                        **context):
        """Track capability detection error"""
        severity = self._determine_severity(error, ErrorCategory.CAPABILITY_DETECTION)
        return self.track_error(
            category=ErrorCategory.CAPABILITY_DETECTION,
            severity=severity,
            operation="capability_detection",
            error=error,
            pillar=pillar,
            correlation_id=correlation_id,
            **context
        )
    
    def track_score_calculation_error(self,
                                     pillar: str,
                                     error: Exception,
                                     correlation_id: Optional[str] = None,
                                     **context):
        """Track score calculation error"""
        severity = self._determine_severity(error, ErrorCategory.SCORE_CALCULATION)
        return self.track_error(
            category=ErrorCategory.SCORE_CALCULATION,
            severity=severity,
            operation="score_calculation",
            error=error,
            pillar=pillar,
            correlation_id=correlation_id,
            **context
        )
    
    def track_configuration_loading_error(self,
                                         config_file: str,
                                         error: Exception,
                                         correlation_id: Optional[str] = None,
                                         **context):
        """Track configuration loading error"""
        return self.track_error(
            category=ErrorCategory.CONFIGURATION_LOADING,
            severity=ErrorSeverity.CRITICAL,  # Config errors are always critical
            operation="configuration_loading",
            error=error,
            pillar=None,
            correlation_id=correlation_id,
            config_file=config_file,
            **context
        )
    
    def track_pattern_adjustment_error(self,
                                      pattern_type: str,
                                      error: Exception,
                                      correlation_id: Optional[str] = None,
                                      **context):
        """Track pattern adjustment error"""
        severity = self._determine_severity(error, ErrorCategory.PATTERN_ADJUSTMENT)
        return self.track_error(
            category=ErrorCategory.PATTERN_ADJUSTMENT,
            severity=severity,
            operation="pattern_adjustment",
            error=error,
            pillar=None,
            correlation_id=correlation_id,
            pattern_type=pattern_type,
            **context
        )
    
    def track_recommendation_generation_error(self,
                                             pillar: Optional[str],
                                             error: Exception,
                                             correlation_id: Optional[str] = None,
                                             **context):
        """Track recommendation generation error"""
        severity = self._determine_severity(error, ErrorCategory.RECOMMENDATION_GENERATION)
        return self.track_error(
            category=ErrorCategory.RECOMMENDATION_GENERATION,
            severity=severity,
            operation="recommendation_generation",
            error=error,
            pillar=pillar,
            correlation_id=correlation_id,
            **context
        )
    
    def mark_recovery_attempted(self,
                               error_id: str,
                               recovery_action: str,
                               success: bool):
        """Mark that recovery was attempted for an error"""
        for error_event in self.error_history:
            if error_event.error_id == error_id:
                error_event.recovery_attempted = True
                error_event.recovery_successful = success
                error_event.recovery_action = recovery_action
                
                self.logger.info(
                    f"Recovery {'successful' if success else 'failed'} for error {error_id}: {recovery_action}"
                )
                break
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on error type and category"""
        error_type = type(error).__name__
        
        # Critical errors
        if error_type in ['SystemError', 'MemoryError', 'RuntimeError']:
            return ErrorSeverity.CRITICAL
        
        # Configuration errors are always critical
        if category == ErrorCategory.CONFIGURATION_LOADING:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if error_type in ['ValueError', 'TypeError', 'KeyError']:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if error_type in ['AttributeError', 'IndexError']:
            return ErrorSeverity.MEDIUM
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Get logging level for error severity"""
        severity_to_log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return severity_to_log_level.get(severity, logging.ERROR)
    
    def _update_error_stats(self, error_event: ErrorEvent):
        """Update aggregated error statistics"""
        category_key = error_event.category.value
        
        if category_key not in self.error_stats:
            self.error_stats[category_key] = ErrorStats(
                category=category_key,
                total_errors=0,
                errors_by_severity={},
                errors_by_type={},
                last_error_time=error_event.timestamp,
                error_rate_per_hour=0.0,
                recovery_success_rate=0.0
            )
        
        stats = self.error_stats[category_key]
        stats.total_errors += 1
        stats.last_error_time = error_event.timestamp
        
        # Update severity counts
        severity_key = error_event.severity.value
        stats.errors_by_severity[severity_key] = stats.errors_by_severity.get(severity_key, 0) + 1
        
        # Update type counts
        stats.errors_by_type[error_event.error_type] = stats.errors_by_type.get(error_event.error_type, 0) + 1
        
        # Calculate error rate (errors per hour)
        self._calculate_error_rate(category_key)
        
        # Calculate recovery success rate
        self._calculate_recovery_rate(category_key)
    
    def _calculate_error_rate(self, category_key: str):
        """Calculate error rate per hour for a category"""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_errors = [
            e for e in self.error_history
            if e.category.value == category_key and e.timestamp >= one_hour_ago
        ]
        
        self.error_stats[category_key].error_rate_per_hour = len(recent_errors)
    
    def _calculate_recovery_rate(self, category_key: str):
        """Calculate recovery success rate for a category"""
        category_errors = [e for e in self.error_history if e.category.value == category_key]
        
        if not category_errors:
            return
        
        recovery_attempted = [e for e in category_errors if e.recovery_attempted]
        
        if not recovery_attempted:
            self.error_stats[category_key].recovery_success_rate = 0.0
            return
        
        successful_recoveries = [e for e in recovery_attempted if e.recovery_successful]
        self.error_stats[category_key].recovery_success_rate = len(successful_recoveries) / len(recovery_attempted)
    
    def _check_error_rate_threshold(self, category: ErrorCategory, severity: ErrorSeverity):
        """Check if error rate exceeds threshold"""
        threshold = self.error_rate_thresholds.get(severity, 10)
        
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_errors = [
            e for e in self.error_history
            if e.category == category and e.severity == severity and e.timestamp >= one_hour_ago
        ]
        
        if len(recent_errors) >= threshold:
            self.logger.critical(
                f"Error rate threshold exceeded: {category.value} - {severity.value} "
                f"({len(recent_errors)} errors in last hour, threshold: {threshold})"
            )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary"""
        if not self.error_history:
            return {
                'total_errors': 0,
                'tracking_active': True
            }
        
        # Overall statistics
        total_errors = len(self.error_history)
        
        # Errors by category
        by_category = {}
        for category, count in self.error_count_by_category.items():
            by_category[category.value] = count
        
        # Errors by severity
        by_severity = {}
        for severity, count in self.error_count_by_severity.items():
            by_severity[severity.value] = count
        
        # Recent errors (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_errors = [e for e in self.error_history if e.timestamp >= one_hour_ago]
        
        # Recovery statistics
        recovery_attempted = [e for e in self.error_history if e.recovery_attempted]
        successful_recoveries = [e for e in recovery_attempted if e.recovery_successful]
        
        return {
            'total_errors': total_errors,
            'recent_errors_last_hour': len(recent_errors),
            'by_category': by_category,
            'by_severity': by_severity,
            'recovery_attempted': len(recovery_attempted),
            'recovery_successful': len(successful_recoveries),
            'recovery_success_rate': len(successful_recoveries) / len(recovery_attempted) if recovery_attempted else 0.0,
            'category_stats': {
                key: {
                    'total_errors': stats.total_errors,
                    'errors_by_severity': stats.errors_by_severity,
                    'error_rate_per_hour': stats.error_rate_per_hour,
                    'recovery_success_rate': stats.recovery_success_rate,
                    'last_error': stats.last_error_time.isoformat()
                }
                for key, stats in self.error_stats.items()
            },
            'tracking_active': True
        }
    
    def get_recent_errors(self, limit: int = 10, category: Optional[ErrorCategory] = None) -> List[ErrorEvent]:
        """Get recent errors, optionally filtered by category"""
        errors = list(self.error_history)
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        # Sort by timestamp descending
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        
        return errors[:limit]
    
    def get_critical_errors(self) -> List[ErrorEvent]:
        """Get all critical errors"""
        return [e for e in self.error_history if e.severity == ErrorSeverity.CRITICAL]
    
    def log_error_summary(self):
        """Log current error summary"""
        summary = self.get_error_summary()
        
        self.logger.info("=== Error Tracking Summary ===")
        self.logger.info(f"Total errors tracked: {summary['total_errors']}")
        self.logger.info(f"Recent errors (last hour): {summary['recent_errors_last_hour']}")
        
        self.logger.info("\nBy Severity:")
        for severity, count in summary['by_severity'].items():
            self.logger.info(f"  {severity}: {count}")
        
        self.logger.info("\nBy Category:")
        for category, count in summary['by_category'].items():
            self.logger.info(f"  {category}: {count}")
        
        if summary['recovery_attempted'] > 0:
            self.logger.info(
                f"\nRecovery Success Rate: {summary['recovery_success_rate']:.1%} "
                f"({summary['recovery_successful']}/{summary['recovery_attempted']})"
            )
    
    def export_errors(self, filepath: str):
        """Export error history to JSON file"""
        errors_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'summary': self.get_error_summary(),
            'recent_errors': [
                {
                    'error_id': e.error_id,
                    'timestamp': e.timestamp.isoformat(),
                    'category': e.category.value,
                    'severity': e.severity.value,
                    'operation': e.operation,
                    'pillar': e.pillar,
                    'error_type': e.error_type,
                    'error_message': e.error_message,
                    'correlation_id': e.correlation_id,
                    'recovery_attempted': e.recovery_attempted,
                    'recovery_successful': e.recovery_successful,
                    'recovery_action': e.recovery_action
                }
                for e in self.get_recent_errors(limit=100)
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(errors_data, f, indent=2)
        
        self.logger.info(f"Error history exported to {filepath}")
    
    def reset_errors(self):
        """Reset all error tracking (useful for testing)"""
        self.error_history.clear()
        self.error_stats.clear()
        self.error_count_by_category.clear()
        self.error_count_by_severity.clear()
        self.logger.info("Error tracking reset")


# Global error tracker instance
scoring_error_tracker = ScoringErrorTracker()
