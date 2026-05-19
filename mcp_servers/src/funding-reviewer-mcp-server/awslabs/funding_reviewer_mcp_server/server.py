"""
Simplified POC Funding Reviewer MCP Server

This module implements a simplified MCP server for automated POC funding compliance analysis.
All analysis is performed by AWS Bedrock, not by code-based validation.
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

from .config import ConfigManager, get_config
from .models import UploadedFile, ValidationResult, FileType
from .s3_manager import S3Manager


def setup_logging(config=None):
    """Setup logging with both console and file handlers."""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(os.path.abspath(__file__))
    while not os.path.basename(log_dir).startswith('funding-reviewer-mcp-server'):
        log_dir = os.path.dirname(log_dir)
        if log_dir == os.path.dirname(log_dir):  # Reached root
            log_dir = os.getcwd()
            break
    
    # Use config if provided, otherwise fall back to environment variables
    if config:
        log_level = config.logging.level.upper()
        log_file = config.logging.log_file or os.path.join(log_dir, 'funding-reviewer-mcp-server.log')
        debug_mode = config.logging.debug_mode
        log_format = config.logging.format
    else:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_file = os.getenv('LOG_FILE') or os.path.join(log_dir, 'funding-reviewer-mcp-server.log')
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes', 'on')
        log_format = os.getenv('LOG_FORMAT', 'text')
    
    # Override log level to DEBUG if debug_mode is enabled
    if debug_mode:
        log_level = 'DEBUG'
    
    fastmcp_log_level = os.getenv('FASTMCP_LOG_LEVEL', log_level).upper()
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level, logging.INFO)
    fastmcp_numeric_level = getattr(logging, fastmcp_log_level, logging.INFO)
    
    # Create formatter based on format preference
    if log_format.lower() == 'json':
        # Simple JSON-like format for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
    else:
        # Standard text format
        if debug_mode:
            # More detailed format for debug mode
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Setup root logger
    root_logger.setLevel(numeric_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Set FastMCP logger level
    fastmcp_logger = logging.getLogger('fastmcp')
    fastmcp_logger.setLevel(fastmcp_numeric_level)
    
    # Set MCP logger level
    mcp_logger = logging.getLogger('mcp')
    mcp_logger.setLevel(fastmcp_numeric_level)
    
    return log_file

# Setup basic logging first (will be reconfigured after config is loaded)
log_file_path = setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"POC Funding Reviewer MCP Server starting - logging to {log_file_path}")
logger.info(f"FastMCP log level set to: {os.getenv('FASTMCP_LOG_LEVEL', 'INFO')}")

# Initialize global components
config = get_config()

# Reconfigure logging with config settings
log_file_path = setup_logging(config)
logger = logging.getLogger(__name__)
logger.info(f"Logging reconfigured with config - Level: {config.logging.level}, Debug Mode: {config.logging.debug_mode}")
logger.info(f"Log file: {log_file_path}")

if config.logging.debug_mode:
    logger.debug("DEBUG MODE ENABLED - Enhanced logging and error details active")
    logger.debug(f"Configuration loaded: {config.to_dict()}")

# Initialize FastMCP server
mcp = FastMCP(
    config.mcp_server.name,
    instructions="""🎯 POC FUNDING REVIEWER - Automated POC funding compliance analysis using AWS Bedrock.

    This server provides comprehensive analysis of POC funding requests including:
    - Document validation and correlation
    - Financial assessment and eligibility checking  
    - Architecture analysis and Well-Architected validation
    - Compliance verification against POC funding requirements
    
    Available tools:
    - analyze_poc_funding_request: Main analysis tool for POC funding requests
    - health_check: Server health status checking
    """,
)


# Initialize components globally
try:
    logger.info("Initializing analysis components...")
    logger.debug(f"Configuration loaded: {config.to_dict()}")
    
    # Initialize simplified document processor
    logger.info("Initializing document processor...")
    from .document_processor import SimpleDocumentProcessor
    document_processor = SimpleDocumentProcessor()
    logger.info("Document processor initialized successfully")
    
    # Initialize simplified analysis engine
    logger.info("Initializing Bedrock analysis engine...")
    from .bedrock_analysis_engine import SimplifiedBedrockEngine
    bedrock_engine = SimplifiedBedrockEngine(config)
    logger.info("Bedrock analysis engine initialized successfully")
    
    # Initialize S3 manager
    logger.info("Initializing S3 manager...")
    s3_manager = S3Manager(config=config)
    logger.info("S3 manager initialized successfully")
    
    logger.info("All analysis components initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize analysis components: {e}")
    logger.exception("Component initialization error details:")
    raise

# Helper functions
def _get_image_content_type(filename: str) -> str:
    """Get MIME type for image file based on extension"""
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    content_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    return content_types.get(extension, 'image/png')

def _get_document_content_type(filename: str) -> str:
    """Get MIME type for document file based on extension"""
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    content_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return content_types.get(extension, 'application/pdf')

async def _get_file_content_and_metadata(
    base64_content: Optional[str] = None,
    url: Optional[str] = None,
    filename: str = "",
    content_type_func = _get_document_content_type
) -> tuple[bytes, str, str]:
    """Get file content from either base64 or URL (S3 or public HTTP/HTTPS).
    
    Args:
        base64_content: Base64 encoded content
        url: URL to download from (S3, HTTP, or HTTPS)
        filename: Original filename
        content_type_func: Function to determine content type from filename
        
    Returns:
        Tuple of (content_bytes, filename, content_type)
        
    Raises:
        ValueError: If neither or both sources are provided, or if download fails
    """
    if not base64_content and not url:
        raise ValueError("Either base64_content or url must be provided")
    
    if base64_content and url:
        raise ValueError("Only one of base64_content or url should be provided")
    
    if base64_content:
        # Handle base64 content (existing logic)
        try:
            content = base64.b64decode(base64_content)
            content_type = content_type_func(filename)
            return content, filename, content_type
        except Exception as e:
            raise ValueError(f"Failed to decode base64 content: {e}")
    
    else:  # URL (S3 or public)
        # Handle URL download (S3 or public HTTP/HTTPS)
        try:
            # Download content from URL
            content = s3_manager.download_file_content(url)
            
            # Get metadata if filename not provided
            if not filename:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                
                if parsed_url.scheme == 's3':
                    # Extract filename from S3 key
                    _, key = s3_manager.parse_s3_url(url)
                    filename = key.split('/')[-1]  # Get last part of key as filename
                else:
                    # Extract filename from public URL path
                    path = parsed_url.path
                    filename = path.split('/')[-1] if path else 'downloaded_file'
                    # Ensure we have a filename with extension
                    if not filename or '.' not in filename:
                        filename = 'downloaded_file.bin'
            
            content_type = content_type_func(filename)
            return content, filename, content_type
            
        except Exception as e:
            raise ValueError(f"Failed to download from URL {url}: {e}")

async def _parse_and_validate_documents(
    # Base64 content parameters
    sow_document: Optional[str] = None, 
    sow_filename: str = "",
    architecture_diagram: Optional[str] = None, 
    diagram_filename: str = "",
    pricing_calculator_csv: Optional[str] = None, 
    csv_filename: Optional[str] = None,
    # S3 URL parameters
    sow_document_url: Optional[str] = None,
    architecture_diagram_url: Optional[str] = None,
    pricing_calculator_csv_url: Optional[str] = None
) -> Dict[str, Any]:
    """Parse and validate documents from parameters (supports both base64 and S3 URLs)."""
    logger.debug("📄 Starting document parsing and validation")
    documents = {}
    
    # Parse SOW document
    if sow_document or sow_document_url:
        logger.info(f"📋 Parsing SOW document from {'base64' if sow_document else 'S3 URL'}")
        try:
            sow_content, final_sow_filename, content_type = await _get_file_content_and_metadata(
                base64_content=sow_document,
                url=sow_document_url,
                filename=sow_filename,
                content_type_func=_get_document_content_type
            )
            
            logger.debug(f"SOW content size: {len(sow_content)} bytes")
            
            sow_file = UploadedFile(
                filename=final_sow_filename,
                content_type=content_type,
                size=len(sow_content),
                content=sow_content
            )
            
            # Validate the file
            logger.debug("Validating SOW document...")
            validation_result = document_processor.validate_file(sow_file)
            if not validation_result.is_valid:
                logger.error(f"SOW validation failed: {validation_result.error_messages}")
                raise ValueError(f"SOW validation failed: {validation_result.error_messages}")
            
            documents["sow"] = sow_file
            logger.info(f"✅ SOW document parsed successfully: {final_sow_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to parse SOW document: {e}")
            raise ValueError(f"Failed to parse SOW document: {e}")
    
    # Parse architecture diagram
    if architecture_diagram or architecture_diagram_url:
        logger.info(f"🏗️ Parsing architecture diagram from {'base64' if architecture_diagram else 'S3 URL'}")
        try:
            diagram_content, final_diagram_filename, content_type = await _get_file_content_and_metadata(
                base64_content=architecture_diagram,
                url=architecture_diagram_url,
                filename=diagram_filename,
                content_type_func=_get_image_content_type
            )
            
            diagram_file = UploadedFile(
                filename=final_diagram_filename,
                content_type=content_type,
                size=len(diagram_content),
                content=diagram_content
            )
            
            # Validate the file
            validation_result = document_processor.validate_file(diagram_file)
            if not validation_result.is_valid:
                raise ValueError(f"Diagram validation failed: {validation_result.error_messages}")
            
            documents["diagram"] = diagram_file
            logger.info(f"✅ Architecture diagram parsed successfully: {final_diagram_filename}")
            
        except Exception as e:
            raise ValueError(f"Failed to parse architecture diagram: {e}")
    
    # Parse CSV file (optional)
    if pricing_calculator_csv or pricing_calculator_csv_url:
        logger.info(f"💰 Parsing pricing calculator CSV from {'base64' if pricing_calculator_csv else 'S3 URL'}")
        try:
            csv_content, final_csv_filename, content_type = await _get_file_content_and_metadata(
                base64_content=pricing_calculator_csv,
                url=pricing_calculator_csv_url,
                filename=csv_filename,
                content_type_func=lambda f: "text/csv"
            )
            
            csv_file = UploadedFile(
                filename=final_csv_filename,
                content_type="text/csv",
                size=len(csv_content),
                content=csv_content
            )
            
            # Validate the file
            validation_result = document_processor.validate_file(csv_file)
            if not validation_result.is_valid:
                raise ValueError(f"CSV validation failed: {validation_result.error_messages}")
            
            documents["csv"] = csv_file
            logger.info(f"✅ CSV file parsed successfully: {final_csv_filename}")
            
        except Exception as e:
            logger.warning(f"Failed to parse CSV file: {e}")
            # CSV is optional, so don't fail the entire request
    
    return documents


# TEMPORARILY DISABLED: Use analyze_poc_funding_request_urls instead to avoid token limits
# @mcp.tool(
#     name='analyze_poc_funding_request',
#     description="""Simplified POC funding analysis using direct Bedrock integration.
#     
#     This tool performs comprehensive analysis of POC funding requests including:
#     - Document validation and correlation
#     - Financial assessment and eligibility checking
#     - Architecture analysis and Well-Architected validation
#     - Compliance verification against POC funding requirements
#     
#     Supports both base64 encoded content and S3 URLs for file input.
#     
#     Returns: Complete analysis results from Bedrock"""
# )
async def analyze_poc_funding_request(
    # Base64 content options (original functionality)
    sow_document: str = Field(description="Base64 encoded SOW document content (PDF or DOCX)"),
    sow_filename: str = Field(description="Original filename of the SOW document"),
    architecture_diagram: str = Field(description="Base64 encoded architecture diagram (PNG/JPG) content"),
    diagram_filename: str = Field(description="Original filename of the architecture diagram"),
    pricing_calculator_csv: Optional[str] = Field(None, description="Base64 encoded AWS Pricing Calculator CSV file content (optional)"),
    csv_filename: Optional[str] = Field(None, description="Original filename of the pricing calculator CSV (optional)"),
    
    request_metadata: Dict[str, Any] = Field(description="POC funding request metadata"),
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    POC funding analysis using base64 encoded documents (original functionality)
    
    Args:
        sow_document: Base64 encoded SOW document content (PDF or DOCX)
        sow_filename: Original filename of the SOW document
        architecture_diagram: Base64 encoded architecture diagram (PNG/JPG)
        diagram_filename: Original filename of the architecture diagram
        pricing_calculator_csv: Optional base64 encoded CSV content
        csv_filename: Optional CSV filename
        request_metadata: POC funding request metadata
        ctx: MCP context
        
    Returns:
        Analysis results from Bedrock including formatted response
    """
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"🎯 Starting POC funding analysis request {request_id}")
    logger.info(f"Correlation ID: {correlation_id}")
    logger.debug(f"SOW filename: {sow_filename}")
    logger.debug(f"Diagram filename: {diagram_filename}")
    logger.debug(f"CSV filename: {csv_filename}")
    logger.debug(f"Request metadata: {request_metadata}")
    
    # Validate and enhance request metadata with eligibility information
    logger.info("🔍 Validating POC funding eligibility information...")
    
    # Check for required eligibility fields
    required_fields = ['partner_tier', 'opportunity_stage', 'opportunity_probability', 'aws_account_id']
    missing_fields = []
    
    for field in required_fields:
        # Check for various possible field names
        field_variants = {
            'partner_tier': ['partner_tier', 'partner_stage', 'partnerTier', 'partnerStage'],
            'opportunity_stage': ['opportunity_stage', 'opportunityStage', 'stage'],
            'opportunity_probability': ['opportunity_probability', 'opportunityProbability', 'probability'],
            'aws_account_id': ['aws_account_id', 'awsAccountId', 'account_id', 'accountId']
        }
        
        found = False
        for variant in field_variants.get(field, [field]):
            if variant in request_metadata and request_metadata[variant] is not None:
                # Normalize the field name in metadata
                if variant != field:
                    request_metadata[field] = request_metadata[variant]
                found = True
                break
        
        if not found:
            missing_fields.append(field)
    
    # Log eligibility status
    if missing_fields:
        logger.warning(f"⚠️ Missing required POC funding eligibility information: {missing_fields}")
        logger.info("📋 Analysis will proceed but will flag missing information for collection")
        # Add missing fields info to metadata for the analysis engine
        request_metadata['_missing_eligibility_fields'] = missing_fields
    else:
        logger.info("✅ All required POC funding eligibility information provided")
        
        # Validate eligibility criteria values
        eligibility_issues = []
        
        # Check partner tier - configure valid tiers for your deployment
        valid_tiers = []  # Configure: e.g., ['Tier1', 'Tier2', 'Tier3']
        partner_tier = request_metadata.get('partner_tier', '')
        if valid_tiers and partner_tier not in valid_tiers:
            eligibility_issues.append(f"Partner tier '{partner_tier}' must be one of: {valid_tiers}")
        
        # Check opportunity probability - configure minimum threshold
        try:
            probability = float(request_metadata.get('opportunity_probability', 0))
            min_probability = 0  # Configure: minimum probability threshold
            if min_probability and probability < min_probability:
                eligibility_issues.append(f"Opportunity probability {probability}% must be ≥{min_probability}%")
        except (ValueError, TypeError):
            eligibility_issues.append("Opportunity probability must be a valid number")
        
        # Check opportunity stage
        stage = request_metadata.get('opportunity_stage', '')
        invalid_stages = ['launched']  # Configure: stages that are ineligible
        if stage.lower() in invalid_stages:
            eligibility_issues.append(f"Opportunity stage '{stage}' is not eligible for funding")
        
        if eligibility_issues:
            logger.warning(f"⚠️ Eligibility criteria issues found: {eligibility_issues}")
            request_metadata['_eligibility_issues'] = eligibility_issues
        else:
            logger.info("✅ All eligibility criteria validation passed")
    
    # Validate input parameters (base64 content)
    if not sow_document:
        raise ValueError("sow_document (base64 content) is required")
    
    if not architecture_diagram:
        raise ValueError("architecture_diagram (base64 content) is required")
    
    logger.info(f"📥 Input method: SOW=base64, Diagram=base64, CSV={'base64' if pricing_calculator_csv else 'none'}")
    
    try:
        # Parse and validate documents
        logger.info("📄 Parsing and validating documents...")
        documents = await _parse_and_validate_documents(
            sow_document=sow_document,
            sow_filename=sow_filename, 
            architecture_diagram=architecture_diagram,
            diagram_filename=diagram_filename,
            pricing_calculator_csv=pricing_calculator_csv,
            csv_filename=csv_filename,
            sow_document_url=None,  # Not used in base64 version
            architecture_diagram_url=None,  # Not used in base64 version
            pricing_calculator_csv_url=None  # Not used in base64 version
        )
        logger.info(f"✅ Documents parsed successfully: {list(documents.keys())}")
        
        # Create simplified analysis request
        logger.info("🔧 Creating analysis request...")
        from .bedrock_analysis_engine import SimplifiedAnalysisRequest
        
        analysis_request = SimplifiedAnalysisRequest(
            sow_document=documents.get("sow"),
            architecture_diagram=documents.get("diagram"),
            pricing_calculator_csv=documents.get("csv"),
            request_metadata=request_metadata,
            correlation_id=correlation_id
        )
        logger.debug(f"Analysis request created with correlation ID: {correlation_id}")
        
        # Perform Bedrock analysis
        logger.info("🤖 Starting Bedrock analysis...")
        analysis_result = await bedrock_engine.analyze_poc_funding_request(
            analysis_request, correlation_id
        )
        
        # Format and return response
        return {
            "status": analysis_result.status,
            "request_id": request_id,
            "analysis_result": analysis_result.analysis,
            "formatted_response": analysis_result.formatted_response,
            "processing_time": analysis_result.processing_time,
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"POC funding analysis failed: {e}")
        
        # Enhanced error logging in debug mode
        if config.logging.debug_mode:
            logger.exception("Full error traceback:")
            logger.debug(f"Request details - SOW: {bool(sow_document)}, "
                        f"Diagram: {bool(architecture_diagram)}, "
                        f"CSV: {bool(pricing_calculator_csv)}")
        
        error_response = {
            "status": "error",
            "request_id": request_id,
            "error": {
                "code": "analysis_failed",
                "message": str(e)
            },
            "analysis_result": {
                "program_identification": {"error": "Analysis failed"},
                "eligibility_check": {"error": "Analysis failed"},
                "financial_assessment": {"error": "Analysis failed"},
                "document_review": {"error": "Analysis failed"},
                "document_correlation": {"error": "Analysis failed"},
                "scope_verification": {"error": "Analysis failed"},
                "well_architected_validation": {"error": "Analysis failed"},
                "review_summary": {
                    "status": "Error",
                    "key_findings": [f"Analysis failed: {str(e)}"],
                    "action_items": ["Retry analysis or contact support"],
                    "error": str(e)
                }
            },
            "processing_time": processing_time,
            "correlation_id": correlation_id
        }
        
        # Add debug information if debug mode is enabled
        if config.logging.debug_mode:
            import traceback
            error_response["debug_info"] = {
                "exception_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "config_summary": {
                    "bedrock_model": config.bedrock.model_id,
                    "bedrock_region": config.bedrock.region,
                    "max_file_size_mb": config.file_processing.max_file_size_mb
                }
            }
        
        return error_response


@mcp.tool(
    name="analyze_poc_funding_request_urls",
    description="POC funding analysis using S3 URLs for document access (optimized for backend integration)"
)
async def analyze_poc_funding_request_urls(
    # S3 URL parameters only
    sow_document_url: str = Field(description="S3 URL to SOW document (PDF or DOCX)"),
    sow_filename: str = Field(description="Original filename of the SOW document"),
    architecture_diagram_url: str = Field(description="S3 URL to architecture diagram (PNG/JPG)"),
    diagram_filename: str = Field(description="Original filename of the architecture diagram"),
    pricing_calculator_csv_url: Optional[str] = Field(None, description="S3 URL to pricing calculator CSV (optional)"),
    csv_filename: Optional[str] = Field(None, description="Original filename of the pricing calculator CSV (optional)"),
    
    request_metadata: Dict[str, Any] = Field(description="POC funding request metadata"),
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    POC funding analysis using S3 URLs for document access (optimized for backend integration)
    
    This tool is designed for backend systems that store documents in S3 and want to avoid
    the token limits associated with base64 encoding large documents.
    
    Args:
        sow_document_url: S3 URL to SOW document (PDF or DOCX)
        sow_filename: Original filename of the SOW document
        architecture_diagram_url: S3 URL to architecture diagram (PNG/JPG)
        diagram_filename: Original filename of the architecture diagram
        pricing_calculator_csv_url: Optional S3 URL to pricing calculator CSV
        csv_filename: Optional CSV filename
        request_metadata: POC funding request metadata
        ctx: MCP context
        
    Returns:
        Analysis results from Bedrock
    """
    request_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"🎯 Starting POC funding analysis request (URLs) {request_id}")
    logger.info(f"Correlation ID: {correlation_id}")
    logger.debug(f"SOW filename: {sow_filename}")
    logger.debug(f"Diagram filename: {diagram_filename}")
    logger.debug(f"CSV filename: {csv_filename}")
    logger.debug(f"Request metadata: {request_metadata}")
    
    # Validate and enhance request metadata with eligibility information
    logger.info("🔍 Validating POC funding eligibility information...")
    
    # Check for required eligibility fields
    required_fields = ['partner_tier', 'opportunity_stage', 'opportunity_probability', 'aws_account_id']
    missing_fields = []
    
    for field in required_fields:
        # Check for various possible field names
        field_variants = {
            'partner_tier': ['partner_tier', 'partner_stage', 'partnerTier', 'partnerStage'],
            'opportunity_stage': ['opportunity_stage', 'opportunityStage', 'stage'],
            'opportunity_probability': ['opportunity_probability', 'opportunityProbability', 'probability'],
            'aws_account_id': ['aws_account_id', 'awsAccountId', 'account_id', 'accountId']
        }
        
        found = False
        for variant in field_variants.get(field, [field]):
            if variant in request_metadata and request_metadata[variant] is not None:
                # Normalize the field name in metadata
                if variant != field:
                    request_metadata[field] = request_metadata[variant]
                found = True
                break
        
        if not found:
            missing_fields.append(field)
    
    # Log eligibility status
    if missing_fields:
        logger.warning(f"⚠️ Missing required POC funding eligibility information: {missing_fields}")
        logger.info("📋 Analysis will proceed but will flag missing information for collection")
        # Add missing fields info to metadata for the analysis engine
        request_metadata['_missing_eligibility_fields'] = missing_fields
    else:
        logger.info("✅ All required POC funding eligibility information provided")
        
        # Validate eligibility criteria values
        eligibility_issues = []
        
        # Check partner tier - configure valid tiers for your deployment
        valid_tiers = []  # Configure: e.g., ['Tier1', 'Tier2', 'Tier3']
        partner_tier = request_metadata.get('partner_tier', '')
        if valid_tiers and partner_tier not in valid_tiers:
            eligibility_issues.append(f"Partner tier '{partner_tier}' must be one of: {valid_tiers}")
        
        # Check opportunity probability - configure minimum threshold
        try:
            probability = float(request_metadata.get('opportunity_probability', 0))
            min_probability = 0  # Configure: minimum probability threshold
            if min_probability and probability < min_probability:
                eligibility_issues.append(f"Opportunity probability {probability}% must be ≥{min_probability}%")
        except (ValueError, TypeError):
            eligibility_issues.append("Opportunity probability must be a valid number")
        
        # Check opportunity stage
        stage = request_metadata.get('opportunity_stage', '')
        invalid_stages = ['launched']  # Configure: stages that are ineligible
        if stage.lower() in invalid_stages:
            eligibility_issues.append(f"Opportunity stage '{stage}' is not eligible for funding")
        
        if eligibility_issues:
            logger.warning(f"⚠️ Eligibility criteria issues found: {eligibility_issues}")
            request_metadata['_eligibility_issues'] = eligibility_issues
        else:
            logger.info("✅ All eligibility criteria validation passed")
    
    # Validate input parameters (S3 URLs only)
    if not sow_document_url:
        raise ValueError("sow_document_url (S3 URL) is required")
    
    if not architecture_diagram_url:
        raise ValueError("architecture_diagram_url (S3 URL) is required")
    
    logger.info(f"📥 Input method: SOW=S3, Diagram=S3, CSV={'S3' if pricing_calculator_csv_url else 'none'}")
    
    try:
        # Parse and validate documents
        logger.info("📄 Parsing and validating documents...")
        documents = await _parse_and_validate_documents(
            sow_document=None,  # No base64 support in URL version
            sow_filename=sow_filename, 
            architecture_diagram=None,  # No base64 support in URL version
            diagram_filename=diagram_filename,
            pricing_calculator_csv=None,  # No base64 support in URL version
            csv_filename=csv_filename,
            sow_document_url=sow_document_url,
            architecture_diagram_url=architecture_diagram_url,
            pricing_calculator_csv_url=pricing_calculator_csv_url
        )
        logger.info(f"✅ Documents parsed successfully: {list(documents.keys())}")
        
        # Create simplified analysis request
        logger.info("🔧 Creating analysis request...")
        from .bedrock_analysis_engine import SimplifiedAnalysisRequest
        
        analysis_request = SimplifiedAnalysisRequest(
            sow_document=documents.get("sow"),
            architecture_diagram=documents.get("diagram"),
            pricing_calculator_csv=documents.get("csv"),
            request_metadata=request_metadata,
            correlation_id=correlation_id
        )
        logger.debug(f"Analysis request created with correlation ID: {correlation_id}")
        
        # Perform Bedrock analysis
        logger.info("🤖 Starting Bedrock analysis...")
        analysis_result = await bedrock_engine.analyze_poc_funding_request(
            analysis_request, correlation_id
        )
        
        # Format and return response
        return {
            "status": analysis_result.status,
            "request_id": request_id,
            "analysis_result": analysis_result.analysis,
            "formatted_response": analysis_result.formatted_response,
            "processing_time": analysis_result.processing_time,
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"POC funding analysis failed: {e}")
        
        # Enhanced error logging in debug mode
        if config.logging.debug_mode:
            logger.exception("Full error traceback:")
            logger.debug(f"Request details - SOW: {bool(sow_document_url)}, "
                        f"Diagram: {bool(architecture_diagram_url)}, "
                        f"CSV: {bool(pricing_calculator_csv_url)}")
        
        error_response = {
            "status": "error",
            "request_id": request_id,
            "error": {
                "code": "analysis_failed",
                "message": str(e)
            },
            "analysis_result": {
                "program_identification": {"error": "Analysis failed"},
                "eligibility_check": {"error": "Analysis failed"},
                "financial_assessment": {"error": "Analysis failed"},
                "document_review": {"error": "Analysis failed"},
                "document_correlation": {"error": "Analysis failed"},
                "scope_verification": {"error": "Analysis failed"},
                "well_architected_validation": {"error": "Analysis failed"},
                "review_summary": {
                    "status": "Need More Information",
                    "key_findings": ["Analysis failed due to technical error"],
                    "clarifying_questions": ["Please retry the analysis"],
                    "approval_confidence": 0.0,
                    "next_steps": ["Contact support if issue persists"]
                },
                "raw_response": str(e)[:1000] if str(e) else "Unknown error occurred"
            },
            "processing_time": processing_time,
            "correlation_id": correlation_id
        }
        
        # Add debug information if debug mode is enabled
        if config.logging.debug_mode:
            import traceback
            error_response["debug_info"] = {
                "exception_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "config_summary": {
                    "bedrock_model": config.bedrock.model_id,
                    "bedrock_region": config.bedrock.region,
                    "max_file_size_mb": config.file_processing.max_file_size_mb
                }
            }
        
        return error_response


