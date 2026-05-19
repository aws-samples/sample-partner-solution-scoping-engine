# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Service for handling chat operations.
"""
import logging
import uuid
import re
import json
import os
import boto3
import asyncio
import concurrent.futures
import tempfile
import time
from datetime import datetime
from flask import current_app
from botocore.config import Config
from services.db_service import ddb_update_item
from ..models.chat import save_chat, get_chat, list_chats_for_user, save_chat_message, update_conversation_stage
from ..models.chat_variables import update_chat_variables
from .document_processor import DocumentProcessor
from ..config.personas import PersonaManager
from ..config.app_config import CustomerConfig
from .bedrock_service import BedrockService
from .mcp_server_manager import MCPServerManager
from ..services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class ResponseDeduplicator:
    def __init__(self):
        self.recent_responses = {}
    
    def is_duplicate(self, chat_id, content_start):
        key = f"{chat_id}:{content_start[:50]}"
        now = time.time()
        
        # Clean up old entries periodically
        if len(self.recent_responses) > 100:
            self.recent_responses = {k: v for k, v in self.recent_responses.items() if now - v < 60}
        
        if key in self.recent_responses:
            if now - self.recent_responses[key] < 30:  # 30 second window
                return True
        
        self.recent_responses[key] = now
        return False

# Global deduplicator instance
_response_deduplicator = ResponseDeduplicator()

def normalize_filename_for_classification(filename):
    """
    Normalize filename for consistent classification mapping.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Normalized filename using secure_filename transformation
    """
    from werkzeug.utils import secure_filename
    return secure_filename(filename)

def map_classification_to_document_type(classification):
    """
    Map frontend file classifications to document types for grouping in Documents section.
    Uses centralized mapping from config.json.
    
    Args:
        classification (str): Frontend classification (sow_document, architecture_diagram, etc.)
        
    Returns:
        str: Document type for grouping
    """
    if not classification:
        return "user_upload"
    
    try:
        from flask import current_app
        file_classification_config = current_app.config.get('FILE_CLASSIFICATION_CONFIG', {})
        classification_mapping = file_classification_config.get('document_type_mapping', {})
        
        mapped_type = classification_mapping.get(classification, "user_upload")
        logger.debug(f"Mapped classification '{classification}' to document_type '{mapped_type}'")
        return mapped_type
        
    except Exception as e:
        logger.warning(f"Error accessing classification mapping from config: {e}")
        # Fallback mapping if config is not available
        fallback_mapping = {
            'sow_document': 'sow_document',
            'architecture_diagram': 'diagram',
            'pricing_calculator_csv': 'pricing_report',
            'funding_document': 'funding_document',
            'technical_document': 'user_upload',
            'contract': 'user_upload',
            'presentation': 'user_upload',
        }
        return fallback_mapping.get(classification, "user_upload")

def add_system_message_to_chat(chat_id: str, message: str, message_id: str = None) -> None:
    """
    Add a system message to the chat history.
    
    Args:
        chat_id (str): The chat ID
        message (str): The system message to add
        message_id (str, optional): Specific message ID to use (for cross-chat consistency)
    """
    try:
        from ..models.chat import get_chat_by_chat_id
        from ..services.db_service import ddb_update_item
        
        # Get the chat to verify it exists
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            logger.error(f"Chat {chat_id} not found when adding system message")
            return
        
        # Use provided message_id or generate new one
        msg_id = message_id if message_id else str(uuid.uuid4())
        
        # Create system message in DynamoDB format
        system_message = {
            'M': {
                'message_id': {'S': msg_id},
                'role': {'S': 'system'},
                'content': {'S': message},
                'message_timestamp': {'S': datetime.utcnow().isoformat()}
            }
        }
        
        # Update chat using DynamoDB list_append
        ddb_update_item(
            key={
                'user_id': {'S': chat['user_id']},
                'timestamp': {'S': chat['timestamp']}
            },
            update_expression='SET chat_message_history = list_append(if_not_exists(chat_message_history, :empty_list), :msg)',
            expression_attribute_values={
                ':empty_list': {'L': []},
                ':msg': {'L': [system_message]}
            }
        )
        
        logger.info(f"Added system message to chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error adding system message to chat {chat_id}: {e}")


def update_chat_with_bot_id(chat_id, bot_id):
    """Update chat record with bot ID"""
    try:
        from models.chat import get_chat_by_chat_id
        
        # Get the chat first
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            raise Exception(f"Chat {chat_id} not found")
        
        # Update the chat record with bot_id
        key = {
            'user_id': {'S': chat['user_id']},
            'timestamp': {'S': chat['timestamp']}
        }
        
        update_expression = "SET bot_id = :bot_id, updated_at = :updated_at"
        expression_values = {
            ':bot_id': {'S': bot_id},
            ':updated_at': {'S': datetime.now().isoformat()}
        }
        
        success = ddb_update_item(
            key,
            update_expression,
            expression_values
        )
        
        if success:
            logger.info(f"Updated chat {chat_id} with bot_id {bot_id}")
            return True
        else:
            logger.error(f"Failed to update chat {chat_id} with bot_id {bot_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error updating chat with bot_id: {str(e)}")
        raise e

def sanitize_filename_for_bedrock(filename):
    """
    Sanitize filename to meet Bedrock's document naming requirements.
    
    This function is deprecated - use DocumentProcessor.sanitize_filename_for_bedrock() instead.
    Kept for backward compatibility.
    """
    return DocumentProcessor.sanitize_filename_for_bedrock(filename)
from ..config.personas import PersonaManager
from ..config.app_config import CustomerConfig
from .bedrock_service import BedrockService
from .mcp_server_manager import MCPServerManager
from ..services.document_processor import DocumentProcessor
import tempfile

def save_diagram_code(chat_id, diagram_code):
    """Save diagram code to S3 as diagram_code.py"""
    try:
        # Create temporary file with diagram code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(diagram_code)
            temp_file_path = temp_file.name
        
        # Upload to S3
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        s3_key = f"{chat_id}/diagram_code.py"
        
        s3_client = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        s3_client.upload_file(temp_file_path, bucket_name, s3_key, 
                             ExtraArgs={'ContentType': 'text/plain'})
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        logger.debug(f"Saved diagram code to S3: s3://{bucket_name}/{s3_key}")
        
    except Exception as e:
        logger.error(f"Error saving diagram code to S3: {e}")

# Use a singleton pattern with lazy loading
_bedrock_service = None
_mcp_manager = None  # Singleton instance of MCPServerManager

def get_mcp_manager():
    """Get the MCPServerManager instance, creating it if necessary."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPServerManager.get_instance()
        logger.debug("Created MCPServerManager instance")
    return _mcp_manager

