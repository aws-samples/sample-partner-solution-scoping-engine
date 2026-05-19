"""Error handling and exception management for WAFR MCP Server"""

import traceback
from typing import Dict, Any, Optional
from datetime import datetime


class WAFRAssessmentError(Exception):
    """Base exception for WAFR assessment errors."""
    
    def __init__(self, message: str, error_code: str = "WAFR_ERROR", details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class DocumentProcessingError(WAFRAssessmentError):
    """Document processing and analysis errors."""
    
    def __init__(self, message: str, document_path: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", details)
        self.document_path = document_path


class AWSIntegrationError(WAFRAssessmentError):
    """AWS API integration errors."""
    
    def __init__(self, message: str, service: Optional[str] = None, operation: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "AWS_INTEGRATION_ERROR", details)
        self.service = service
        self.operation = operation


class AssessmentEngineError(WAFRAssessmentError):
    """Assessment logic and scoring errors."""
    
    def __init__(self, message: str, pillar: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "ASSESSMENT_ENGINE_ERROR", details)
        self.pillar = pillar


class ReportGenerationError(WAFRAssessmentError):
    """Report generation and storage errors."""
    
    def __init__(self, message: str, report_type: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "REPORT_GENERATION_ERROR", details)
        self.report_type = report_type


class ConfigurationError(WAFRAssessmentError):
    """Configuration and setup errors."""
    
    def __init__(self, message: str, component: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.component = component


def handle_mcp_error(error: Exception, operation: str) -> Dict[str, Any]:
    """
    Handle MCP tool errors and return structured error response.
    
    Args:
        error: The exception that occurred
        operation: The operation that failed
        
    Returns:
        Structured error response for MCP client
    """
    error_response = {
        "success": False,
        "error": {
            "operation": operation,
            "message": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Add specific error details for WAFR errors
    if isinstance(error, WAFRAssessmentError):
        error_response["error"].update({
            "error_code": error.error_code,
            "details": error.details
        })
        
        # Add specific fields for different error types
        if isinstance(error, DocumentProcessingError) and error.document_path:
            error_response["error"]["document_path"] = error.document_path
        elif isinstance(error, AWSIntegrationError):
            if error.service:
                error_response["error"]["aws_service"] = error.service
            if error.operation:
                error_response["error"]["aws_operation"] = error.operation
        elif isinstance(error, AssessmentEngineError) and error.pillar:
            error_response["error"]["pillar"] = error.pillar
        elif isinstance(error, ReportGenerationError) and error.report_type:
            error_response["error"]["report_type"] = error.report_type
        elif isinstance(error, ConfigurationError) and error.component:
            error_response["error"]["component"] = error.component
    
    # Add stack trace for debugging (only in development)
    import os
    if os.getenv("WAFR_DEBUG", "false").lower() == "true":
        error_response["error"]["traceback"] = traceback.format_exc()
    
    return error_response


def handle_graceful_degradation(error: Exception, operation: str, fallback_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Handle errors with graceful degradation, returning partial results when possible.
    
    Args:
        error: The exception that occurred
        operation: The operation that failed
        fallback_data: Optional fallback data to return
        
    Returns:
        Response with partial results and error information
    """
    response = {
        "success": False,
        "partial_success": True,
        "operation": operation,
        "error": {
            "message": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if fallback_data:
        response["data"] = fallback_data
        response["message"] = f"Operation partially completed with fallback data due to error: {str(error)}"
    else:
        response["message"] = f"Operation failed: {str(error)}"
    
    return response


class ErrorRecoveryManager:
    """
    Manages error recovery strategies for different types of failures.
    """
    
    def __init__(self):
        self.retry_counts = {}
        self.max_retries = 3
    
    def should_retry(self, operation: str, error: Exception) -> bool:
        """
        Determine if an operation should be retried based on error type.
        
        Args:
            operation: The operation that failed
            error: The exception that occurred
            
        Returns:
            True if operation should be retried
        """
        # Don't retry configuration errors
        if isinstance(error, ConfigurationError):
            return False
        
        # Don't retry document processing errors (usually permanent)
        if isinstance(error, DocumentProcessingError):
            return False
        
        # Retry AWS integration errors (may be transient)
        if isinstance(error, AWSIntegrationError):
            retry_count = self.retry_counts.get(operation, 0)
            return retry_count < self.max_retries
        
        # Retry assessment engine errors (may be transient)
        if isinstance(error, AssessmentEngineError):
            retry_count = self.retry_counts.get(operation, 0)
            return retry_count < self.max_retries
        
        # Default: don't retry unknown errors
        return False
    
    def record_retry(self, operation: str):
        """Record a retry attempt for an operation."""
        self.retry_counts[operation] = self.retry_counts.get(operation, 0) + 1
    
    def reset_retry_count(self, operation: str):
        """Reset retry count for an operation after success."""
        if operation in self.retry_counts:
            del self.retry_counts[operation]
    
    async def execute_with_retry(self, operation: str, func, *args, **kwargs):
        """
        Execute a function with retry logic.
        
        Args:
            operation: Operation name for tracking
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises exception after max retries
        """
        last_error = None
        
        while True:
            try:
                result = await func(*args, **kwargs)
                self.reset_retry_count(operation)
                return result
            except Exception as e:
                last_error = e
                
                if not self.should_retry(operation, e):
                    raise e
                
                self.record_retry(operation)
                
                # Exponential backoff
                import asyncio
                retry_count = self.retry_counts.get(operation, 0)
                delay = min(2 ** retry_count, 30)  # Max 30 seconds
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_error:
            raise last_error