@mcp.tool(
    name='health_check',
    description="""Tool for checking server health status.
    
    Returns health status information including component status and optional details."""
)
async def health_check(
    include_details: Optional[bool] = Field(False, description="Include detailed health information"),
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Tool for checking server health status
    
    Args:
        include_details: Include detailed health information
        ctx: MCP context
        
    Returns:
        Health status information
    """
    logger.info("🏥 Health check requested")
    logger.debug(f"Include details: {include_details}")
    
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "server_name": config.mcp_server.name,
            "server_version": "1.0.0",
            "checks": {
                "bedrock_engine": bedrock_engine is not None,
                "document_processor": document_processor is not None,
                "configuration": config is not None
            }
        }
        
        logger.debug(f"Component checks: {health_status['checks']}")
        
        # Check if any critical components failed
        failed_checks = [name for name, status in health_status["checks"].items() if not status]
        
        if failed_checks:
            health_status["status"] = "unhealthy"
            health_status["failed_checks"] = failed_checks
        
        if include_details:
            health_status["details"] = {
                "bedrock_model": config.bedrock.model_id,
                "aws_region": config.bedrock.region
            }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# Factory functions for backward compatibility


def create_server(config: Optional[ConfigManager] = None) -> FastMCP:
    """
    Factory function to create a POC Funding Reviewer MCP Server instance
    
    Args:
        config: Optional configuration manager instance (ignored, uses global config)
    
    Returns:
        Configured FastMCP instance
    """
    return mcp


def create_app() -> FastMCP:
    """Create and return the FastMCP application"""
    return mcp


def main():
    """Main entry point for the MCP server"""
    logger.info("=" * 60)
    logger.info("POC FUNDING REVIEWER MCP SERVER STARTING")
    logger.info("=" * 60)
    logger.info(f"Server name: {config.mcp_server.name}")
    logger.info(f"Server version: {config.mcp_server.version}")
    logger.info(f"Log file: {log_file_path}")
    logger.info(f"AWS Region: {config.bedrock.region}")
    logger.info(f"Bedrock Model: {config.bedrock.model_id}")
    logger.debug("Server starting with stdio transport")
    
    try:
        logger.info("Starting MCP server run loop...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.exception("Server error details:")
        raise
    finally:
        logger.info("POC Funding Reviewer MCP Server stopped")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()