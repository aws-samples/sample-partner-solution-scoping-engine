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
Chat routes for handling chat interactions.
"""
import asyncio
import logging
import uuid
import json
import boto3
import re
from flask import Blueprint, request, jsonify, Response, make_response, stream_with_context, session
from ..config.app_config import CustomerConfig
from ..services import chat_service
from ..services.mcp_client_service import MCPClient
from ..services.message_processor import MessageProcessor
from ..middleware.auth_middleware import login_required, get_current_user
from ..models.chat import save_chat_message, get_chat_by_chat_id, update_chat_name, update_conversation_stage, get_chat_messages
from datetime import datetime
import sys

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat_bp', __name__)


class PersonaMessageEnhancer:
    """Base class for persona-specific message enhancement."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance the message based on persona-specific logic."""
        return message
    
    def process_files_for_bedrock(self, file_objects, intent):
        """Process files for Bedrock based on persona-specific logic."""
        return file_objects


class APNFundingEnhancer(PersonaMessageEnhancer):
    """Message enhancer for APN Funding Assistant persona."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message with POC funding document structure."""
        if intent != 'poc_funding_review':
            return message
            
        if not file_metadata or not processed_files:
            # POC funding intent but no file metadata - simple notification
            logger.warning(f"POC_FUNDING_WARNING: POC funding intent received but no file metadata or processed files")
            return message + f"\n\nThis is a POC funding analysis request. Please upload the required documents if you haven't already."
        
        logger.info(f"POC_FILE_METADATA: Creating enhanced message with frontend classifications for MCP tool")
        
        # Create a mapping of filename to S3 URL from processed_files
        classified_files = {}
        
        for file_info in processed_files:
            # Use original_display_filename for display, fallback to original_filename for backward compatibility
            display_filename = file_info.get('original_display_filename') or file_info.get('original_filename')
            s3_url = file_info.get('s3_url')
            version_id = file_info.get('version_id')
            classification = file_info.get('document_classification')
            
            # If no classification found, mark as unknown
            if not classification:
                classification = 'unknown'
                logger.warning(f"No classification found for file: {display_filename}")
            
            if display_filename and s3_url:
                # Handle multiple files with same classification by using lists
                if classification not in classified_files:
                    classified_files[classification] = []
                
                classified_files[classification].append({
                    'filename': display_filename,
                    's3_url': s3_url,
                    'version_id': version_id
                })
        
        logger.info(f"POC_FILE_METADATA: Using frontend classifications - Classified files: {classified_files}")
        
        # Enhanced message with structured file information for APN Funding Assistant
        enhanced_message = message + "\n\n**POC Funding Documents Uploaded:**\n"
        
        # Add structured file information based on classification
        if 'sow_document' in classified_files:
            for file_info in classified_files['sow_document']:
                enhanced_message += f"- SOW Document: [{file_info['filename']}]({file_info['s3_url']}?versionId={file_info['version_id']})\n"
        
        if 'pricing_calculator_csv' in classified_files:
            for file_info in classified_files['pricing_calculator_csv']:
                enhanced_message += f"- Pricing Calculator: [{file_info['filename']}]({file_info['s3_url']}?versionId={file_info['version_id']})\n"
        
        if 'architecture_diagram' in classified_files:
            for file_info in classified_files['architecture_diagram']:
                enhanced_message += f"- Architecture Diagram: ![{file_info['filename']}]({file_info['s3_url']}?versionId={file_info['version_id']})\n"
        
        # Add any other classified files
        for classification, file_list in classified_files.items():
            if classification and classification not in ['sow_document', 'architecture_diagram', 'pricing_calculator_csv']:
                # Handle unknown/unclassified files
                if classification == 'unknown':
                    display_name = 'Unknown Document'
                    logger.warning(f"POC_FUNDING_CLASSIFICATION: File(s) classified as 'unknown': {[f['filename'] for f in file_list]}")
                else:
                    display_name = classification.replace('_', ' ').title()
                    logger.debug(f"POC_FUNDING_CLASSIFICATION: Processing {classification} files: {[f['filename'] for f in file_list]}")
                
                for file_info in file_list:
                    enhanced_message += f"- {display_name}: [{file_info['filename']}]({file_info['s3_url']}?versionId={file_info['version_id']})\n"
        
        # Log summary of classification results
        classification_summary = {}
        for classification, file_list in classified_files.items():
            classification_summary[classification] = len(file_list)
        
        logger.info(f"POC_FILE_METADATA: Enhanced message with structured file information")
        logger.info(f"POC_CLASSIFICATION_SUMMARY: {classification_summary}")
        
        return enhanced_message
    
    def process_files_for_bedrock(self, file_objects, intent):
        """For POC funding requests, don't send file_objects to Bedrock."""
        if intent == 'poc_funding_review':
            logger.info(f"POC_FUNDING_OPTIMIZATION: Not sending {len(file_objects)} file objects to Bedrock - tool will use S3 URLs directly")
            return None
        return file_objects


class AWSolutionsEnhancer(PersonaMessageEnhancer):
    """Message enhancer for AWS Solutions Assistant persona."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message for AWS Solutions Assistant."""
        # For now, use default behavior - can be extended later
        return message


def validate_file_classifications(uploaded_files, file_classifications):
    """
    Validate that all uploaded files have corresponding classifications.
    
    Args:
        uploaded_files (list): List of uploaded file objects
        file_classifications (dict): Dict mapping filenames to classifications
        
    Returns:
        dict: Validation results with warnings and mappings
    """
    from werkzeug.utils import secure_filename
    
    validation_results = {
        'valid': True,
        'warnings': [],
        'filename_mappings': {}
    }
    
    if not file_classifications:
        validation_results['warnings'].append("No file classifications provided")
        return validation_results
    
    for file in uploaded_files:
        if file.filename:
            original_name = file.filename
            secure_name = secure_filename(file.filename)
            
            # Track filename mappings
            validation_results['filename_mappings'][original_name] = secure_name
            
            # Check if classification exists for either filename
            has_original_classification = original_name in file_classifications
            has_secure_classification = secure_name in file_classifications
            
            if not has_original_classification and not has_secure_classification:
                validation_results['valid'] = False
                validation_results['warnings'].append(
                    f"No classification found for file: '{original_name}' (secure: '{secure_name}')"
                )
                logger.warning(f"CLASSIFICATION_VALIDATION: Missing classification for {original_name}")
            else:
                classification = file_classifications.get(original_name) or file_classifications.get(secure_name)
                logger.debug(f"CLASSIFICATION_VALIDATION: Found classification for {original_name}: {classification}")
    
    logger.debug(f"CLASSIFICATION_VALIDATION: Available keys: {list(file_classifications.keys())}")
    return validation_results