def extract_variables_from_response(response_text, chat_id=None):
    """
    Extract variables from the model's response text.
    
    Args:
        response_text (str): The model's response text
        chat_id (str): Chat ID for saving diagram code
        
    Returns:
        dict: Dictionary of extracted variables
    """
    variables = {}
    
    # Extract variables using regex patterns
    patterns = {
        # Match content between quotes after the variable name
        'aws-managed-solution': r'{{aws-managed-solution}}.*?[\'"](.+?)[\'"]',
        'customer-managed-solution': r'{{customer-managed-solution}}.*?[\'"](.+?)[\'"]',
        'hybrid-solution': r'{{hybrid-solution}}.*?[\'"](.+?)[\'"]',
        'recommended-solution': r'{{recommended-solution}}.*?[\'"](.+?)[\'"]',
        'sales-pitch': r'{{sales-pitch}}.*?[\'"](.+?)[\'"]',
        
        # For questions, we need to capture potentially multi-line content
        'high-level-questions': r'{{high-level-questions}}.*?\[(.*?)\]',
        'deep-dive-questions': r'{{deep-dive-questions}}.*?\[(.*?)\]',
        'packaging-questions': r'{{packaging-questions}}.*?\[(.*?)\]',
        
        # For pricing and diagram, capture structured content
        'pricing': r'{{pricing}}.*?\{(.*?)\}',
        'diagram': r'{{diagram}}.*?```python\s*(.*?)\s*```',
    }
    
    # Extract each variable using its pattern
    for var_name, pattern in patterns.items():
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            variables[var_name] = match.group(1).strip()
            logger.debug(f"Extracted variable {var_name}: length={len(variables[var_name])}")
            
            # Save diagram code to S3 if extracted
            if var_name == 'diagram' and chat_id:
                save_diagram_code(chat_id, variables[var_name])
    
    return variables

def get_bedrock_service():
    """Get the BedrockService instance, creating it if necessary."""
    global _bedrock_service
    if _bedrock_service is None:
        # Get the AWS region from app config
        region = current_app.config['AWS_REGION']
        
        # Create the base config with retry settings and increased timeout for CloudFormation generation and POC funding analysis
        boto_config = Config(
            region_name=region,
            read_timeout=600,  # Increased to 600s (10 minutes) for CloudFormation template generation and POC funding analysis
            connect_timeout=10
        )
        
        # Add cross-region inference only if secondary regions are configured
        """ if 'BEDROCK_SECONDARY_REGIONS' in current_app.config['CUSTOMER_CONFIG']:
            secondary_regions = current_app.config['CUSTOMER_CONFIG']['BEDROCK_SECONDARY_REGIONS']
            
            # Convert string to list if needed
            if isinstance(secondary_regions, str):
                secondary_regions = [secondary_regions]
                
            # Only add if we have valid secondary regions
            if secondary_regions:
                try:
                    boto_config = boto_config.merge(Config(
                        cross_region_inference_profile={
                            "primaryRegion": region,
                            "secondaryRegions": secondary_regions
                        }
                    ))
                    logger.debug(f"Enabled cross-region inference with secondary regions: {secondary_regions}")
                except TypeError:
                    # This version of boto3/botocore doesn't support cross_region_inference_profile
                    logger.warning(f"Cross-region inference not supported in this boto3 version. Using primary region only: {region}") """
        
        # Create a Bedrock client with profile if configured
        if CustomerConfig.should_use_bedrock_profile():
            profile_name = CustomerConfig.get_bedrock_aws_profile()
            session = boto3.Session(profile_name=profile_name)
            bedrock_client = session.client('bedrock-runtime', config=boto_config)
            # Debug: Check which account we're using
            sts_client = session.client('sts')
            caller_identity = sts_client.get_caller_identity()
            logger.debug(f"BEDROCK USING PROFILE '{profile_name}' - Account: {caller_identity['Account']}, ARN: {caller_identity['Arn']}")
        else:
            bedrock_client = boto3.client('bedrock-runtime', config=boto_config)
            # Debug: Check which account we're using with default credentials
            sts_client = boto3.client('sts')
            caller_identity = sts_client.get_caller_identity()
            logger.debug("BEDROCK USING DEFAULT CREDENTIALS - credentials validated")
        
        # Get the model ID from config
        model_id = current_app.config['CUSTOMER_CONFIG'].get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0')
        
        # Get the MCP manager instance
        mcp_manager = get_mcp_manager()
        
        # Create the BedrockService instance
        _bedrock_service = BedrockService(bedrock_client, model_id, mcp_manager)
        logger.debug(f"Created BedrockService with model_id: {model_id}")
    
    return _bedrock_service

def create_chat(user_id, assistant_id, customer_id, interaction_type, chat_name=None):
    """
    Create a new chat session.
    
    Args:
        user_id (str): ID of the user creating the chat
        assistant_id (str): ID of the selected assistant persona
        customer_id (str): ID of the selected customer persona
        interaction_type (str): Type of interaction (e.g., 'chat', 'email')
        chat_name (str, optional): Custom name for the chat
        
    Returns:
        dict: Created chat session
    """
    try:
        # Generate a unique conversation ID
        chat_id = str(uuid.uuid4())
        
        # Use provided chat name or generate a default one
        if not chat_name or not chat_name.strip():
            # Generate a default chat name in the format "Chat-<last 5 of UUID>-dated-<MM-DD-YYYY>"
            last_5_uuid = chat_id[-5:]
            current_date = datetime.utcnow().strftime("%m-%d-%Y")
            chat_name = f"Chat-{last_5_uuid}-dated-{current_date}"
        else:
            chat_name = chat_name.strip()
        
        # Create chat data with all required fields
        chat_data = {
            'chat_id': chat_id,
            'user_id': user_id,
            'assistant_persona': assistant_id,
            'customer_persona': customer_id,
            'interaction_method': interaction_type,
            'timestamp': datetime.utcnow().isoformat(),
            'chat_message_history': [],
            'stage': 'INITIAL',  # Start with INITIAL stage
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'chat_name': chat_name  # Add the default chat name
        }
        
        logger.debug(f"Creating new chat session with ID: {chat_id} and name: {chat_name}")
        logger.debug(f"Chat data: {chat_data}")
        
        # Save the chat to DynamoDB
        save_chat(chat_data)
        
        # Initialize MCP tools for the new chat is handled in the route
        
        logger.debug(f"Successfully created chat session: {chat_id}")
        return chat_data
    except Exception as e:
        logger.error(f"Error creating chat: {e}", exc_info=True)
        raise



