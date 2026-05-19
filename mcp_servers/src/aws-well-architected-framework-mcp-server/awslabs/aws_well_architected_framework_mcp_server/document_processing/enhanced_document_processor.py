"""Enhanced Document Processing Module for WAFR Server

Provides comprehensive document validation and processing capabilities
matching the funding reviewer server's implementation.
"""

import base64
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Supported file types with validation."""
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
    FILE_EMPTY = "file_empty"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_TYPE = "unsupported_type"
    INVALID_FORMAT = "invalid_format"


@dataclass
class ValidationError:
    """Validation error details."""
    error_type: ValidationErrorType
    message: str


@dataclass
class ValidationResult:
    """File validation result."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    file_type: Optional[FileType] = None
    
    def add_error(self, error_type: ValidationErrorType, message: str):
        """Add validation error."""
        self.errors.append(ValidationError(error_type, message))
        self.is_valid = False


@dataclass
class UploadedFile:
    """Uploaded file representation."""
    filename: str
    content: bytes
    size: int
    
    @property
    def is_empty(self) -> bool:
        """Check if file is empty."""
        return self.size == 0 or not self.content
    
    def get_file_type(self) -> Optional[FileType]:
        """Detect file type using magic bytes."""
        if not self.content or len(self.content) < 4:
            return None
        
        magic_bytes = self.content[:12]
        
        # PDF
        if magic_bytes.startswith(b'%PDF-'):
            return FileType.PDF
        
        # PNG
        if magic_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return FileType.PNG
        
        # JPEG
        if magic_bytes.startswith(b'\xff\xd8\xff'):
            return FileType.JPEG if self.filename.lower().endswith('.jpeg') else FileType.JPG
        
        # GIF
        if magic_bytes.startswith(b'GIF87a') or magic_bytes.startswith(b'GIF89a'):
            return FileType.GIF
        
        # WEBP
        if magic_bytes.startswith(b'RIFF') and magic_bytes[8:12] == b'WEBP':
            return FileType.WEBP
        
        # DOCX (ZIP archive)
        if magic_bytes.startswith(b'PK\x03\x04') or magic_bytes.startswith(b'PK\x05\x06'):
            if self.filename.lower().endswith('.docx'):
                return FileType.DOCX
        
        # CSV (UTF-8 text)
        if self.filename.lower().endswith('.csv'):
            try:
                self.content.decode('utf-8')
                return FileType.CSV
            except UnicodeDecodeError:
                pass
        
        return None


class EnhancedDocumentProcessor:
    """Enhanced document processor with comprehensive validation."""
    
    def __init__(self, max_file_size_mb: int = 50):
        """Initialize processor with configurable limits."""
        self.max_file_size_mb = max_file_size_mb
        self.supported_types = {
            FileType.PDF: "application/pdf",
            FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            FileType.PNG: "image/png",
            FileType.JPG: "image/jpeg",
            FileType.JPEG: "image/jpeg",
            FileType.GIF: "image/gif",
            FileType.WEBP: "image/webp",
            FileType.CSV: "text/csv"
        }
    
    def validate_file(self, file: UploadedFile) -> ValidationResult:
        """Validate uploaded file with comprehensive checks."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check if file is empty
        if file.is_empty:
            result.add_error(ValidationErrorType.FILE_EMPTY, "File is empty")
            return result
        
        # Check file size
        max_size_bytes = self.max_file_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            result.add_error(
                ValidationErrorType.FILE_TOO_LARGE,
                f"File size ({file.size} bytes) exceeds maximum ({max_size_bytes} bytes)"
            )
            return result
        
        # Detect and validate file type
        file_type = file.get_file_type()
        if not file_type or file_type not in self.supported_types:
            result.add_error(
                ValidationErrorType.UNSUPPORTED_TYPE,
                f"File type {file_type} is not supported"
            )
            return result
        
        result.file_type = file_type
        
        # Validate file format integrity
        if not self._validate_file_format(file, file_type):
            result.add_error(
                ValidationErrorType.INVALID_FORMAT,
                f"File format validation failed for {file_type.value}"
            )
        
        return result
    
    def _validate_file_format(self, file: UploadedFile, file_type: FileType) -> bool:
        """Validate file format using magic bytes."""
        if not file.content or len(file.content) < 4:
            return False
        
        magic_bytes = file.content[:12]
        
        if file_type == FileType.PDF:
            return magic_bytes.startswith(b'%PDF-')
        elif file_type == FileType.PNG:
            return magic_bytes.startswith(b'\x89PNG\r\n\x1a\n')
        elif file_type in [FileType.JPG, FileType.JPEG]:
            return magic_bytes.startswith(b'\xff\xd8\xff')
        elif file_type == FileType.GIF:
            return magic_bytes.startswith(b'GIF87a') or magic_bytes.startswith(b'GIF89a')
        elif file_type == FileType.WEBP:
            return magic_bytes.startswith(b'RIFF') and magic_bytes[8:12] == b'WEBP'
        elif file_type == FileType.DOCX:
            return magic_bytes.startswith(b'PK\x03\x04') or magic_bytes.startswith(b'PK\x05\x06')
        elif file_type == FileType.CSV:
            try:
                file.content.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
        
        return True
    
    def prepare_for_bedrock(self, file: UploadedFile) -> Dict[str, Any]:
        """Prepare file for Bedrock multimodal analysis."""
        file_type = file.get_file_type()
        media_type = self.supported_types.get(file_type, "application/octet-stream")
        
        # Encode file content as base64
        file_base64 = base64.b64encode(file.content).decode('utf-8')
        
        # Determine content type for Bedrock
        if file_type in [FileType.PNG, FileType.JPG, FileType.JPEG, FileType.GIF, FileType.WEBP]:
            content_type = "image"
        elif file_type in [FileType.PDF, FileType.DOCX]:
            content_type = "document"
        else:
            content_type = "text"
        
        return {
            "type": content_type,
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": file_base64
            },
            "filename": file.filename,
            "file_type": file_type.value if file_type else "unknown",
            "size": file.size
        }