def get_persona_enhancer(persona_id):
    """Factory function to get the appropriate persona enhancer for Bedrock file processing."""
    enhancers = {
        'apn_funding_assistant': APNFundingEnhancer(),
        'aws_solutions_assistant': AWSolutionsEnhancer(),
    }
    return enhancers.get(persona_id, PersonaMessageEnhancer())

def get_bedrock_client():
    """Get a Bedrock client with the configured region."""
    return boto3.client('bedrock-runtime', region_name=CustomerConfig.get_aws_region())

def load_mcp_servers():
    """Load MCP server configurations."""
    try:
        with open('backend/config/mcp.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Load MCP configs failed: error={str(e)}")
        return {}

def get_assistant_persona(persona_id):
    """Get assistant persona by ID."""
    # This is a placeholder - implement actual persona retrieval
    class Persona:
        def __init__(self, id, system_prompt, guardrail=None, guardrail_version=None):
            self.id = id
            self.system_prompt = system_prompt
            self.guardrail = guardrail
            self.guardrail_version = guardrail_version
    
    # Return a default persona for now
    return Persona(
        persona_id, 
        """You are an expert AWS solutions architect speaking with User who is seller for an organization which sells AWS solutions. As an expert AWS Solutions Architect, you assist inside sellers with designing AWS solutions for their customers. You are knowledgeable about AWS services, pricing, and best practices. You can help with architecture diagrams, cost estimates, and technical recommendations.

IMPORTANT TOOL USAGE INSTRUCTIONS:
- When a user requests POC funding analysis, compliance review, or asks you to review documents for POC funding requirements, you MUST use the analyze_poc_funding_request_urls tool.
- When provided with S3 URLs for SOW documents, architecture diagrams, or pricing calculator files, use the analyze_poc_funding_request_urls tool to perform comprehensive POC funding compliance analysis.

CRITICAL POC FUNDING RESPONSE FORMATTING:
When you receive results from the analyze_poc_funding_request_urls tool, you MUST present ALL detailed analysis sections in a comprehensive, well-formatted response. Structure your response as follows:

## POC Funding Compliance Analysis Results

### 1. Program Identification
[Include all program identification details from the tool response]

### 2. Eligibility Check
[Present complete eligibility criteria evaluation with specific requirements and status]

### 3. Financial Assessment
[Show detailed cost breakdown, budget analysis, and financial compliance]

### 4. Document Review
#### SOW Document Analysis
[Detailed findings from SOW document review]
#### Architecture Diagram Analysis  
[Comprehensive architecture evaluation and recommendations]
#### Pricing Calculator Analysis
[Complete cost structure and pricing validation]

### 5. Document Correlation
[Analysis of how documents align and any inconsistencies found]

### 6. Scope Verification
[Detailed scope analysis and POC appropriateness assessment]

### 7. Well-Architected Framework Validation
[Complete evaluation against AWS Well-Architected principles]

### 8. Review Summary & Recommendations
[All findings, clarifying questions, next steps, and detailed recommendations]

Do NOT provide just a high-level summary - users need to see all the detailed analysis results from each section of the tool response.
- For diagram creation requests, use the generate_diagram tool.
- For cost analysis requests, use the appropriate pricing tools.
- For funding analysis requests, use the get_funding_eligibility tool.
- Always use available tools when they match the user's request rather than providing generic responses.""",
        None,
        None
    )

@chat_bp.route('/chats', methods=['GET'])
@login_required
def list_chats():
    """Lists chats with role-based filtering."""
    current_user = get_current_user()
    
    logger.debug(f"Listing chats for user: {current_user.user_id}")
    
    # Get query parameters
    stage_filter = request.args.get('stage')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    include_completed_sa_reviews = request.args.get('include_completed_sa_reviews', 'false').lower() == 'true'
    
    logger.debug(f"DEBUG: chat_routes - Received request with stage_filter: {stage_filter}, limit: {limit}, offset: {offset}, include_completed_sa_reviews: {include_completed_sa_reviews}")
    
    try:
        # Role-based chat access
        if current_user.is_solutions_architect():
            # Solutions architects can see chats from sellers they support
            if stage_filter == 'SOLUTION_REVIEW':
                # For SA Review, get all users' chats that need review (efficient GSI query)
                all_chats = chat_service.get_all_chats_for_review()
                logger.debug(f"DEBUG: chat_routes - SA retrieved {len(all_chats)} chats needing review")
                
                # Filter to only supported sellers and exclude SA's own chats
                all_chats = [chat for chat in all_chats 
                            if current_user.can_access_chat(chat.get('user_id')) 
                            and chat.get('user_id') != current_user.user_id]
                logger.debug(f"DEBUG: chat_routes - After filtering to supported sellers: {len(all_chats)} chats remain")
            else:
                # For other filters, SAs still see only their own chats for now
                # Note: Could add efficient all-users query for other stage filters
                all_chats = chat_service.get_all_chats(current_user.user_id, include_completed_sa_reviews)
                logger.debug(f"DEBUG: chat_routes - SA retrieved {len(all_chats)} own chats (other filters)")
        else:
            # Sales people see only their own chats
            if stage_filter == 'SOLUTION_REVIEW':
                # Non-SA users cannot access SA Review functionality
                logger.debug("DEBUG: chat_routes - Non-SA user attempted to access SOLUTION_REVIEW, returning empty list")
                all_chats = []
            else:
                all_chats = chat_service.get_all_chats(current_user.user_id, include_completed_sa_reviews)
                logger.debug(f"DEBUG: chat_routes - Sales user retrieved {len(all_chats)} own chats")
        
        # Apply additional stage filtering if specified (beyond role-based filtering)
        if stage_filter and stage_filter != 'SOLUTION_REVIEW':
            if stage_filter == 'SOLUTION_FINALIZED':
                logger.debug("DEBUG: chat_routes - Filtering for SOLUTION_FINALIZED chats")
                # Include chats with SOLUTION_FINALIZED stage OR completed SA review statuses
                completed_statuses = ['merged', 'dismissed', 'complete_no_changes', 'reassigned']
                filtered_chats = [chat for chat in all_chats if 
                                chat.get('stage') == 'SOLUTION_FINALIZED' or 
                                chat.get('review_status') in completed_statuses]
                logger.debug(f"DEBUG: chat_routes - Found {len(filtered_chats)} chats with SOLUTION_FINALIZED stage or completed review status")
            elif stage_filter == 'SOLUTION_PROPOSED':
                logger.debug("DEBUG: chat_routes - Filtering for SOLUTION_PROPOSED chats")
                filtered_chats = [chat for chat in all_chats if chat.get('stage') == 'SOLUTION_PROPOSED']
                logger.debug(f"DEBUG: chat_routes - Found {len(filtered_chats)} chats with SOLUTION_PROPOSED stage")
            elif stage_filter == 'NOT_FINALIZED':
                logger.debug("DEBUG: chat_routes - Filtering for NOT_FINALIZED chats")
                filtered_chats = [chat for chat in all_chats if chat.get('stage') != 'SOLUTION_FINALIZED']
                logger.debug(f"DEBUG: chat_routes - Found {len(filtered_chats)} chats that are not SOLUTION_FINALIZED")
            else:
                logger.debug(f"DEBUG: chat_routes - Unknown stage filter: {stage_filter}, returning all chats")
                filtered_chats = all_chats
        else:
            # SOLUTION_REVIEW filtering already handled in role-based access above
            logger.debug("DEBUG: chat_routes - Using chats from role-based filtering")
            filtered_chats = all_chats
            
        # Apply pagination
        paginated_chats = filtered_chats[offset:offset+limit]
        logger.debug(f"DEBUG: chat_routes - After pagination: returning {len(paginated_chats)} chats")
        
        # Format response
        formatted_chats = [{
            'chatId': chat.get('chat_id', ''),
            'chatName': chat.get('chat_name', ''),
            'stage': chat.get('stage', 'INITIAL'),
            'userId': chat.get('user_id', ''),  # Changed from customerPersona to userId
            'createdAt': chat.get('created_at', ''),
            'updatedAt': chat.get('updated_at', '')
        } for chat in paginated_chats]
        
        # Log the stages of the formatted chats
        stage_counts = {}
        for chat in formatted_chats:
            stage = chat['stage']
            if stage in stage_counts:
                stage_counts[stage] += 1
            else:
                stage_counts[stage] = 1
        logger.debug(f"DEBUG: chat_routes - Stage counts in response: {stage_counts}")
        
        return jsonify({
            'chats': formatted_chats,
            'total': len(filtered_chats)
        })
    except Exception as e:
        logger.error(f"List chats failed: error={str(e)}")
        return jsonify({"error": "Failed to retrieve chat history"}), 500

@chat_bp.route('/chats', methods=['POST'])
@login_required
def create_chat():
    """Creates a new chat session."""
    current_user = get_current_user()
    logger.debug("Received POST request to /chats")
    logger.debug(f"Request content-type: {request.content_type}")
    
    user_id = current_user.user_id
    logger.debug(f"Using user_id from authenticated user: {user_id}")
    
    data = request.json
    if not data:
        logger.warning(f"Create chat request received with no JSON body for user: {user_id}")
        return jsonify({"error": "Missing request body"}), 400

    # Extract required fields for initial chat creation
    assistant_persona = data.get('assistant_persona') or data.get('assistantPersona')
    customer_persona = data.get('customer_persona') or data.get('customerPersona')
    interaction_method = data.get('interaction_method') or data.get('interactionMethod')
    chat_name = data.get('chat_name') or data.get('chatName', '')

    logger.debug(f"Extracted fields - assistant_persona: {assistant_persona}, customer_persona: {customer_persona}, interaction_method: {interaction_method}, chat_name: {chat_name}")

    # Handle assistant_persona object
    if isinstance(assistant_persona, dict):
        assistant_persona = assistant_persona.get('value')
        if not assistant_persona:
            logger.warning(f"Assistant persona object missing value field: {data.get('assistant_persona')}")
            return jsonify({"error": "Assistant persona object missing value field"}), 400

    # Handle customer_persona object
    if isinstance(customer_persona, dict):
        customer_persona = customer_persona.get('value')
        if not customer_persona:
            logger.warning(f"Customer persona object missing value field: {data.get('customer_persona')}")
            return jsonify({"error": "Customer persona object missing value field"}), 400

    if not all([assistant_persona, customer_persona, interaction_method]):
        missing = [field for field, value in {
            'assistant_persona': assistant_persona,
            'customer_persona': customer_persona,
            'interaction_method': interaction_method
        }.items() if not value]
        # Use structured logging with separate parameters instead of f-strings
        logger.warning("Create chat request missing required fields", 
                      extra={"missing_fields": missing, "user_id": user_id})
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    # Validate persona and interaction_method against known values
    from ..config.personas import PersonaManager
    persona_manager = PersonaManager()
    if assistant_persona not in persona_manager.assistant_personas:
        logger.warning(f"Invalid assistant_persona: {assistant_persona[:50]}, user={user_id}")
        return jsonify({"error": "Invalid assistant persona"}), 400
    if customer_persona not in persona_manager.customer_personas:
        logger.warning(f"Invalid customer_persona: {customer_persona[:50]}, user={user_id}")
        return jsonify({"error": "Invalid customer persona"}), 400
    VALID_INTERACTION_METHODS = {'email', 'phone', 'video', 'chat', 'in_person'}
    if interaction_method not in VALID_INTERACTION_METHODS:
        logger.warning(f"Invalid interaction_method: {interaction_method[:50]}, user={user_id}")
        return jsonify({"error": "Invalid interaction method"}), 400

    try:
        logger.debug(f"Creating chat with - user_id: {user_id}, assistant_id: {assistant_persona}, customer_id: {customer_persona}, interaction_type: {interaction_method}, chat_name: {chat_name}")
        # Create new chat with the service
        chat = chat_service.create_chat(
            user_id=user_id,
            assistant_id=assistant_persona,
            customer_id=customer_persona,
            interaction_type=interaction_method,
            chat_name=chat_name
        )
        
        # Set the current_chat_id in the session
        session['current_chat_id'] = chat['chat_id']
        logger.debug(f"Set current_chat_id in session: {session['current_chat_id']}")
        
        # Ensure chat ID is properly returned
        response_data = {
            'chatId': chat['chat_id'],
            'userId': chat['user_id'],
            'assistantPersona': chat['assistant_persona'],
            'customerPersona': chat['customer_persona'],
            'interactionMethod': chat['interaction_method'],
            'timestamp': chat['timestamp'],
            'stage': chat['stage'],
            'chatName': chat.get('chat_name', '')  # Include chat name in response
        }
        
        logger.info(f"Chat created: chat_id={chat['chat_id']}, user={user_id}, persona={assistant_persona}")
        return jsonify(response_data), 201
    except Exception as e:
        logger.error(f"Create chat failed: user={user_id}, error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to create chat session"}), 500

