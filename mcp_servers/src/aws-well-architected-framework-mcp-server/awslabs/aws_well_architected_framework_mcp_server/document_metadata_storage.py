"""
Document metadata storage module for WAFR Server.

This module provides functionality to store WAFR document metadata in DynamoDB
following the same pattern as SOW documents for consistent document section integration.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os
import sys

from .consts import get_aws_region

# Set up logging
logger = logging.getLogger(__name__)

def get_sera_config():
    """Get SERA configuration for DynamoDB access."""
    try:
        # Add backend path to sys.path to import the configuration
        backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from config.app_config import CustomerConfig
        
        # Load configuration if not already loaded
        if not CustomerConfig._config:
            CustomerConfig.load_config()
        
        return {
            'DYNAMODB_TABLE_NAME': CustomerConfig.get_value('DYNAMODB_TABLE_NAME'),
            'AWS_REGION': CustomerConfig.get_aws_region(),
            'S3_UPLOAD_BUCKET': CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        }
    except Exception as e:
        logger.error(f"Failed to get SERA config: {e}")
        return None

async def store_wafr_metadata_in_dynamodb(chat_id: str, wafr_metadata: Dict[str, Any]) -> None:
    """
    Store WAFR document metadata in DynamoDB following cost-analysis pattern.
    
    Args:
        chat_id: Chat session ID
        wafr_metadata: WAFR document metadata
    """
    logger.info(f'Starting DynamoDB save for chat_id={chat_id}')
    
    if not chat_id:
        logger.warning(f'Skipping DynamoDB save - chat_id={chat_id}')
        return
    
    try:
        # Import and use the backend's metadata storage function with error handling
        backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        try:
            # Try the importlib approach first
            import importlib.util
            spec = importlib.util.spec_from_file_location("chat_models", os.path.join(backend_path, "models", "chat.py"))
            chat_models = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(chat_models)
            success = chat_models.store_wafr_metadata_in_dynamodb(chat_id, wafr_metadata)
        except Exception as import_error:
            logger.warning(f"Importlib approach failed: {import_error}")
            try:
                # Fallback to direct import (may work in MCP server context)
                from models.chat import store_wafr_metadata_in_dynamodb as backend_store_function
                success = backend_store_function(chat_id, wafr_metadata)
            except Exception as fallback_error:
                logger.error(f"Both import approaches failed. Importlib: {import_error}, Direct: {fallback_error}")
                # Don't raise - just log the failure and continue
                success = False
        
        if success:
            logger.info(f"Successfully stored WAFR document metadata for chat_id: {chat_id}")
        else:
            logger.warning(f"Backend metadata storage failed for chat_id: {chat_id}")
            
    except Exception as e:
        logger.error(f'Failed to save WAFR data to DynamoDB: {str(e)}')
        # Don't raise - DynamoDB storage failure shouldn't break the main WAFR functionality
        logger.warning("Continuing without DynamoDB metadata storage")

def generate_s3_key_for_wafr_document(chat_id: str, filename: str = "wafr_assessment.docx") -> str:
    """
    Generate S3 key for WAFR document following the established pattern.
    
    Args:
        chat_id: Chat session ID
        filename: Document filename (default: wafr_assessment.docx)
        
    Returns:
        str: S3 key in format {chat_id}/wafr/{filename}
    """
    return f"{chat_id}/wafr/{filename}"

def create_wafr_document_metadata(
    s3_url: str,
    s3_key: str,
    version_id: Optional[str] = None,
    file_size: Optional[int] = None,
    generation_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create WAFR document metadata dictionary.
    
    Args:
        s3_url: S3 URL of the document
        s3_key: S3 key of the document
        version_id: S3 version ID (optional)
        file_size: File size in bytes (optional)
        generation_time: Time taken to generate document in seconds (optional)
        
    Returns:
        Dict containing WAFR document metadata
    """
    metadata = {
        's3_url': s3_url,
        's3_key': s3_key,
        'document_type': 'wafr_assessment',
        'tool_name': 'aws_well_architected_framework_mcp_server',
        'status': 'generated',
        'approved': True,  # Auto-approve for universal access
        'generated_date': datetime.now().isoformat(),
        'created_timestamp': datetime.now().isoformat()
    }
    
    if version_id:
        metadata['version_id'] = version_id
    
    if file_size is not None:
        metadata['file_size'] = file_size
    
    if generation_time is not None:
        metadata['generation_time'] = generation_time
    
    return metadata


