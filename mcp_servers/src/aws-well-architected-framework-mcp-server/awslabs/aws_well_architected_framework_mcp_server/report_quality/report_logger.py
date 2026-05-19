"""Comprehensive Error Logging for WAFR Report Generation.

This module provides detailed logging capabilities for report generation
with integration into the existing logging infrastructure.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for report generation."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationLogEntry:
    """Log entry for validation errors."""
    timestamp: datetime
    component: str
    validation_type: str
    message: str
    severity: str
    data_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "validation_type": self.validation_type,
            "message": self.message,
            "severity": self.severity,
            "data_context": self.data_context
        }


@dataclass
class FormattingLogEntry:
    """Log entry for formatting errors."""
    timestamp: datetime
    section: str
    error_type: str
    message: str
    pillar: Optional[str] = None
    fallback_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "section": self.section,
            "error_type": self.error_type,
            "message": self.message,
            "pillar": self.pillar,
            "fallback_used": self.fallback_used
        }


@dataclass
class ContentWarningEntry:
    """Log entry for content quality warnings."""
    timestamp: datetime
    warning_type: str
    message: str
    affected_component: str
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "warning_type": self.warning_type,
            "message": self.message,
            "affected_component": self.affected_component,
            "recommendation": self.recommendation
        }


@dataclass
class GenerationStats:
    """Statistics for report generation."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    total_pillars: int = 0
    successful_pillars: int = 0
    failed_pillars: int = 0
    total_recommendations: int = 0
    validation_errors: int = 0
    formatting_errors: int = 0
    content_warnings: int = 0
    fallbacks_used: int = 0
    report_size_bytes: int = 0
    success: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_pillars": self.total_pillars,
            "successful_pillars": self.successful_pillars,
            "failed_pillars": self.failed_pillars,
            "total_recommendations": self.total_recommendations,
            "validation_errors": self.validation_errors,
            "formatting_errors": self.formatting_errors,
            "content_warnings": self.content_warnings,
            "fallbacks_used": self.fallbacks_used,
            "report_size_bytes": self.report_size_bytes,
            "success": self.success
        }