@chat_bp.route('/chats/<chat_id>/new-messages', methods=['GET'])
@login_required
def check_new_messages(chat_id):
    """Check if there are new messages for a chat"""
    try:
        # For now, always return False since we're using polling to reload messages
        # This endpoint exists for future enhancement with real-time notifications
        return jsonify({'has_new_messages': False})
        
    except Exception as e:
        logger.error(f"Check new messages failed: error={str(e)}")
        return jsonify({'has_new_messages': False})

@chat_bp.route('/chats/<conversation_id>', methods=['GET'])
@login_required
def get_chat_session(conversation_id):
    """Gets the complete chat session for a specific conversation."""
    current_user = get_current_user()
    
    # Update current_chat_id in session
    session['current_chat_id'] = conversation_id
    logger.debug(f"Updated current_chat_id in session: {session['current_chat_id']}")
    
    logger.debug(f"Getting chat session for conversation: {conversation_id} for user: {current_user.user_id}")
    try:
        # Check access permissions using proper access control
        session_data = chat_service.get_chat_session_any_user(conversation_id)
        
        if not session_data:
            return jsonify({"error": "Chat not found"}), 404
        
        # Verify user can access this chat
        if not current_user.can_access_chat(session_data.get('user_id')):
            logger.warning(f"Access denied: user={current_user.user_id}, chat_owner={session_data.get('user_id')}, chat_id={conversation_id}")
            return jsonify({"error": "Chat not found"}), 404
        
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"Get chat session failed: error={str(e)}")
        return jsonify({"error": "Failed to retrieve chat session"}), 500