async def register_wafr_document_in_chat(chat_id: str, wafr_metadata: Dict[str, Any]) -> bool:
    """
    Register WAFR document in the chat's documents field for frontend access.
    
    This function adds the WAFR document to the 'documents' field in DynamoDB,
    which is required for the frontend Documents component to list and download
    the document using CloudFront signed URLs.
    
    Note: This function may fail in MCP server context due to Flask dependencies
    in the backend models. This is non-blocking - the document is still generated
    and uploaded to S3 successfully.
    
    Args:
        chat_id: Chat session ID
        wafr_metadata: WAFR document metadata containing s3_key, version_id, etc.
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f'Registering WAFR document in chat documents for chat_id={chat_id}')
    
    if not chat_id:
        logger.warning('Skipping document registration - chat_id is empty')
        return False
    
    try:
        # Import backend's update_chat_document function
        backend_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend'
        )
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        import importlib.util
        import uuid
        
        # Generate a unique document ID
        document_id = f"wafr_{uuid.uuid4().hex[:8]}"
        
        # Create document metadata in the format expected by the frontend
        document_metadata = {
            's3_key': wafr_metadata.get('s3_key'),
            's3_url': wafr_metadata.get('s3_url'),
            'version_id': wafr_metadata.get('version_id'),
            'document_type': 'wafr_assessment',
            'tool_name': 'aws_well_architected_framework_mcp_server',
            'name': 'WAFR Assessment Report',
            'original_filename': 'wafr_assessment.docx',  # Required for frontend file type detection
            'approved': True,  # Auto-approve for universal access
            'created_timestamp': datetime.now().isoformat(),
            'file_size': wafr_metadata.get('file_size'),
        }
        
        # Try to load the chat models module
        # This may fail in MCP server context due to Flask dependencies
        try:
            spec = importlib.util.spec_from_file_location(
                "chat_models", 
                os.path.join(backend_path, "models", "chat.py")
            )
            chat_models = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(chat_models)
            
            # Use update_chat_document to add to the documents field
            success = chat_models.update_chat_document(chat_id, document_id, document_metadata)
            
            if success:
                logger.info(
                    f"Successfully registered WAFR document {document_id} "
                    f"for chat_id: {chat_id}"
                )
            else:
                logger.warning(f"Failed to register WAFR document for chat_id: {chat_id}")
            
            return success
            
        except ModuleNotFoundError as e:
            # Flask or other backend dependencies not available in MCP server context
            # This is expected and non-blocking - document is still in S3
            if 'flask' in str(e).lower():
                logger.info(
                    f"Skipping document registration (Flask not available in MCP context) - "
                    f"document is still accessible via S3 URL"
                )
            else:
                logger.warning(f"Module not found during document registration: {e}")
            return False
            
        except Exception as import_error:
            logger.warning(f"Could not load chat models for document registration: {import_error}")
            return False
        
    except Exception as e:
        logger.error(f'Failed to register WAFR document in chat: {str(e)}')
        return False


# ============================================================
# ARCHITECTURE DATA CACHING
# These functions cache architecture_data in DynamoDB to prevent
# INPUT_TOO_LONG errors when passing data between WAFR tool calls
# ============================================================

# In-memory cache for architecture data (fallback if DynamoDB fails)
_architecture_data_cache: Dict[str, Dict[str, Any]] = {}

async def cache_architecture_data(chat_id: str, architecture_data: Dict[str, Any]) -> bool:
    """
    Cache architecture data in DynamoDB for retrieval by subsequent tool calls.
    
    This prevents INPUT_TOO_LONG errors by allowing tools to retrieve cached data
    instead of receiving the full ~666KB architecture_data in each tool call.
    
    Args:
        chat_id: Chat session ID
        architecture_data: Full architecture data from analyze_architecture_documents
        
    Returns:
        bool: True if caching succeeded, False otherwise
    """
    logger.info(f'Caching architecture data for chat_id={chat_id}')
    
    if not chat_id:
        logger.warning('Cannot cache architecture data - chat_id is empty')
        return False
    
    # Always store in memory cache as fallback
    _architecture_data_cache[chat_id] = architecture_data
    logger.info(f'✅ Stored architecture data in memory cache for chat_id={chat_id}')
    
    # Log key metrics from architecture data
    services_count = len(architecture_data.get('identified_services', []))
    patterns_count = len(architecture_data.get('architectural_patterns', []))
    logger.info(f'📊 Architecture data contains {services_count} services, {patterns_count} patterns')
    
    try:
        import json
        import boto3
        from botocore.exceptions import ClientError
        from boto3.dynamodb.conditions import Key
        
        # Get DynamoDB table name from config
        config = get_sera_config()
        logger.debug(f'CACHE_DEBUG: Config loaded: {config is not None}')
        
        if not config:
            logger.warning('❌ DynamoDB config not available, using memory cache only')
            return True  # Memory cache succeeded
            
        if not config.get('DYNAMODB_TABLE_NAME'):
            logger.warning('❌ DynamoDB table name not configured, using memory cache only')
            return True  # Memory cache succeeded
        
        table_name = config['DYNAMODB_TABLE_NAME']
        region = config.get('AWS_REGION') or get_aws_region()
        logger.info(f'📦 Caching to DynamoDB table={table_name}, region={region}')
        
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # CRITICAL FIX: The table uses (user_id, timestamp) as primary key, not chat_id
        # We need to query the GSI first to get the actual primary key
        logger.info(f'🔍 Querying GSI chat-id-gsi to find primary key for chat_id={chat_id}')
        
        gsi_response = table.query(
            IndexName='chat-id-gsi',
            KeyConditionExpression=Key('chat_id').eq(chat_id),
            Limit=1
        )
        
        items = gsi_response.get('Items', [])
        if not items:
            logger.warning(f'❌ No chat record found for chat_id={chat_id} in GSI')
            return True  # Memory cache succeeded but no DynamoDB record to update
        
        # Get the actual primary key from the GSI result
        chat_record = items[0]
        user_id = chat_record.get('user_id')
        timestamp = chat_record.get('timestamp')
        
        if not user_id or not timestamp:
            logger.warning(f'❌ Missing user_id or timestamp in GSI result for chat_id={chat_id}')
            return True  # Memory cache succeeded
        
        logger.info(f'✅ Found primary key: user_id={user_id}, timestamp={timestamp}')
        
        # Compress architecture data for storage (remove large raw_analysis text)
        compressed_data = _compress_architecture_data_for_storage(architecture_data)
        compressed_size = len(json.dumps(compressed_data))
        logger.info(f'📦 Compressed architecture data size: {compressed_size} bytes')
        
        # Update the chat record with architecture data using the correct primary key
        table.update_item(
            Key={'user_id': user_id, 'timestamp': timestamp},
            UpdateExpression='SET wafr_architecture_data = :data, wafr_architecture_timestamp = :ts',
            ExpressionAttributeValues={
                ':data': json.dumps(compressed_data),
                ':ts': datetime.now().isoformat()
            }
        )
        
        logger.info(f'✅ Successfully cached architecture data in DynamoDB for chat_id={chat_id}')
        return True
        
    except Exception as e:
        logger.error(f'❌ Failed to cache architecture data in DynamoDB: {str(e)}')
        import traceback
        logger.error(f'❌ Traceback: {traceback.format_exc()}')
        logger.info('⚠️ Architecture data is available in memory cache only (will be lost on next tool call)')
        return True  # Memory cache succeeded but DynamoDB failed


async def get_cached_architecture_data(chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached architecture data for a chat session.
    
    Tries DynamoDB first, falls back to memory cache.
    
    Args:
        chat_id: Chat session ID
        
    Returns:
        Cached architecture data or None if not found
    """
    logger.info(f'🔍 Retrieving cached architecture data for chat_id={chat_id}')
    
    if not chat_id:
        logger.warning('❌ Cannot retrieve architecture data - chat_id is empty')
        return None
    
    # Check memory cache first (faster)
    logger.debug(f'CACHE_DEBUG: Memory cache keys: {list(_architecture_data_cache.keys())}')
    if chat_id in _architecture_data_cache:
        cached = _architecture_data_cache[chat_id]
        services_count = len(cached.get('identified_services', []))
        logger.info(f'✅ Found architecture data in memory cache for chat_id={chat_id} ({services_count} services)')
        return cached
    
    logger.info(f'⚠️ Not in memory cache, trying DynamoDB...')
    
    try:
        import json
        import boto3
        from boto3.dynamodb.conditions import Key
        
        # Get DynamoDB table name from config
        config = get_sera_config()
        logger.debug(f'CACHE_DEBUG: Config loaded: {config is not None}')
        
        if not config:
            logger.warning('❌ DynamoDB config not available')
            return None
            
        if not config.get('DYNAMODB_TABLE_NAME'):
            logger.warning('❌ DynamoDB table name not configured')
            return None
        
        table_name = config['DYNAMODB_TABLE_NAME']
        region = config.get('AWS_REGION') or get_aws_region()
        logger.info(f'📦 Querying DynamoDB table={table_name}, region={region}')
        
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # CRITICAL FIX: The table uses (user_id, timestamp) as primary key, not chat_id
        # We need to query the GSI to get the record by chat_id
        logger.info(f'🔍 Querying GSI chat-id-gsi to find record for chat_id={chat_id}')
        
        gsi_response = table.query(
            IndexName='chat-id-gsi',
            KeyConditionExpression=Key('chat_id').eq(chat_id),
            ProjectionExpression='wafr_architecture_data, user_id, #ts',
            ExpressionAttributeNames={'#ts': 'timestamp'},  # timestamp is a reserved word
            Limit=1
        )
        
        items = gsi_response.get('Items', [])
        if not items:
            logger.warning(f'❌ No chat record found for chat_id={chat_id} in GSI')
            return None
        
        item = items[0]
        logger.debug(f'CACHE_DEBUG: DynamoDB item keys: {list(item.keys())}')
        
        if 'wafr_architecture_data' in item:
            architecture_data = json.loads(item['wafr_architecture_data'])
            
            # Store in memory cache for faster subsequent access
            _architecture_data_cache[chat_id] = architecture_data
            
            services_count = len(architecture_data.get('identified_services', []))
            logger.info(f'✅ Retrieved architecture data from DynamoDB for chat_id={chat_id} ({services_count} services)')
            return architecture_data
        
        logger.warning(f'❌ No wafr_architecture_data field found in DynamoDB for chat_id={chat_id}')
        return None
        
    except Exception as e:
        logger.error(f'❌ Failed to retrieve architecture data from DynamoDB: {str(e)}')
        import traceback
        logger.error(f'❌ Traceback: {traceback.format_exc()}')
        return None