def send_message(chat_id, user_id, content, stream=False):
    """
    Send a message to a chat session and get AI response.
    
    Args:
        chat_id (str): ID of the chat session
        user_id (str): ID of the user sending the message
        content (str): Message content
        stream (bool): Whether to stream the response
        
    Returns:
        dict: Updated chat session with new messages
    """
    try:
        # Get the chat session
        chat = get_chat(chat_id)
        if not chat:
            raise ValueError(f"Chat session {chat_id} not found")
        
        if chat['user_id'] != user_id:
            raise ValueError("User not authorized to send messages to this chat")
        
        # Add user message
        user_message = {
            'role': 'user',
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        }
        chat['messages'].append(user_message)
        
        # Prepare messages for Bedrock (filter out system messages)
        messages = [
            {
                'role': msg['role'],
                'content': msg['content']
            }
            for msg in chat['messages']
            if msg['role'] != 'system'  # Skip system messages - Bedrock only accepts 'user' and 'assistant'
        ]
        
        # Get system prompt based on assistant and customer - with validation
        assistant_persona = chat.get('assistant_persona')
        customer_persona = chat.get('customer_persona')
        if not assistant_persona or not customer_persona:
            logger.error(f"Chat {chat_id} missing required persona fields - assistant: {assistant_persona}, customer: {customer_persona}")
            raise ValueError(f"Chat {chat_id} is missing required persona fields")
        system_prompt = f"You are {assistant_persona} interacting with {customer_persona}."
        
        # Replace bedrock_service with get_bedrock_service()
        service = get_bedrock_service()
        
        if stream:
            # For streaming, we'll return a generator
            def stream_response():
                # Save the chat with user message first
                save_chat(chat)
                
                # Stream the response
                for chunk in service.converse_stream(messages, system_prompt):
                    if chunk['type'] == 'content':
                        yield chunk['content']
                    elif chunk['type'] == 'stop':
                        # Add AI message to chat and save                        
                        ai_message = {
                            'role': 'assistant',
                            'content': ''.join(streamed_content),
                            'timestamp': datetime.utcnow().isoformat()
                        }                        
                        logger.debug(f'Saving streaming assistance message to Dynamo: message_id={ai_message.get("message_id")}')
                        chat['messages'].append(ai_message)
                        save_chat(chat)
                        break
            return stream_response()
        else:
            # For non-streaming, get complete response
            response = service.converse(messages, system_prompt)
            
            # Add AI message to chat
            ai_message = {
                'role': 'assistant',
                'content': response['content'],
                'timestamp': datetime.utcnow().isoformat()
            }
            chat['messages'].append(ai_message)
            logger.debug(f'Saving streaming non-streaming message to Dynamo: message_id={ai_message.get("message_id")}')
            # Save updated chat
            save_chat(chat)
            return chat
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise

