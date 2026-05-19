"""
Simplified Document Processing Module for POC Funding Reviewer

This module provides minimal document processing - just validation and 
preparation for direct Bedrock analysis. All content analysis is done by the LLM.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from .models import UploadedFile, ValidationResult, ValidationError, ValidationErrorType, FileType
from .config import get_config


class SimpleDocumentProcessor:
    """Simplified document processor that just validates and prepares files for Bedrock."""
    
    def __init__(self):
        """Initialize the simple document processor."""
        self.config = get_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Supported file types
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
        """Validate the uploaded file with basic checks only.
        
        Args:
            file: The uploaded file to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check if file is empty
        if file.is_empty:
            result.add_error(
                ValidationErrorType.FILE_EMPTY,
                "File is empty"
            )
            return result
        
        # Check file size
        max_size_bytes = self.config.file_processing.max_file_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            result.add_error(
                ValidationErrorType.FILE_TOO_LARGE,
                f"File size ({file.size} bytes) exceeds maximum allowed size ({max_size_bytes} bytes)"
            )
            return result
        
        # Check file type
        file_type = file.get_file_type()
        if not file_type or file_type not in self.supported_types:
            result.add_error(
                ValidationErrorType.UNSUPPORTED_TYPE,
                f"File type {file_type} is not supported"
            )
            return result
        
        result.file_type = file_type
        
        # File format validation is now handled in get_file_type() using magic bytes
        # If we reach here, the file type was successfully detected
        
        return result
    
    def _validate_file_format(self, file: UploadedFile, file_type: FileType) -> bool:
        """Basic file format validation using magic bytes.
        
        Args:
            file: The uploaded file
            file_type: The detected file type
            
        Returns:
            True if file format appears valid
        """
        if not file.content or len(file.content) < 4:
            return False
        
        # Check magic bytes for common formats
        magic_bytes = file.content[:8]
        
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
            # DOCX files are ZIP archives
            return magic_bytes.startswith(b'PK\x03\x04') or magic_bytes.startswith(b'PK\x05\x06')
        elif file_type == FileType.CSV:
            # For CSV, just check if it's valid UTF-8 text
            try:
                file.content.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
        
        return True
    
    def prepare_for_bedrock(self, file: UploadedFile) -> Dict[str, Any]:
        """Prepare file for direct Bedrock multimodal analysis.
        
        Args:
            file: The uploaded file to prepare
            
        Returns:
            Dictionary with file data ready for Bedrock API
        """
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
    
    def get_file_summary(self, file: UploadedFile) -> str:
        """Get a simple summary of the file for logging/display.
        
        Args:
            file: The uploaded file
            
        Returns:
            Human-readable file summary
        """
        file_type = file.get_file_type()
        size_mb = file.size / (1024 * 1024)
        
        return f"{file.filename} ({file_type.value if file_type else 'unknown'}, {size_mb:.1f}MB)"


# Legacy compatibility - create instances of the old processors that use the simplified approach
class PDFProcessor(SimpleDocumentProcessor):
    """Legacy PDF processor - now uses simplified approach."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("Using simplified PDF processor - content analysis delegated to Bedrock")
    
    def validate(self, file: UploadedFile) -> ValidationResult:
        return self.validate_file(file)
    
    def process(self, file: UploadedFile):
        """Process PDF file - returns minimal processed document."""
        from .models import ProcessedSOW
        import time
        
        start_time = time.time()
        validation_result = self.validate_file(file)
        
        if not validation_result.is_valid:
            raise ValueError(f"File validation failed: {validation_result.error_messages}")
        
        processing_time = time.time() - start_time
        
        return ProcessedSOW(
            file_info=file,
            content=f"[PDF Document ready for Bedrock analysis: {file.filename}]",
            processing_time=processing_time,
            metadata={
                "ready_for_bedrock": True,
                "bedrock_data": self.prepare_for_bedrock(file)
            },
            project_scope="[To be analyzed by Bedrock]",
            deliverables=[],
            timeline="[To be analyzed by Bedrock]", 
            cost_breakdown={},
            services_mentioned=[]
        )


class DOCXProcessor(SimpleDocumentProcessor):
    """Legacy DOCX processor - now uses simplified approach."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("Using simplified DOCX processor - content analysis delegated to Bedrock")
    
    def validate(self, file: UploadedFile) -> ValidationResult:
        return self.validate_file(file)
    
    def process(self, file: UploadedFile):
        """Process DOCX file - returns minimal processed document."""
        from .models import ProcessedSOW
        import time
        
        start_time = time.time()
        validation_result = self.validate_file(file)
        
        if not validation_result.is_valid:
            raise ValueError(f"File validation failed: {validation_result.error_messages}")
        
        processing_time = time.time() - start_time
        
        return ProcessedSOW(
            file_info=file,
            content=f"[DOCX Document ready for Bedrock analysis: {file.filename}]",
            processing_time=processing_time,
            metadata={
                "ready_for_bedrock": True,
                "bedrock_data": self.prepare_for_bedrock(file)
            },
            project_scope="[To be analyzed by Bedrock]",
            deliverables=[],
            timeline="[To be analyzed by Bedrock]",
            cost_breakdown={},
            services_mentioned=[]
        )


class ImageProcessor(SimpleDocumentProcessor):
    """Legacy Image processor - now uses simplified approach."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("Using simplified Image processor - content analysis delegated to Bedrock")
    
    def validate(self, file: UploadedFile) -> ValidationResult:
        return self.validate_file(file)
    
    def process(self, file: UploadedFile):
        """Process image file - returns minimal processed document."""
        from .models import ProcessedDiagram
        import time
        
        start_time = time.time()
        validation_result = self.validate_file(file)
        
        if not validation_result.is_valid:
            raise ValueError(f"File validation failed: {validation_result.error_messages}")
        
        processing_time = time.time() - start_time
        
        return ProcessedDiagram(
            file_info=file,
            content=f"[Architecture Diagram ready for Bedrock vision analysis: {file.filename}]",
            processing_time=processing_time,
            metadata={
                "ready_for_bedrock": True,
                "bedrock_data": self.prepare_for_bedrock(file)
            },
            image_data=file.content,
            detected_services=[],
            architecture_description="[To be analyzed by Bedrock]",
            well_architected_compliance=False,
            image_format=file.get_file_type().value if file.get_file_type() else "unknown",
            image_dimensions=(0, 0),
            file_size_kb=file.size / 1024
        )


class CSVProcessor(SimpleDocumentProcessor):
    """Legacy CSV processor - now uses simplified approach."""
    
    def __init__(self):
        super().__init__()
        self.logger.info("Using simplified CSV processor - content analysis delegated to Bedrock")
    
    def validate(self, file: UploadedFile) -> ValidationResult:
        return self.validate_file(file)
    
    def process(self, file: UploadedFile):
        """Process CSV file - returns minimal processed document."""
        from .models import ProcessedCSV
        import time
        
        start_time = time.time()
        validation_result = self.validate_file(file)
        
        if not validation_result.is_valid:
            raise ValueError(f"File validation failed: {validation_result.error_messages}")
        
        processing_time = time.time() - start_time
        
        return ProcessedCSV(
            file_info=file,
            content=f"[CSV Document ready for Bedrock analysis: {file.filename}]",
            processing_time=processing_time,
            metadata={
                "ready_for_bedrock": True,
                "bedrock_data": self.prepare_for_bedrock(file)
            },
            services=[],
            total_cost=0.0,
            monthly_breakdown={}
        )