def _compress_architecture_data_for_storage(architecture_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compress architecture data for DynamoDB storage.
    
    Removes very large fields that can be regenerated, keeping essential data.
    
    Args:
        architecture_data: Full architecture data
        
    Returns:
        Compressed architecture data
    """
    import json
    
    def make_json_serializable(obj):
        """Recursively convert objects to JSON-serializable format."""
        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Convert objects with __dict__ (like DocumentInfo) to dict
            return make_json_serializable(obj.__dict__)
        elif hasattr(obj, 'to_dict'):
            # Some objects have a to_dict method
            return make_json_serializable(obj.to_dict())
        else:
            # Fallback: convert to string
            return str(obj)
    
    # First, make everything JSON serializable
    try:
        compressed = make_json_serializable(architecture_data)
    except Exception as e:
        logger.warning(f"Error making architecture_data serializable: {e}, using basic dict conversion")
        compressed = dict(architecture_data) if isinstance(architecture_data, dict) else {}
    
    # Remove very large text fields that aren't needed for pillar assessments
    # The pillar assessments primarily use identified_services, architectural_patterns, etc.
    fields_to_compress = ['raw_analysis', 'combined_insights']
    
    for field in fields_to_compress:
        if field in compressed and isinstance(compressed[field], str):
            # Keep first 5000 chars as summary
            if len(compressed[field]) > 5000:
                compressed[field] = compressed[field][:5000] + '... [truncated for storage]'
    
    # Compress document_analyses if present
    if 'document_analyses' in compressed:
        for doc_analysis in compressed.get('document_analyses', []):
            if isinstance(doc_analysis, dict):
                doc_info = doc_analysis.get('document_info', {})
                if isinstance(doc_info, dict) and 'raw_text' in doc_info:
                    raw_text = doc_info.get('raw_text', '')
                    if isinstance(raw_text, str) and len(raw_text) > 5000:
                        doc_info['raw_text'] = raw_text[:5000] + '... [truncated]'
    
    # Verify the result is JSON serializable
    try:
        json.dumps(compressed)
    except (TypeError, ValueError) as e:
        logger.error(f"Compressed data is not JSON serializable: {e}")
        # Return minimal essential data
        return {
            'identified_services': compressed.get('identified_services', []),
            'architectural_patterns': compressed.get('architectural_patterns', []),
            'success': compressed.get('success', True),
            'message': compressed.get('message', 'Architecture data compressed')
        }
    
    return compressed


def clear_architecture_data_cache(chat_id: Optional[str] = None) -> None:
    """
    Clear architecture data from memory cache.
    
    Args:
        chat_id: Specific chat ID to clear, or None to clear all
    """
    global _architecture_data_cache
    
    if chat_id:
        if chat_id in _architecture_data_cache:
            del _architecture_data_cache[chat_id]
            logger.debug(f'Cleared architecture data cache for chat_id={chat_id}')
    else:
        _architecture_data_cache.clear()  # Clear in place instead of reassigning
        logger.debug('Cleared all architecture data cache')
        logger.debug('Cleared all architecture data cache')


# ============================================================
# PILLAR ASSESSMENT CACHING (Issue 3 Fix)
# These functions cache pillar assessments in DynamoDB to prevent
# data loss when Bedrock compresses conversation context
# ============================================================

# In-memory cache for pillar assessments (fallback if DynamoDB fails)
_pillar_assessments_cache: Dict[str, Dict[str, Any]] = {}


async def cache_pillar_assessment(chat_id: str, pillar_name: str, assessment_data: Dict[str, Any]) -> bool:
    """
    Cache a single pillar assessment in DynamoDB for retrieval by generate_professional_report.
    
    This prevents pillar assessment data loss when Bedrock compresses conversation context
    (Issue 3: Pillar Assessment Data Loss).
    
    Args:
        chat_id: Chat session ID
        pillar_name: Name of the pillar (e.g., 'security', 'reliability')
        assessment_data: Full pillar assessment data
        
    Returns:
        bool: True if caching succeeded, False otherwise
    """
    logger.info(f'Caching pillar assessment for chat_id={chat_id}, pillar={pillar_name}')
    
    if not chat_id:
        logger.warning('Cannot cache pillar assessment - chat_id is empty')
        return False
    
    # Initialize chat entry in memory cache if needed
    if chat_id not in _pillar_assessments_cache:
        _pillar_assessments_cache[chat_id] = {}
    
    # Store in memory cache
    _pillar_assessments_cache[chat_id][pillar_name] = assessment_data
    logger.info(f'✅ Stored {pillar_name} assessment in memory cache for chat_id={chat_id}')
    
    # Log key metrics
    score = assessment_data.get('score', 0)
    caps_count = len(assessment_data.get('detected_capabilities', []))
    recs_count = len(assessment_data.get('recommendations', []))
    logger.info(f'📊 {pillar_name}: score={score}, capabilities={caps_count}, recommendations={recs_count}')
    
    try:
        import json
        import boto3
        from boto3.dynamodb.conditions import Key
        
        # Get DynamoDB table name from config
        config = get_sera_config()
        
        if not config or not config.get('DYNAMODB_TABLE_NAME'):
            logger.warning('❌ DynamoDB config not available, using memory cache only')
            return True  # Memory cache succeeded
        
        table_name = config['DYNAMODB_TABLE_NAME']
        region = config.get('AWS_REGION') or get_aws_region()
        
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # Query GSI to get primary key
        gsi_response = table.query(
            IndexName='chat-id-gsi',
            KeyConditionExpression=Key('chat_id').eq(chat_id),
            Limit=1
        )
        
        items = gsi_response.get('Items', [])
        if not items:
            logger.warning(f'❌ No chat record found for chat_id={chat_id}')
            return True  # Memory cache succeeded
        
        chat_record = items[0]
        user_id = chat_record.get('user_id')
        timestamp = chat_record.get('timestamp')
        
        if not user_id or not timestamp:
            logger.warning(f'❌ Missing primary key for chat_id={chat_id}')
            return True
        
        # Get existing pillar assessments from DynamoDB
        existing_assessments = {}
        if 'wafr_pillar_assessments' in chat_record:
            try:
                existing_assessments = json.loads(chat_record['wafr_pillar_assessments'])
            except (json.JSONDecodeError, TypeError):
                existing_assessments = {}
        
        # Add/update this pillar assessment
        existing_assessments[pillar_name] = assessment_data
        
        # Update DynamoDB
        table.update_item(
            Key={'user_id': user_id, 'timestamp': timestamp},
            UpdateExpression='SET wafr_pillar_assessments = :data, wafr_pillar_timestamp = :ts',
            ExpressionAttributeValues={
                ':data': json.dumps(existing_assessments),
                ':ts': datetime.now().isoformat()
            }
        )
        
        logger.info(f'✅ Cached {pillar_name} assessment in DynamoDB for chat_id={chat_id}')
        return True
        
    except Exception as e:
        logger.error(f'❌ Failed to cache pillar assessment in DynamoDB: {str(e)}')
        return True  # Memory cache succeeded


async def get_cached_pillar_assessments(chat_id: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Retrieve all cached pillar assessments for a chat session.
    
    This is used by generate_professional_report to get full pillar data
    when Bedrock passes compressed/minimal pillar_assessments.
    
    Args:
        chat_id: Chat session ID
        
    Returns:
        Dict mapping pillar names to their full assessment data, or None if not found
    """
    logger.info(f'🔍 Retrieving cached pillar assessments for chat_id={chat_id}')
    
    if not chat_id:
        logger.warning('❌ Cannot retrieve pillar assessments - chat_id is empty')
        return None
    
    # Check memory cache first
    if chat_id in _pillar_assessments_cache:
        cached = _pillar_assessments_cache[chat_id]
        logger.info(f'✅ Found {len(cached)} pillar assessments in memory cache')
        return cached
    
    logger.info(f'⚠️ Not in memory cache, trying DynamoDB...')
    
    try:
        import json
        import boto3
        from boto3.dynamodb.conditions import Key
        
        config = get_sera_config()
        
        if not config or not config.get('DYNAMODB_TABLE_NAME'):
            logger.warning('❌ DynamoDB config not available')
            return None
        
        table_name = config['DYNAMODB_TABLE_NAME']
        region = config.get('AWS_REGION') or get_aws_region()
        
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # Query GSI
        gsi_response = table.query(
            IndexName='chat-id-gsi',
            KeyConditionExpression=Key('chat_id').eq(chat_id),
            ProjectionExpression='wafr_pillar_assessments',
            Limit=1
        )
        
        items = gsi_response.get('Items', [])
        if not items:
            logger.warning(f'❌ No chat record found for chat_id={chat_id}')
            return None
        
        item = items[0]
        
        if 'wafr_pillar_assessments' in item:
            pillar_assessments = json.loads(item['wafr_pillar_assessments'])
            
            # Store in memory cache
            _pillar_assessments_cache[chat_id] = pillar_assessments
            
            logger.info(f'✅ Retrieved {len(pillar_assessments)} pillar assessments from DynamoDB')
            return pillar_assessments
        
        logger.warning(f'❌ No wafr_pillar_assessments found for chat_id={chat_id}')
        return None
        
    except Exception as e:
        logger.error(f'❌ Failed to retrieve pillar assessments from DynamoDB: {str(e)}')
        return None


def clear_pillar_assessments_cache(chat_id: Optional[str] = None) -> None:
    """
    Clear pillar assessments from memory cache.
    
    Args:
        chat_id: Specific chat ID to clear, or None to clear all
    """
    global _pillar_assessments_cache
    
    if chat_id:
        if chat_id in _pillar_assessments_cache:
            del _pillar_assessments_cache[chat_id]
            logger.debug(f'Cleared pillar assessments cache for chat_id={chat_id}')
    else:
        _pillar_assessments_cache.clear()
        logger.debug('Cleared all pillar assessments cache')