def process_user_message_stream(chat_id, user_id, content, intent=None, existing_messages=None, files=None, file_objects=None, frontend_message_id=None):
    """
    Process a user message and return a streaming response generator.
    
    Args:
        chat_id (str): The ID of the chat session
        user_id (str): The ID of the user
        content (str): The message content
        intent (str, optional): Explicit intent for tool selection
        existing_messages (list, optional): Existing messages to use instead of loading from DB
        files (list, optional): List of uploaded file metadata for DynamoDB storage
        file_objects (list, optional): List of file objects with content for Bedrock
        frontend_message_id (str, optional): Frontend temporary message ID for tracking
        
    Returns:
        generator: A generator that yields response chunks
    """
    try:
        # If existing_messages is provided, use those instead of loading from DB
        if existing_messages:
            messages = existing_messages
            logger.debug(f"Using {len(messages)} provided messages instead of loading from DB")
        else:
            # Check if this is an SA trying to interact with someone else's chat
            from ..middleware.auth_middleware import get_current_user
            from ..models.support_relationship import user_supports_seller
            from ..models.sa_review import copy_chat_for_sa_review, get_sa_copy_for_original
            
            current_user = get_current_user()
            is_sa_review = False
            original_chat_id = None
            sa_copy_just_created = False  # Flag to track if we just created an SA copy
            
            # Try to get the chat session - first try as the user's own chat
            updated_chat = get_chat_session(user_id, chat_id)
            
            # If not found, check if this is an SA accessing someone else's chat
            if not updated_chat:
                logger.debug(f"Chat not found for user {user_id}, checking if SA can access chat {chat_id}")
                
                # Get the chat by chat_id to see who owns it
                from ..models.chat import get_chat_by_chat_id
                original_chat = get_chat_by_chat_id(chat_id)
                
                if not original_chat:
                    raise ValueError(f"Chat session {chat_id} not found")
                
                original_owner = original_chat.get('user_id')
                
                # Check if current user supports the original owner
                if user_supports_seller(user_id, original_owner):
                    logger.debug(f"SA {user_id} can access chat {chat_id} owned by {original_owner}")
                    
                    # Check if this is an SA copy or original chat
                    if original_chat.get('source_chat_id'):
                        # This is already an SA copy
                        updated_chat = original_chat
                        is_sa_review = True
                        original_chat_id = original_chat.get('source_chat_id')
                        logger.debug(f"Using existing SA copy {chat_id} for original {original_chat_id}")
                    else:
                        # This is the original chat - need to create/get SA copy
                        original_chat_id = chat_id
                        
                        # Check if SA copy already exists
                        existing_sa_copy = get_sa_copy_for_original(original_chat_id, user_id)
                        
                        if existing_sa_copy and existing_sa_copy.get('review_status') not in ['merged', 'reassigned']:
                            # Use existing SA copy (only if it's still active)
                            updated_chat = existing_sa_copy
                            chat_id = existing_sa_copy.get('chat_id')  # Switch to SA copy chat_id
                            is_sa_review = True
                            logger.debug(f"Using existing SA copy {chat_id} for original {original_chat_id}")
                        else:
                            # Create new SA copy
                            logger.info(f"Creating SA copy for original chat {original_chat_id} by SA {user_id}")
                            sa_copy = copy_chat_for_sa_review(original_chat_id, user_id)
                            updated_chat = sa_copy
                            chat_id = sa_copy.get('chat_id')  # Switch to SA copy chat_id
                            is_sa_review = True
                            sa_copy_just_created = True  # Mark that we just created the copy
                            logger.debug(f"Created new SA copy {chat_id} for original {original_chat_id}")
                else:
                    raise ValueError(f"User {user_id} does not have permission to access chat {chat_id}")
            else:
                # Check if this is already an SA copy
                if updated_chat.get('source_chat_id'):
                    is_sa_review = True
                    original_chat_id = updated_chat.get('source_chat_id')
                    logger.debug(f"Working with SA copy {chat_id} for original {original_chat_id}")
            
            # Log the current state of the chat session
            current_stage = updated_chat.get('stage', 'INITIAL')
            logger.debug(f"CONVERSATION_STATE: chat_id='{chat_id}', stage='{current_stage}', intent='{intent or 'None'}', is_sa_review={is_sa_review}")
            
            # Log the current state of the chat session
            logger.debug(f"CHAT_SESSION: chat_id='{chat_id}', message_count={len(updated_chat.get('messages', []))}")
            
            # Update SA last activity if this is an SA review
            if is_sa_review:
                from ..models.chat import update_chat_field
                current_time = datetime.utcnow().isoformat()
                try:
                    update_chat_field(chat_id, 'sa_last_activity', current_time)
                    logger.debug(f"Updated SA last activity for {chat_id}")
                except Exception as e:
                    logger.warning(f"Failed to update SA last activity: {e}")
            
            # Check if this is an SA review initiation message that shouldn't go to LLM
            is_review_initiation = (
                sa_copy_just_created or 
                (is_sa_review and content and any(phrase in content.lower() for phrase in [
                    'let me review', 'i will review', 'reviewing this', 'review the solution',
                    'start review', 'begin review'
                ]))
            )
            
            # If this is an SA review initiation, return a simple acknowledgment without LLM processing
            if is_review_initiation:
                logger.info(f"SA review initiation detected - returning acknowledgment without LLM processing (just_created={sa_copy_just_created})")
                
                # Add the user message to the SA copy for record keeping
                if content:
                    user_message = {
                        'message_id': str(uuid.uuid4()),
                        'role': 'user',
                        'content': content,
                        'message_timestamp': datetime.utcnow().isoformat()
                    }
                    save_chat_message(user_id, chat_id, user_message)
                    logger.debug(f"Saved SA review initiation message to chat {chat_id}")
                
                # Return a simple acknowledgment message
                acknowledgment = f"SA Review started for chat {original_chat_id}. You are now working in SA copy {chat_id}. All your changes will be tracked separately from the original chat."
                
                def simple_generator():
                    logger.debug(f"Yielding acknowledgment message for SA review initiation")
                    yield acknowledgment
                
                logger.debug(f"About to return simple generator - should stop LLM processing")
                return simple_generator()
            
            # Initialize variables for generator scope
            message_id = None
            updated_content = None
            
            # Add user message to chat if content or files are provided
            if content or files or file_objects:
                # Create initial display content for DynamoDB (text only)
                display_content = content.strip() if content else ""
                                
                logger.debug(f"USER_MESSAGE_CONTENT: length={len(content) if content else 0}")
                
                # Create initial user message
                user_message = {
                    'message_id': str(uuid.uuid4()),
                    'frontend_message_id': frontend_message_id,  # Store frontend ID for tracking
                    'role': 'user',
                    'content': display_content,  # Initial content (may be updated)
                    'message_timestamp': datetime.utcnow().isoformat()
                }
                
                message_id = user_message['message_id']
                
                # Process files if any
                updated_content = display_content
                if files:
                    logger.info(f"Processing {len(files)} uploaded files for message {message_id}")
                    
                    # 1. Save files to documents attribute
                    file_links = []
                    for i, file_metadata in enumerate(files):
                        doc_id = f"upload_{file_metadata['version_id']}"
                        
                        # Get classification from frontend and map to document type
                        document_classification = file_metadata.get('document_classification', 'user_upload')
                        document_type = map_classification_to_document_type(document_classification)
                        
                        document_entry = {
                            "document_type": document_type,  # Use mapped document type
                            "tool_name": "user_uploaded",  # Fixed: use tool_name instead of source
                            "s3_key": file_metadata['s3_key'],
                            "version_id": file_metadata['version_id'],
                            "approved": False,  # User uploads require approval
                            "approved_by": None,  # Initially no approver
                            "created_timestamp": file_metadata['upload_timestamp'],
                            "original_filename": file_metadata['original_filename'],
                            "content_type": file_metadata['type'],
                            "file_size": file_metadata['file_size'],
                            "name": file_metadata['original_filename'],
                            "message_id": message_id  # Link to message for reference
                        }
                        
                        # Save to documents attribute
                        from ..models.chat import update_chat_document
                        update_chat_document(chat_id, doc_id, document_entry)
                        
                        # Create file link for message
                        filename = file_metadata['original_filename']
                        s3_url = file_metadata['s3_url']
                        version_id = file_metadata['version_id']
                        content_type = file_metadata['type']
                        
                        # Check if this is an image file based on extension
                        file_extension = os.path.splitext(filename)[1].lower().lstrip('.')
                        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']
                        is_image = file_extension in image_extensions
                        
                        # Check if user sent no message content (files only)
                        user_sent_no_message = not display_content or not display_content.strip()
                        
                        # Generate appropriate markdown format
                        if is_image and user_sent_no_message:
                            # For image files when user sent no message, use image format for inline display
                            file_link = f"![{filename}]({s3_url}?versionId={version_id})"
                            logger.debug(f"Generated image format for {filename}: ![{filename}](...)")
                        else:
                            # For all other cases, use link format
                            file_link = f"[{filename}]({s3_url}?versionId={version_id})"
                            logger.debug(f"Generated link format for {filename}: [{filename}](...)")
                        
                        file_links.append(file_link)
                        
                        logger.info(f"DOCUMENT_SAVE: Saved {filename} as {document_type} (classification: {document_classification}, approved: False)")
                    
                    # 2. Use the enhanced message from MessageProcessor - it already contains proper file formatting
                    # MessageProcessor enhancers handle persona-specific file formatting, eliminating duplicates
                    updated_content = display_content
                    logger.info(f"FILE_FORMATTING: Using MessageProcessor enhanced content for all personas (no duplicate messages)")
                    
                    # Update the message in DynamoDB
                    updated_user_message = {
                        'message_id': message_id,
                        'role': 'user',
                        'content': updated_content,
                        'message_timestamp': user_message['message_timestamp']
                    }
                    
                    # Save the final message with file links
                    save_chat_message(user_id, chat_id, updated_user_message)
                    
                    logger.info(f"Saved user message {message_id} with {len(files)} file links")
                else:
                    # No files to process, save the original message
                    save_chat_message(user_id, chat_id, user_message)
                    logger.info(f"Saved user message {message_id} without files")
                
                # Get the updated chat with the new message included
                updated_chat = get_chat_session(user_id, chat_id)
            
            # Get assistant persona ID early for use in message processing - strict validation
            assistant_persona_id = updated_chat.get('assistant_persona')
            if not assistant_persona_id:
                logger.error(f"Chat {chat_id} missing required assistant_persona field - data corruption detected")
                raise ValueError(f"Chat {chat_id} is missing required assistant_persona field")
            
            # Extract all messages from this specific chat's message history
            messages = []
            if 'messages' in updated_chat:
                logger.debug(f"Found {len(updated_chat['messages'])} messages in chat {chat_id}")
                
                # Debug the structure of the messages
                logger.debug(f"Message structure: {type(updated_chat['messages'])}")
                if updated_chat['messages']:
                    logger.debug(f"First message structure: {type(updated_chat['messages'][0])}")
                    # logger.debug(f"First message content: {updated_chat['messages'][0]}") # TURNED OFF
                
                # Handle different possible structures
                for msg in updated_chat['messages']:
                    # Check if this is a DynamoDB formatted message
                    if isinstance(msg, dict) and 'M' in msg:
                        # DynamoDB format
                        msg_dict = msg['M']
                        role = msg_dict.get('role', {}).get('S', 'user')
                        content_value = msg_dict.get('content', {}).get('S', '')
                        
                        # Skip system messages - Bedrock only accepts 'user' and 'assistant' roles
                        if role == 'system':
                            logger.debug(f"Skipping system message")
                            continue
                        
                        # Messages are already properly formatted by MessageProcessor before DynamoDB storage
                        if content_value and content_value.strip():
                            messages.append({
                                'role': role,
                                'content': content_value
                            })
                            logger.debug(f"Added DynamoDB formatted message: role={role}, length={len(content_value)}")
                    elif isinstance(msg, dict):
                        # Regular dict format
                        role = msg.get('role', 'user')
                        content_value = msg.get('content', '')
                        
                        # Skip system messages - Bedrock only accepts 'user' and 'assistant' roles
                        if role == 'system':
                            logger.debug(f"Skipping system message")
                            continue
                        
                        # Messages are already properly formatted by MessageProcessor before DynamoDB storage
                        if content_value and content_value.strip():
                            messages.append({
                                'role': role,
                                'content': content_value
                            })
                            logger.debug(f"Added dict formatted message: role={role}, length={len(content_value)}")
        
        # Add the current message (with files if provided) - only if we have files to add
        # If we only have text content, it was already saved to DynamoDB and loaded above
        if file_objects:
            # Create message with file content for Bedrock using ContentBlock format
            message_content = []
            
            # Add text content if provided (even if empty, but not None)
            text_content = content.strip() if content else ""
            
            # Always add text content - either user's message or default prompt
            if not text_content and file_objects:
                text_content = "Please analyze the uploaded files."
            elif not text_content and not file_objects:
                text_content = "Hello"  # Fallback for edge case
            
            message_content.append({"text": text_content})
            logger.debug(f"Added text content to Bedrock message: length={len(text_content)}")
            
            # Add file content directly to Bedrock message using proper ContentBlock format
            for file_obj in file_objects:
                formatted_block = DocumentProcessor.format_file_for_bedrock(file_obj)
                if formatted_block:
                    message_content.append(formatted_block)
            
            # If no content was added, add a default message
            if not message_content:
                message_content = [{"text": "Analyze the uploaded files."}]
            
            # Replace the last message (which is the text-only version) with the file version
            # or add as new message if no existing messages
            new_message = {
                'role': 'user',
                'content': message_content
            }
            
            # Check if the last message is the same text content we just saved
            if (messages and messages[-1]['role'] == 'user' and 
                isinstance(messages[-1]['content'], str) and 
                messages[-1]['content'].strip() == text_content):
                # Replace the last message with the file version
                messages[-1] = new_message
                logger.debug(f"Replaced last text-only message with file version")
            else:
                # Add as new message
                messages.append(new_message)
                logger.debug(f"Added new message with files")
            
            logger.debug(f"Message with {len(file_objects)} file objects using ContentBlock format")
            logger.debug(f"Message content blocks: {len(message_content)}")
            for i, block in enumerate(message_content):
                if 'text' in block:
                    logger.debug(f"  Block {i}: text - length={len(block['text'])}")
                elif 'document' in block:
                    logger.debug(f"  Block {i}: document - {block['document']['name']} (format: auto-detected)")
                    logger.debug(f"    Document bytes length: {len(block['document']['source']['bytes'])}")
                elif 'image' in block:
                    logger.debug(f"  Block {i}: image - {block['image']['format']}")
                    logger.debug(f"    Image bytes length: {len(block['image']['source']['bytes'])}")
            
            # Log the complete message structure being sent to Bedrock
            logger.debug(f"COMPLETE_MESSAGE_TO_BEDROCK:")
            logger.debug(f"  Role: {new_message['role']}")
            logger.debug(f"  Content type: {type(new_message['content'])}")
            logger.debug(f"  Content length: {len(new_message['content'])}")
            
            # Log a sample of the actual structure (without full base64 content)
            sample_content = []
            for block in new_message['content']:
                if 'text' in block:
                    sample_content.append({'text': block['text'][:100] + '...' if len(block['text']) > 100 else block['text']})
                elif 'document' in block:
                    sample_content.append({
                        'document': {
                            'name': block['document']['name'],
                            'format': block['document'].get('format', 'unknown'),
                            'source': {'bytes': f'[{len(block["document"]["source"]["bytes"])} raw bytes]'}
                        }
                    })
                elif 'image' in block:
                    sample_content.append({
                        'image': {
                            'format': block['image']['format'],
                            'source': {'bytes': f'[{len(block["image"]["source"]["bytes"])} raw bytes]'}
                        }
                    })
            logger.debug(f"  Sample content structure: {sample_content}")
        
        
        # Log final message count and structure for debugging
        logger.debug(f"FINAL_MESSAGES_FOR_BEDROCK: {len(messages)} messages")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, list):
                logger.debug(f"  Message {i}: {role} - {len(content)} content blocks")
                # Check if this message has files
                has_files_in_msg = any('document' in block or 'image' in block for block in content if isinstance(block, dict))
                if has_files_in_msg:
                    logger.debug(f"    Message {i} contains files - tools will be excluded")
            else:
                content_preview = content[:50] + "..." if len(str(content)) > 50 else str(content)
                logger.debug(f"  Message {i}: {role} - '{content_preview}'")
        
        # Handle case where no messages were extracted but we have files or content
        # This should only happen if no messages were saved to DynamoDB (edge case)
        if not messages and (content and content.strip() or file_objects):
            if file_objects:
                # Create message with file content for Bedrock using ContentBlock format
                message_content = []
                
                # Add text content if provided (even if empty, but not None)
                text_content = content.strip() if content else ""
                
                # Always add text content - either user's message or default prompt
                if not text_content and file_objects:
                    text_content = "Please analyze the uploaded files."
                elif not text_content and not file_objects:
                    text_content = "Hello"  # Fallback for edge case
                
                message_content.append({"text": text_content})
                logger.debug(f"Added text content to Bedrock message: length={len(text_content)}")
                
                # Add file content directly to Bedrock message using proper ContentBlock format
                for file_obj in file_objects:
                    formatted_block = DocumentProcessor.format_file_for_bedrock(file_obj)
                    if formatted_block:
                        message_content.append(formatted_block)
                
                # If no content was added, add a default message
                if not message_content:
                    message_content = [{"text": "Analyze the uploaded files."}]
                
                messages = [{
                    'role': 'user',
                    'content': message_content
                }]
                logger.debug(f"Created initial Bedrock message with {len(file_objects)} file objects using ContentBlock format")
            else:
                # Text-only message
                messages = [{
                    'role': 'user',
                    'content': content
                }]
                logger.debug(f"Created initial text-only message: length={len(content)}")
        
        # Check if this is the first message and set as initial question
        try:
            if (content or file_objects) and len(messages) <= 2:  # Only the current message exists or first response
                initial_question = content or f"[Uploaded {len(file_objects)} file(s)]" if file_objects else ""
                if file_objects and content:
                    initial_question = f"{content}"
                update_chat_variables(user_id, chat_id, {'initial-question': initial_question})
                logger.debug(f"Set initial question for chat {chat_id}: {initial_question[:50]}...")
        except Exception as e:
            logger.error(f"Failed to set initial question: {e}", exc_info=True)
            # Continue even if this fails
        
        # Get the proper system prompt from the persona management system
        persona_manager = PersonaManager()
        
        # Get customer persona and interaction method with strict validation
        customer_persona_id = updated_chat.get('customer_persona')
        if not customer_persona_id:
            logger.error(f"Chat {chat_id} missing required customer_persona field - data corruption detected")
            raise ValueError(f"Chat {chat_id} is missing required customer_persona field")
            
        interaction_method = updated_chat.get('interaction_method')
        if not interaction_method:
            logger.error(f"Chat {chat_id} missing required interaction_method field - data corruption detected")
            raise ValueError(f"Chat {chat_id} is missing required interaction_method field")
        
        # Get the assistant persona with its full system prompt
        # Using default user groups for now - this should be updated with actual user groups
        assistant_persona = persona_manager.get_assistant_persona(assistant_persona_id, ["sera_sales_person"])
        customer_persona = persona_manager.get_customer_persona(customer_persona_id)
        
        if not assistant_persona:
            logger.warning(f"Assistant persona {assistant_persona_id} not found, using generic prompt")
            system_prompt = f"You are an AWS assistant interacting with {customer_persona_id} via {interaction_method}."
            # Add chat session context for tools that need chat_id
            system_prompt += f"\n\nIMPORTANT: When using tools that require a chat_id parameter, always use this exact chat session ID: {chat_id}"
        else:
            # Use the rich system prompt from the persona management system
            # Replace placeholders in the system prompt
            system_prompt = assistant_persona.system_prompt
            
            # ONLY replace single-bracketed variables, NOT double-bracketed ones
            # Get actual user's first name
            current_user = get_current_user()
            user_first_name = current_user.first_name if current_user and current_user.first_name else "User"
            
            system_prompt = system_prompt.replace("{user_first_name}", user_first_name)
            system_prompt = system_prompt.replace("{customer_persona}", customer_persona.name if customer_persona else customer_persona_id)
            system_prompt = system_prompt.replace("{interaction_method}", interaction_method)
            
            # Add chat session context for tools that need chat_id
            system_prompt += f"\n\nIMPORTANT: When using tools that require a chat_id parameter, always use this exact chat session ID: {chat_id}"
            
            # Add current conversation stage context
            current_stage = updated_chat.get('stage', 'INITIAL')
            system_prompt += f"\n\nCURRENT CONVERSATION STAGE: {current_stage}"
            system_prompt += f"\nYou MUST call update_conversation_stage tool if the conversation has progressed beyond the current stage."
            
            
            logger.debug(f"Replaced single-bracketed variables in system prompt")
        
        logger.debug(f"Using system prompt for assistant {assistant_persona_id}")
        # System prompt content not logged to protect customer data
        logger.debug(f"Sending {len(messages)} messages to Bedrock")
        
        # Get bedrock service
        service = get_bedrock_service()
        
        # Get guardrail ID and version
        guardrail_id = assistant_persona.guardrail if assistant_persona else None
        guardrail_version = assistant_persona.guardrail_version if assistant_persona else None
        
        # Get the MCP server manager singleton
        mcp_manager = get_mcp_manager()
        
        # Get tools from the manager (should be already initialized)
        try:
            # Get tools directly from the MCPServerManager (using thread pool for async)
            def get_tools():
                return asyncio.run(mcp_manager.get_tools())
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(get_tools)
                mcp_tools = future.result()
                
            logger.debug(f"Using {len(mcp_tools)} tools from MCPServerManager")
            
            # Validate POC funding tools if this is a POC funding request
            if intent == 'poc_funding_review' and mcp_tools:
                from .tool_registry import validate_poc_funding_tools
                if not validate_poc_funding_tools(mcp_tools):
                    logger.error(f"POC_FUNDING_ERROR: POC funding tools validation failed!")
                    
        except Exception as e:
            logger.error(f"Error retrieving tools from MCP server manager: {e}", exc_info=True)
            mcp_tools = None
        
        # Create a generator that yields response chunks
        def generate_response():
            # FIRST: Yield the updated user message if files were uploaded
            if files and message_id and updated_content:
                logger.debug(f"Yielding updated user message with file links for message {message_id} (frontend_id: {frontend_message_id})")
                yield {
                    'type': 'message_update',
                    'message_id': message_id,
                    'frontend_message_id': frontend_message_id,
                    'content': updated_content,
                    'role': 'user'
                }
            
            # Add built-in conversation stage tool
            stage_tool = {
                "toolSpec": {
                    "name": "update_conversation_stage",
                    "description": "REQUIRED: Update the current conversation stage when a stage change occurs",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "stage": {
                                    "type": "string",
                                    "enum": ["GATHERING_INFO", "SOLUTION_PROPOSED", "SOLUTION_FINALIZED"],
                                    "description": "The new conversation stage"
                                }
                            },
                            "required": ["stage"]
                        }
                    }
                }
            }
            
            # Combine MCP tools with built-in tools
            if mcp_tools:
                tools_to_use = mcp_tools + [stage_tool]
            else:
                tools_to_use = [stage_tool]
            logger.debug(f"Using {len(mcp_tools) if mcp_tools else 0} tools from MCPServerManager")
            
            # Prepare prompt variables for POC funding analysis (legacy support)
            prompt_variables = {}
            # Note: APN Funding Assistant now receives S3 URLs directly in message content
            # This prompt variables logic is kept for backward compatibility but not actively used

            
            accumulated_text = ""
            accumulated_files = []
            # Prompt variables no longer needed for APN Funding Assistant (S3 URLs now in message content)
            prompt_vars_to_pass = None
            logger.debug(f"POC_FUNDING_VARIABLES: Using direct S3 URLs in message content instead of prompt variables")
            
            for chunk in service.send_message_stream(messages, chat_id, user_id, system_prompt, guardrail_id, guardrail_version, tools_to_use, prompt_vars_to_pass, files, assistant_persona, message_id):                
                logger.debug(f"Received chunk from Bedrock: {chunk}")

                if 'files' in chunk and chunk['files']:         
                    logger.debug(f'Files returned in stream: {chunk["files"]}')
                    # Make sure accumulated_files is a list
                    if not accumulated_files:
                        accumulated_files = []
                    
                    # Handle the files dictionary structure
                    if isinstance(chunk['files'], dict):
                        # Iterate through each key-value pair in the dictionary
                        for file_key, file_value in chunk['files'].items():
                            # If the value is an array (multiple files), append each item individually
                            if isinstance(file_value, list):
                                for item in file_value:
                                    accumulated_files.append(item)
                            else:
                                # Single file object
                                accumulated_files.append(file_value)
                    # Handle case where files might be a list
                    elif isinstance(chunk['files'], list):
                        for file_item in chunk['files']:
                            accumulated_files.append(file_item)
                            
                    logger.debug(f'New accumulated files: {accumulated_files}')           

                if chunk['type'] == 'content':
                    accumulated_text += chunk['content']
                    yield chunk['content']
                elif chunk['type'] == 'info':
                    # Format info messages with markdown emphasis for smaller appearance
                    content = chunk['content']
                    if "Using tool " in content:
                        content = content.replace("Using tool ", "\n*`Using tool ")
                        content = content.replace("...\n", "...`*\n")
                    if "Rate limited by Bedrock API" in content:
                        content = content.replace("Rate limited by Bedrock API", "\n*`Rate limited by Bedrock API`*")
                    
                    # Pass through formatted info messages and accumulate them for persistence
                    accumulated_text += content
                    yield content
                elif chunk['type'] == 'citation':
                    # Handle citation chunks - log them but don't yield to frontend yet
                    # Citations will be included in the final stop event
                    citation_info = chunk.get('citation', {})
                    title = citation_info.get('title', 'Unknown Document')
                    logger.debug(f"STREAM_CITATION: document='{title}'")
                    # Don't yield citation chunks individually - they'll be formatted in the stop event
                elif chunk['type'] == 'tool_result':
                    # Handle tool_result chunks - don't display the raw JSON to user
                    logger.debug(f"STREAM_TOOL_RESULT: length={len(chunk.get('content', ''))}")
                    # Don't yield tool_result chunks to frontend - they contain internal data
                elif chunk['type'] == 'stop':
                    # Ensure trailing newline for proper rendering
                    yield "\n"
                    accumulated_text += "\n"
                    # Log stop reason
                    logger.debug(f"STREAM_STOP: reason='{chunk.get('stop_reason', 'unknown')}', chat_id='{chat_id}'")                    
                    # Only save the accumulated text to chat history if it's not empty and not a tool use JSON
                    logger.debug(f"Check if accumulated_text contains any files: {accumulated_files}")
                    if accumulated_text.strip() and not accumulated_text.strip().startswith('[{"toolUse"'):
                        # Save the complete response as an assistant message
                        logger.debug(f'There are some files: {accumulated_files}')
                        
                        assistant_message = {
                            'message_id': str(uuid.uuid4()),
                            'role': 'assistant',
                            'content': accumulated_text,
                            'files': accumulated_files,
                            'message_timestamp': datetime.utcnow().isoformat()
                        }
                        
                        # Add citations if they exist in the stop chunk
                        if 'citations' in chunk and chunk['citations']:
                            assistant_message['citations'] = chunk['citations']
                            logger.debug(f"CITATIONS_SAVED: Found {len(chunk['citations'])} citations in assistant message")
                        
                        save_chat_message(user_id, chat_id, assistant_message)
                        logger.debug(f"Saved assistant text response to chat history: length={len(accumulated_text)}")
                        
                        
                    # Log the final conversation history
                    updated_chat = get_chat_session(user_id, chat_id)
                    if updated_chat and 'messages' in updated_chat:
                        logger.debug(f"Final conversation history length after response: {len(updated_chat['messages'])}")
                    
                    # Extract variables from AI response
                    try:
                        extracted_vars = extract_variables_from_response(accumulated_text, chat_id)
                        
                        # Update chat variables if any were extracted
                        if extracted_vars:
                            update_chat_variables(user_id, chat_id, extracted_vars)
                            logger.debug(f"VARIABLES_EXTRACTED: count={len(extracted_vars)}, keys={list(extracted_vars.keys())}")
                    except Exception as e:
                        logger.error(f"VARIABLES_EXTRACTION_ERROR: {str(e)[:50]}")
                        # Continue even if this fails
                    
                elif chunk['type'] == 'tool_result':
                    # Handle tool result
                    logger.debug(f"TOOL_RESULT: tool_name='{chunk.get('tool_name')}', tool_id='{chunk.get('tool_id')}'")
                    if 'files' in chunk and chunk['files']:
                        yield chunk
                    
                    # Do NOT save tool use messages to chat history - only pass to Bedrock
                    # Tool execution message is already handled by bedrock_service.py
                    
                    # No need to continue the conversation here - bedrock_service.py now handles this internally
                    
                elif chunk['type'] == 'error':
                    # Handle error chunks from bedrock service (rate limits, etc.)
                    # Log the actual error but don't break the streaming flow
                    error_message = chunk['content']
                    logger.error(f"STREAM_ERROR: {error_message}, chat_id='{chat_id}'")
                    # Don't yield anything - let the existing retry mechanism handle it
                    # The bedrock service will continue with friendly waiting messages
                elif chunk['type'] == 'metadata':
                    # Log usage metrics
                    if 'usage' in chunk:
                        input_tokens = chunk['usage'].get('inputTokens', 0)
                        output_tokens = chunk['usage'].get('outputTokens', 0)
                        total_tokens = chunk['usage'].get('totalTokens', 0)
                        logger.debug(f"TOKEN_USAGE: chat_id='{chat_id}', input={input_tokens}, output={output_tokens}, total={total_tokens}")
        
        return generate_response()
        
    except Exception as e:
        logger.error(f"Error sending streaming message: {e}", exc_info=True)
        raise

