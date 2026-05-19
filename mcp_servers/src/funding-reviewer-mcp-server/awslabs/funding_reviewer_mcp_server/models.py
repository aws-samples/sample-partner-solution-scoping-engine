"""
Simplified data models for the POC funding reviewer MCP server.

This module contains only the essential models needed for file handling and validation.
All analysis models have been removed as analysis is now handled directly by Bedrock.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


class FileType(Enum):
    """Supported file types for document processing."""
    PDF = "pdf"
    DOCX = "docx"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    GIF = "gif"
    WEBP = "webp"
    CSV = "csv"


class ValidationErrorType(Enum):
    """Types of validation errors."""
    INVALID_FORMAT = "invalid_format"
    FILE_TOO_LARGE = "file_too_large"
    FILE_EMPTY = "file_empty"
    CORRUPTED_FILE = "corrupted_file"
    UNSUPPORTED_TYPE = "unsupported_type"
    MISSING_CONTENT = "missing_content"


@dataclass
class UploadedFile:
    """Represents an uploaded file for processing."""
    filename: str
    content_type: str
    size: int
    content: bytes
    file_path: Optional[str] = None
    
    @property
    def file_extension(self) -> str:
        """Get the file extension."""
        return Path(self.filename).suffix.lower().lstrip('.')
    
    @property
    def is_empty(self) -> bool:
        """Check if the file is empty."""
        return self.size == 0 or len(self.content) == 0
    
    def get_file_type(self) -> Optional[FileType]:
        """Determine the file type based on magic bytes first, then extension."""
        # First try to detect by magic bytes (more reliable)
        if self.content and len(self.content) >= 8:
            magic_bytes = self.content[:8]
            
            # Check magic bytes for common formats
            if magic_bytes.startswith(b'%PDF-'):
                return FileType.PDF
            elif magic_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                return FileType.PNG
            elif magic_bytes.startswith(b'\xff\xd8\xff'):
                return FileType.JPG
            elif magic_bytes.startswith(b'GIF87a') or magic_bytes.startswith(b'GIF89a'):
                return FileType.GIF
            elif magic_bytes.startswith(b'RIFF') and len(self.content) >= 12 and self.content[8:12] == b'WEBP':
                return FileType.WEBP
            elif magic_bytes.startswith(b'PK\x03\x04') or magic_bytes.startswith(b'PK\x05\x06'):
                return FileType.DOCX
        
        # Fall back to extension-based detection
        extension = self.file_extension
        try:
            return FileType(extension)
        except ValueError:
            return None


@dataclass
class ValidationError:
    """Represents a validation error."""
    error_type: ValidationErrorType
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of file validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    file_type: Optional[FileType] = None
    
    def add_error(self, error_type: ValidationErrorType, message: str, 
                  field: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a validation error."""
        error = ValidationError(error_type, message, field, details)
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)
    
    @property
    def error_messages(self) -> List[str]:
        """Get all error messages."""
        return [error.message for error in self.errors]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


# Legacy compatibility classes - these are kept minimal for backward compatibility
# but all analysis is now done by Bedrock, not by these classes

@dataclass
class ProcessedDocument:
    """Minimal processed document for legacy compatibility."""
    file_info: UploadedFile
    content: str
    processing_time: float
    metadata: Dict[str, Any]


@dataclass
class ProcessedSOW(ProcessedDocument):
    """Minimal processed SOW for legacy compatibility."""
    project_scope: str = ""
    deliverables: List[str] = None
    timeline: str = ""
    cost_breakdown: Dict[str, float] = None
    services_mentioned: List[str] = None
    
    def __post_init__(self):
        if self.deliverables is None:
            self.deliverables = []
        if self.cost_breakdown is None:
            self.cost_breakdown = {}
        if self.services_mentioned is None:
            self.services_mentioned = []


@dataclass
class ProcessedDiagram(ProcessedDocument):
    """Minimal processed diagram for legacy compatibility."""
    image_data: bytes
    detected_services: List[str] = None
    architecture_description: str = ""
    well_architected_compliance: bool = False
    image_format: str = "unknown"
    image_dimensions: tuple = (0, 0)
    file_size_kb: float = 0.0
    
    def __post_init__(self):
        if self.detected_services is None:
            self.detected_services = []


@dataclass
class ProcessedCSV(ProcessedDocument):
    """Minimal processed CSV for legacy compatibility."""
    services: List[Any] = None
    total_cost: float = 0.0
    monthly_breakdown: Dict[str, float] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []
        if self.monthly_breakdown is None:
            self.monthly_breakdown = {}