def debug_file_classifications_parsing(request):
    """Debug helper to track file classification parsing issues."""
    # Log raw FormData
    logger.debug(f"FORMDATA_DEBUG: Content-Type: {request.content_type}")
    logger.debug(f"FORMDATA_DEBUG: Content-Length: {request.content_length}")
    
    # Log all form fields
    for key, value in request.form.items():
        if key == 'fileClassifications':
            logger.debug(f"FORMDATA_DEBUG: {key} = {value[:200]}..." if len(str(value)) > 200 else f"FORMDATA_DEBUG: {key} = {value}")
        else:
            logger.debug(f"FORMDATA_DEBUG: {key} = {type(value)}")
    
    # Log all files
    for key, file in request.files.items():
        logger.debug(f"FORMDATA_DEBUG: File {key} = {file.filename} ({file.content_type})")

def validate_and_fix_classifications(file_classifications, uploaded_files):
    """
    Validate file classifications and attempt to fix common corruption issues.
    """
    if not file_classifications or not uploaded_files:
        return file_classifications
    
    # Create a mapping of uploaded filenames
    uploaded_filenames = [file.filename for file in uploaded_files if file.filename]
    
    # Check for missing classifications
    for filename in uploaded_filenames:
        if filename not in file_classifications:
            logger.warning(f"Missing classification for uploaded file: {filename}")
    
    # Check for extra classifications (not in uploaded files)
    for filename in file_classifications.keys():
        if filename not in uploaded_filenames:
            logger.warning(f"Classification exists for non-uploaded file: {filename}")
    
    # Validate classification values
    valid_classifications = [
        'sow_document', 'pricing_calculator_csv', 'architecture_diagram', 
        'funding_document', 'technical_document', 'contract', 'presentation'
    ]
    
    for filename, classification in file_classifications.items():
        if classification not in valid_classifications:
            logger.warning(f"Invalid classification: file={filename[:50]}..., classification={classification}")
    
    return file_classifications

