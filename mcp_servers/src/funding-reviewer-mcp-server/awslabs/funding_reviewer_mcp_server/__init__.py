"""Funding Reviewer MCP Server Package - Simplified Version"""

from .models import (
    FileType,
    ValidationErrorType,
    UploadedFile,
    ValidationError,
    ValidationResult,
    ProcessedDocument
)
from .document_processor import SimpleDocumentProcessor

__version__ = "1.0.0"
__author__ = "AWS Labs"
__description__ = "MCP server for automated POC funding compliance analysis"

__all__ = [
    "FileType",
    "ValidationErrorType", 
    "UploadedFile",
    "ValidationError",
    "ValidationResult",
    "ProcessedDocument",
    "SimpleDocumentProcessor"
]