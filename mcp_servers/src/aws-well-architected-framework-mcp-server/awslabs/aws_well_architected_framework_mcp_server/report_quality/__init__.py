"""Report Quality Enhancement Module for WAFR Report Generation.

This module provides comprehensive error handling, validation, and logging
capabilities for professional WAFR report generation.
"""

from .error_handler import (
    GracefulDegradationHandler,
    ValidationError,
    FallbackResult
)
from .report_logger import (
    ReportGenerationLogger,
    ReportLoggerFactory,
    GenerationStats,
    ValidationLogEntry,
    FormattingLogEntry,
    ContentWarningEntry
)
from .docx_validator import (
    DOCXValidator,
    DOCXValidationResult,
    get_docx_validator
)

__all__ = [
    # Error handling
    'GracefulDegradationHandler',
    'ValidationError',
    'FallbackResult',
    
    # Logging
    'ReportGenerationLogger',
    'ReportLoggerFactory',
    'GenerationStats',
    'ValidationLogEntry',
    'FormattingLogEntry',
    'ContentWarningEntry',
    
    # DOCX validation
    'DOCXValidator',
    'DOCXValidationResult',
    'get_docx_validator',
]
