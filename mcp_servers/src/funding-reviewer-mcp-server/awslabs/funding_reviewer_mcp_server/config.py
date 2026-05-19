"""
Configuration Management for POC Funding Reviewer MCP Server

This module provides centralized configuration management for the POC funding reviewer,
including environment variable handling, model configuration, and validation.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BedrockConfig:
    """Configuration for AWS Bedrock integration"""
    model_id: str = "us.anthropic.claude-sonnet-4-6"
    region: str = "us-east-1"
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_backoff_factor: float = 2.0


@dataclass
class FileProcessingConfig:
    """Configuration for file processing"""
    max_file_size_mb: int = 50
    supported_image_formats: List[str] = field(default_factory=lambda: ["png", "jpg", "jpeg"])
    supported_document_formats: List[str] = field(default_factory=lambda: ["pdf", "docx"])
    temp_dir: str = "/tmp/funding_reviewer"
    cleanup_temp_files: bool = True


@dataclass
class MCPServerConfig:
    """Configuration for MCP server"""
    name: str = "funding-reviewer"
    version: str = "1.0.0"
    description: str = "MCP server for automated POC funding compliance analysis"
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 600


@dataclass
class LoggingConfig:
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "json"
    enable_correlation_ids: bool = True
    log_file: Optional[str] = None
    max_log_size_mb: int = 100
    backup_count: int = 5
    debug_mode: bool = False


@dataclass
class ReferenceDocumentConfig:
    """Configuration for reference documents"""
    general_guidance_path: str = "awslabs/funding_reviewer_mcp_server/docs/poc_general_guidance.md"
    project_template_path: str = "awslabs/funding_reviewer_mcp_server/docs/PoC_Project_Plan_Template.docx"
    require_reference_docs: bool = False  # Allow graceful degradation


# Removed AWSDocumentationMCPConfig and ValidationConfig - not needed for simplified LLM-based analysis


class ConfigManager:
    """
    Centralized configuration management for POC Funding Reviewer
    
    This class handles loading configuration from environment variables,
    validating settings, and providing typed access to configuration values.
    """
    
    def __init__(self, env_prefix: str = "POC_FUNDING_"):
        """
        Initialize the configuration manager
        
        Args:
            env_prefix: Prefix for environment variables
        """
        self.env_prefix = env_prefix
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration sections
        self.bedrock: BedrockConfig = BedrockConfig()
        self.file_processing: FileProcessingConfig = FileProcessingConfig()
        self.mcp_server: MCPServerConfig = MCPServerConfig()
        self.logging: LoggingConfig = LoggingConfig()
        self.reference_docs: ReferenceDocumentConfig = ReferenceDocumentConfig()
        # Removed validation and aws_docs_mcp configs - not needed for simplified server
        
        # Load configuration from environment
        self._load_from_environment()
        
        # Validate configuration
        self._validate_configuration()
        
        self.logger.info("Configuration loaded and validated successfully")
    
    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables"""
        self.logger.info("Loading configuration from environment variables")
        
        # AWS/Bedrock Configuration
        self.bedrock.model_id = self._get_env_var(
            "BEDROCK_MODEL_ID", 
            self.bedrock.model_id,
            str
        )
        self.bedrock.region = self._get_env_var(
            "AWS_REGION", 
            self.bedrock.region,
            str
        )
        self.bedrock.temperature = self._get_env_var(
            "BEDROCK_TEMPERATURE", 
            self.bedrock.temperature,
            float
        )
        self.bedrock.max_tokens = self._get_env_var(
            "BEDROCK_MAX_TOKENS", 
            self.bedrock.max_tokens,
            int
        )
        self.bedrock.timeout_seconds = self._get_env_var(
            "BEDROCK_TIMEOUT", 
            self.bedrock.timeout_seconds,
            int
        )
        self.bedrock.max_retries = self._get_env_var(
            "BEDROCK_MAX_RETRIES", 
            self.bedrock.max_retries,
            int
        )
        self.bedrock.retry_backoff_factor = self._get_env_var(
            "BEDROCK_RETRY_BACKOFF_FACTOR", 
            self.bedrock.retry_backoff_factor,
            float
        )
        
        # File Processing Configuration
        self.file_processing.max_file_size_mb = self._get_env_var(
            "MAX_FILE_SIZE_MB", 
            self.file_processing.max_file_size_mb,
            int
        )
        self.file_processing.supported_image_formats = self._get_env_list(
            "SUPPORTED_IMAGE_FORMATS", 
            self.file_processing.supported_image_formats
        )
        self.file_processing.supported_document_formats = self._get_env_list(
            "SUPPORTED_DOCUMENT_FORMATS", 
            self.file_processing.supported_document_formats
        )
        self.file_processing.temp_dir = self._get_env_var(
            "TEMP_DIR", 
            self.file_processing.temp_dir,
            str
        )
        self.file_processing.cleanup_temp_files = self._get_env_var(
            "CLEANUP_TEMP_FILES", 
            self.file_processing.cleanup_temp_files,
            bool
        )
        
        # MCP Server Configuration
        self.mcp_server.name = self._get_env_var(
            "MCP_SERVER_NAME", 
            self.mcp_server.name,
            str
        )
        self.mcp_server.version = self._get_env_var(
            "MCP_SERVER_VERSION", 
            self.mcp_server.version,
            str
        )
        self.mcp_server.max_concurrent_requests = self._get_env_var(
            "MAX_CONCURRENT_REQUESTS", 
            self.mcp_server.max_concurrent_requests,
            int
        )
        self.mcp_server.request_timeout_seconds = self._get_env_var(
            "REQUEST_TIMEOUT", 
            self.mcp_server.request_timeout_seconds,
            int
        )
        
        # Logging Configuration
        self.logging.level = self._get_env_var(
            "LOG_LEVEL", 
            self.logging.level,
            str
        )
        self.logging.format = self._get_env_var(
            "LOG_FORMAT", 
            self.logging.format,
            str
        )
        self.logging.enable_correlation_ids = self._get_env_var(
            "ENABLE_CORRELATION_IDS", 
            self.logging.enable_correlation_ids,
            bool
        )
        self.logging.log_file = self._get_env_var(
            "LOG_FILE", 
            self.logging.log_file,
            str,
            required=False
        )
        self.logging.debug_mode = self._get_env_var(
            "DEBUG_MODE", 
            self.logging.debug_mode,
            bool
        )
        
        # Reference Document Configuration
        self.reference_docs.general_guidance_path = self._get_env_var(
            "REFERENCE_DOCS_PATH", 
            self.reference_docs.general_guidance_path,
            str
        )
        self.reference_docs.project_template_path = self._get_env_var(
            "PROJECT_TEMPLATE_PATH", 
            self.reference_docs.project_template_path,
            str
        )
        self.reference_docs.require_reference_docs = self._get_env_var(
            "REQUIRE_REFERENCE_DOCS", 
            self.reference_docs.require_reference_docs,
            bool
        )
        
        # Removed validation and AWS Documentation MCP configuration - not needed for simplified server
        
        self.logger.info("Environment configuration loaded")
    
    def _get_env_var(
        self, 
        var_name: str, 
        default: Any, 
        var_type: type,
        required: bool = True
    ) -> Any:
        """
        Get environment variable with type conversion and validation
        
        Args:
            var_name: Environment variable name (without prefix)
            default: Default value if not found
            var_type: Expected type for conversion
            required: Whether the variable is required
            
        Returns:
            Converted environment variable value or default
            
        Raises:
            ValueError: If required variable is missing or conversion fails
        """
        # Special handling for AWS-specific and common variables - check without prefix first
        common_vars = ["AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE", 
                      "BEDROCK_MODEL_ID", "BEDROCK_TEMPERATURE", "BEDROCK_MAX_TOKENS", "BEDROCK_TIMEOUT",
                      "BEDROCK_MAX_RETRIES", "BEDROCK_RETRY_BACKOFF_FACTOR",
                      "MCP_SERVER_NAME", "MCP_SERVER_VERSION", "MCP_SERVER_PORT", "MCP_SERVER_HOST",
                      "LOG_LEVEL", "LOG_FORMAT", "LOG_FILE", "ENABLE_CORRELATION_IDS", "DEBUG_MODE",
                      "MAX_FILE_SIZE_MB", "REQUEST_TIMEOUT", "MAX_CONCURRENT_REQUESTS",
                      "SUPPORTED_IMAGE_FORMATS", "SUPPORTED_DOCUMENT_FORMATS", "TEMP_DIR", "CLEANUP_TEMP_FILES",
                      "REFERENCE_DOCS_PATH", "PROJECT_TEMPLATE_PATH", "REQUIRE_REFERENCE_DOCS"]
        
        if var_name in common_vars:
            env_value = os.getenv(var_name)  # Check without prefix first
            if env_value is None:
                full_var_name = f"{self.env_prefix}{var_name}"
                env_value = os.getenv(full_var_name)  # Then check with prefix
            else:
                full_var_name = var_name
        else:
            full_var_name = f"{self.env_prefix}{var_name}"
            env_value = os.getenv(full_var_name)
        
        if env_value is None:
            if required and default is None:
                raise ValueError(f"Required environment variable {full_var_name} is not set")
            return default
        
        try:
            if var_type == bool:
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif var_type == int:
                return int(env_value)
            elif var_type == float:
                return float(env_value)
            elif var_type == str:
                return env_value
            else:
                return var_type(env_value)
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Failed to convert {full_var_name}='{env_value}' to {var_type.__name__}, "
                f"using default: {default}. Error: {e}"
            )
            return default
    
    def _get_env_list(self, var_name: str, default: List[str]) -> List[str]:
        """
        Get environment variable as a list (comma-separated)
        
        Args:
            var_name: Environment variable name (without prefix)
            default: Default list if not found
            
        Returns:
            List of strings from environment variable or default
        """
        full_var_name = f"{self.env_prefix}{var_name}"
        env_value = os.getenv(full_var_name)
        
        if env_value is None:
            return default
        
        return [item.strip() for item in env_value.split(',') if item.strip()]
    
    def _validate_configuration(self) -> None:
        """Validate configuration values and constraints"""
        self.logger.info("Validating configuration")
        
        validation_errors = []
        
        # Validate Bedrock configuration
        if self.bedrock.temperature < 0.0 or self.bedrock.temperature > 1.0:
            validation_errors.append("Bedrock temperature must be between 0.0 and 1.0")
        
        if self.bedrock.max_tokens < 1:
            validation_errors.append("Bedrock max_tokens must be positive")
        
        if self.bedrock.timeout_seconds < 1:
            validation_errors.append("Bedrock timeout_seconds must be positive")
        
        if self.bedrock.max_retries < 0:
            validation_errors.append("Bedrock max_retries must be non-negative")
        
        # Validate file processing configuration
        if self.file_processing.max_file_size_mb < 1:
            validation_errors.append("max_file_size_mb must be positive")
        
        if not self.file_processing.supported_image_formats:
            validation_errors.append("supported_image_formats cannot be empty")
        
        if not self.file_processing.supported_document_formats:
            validation_errors.append("supported_document_formats cannot be empty")
        
        # Validate MCP server configuration
        if self.mcp_server.max_concurrent_requests < 1:
            validation_errors.append("max_concurrent_requests must be positive")
        
        if self.mcp_server.request_timeout_seconds < 1:
            validation_errors.append("request_timeout_seconds must be positive")
        
        # Validate logging configuration
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_log_levels:
            validation_errors.append(f"log_level must be one of: {valid_log_levels}")
        
        valid_log_formats = ["json", "text"]
        if self.logging.format.lower() not in valid_log_formats:
            validation_errors.append(f"log_format must be one of: {valid_log_formats}")
        
        # Removed validation configuration checks - LLM handles validation
        
        # Validate reference document paths (if required)
        if self.reference_docs.require_reference_docs:
            if not Path(self.reference_docs.general_guidance_path).exists():
                validation_errors.append(f"Required reference document not found: {self.reference_docs.general_guidance_path}")
            
            if not Path(self.reference_docs.project_template_path).exists():
                validation_errors.append(f"Required reference document not found: {self.reference_docs.project_template_path}")
        
        # Raise exception if validation errors found
        if validation_errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
            raise ValueError(error_message)
        
        self.logger.info("Configuration validation completed successfully")
    
    def get_aws_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get AWS credentials from environment
        
        Returns:
            Dictionary with AWS credentials
        """
        return {
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
            "aws_profile": os.getenv("AWS_PROFILE"),
            "region": self.bedrock.region
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "bedrock": {
                "model_id": self.bedrock.model_id,
                "region": self.bedrock.region,
                "temperature": self.bedrock.temperature,
                "max_tokens": self.bedrock.max_tokens,
                "timeout_seconds": self.bedrock.timeout_seconds,
                "max_retries": self.bedrock.max_retries,
                "retry_backoff_factor": self.bedrock.retry_backoff_factor
            },
            "file_processing": {
                "max_file_size_mb": self.file_processing.max_file_size_mb,
                "supported_image_formats": self.file_processing.supported_image_formats,
                "supported_document_formats": self.file_processing.supported_document_formats,
                "temp_dir": self.file_processing.temp_dir,
                "cleanup_temp_files": self.file_processing.cleanup_temp_files
            },
            "mcp_server": {
                "name": self.mcp_server.name,
                "version": self.mcp_server.version,
                "description": self.mcp_server.description,
                "max_concurrent_requests": self.mcp_server.max_concurrent_requests,
                "request_timeout_seconds": self.mcp_server.request_timeout_seconds
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "enable_correlation_ids": self.logging.enable_correlation_ids,
                "log_file": self.logging.log_file
            },
            "reference_docs": {
                "general_guidance_path": self.reference_docs.general_guidance_path,
                "project_template_path": self.reference_docs.project_template_path,
                "require_reference_docs": self.reference_docs.require_reference_docs
            },
            # Removed validation and aws_docs_mcp configs - not needed for simplified server
        }
    
    def __str__(self) -> str:
        """String representation of configuration (safe for logging)"""
        config_dict = self.to_dict()
        
        # Remove sensitive information for logging
        safe_config = config_dict.copy()
        
        return f"ConfigManager({safe_config})"


# Global configuration instance
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    Get the global configuration instance
    
    Returns:
        Global ConfigManager instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigManager()
    
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance (mainly for testing)"""
    global _config_instance
    _config_instance = None