def get_chat_session(user_id, chat_id=None):
    """
    Get chat session(s) for a user.
    
    Args:
        user_id (str): ID of the user
        chat_id (str, optional): ID of a specific chat to retrieve
        
    Returns:
        list or dict: List of all chat sessions or specific chat session if chat_id provided
    """
    try:
        # Get all chats for the user
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        
        if chat_id:
            # If specific chat requested, find it
            logger.debug(f"Looking for chat with ID {chat_id}")
            chat = next((c for c in chats if c.get('chat_id') == chat_id), None)
            if not chat:
                logger.debug(f"No chat found with ID {chat_id} for user {user_id}")
                return None
            
            # Add SA copy information
            chat['is_sa_copy'] = chat.get('source_chat_id') is not None
            return chat
        
        # Return all chats
        return chats
    except Exception as e:
        logger.error(f"Error getting chat session: {e}")
        raise

def get_all_chats(user_id, include_completed_sa_reviews=False):
    """
    Get all chats for a user.
    
    Args:
        user_id (str): ID of the user
        include_completed_sa_reviews (bool): Whether to include completed SA review copies
        
    Returns:
        list: List of all chat sessions
    """
    try:
        # Get all chats for the user
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        logger.debug(f"Retrieved {len(chats)} chats for user {user_id}")
        
        # Filter out completed SA review copies unless explicitly requested
        if not include_completed_sa_reviews:
            # Completed SA review statuses that should be hidden from active chat list
            completed_statuses = ['merged', 'dismissed', 'complete_no_changes', 'reassigned']
            
            original_count = len(chats)
            
            # Debug: Log SA copy chats found
            sa_copy_chats = [chat for chat in chats if chat.get('source_chat_id')]
            logger.debug(f"Found {len(sa_copy_chats)} SA copy chats for user {user_id}")
            for sa_chat in sa_copy_chats[:3]:  # Log first 3 for debugging
                chat_id = sa_chat.get('chat_id', 'unknown')
                source_id = sa_chat.get('source_chat_id', 'unknown') 
                status = sa_chat.get('review_status', 'none')
                logger.debug(f"  SA copy: {chat_id[:8]}... source: {source_id[:8]}... status: {status}")
            
            chats = [
                chat for chat in chats 
                if not (
                    chat.get('source_chat_id') and  # Is an SA copy (has source_chat_id)
                    chat.get('review_status') in completed_statuses  # Has completed status
                )
            ]
            
            filtered_count = original_count - len(chats)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} completed SA review copies for user {user_id}")
            else:
                logger.debug(f"No SA review copies filtered for user {user_id}")
        
        # Debug: Log the stages of all chats
        stage_counts = {}
        for chat in chats:
            stage = chat.get('stage', 'UNKNOWN')
            if stage in stage_counts:
                stage_counts[stage] += 1
            else:
                stage_counts[stage] = 1
        
        logger.debug(f"DEBUG: chat_service - Stage counts in all chats: {stage_counts}")
        
        # Debug: Log a few examples of chats with SOLUTION_FINALIZED stage
        solution_finalized_chats = [chat for chat in chats if chat.get('stage') == 'SOLUTION_FINALIZED']
        logger.debug(f"DEBUG: chat_service - Found {len(solution_finalized_chats)} chats with SOLUTION_FINALIZED stage")
        
        if solution_finalized_chats:
            for i, chat in enumerate(solution_finalized_chats[:3]):  # Log up to 3 examples
                logger.debug(f"DEBUG: chat_service - SOLUTION_FINALIZED chat {i+1}: chat_id={chat.get('chat_id')}, stage={chat.get('stage')}")
        
        return chats
    except Exception as e:
        logger.error(f"Error getting all chats: {e}")
        raise

