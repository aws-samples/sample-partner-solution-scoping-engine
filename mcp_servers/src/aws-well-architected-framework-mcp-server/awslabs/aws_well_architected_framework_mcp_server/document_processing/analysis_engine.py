"""Document analysis engine for WAFR assessments"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from dataclasses import dataclass
import uuid

from .bedrock_client import ClaudeBedrockClient, DocumentValidator
from ..core.logger import setup_logger
from ..core.error_handler import DocumentProcessingError, handle_graceful_degradation
from ..models.assessment import DocumentInfo, AWSService
from ..consts import get_aws_region

# Import validation modules (Universal Validation Framework)
from ..core.validation_integration import ValidationIntegration, validation_integration

# Import filtering functions for cleaning nested extracted_data fields
from ..template_engine import _filter_valid_services

logger = setup_logger(__name__)


@dataclass
class S3AccessError(Exception):
    """Specific error for S3 access issues"""
    error_code: str
    bucket: str
    key: Optional[str]
    diagnostic_info: Dict[str, Any]
    recommendations: List[str]


@dataclass
class DocumentAccessDiagnostics:
    """Comprehensive diagnostics for document access issues"""
    document_url: str
    access_attempted: datetime
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    s3_diagnostics: Optional[Dict[str, Any]]
    credential_info: Dict[str, Any]
    recommendations: List[str]


class EnhancedS3DocumentLoader:
    """Enhanced S3 document loader with comprehensive error handling and diagnostics"""
    
    def __init__(self, region_name: str = None):
        self.region_name = region_name or get_aws_region()
        self.logger = logging.getLogger(__name__)
        self._s3_client = None
        self._credentials_validated = False
    
    @property
    def s3_client(self):
        """Lazy-loaded S3 client with credential validation"""
        if self._s3_client is None:
            self._s3_client = self._create_s3_client()
        return self._s3_client
    
    def _create_s3_client(self):
        """Create S3 client with proper configuration"""
        try:
            import boto3
            from botocore.config import Config
            
            # Configure with retry and timeout settings
            config = Config(
                region_name=self.region_name,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                read_timeout=60,
                connect_timeout=10
            )
            
            # Create client (uses default credential chain)
            client = boto3.client('s3', config=config)
            
            # Validate credentials by listing buckets
            try:
                client.list_buckets()
                self._credentials_validated = True
                self.logger.info("✅ S3 credentials validated successfully")
            except Exception as e:
                self.logger.error(f"❌ S3 credential validation failed: {e}")
                self._credentials_validated = False
            
            return client
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create S3 client: {e}")
            raise DocumentProcessingError(f"S3 client initialization failed: {e}")
    
    async def load_document_with_diagnostics(self, s3_url: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Load document from S3 with comprehensive diagnostics
        
        Returns:
            Tuple of (document_content, diagnostic_info)
        """
        diagnostic_info = {
            'url': s3_url,
            'credentials_valid': self._credentials_validated,
            'bucket': None,
            'key': None,
            'version_id': None,
            'object_exists': False,
            'access_granted': False,
            'content_length': 0,
            'error_details': None
        }
        
        try:
            # Parse S3 URL - handle both s3:// and https:// formats with version ID support
            from urllib.parse import urlparse, parse_qs, unquote
            version_id = None
            
            if s3_url.startswith('s3://'):
                # Format: s3://bucket/key?versionId=xxx
                # Use urlparse for robust parsing of query parameters
                # Note: urlparse treats s3:// URLs with bucket as path, not netloc
                # So we need to handle it specially
                
                s3_path = s3_url[5:]  # Remove 's3://'
                
                # Split path and query string properly
                if '?' in s3_path:
                    path_part, query_string = s3_path.split('?', 1)
                    # Parse query parameters
                    query_params = parse_qs(query_string)
                    # Get versionId (parse_qs returns lists, so get first value)
                    if 'versionId' in query_params:
                        version_id = unquote(query_params['versionId'][0])
                    s3_path = path_part
                
                if '/' not in s3_path:
                    raise DocumentProcessingError(f"Invalid S3 URL format, missing key: {s3_url}")
                bucket, key = s3_path.split('/', 1)
            elif 'amazonaws.com' in s3_url:
                # Format: https://bucket.s3.amazonaws.com/key or https://s3.amazonaws.com/bucket/key
                from urllib.parse import urlparse
                parsed = urlparse(s3_url)
                
                if parsed.netloc == 's3.amazonaws.com':
                    # Format: https://s3.amazonaws.com/bucket/key
                    path_parts = parsed.path.strip('/').split('/')
                    if len(path_parts) < 2:
                        raise DocumentProcessingError(f"Invalid S3 URL format, missing bucket or key: {s3_url}")
                    bucket = path_parts[0]
                    key = '/'.join(path_parts[1:])
                elif '.s3.amazonaws.com' in parsed.netloc:
                    # Format: https://bucket.s3.amazonaws.com/key
                    bucket = parsed.netloc.split('.s3.amazonaws.com')[0]
                    key = parsed.path.strip('/')
                    if not key:
                        raise DocumentProcessingError(f"Invalid S3 URL format, missing key: {s3_url}")
                elif parsed.netloc.endswith('.amazonaws.com') and 's3' in parsed.netloc:
                    # Format: https://bucket.s3.region.amazonaws.com/key
                    bucket = parsed.netloc.split('.s3.')[0]
                    key = parsed.path.strip('/')
                    if not key:
                        raise DocumentProcessingError(f"Invalid S3 URL format, missing key: {s3_url}")
                else:
                    raise DocumentProcessingError(f"Unrecognized S3 URL format: {s3_url}")
            else:
                raise DocumentProcessingError(f"Invalid S3 URL format: {s3_url}")
            
            # Update diagnostic info
            diagnostic_info['bucket'] = bucket
            diagnostic_info['key'] = key
            diagnostic_info['version_id'] = version_id
            
            self.logger.info(f"🔍 Loading document from S3: bucket={bucket}, key={key}, version_id={version_id}")
            
            # Track if we're using versionId (may fallback if s3:GetObjectVersion denied)
            used_version_id = version_id
            
            # Check if object exists
            try:
                from botocore.exceptions import ClientError
                # Include version_id in head_object call if available
                head_params = {'Bucket': bucket, 'Key': key}
                if version_id:
                    head_params['VersionId'] = version_id
                
                try:
                    head_response = self.s3_client.head_object(**head_params)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    # If 403/AccessDenied with versionId, retry without it (s3:GetObjectVersion may not be allowed)
                    if version_id and error_code in ('403', 'AccessDenied', 'Forbidden'):
                        self.logger.warning(
                            f"⚠️ s3:GetObjectVersion denied for {key}, falling back to latest version"
                        )
                        head_params = {'Bucket': bucket, 'Key': key}
                        head_response = self.s3_client.head_object(**head_params)
                        used_version_id = None  # Mark that we're not using versionId
                        diagnostic_info['version_id_fallback'] = True
                    else:
                        raise
                
                diagnostic_info['object_exists'] = True
                diagnostic_info['content_length'] = head_response.get('ContentLength', 0)
                self.logger.info(f"✅ S3 object exists: {diagnostic_info['content_length']} bytes")
            except Exception as e:
                from botocore.exceptions import ClientError
                if isinstance(e, ClientError):
                    if e.response['Error']['Code'] == '404':
                        diagnostic_info['error_details'] = f"S3 object not found: {s3_url}"
                        raise DocumentProcessingError(f"S3 object not found: {s3_url}")
                    elif e.response['Error']['Code'] in ('Forbidden', '403', 'AccessDenied'):
                        diagnostic_info['error_details'] = f"Access denied to S3 object: {s3_url}"
                        raise DocumentProcessingError(f"Access denied to S3 object: {s3_url}")
                    else:
                        diagnostic_info['error_details'] = f"S3 head_object error: {e}"
                        raise DocumentProcessingError(f"S3 error checking object: {e}")
                else:
                    diagnostic_info['error_details'] = f"S3 head_object error: {e}"
                    raise DocumentProcessingError(f"S3 error checking object: {e}")
            
            # Download object
            try:
                from botocore.exceptions import ClientError
                # Use the version_id that worked in head_object (may be None if fallback occurred)
                get_params = {'Bucket': bucket, 'Key': key}
                if used_version_id:
                    get_params['VersionId'] = used_version_id
                
                response = self.s3_client.get_object(**get_params)
                document_content = response['Body'].read()
                diagnostic_info['access_granted'] = True
                
                self.logger.info(f"✅ Successfully loaded document from S3: {len(document_content)} bytes")
                return document_content, diagnostic_info
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                diagnostic_info['error_details'] = f"S3 get_object error ({error_code}): {e}"
                
                if error_code == 'NoSuchBucket':
                    raise DocumentProcessingError(f"S3 bucket not found: {bucket}")
                elif error_code == 'NoSuchKey':
                    raise DocumentProcessingError(f"S3 object not found: {s3_url}")
                elif error_code == 'AccessDenied':
                    raise DocumentProcessingError(f"Access denied to S3 object: {s3_url}")
                else:
                    raise DocumentProcessingError(f"S3 error ({error_code}): {e}")
                    
        except DocumentProcessingError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            diagnostic_info['error_details'] = f"Unexpected error: {e}"
            self.logger.error(f"❌ Unexpected error loading document from S3: {e}")
            raise DocumentProcessingError(f"Error loading document from S3: {e}")
    
    def generate_diagnostic_report(self, s3_url: str) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report for S3 access issues"""
        from urllib.parse import parse_qs, unquote
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'url': s3_url,
            'credentials_check': self._check_credentials(),
            'bucket_access_check': None,
            'object_access_check': None,
            'recommendations': []
        }
        
        try:
            # Parse URL
            if s3_url.startswith('s3://'):
                s3_path = s3_url[5:]
                
                # Handle version ID query parameter properly
                version_id = None
                if '?' in s3_path:
                    path_part, query_string = s3_path.split('?', 1)
                    query_params = parse_qs(query_string)
                    if 'versionId' in query_params:
                        version_id = unquote(query_params['versionId'][0])
                    s3_path = path_part
                
                if '/' in s3_path:
                    bucket, key = s3_path.split('/', 1)
                    
                    # Check bucket access
                    report['bucket_access_check'] = self._check_bucket_access(bucket)
                    
                    # Check object access
                    report['object_access_check'] = self._check_object_access(bucket, key, version_id)
        
        except Exception as e:
            report['diagnostic_error'] = str(e)
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def get_credential_source_info(self) -> Dict[str, Any]:
        """Get information about current AWS credential source"""
        
        try:
            import boto3
            
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials is None:
                return {
                    'source': 'none',
                    'message': 'No AWS credentials found'
                }
            
            # Determine credential source
            if hasattr(credentials, 'method'):
                source = credentials.method
            else:
                source = 'unknown'
            
            return {
                'source': source,
                'access_key_id': credentials.access_key[:8] + '...' if credentials.access_key else None,
                'message': f'Using credentials from: {source}'
            }
            
        except Exception as e:
            return {
                'source': 'error',
                'message': f'Error checking credentials: {e}'
            }
    
    def _check_credentials(self) -> Dict[str, Any]:
        """Check AWS credentials validity"""
        try:
            import boto3
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            
            return {
                'valid': True,
                'account': identity.get('Account'),
                'user_arn': identity.get('Arn'),
                'user_id': identity.get('UserId')
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _check_bucket_access(self, bucket: str) -> Dict[str, Any]:
        """Check bucket-level access permissions"""
        try:
            # Try to list objects (limited to 1)
            response = self.s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            
            return {
                'accessible': True,
                'exists': True,
                'object_count_sample': response.get('KeyCount', 0)
            }
        except Exception as e:
            from botocore.exceptions import ClientError
            if isinstance(e, ClientError):
                error_code = e.response['Error']['Code']
                return {
                    'accessible': False,
                    'exists': error_code != 'NoSuchBucket',
                    'error_code': error_code,
                    'error_message': str(e)
                }
            else:
                return {
                    'accessible': False,
                    'exists': None,
                    'error': str(e)
                }
    
    def _check_object_access(self, bucket: str, key: str, version_id: str = None) -> Dict[str, Any]:
        """Check object-level access permissions"""
        try:
            from botocore.exceptions import ClientError
            # Try head_object first with version_id if available
            head_params = {'Bucket': bucket, 'Key': key}
            if version_id:
                head_params['VersionId'] = version_id
            
            try:
                head_response = self.s3_client.head_object(**head_params)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                # If 403/AccessDenied with versionId, retry without it
                if version_id and error_code in ('403', 'AccessDenied', 'Forbidden'):
                    self.logger.warning(
                        f"s3:GetObjectVersion denied for {key}, falling back to latest version"
                    )
                    head_params = {'Bucket': bucket, 'Key': key}
                    head_response = self.s3_client.head_object(**head_params)
                else:
                    raise
            
            return {
                'exists': True,
                'accessible': True,
                'size': head_response.get('ContentLength', 0),
                'last_modified': head_response.get('LastModified'),
                'content_type': head_response.get('ContentType')
            }
        except Exception as e:
            from botocore.exceptions import ClientError
            if isinstance(e, ClientError):
                error_code = e.response['Error']['Code']
                return {
                    'exists': error_code != 'NoSuchKey',
                    'accessible': False,
                    'error_code': error_code,
                    'error_message': str(e)
                }
            else:
                return {
                    'exists': None,
                    'accessible': False,
                    'error': str(e)
                }
    
    def _generate_recommendations(self, diagnostic_report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on diagnostic results"""
        
        recommendations = []
        
        # Credential issues
        creds = diagnostic_report.get('credentials_check', {})
        if not creds.get('valid', False):
            recommendations.append(
                "AWS credentials are invalid or not configured. "
                "Ensure the WAFR MCP server has access to valid AWS credentials "
                "through environment variables, IAM roles, or AWS credential files."
            )
        
        # Bucket access issues
        bucket_check = diagnostic_report.get('bucket_access_check', {})
        if bucket_check and not bucket_check.get('accessible', False):
            error_code = bucket_check.get('error_code')
            if error_code == 'NoSuchBucket':
                recommendations.append(
                    "S3 bucket does not exist. Verify the bucket name in the document URL "
                    "matches the actual S3 bucket used by the SERA backend."
                )
            elif error_code == 'AccessDenied':
                recommendations.append(
                    "Access denied to S3 bucket. Ensure the WAFR MCP server's AWS credentials "
                    "have s3:ListBucket and s3:GetObject permissions for the target bucket."
                )
        
        # Object access issues
        object_check = diagnostic_report.get('object_access_check', {})
        if object_check and not object_check.get('accessible', False):
            error_code = object_check.get('error_code')
            if error_code == 'NoSuchKey':
                recommendations.append(
                    "S3 object not found. Verify the document was uploaded successfully "
                    "and the S3 key path matches the expected format."
                )
            elif error_code == 'AccessDenied':
                recommendations.append(
                    "Access denied to S3 object. Ensure the WAFR MCP server's AWS credentials "
                    "have s3:GetObject permission for the specific object."
                )
        
        return recommendations