@chat_bp.route('/chats/<chat_id>/messages', methods=['POST'])
@login_required
def send_message(chat_id):
    """Send a message to the chat and stream the response."""
    current_user = get_current_user()
    
    try:
        # Check if this is a multipart request (with files)
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            # Add comprehensive debugging for FormData parsing
            debug_file_classifications_parsing(request)
            
            # Handle file upload
            message = request.form.get('message', '').strip()
            intent = request.form.get('intent')
            frontend_message_id = request.form.get('frontend_message_id')
            uploaded_files = request.files.getlist('files')
            file_metadata_str = request.form.get('fileMetadata')
            file_classifications_str = request.form.get('fileClassifications')
            
            logger.debug(f"MULTIPART_REQUEST: chat_id={chat_id}")
            logger.debug(f"  Message length: {len(message)}")
            logger.info(f"  FILES_UPLOAD_DEBUG: Files count: {len(uploaded_files)}")
            if len(uploaded_files) == 0:
                logger.warning(f"  ⚠️ WAFR_NO_FILES: Multipart request received but NO FILES attached!")
            logger.debug(f"  Intent: {intent}")
            logger.debug(f"  FileMetadata: {file_metadata_str}")
            logger.debug(f"  FileClassifications RAW: {file_classifications_str}")
            
            # Parse file metadata if provided
            file_metadata = {}
            if file_metadata_str:
                try:
                    import json
                    file_metadata = json.loads(file_metadata_str)
                    logger.info(f"POC_FILE_METADATA: Parsed file metadata: {file_metadata}")
                except Exception as e:
                    logger.warning(f"Parse file metadata failed: error={str(e)}")
            
            # Parse file classifications if provided with enhanced debugging
            file_classifications = {}
            if file_classifications_str:
                try:
                    import json
                    logger.debug(f"RAW_FILE_CLASSIFICATIONS_STRING: {file_classifications_str}")
                    file_classifications = json.loads(file_classifications_str)
                    logger.debug(f"PARSED_FILE_CLASSIFICATIONS: {file_classifications}")
                    
                    # Validate each classification mapping
                    for filename, classification in file_classifications.items():
                        logger.debug(f"CLASSIFICATION_MAPPING: '{filename}' -> '{classification}'")
                    
                    # Validate and attempt to fix classifications
                    file_classifications = validate_and_fix_classifications(file_classifications, uploaded_files)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Parse file classifications failed: error={str(e)}")
                    logger.error(f"Raw parse failure: data={repr(file_classifications_str)[:50]}...")
                    file_classifications = {}
                except Exception as e:
                    logger.error(f"Parse file classifications unexpected: error={str(e)}")
                    file_classifications = {}
            
            # Log form data for debugging
            logger.debug(f"  Form keys: {list(request.form.keys())}")
            for key in request.form.keys():
                logger.debug(f"    {key}: '{request.form.get(key)}'")
                
        else:
            # Handle JSON request (text only)
            data = request.get_json()
            message = data.get('message', '').strip() if data else ''
            intent = data.get('intent') if data else None
            frontend_message_id = data.get('frontend_message_id') if data else None
            file_metadata = data.get('fileMetadata', {}) if data else {}
            file_classifications = data.get('fileClassifications', {}) if data else {}
            uploaded_files = []
            
            logger.debug(f"JSON_REQUEST: chat_id={chat_id}")
            logger.debug(f"  Message length: {len(message)}")
            logger.debug(f"  Intent: {intent}")
            logger.debug(f"  FileMetadata: {file_metadata}")
        
        # At least message or files should be provided
        if not message and not uploaded_files:
            logger.warning(f"Empty request: no message content and no files provided")
            return make_response(jsonify({"error": "Message or files are required"}), 400)

        logger.info(f"CHAT_ROUTES_DEBUG: Received intent: '{intent}'")
        logger.info(f"CHAT_ROUTES_DEBUG: Has uploaded files: {len(uploaded_files) if uploaded_files else 0}")
        logger.info(f"CHAT_ROUTES_DEBUG: Message length: {len(message)}")
        
        # Validate that we have either message content or files
        has_content = message and len(message.strip()) > 0
        has_files = uploaded_files and len(uploaded_files) > 0
        
        if not has_content and not has_files:
            logger.warning(f"Invalid request: no message content and no files")
            return make_response(jsonify({"error": "Either message content or files must be provided"}), 400)
        
        logger.debug(f"REQUEST_VALIDATION: has_content={has_content}, has_files={has_files}")
        
        user_id = current_user.user_id
        
        # Process uploaded files if any
        processed_files = []
        file_objects = []
        poc_metadata = None
        
        if uploaded_files:
            logger.debug(f"Processing {len(uploaded_files)} uploaded files:")
            for i, file in enumerate(uploaded_files):
                logger.debug(f"  File {i}: {file.filename}, original_content_type: {file.content_type}")
            
            # Validate file classifications
            validation_results = validate_file_classifications(uploaded_files, file_classifications)
            if not validation_results['valid']:
                logger.warning(f"File classification validation failed: {validation_results['warnings']}")
            
            # Check for POC-specific metadata
            file_metadata_str = request.form.get('fileMetadata')
            if file_metadata_str and intent == 'poc_funding_review':
                try:
                    import json
                    poc_metadata = json.loads(file_metadata_str)
                    logger.debug(f"POC metadata received: {poc_metadata}")
                except Exception as e:
                    logger.warning(f"Parse POC metadata failed: error={str(e)}")
            
            try:
                from ..services.document_processor import DocumentProcessor
                processed_files, file_objects = DocumentProcessor.upload_file_objects_to_s3(
                    uploaded_files, 
                    chat_id, 
                    file_classifications=file_classifications
                )
                logger.debug(f"Successfully processed files: {len(processed_files)} metadata, {len(file_objects)} objects for Bedrock")
                logger.debug(f"File classifications applied: {file_classifications}")
                logger.debug(f"Filename mappings: {validation_results['filename_mappings']}")
                
                # Enhance file objects with POC metadata if available
                if poc_metadata and intent == 'poc_funding_review':
                    for i, file_obj in enumerate(file_objects):
                        filename = file_obj.get('name', '')
                        # Match file to POC metadata by filename
                        for poc_type, metadata in poc_metadata.items():
                            if metadata.get('filename') == filename:
                                file_obj['poc_type'] = metadata.get('type')
                                file_obj['poc_required'] = metadata.get('required', False)
                                logger.debug(f"Enhanced file {i} with POC metadata: type={metadata.get('type')}")
                                break
                
                # Log the corrected content types
                for i, file_obj in enumerate(file_objects):
                    logger.debug(f"  Processed file {i}: {file_obj.get('name')}, corrected_content_type: {file_obj.get('content_type')}, poc_type: {file_obj.get('poc_type', 'N/A')}")
            except Exception as e:
                logger.error(f"Process uploaded files failed: error={str(e)}")
                return make_response(jsonify({"error": "Failed to process uploaded files"}), 500)
        
        # Update current_chat_id in session
        session['current_chat_id'] = chat_id
        logger.debug(f"Updated current_chat_id in session: {session['current_chat_id']}")

        # Get chat to determine persona
        chat_data = chat_service.get_chat_session(user_id, chat_id)
        persona_id = chat_data.get('assistant_persona', 'default')
        
        # For POC funding review, use frontend classifications directly
        # The file_classifications variable already contains the correct frontend data
        if intent == 'poc_funding_review' and file_classifications:
            logger.info(f"POC_FUNDING_FRONTEND_CLASSIFICATIONS: Using frontend classifications directly")
            # Use the already parsed file_classifications instead of recreating from processed_files
            file_metadata = file_classifications.copy()
            logger.info(f"POC_FUNDING_FRONTEND_CLASSIFICATIONS: Using file_metadata from frontend: {file_metadata}")
        elif intent == 'poc_funding_review' and processed_files and not file_metadata:
            logger.info(f"POC_FUNDING_FRONTEND_CLASSIFICATIONS: Fallback - using classifications from processed files")
            # Fallback: Create file_metadata from frontend classifications stored in processed_files
            file_metadata = {}
            for file_info in processed_files:
                original_filename = file_info.get('original_filename')
                frontend_classification = file_info.get('document_classification')
                
                if original_filename and frontend_classification:
                    file_metadata[original_filename] = frontend_classification
                    logger.debug(f"Using frontend classification: {original_filename} -> {frontend_classification}")
            
            logger.info(f"POC_FUNDING_FRONTEND_CLASSIFICATIONS: Fallback file_metadata: {file_metadata}")
        
        # Use centralized message processor
        enhanced_message = MessageProcessor.process_user_message_with_files(message, intent, processed_files, file_metadata, persona_id)
        
        logger.info(f"PERSONA_ENHANCEMENT: Used MessageProcessor for persona '{persona_id}'")
        logger.info(f"POC_FUNDING_CHECK: intent='{intent}', has_file_metadata={bool(file_metadata)}, processed_files_count={len(processed_files) if processed_files else 0}")

        # Use the streaming function from chat_service
        logger.debug(f"Calling chat_service.process_user_message_stream with:")
        logger.debug(f"  chat_id: {chat_id}")
        logger.debug(f"  user_id: {user_id}")
        logger.debug(f"  enhanced_message length: {len(enhanced_message)}")
        logger.debug(f"  intent: {intent}")
        logger.debug(f"  processed_files count: {len(processed_files)}")
        logger.debug(f"  file_objects count: {len(file_objects)}")
        
        # Use persona-specific logic for Bedrock file processing
        enhancer = get_persona_enhancer(persona_id)
        bedrock_file_objects = enhancer.process_files_for_bedrock(file_objects, intent)
        
        logger.debug(f"Calling process_user_message_stream: chat_id={chat_id}, intent={intent}, files={len(processed_files) if processed_files else 0}, bedrock_objs={'None' if bedrock_file_objects is None else len(bedrock_file_objects)}")
        
        response_stream = chat_service.process_user_message_stream(
            chat_id, user_id, enhanced_message, intent, 
            files=processed_files,  # For DynamoDB storage
            file_objects=bedrock_file_objects,  # For Bedrock processing (None for POC funding)
            frontend_message_id=frontend_message_id  # For frontend message tracking
        )
        
        logger.info(f"Message processing started: chat_id={chat_id}, user={user_id}, intent={intent}, files={len(processed_files) if processed_files else 0}")
        
        # Use Flask's stream_with_context to ensure the request context is available
        @stream_with_context
        def generate():
            try:
                for chunk in response_stream:
                    # Convert to JSON string and then to bytes if it's a dictionary
                    if isinstance(chunk, dict):
                        import json
                        json_str = json.dumps(chunk)
                        yield json_str.encode('utf-8')
                    # Convert string to bytes before yielding
                    elif isinstance(chunk, str):
                        yield chunk.encode('utf-8')
                    # If it's already bytes, yield as is
                    elif isinstance(chunk, bytes): 
                        yield chunk
                    # For any other type, convert to string first
                    else:
                        yield str(chunk).encode('utf-8')
            except Exception as e:
                logger.error(f"Error in stream generation: {e}", exc_info=True)
                yield "\n\nError: Failed to complete response. Please try again.".encode('utf-8')

        return Response(generate(), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        return make_response(jsonify({"error": "Failed to process message"}), 500)

@chat_bp.route('/chats/<chat_id>/stage', methods=['GET'])
@login_required
def get_chat_stage(chat_id):
    """Get the current stage of a chat conversation."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    try:
        chat = chat_service.get_chat_session(user_id, chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
            
        return jsonify({
            "chatId": chat_id,
            "stage": chat.get('stage', 'INITIAL')
        })
    except Exception as e:
        logger.error(f"Error getting chat stage: {e}", exc_info=True)
        return jsonify({"error": "Failed to get chat stage"}), 500

@chat_bp.route('/chats/<chat_id>/stage', methods=['PUT'])
@login_required
def update_chat_stage(chat_id):
    """Update the stage of a chat conversation."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    try:
        data = request.get_json()
        new_stage = data.get('stage')
        
        if not new_stage:
            return jsonify({"error": "Stage is required"}), 400
            
        updated_chat = chat_service.update_chat_stage(user_id, chat_id, new_stage)
        
        return jsonify({
            "chatId": chat_id,
            "stage": updated_chat.get('stage', 'INITIAL')
        })
    except Exception as e:
        logger.error(f"Error updating chat stage: {e}", exc_info=True)
        return jsonify({"error": "Failed to update chat stage"}), 500

@chat_bp.route('/chats', methods=['OPTIONS'])
def options_chats():
    """Handle OPTIONS requests for /chats endpoint."""
    logger.debug("Received OPTIONS request to /chats")
    
    # Create response with appropriate CORS headers
    response = jsonify({'success': True})
    # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost')
    # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
    # response.headers.add('Access-Control-Allow-Origin', 'https://your-domain.com')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '600')
    
    return response 

# @chat_bp.route('/test-post', methods=['GET', 'POST', 'OPTIONS'])
# def test_post():
#     """Test endpoint for debugging POST requests and session data."""
#     from flask import session
#     
#     if request.method == 'OPTIONS':
#         response = jsonify({'success': True})
#         # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
#         response.headers.add('Access-Control-Allow-Origin', 'http://localhost')
#         # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
#         # response.headers.add('Access-Control-Allow-Origin', 'https://your-domain.com')
#         response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
#         response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
#         response.headers.add('Access-Control-Allow-Credentials', 'true')
#         return response
#         
#     logger.debug(f"Received {request.method} request to /test-post")
#     logger.debug(f"Request headers: {dict(request.headers)}")
#     
#     # Get session data and convert to dict for JSON serialization
#     session_data = {}
#     try:
#         for key in session:
#             try:
#                 # Try to convert session values to serializable types
#                 session_data[key] = session[key]
#             except Exception as e:
#                 session_data[key] = f"[Error serializing: {str(e)}]"
#         logger.debug(f"Session data: {session_data}")
#     except Exception as e:
#         logger.error(f"Error accessing session data: {e}", exc_info=True)
#         session_data = {"error": f"Failed to access session: {str(e)}"}
#     
#     response_data = {
#         "status": "success",
#         "method": request.method,
#         "time": datetime.utcnow().isoformat(),
#         "headers_received": dict(request.headers),
#         "session_data": session_data,
#         "user_id": session.get('user_id', "unknown"),  # Get user_id from session
#         "server_info": {
#             "server_time": datetime.utcnow().isoformat(),
#             "python_version": sys.version,
#             "flask_version": "2.0+" # Approximate
#         }
#     }
#     
#     if request.method == 'POST':
#         data = request.get_json() or {}
#         # logger.debug(f"Request data: {data}") # TURNED OFF
#         response_data["request_data"] = data
#         
#     response = jsonify(response_data)
#     # Add CORS headers explicitly
#     # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
#     response.headers.add('Access-Control-Allow-Origin', 'http://localhost:7001')
#     # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
#     # response.headers.add('Access-Control-Allow-Origin', 'https://your-domain.com')
#     response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
#     response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
#     response.headers.add('Access-Control-Allow-Credentials', 'true')
#     
#     return response
@chat_bp.route('/chats/recent', methods=['GET'])
@login_required
def get_recent_chats():
    """Get the 5 most recent chats for the user, excluding SA copy chats."""
    current_user = get_current_user()
    user_id = current_user.user_id
        
    try:
        # Get more chats to account for filtering
        from ..models.chat import list_chats_for_user
        recent_chats_response = list_chats_for_user(user_id, limit=10, sort_by='updated_at')
        recent_chats = recent_chats_response.get('chats', [])
        
        # Filter out SA copy chats and limit to 5
        formatted_chats = []
        for chat in recent_chats:
            # Exclude SA copy chats (they have source_chat_id)
            if 'source_chat_id' not in chat:
                formatted_chat = {
                    'chatId': chat.get('chat_id', ''),
                    'chatName': chat.get('chat_name', ''),
                    'updatedAt': chat.get('updated_at', ''),
                    'stage': chat.get('stage', 'INITIAL')
                }
                formatted_chats.append(formatted_chat)
                if len(formatted_chats) >= 5:
                    break
        
        return jsonify(formatted_chats)
    except Exception as e:
        return jsonify({"error": "Failed to get recent chats"}), 500

@chat_bp.route('/chats/reviews', methods=['GET'])
@login_required
def get_sa_reviews():
    """Get SA review copy chats for the user with optional limit."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    # Get limit parameter, default to 5 for backward compatibility
    limit = request.args.get('limit', 5, type=int)
        
    try:
        # Get recent chats sorted by updated_at
        from ..models.chat import list_chats_for_user
        recent_chats_response = list_chats_for_user(user_id, limit=max(limit * 2, 20), sort_by='updated_at')
        recent_chats = recent_chats_response.get('chats', [])
        
        # Filter for SA copy chats only
        formatted_chats = []
        for chat in recent_chats:
            # Only include SA copy chats (they have source_chat_id)
            if 'source_chat_id' in chat:
                formatted_chat = {
                    'chatId': chat.get('chat_id', ''),
                    'chatName': chat.get('chat_name', ''),
                    'updatedAt': chat.get('updated_at', ''),
                    'stage': chat.get('stage', 'INITIAL'),
                    'reviewStatus': chat.get('review_status', 'unknown'),
                    'sourceChatId': chat.get('source_chat_id', '')
                }
                formatted_chats.append(formatted_chat)
                if len(formatted_chats) >= limit:
                    break
        
        return jsonify({
            'chats': formatted_chats,
            'total': len(formatted_chats)
        })
    except Exception as e:
        return jsonify({"error": "Failed to get SA review chats"}), 500

@chat_bp.route('/chats/<chat_id>/name', methods=['PUT'])
@login_required
def update_chat_name(chat_id):
    """Update the name of a chat."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    try:
        data = request.get_json()
        new_name = data.get('name')
        
        if not new_name:
            return jsonify({"error": "Chat name is required"}), 400
            
        # Trim to 50 characters if longer
        new_name = new_name[:50]
        
        from ..models.chat import update_chat_name
        updated_chat = update_chat_name(user_id, chat_id, new_name)
        
        return jsonify({
            'chatId': updated_chat['chat_id'],
            'chatName': updated_chat['chat_name']
        })
    except ValueError as e:
        logger.error(f"Update chat name validation failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Resource not found"}), 404
    except Exception as e:
        logger.error(f"Update chat name failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to update chat name"}), 500