def update_chat_stage(user_id, chat_id, new_stage):
    """
    Update the conversation stage of a chat.
    
    Args:
        user_id (str): ID of the user
        chat_id (str): ID of the chat
        new_stage (str): New stage value
        
    Returns:
        dict: Updated chat data
    """
    try:
        return update_conversation_stage(user_id, chat_id, new_stage)
    except Exception as e:
        logger.error(f"Error updating chat stage: {e}")
        raise


def store_sow_metadata_in_chat(chat_id, sow_result):
    """
    Store SOW generation metadata in chat context for SOW review functionality.
    
    Args:
        chat_id (str): Chat session ID
        sow_result (dict): SOW generation result with S3 details
    """
    try:
        from datetime import datetime
        
        # Get current chat context
        from ..models.chat import get_chat_by_chat_id
        chat = get_chat_by_chat_id(chat_id)
        context = chat.get('chat_variables', {}) if chat else {}
        
        # Extract SOW metadata from result
        sow_metadata = {
            'status': 'generated',  # Start with generated status
            'generated_date': datetime.utcnow().isoformat(),
            's3_url': sow_result.get('s3_url'),
            's3_key': sow_result.get('s3_key'),
            'version_id': sow_result.get('version_id'),
            'file_size': sow_result.get('file_size'),
            'generation_time': sow_result.get('generation_time'),
            'template_type': 'aws_map',  # Default, could be extracted from tool args
            'estimated_cost': 0.0,      # Could be calculated from tool args
            'customer_name': 'Unknown',  # Could be extracted from tool args
            'project_title': 'Unknown', # Could be extracted from tool args
            'partner_name': 'ExamplePartner' # Default from config
        }
        
        # Store in chat context
        context['sow_metadata'] = sow_metadata
        update_chat_variables(chat.get('user_id'), chat_id, context)
        
        logger.debug(f"SOW metadata stored in chat context: chat_id={chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to store SOW metadata in chat context: {e}", exc_info=True)
        raise