class ReportGenerationLogger:
    """Comprehensive logger for WAFR report generation with integration into existing infrastructure."""
    
    def __init__(self, chat_id: str):
        """
        Initialize the report generation logger.
        
        Args:
            chat_id: Unique chat session identifier for tracking
        """
        self.chat_id = chat_id
        self.validation_errors: List[ValidationLogEntry] = []
        self.formatting_errors: List[FormattingLogEntry] = []
        self.content_warnings: List[ContentWarningEntry] = []
        self.stats = GenerationStats(start_time=datetime.now())
        
        logger.info(f"📊 Report generation logger initialized for chat_id: {chat_id}")
    
    def log_validation_error(
        self,
        component: str,
        validation_type: str,
        message: str,
        severity: str = "error",
        data_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a validation error with component context.
        
        Args:
            component: Component where validation failed
            validation_type: Type of validation (e.g., "data_structure", "required_field")
            message: Error message
            severity: Error severity ("critical", "error", "warning")
            data_context: Additional context data
        """
        entry = ValidationLogEntry(
            timestamp=datetime.now(),
            component=component,
            validation_type=validation_type,
            message=message,
            severity=severity,
            data_context=data_context or {}
        )
        
        self.validation_errors.append(entry)
        self.stats.validation_errors += 1
        
        # Log to standard logger with appropriate level
        log_message = f"❌ Validation Error [{component}]: {message}"
        if severity == "critical":
            logger.critical(log_message, extra={"chat_id": self.chat_id, "context": data_context})
        elif severity == "error":
            logger.error(log_message, extra={"chat_id": self.chat_id, "context": data_context})
        else:
            logger.warning(log_message, extra={"chat_id": self.chat_id, "context": data_context})
    
    def log_formatting_error(
        self,
        section: str,
        error_type: str,
        message: str,
        pillar: Optional[str] = None,
        fallback_used: bool = False
    ) -> None:
        """
        Log a formatting error with section context.
        
        Args:
            section: Report section where error occurred
            error_type: Type of formatting error
            message: Error message
            pillar: Optional pillar name if error is pillar-specific
            fallback_used: Whether a fallback was used
        """
        entry = FormattingLogEntry(
            timestamp=datetime.now(),
            section=section,
            error_type=error_type,
            message=message,
            pillar=pillar,
            fallback_used=fallback_used
        )
        
        self.formatting_errors.append(entry)
        self.stats.formatting_errors += 1
        
        if fallback_used:
            self.stats.fallbacks_used += 1
        
        # Log to standard logger
        pillar_info = f" [Pillar: {pillar}]" if pillar else ""
        fallback_info = " (fallback used)" if fallback_used else ""
        log_message = f"⚠️ Formatting Error [{section}]{pillar_info}: {message}{fallback_info}"
        logger.error(log_message, extra={"chat_id": self.chat_id, "section": section, "pillar": pillar})
    
    def log_content_warning(
        self,
        warning_type: str,
        message: str,
        affected_component: str,
        recommendation: str = ""
    ) -> None:
        """
        Log a content quality warning.
        
        Args:
            warning_type: Type of warning (e.g., "incomplete_data", "low_confidence")
            message: Warning message
            affected_component: Component affected by the warning
            recommendation: Recommended action to address the warning
        """
        entry = ContentWarningEntry(
            timestamp=datetime.now(),
            warning_type=warning_type,
            message=message,
            affected_component=affected_component,
            recommendation=recommendation or "Review and verify the affected content"
        )
        
        self.content_warnings.append(entry)
        self.stats.content_warnings += 1
        
        # Log to standard logger
        log_message = f"⚠️ Content Warning [{affected_component}]: {message}"
        if recommendation:
            log_message += f" | Recommendation: {recommendation}"
        logger.warning(log_message, extra={"chat_id": self.chat_id, "component": affected_component})
    
    def log_generation_summary(self, success: bool, report_size_bytes: int = 0) -> None:
        """
        Log summary of report generation with statistics.
        
        Args:
            success: Whether report generation was successful
            report_size_bytes: Size of generated report in bytes
        """
        self.stats.end_time = datetime.now()
        self.stats.duration_seconds = (self.stats.end_time - self.stats.start_time).total_seconds()
        self.stats.success = success
        self.stats.report_size_bytes = report_size_bytes
        
        # Create comprehensive summary
        summary = {
            "chat_id": self.chat_id,
            "generation_stats": self.stats.to_dict(),
            "error_summary": {
                "validation_errors": len(self.validation_errors),
                "formatting_errors": len(self.formatting_errors),
                "content_warnings": len(self.content_warnings),
                "total_issues": len(self.validation_errors) + len(self.formatting_errors) + len(self.content_warnings)
            },
            "quality_metrics": {
                "pillar_success_rate": (
                    self.stats.successful_pillars / self.stats.total_pillars * 100
                    if self.stats.total_pillars > 0 else 0
                ),
                "fallback_usage_rate": (
                    self.stats.fallbacks_used / self.stats.total_pillars * 100
                    if self.stats.total_pillars > 0 else 0
                )
            }
        }
        
        # Log summary with appropriate level
        if success:
            if self.stats.validation_errors > 0 or self.stats.formatting_errors > 0:
                logger.warning(
                    f"✅ Report generation completed with issues for chat_id: {self.chat_id}",
                    extra={"summary": summary}
                )
            else:
                logger.info(
                    f"✅ Report generation completed successfully for chat_id: {self.chat_id}",
                    extra={"summary": summary}
                )
        else:
            logger.error(
                f"❌ Report generation failed for chat_id: {self.chat_id}",
                extra={"summary": summary}
            )
        
        # Log detailed statistics
        logger.info(
            f"📊 Report Generation Statistics:\n"
            f"  Duration: {self.stats.duration_seconds:.2f}s\n"
            f"  Pillars: {self.stats.successful_pillars}/{self.stats.total_pillars} successful\n"
            f"  Recommendations: {self.stats.total_recommendations}\n"
            f"  Errors: {self.stats.validation_errors} validation, {self.stats.formatting_errors} formatting\n"
            f"  Warnings: {self.stats.content_warnings}\n"
            f"  Fallbacks: {self.stats.fallbacks_used}\n"
            f"  Report Size: {self.stats.report_size_bytes / 1024:.2f} KB",
            extra={"chat_id": self.chat_id}
        )
    
    def update_pillar_stats(self, total: int, successful: int, failed: int) -> None:
        """
        Update pillar processing statistics.
        
        Args:
            total: Total number of pillars
            successful: Number of successfully processed pillars
            failed: Number of failed pillars
        """
        self.stats.total_pillars = total
        self.stats.successful_pillars = successful
        self.stats.failed_pillars = failed
    
    def update_recommendation_count(self, count: int) -> None:
        """
        Update total recommendation count.
        
        Args:
            count: Total number of recommendations generated
        """
        self.stats.total_recommendations = count
    
    def get_validation_errors(self) -> List[Dict[str, Any]]:
        """Get all validation errors as dictionaries."""
        return [entry.to_dict() for entry in self.validation_errors]
    
    def get_formatting_errors(self) -> List[Dict[str, Any]]:
        """Get all formatting errors as dictionaries."""
        return [entry.to_dict() for entry in self.formatting_errors]
    
    def get_content_warnings(self) -> List[Dict[str, Any]]:
        """Get all content warnings as dictionaries."""
        return [entry.to_dict() for entry in self.content_warnings]
    
    def get_full_log(self) -> Dict[str, Any]:
        """
        Get complete log data for export or analysis.
        
        Returns:
            Dictionary containing all log entries and statistics
        """
        return {
            "chat_id": self.chat_id,
            "generation_stats": self.stats.to_dict(),
            "validation_errors": self.get_validation_errors(),
            "formatting_errors": self.get_formatting_errors(),
            "content_warnings": self.get_content_warnings(),
            "summary": {
                "total_issues": (
                    len(self.validation_errors) +
                    len(self.formatting_errors) +
                    len(self.content_warnings)
                ),
                "critical_issues": len([
                    e for e in self.validation_errors
                    if e.severity == "critical"
                ]),
                "success": self.stats.success
            }
        }
    
    def export_to_json(self) -> str:
        """
        Export complete log to JSON string.
        
        Returns:
            JSON string of complete log data
        """
        return json.dumps(self.get_full_log(), indent=2, default=str)
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors were logged."""
        return any(e.severity == "critical" for e in self.validation_errors)
    
    def has_errors(self) -> bool:
        """Check if any errors were logged."""
        return len(self.validation_errors) > 0 or len(self.formatting_errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were logged."""
        return len(self.content_warnings) > 0
    
    def get_error_summary_for_report(self) -> Dict[str, Any]:
        """
        Get error summary suitable for inclusion in the report.
        
        Returns:
            Dictionary with user-friendly error summary
        """
        if not self.has_errors() and not self.has_warnings():
            return {
                "status": "success",
                "message": "Report generated successfully with no issues"
            }
        
        summary = {
            "status": "partial" if self.has_critical_errors() else "success_with_warnings",
            "message": "",
            "details": []
        }
        
        if self.has_critical_errors():
            summary["message"] = "Report generated with critical errors. Some sections may contain incomplete data."
            summary["details"].append(
                "Critical errors occurred during generation. Please review the report carefully."
            )
        elif self.has_errors():
            summary["message"] = "Report generated with minor errors. Report quality may be affected."
            summary["details"].append(
                f"{len(self.validation_errors) + len(self.formatting_errors)} errors occurred during generation."
            )
        
        if self.has_warnings():
            summary["details"].append(
                f"{len(self.content_warnings)} warnings were generated. Some data may be incomplete."
            )
        
        if self.stats.fallbacks_used > 0:
            summary["details"].append(
                f"Fallback data was used in {self.stats.fallbacks_used} instances."
            )
        
        return summary
    
    def clear(self) -> None:
        """Clear all logged entries and reset statistics."""
        self.validation_errors.clear()
        self.formatting_errors.clear()
        self.content_warnings.clear()
        self.stats = GenerationStats(start_time=datetime.now())
        logger.info(f"🔄 Report generation logger cleared for chat_id: {self.chat_id}")


class ReportLoggerFactory:
    """Factory for creating and managing report loggers."""
    
    _loggers: Dict[str, ReportGenerationLogger] = {}
    
    @classmethod
    def get_logger(cls, chat_id: str) -> ReportGenerationLogger:
        """
        Get or create a logger for a chat session.
        
        Args:
            chat_id: Unique chat session identifier
            
        Returns:
            ReportGenerationLogger instance
        """
        if chat_id not in cls._loggers:
            cls._loggers[chat_id] = ReportGenerationLogger(chat_id)
        return cls._loggers[chat_id]
    
    @classmethod
    def remove_logger(cls, chat_id: str) -> None:
        """
        Remove a logger from the factory.
        
        Args:
            chat_id: Unique chat session identifier
        """
        if chat_id in cls._loggers:
            del cls._loggers[chat_id]
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all loggers from the factory."""
        cls._loggers.clear()
