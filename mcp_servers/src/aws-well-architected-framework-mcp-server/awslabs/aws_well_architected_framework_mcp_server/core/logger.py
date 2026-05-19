"""Logging configuration for WAFR MCP Server"""

import logging
import sys
from typing import Optional
from datetime import datetime


def setup_logger(name: str, level: str = "ERROR") -> logging.Logger:
    """
    Set up structured logging for the WAFR MCP Server.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set logging level - use ERROR for MCP compatibility (minimal output)
    log_level = getattr(logging, level.upper(), logging.ERROR)
    logger.setLevel(log_level)
    
    # Create console handler - use stderr to avoid interfering with MCP JSON-RPC on stdout
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


class WAFRLogger:
    """
    Structured logger for WAFR assessment operations.
    
    Provides context-aware logging with assessment tracking.
    """
    
    def __init__(self, name: str):
        self.logger = setup_logger(name)
        self.assessment_context: Optional[str] = None
    
    def set_assessment_context(self, chat_id: str, assessment_id: Optional[str] = None):
        """Set assessment context for logging."""
        if assessment_id:
            self.assessment_context = f"[{chat_id}:{assessment_id}]"
        else:
            self.assessment_context = f"[{chat_id}]"
    
    def clear_assessment_context(self):
        """Clear assessment context."""
        self.assessment_context = None
    
    def _format_message(self, message: str) -> str:
        """Format message with assessment context."""
        if self.assessment_context:
            return f"{self.assessment_context} {message}"
        return message
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message), **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message(message), **kwargs)
    
    def log_assessment_start(self, chat_id: str, pillars: list):
        """Log assessment start."""
        self.set_assessment_context(chat_id)
        self.info(f"Starting WAFR assessment for pillars: {pillars}")
    
    def log_assessment_completion(self, chat_id: str, assessment_id: str):
        """Log assessment completion with ID."""
        self.info(f"Assessment {assessment_id} completed successfully")
        self.clear_assessment_context()
    
    def log_assessment_complete(self, chat_id: str, duration: float, findings_count: int):
        """Log assessment completion."""
        self.info(f"Assessment completed in {duration:.2f}s with {findings_count} findings")
        self.clear_assessment_context()
    
    def log_pillar_assessment(self, pillar: str, score: float, findings: int):
        """Log pillar assessment results."""
        self.info(f"{pillar} pillar: score={score:.2f}, findings={findings}")
    
    def log_document_processing(self, document_count: int, services_found: int):
        """Log document processing results."""
        self.info(f"Processed {document_count} documents, found {services_found} AWS services")
    
    def log_error_with_context(self, error: Exception, operation: str):
        """Log error with operation context."""
        self.error(f"Error in {operation}: {str(error)}", exc_info=True)
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()