def get_all_chats_for_review():
    """
    Get all chats from all users that are in review stages (SOLUTION_PROPOSED or SOLUTION_FINALIZED)
    and don't have SA review feedback yet.
    This is used by Solutions Architects for review purposes.
    
    Returns:
        list: List of chat sessions needing SA review from all users
    """
    try:
        from ..models.chat import get_all_chats_needing_sa_review
        
        # Get all chats needing SA review using the efficient GSI query
        response = get_all_chats_needing_sa_review()
        chats = response.get('chats', [])
        
        logger.debug(f"Found {len(chats)} chats needing SA review")
        return chats
        
    except Exception as e:
        logger.error(f"Error getting all chats for review: {e}")
        raise


def get_all_chats_from_all_users():
    """
    Get all chats from all users (for Solutions Architects).
    This is a fallback method - prefer get_all_chats_for_review() for efficiency.
    
    Returns:
        list: List of all chat sessions from all users
    """
    try:
        # For now, this is not implemented as it would require scanning the entire table
        # which is inefficient. SAs should use the review-specific function instead.
        logger.warning("get_all_chats_from_all_users not implemented - use get_all_chats_for_review() instead")
        return []
        
    except Exception as e:
        logger.error(f"Error getting all chats from all users: {e}")
        raise


def get_chat_session_any_user(chat_id):
    """
    Get a chat session by ID without user restriction.
    This is used by Solutions Architects who can access any chat.
    
    Args:
        chat_id (str): Chat session ID
        
    Returns:
        dict: Chat session data in the same format as get_chat_session
    """
    try:
        from ..models.chat import get_chat_by_chat_id
        
        # Use the new function to get chat by chat_id directly
        chat = get_chat_by_chat_id(chat_id)
        
        if not chat:
            logger.warning(f"Chat {chat_id} not found")
            return None
        
        # Return the raw chat data with SA copy information
        # Add is_sa_copy flag for frontend
        chat['is_sa_copy'] = chat.get('source_chat_id') is not None
        
        return chat
        
    except Exception as e:
        logger.error(f"Error getting chat session for any user: {e}")
        raise
