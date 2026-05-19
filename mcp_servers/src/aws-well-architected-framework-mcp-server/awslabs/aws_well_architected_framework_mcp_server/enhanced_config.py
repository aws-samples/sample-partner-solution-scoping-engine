"""Enhanced Configuration Manager for WAFR Server

Provides comprehensive configuration management matching funding reviewer capabilities.
Uses backend CustomerConfig for AWS and application settings.
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Optional

# Import backend CustomerConfig for centralized configuration
try:
    # Add backend path to sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..', '..', 'backend'))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from config.app_config import CustomerConfig
    BACKEND_CONFIG_AVAILABLE = True
except ImportError:
    BACKEND_CONFIG_AVAILABLE = False
    CustomerConfig = None


@dataclass
class BedrockConfig:
    """Bedrock service configuration."""
    model_id: str = "us.anthropic.claude-sonnet-4-6"
    region: str = None  # Will be set from environment via get_aws_region()
    temperature: float = 0  # Set to 0 for deterministic/consistent results
    max_tokens: int = 20000
    timeout_seconds: int = 600
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    
    def __post_init__(self):
        if self.region is None:
            from .consts import get_aws_region
            self.region = get_aws_region()


@dataclass
class FileProcessingConfig:
    """File processing configuration."""
    max_file_size_mb: int = 50
    supported_image_formats: List[str] = None
    supported_document_formats: List[str] = None
    temp_dir: str = "/tmp/wafr_processor"
    cleanup_temp_files: bool = True
    
    def __post_init__(self):
        if self.supported_image_formats is None:
            self.supported_image_formats = ['png', 'jpg', 'jpeg', 'gif', 'webp']
        if self.supported_document_formats is None:
            self.supported_document_formats = ['pdf', 'docx', 'csv']


@dataclass
class S3Config:
    """S3 service configuration."""
    region: str = None  # Will be set from environment via get_aws_region()
    bucket_name: Optional[str] = None
    presigned_url_expiration: int = 3600
    upload_timeout: int = 300
    
    def __post_init__(self):
        if self.region is None:
            from .consts import get_aws_region
            self.region = get_aws_region()
        if not self.bucket_name:
            self.bucket_name = os.getenv('SERA_S3_BUCKET', os.getenv('S3_DOCUMENTS_BUCKET'))


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str = "aws-well-architected-framework"
    version: str = "2.0.0"
    description: str = "Enhanced AWS Well-Architected Framework assessment MCP server"
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 900


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    enable_correlation_ids: bool = True
    log_file: Optional[str] = None
    debug_mode: bool = False
    
    def __post_init__(self):
        # Override from environment
        self.level = os.getenv('LOG_LEVEL', self.level).upper()
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes', 'on')
        if self.debug_mode:
            self.level = 'DEBUG'


@dataclass
class WAFRConfig:
    """WAFR-specific configuration."""
    enable_live_scanning: bool = True
    enable_cost_analysis: bool = True
    enable_security_analysis: bool = True
    enable_performance_analysis: bool = True
    enable_reliability_analysis: bool = True
    enable_sustainability_analysis: bool = True
    default_assessment_depth: str = "comprehensive"  # basic, standard, comprehensive
    max_assessment_time_minutes: int = 30
    # NEW: Document section integration feature flag
    enable_document_section_integration: bool = True
    fallback_to_attachment_on_failure: bool = True


class EnhancedConfigManager:
    """Enhanced configuration manager for WAFR server.
    
    Uses backend CustomerConfig when available, falls back to environment variables.
    """
    
    def __init__(self):
        """Initialize configuration from backend CustomerConfig or environment variables."""
        # Load backend config if available
        if BACKEND_CONFIG_AVAILABLE and CustomerConfig:
            try:
                if not CustomerConfig._config:
                    CustomerConfig.load_config()
            except Exception:
                pass  # Will fall back to environment variables
        
        # Bedrock configuration - prefer backend config
        bedrock_model = BedrockConfig.model_id
        bedrock_region = BedrockConfig.region
        
        if BACKEND_CONFIG_AVAILABLE and CustomerConfig and CustomerConfig._config:
            try:
                bedrock_model = CustomerConfig.get_bedrock_model_id()
                bedrock_region = CustomerConfig.get_aws_region()
            except Exception:
                pass  # Use defaults
        
        self.bedrock = BedrockConfig(
            model_id=os.getenv('BEDROCK_MODEL_ID', bedrock_model),
            region=os.getenv('AWS_REGION', bedrock_region),
            temperature=float(os.getenv('BEDROCK_TEMPERATURE', str(BedrockConfig.temperature))),
            max_tokens=int(os.getenv('BEDROCK_MAX_TOKENS', str(BedrockConfig.max_tokens))),
            timeout_seconds=int(os.getenv('BEDROCK_TIMEOUT', str(BedrockConfig.timeout_seconds))),
            max_retries=int(os.getenv('BEDROCK_MAX_RETRIES', str(BedrockConfig.max_retries)))
        )
        
        self.file_processing = FileProcessingConfig(
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', str(FileProcessingConfig.max_file_size_mb))),
            temp_dir=os.getenv('TEMP_DIR', FileProcessingConfig.temp_dir),
            cleanup_temp_files=os.getenv('CLEANUP_TEMP_FILES', 'true').lower() == 'true'
        )
        
        # S3 configuration - prefer backend config
        s3_bucket = None
        s3_region = S3Config.region
        
        if BACKEND_CONFIG_AVAILABLE and CustomerConfig and CustomerConfig._config:
            try:
                s3_bucket = CustomerConfig.get_sow_s3_bucket()
                s3_region = CustomerConfig.get_aws_region()
            except Exception:
                pass  # Use defaults
        
        self.s3 = S3Config(
            region=os.getenv('AWS_REGION', s3_region),
            bucket_name=os.getenv('SERA_S3_BUCKET', s3_bucket or os.getenv('S3_DOCUMENTS_BUCKET')),
            presigned_url_expiration=int(os.getenv('S3_PRESIGNED_URL_EXPIRATION', str(S3Config.presigned_url_expiration)))
        )
        
        self.mcp_server = MCPServerConfig(
            name=os.getenv('MCP_SERVER_NAME', MCPServerConfig.name),
            version=os.getenv('MCP_SERVER_VERSION', MCPServerConfig.version),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', str(MCPServerConfig.max_concurrent_requests)))
        )
        
        self.logging = LoggingConfig(
            log_file=os.getenv('LOG_FILE')
        )
        
        self.wafr = WAFRConfig(
            enable_live_scanning=os.getenv('ENABLE_LIVE_SCANNING', 'true').lower() == 'true',
            enable_cost_analysis=os.getenv('ENABLE_COST_ANALYSIS', 'true').lower() == 'true',
            default_assessment_depth=os.getenv('DEFAULT_ASSESSMENT_DEPTH', WAFRConfig.default_assessment_depth),
            # NEW: Document section integration feature flags
            enable_document_section_integration=os.getenv('ENABLE_DOCUMENT_SECTION_INTEGRATION', 'true').lower() == 'true',
            fallback_to_attachment_on_failure=os.getenv('FALLBACK_TO_ATTACHMENT_ON_FAILURE', 'true').lower() == 'true'
        )
    
    def validate_configuration(self) -> bool:
        """Validate configuration settings."""
        try:
            # Validate Bedrock configuration
            if not self.bedrock.model_id:
                raise ValueError("Bedrock model ID is required")
            
            if not self.bedrock.region:
                raise ValueError("AWS region is required")
            
            if self.bedrock.max_tokens <= 0:
                raise ValueError("Max tokens must be positive")
            
            # Validate file processing configuration
            if self.file_processing.max_file_size_mb <= 0:
                raise ValueError("Max file size must be positive")
            
            # Validate S3 configuration
            if not self.s3.region:
                raise ValueError("S3 region is required")
            
            # Create temp directory if it doesn't exist
            os.makedirs(self.file_processing.temp_dir, exist_ok=True)
            
            return True
            
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def get_config_summary(self) -> dict:
        """Get configuration summary for logging."""
        return {
            "bedrock_model": self.bedrock.model_id,
            "aws_region": self.bedrock.region,
            "max_file_size_mb": self.file_processing.max_file_size_mb,
            "s3_bucket": self.s3.bucket_name,
            "log_level": self.logging.level,
            "debug_mode": self.logging.debug_mode
        }


# Global configuration instance
_config_instance = None


def get_enhanced_config() -> EnhancedConfigManager:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnhancedConfigManager()
        _config_instance.validate_configuration()
    return _config_instance
