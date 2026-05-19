"""Enhanced S3 Manager for WAFR Server

Provides comprehensive S3 integration matching funding reviewer capabilities.
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError

from .enhanced_document_processor import UploadedFile, FileType
from .consts import get_aws_region

logger = logging.getLogger(__name__)


class EnhancedS3Manager:
    """Enhanced S3 manager with comprehensive document and report management."""
    
    def __init__(self, region_name: str = None, bucket_name: Optional[str] = None):
        """Initialize enhanced S3 manager."""
        self.region_name = region_name or get_aws_region()
        self.s3_client = boto3.client('s3', region_name=self.region_name)
        self.bucket_name = bucket_name or self._get_default_bucket()
        
    def _get_default_bucket(self) -> str:
        """Get default S3 bucket from environment or configuration."""
        # Try to get from environment first
        bucket = os.getenv('SERA_S3_BUCKET', os.getenv('S3_DOCUMENTS_BUCKET'))
        if bucket:
            return bucket
        
        # Fallback to account-based naming
        try:
            sts = boto3.client('sts')
            account_id = sts.get_caller_identity()['Account']
            return f"sera-chat-docs-{account_id}"
        except Exception:
            return "sera-wafr-documents"
    
    def validate_s3_access(self) -> bool:
        """Validate S3 bucket access and permissions."""
        try:
            # Check if bucket exists and is accessible
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            # Test write permissions with a small test object
            test_key = f"wafr-test/{uuid.uuid4()}.txt"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=test_key,
                Body=b"WAFR S3 access test",
                ContentType="text/plain"
            )
            
            # Clean up test object
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)
            
            logger.info(f"S3 access validated for bucket: {self.bucket_name}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 access validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating S3 access: {e}")
            return False
    
    def upload_document(
        self,
        file: UploadedFile,
        chat_id: str,
        document_type: str = "upload"
    ) -> Dict[str, Any]:
        """
        Upload document to S3 with proper organization.
        
        Args:
            file: UploadedFile object
            chat_id: Chat/session identifier
            document_type: Type of document (upload, report, diagram, etc.)
            
        Returns:
            Upload result with S3 details
        """
        try:
            # Generate S3 key with proper organization
            file_extension = self._get_file_extension(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            s3_key = f"wafr/{chat_id}/{document_type}/{timestamp}_{file.filename}"
            
            # Determine content type
            file_type = file.get_file_type()
            content_type = self._get_content_type(file_type)
            
            # Upload to S3 with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file.content,
                ContentType=content_type,
                Metadata={
                    'chat-id': chat_id,
                    'document-type': document_type,
                    'original-filename': file.filename,
                    'file-size': str(file.size),
                    'upload-timestamp': timestamp,
                    'file-type': file_type.value if file_type else 'unknown'
                }
            )
            
            # Generate presigned URL for access
            presigned_url = self.generate_presigned_url(s3_key, expiration=3600)
            
            result = {
                "status": "success",
                "s3_key": s3_key,
                "s3_url": f"s3://{self.bucket_name}/{s3_key}",
                "presigned_url": presigned_url,
                "bucket": self.bucket_name,
                "content_type": content_type,
                "size": file.size,
                "upload_timestamp": timestamp
            }
            
            logger.info(f"Document uploaded successfully: {s3_key}")
            return result
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise Exception(f"Failed to upload document to S3: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise Exception(f"Document upload failed: {e}")
    
    def download_document_from_url(self, s3_url: str) -> UploadedFile:
        """
        Download document from S3 URL.
        
        Args:
            s3_url: S3 URL (s3://bucket/key format)
            
        Returns:
            UploadedFile object with content
        """
        try:
            # Parse S3 URL
            parsed = urlparse(s3_url)
            if parsed.scheme != 's3':
                raise ValueError(f"Invalid S3 URL format: {s3_url}")
            
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            # Download object
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Extract filename from key or metadata
            filename = response.get('Metadata', {}).get('original-filename')
            if not filename:
                filename = os.path.basename(key)
            
            # Create UploadedFile object
            file = UploadedFile(
                filename=filename,
                content=content,
                size=len(content)
            )
            
            logger.info(f"Document downloaded successfully: {filename}")
            return file
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise Exception(f"Failed to download document from S3: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise Exception(f"Document download failed: {e}")
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """
        Generate presigned URL for S3 object access.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            method: S3 method (get_object, put_object)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise Exception(f"Presigned URL generation failed: {e}")
    
    def upload_report(
        self,
        report_content: bytes,
        chat_id: str,
        report_type: str = "wafr_assessment",
        content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) -> Dict[str, Any]:
        """
        Upload WAFR assessment report to S3.
        
        Args:
            report_content: Report content as bytes
            chat_id: Chat/session identifier
            report_type: Type of report
            content_type: MIME content type
            
        Returns:
            Upload result with S3 details
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}.docx"
            s3_key = f"wafr/{chat_id}/reports/{filename}"
            
            # Upload report
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=report_content,
                ContentType=content_type,
                Metadata={
                    'chat-id': chat_id,
                    'report-type': report_type,
                    'generation-timestamp': timestamp,
                    'content-type': content_type
                }
            )
            
            # Generate presigned URL
            presigned_url = self.generate_presigned_url(s3_key, expiration=7200)  # 2 hours
            
            result = {
                "status": "success",
                "s3_key": s3_key,
                "s3_url": f"s3://{self.bucket_name}/{s3_key}",
                "presigned_url": presigned_url,
                "filename": filename,
                "size": len(report_content),
                "generation_timestamp": timestamp
            }
            
            logger.info(f"Report uploaded successfully: {s3_key}")
            return result
            
        except Exception as e:
            logger.error(f"Report upload failed: {e}")
            raise Exception(f"Failed to upload report to S3: {e}")
    
    def list_chat_documents(self, chat_id: str) -> List[Dict[str, Any]]:
        """
        List all documents for a specific chat session.
        
        Args:
            chat_id: Chat/session identifier
            
        Returns:
            List of document metadata
        """
        try:
            prefix = f"wafr/{chat_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            documents = []
            for obj in response.get('Contents', []):
                # Get object metadata
                try:
                    head_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    metadata = head_response.get('Metadata', {})
                    
                    doc_info = {
                        "s3_key": obj['Key'],
                        "filename": metadata.get('original-filename', os.path.basename(obj['Key'])),
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "document_type": metadata.get('document-type', 'unknown'),
                        "file_type": metadata.get('file-type', 'unknown'),
                        "presigned_url": self.generate_presigned_url(obj['Key'])
                    }
                    
                    documents.append(doc_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {obj['Key']}: {e}")
                    continue
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list chat documents: {e}")
            return []
    
    def delete_document(self, s3_key: str) -> bool:
        """
        Delete document from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Success status
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Document deleted successfully: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return os.path.splitext(filename)[1].lower()
    
    def _get_content_type(self, file_type: Optional[FileType]) -> str:
        """Get MIME content type for file type."""
        content_type_map = {
            FileType.PDF: "application/pdf",
            FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            FileType.PNG: "image/png",
            FileType.JPG: "image/jpeg",
            FileType.JPEG: "image/jpeg",
            FileType.GIF: "image/gif",
            FileType.WEBP: "image/webp",
            FileType.CSV: "text/csv"
        }
        return content_type_map.get(file_type, "application/octet-stream")
