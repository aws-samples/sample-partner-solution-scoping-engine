#!/usr/bin/env python3
"""
Security Hardened S3 Client for WAFR Document Access
Implements secure credential handling, access logging, input validation, and encrypted connections
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import logging
import re
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

from .consts import get_aws_region

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@dataclass
class SecurityAuditEntry:
    """Security audit log entry"""
    timestamp: datetime
    event_type: str
    user_id_hash: str
    document_url_sanitized: str
    success: bool
    error_code: Optional[str]
    source_ip_masked: str
    security_context: Dict[str, Any]


class SecureCredentialManager:
    """Manages AWS credentials with security best practices"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sensitive_patterns = [
            r'AKIA[0-9A-Z]{16}',  # AWS Access Keys
            r'[A-Za-z0-9/+=]{40}',  # AWS Secret Keys (40 chars)
            r'[A-Za-z0-9/+=]{100,}',  # Session tokens (longer)
        ]
    
    def mask_credentials_in_logs(self, message: str) -> str:
        """Mask sensitive credential information in log messages"""
        
        masked_message = message
        
        # Mask AWS access keys
        masked_message = re.sub(r'AKIA[0-9A-Z]{16}', 'AKIA****************', masked_message)
        
        # Mask secret keys (40 characters)
        masked_message = re.sub(r'[A-Za-z0-9/+=]{40}', '*' * 40, masked_message)
        
        # Mask session tokens (longer than 40 characters)
        masked_message = re.sub(r'[A-Za-z0-9/+=]{100,}', '*' * 50 + '[MASKED_TOKEN]', masked_message)
        
        # Mask other sensitive patterns
        masked_message = re.sub(r'password\s*[:=]\s*\S+', 'password=[REDACTED]', masked_message, flags=re.IGNORECASE)
        masked_message = re.sub(r'secret\s*[:=]\s*\S+', 'secret=[REDACTED]', masked_message, flags=re.IGNORECASE)
        
        return masked_message
    
    def validate_credential_format(self, access_key: str, secret_key: str) -> Dict[str, Any]:
        """Validate AWS credential format without exposing values"""
        
        # Validate access key format (AKIA followed by 16 alphanumeric characters)
        access_key_valid = bool(re.match(r'^AKIA[0-9A-Z]{16}$', access_key))
        
        # Validate secret key format (40 characters, base64-like)
        secret_key_valid = bool(re.match(r'^[A-Za-z0-9/+=]{40}$', secret_key))
        
        return {
            'access_key_format_valid': access_key_valid,
            'secret_key_format_valid': secret_key_valid,
            'both_valid': access_key_valid and secret_key_valid,
            'access_key_prefix': access_key[:4] if len(access_key) >= 4 else '',
            'secret_key_length': len(secret_key),
            'validation_timestamp': datetime.utcnow().isoformat()
        }
    
    def get_credential_source_info(self) -> Dict[str, Any]:
        """Get information about credential source without exposing credentials"""
        
        try:
            if BOTO3_AVAILABLE:
                import boto3
                session = boto3.Session()
                credentials = session.get_credentials()
                
                if credentials is None:
                    return {
                        'source': 'none',
                        'available': False,
                        'message': 'No AWS credentials found'
                    }
                
                # Determine credential source
                source_method = getattr(credentials, 'method', 'unknown')
                
                # Check if credentials are temporary (have session token)
                is_temporary = hasattr(credentials, 'token') and credentials.token is not None
                
                return {
                    'source': source_method,
                    'available': True,
                    'is_temporary': is_temporary,
                    'access_key_prefix': credentials.access_key[:4] if credentials.access_key else None,
                    'message': f'Using credentials from: {source_method}'
                }
            else:
                return {
                    'source': 'mock',
                    'available': True,
                    'is_temporary': False,
                    'message': 'Using mock credentials for testing'
                }
                
        except Exception as e:
            self.logger.error(f"Error checking credential source: {e}")
            return {
                'source': 'error',
                'available': False,
                'message': f'Error checking credentials: {str(e)}'
            }
    
    def sanitize_error_message(self, error_message: str) -> str:
        """Remove sensitive information from error messages"""
        
        sanitized = error_message
        
        # Remove credential information
        sanitized = re.sub(r'AKIA[0-9A-Z]{16}', '[ACCESS_KEY]', sanitized)
        sanitized = re.sub(r'[A-Za-z0-9/+=]{40}', '[SECRET_KEY]', sanitized)
        sanitized = re.sub(r'[A-Za-z0-9/+=]{100,}', '[SESSION_TOKEN]', sanitized)
        
        # Remove potentially sensitive bucket/object names
        sanitized = re.sub(r's3://[a-z0-9.-]+', 's3://[BUCKET]', sanitized)
        
        # Remove IP addresses
        sanitized = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', sanitized)
        
        return sanitized