@chat_bp.route('/chats/<chat_id>', methods=['DELETE'])
@login_required
def delete_chat_route(chat_id):
    """Delete a chat."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    try:
        # Automatically reassign any in-progress review before deletion
        from ..models.sa_review import reassign_sa_review
        try:
            reassign_sa_review(chat_id, current_user.user_id, "Chat deleted - automatically reassigned")
        except:
            # If reassign fails (e.g., not a review chat or not in progress), continue with deletion
            pass
        
        from ..models.chat import delete_chat_by_id
        success = delete_chat_by_id(user_id, chat_id)
        
        # If this was the current chat, remove it from the session
        if session.get('current_chat_id') == chat_id:
            session.pop('current_chat_id', None)
            logger.debug(f"Removed current_chat_id from session after deletion")
        
        if success:
            return jsonify({"success": True, "message": "Chat deleted successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to delete chat"}), 500
    except ValueError as e:
        logger.error(f"Delete chat validation failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Resource not found"}), 404
    except Exception as e:
        logger.error(f"Delete chat failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to delete chat"}), 500

@chat_bp.route('/chats/<chat_id>/feedback', methods=['POST'])
@login_required
def save_feedback_route(chat_id):
    """Save feedback for a chat."""
    current_user = get_current_user()
    user_id = current_user.user_id
    
    try:
        data = request.get_json()
        feedback_type = data.get('type')
        feedback_provider = data.get('provider')
        feedback_detail = data.get('detail')
        
        if not feedback_type or not feedback_provider:
            return jsonify({"error": "Feedback type and provider are required"}), 400
            
        if feedback_type not in ['positive', 'negative']:
            return jsonify({"error": "Feedback type must be 'positive' or 'negative'"}), 400
            
        if feedback_provider not in ['User', 'Partner', 'Customer']:
            return jsonify({"error": "Feedback provider must be 'User', 'Partner', or 'Customer'"}), 400
        
        # Validate chat is in an appropriate stage for feedback
        from ..models.chat import get_chat_by_chat_id
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        if chat.get('user_id') != user_id:
            return jsonify({"error": "Chat not found"}), 404
        if chat.get('stage') not in ('SOLUTION_PROPOSED', 'SOLUTION_FINALIZED'):
            return jsonify({"error": "Feedback can only be submitted for chats with a proposed or finalized solution"}), 400
        
        feedback_data = {
            'type': feedback_type,
            'provider': feedback_provider,
            'detail': feedback_detail or ''
        }
        
        from ..models.chat import save_feedback
        updated_chat = save_feedback(user_id, chat_id, feedback_data)
        
        return jsonify({
            'chatId': updated_chat['chat_id'],
            'feedback': updated_chat.get('feedback', {})
        })
    except ValueError as e:
        logger.error(f"Save feedback validation failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Resource not found"}), 404
    except Exception as e:
        logger.error(f"Save feedback failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to save feedback"}), 500

@chat_bp.route('/chats/<chat_id>/sa-feedback', methods=['POST'])
@login_required
def save_sa_feedback_route(chat_id):
    """Save Solutions Architect review feedback for a chat."""
    current_user = get_current_user()
    
    # Only SAs can provide SA feedback
    if not current_user.is_solutions_architect():
        return jsonify({"error": "Only Solutions Architects can provide SA feedback"}), 403
    
    user_name = current_user.first_name or current_user.user_id
    
    try:
        data = request.get_json()
        feedback_type = data.get('type')  # Frontend sends 'type', not 'feedback_type'
        feedback_detail = data.get('detail')
        
        if not feedback_type:
            return jsonify({"error": "Feedback type is required"}), 400
            
        if feedback_type not in ['positive', 'negative']:
            return jsonify({"error": "Feedback type must be 'positive' or 'negative'"}), 400
        
        sa_feedback_data = {
            'architect_name': user_name,
            'feedback_type': feedback_type,  # Store as 'feedback_type' in database
            'detail': feedback_detail or ''
        }
        
        # Use the new function that works directly with chat_id
        from ..models.chat import save_sa_review_feedback_by_chat_id
        
        updated_chat = save_sa_review_feedback_by_chat_id(chat_id, sa_feedback_data)
        
        return jsonify({
            'chatId': updated_chat['chat_id'],
            'sa_review_feedback': updated_chat.get('sa_review_feedback', {})
        })
    except ValueError as e:
        logger.error(f"Save SA feedback validation failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Resource not found"}), 404
    except Exception as e:
        logger.error(f"Save SA feedback failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to save SA review feedback"}), 500

@chat_bp.route('/chats/<chat_id>/approvals/<approval_id>/download', methods=['GET'])
@login_required
def download_approval_documents(chat_id, approval_id):
    """Download all documents associated with an approval as a zip file."""
    try:
        import zipfile
        import io
        from ..models.chat import get_chat_by_chat_id
        
        current_user = get_current_user()
        
        # Get the chat data
        chat_data = get_chat_by_chat_id(chat_id)
        if not chat_data:
            return jsonify({"error": "Chat not found"}), 404
        
        # Verify ownership or SA reviewer access
        is_owner = chat_data.get('user_id') == current_user.user_id
        is_sa_reviewer = chat_data.get('sa_reviewer') == current_user.user_id
        is_sa = current_user.is_solutions_architect() if hasattr(current_user, 'is_solutions_architect') else False
        if not (is_owner or is_sa_reviewer or is_sa):
            return jsonify({"error": "Chat not found"}), 404
            
        # Find the specific approval
        approval = None
        for app in chat_data.get('approvals', []):
            if app.get('approval_id') == approval_id:
                approval = app
                break
                
        if not approval:
            return jsonify({"error": "Approval not found"}), 404
            
        # Get S3 client
        s3_client = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        # Create zip file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each document to the zip
            for doc_id in approval.get('document_ids', []):
                try:
                    # Check if document exists in chat documents to get s3_key and version_id
                    if doc_id in chat_data.get('documents', {}):
                        doc_info = chat_data['documents'][doc_id]
                        s3_key = doc_info.get('s3_key', f"{chat_id}/{doc_id}")
                        version_id = doc_info.get('version_id')
                    else:
                        s3_key = f"{chat_id}/{doc_id}"
                        version_id = None
                    
                    # Extract filename from S3 key
                    filename = s3_key.split('/')[-1]
                    
                    # Get document from S3 with version ID if available
                    get_params = {'Bucket': bucket_name, 'Key': s3_key}
                    if version_id:
                        get_params['VersionId'] = version_id
                        
                    response = s3_client.get_object(**get_params)
                    file_content = response['Body'].read()
                    
                    # Add to zip with S3 filename
                    zip_file.writestr(filename, file_content)
                except Exception as e:
                    logger.warning(f"Add document to zip failed: doc_id={doc_id}, error={str(e)}")
                    continue
        
        zip_buffer.seek(0)
        
        # Create response
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename=approval_{approval_id}_documents.zip'
        
        return response
        
    except Exception as e:
        logger.error(f"Download approval docs failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to download documents"}), 500