class AWSCredentialManager:
    """Manages AWS credentials for WAFR MCP server S3 access"""
    
    @staticmethod
    def validate_s3_access(bucket_name: str) -> Dict[str, Any]:
        """Validate S3 access with current credentials"""
        
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client('s3')
            
            # Test bucket access
            s3_client.head_bucket(Bucket=bucket_name)
            
            # Test object listing
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            
            return {
                'valid': True,
                'bucket_accessible': True,
                'message': f'Successfully validated access to bucket: {bucket_name}'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            return {
                'valid': False,
                'bucket_accessible': False,
                'error_code': error_code,
                'message': f'S3 access validation failed: {e}'
            }
        except Exception as e:
            return {
                'valid': False,
                'bucket_accessible': False,
                'message': f'Credential validation failed: {e}'
            }


class DocumentAccessErrorHandler:
    """Handles document access errors with detailed diagnostics and recovery"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_s3_access_error(self, error: Exception, s3_url: str) -> Dict[str, Any]:
        """Handle S3 access errors with detailed diagnostics"""
        
        try:
            # Generate diagnostic report
            s3_loader = EnhancedS3DocumentLoader()
            diagnostic_report = s3_loader.generate_diagnostic_report(s3_url)
            
            # Create user-friendly error response
            error_response = {
                'success': False,
                'error_type': 'document_access_failure',
                'error_message': self._create_user_friendly_message(error, diagnostic_report),
                'diagnostic_report': diagnostic_report,
                'fallback_available': True,
                'recovery_actions': self._get_recovery_actions(diagnostic_report)
            }
            
            self.logger.error(f"❌ S3 document access failed: {error}")
            self.logger.info(f"🔍 Diagnostic report generated for: {s3_url}")
            
            return error_response
            
        except Exception as diagnostic_error:
            self.logger.error(f"❌ Error generating diagnostics: {diagnostic_error}")
            
            return {
                'success': False,
                'error_type': 'document_access_failure',
                'error_message': f'Failed to access uploaded document: {str(error)}',
                'fallback_available': True,
                'recovery_actions': [
                    'Verify document was uploaded successfully',
                    'Check AWS credentials and permissions',
                    'Try re-uploading the document'
                ]
            }
    
    def _create_user_friendly_message(self, error: Exception, diagnostic_report: Dict[str, Any]) -> str:
        """Create user-friendly error message based on diagnostics"""
        
        creds = diagnostic_report.get('credentials_check', {})
        bucket_check = diagnostic_report.get('bucket_access_check', {})
        object_check = diagnostic_report.get('object_access_check', {})
        
        if not creds.get('valid', False):
            return (
                "Unable to access your uploaded document due to AWS credential issues. "
                "The system administrator needs to configure proper AWS access for document analysis."
            )
        
        if bucket_check and not bucket_check.get('accessible', False):
            return (
                "Unable to access the document storage bucket. "
                "This appears to be a configuration issue that requires administrator attention."
            )
        
        if object_check and not object_check.get('exists', True):
            return (
                "Your uploaded document could not be found in storage. "
                "Please try uploading the document again."
            )
        
        if object_check and not object_check.get('accessible', False):
            return (
                "Unable to access your uploaded document due to permission restrictions. "
                "The system administrator needs to review document access permissions."
            )
        
        return (
            "There was an issue accessing your uploaded document. "
            "Please try uploading the document again or contact support if the issue persists."
        )
    
    def _get_recovery_actions(self, diagnostic_report: Dict[str, Any]) -> List[str]:
        """Get specific recovery actions based on diagnostic results"""
        
        actions = []
        
        creds = diagnostic_report.get('credentials_check', {})
        if not creds.get('valid', False):
            actions.extend([
                'Configure AWS credentials for the WAFR MCP server',
                'Ensure IAM permissions include s3:GetObject and s3:ListBucket',
                'Verify AWS region configuration matches S3 bucket region'
            ])
        
        bucket_check = diagnostic_report.get('bucket_access_check', {})
        if bucket_check and not bucket_check.get('accessible', False):
            actions.extend([
                'Verify S3 bucket name configuration',
                'Check bucket-level IAM policies and permissions',
                'Ensure bucket exists in the correct AWS region'
            ])
        
        object_check = diagnostic_report.get('object_access_check', {})
        if object_check and not object_check.get('exists', True):
            actions.extend([
                'Verify document upload completed successfully',
                'Check S3 object key format and naming',
                'Re-upload the document if necessary'
            ])
        
        if not actions:
            actions = [
                'Re-upload the document',
                'Verify document format is supported (PDF, PNG, JPEG, TXT)',
                'Check document size is within limits',
                'Contact administrator if issue persists'
            ]
        
        return actions


class DocumentAnalysisEngine:
    """
    Comprehensive document analysis engine for WAFR assessments.
    
    Processes various document types using Claude's multimodal capabilities
    to extract AWS services, architectural patterns, and assessment-relevant information.
    """
    
    def __init__(self, region_name: str = None):
        """Initialize document analysis engine."""
        from ..consts import get_aws_region
        region = region_name or get_aws_region()
        self.claude_client = ClaudeBedrockClient(region)
        self.validator = DocumentValidator()
        self.s3_loader = EnhancedS3DocumentLoader(region)
        self.logger = logging.getLogger(__name__)
        
    async def analyze_documents(
        self,
        documents: List[str],
        document_types: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze multiple documents for WAFR assessment.
        
        Args:
            documents: List of document paths/URLs
            document_types: List of document types
            
        Returns:
            Comprehensive analysis results
        """
        try:
            logger.info(f"Starting analysis of {len(documents)} documents")
            
            # Handle empty documents case
            if not documents:
                logger.warning("❌ No documents provided for analysis")
                return {
                    "success": False,
                    "error": "No documents provided for analysis",
                    "message": "Please upload architecture documents (PDFs, images, or text files) to proceed with the WAFR assessment.",
                    "identified_services": [],
                    "architecture_patterns": [],
                    "security_findings": [],
                    "performance_insights": [],
                    "cost_optimization_opportunities": [],
                    "reliability_concerns": [],
                    "operational_recommendations": [],
                    "sustainability_suggestions": [],
                    "document_summaries": [],
                    "confidence_scores": {},
                    "processing_metadata": {
                        "total_documents": 0,
                        "successful_analyses": 0,
                        "failed_analyses": 0,
                        "processing_time": 0.0,
                        "status": "no_documents_provided"
                    }
                }
            
            # Validate inputs for non-empty documents
            if len(documents) != len(document_types):
                raise DocumentProcessingError("Documents and types lists must have same length")
            
            # Process documents concurrently
            analysis_tasks = []
            for doc_path, doc_type in zip(documents, document_types):
                task = self._analyze_single_document(doc_path, doc_type)
                analysis_tasks.append(task)
            
            # Wait for all analyses to complete
            document_analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Combine results
            combined_analysis = await self._combine_document_analyses(
                document_analyses, documents, document_types
            )
            
            logger.info("Document analysis completed successfully")
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            return handle_graceful_degradation(e, "document_analysis", {
                "success": False,
                "error": str(e),
                "partial_results": {}
            })
    
    async def _analyze_single_document(
        self,
        document_path: str,
        document_type: str
    ) -> Dict[str, Any]:
        """Analyze a single document with optimized performance."""
        
        document_id = str(uuid.uuid4())
        logger.info(f"🔍 Starting analysis for document {document_id}: {document_path}")
        
        try:
            # Load document content
            logger.info(f"🔍 Loading document content from: {document_path}")
            document_content = await self._load_document(document_path)
            logger.info(f"✅ Document loaded successfully: {len(document_content)} bytes")
            
            # Quick validation - only check if content exists
            if not document_content or len(document_content) < 100:
                logger.warning(f"⚠️ Document appears empty or too small")
                raise DocumentProcessingError("Document is empty or corrupted")
            
            # Analyze with Claude (skip extensive validation for performance)
            logger.info(f"🔍 Calling Claude Bedrock for document analysis...")
            claude_analysis = await self.claude_client.analyze_document(
                document_content, document_type
            )
            logger.info(f"✅ Claude analysis completed successfully")
            
            # Quick extraction (simplified for performance)
            extracted_services = await self._extract_aws_services(claude_analysis)
            architectural_patterns = await self._extract_architectural_patterns(claude_analysis)
            
            # === PHASE 2 & 3: Evidence-Based Validation ===
            # Apply Universal Validation Framework to eliminate false positives
            logger.info(f"🔍 Applying evidence-based validation (UNIV-001 to UNIV-010)...")
            
            # Get document text for validation
            if isinstance(document_content, bytes):
                document_text = document_content.decode('utf-8', errors='ignore')
            else:
                document_text = str(document_content)
            
            # Run validation integration
            try:
                enhanced_result = validation_integration.enhance_analysis(
                    document_text=document_text,
                    claude_services=extracted_services,
                    claude_patterns=architectural_patterns
                )
                
                # Use validated results
                validated_services = enhanced_result.final_services
                validated_patterns = enhanced_result.final_patterns
                
                # Log validation summary
                summary = enhanced_result.validation_summary
                logger.info(f"✅ Validation complete: {summary.get('validated_count', 0)} validated, "
                           f"{summary.get('rejected_count', 0)} rejected (false positives eliminated)")
                
                # Store enhanced features in extracted_data
                enhanced_extracted_data = claude_analysis.get("extracted_data", {})
                enhanced_extracted_data['security_features'] = enhanced_result.security_features
                enhanced_extracted_data['reliability_features'] = enhanced_result.reliability_features
                enhanced_extracted_data['sustainability_features'] = enhanced_result.sustainability_features
                enhanced_extracted_data['validation_summary'] = summary
                enhanced_extracted_data['rejected_services'] = enhanced_result.rejected_services
                
                # Update confidence scores based on validation
                confidence_scores = enhanced_result.confidence_adjustments
                confidence_scores['overall'] = claude_analysis.get("confidence_score", 0.8)
                confidence_scores['validation_applied'] = True
                
            except Exception as validation_error:
                logger.warning(f"⚠️ Validation failed, using Claude results: {validation_error}")
                validated_services = extracted_services
                validated_patterns = architectural_patterns
                enhanced_extracted_data = claude_analysis.get("extracted_data", {})
                confidence_scores = {"overall": claude_analysis.get("confidence_score", 0.8)}
            
            # === CRITICAL FIX: Filter nested extracted_data fields to remove markdown/meta-text pollution ===
            # These fields can contain polluted entries like "Encryption:**", "Evidence type: TEXT_MENTION", etc.
            nested_fields_to_filter = [
                'security_boundaries',
                'architectural_patterns',
                'cost_elements',
                'operational_elements',
                'performance_elements',
                'compliance_indicators',
                'data_flows',
                'reliability_features',
                'sustainability_features',
                'security_features',
                'aws_services',
                'third_party_services'
            ]
            
            for field in nested_fields_to_filter:
                if field in enhanced_extracted_data and isinstance(enhanced_extracted_data[field], list):
                    original_count = len(enhanced_extracted_data[field])
                    enhanced_extracted_data[field] = _filter_valid_services(enhanced_extracted_data[field])
                    filtered_count = len(enhanced_extracted_data[field])
                    if original_count != filtered_count:
                        logger.info(f"🧹 NESTED_FILTER: {field}: {original_count} -> {filtered_count} items (removed {original_count - filtered_count} polluted entries)")
            
            # === CRITICAL FIX: Filter top-level validated_services and validated_patterns ===
            # These can contain polluted entries like "Multi-Tier Application:**" or sentence-like descriptions
            original_services_count = len(validated_services)
            validated_services = _filter_valid_services(validated_services)
            if original_services_count != len(validated_services):
                logger.info(f"🧹 TOP_LEVEL_FILTER: identified_services: {original_services_count} -> {len(validated_services)} items")
            
            original_patterns_count = len(validated_patterns)
            validated_patterns = _filter_valid_services(validated_patterns)
            if original_patterns_count != len(validated_patterns):
                logger.info(f"🧹 TOP_LEVEL_FILTER: architectural_patterns: {original_patterns_count} -> {len(validated_patterns)} items")
            
            # Create simplified document info with validated results
            logger.info(f"✅ Analysis completed for document {document_id}")
            document_info = DocumentInfo(
                document_id=document_id,
                filename=document_path.split('/')[-1],
                file_type=document_type,
                file_size=len(document_content),
                upload_timestamp=datetime.utcnow(),
                processing_status="completed",
                extracted_data=enhanced_extracted_data,
                text_analysis=claude_analysis.get("raw_analysis"),
                identified_services=validated_services,
                architectural_patterns=validated_patterns,
                configuration_data=enhanced_extracted_data,
                processing_errors=[],
                confidence_scores=confidence_scores
            )
            logger.info(f"✅ [STEP 7/7] DocumentInfo created: services={len(document_info.identified_services)}, patterns={len(document_info.architectural_patterns)}")
            
            logger.info(f"🎉 Document analysis completed successfully for {document_id}")
            return {
                "document_info": document_info,
                "analysis_result": claude_analysis,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing document {document_path}: {e}", exc_info=True)
            logger.error(f"❌ Exception type: {type(e).__name__}")
            logger.error(f"❌ Exception details: {str(e)}")
            return {
                "document_info": None,
                "analysis_result": None,
                "success": False,
                "error": str(e)
            }
    
    async def _load_document(self, document_path: str) -> bytes:
        """Enhanced document loading with comprehensive error handling"""
        
        try:
            # Check for S3 URLs first (both s3:// and https:// formats)
            if document_path.startswith('s3://') or 'amazonaws.com' in document_path:
                # Use enhanced S3 loader for both s3:// and HTTPS S3 URLs
                document_content, diagnostic_info = await self.s3_loader.load_document_with_diagnostics(document_path)
                
                # Log diagnostic information
                self.logger.info(f"📊 S3 Access Diagnostics: {diagnostic_info}")
                
                return document_content
            elif document_path.startswith(('http://', 'https://')):
                # Handle non-S3 HTTP/HTTPS URLs
                return await self._load_document_from_url(document_path)
            else:
                # Handle local file paths
                with open(document_path, 'rb') as f:
                    return f.read()
                    
        except DocumentProcessingError as e:
            # Generate diagnostic report for S3 errors
            if document_path.startswith('s3://'):
                diagnostic_report = self.s3_loader.generate_diagnostic_report(document_path)
                self.logger.error(f"🔍 S3 Diagnostic Report: {json.dumps(diagnostic_report, indent=2, default=str)}")
                
                # Enhance error message with recommendations
                recommendations = diagnostic_report.get('recommendations', [])
                if recommendations:
                    enhanced_error = f"{str(e)}\n\nRecommendations:\n" + "\n".join(f"• {rec}" for rec in recommendations)
                    raise DocumentProcessingError(enhanced_error)
            
            raise
        except FileNotFoundError:
            raise DocumentProcessingError(f"Document not found: {document_path}")
        except Exception as e:
            raise DocumentProcessingError(f"Error loading document: {e}")
    

    
    async def _load_document_from_url(self, url: str) -> bytes:
        """Load document from HTTP/HTTPS URL."""
        
        try:
            import aiohttp
            
            logger.info(f"Loading document from URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise DocumentProcessingError(
                            f"HTTP error {response.status} loading document from {url}"
                        )
                    
                    document_content = await response.read()
                    logger.info(f"Successfully loaded document from URL: {len(document_content)} bytes")
                    return document_content
                    
        except ImportError:
            raise DocumentProcessingError(
                "aiohttp not available for URL loading. Please install aiohttp or use local files."
            )
        except Exception as e:
            raise DocumentProcessingError(f"Error loading document from URL: {e}")
    
    def _deduplicate_services(self, services: List[str]) -> List[str]:
        """
        Deduplicate services by normalizing names and removing duplicates.
        
        Handles cases like:
        - "ECS" and "**Amazon ECS** (Confidence: 95%)" -> keeps "**Amazon ECS** (Confidence: 95%)"
        - "Lambda" and "AWS Lambda" -> keeps one
        
        Returns:
            Deduplicated list of services, preferring formatted versions
        """
        import re
        
        # Map normalized names to their best representation
        service_map = {}  # normalized_name -> (original_name, has_confidence)
        
        for service in services:
            if not service or not service.strip():
                continue
            
            # Extract the core service name for comparison
            service_lower = service.lower().strip()
            
            # Remove markdown formatting for comparison
            core_name = re.sub(r'\*\*([^*]+)\*\*', r'\1', service_lower)
            
            # Remove confidence scores for comparison
            core_name = re.sub(r'\s*\(confidence:?\s*\d+%?\)', '', core_name)
            
            # Remove common prefixes
            core_name = core_name.replace('amazon ', '').replace('aws ', '').strip()
            
            # Remove descriptions after dash
            core_name = core_name.split(' - ')[0].strip()
            core_name = core_name.split(':')[0].strip()
            
            # Check if this service has confidence info (prefer these)
            has_confidence = 'confidence' in service_lower
            has_formatting = '**' in service
            
            # Determine priority: formatted with confidence > formatted > plain
            priority = (has_confidence, has_formatting, len(service))
            
            if core_name not in service_map:
                service_map[core_name] = (service, priority)
            else:
                existing_service, existing_priority = service_map[core_name]
                # Keep the one with higher priority
                if priority > existing_priority:
                    service_map[core_name] = (service, priority)
        
        # Return deduplicated services
        return [service for service, _ in service_map.values()]
    
    async def _extract_aws_services(self, claude_analysis: Dict[str, Any]) -> List[str]:
        """Extract AWS services from Claude analysis."""
        
        services = []
        extracted_data = claude_analysis.get("extracted_data", {})
        
        # Extract from structured data
        aws_services = extracted_data.get("aws_services", [])
        for service_item in aws_services:
            if isinstance(service_item, dict):
                service_name = service_item.get("item", "")
            else:
                service_name = str(service_item)
            
            # Clean and validate service name
            service_name = service_name.strip()
            if service_name and self._is_valid_aws_service(service_name):
                services.append(service_name)
        
        # Also extract from raw analysis text
        raw_analysis = claude_analysis.get("raw_analysis", "")
        additional_services = await self._extract_services_from_text(raw_analysis)
        services.extend(additional_services)
        
        # Remove duplicates using intelligent deduplication
        return self._deduplicate_services(services)
    
    async def _extract_architectural_patterns(self, claude_analysis: Dict[str, Any]) -> List[str]:
        """Extract architectural patterns from Claude analysis."""
        
        patterns = []
        extracted_data = claude_analysis.get("extracted_data", {})
        
        # Extract from structured data
        arch_patterns = extracted_data.get("architectural_patterns", [])
        for pattern_item in arch_patterns:
            if isinstance(pattern_item, dict):
                pattern_name = pattern_item.get("item", "")
            else:
                pattern_name = str(pattern_item)
            
            pattern_name = pattern_name.strip()
            if pattern_name:
                patterns.append(pattern_name)
        
        return patterns
    
    def _is_valid_aws_service(self, service_name: str) -> bool:
        """Validate if service name is a known AWS service."""
        
        # Comprehensive AWS services list (expanded for better detection)
        aws_services = {
            # Compute
            'ec2', 'lambda', 'ecs', 'eks', 'fargate', 'batch', 'lightsail',
            'elastic beanstalk', 'app runner', 'outposts',
            
            # Storage
            's3', 'ebs', 'efs', 'fsx', 'storage gateway', 'backup',
            
            # Database
            'rds', 'dynamodb', 'redshift', 'neptune', 'documentdb', 'keyspaces',
            'timestream', 'qldb', 'memorydb', 'elasticache',
            
            # Networking
            'vpc', 'cloudfront', 'route53', 'elb', 'alb', 'nlb', 'api gateway',
            'direct connect', 'transit gateway', 'nat gateway', 'internet gateway',
            
            # Security
            'iam', 'cognito', 'secrets manager', 'parameter store', 'kms', 'waf',
            'shield', 'guardduty', 'security hub', 'inspector', 'macie', 'certificate manager',
            
            # Analytics
            'kinesis', 'athena', 'glue', 'emr', 'quicksight', 'data pipeline',
            'elasticsearch', 'opensearch', 'msk', 'kinesis analytics',
            
            # Application Integration
            'sns', 'sqs', 'eventbridge', 'step functions', 'swf', 'mq', 'appflow',
            
            # Management & Governance
            'cloudformation', 'cloudwatch', 'cloudtrail', 'config', 'systems manager',
            'control tower', 'organizations', 'trusted advisor', 'well-architected tool',
            
            # Developer Tools
            'codecommit', 'codebuild', 'codedeploy', 'codepipeline', 'codestar',
            'cloud9', 'x-ray', 'amplify', 'cdk',
            
            # Mobile & Web
            'amplify', 'appsync', 'device farm', 'pinpoint'
        }
        
        service_lower = service_name.lower().strip()
        
        # Direct match
        if service_lower in aws_services:
            return True
            
        # Partial match for compound names
        return any(aws_service in service_lower for aws_service in aws_services)
    
    async def _extract_services_from_text(self, text: str) -> List[str]:
        """Extract AWS services mentioned in text with enhanced patterns."""
        
        services = []
        text_lower = text.lower()
        
        # Enhanced AWS service patterns including common variations
        service_patterns = [
            # Compute
            'amazon ec2', 'ec2', 'elastic compute cloud',
            'aws lambda', 'lambda', 'lambda function', 'serverless function',
            'ecs', 'elastic container service', 'fargate',
            
            # Storage
            'amazon s3', 's3', 'simple storage service', 'object storage', 'bucket',
            
            # Database
            'amazon rds', 'rds', 'relational database service',
            'dynamodb', 'amazon dynamodb', 'nosql database', 'document database',
            
            # Networking & Content Delivery
            'vpc', 'virtual private cloud',
            'cloudfront', 'amazon cloudfront', 'cdn', 'content delivery network',
            'api gateway', 'amazon api gateway', 'rest api', 'http api',
            'elastic load balancer', 'elb', 'application load balancer', 'alb',
            'route 53', 'route53', 'amazon route 53',
            
            # Security & Identity
            'iam', 'identity and access management',
            'cognito', 'amazon cognito', 'user pool', 'identity pool', 'authentication',
            'kms', 'key management service',
            
            # Application Integration
            'sns', 'simple notification service', 'notification service',
            'sqs', 'simple queue service', 'message queue',
            'eventbridge', 'event bridge', 'cloudwatch events',
            'step functions', 'state machine', 'workflow',
            
            # Management & Governance
            'cloudformation', 'aws cloudformation', 'infrastructure template',
            'cloudwatch', 'amazon cloudwatch', 'monitoring', 'metrics', 'logs',
            'x-ray', 'xray', 'tracing', 'distributed tracing',
            
            # Developer Tools
            'amplify', 'aws amplify', 'frontend hosting',
            'cdk', 'cloud development kit', 'infrastructure as code'
        ]
        
        for pattern in service_patterns:
            if pattern in text_lower:
                # Map pattern to standard service name
                service_name = self._normalize_service_name(pattern)
                if service_name:
                    services.append(service_name)
        
        return list(set(services))
    
    def _normalize_service_name(self, pattern: str) -> str:
        """Normalize service pattern to standard AWS service name."""
        
        normalization_map = {
            # Compute
            'amazon ec2': 'EC2',
            'ec2': 'EC2',
            'elastic compute cloud': 'EC2',
            'aws lambda': 'Lambda',
            'lambda': 'Lambda',
            'lambda function': 'Lambda',
            'serverless function': 'Lambda',
            'ecs': 'ECS',
            'elastic container service': 'ECS',
            'fargate': 'Fargate',
            
            # Storage
            'amazon s3': 'S3',
            's3': 'S3',
            'simple storage service': 'S3',
            'object storage': 'S3',
            'bucket': 'S3',
            
            # Database
            'amazon rds': 'RDS',
            'rds': 'RDS',
            'relational database service': 'RDS',
            'dynamodb': 'DynamoDB',
            'amazon dynamodb': 'DynamoDB',
            'nosql database': 'DynamoDB',
            'document database': 'DynamoDB',
            
            # Networking & Content Delivery
            'vpc': 'VPC',
            'virtual private cloud': 'VPC',
            'cloudfront': 'CloudFront',
            'amazon cloudfront': 'CloudFront',
            'cdn': 'CloudFront',
            'content delivery network': 'CloudFront',
            'api gateway': 'API Gateway',
            'amazon api gateway': 'API Gateway',
            'rest api': 'API Gateway',
            'http api': 'API Gateway',
            'elastic load balancer': 'ELB',
            'elb': 'ELB',
            'application load balancer': 'ALB',
            'alb': 'ALB',
            'route 53': 'Route 53',
            'route53': 'Route 53',
            'amazon route 53': 'Route 53',
            
            # Security & Identity
            'iam': 'IAM',
            'identity and access management': 'IAM',
            'cognito': 'Cognito',
            'amazon cognito': 'Cognito',
            'user pool': 'Cognito',
            'identity pool': 'Cognito',
            'authentication': 'Cognito',
            'kms': 'KMS',
            'key management service': 'KMS',
            
            # Application Integration
            'sns': 'SNS',
            'simple notification service': 'SNS',
            'notification service': 'SNS',
            'sqs': 'SQS',
            'simple queue service': 'SQS',
            'message queue': 'SQS',
            'eventbridge': 'EventBridge',
            'event bridge': 'EventBridge',
            'cloudwatch events': 'EventBridge',
            'step functions': 'Step Functions',
            'state machine': 'Step Functions',
            'workflow': 'Step Functions',
            
            # Management & Governance
            'cloudformation': 'CloudFormation',
            'aws cloudformation': 'CloudFormation',
            'infrastructure template': 'CloudFormation',
            'cloudwatch': 'CloudWatch',
            'amazon cloudwatch': 'CloudWatch',
            'monitoring': 'CloudWatch',
            'metrics': 'CloudWatch',
            'logs': 'CloudWatch',
            'x-ray': 'X-Ray',
            'xray': 'X-Ray',
            'tracing': 'X-Ray',
            'distributed tracing': 'X-Ray',
            
            # Developer Tools
            'amplify': 'Amplify',
            'aws amplify': 'Amplify',
            'frontend hosting': 'Amplify',
            'cdk': 'CDK',
            'cloud development kit': 'CDK',
            'infrastructure as code': 'CDK'
        }
        
        return normalization_map.get(pattern.lower(), pattern.title())
    
    async def _combine_document_analyses(
        self,
        document_analyses: List[Any],
        documents: List[str],
        document_types: List[str]
    ) -> Dict[str, Any]:
        """Combine multiple document analyses into comprehensive result."""
        
        logger.info(f"🔄 Combining {len(document_analyses)} document analyses...")
        
        combined_result = {
            "success": True,
            "total_documents": len(documents),
            "processed_documents": 0,
            "failed_documents": 0,
            "document_analyses": [],
            "identified_services": [],
            "architectural_patterns": [],
            "combined_insights": {},
            "processing_errors": [],
            "raw_analysis": "",  # FIX: Aggregate raw analysis text for capability detection
            "document_summaries": []  # FIX: Include document summaries for capability detection
        }
        
        all_services = set()
        all_patterns = set()
        all_raw_analysis_parts = []  # FIX: Collect raw analysis from all documents
        
        for i, analysis in enumerate(document_analyses):
            logger.info(f"📄 Processing analysis {i+1}/{len(document_analyses)} for document: {documents[i]}")
            logger.debug(f"📊 Analysis type: {type(analysis)}, is Exception: {isinstance(analysis, Exception)}")
            
            if isinstance(analysis, Exception):
                # Handle failed analysis
                logger.error(f"❌ Document {i+1} failed with exception: {analysis}")
                combined_result["failed_documents"] += 1
                combined_result["processing_errors"].append({
                    "document": documents[i],
                    "error": str(analysis)
                })
                continue
            
            logger.debug(f"📊 Analysis success status: {analysis.get('success', False)}")
            
            if analysis.get("success", False):
                combined_result["processed_documents"] += 1
                combined_result["document_analyses"].append(analysis)
                
                # Collect services and patterns
                doc_info = analysis.get("document_info")
                logger.debug(f"📊 doc_info type: {type(doc_info)}, is None: {doc_info is None}")
                
                # FIX: Collect raw_analysis text for capability detection
                analysis_result = analysis.get("analysis_result", {})
                if analysis_result:
                    raw_text = analysis_result.get("raw_analysis", "")
                    if raw_text:
                        all_raw_analysis_parts.append(raw_text)
                        logger.debug(f"📊 Collected raw_analysis: {len(raw_text)} chars")
                    
                    # Also collect extracted_data text for comprehensive capability detection
                    extracted_data = analysis_result.get("extracted_data", {})
                    if extracted_data:
                        # Collect all text fields from extracted_data
                        for key in ['aws_services', 'architectural_patterns', 'security_boundaries', 
                                   'cost_elements', 'operational_elements', 'performance_elements',
                                   'compliance_indicators', 'security_features', 'reliability_features',
                                   'sustainability_features']:
                            items = extracted_data.get(key, [])
                            for item in items:
                                if isinstance(item, dict):
                                    item_text = item.get('item', '') or item.get('name', '') or str(item)
                                    all_raw_analysis_parts.append(item_text)
                                elif isinstance(item, str):
                                    all_raw_analysis_parts.append(item)
                
                if doc_info:
                    logger.debug(f"📊 doc_info.identified_services type: {type(doc_info.identified_services)}")
                    logger.debug(f"📊 doc_info.identified_services value: {doc_info.identified_services}")
                    logger.debug(f"📊 doc_info.architectural_patterns type: {type(doc_info.architectural_patterns)}")
                    logger.debug(f"📊 doc_info.architectural_patterns value: {doc_info.architectural_patterns}")
                    
                    services_before = len(all_services)
                    patterns_before = len(all_patterns)
                    
                    all_services.update(doc_info.identified_services or [])
                    all_patterns.update(doc_info.architectural_patterns or [])
                    
                    # FIX: Also collect text_analysis from doc_info
                    if hasattr(doc_info, 'text_analysis') and doc_info.text_analysis:
                        all_raw_analysis_parts.append(doc_info.text_analysis)
                    
                    logger.info(f"✅ Document {i+1}: Added {len(all_services) - services_before} services, {len(all_patterns) - patterns_before} patterns")
                else:
                    logger.warning(f"⚠️ Document {i+1}: doc_info is None, no services/patterns collected")
            else:
                logger.error(f"❌ Document {i+1} marked as failed: {analysis.get('error', 'Unknown error')}")
                combined_result["failed_documents"] += 1
                combined_result["processing_errors"].append({
                    "document": documents[i],
                    "error": analysis.get("error", "Unknown error")
                })
        
        # FIX: Combine all raw analysis text for capability detection
        combined_result["raw_analysis"] = " ".join(all_raw_analysis_parts)
        logger.info(f"📊 Combined raw_analysis: {len(combined_result['raw_analysis'])} chars for capability detection")
        
        # Set combined results
        combined_result["identified_services"] = list(all_services)
        combined_result["architectural_patterns"] = list(all_patterns)
        
        logger.info(f"📊 Combined results: {len(all_services)} services, {len(all_patterns)} patterns")
        logger.info(f"📊 Services: {list(all_services)[:10]}{'...' if len(all_services) > 10 else ''}")
        logger.info(f"📊 Patterns: {list(all_patterns)[:5]}{'...' if len(all_patterns) > 5 else ''}")
        
        # Generate combined insights
        logger.info(f"🔍 Generating combined insights from {len(combined_result['document_analyses'])} analyses...")
        combined_result["combined_insights"] = await self._generate_combined_insights(
            combined_result["document_analyses"]
        )
        logger.info(f"✅ Combined insights generated")
        
        # Update success status and provide meaningful feedback
        if combined_result["processed_documents"] == 0:
            logger.error(f"❌ FINAL RESULT: No documents processed successfully (failed: {combined_result['failed_documents']})")
            combined_result["success"] = False
            combined_result["error"] = "No documents could be processed successfully"
            combined_result["message"] = "Document analysis failed. Please check that your documents are valid and accessible."
        elif len(all_services) == 0 and len(all_patterns) == 0:
            logger.warning(f"⚠️ FINAL RESULT: Documents processed but no services/patterns extracted (processed: {combined_result['processed_documents']})")
            combined_result["success"] = True  # Processing succeeded but limited extraction
            combined_result["warning"] = "Limited content extraction"
            combined_result["message"] = "Documents were processed but no AWS services or architectural patterns were identified. Consider providing more detailed architecture diagrams or documentation."
        else:
            logger.info(f"✅ FINAL RESULT: Successfully analyzed {combined_result['processed_documents']} documents: {len(all_services)} services, {len(all_patterns)} patterns")
            combined_result["message"] = f"Successfully analyzed {combined_result['processed_documents']} documents and identified {len(all_services)} AWS services and {len(all_patterns)} architectural patterns."
        
        return combined_result
    
    async def _generate_combined_insights(
        self,
        document_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate combined insights from multiple document analyses."""
        
        insights = {
            "architecture_complexity": "medium",
            "security_posture": "unknown",
            "compliance_indicators": [],
            "performance_considerations": [],
            "cost_optimization_opportunities": [],
            "operational_readiness": "unknown"
        }
        
        # Analyze complexity based on number of services and patterns
        total_services = set()
        total_patterns = set()
        
        for analysis in document_analyses:
            doc_info = analysis.get("document_info")
            if doc_info:
                total_services.update(doc_info.identified_services or [])
                total_patterns.update(doc_info.architectural_patterns or [])
        
        # Determine complexity
        service_count = len(total_services)
        if service_count > 10:
            insights["architecture_complexity"] = "high"
        elif service_count > 5:
            insights["architecture_complexity"] = "medium"
        else:
            insights["architecture_complexity"] = "low"
        
        # Extract compliance and other indicators from analyses
        for analysis in document_analyses:
            analysis_result = analysis.get("analysis_result", {})
            extracted_data = analysis_result.get("extracted_data", {})
            
            # Collect compliance indicators
            compliance_items = extracted_data.get("compliance_indicators", [])
            for item in compliance_items:
                if isinstance(item, dict):
                    insights["compliance_indicators"].append(item.get("item", ""))
                else:
                    insights["compliance_indicators"].append(str(item))
            
            # Collect performance considerations
            performance_items = extracted_data.get("performance_elements", [])
            for item in performance_items:
                if isinstance(item, dict):
                    insights["performance_considerations"].append(item.get("item", ""))
                else:
                    insights["performance_considerations"].append(str(item))
            
            # Collect cost optimization opportunities
            cost_items = extracted_data.get("cost_elements", [])
            for item in cost_items:
                if isinstance(item, dict):
                    insights["cost_optimization_opportunities"].append(item.get("item", ""))
                else:
                    insights["cost_optimization_opportunities"].append(str(item))
        
        # Remove duplicates
        insights["compliance_indicators"] = list(set(insights["compliance_indicators"]))
        insights["performance_considerations"] = list(set(insights["performance_considerations"]))
        insights["cost_optimization_opportunities"] = list(set(insights["cost_optimization_opportunities"]))
        
        return insights