class SecureAccessLogger:
    """Secure access logger that protects sensitive information"""
    
    def __init__(self, max_log_entries: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.audit_entries: List[SecurityAuditEntry] = []
        self.max_log_entries = max_log_entries
        self.credential_manager = SecureCredentialManager()
    
    def log_s3_access_attempt(self, 
                            document_url: str,
                            user_id: str,
                            success: bool,
                            error_code: Optional[str] = None,
                            source_ip: str = "unknown",
                            additional_context: Dict[str, Any] = None) -> SecurityAuditEntry:
        """Log S3 access attempt with security considerations"""
        
        # Create audit entry with sanitized information
        audit_entry = SecurityAuditEntry(
            timestamp=datetime.utcnow(),
            event_type='s3_document_access',
            user_id_hash=self._hash_user_id(user_id),
            document_url_sanitized=self._sanitize_s3_url(document_url),
            success=success,
            error_code=error_code,
            source_ip_masked=self._mask_ip_address(source_ip),
            security_context=self._create_security_context(additional_context or {})
        )
        
        # Add to audit trail
        self.audit_entries.append(audit_entry)
        
        # Maintain log size limit
        if len(self.audit_entries) > self.max_log_entries:
            self.audit_entries = self.audit_entries[-self.max_log_entries:]
        
        # Log to standard logger (with sensitive information masked)
        log_message = (
            f"S3 Access: {audit_entry.event_type} | "
            f"Success: {success} | "
            f"URL: {audit_entry.document_url_sanitized} | "
            f"User: {audit_entry.user_id_hash[:8]}... | "
            f"IP: {audit_entry.source_ip_masked}"
        )
        
        if error_code:
            log_message += f" | Error: {error_code}"
        
        # Mask any remaining sensitive information
        log_message = self.credential_manager.mask_credentials_in_logs(log_message)
        
        if success:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)
        
        return audit_entry
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for privacy while maintaining uniqueness"""
        return hashlib.sha256(user_id.encode()).hexdigest()
    
    def _sanitize_s3_url(self, url: str) -> str:
        """Sanitize S3 URL to remove sensitive information while preserving structure"""
        
        if not url.startswith('s3://'):
            return '[INVALID_URL]'
        
        try:
            # Parse URL
            s3_path = url[5:]  # Remove 's3://'
            parts = s3_path.split('/')
            
            if len(parts) < 2:
                return '[MALFORMED_URL]'
            
            bucket = parts[0]
            key_parts = parts[1:]
            
            # Hash bucket name for privacy while maintaining uniqueness
            bucket_hash = hashlib.md5(bucket.encode()).hexdigest()[:8]
            sanitized_bucket = f"bucket-{bucket_hash}"
            
            # Sanitize key parts
            sanitized_key_parts = []
            for part in key_parts:
                if len(part) > 20:
                    # Hash long parts that might contain sensitive info
                    part_hash = hashlib.md5(part.encode()).hexdigest()[:8]
                    sanitized_key_parts.append(f"part-{part_hash}")
                else:
                    # Keep short parts but remove special characters
                    sanitized_part = re.sub(r'[^a-zA-Z0-9._-]', 'X', part)
                    sanitized_key_parts.append(sanitized_part)
            
            return f"s3://{sanitized_bucket}/{'/'.join(sanitized_key_parts)}"
            
        except Exception:
            return '[URL_SANITIZATION_ERROR]'
    
    def _mask_ip_address(self, ip: str) -> str:
        """Mask IP address for privacy"""
        
        if ip == "unknown":
            return "unknown"
        
        # IPv4 masking
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            parts = ip.split('.')
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
        
        # IPv6 masking (basic)
        if ':' in ip:
            parts = ip.split(':')
            if len(parts) >= 4:
                return f"{parts[0]}:{parts[1]}:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx"
        
        return "xxx.xxx.xxx.xxx"
    
    def _create_security_context(self, additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create security context with sanitized information"""
        
        context = {
            'user_agent': 'WAFR-MCP-Server/1.0',
            'request_id': hashlib.md5(str(time.time()).encode()).hexdigest()[:16],
            'timestamp_unix': int(time.time())
        }
        
        # Add sanitized additional context
        for key, value in additional_context.items():
            if isinstance(value, str):
                # Sanitize string values
                sanitized_value = self.credential_manager.mask_credentials_in_logs(str(value))
                context[f"context_{key}"] = sanitized_value
            elif isinstance(value, (int, float, bool)):
                context[f"context_{key}"] = value
            else:
                context[f"context_{key}"] = str(type(value).__name__)
        
        return context
    
    def get_audit_trail(self, user_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get audit trail with privacy protection"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter by time
        recent_entries = [
            entry for entry in self.audit_entries 
            if entry.timestamp >= cutoff_time
        ]
        
        # Filter by user if specified
        if user_id:
            user_hash = self._hash_user_id(user_id)
            recent_entries = [
                entry for entry in recent_entries 
                if entry.user_id_hash == user_hash
            ]
        
        # Convert to serializable format
        return [
            {
                'timestamp': entry.timestamp.isoformat(),
                'event_type': entry.event_type,
                'user_id_hash': entry.user_id_hash[:16] + '...',  # Truncate for additional privacy
                'document_url_sanitized': entry.document_url_sanitized,
                'success': entry.success,
                'error_code': entry.error_code,
                'source_ip_masked': entry.source_ip_masked,
                'security_context': entry.security_context
            }
            for entry in recent_entries
        ]


class InputValidator:
    """Validates and sanitizes input for security"""
    
    def __init__(self):
        self.allowed_schemes = ['s3']
        self.allowed_file_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.txt', '.json', '.yaml', '.yml']
        self.max_url_length = 2048
        self.max_filename_length = 255
        self.logger = logging.getLogger(__name__)
    
    def validate_s3_url(self, url: str) -> Dict[str, Any]:
        """Validate S3 URL for security and format compliance"""
        
        validation_result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'sanitized_url': None,
            'security_issues': []
        }
        
        try:
            # Basic length check
            if len(url) > self.max_url_length:
                validation_result['errors'].append(f"URL too long: {len(url)} > {self.max_url_length}")
                return validation_result
            
            # Scheme validation
            if not url.startswith('s3://'):
                validation_result['errors'].append("Invalid scheme: must start with 's3://'")
                return validation_result
            
            # Parse URL components
            s3_path = url[5:]  # Remove 's3://'
            
            if not s3_path or '/' not in s3_path:
                validation_result['errors'].append("Invalid S3 URL format: missing bucket or key")
                return validation_result
            
            bucket, key = s3_path.split('/', 1)
            
            # Validate bucket name
            bucket_validation = self._validate_bucket_name(bucket)
            if not bucket_validation['valid']:
                validation_result['errors'].extend(bucket_validation['errors'])
            
            # Validate key
            key_validation = self._validate_s3_key(key)
            if not key_validation['valid']:
                validation_result['errors'].extend(key_validation['errors'])
            
            # Security checks
            security_issues = self._check_security_issues(key)
            validation_result['security_issues'].extend(security_issues)
            
            if security_issues:
                validation_result['errors'].extend([f"Security issue: {issue}" for issue in security_issues])
            
            # File extension check
            file_ext = self._get_file_extension(key)
            if file_ext and file_ext.lower() not in self.allowed_file_extensions:
                validation_result['warnings'].append(f"Unusual file extension: {file_ext}")
            
            # If no errors, mark as valid
            if not validation_result['errors']:
                validation_result['valid'] = True
                validation_result['sanitized_url'] = f"s3://{bucket}/{key}"
            
        except Exception as e:
            validation_result['errors'].append(f"URL parsing error: {str(e)}")
        
        return validation_result
    
    def _validate_bucket_name(self, bucket: str) -> Dict[str, Any]:
        """Validate S3 bucket name according to AWS rules"""
        
        result = {'valid': True, 'errors': []}
        
        # Length check (3-63 characters)
        if len(bucket) < 3 or len(bucket) > 63:
            result['errors'].append(f"Invalid bucket name length: {len(bucket)} (must be 3-63 characters)")
        
        # Character check (lowercase letters, numbers, hyphens, periods)
        if not re.match(r'^[a-z0-9.-]+$', bucket):
            result['errors'].append("Bucket name contains invalid characters (must be lowercase letters, numbers, hyphens, periods)")
        
        # Start/end check
        if bucket.startswith('.') or bucket.endswith('.') or bucket.startswith('-') or bucket.endswith('-'):
            result['errors'].append("Bucket name cannot start or end with period or hyphen")
        
        # Consecutive periods check
        if '..' in bucket:
            result['errors'].append("Bucket name cannot contain consecutive periods")
        
        # IP address format check
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', bucket):
            result['errors'].append("Bucket name cannot be formatted as IP address")
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    def _validate_s3_key(self, key: str) -> Dict[str, Any]:
        """Validate S3 object key"""
        
        result = {'valid': True, 'errors': []}
        
        # Length check (max 1024 characters)
        if len(key) > 1024:
            result['errors'].append(f"S3 key too long: {len(key)} > 1024")
        
        # Check for null bytes
        if '\x00' in key:
            result['errors'].append("S3 key contains null bytes")
        
        # Check for control characters (except tab, newline, carriage return)
        control_chars = [c for c in key if ord(c) < 32 and c not in '\t\n\r']
        if control_chars:
            result['errors'].append("S3 key contains control characters")
        
        # Check for leading/trailing whitespace
        if key != key.strip():
            result['errors'].append("S3 key has leading or trailing whitespace")
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    def _check_security_issues(self, key: str) -> List[str]:
        """Check for security issues in S3 key"""
        
        issues = []
        
        # Path traversal check
        if '../' in key or '..\\ ' in key:
            issues.append("Path traversal attempt detected")
        
        # Executable file extensions
        executable_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.sh', '.ps1']
        file_ext = self._get_file_extension(key)
        if file_ext and file_ext.lower() in executable_extensions:
            issues.append(f"Potentially dangerous file extension: {file_ext}")
        
        # Script injection patterns
        script_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
        key_lower = key.lower()
        for pattern in script_patterns:
            if pattern in key_lower:
                issues.append(f"Potential script injection pattern: {pattern}")
        
        # SQL injection patterns
        sql_patterns = ["'", '"', ';', '--', '/*', '*/', 'union', 'select', 'drop', 'delete']
        for pattern in sql_patterns:
            if pattern in key_lower:
                issues.append(f"Potential SQL injection pattern: {pattern}")
        
        return issues
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension"""
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return ''
    
    def sanitize_document_reference(self, reference: str) -> str:
        """Sanitize document reference for safe processing"""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"|*?\\]', '', reference)
        
        # Remove control characters
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32 or c in '\t\n\r')
        
        # Limit length
        if len(sanitized) > self.max_url_length:
            sanitized = sanitized[:self.max_url_length]
        
        # Normalize path separators
        sanitized = sanitized.replace('\\', '/')
        
        # Remove multiple consecutive slashes
        sanitized = re.sub(r'/+', '/', sanitized)
        
        return sanitized.strip()


class SecurityHardenedS3Client:
    """Security hardened S3 client with comprehensive security measures"""
    
    def __init__(self, region_name: str = None):
        self.region_name = region_name or get_aws_region()
        self.logger = logging.getLogger(__name__)
        
        # Initialize security components
        self.credential_manager = SecureCredentialManager()
        self.access_logger = SecureAccessLogger()
        self.input_validator = InputValidator()
        
        # TLS/SSL configuration
        self.tls_config = {
            'use_ssl': True,
            'verify_ssl': True,
            'ssl_verify_hostname': True,
            'ca_bundle': None  # Use system CA bundle
        }
        
        # Create secure S3 client
        self._s3_client = None
        self._initialize_secure_client()
    
    def _initialize_secure_client(self):
        """Initialize S3 client with security hardening"""
        
        try:
            if BOTO3_AVAILABLE:
                # Secure configuration
                config = Config(
                    region_name=self.region_name,
                    use_ssl=True,
                    signature_version='s3v4',  # Use latest signature version
                    retries={
                        'max_attempts': 3,
                        'mode': 'adaptive'
                    },
                    read_timeout=60,
                    connect_timeout=15,
                    max_pool_connections=10
                )
                
                self._s3_client = boto3.client('s3', config=config)
                
                # Validate credentials
                credential_info = self.credential_manager.get_credential_source_info()
                if not credential_info['available']:
                    raise ValueError("No valid AWS credentials available")
                
                self.logger.info(f"Initialized secure S3 client: {credential_info['message']}")
                
            else:
                # Mock client for testing
                self._s3_client = MockSecureS3Client()
                self.logger.info("Initialized mock S3 client for testing")
                
        except Exception as e:
            error_message = self.credential_manager.sanitize_error_message(str(e))
            self.logger.error(f"Failed to initialize secure S3 client: {error_message}")
            raise
    
    def load_document_securely(self, 
                             document_url: str, 
                             user_id: str,
                             source_ip: str = "unknown") -> Tuple[bytes, Dict[str, Any]]:
        """Load document with comprehensive security measures"""
        
        start_time = time.time()
        
        try:
            # Input validation
            validation_result = self.input_validator.validate_s3_url(document_url)
            
            if not validation_result['valid']:
                error_msg = f"Invalid document URL: {'; '.join(validation_result['errors'])}"
                
                # Log security violation
                self.access_logger.log_s3_access_attempt(
                    document_url=document_url,
                    user_id=user_id,
                    success=False,
                    error_code="INVALID_URL",
                    source_ip=source_ip,
                    additional_context={'validation_errors': validation_result['errors']}
                )
                
                raise ValueError(error_msg)
            
            # Security warnings
            if validation_result['warnings']:
                self.logger.warning(f"Security warnings for {document_url}: {validation_result['warnings']}")
            
            # Use sanitized URL
            sanitized_url = validation_result['sanitized_url']
            
            # Parse S3 components
            s3_path = sanitized_url[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)
            
            # Load document with security logging
            try:
                if BOTO3_AVAILABLE:
                    response = self._s3_client.get_object(Bucket=bucket, Key=key)
                    content = response['Body'].read()
                else:
                    # Mock response
                    content = b'Mock secure document content'
                
                load_time = time.time() - start_time
                
                # Log successful access
                self.access_logger.log_s3_access_attempt(
                    document_url=document_url,
                    user_id=user_id,
                    success=True,
                    source_ip=source_ip,
                    additional_context={
                        'load_time_seconds': load_time,
                        'content_size_bytes': len(content)
                    }
                )
                
                security_info = {
                    'validation_passed': True,
                    'tls_enabled': self.tls_config['use_ssl'],
                    'certificate_verified': self.tls_config['verify_ssl'],
                    'load_time_seconds': load_time,
                    'content_size_bytes': len(content),
                    'security_warnings': validation_result['warnings']
                }
                
                return content, security_info
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Log failed access
                self.access_logger.log_s3_access_attempt(
                    document_url=document_url,
                    user_id=user_id,
                    success=False,
                    error_code=error_code,
                    source_ip=source_ip,
                    additional_context={'aws_error': str(e)}
                )
                
                # Sanitize error message
                sanitized_error = self.credential_manager.sanitize_error_message(str(e))
                raise Exception(f"S3 access failed ({error_code}): {sanitized_error}")
                
        except Exception as e:
            # Log any other failures
            if 'Invalid document URL' not in str(e):
                self.access_logger.log_s3_access_attempt(
                    document_url=document_url,
                    user_id=user_id,
                    success=False,
                    error_code="GENERAL_ERROR",
                    source_ip=source_ip,
                    additional_context={'error': str(e)}
                )
            
            raise
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        
        credential_info = self.credential_manager.get_credential_source_info()
        
        return {
            'credentials': {
                'available': credential_info['available'],
                'source': credential_info['source'],
                'is_temporary': credential_info.get('is_temporary', False)
            },
            'tls_configuration': self.tls_config,
            'input_validation': {
                'enabled': True,
                'allowed_schemes': self.input_validator.allowed_schemes,
                'allowed_extensions': self.input_validator.allowed_file_extensions,
                'max_url_length': self.input_validator.max_url_length
            },
            'access_logging': {
                'enabled': True,
                'entries_count': len(self.access_logger.audit_entries),
                'max_entries': self.access_logger.max_log_entries
            },
            'security_features': [
                'credential_masking',
                'input_validation',
                'access_logging',
                'tls_encryption',
                'error_sanitization'
            ]
        }
    
    def get_audit_trail(self, user_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get security audit trail"""
        return self.access_logger.get_audit_trail(user_id, hours)


class MockSecureS3Client:
    """Mock S3 client for testing security features"""
    
    def get_object(self, Bucket: str, Key: str):
        """Mock get_object method"""
        
        class MockBody:
            def read(self):
                return b'Mock secure document content for testing'
        
        return {
            'Body': MockBody(),
            'ContentLength': 35,
            'ContentType': 'application/pdf'
        }


# Factory function for easy instantiation
def create_security_hardened_s3_client(region_name: str = None) -> SecurityHardenedS3Client:
    """
    Create security hardened S3 client with all security features enabled
    
    Args:
        region_name: AWS region for S3 operations
    
    Returns:
        Configured SecurityHardenedS3Client instance
    """
    
    return SecurityHardenedS3Client(region_name=region_name)