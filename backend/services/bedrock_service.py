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
Service for interacting with Amazon Bedrock.
This implementation follows the example code pattern from the MCP documentation.
"""
import json
import logging
import random
import time
import os
import sys
import asyncio
import concurrent.futures
import boto3
from collections import defaultdict
from datetime import datetime, timedelta
from botocore.config import Config
from botocore.exceptions import ClientError
from backend.config.app_config import CustomerConfig
from backend.services.document_processor import DocumentProcessor
from backend.services.token_usage_logger import TokenUsageLogger


logger = logging.getLogger(__name__)

# Import configuration
from ..config.app_config import CustomerConfig

# Token limits for conversation management
MAX_SAFE_TOKENS = 120000  # Conservative limit to stay under 200K context
TOKEN_TRUNCATION_TARGET = 80000  # Target when truncating conversation

# Friendly waiting messages for throttling
FRIENDLY_WAITING_MESSAGES = [
    "Just a moment of brilliance coming up",
    "Almost there",
    "Getting everything in order",
    "Fine-tuning the details",
    "Last few calculations",
    "Putting on finishing touches",
    "Spinning up the idea machine",
    "Channeling my inner genius",
    "Engineering the answer",
    "Building something special",
    "Mapping out the possibilities",
    "Assembling the perfect solution",
    "Pondering the possibilities",
    "Processing that brilliant idea",
    "Connecting the dots",
    "Deep in thought"
]

import uuid
from ..models.chat import create_document_metadata, update_chat_document, create_document_reference_for_message

def store_document_and_create_reference(chat_id, document_type, tool_results_json, tool_name):
    """
    Store document metadata and create message reference.
    
    Args:
        chat_id (str): Chat ID
        document_type (str): Type of document
        tool_results_json (dict): MCP tool result with S3 metadata
        tool_name (str): Name of the MCP tool
    
    Returns:
        str: Document reference for message content
    """
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Create document metadata
        metadata = create_document_metadata(
            document_type=document_type,
            s3_url=tool_results_json.get('s3_url'),
            s3_key=tool_results_json.get('s3_key'),
            version_id=tool_results_json.get('s3_file_version_id') or tool_results_json.get('version_id'),
            file_size=tool_results_json.get('file_size'),
            tool_name=tool_name
        )
        
        # Store in chat documents
        success = update_chat_document(chat_id, document_id, metadata)
        
        # Create reference for message
        return create_document_reference_for_message(document_id, document_type)
        
    except Exception as e:
        logger.error(f"Error storing document: {e}")
        return f"[Error storing {document_type}]"

class BedrockService:
    # Configuration-driven classification rules
    CLASSIFICATION_RULES = {
        'sow_document': {
            'keywords': ['sow', 'statement', 'work', 'scope', 'proposal', 'poc', 'tfc', 'project', 'plan'],
            'extensions': ['.pdf', '.docx', '.doc']
        },
        'architecture_diagram': {
            'keywords': ['architecture', 'diagram', 'design'],
            'extensions': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
        },
        'pricing_calculator_csv': {
            'keywords': ['pricing', 'cost', 'calculator'],
            'extensions': ['.csv', '.xlsx']
        }
    }
    
    def __init__(self, client, model_id, mcp_manager=None):
        """
        Initialize the BedrockService.
        
        Args:
            client: Bedrock client.
            model_id (str): Model ID to use.
            mcp_manager: MCP manager instance.
        """
        self.client = client
        self.model_id = model_id
        self.mcp_manager = mcp_manager
        
        # Token usage tracking for rate limit analysis
        self.token_usage_history = defaultdict(list)  # chat_id -> list of (timestamp, tokens)
        self.last_token_limit_time = None
        
        # Initialize token usage logger
        bucket_name = CustomerConfig.get_token_usage_bucket()
        self.token_usage_logger = TokenUsageLogger(bucket_name) if bucket_name else None
        
        # Initialize retry counter for tool calls
        self._current_retry_count = 0
        
        logger.debug(f"BedrockService initialized with model_id: {model_id}")
    
    def _determine_poc_file_type(self, original_filename, file_identification, default_type=None, context="", sow_file_exists=False):
        """
        Determine POC file type using three-tier priority system with configuration-driven rules.
        
        Args:
            original_filename (str): Original filename
            file_identification (dict): File identification from message text
            default_type (str): Default type if no classification found
            context (str): Context for logging (e.g., "document", "image")
            sow_file_exists (bool): Whether a SOW file already exists (for smart defaults)
            
        Returns:
            str: POC file type (sow_document, architecture_diagram, pricing_calculator_csv) or None
        """
        poc_type = None
        
        # First priority: Frontend classification
        if hasattr(self, 'current_file_metadata') and self.current_file_metadata:
            for file_meta in self.current_file_metadata:
                if file_meta.get('original_filename') == original_filename:
                    classification = file_meta.get('document_classification')
                    if classification:
                        poc_type = classification
                        logger.info(f"POC_FUNDING_PARAMS: Using frontend classification for {context}: {original_filename} -> {poc_type}")
                        return poc_type
        
        # Second priority: Message text identification
        if original_filename in file_identification:
            poc_type = file_identification[original_filename]
            logger.info(f"POC_FUNDING_PARAMS: Using explicit file identification for {context}: {original_filename} -> {poc_type}")
            return poc_type
        
        # Third priority: Default type (for images)
        if default_type:
            poc_type = default_type
            logger.info(f"POC_FUNDING_PARAMS: Using default type for {context}: {original_filename} -> {poc_type}")
            return poc_type
        
        # Fourth priority: Configuration-driven filename detection
        filename_lower = original_filename.lower()
        
        # Check each classification rule by keywords
        for classification_type, rules in self.CLASSIFICATION_RULES.items():
            if any(keyword in filename_lower for keyword in rules['keywords']):
                poc_type = classification_type
                logger.info(f"POC_FUNDING_PARAMS: Using keyword detection for {context}: {original_filename} -> {poc_type} (matched keywords)")
                return poc_type
        
        # Fifth priority: Extension-based detection with smart defaults
        for classification_type, rules in self.CLASSIFICATION_RULES.items():
            if any(filename_lower.endswith(ext) for ext in rules['extensions']):
                # Special logic for documents that could be SOW or diagrams
                if classification_type == 'sow_document' and not sow_file_exists:
                    poc_type = classification_type
                elif classification_type == 'sow_document' and sow_file_exists:
                    # If SOW already exists, PDF/DOCX might be architecture diagram
                    poc_type = 'architecture_diagram'
                else:
                    poc_type = classification_type
                
                if poc_type:
                    logger.info(f"POC_FUNDING_PARAMS: Using extension detection for {context}: {original_filename} -> {poc_type}")
                    return poc_type
        
        # No classification found
        logger.info(f"POC_FUNDING_PARAMS: No classification found for {context}: {original_filename}")
        return None
    
    def _animated_wait_with_friendly_message(self, delay_seconds, attempt_num=1):
        """
        Show friendly waiting message with animated dots during throttling delays.
        
        Args:
            delay_seconds (int): Total delay time in seconds
            attempt_num (int): Current attempt number for variety
        
        Yields:
            dict: Streaming response chunks with friendly messages
        """
        # Select a random friendly message
        message_base = random.choice(FRIENDLY_WAITING_MESSAGES) # nosec B311 - Using random for UI message selection, not cryptographic purposes
        
        # Initial message with 3 dots
        yield {
            'type': 'info', 
            'content': f"\n{message_base}..."
        }
        
        # Animate dots during the wait
        elapsed = 0
        
        while elapsed < delay_seconds:
            # Wait for a random interval between 1-3 seconds
            interval = random.uniform(1.0, 3.0) # nosec B311 No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock
            sleep_time = min(interval, delay_seconds - elapsed)  # nosec B311 No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock
            time.sleep(sleep_time)  # nosec B311 No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock
            elapsed += sleep_time
            
            if elapsed < delay_seconds:
                # Add 1-3 more dots to the end of the line
                additional_dots = "." * random.randint(1, 3)  # nosec B311 No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock
                # Send just the additional dots (no newline, just append)
                yield {
                    'type': 'info',
                    'content': additional_dots
                }
    
    def _truncate_conversation_if_needed(self, messages, estimated_tokens):
        """
        Truncate conversation history if it's approaching token limits.
        
        Args:
            messages (list): List of formatted messages
            estimated_tokens (int): Estimated token count
            
        Returns:
            list: Potentially truncated message list
        """
        if estimated_tokens <= MAX_SAFE_TOKENS:
            return messages
            
        logger.warning(f"CONVERSATION_TRUNCATION: {estimated_tokens} tokens > {MAX_SAFE_TOKENS} limit")
        
        # Keep system message (if any) and recent messages
        truncated_messages = []
        current_tokens = 0
        
        # Always keep the most recent message (current user input)
        if messages:
            most_recent_msg = messages[-1]
            truncated_messages.append(most_recent_msg)
            
            # Estimate tokens for the most recent message more accurately
            if isinstance(most_recent_msg.get('content'), list):
                # For content blocks, estimate more conservatively
                recent_tokens = 0
                for block in most_recent_msg['content']:
                    if 'text' in block:
                        recent_tokens += len(block['text']) // 4
                    elif 'document' in block or 'image' in block:
                        # File content blocks use much fewer tokens than their base64 size
                        recent_tokens += 1000  # Conservative estimate for file processing
                current_tokens = recent_tokens
            else:
                current_tokens = len(str(most_recent_msg.get('content', ''))) // 4
        
        # Start from the second-to-last message and work backwards
        for msg in reversed(messages[:-1]):
            msg_content = str(msg.get('content', ''))
            msg_tokens = len(msg_content) // 4
            
            if current_tokens + msg_tokens <= TOKEN_TRUNCATION_TARGET:
                truncated_messages.insert(0, msg)  # Insert at beginning
                current_tokens += msg_tokens
            else:
                break
        
        removed_count = len(messages) - len(truncated_messages)
        logger.warning(f"TRUNCATED: Removed {removed_count} old messages, kept {len(truncated_messages)} recent messages")
        logger.debug(f"TRUNCATED_TOKENS: Reduced from ~{estimated_tokens} to ~{current_tokens} tokens")
        
        return truncated_messages
    
    def _track_token_usage(self, chat_id, estimated_tokens):
        """
        Track token usage for rate limit analysis.
        
        Args:
            chat_id (str): Chat ID for scoping usage
            estimated_tokens (int): Estimated tokens for this request
        """
        now = datetime.now()
        
        # Clean old entries (keep last hour)
        cutoff_time = now - timedelta(hours=1)
        self.token_usage_history[chat_id] = [
            (timestamp, tokens) for timestamp, tokens in self.token_usage_history[chat_id]
            if timestamp > cutoff_time
        ]
        
        # Add current usage
        self.token_usage_history[chat_id].append((now, estimated_tokens))
        
        # Calculate usage in last 1 minute and 5 minutes
        one_minute_ago = now - timedelta(minutes=1)
        five_minutes_ago = now - timedelta(minutes=5)
        
        tokens_last_minute = sum(tokens for timestamp, tokens in self.token_usage_history[chat_id] if timestamp > one_minute_ago)
        tokens_last_5_minutes = sum(tokens for timestamp, tokens in self.token_usage_history[chat_id] if timestamp > five_minutes_ago)
        
        logger.debug(f"TOKEN_USAGE_TRACKING for chat {chat_id}:")
        logger.debug(f"  Current request: ~{estimated_tokens} tokens")
        logger.debug(f"  Last 1 minute: ~{tokens_last_minute} tokens")
        logger.debug(f"  Last 5 minutes: ~{tokens_last_5_minutes} tokens")
        logger.debug(f"  Total requests in last hour: {len(self.token_usage_history[chat_id])}")
        
        # Log if we might be approaching rate limits
        # Claude 3.5 Sonnet typically has limits around 80K tokens/minute
        if tokens_last_minute > 60000:
            logger.warning(f"  HIGH_TOKEN_RATE: {tokens_last_minute} tokens in last minute may trigger rate limiting")
    
    def _validate_tool_execution(self, tool_name, tool_result):
        """
        WAFR FIX #1: Validate tool execution to prevent hallucinated responses.
        
        Args:
            tool_name (str): Name of the tool that was executed
            tool_result (dict): Result from tool execution
            
        Returns:
            dict: Validation result with is_valid, error_message, and user_message
        """
        # Critical WAFR tools that must not fail silently
        critical_wafr_tools = [
            'analyze_architecture_documents',
            'assess_pillar_compliance', 
            'generate_comprehensive_wafr_assessment',
            'generate_professional_report'
        ]
        
        # Check if tool result is None or empty
        if not tool_result:
            return {
                'is_valid': False,
                'error_message': f"Tool {tool_name} returned None or empty result",
                'user_message': "The analysis tool did not return any results."
            }
        
        # Check if tool result has error status
        if tool_result.get('status') == 'error':
            error_content = "Unknown error"
            if isinstance(tool_result.get('content'), list) and len(tool_result['content']) > 0:
                content_item = tool_result['content'][0]
                if hasattr(content_item, 'text'):
                    error_content = content_item.text
                else:
                    error_content = str(content_item)
            
            return {
                'is_valid': False,
                'error_message': f"Tool {tool_name} returned error status: {error_content}",
                'user_message': "The analysis tool encountered an error during execution."
            }
        
        # For critical WAFR tools, perform additional validation
        if tool_name in critical_wafr_tools:
            # Check if content is present and meaningful
            if not isinstance(tool_result.get('content'), list) or len(tool_result['content']) == 0:
                return {
                    'is_valid': False,
                    'error_message': f"Critical WAFR tool {tool_name} returned no content",
                    'user_message': "The WAFR analysis tool did not return any analysis results."
                }
            
            # Check if content has actual text
            content_item = tool_result['content'][0]
            if hasattr(content_item, 'text'):
                content_text = content_item.text.strip()
                if not content_text:
                    return {
                        'is_valid': False,
                        'error_message': f"Critical WAFR tool {tool_name} returned empty content",
                        'user_message': "The WAFR analysis tool returned empty results."
                    }
                
                # Check for common error patterns in WAFR tools
                error_patterns = [
                    "no documents provided",
                    "no documents found",
                    "authentication failed",
                    "connection failed",
                    "tool not found",
                    "error fetching documents"
                ]
                
                content_lower = content_text.lower()
                for pattern in error_patterns:
                    if pattern in content_lower:
                        return {
                            'is_valid': False,
                            'error_message': f"WAFR tool {tool_name} failed: {pattern} detected in response",
                            'user_message': f"The WAFR analysis could not be completed. Please ensure your documents are properly uploaded and try again."
                        }
        
        # Tool execution appears valid
        return {
            'is_valid': True,
            'error_message': None,
            'user_message': None
        }
    
    def _generate_user_friendly_error_message(self, tool_name, validation_result):
        """
        WAFR FIX #3: Generate user-friendly error messages with actionable guidance.
        
        Args:
            tool_name (str): Name of the tool that failed
            validation_result (dict): Result from tool validation
            
        Returns:
            str: User-friendly error message with actionable guidance
        """
        base_message = f"I encountered an issue while trying to execute the {tool_name} tool."
        
        # Provide specific guidance based on tool type
        if tool_name == 'analyze_architecture_documents':
            return f"""{base_message}

**What happened:** The document analysis tool could not process your uploaded files.

**Please try the following:**
1. **Check your document upload:** Ensure your architecture document was successfully uploaded and appears in the Documents section
2. **Verify file format:** Make sure your document is in a supported format (PDF, PNG, JPG, or text files)
3. **Re-upload if needed:** If the document doesn't appear in the Documents section, please upload it again
4. **Wait and retry:** Sometimes there's a brief delay in document processing - wait 30 seconds and try again

If the issue persists, please contact support with the error details."""

        elif tool_name in ['assess_pillar_compliance', 'generate_comprehensive_wafr_assessment']:
            return f"""{base_message}

**What happened:** The WAFR assessment tool could not complete the analysis.

**This usually means:**
- The architecture document analysis hasn't completed yet
- There was an issue accessing the uploaded documents

**Please try:**
1. **Ensure document analysis completed:** Make sure your architecture document was successfully analyzed first
2. **Check document upload:** Verify your document appears in the Documents section
3. **Retry the assessment:** Wait a moment and request the WAFR assessment again

If you continue to see this error, please contact support."""

        elif tool_name == 'generate_professional_report':
            return f"""{base_message}

**What happened:** The report generation tool could not create your WAFR report.

**This usually means:**
- The WAFR assessment hasn't completed yet
- There was an issue with the assessment data

**Please try:**
1. **Complete the assessment first:** Ensure the WAFR assessment has finished successfully
2. **Check for assessment results:** Look for pillar scores and recommendations in the chat
3. **Retry report generation:** Request the report again after the assessment is complete

If the assessment completed but you still can't generate a report, please contact support."""

        else:
            # Generic error message for other tools
            return f"""{base_message}

**Error details:** {validation_result.get('user_message', 'Unknown error occurred')}

**Please try:**
1. **Wait and retry:** Sometimes there are temporary connectivity issues
2. **Check your inputs:** Ensure all required information has been provided
3. **Contact support:** If the issue persists, please contact support with these error details

**Technical details for support:** Tool '{tool_name}' failed with: {validation_result.get('error_message', 'Unknown error')}"""
    
    def _contains_fabricated_wafr_content(self, text, failed_tool_names):
        """
        WAFR FIX #4: Detect potentially fabricated WAFR content after tool failures.
        
        Args:
            text (str): Text content being generated
            failed_tool_names (list): List of tools that failed to execute
            
        Returns:
            bool: True if text appears to contain fabricated WAFR content
        """
        if not text or not failed_tool_names:
            return False
        
        text_lower = text.lower()
        
        # Patterns that indicate fabricated WAFR analysis
        fabricated_patterns = [
            # Specific scores or percentages
            r'\d+\.\d+%',  # e.g., "65.4%", "75.2%"
            r'score.*\d+',  # e.g., "score: 75", "overall score 65"
            r'\d+/\d+',     # e.g., "3/5", "4/10"
            
            # WAFR-specific claims
            'pillar.*score',
            'overall.*wafr.*score',
            'assessment.*complete',
            'successfully.*analyzed',
            'identified.*services',
            'architecture.*analysis',
            'comprehensive.*assessment',
            'detailed.*findings',
            'security.*score',
            'reliability.*score',
            'performance.*score',
            'cost.*optimization.*score',
            'operational.*excellence.*score',
            'sustainability.*score',
            
            # Claims about document analysis
            'analyzed.*document',
            'extracted.*from.*architecture',
            'identified.*aws.*services',
            'detected.*patterns',
            
            # Claims about report generation
            'report.*generated',
            'saved.*to.*document.*storage',
            'professional.*report',
        ]
        
        # Check if any fabricated patterns are present
        import re
        for pattern in fabricated_patterns:
            if re.search(pattern, text_lower):
                logger.debug(f"FABRICATION_DETECTED: Pattern '{pattern}' found in text: length={len(text)}")
                return True
        
        # Additional check: if WAFR tools failed and text contains specific WAFR terminology
        wafr_tools = ['analyze_architecture_documents', 'assess_pillar_compliance', 'generate_comprehensive_wafr_assessment']
        if any(tool in failed_tool_names for tool in wafr_tools):
            wafr_terms = [
                'well-architected',
                'wafr',
                'pillar assessment',
                'architecture assessment',
                'aws services identified',
                'recommendations',
                'security findings',
                'performance insights',
                'cost optimization',
                'reliability concerns'
            ]
            
            for term in wafr_terms:
                if term in text_lower:
                    logger.debug(f"WAFR_FABRICATION_DETECTED: WAFR term '{term}' found after tool failure")
                    return True
        
        return False
    
    def _format_citations_for_display(self, citations):
        """
        Format citations for display in the frontend.
        
        Note: This method is not used for Claude models as they don't support citations.
        It's kept for potential future use with other models that support citations.
        
        Args:
            citations (list): List of citation objects
            
        Returns:
            str: Formatted citation text for display
        """
        if not citations:
            return ""
        
        citation_text = "\n\n**Sources:**\n"
        
        for i, citation in enumerate(citations, 1):
            title = citation.get('title', f'Document {i}')
            citation_text += f"{i}. **{title}**"
            
            # Add location information if available
            if 'location' in citation:
                location = citation['location']
                if isinstance(location, dict):
                    # Handle different location types
                    if 'page' in location:
                        citation_text += f" (Page {location['page']})"
                    elif 'position' in location:
                        citation_text += f" (Position {location['position']})"
                    elif 'chunk' in location:
                        citation_text += f" (Section {location['chunk']})"
            
            # Add source content preview if available
            if 'sourceContent' in citation and citation['sourceContent']:
                # Take the first source content fragment as preview
                preview = citation['sourceContent'][0][:150]
                if len(citation['sourceContent'][0]) > 150:
                    preview += "..."
                citation_text += f"\n   *\"{preview}\"*"
            
            citation_text += "\n"
        
        return citation_text
    
    def _write_pdf_to_temp(self, document_block, doc_name):
        """
        Write PDF document content to temporary file for validation purposes.
        
        Args:
            document_block (dict): Document block containing name, format, and source
            doc_name (str): Name of the document
        """
        try:
            import base64
            import tempfile
            import os
            
            # Get the raw bytes content
            pdf_bytes = document_block.get('source', {}).get('bytes', b'')
            if not pdf_bytes:
                logger.warning(f"No bytes content found for PDF validation: {doc_name}")
                return
            
            logger.debug(f"PDF_VALIDATION: Processing {len(pdf_bytes)} bytes for {doc_name}")
            
            # Create temp directory if it doesn't exist
            temp_dir = "/tmp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Clean filename for filesystem
            safe_filename = "".join(c for c in doc_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            if not safe_filename.lower().endswith('.pdf'):
                safe_filename += '.pdf'
            
            # Write to temp file
            temp_file_path = os.path.join(temp_dir, safe_filename)
            
            with open(temp_file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Get file size for validation
            file_size = os.path.getsize(temp_file_path)
            
            logger.info(f"PDF_VALIDATION: Written PDF to {temp_file_path}")
            logger.info(f"PDF_VALIDATION: File size: {file_size} bytes")
            logger.info(f"PDF_VALIDATION: Raw bytes length: {len(pdf_bytes)} bytes")
            
            # Basic PDF validation - check for PDF header
            if pdf_bytes.startswith(b'%PDF-'):
                logger.info(f"PDF_VALIDATION: ✓ Valid PDF header found in {doc_name}")
            else:
                logger.warning(f"PDF_VALIDATION: ✗ Invalid PDF header in {doc_name}")
            
            # Check for PDF trailer
            if b'%%EOF' in pdf_bytes[-100:]:  # Check last 100 bytes for EOF marker
                logger.info(f"PDF_VALIDATION: ✓ PDF EOF marker found in {doc_name}")
            else:
                logger.warning(f"PDF_VALIDATION: ✗ PDF EOF marker not found in {doc_name}")
            
            # Log content structure for debugging
            logger.debug(f"PDF_VALIDATION: Document block structure:")
            logger.debug(f"  - name: {document_block.get('name', 'N/A')}")
            logger.debug(f"  - format: {document_block.get('format', 'N/A')}")
            logger.debug(f"  - source.bytes length: {len(pdf_bytes)}")
            
        except Exception as e:
            logger.error(f"PDF_VALIDATION: Error writing PDF to temp file: {e}")
            logger.error(f"PDF_VALIDATION: Document name: {doc_name}")
            logger.error(f"PDF_VALIDATION: Document block keys: {list(document_block.keys()) if isinstance(document_block, dict) else 'Not a dict'}")
    
    def _log_request_json_structure(self, request_params):
        """
        Log the complete JSON structure being sent to Bedrock with truncated base64 content.
        
        Args:
            request_params (dict): Request parameters for Bedrock API
        """
        try:
            import copy
            
            # Create a deep copy for logging (to avoid modifying original)
            log_params = copy.deepcopy(request_params)
            
            # Truncate raw bytes content in documents and images for readable logging
            for msg in log_params.get('messages', []):
                for block in msg.get('content', []):
                    if 'document' in block and 'source' in block['document'] and 'bytes' in block['document']['source']:
                        original_length = len(block['document']['source']['bytes'])
                        # For raw bytes, just show length and first few bytes as hex
                        raw_bytes = block['document']['source']['bytes']
                        if len(raw_bytes) > 20:
                            hex_preview = raw_bytes[:20].hex()
                            block['document']['source']['bytes'] = f"[TRUNCATED: {original_length} bytes] {hex_preview}..."
                        else:
                            block['document']['source']['bytes'] = f"[{original_length} bytes] {raw_bytes.hex()}"
                    
                    elif 'image' in block and 'source' in block['image'] and 'bytes' in block['image']['source']:
                        original_length = len(block['image']['source']['bytes'])
                        raw_bytes = block['image']['source']['bytes']
                        if len(raw_bytes) > 20:
                            hex_preview = raw_bytes[:20].hex()
                            block['image']['source']['bytes'] = f"[TRUNCATED: {original_length} bytes] {hex_preview}..."
                        else:
                            block['image']['source']['bytes'] = f"[{original_length} bytes] {raw_bytes.hex()}"
            
            # Log the complete structure
            # logger.debug("BEDROCK_REQUEST_JSON_STRUCTURE:")
            # logger.debug(json.dumps(log_params, indent=2, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"Error logging request JSON structure: {e}")
    

    def _prepare_poc_funding_parameters(self, messages, tool_input, chat_id):
        """
        Prepare parameters for POC funding analysis tool by extracting files from messages.
        
        Args:
            messages (list): List of message objects containing files
            tool_input (dict): Original tool input parameters
            chat_id (str): Chat ID for logging
            
        Returns:
            dict: Enhanced tool input with POC-specific file parameters
        """
        import base64
        
        logger.debug(f"Preparing POC funding parameters for chat {chat_id}")
        logger.debug(f"Input messages count: {len(messages)}")
        
        # Initialize POC parameters
        poc_params = tool_input.copy()
        poc_params['request_metadata'] = poc_params.get('request_metadata', {
            'chat_id': chat_id,
            'analysis_type': 'poc_funding_compliance'
        })
        
        # Extract file identification from message text
        file_identification = {}
        
        # Parse the user message text to find file identification
        if messages:
            message = messages[-1]
            if isinstance(message.get('content'), list):
                for block in message['content']:
                    if 'text' in block:
                        message_text = block['text']
                        logger.info(f"POC_FUNDING_PARAMS: Parsing message text for file identification: length={len(message_text)}")
                        
                        # Parse file identification lines
                        lines = message_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line.startswith('SOW:'):
                                filename = line[4:].strip()
                                file_identification[filename] = 'sow_document'
                                logger.info(f"POC_FUNDING_PARAMS: Identified SOW file: {filename}")
                            elif line.startswith('Diagram:'):
                                filename = line[8:].strip()
                                file_identification[filename] = 'architecture_diagram'
                                logger.info(f"POC_FUNDING_PARAMS: Identified Diagram file: {filename}")
                            elif line.startswith('CSV:'):
                                filename = line[4:].strip()
                                file_identification[filename] = 'pricing_calculator_csv'
                                logger.info(f"POC_FUNDING_PARAMS: Identified CSV file: {filename}")
                        break
        
        logger.info(f"POC_FUNDING_PARAMS: File identification mapping: {file_identification}")
        
        # Extract files from messages
        sow_file = None
        diagram_file = None
        pricing_file = None
        
        # Only process the most recent message (last message) to avoid including files from chat history
        # This ensures only files uploaded with the current POC funding request are analyzed
        if messages:
            # Process only the last message (current request)
            message = messages[-1]
            msg_idx = len(messages) - 1
            logger.info(f"POC_FUNDING_PARAMS: Processing ONLY the most recent message {msg_idx}: role={message.get('role')}")
            
            if isinstance(message.get('content'), list):
                logger.debug(f"Most recent message has {len(message['content'])} content blocks")
                
                for block_idx, block in enumerate(message['content']):
                    logger.debug(f"Block {block_idx} keys: {list(block.keys()) if isinstance(block, dict) else 'not a dict'}")
                    
                    if 'document' in block:
                        doc = block['document']
                        filename = doc.get('name', '').lower()
                        logger.debug(f"Found document: {filename}")
                        
                        # Try different ways to get file bytes
                        file_bytes = None
                        if 'source' in doc and 'bytes' in doc['source']:
                            file_bytes = doc['source']['bytes']
                            logger.debug(f"Got file bytes from source.bytes: {len(file_bytes)} bytes")
                        elif 'bytes' in doc:
                            file_bytes = doc['bytes']
                            logger.debug(f"Got file bytes from direct bytes: {len(file_bytes)} bytes")
                        else:
                            logger.warning(f"Could not find file bytes in document structure: {list(doc.keys())}")
                            continue
                        
                        # Determine file type using optimized classification method
                        original_filename = doc.get('name', '')
                        poc_type = self._determine_poc_file_type(
                            original_filename, 
                            file_identification,
                            default_type=None,
                            context="document",
                            sow_file_exists=sow_file
                        )
                        
                        if not poc_type:
                            logger.info(f"POC_FUNDING_PARAMS: File {original_filename} doesn't match POC funding patterns, skipping")
                            continue
                        
                        logger.info(f"POC_FUNDING_PARAMS: Final POC type determination: {poc_type} for file: {original_filename}")
                        
                        # Convert bytes to base64
                        if file_bytes:
                            base64_content = base64.b64encode(file_bytes).decode('utf-8')
                            logger.debug(f"Converted to base64: {len(base64_content)} characters")
                            
                            if poc_type == 'sow_document' and not sow_file:
                                poc_params['sow_document'] = base64_content
                                poc_params['sow_filename'] = original_filename
                                sow_file = True
                                logger.info(f"POC_FUNDING_PARAMS: ✅ Added SOW document: {original_filename}")
                                
                            elif poc_type == 'pricing_calculator_csv' and not pricing_file:
                                poc_params['pricing_calculator_csv'] = base64_content
                                poc_params['csv_filename'] = original_filename
                                pricing_file = True
                                logger.info(f"POC_FUNDING_PARAMS: ✅ Added pricing calculator: {original_filename}")
                            
                            elif poc_type == 'architecture_diagram' and not diagram_file:
                                poc_params['architecture_diagram'] = base64_content
                                poc_params['diagram_filename'] = original_filename
                                diagram_file = True
                                logger.info(f"POC_FUNDING_PARAMS: ✅ Added architecture diagram: {original_filename}")
                            
                    
                    elif 'image' in block:
                        img = block['image']
                        original_filename = img.get('name', 'image')
                        logger.info(f"POC_FUNDING_PARAMS: Found image: {original_filename}")
                        
                        # Try different ways to get image bytes
                        file_bytes = None
                        if 'source' in img and 'bytes' in img['source']:
                            file_bytes = img['source']['bytes']
                            logger.info(f"POC_FUNDING_PARAMS: Got image bytes from source.bytes: {len(file_bytes)} bytes")
                        elif 'bytes' in img:
                            file_bytes = img['bytes']
                            logger.info(f"POC_FUNDING_PARAMS: Got image bytes from direct bytes: {len(file_bytes)} bytes")
                        else:
                            logger.warning(f"POC_FUNDING_PARAMS: Could not find image bytes in structure: {list(img.keys())}")
                            continue
                        
                        # Determine image type using optimized classification method
                        poc_type = self._determine_poc_file_type(
                            original_filename,
                            file_identification, 
                            default_type='architecture_diagram',
                            context="image"
                        )
                        
                        # Process based on identified type
                        if file_bytes:
                            base64_content = base64.b64encode(file_bytes).decode('utf-8')
                            
                            if poc_type == 'architecture_diagram' and not diagram_file:
                                poc_params['architecture_diagram'] = base64_content
                                poc_params['diagram_filename'] = original_filename
                                diagram_file = True
                                logger.info(f"POC_FUNDING_PARAMS: ✅ Added architecture diagram (image): {original_filename}")
                            elif poc_type == 'sow_document' and not sow_file:
                                poc_params['sow_document'] = base64_content
                                poc_params['sow_filename'] = original_filename
                                sow_file = True
                                logger.info(f"POC_FUNDING_PARAMS: ✅ Added SOW document (image): {original_filename}")
        else:
            logger.warning(f"No messages provided for POC funding parameter preparation")
        
        # Log what was found
        logger.info(f"POC_FUNDING_PARAMS: Final parameter preparation summary:")
        logger.info(f"  SOW document: {'✅' if sow_file else '❌'} {poc_params.get('sow_filename', 'N/A')}")
        logger.info(f"  Architecture diagram: {'✅' if diagram_file else '❌'} {poc_params.get('diagram_filename', 'N/A')}")
        logger.info(f"  Pricing calculator: {'✅' if pricing_file else '❌'} {poc_params.get('csv_filename', 'N/A')}")
        logger.info(f"  Total parameters: {len(poc_params)}")
        
        # Log parameter keys (without sensitive content)
        param_keys = [k for k in poc_params.keys() if not k.endswith('_document') and not k.endswith('_diagram') and not k.endswith('_csv')]
        logger.info(f"  Parameter keys (non-binary): {param_keys}")
        
        # Validate required parameters
        if not sow_file or not diagram_file:
            logger.error(f"POC_FUNDING_PARAMS: ❌ Missing required files - SOW: {sow_file}, Diagram: {diagram_file}")
        else:
            logger.info(f"POC_FUNDING_PARAMS: ✅ All required files present for POC analysis")
        
        return poc_params
        
        
    def send_message_stream(self, messages, chat_id, user_id=None, system_prompt=None, guardrail_id=None, guardrail_version=None, tools=None, prompt_variables=None, file_metadata=None, assistant_persona=None, message_id=None):
        """
        Send a message to Bedrock and yield the response as a stream.
        
        Args:
            messages (list): List of message objects.
            system_prompt (str, optional): System prompt to use.
            guardrail_id (str, optional): Guardrail ID to use.
            guardrail_version (str, optional): Guardrail version to use.
            tools (list, optional): List of tools to include in the request.
            prompt_variables (dict, optional): Variables to substitute in the system prompt.
            chat_id: Chat id used as s3 key prefix when uploading the diagram to the s3 bucket
            file_metadata (list, optional): List of file metadata objects with document classifications
            assistant_persona (AssistantPersona, optional): The assistant persona object for configuration-based logic
            
        Yields:
            dict: Response chunks from Bedrock.
        """
        # Store file metadata for use in tool preparation
        self.current_file_metadata = file_metadata or []
        self.current_message_id = message_id
        self.last_service_def_tool_id = None
        
        # Log prompt variables at the start
        if prompt_variables:
            logger.debug(f"BEDROCK_PROMPT_VARIABLES: Received prompt variables: {list(prompt_variables.keys())}")
            populated_vars = {k: v for k, v in prompt_variables.items() if v}
            logger.debug(f"BEDROCK_PROMPT_VARIABLES: Non-empty variables: {list(populated_vars.keys())}")
        else:
            logger.debug(f"BEDROCK_PROMPT_VARIABLES: No prompt variables provided")
        
        # Log file metadata
        if file_metadata:
            logger.debug(f"BEDROCK_FILE_METADATA: Received {len(file_metadata)} file metadata objects")
            for file_meta in file_metadata:
                classification = file_meta.get('document_classification')
                filename = file_meta.get('original_filename')
                if classification:
                    logger.debug(f"BEDROCK_FILE_METADATA: {filename} -> {classification}")
        else:
            logger.debug(f"BEDROCK_FILE_METADATA: No file metadata provided")
        # Format messages for Bedrock
        formatted_messages = []
        for message in messages:
            # Handle different content formats
            if isinstance(message["content"], str):
                # Simple text message
                formatted_message = {
                    "role": message["role"],
                    "content": [{"text": message["content"]}]
                }
            elif isinstance(message["content"], list):
                # Already formatted ContentBlock list (with files, images, etc.)
                formatted_message = {
                    "role": message["role"],
                    "content": message["content"]
                }
            else:
                # Fallback for other formats
                formatted_message = {
                    "role": message["role"],
                    "content": [{"text": str(message["content"])}]
                }
            formatted_messages.append(formatted_message)
        
        # Prepare request parameters
        request_params = {
            "modelId": self.model_id,
            "messages": formatted_messages
        }
        
        # Add system prompt if provided
        if system_prompt:
            system_prompt += "\n\nIMPORTANT: Only call one tool at a time. Never make multiple tool calls in a single response. Wait for each tool result before calling the next tool."
            system_prompt += "\n\nFORMATTING: Ensure all words are complete and no characters are dropped. All markdown formatting must be properly opened and closed (e.g., every ** must have a matching **)."
            request_params["system"] = [{"text": system_prompt}]
            
        # HYBRID APPROACH: Handle prompt variables based on persona configuration
        use_manual_substitution = False
        
        # Check if persona is configured for manual template substitution
        if assistant_persona and hasattr(assistant_persona, 'use_manual_template_substitution') and assistant_persona.use_manual_template_substitution:
            use_manual_substitution = True
            logger.info(f"HYBRID_APPROACH: persona='{assistant_persona.name}' configured for manual template substitution")
        else:
            persona_name = assistant_persona.name if assistant_persona else "unknown"
            logger.info(f"HYBRID_APPROACH: persona='{persona_name}' using AWS Bedrock native promptVariables")
        
        if use_manual_substitution and prompt_variables:
            # MANUAL SUBSTITUTION - configured via persona settings
            processed_system_prompt = system_prompt
            logger.debug(f"MANUAL_SUBSTITUTION: Processing {len(prompt_variables)} prompt variables for {assistant_persona.name}")
            substitution_count = 0
            for key, value in prompt_variables.items():
                if value:  # Only substitute non-empty values
                    template_var = f"{{{{{key}}}}}"  # Create {{variable_name}} pattern
                    if template_var in processed_system_prompt:
                        processed_system_prompt = processed_system_prompt.replace(template_var, str(value))
                        substitution_count += 1
                        logger.debug(f"MANUAL_SUBSTITUTION: Replaced {template_var} with {str(value)[:100]}...")
                    else:
                        logger.debug(f"MANUAL_SUBSTITUTION: Template {template_var} not found in system prompt")
            
            # Update system prompt with substituted values
            request_params["system"] = [{"text": processed_system_prompt}]
            logger.info(f"MANUAL_SUBSTITUTION: Completed {substitution_count} template substitutions for {assistant_persona.name}")
            
        elif prompt_variables and any(prompt_variables.values()):
            # NATIVE AWS BEDROCK promptVariables for other personas
            formatted_prompt_variables = {}
            for key, value in prompt_variables.items():
                if value:  # Only include non-empty values
                    formatted_prompt_variables[key] = {"text": str(value)}
            
            if formatted_prompt_variables:
                request_params["promptVariables"] = formatted_prompt_variables
                logger.debug(f"NATIVE_PROMPT_VARIABLES: Added {len(formatted_prompt_variables)} variables to request: {list(formatted_prompt_variables.keys())}")
                logger.debug(f"NATIVE_PROMPT_VARIABLES: Using AWS Bedrock native template substitution")
            else:
                logger.debug(f"NATIVE_PROMPT_VARIABLES: No non-empty variables to add")
        elif prompt_variables:
            logger.debug(f"PROMPT_VARIABLES: Skipping empty prompt variables: {list(prompt_variables.keys())}")
            
        # Add guardrails if provided
        if guardrail_id:
            request_params["guardrailConfig"] = {
                "guardrailIdentifier": guardrail_id
            }
            if guardrail_version:
                request_params["guardrailConfig"]["guardrailVersion"] = guardrail_version
        
        # Add tools if provided
        if tools:
            request_params["toolConfig"] = {
                "tools": tools
            }
            tool_names = [tool.get('toolSpec', {}).get('name', 'unknown') for tool in tools]
            logger.info(f"BEDROCK_REQUEST: Adding {len(tools)} tools to Bedrock request: {tool_names}")
            
            # Special logging for POC funding
            if 'analyze_poc_funding_request_urls' in tool_names:
                logger.info(f"POC_FUNDING_BEDROCK: POC funding tool included in Bedrock request")
        else:
            logger.warning(f"BEDROCK_REQUEST: No tools provided to Bedrock - model will not be able to use tools")
        
        # Add inference configuration to limit response length
        # This prevents the model from generating very long responses that hit token limits
        # before completing tool calls
        max_tokens = 6000  # Default limit - generous enough for explanations + tool calls
        
        
        request_params["inferenceConfig"] = {
            "maxTokens": max_tokens,
            "temperature": 0.3  # Balanced temperature for natural prose with consistent tool use
        }
        
        # Log comprehensive request analysis for token debugging
        
        # Calculate detailed metrics
        request_size = sys.getsizeof(str(request_params))
        message_count = len(formatted_messages)
        
        # Count files in messages
        file_count = 0
        for msg in formatted_messages:
            for block in msg.get('content', []):
                if isinstance(block, dict) and ('document' in block or 'image' in block):
                    file_count += 1
        
        # Detailed token estimation (rough approximation: ~4 chars per token)
        total_message_length = sum(len(str(msg.get('content', ''))) for msg in formatted_messages)
        estimated_message_tokens = total_message_length // 4
        
        # Analyze system prompt tokens
        system_prompt_length = len(system_prompt) if system_prompt else 0
        estimated_system_tokens = system_prompt_length // 4
        
        # Analyze tool schema tokens (tools can be very large)
        tool_schema_length = 0
        tool_count = 0
        if tools:
            tool_count = len(tools)
            tool_schema_text = json.dumps(tools)
            tool_schema_length = len(tool_schema_text)
        estimated_tool_tokens = tool_schema_length // 4
        
        # Calculate total estimated tokens
        total_estimated_tokens = estimated_message_tokens + estimated_system_tokens + estimated_tool_tokens
        
        # Apply conversation truncation if needed (before logging final analysis)
        if total_estimated_tokens > MAX_SAFE_TOKENS:
            formatted_messages = self._truncate_conversation_if_needed(formatted_messages, estimated_message_tokens)
            # Recalculate after truncation
            message_count = len(formatted_messages)
            total_message_length = sum(len(str(msg.get('content', ''))) for msg in formatted_messages)
            estimated_message_tokens = total_message_length // 4
            total_estimated_tokens = estimated_message_tokens + estimated_system_tokens + estimated_tool_tokens
            
            # Update request params with truncated messages
            request_params["messages"] = formatted_messages
        
        # Track token usage for rate limit analysis
        self._track_token_usage(chat_id, total_estimated_tokens)
        
        # Log comprehensive analysis
        logger.debug(f"BEDROCK_TOKEN_ANALYSIS:")
        logger.debug(f"  Messages: {message_count} messages, {file_count} files, ~{estimated_message_tokens} tokens ({total_message_length} chars)")
        logger.debug(f"  System: ~{estimated_system_tokens} tokens ({system_prompt_length} chars)")
        logger.debug(f"  Tools: {tool_count} tools, ~{estimated_tool_tokens} tokens ({tool_schema_length} chars)")
        logger.debug(f"  TOTAL_ESTIMATED: ~{total_estimated_tokens} tokens")
        logger.debug(f"  Request size: {request_size} bytes")
        
        # Token-based warnings (Claude 3 models typically have 200K context limit)
        if total_estimated_tokens > 150000:  # 150K token warning
            logger.error(f"CRITICAL: Estimated tokens ({total_estimated_tokens}) approaching context limit!")
        elif total_estimated_tokens > 100000:  # 100K token warning
            logger.warning(f"HIGH: Estimated tokens ({total_estimated_tokens}) very high")
        elif total_estimated_tokens > 50000:  # 50K token warning
            logger.warning(f"MEDIUM: Estimated tokens ({total_estimated_tokens}) getting large")
        
        # Specific warnings for different components
        if estimated_tool_tokens > 50000:
            logger.warning(f"Tool schemas are very large: {estimated_tool_tokens} tokens from {tool_count} tools")
        if estimated_message_tokens > 100000:
            logger.warning(f"Message history is very large: {estimated_message_tokens} tokens from {message_count} messages")
        if message_count > 20:
            logger.warning(f"High message count in conversation: {message_count} messages")
            
        # Log individual message sizes if conversation is large
        if message_count > 10:
            logger.debug("INDIVIDUAL_MESSAGE_ANALYSIS:")
            for i, msg in enumerate(formatted_messages):
                msg_content = str(msg.get('content', ''))
                msg_length = len(msg_content)
                msg_tokens = msg_length // 4
                msg_role = msg.get('role', 'unknown')
                logger.debug(f"  Msg {i+1} ({msg_role}): ~{msg_tokens} tokens ({msg_length} chars)")
                
                # Show preview of very large messages
                if msg_tokens > 5000:
                    preview = msg_content[:100] + "..." if len(msg_content) > 100 else msg_content
                    logger.warning(f"    LARGE MESSAGE preview: {preview}")
        
        # Log tool schemas if they're large
        if tool_count > 0 and estimated_tool_tokens > 10000:
            logger.debug("TOOL_SCHEMA_ANALYSIS:")
            for i, tool in enumerate(tools):
                tool_text = json.dumps(tool)
                tool_length = len(tool_text)
                tool_tokens = tool_length // 4
                tool_name = tool.get('toolSpec', {}).get('name', f'tool_{i}')
                logger.debug(f"  Tool '{tool_name}': ~{tool_tokens} tokens ({tool_length} chars)")
                
                if tool_tokens > 5000:
                    logger.warning(f"    LARGE TOOL SCHEMA: {tool_name}")
        
        logger.debug(f"BEDROCK_REQUEST_SUMMARY: {message_count} msgs, {tool_count} tools, ~{total_estimated_tokens} total tokens")
        
        # Use converse_stream API
        return self._process_streaming_conversation(request_params, chat_id, user_id)
        
    def _process_streaming_conversation(self, request_params, chat_id, user_id=None):
        """
        Process a streaming conversation with Bedrock, handling tool use internally.
        
        Args:
            request_params (dict): Parameters for the Bedrock request.
            
        Yields:
            dict: Response chunks from Bedrock.
        """
        logger.debug("Starting streaming conversation with Bedrock")
        
        # Reset retry count for new requests (but not for recursive retries)
        if not hasattr(self, '_in_retry') or not self._in_retry:
            old_count = getattr(self, '_current_retry_count', 0)
            self._current_retry_count = 0
            if old_count > 0:
                logger.debug(f"TOOL_RETRY: Reset retry count from {old_count} to 0 for new request")
        
        # Implement exponential backoff for API calls
        # Get retry configuration
        max_retries = CustomerConfig.get_bedrock_max_retries()
        throttle_delay = CustomerConfig.get_bedrock_throttle_delay()
        
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Keep track of all messages in the conversation
                conversation_messages = request_params.get('messages', []).copy()
                
                # Make the API call
                logger.debug("Calling Bedrock converse_stream API")
                logger.debug(f"API_CALL_PARAMS: modelId={request_params.get('modelId')}")
                logger.debug(f"API_CALL_PARAMS: messages_count={len(request_params.get('messages', []))}")
                logger.debug(f"API_CALL_PARAMS: has_system={bool(request_params.get('system'))}")
                logger.debug(f"API_CALL_PARAMS: has_tools={bool(request_params.get('toolConfig'))}")
                
                # Check if any message has file content
                has_files = False
                file_blocks_found = []
                for i, msg in enumerate(request_params.get('messages', [])):
                    for j, block in enumerate(msg.get('content', [])):
                        if 'document' in block:
                            has_files = True
                            doc_name = block['document']['name']
                            doc_format = block['document'].get('format', 'unknown')
                            file_blocks_found.append(f"msg{i}_block{j}: document({doc_name}) format={doc_format}")
                            logger.debug(f"DOCUMENT_NAME_SENT_TO_BEDROCK: '{doc_name}' (format: {doc_format})")
                            
                            # Write PDF files to disk for validation
                            if doc_format == 'pdf':
                                self._write_pdf_to_temp(block['document'], doc_name)
                                
                        elif 'image' in block:
                            has_files = True
                            file_blocks_found.append(f"msg{i}_block{j}: image({block['image']['format']})")
                        else:
                            # Log what type of block this is
                            block_type = list(block.keys())[0] if block else 'empty'
                            file_blocks_found.append(f"msg{i}_block{j}: {block_type}")
                    if has_files:
                        break
                
                logger.debug(f"API_CALL_PARAMS: has_file_content={has_files}")
                logger.debug(f"API_CALL_PARAMS: content_blocks_found={file_blocks_found}")
                
                # Log complete JSON structure for debugging (with truncated base64 content)
                self._log_request_json_structure(request_params)
                
                # Log input size before API call
                import json
                request_json = json.dumps(request_params, default=str)
                request_size = len(request_json)
                logger.debug(f"BEDROCK_INPUT_SIZE: {request_size:,} chars ({request_size/1024:.1f} KB)")
                if request_size > 500000:  # 500KB threshold
                    logger.warning(f"LARGE_INPUT_DETECTED: {request_size:,} chars - may exceed model limits")
                
                response = self.client.converse_stream(**request_params)
                logger.debug("Received initial response from Bedrock")
                
                # If we get here, the API call was successful, so break out of the retry loop
                break
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                # Log input size for ValidationException (input too long)
                if error_code == 'ValidationException' and 'too long' in error_message:
                    import json
                    request_json = json.dumps(request_params, default=str)
                    request_size = len(request_json)
                    logger.error(f"INPUT_TOO_LONG: {request_size:,} chars ({request_size/1024/1024:.2f} MB)")
                    logger.error(f"Model: {request_params.get('modelId')}")
                    logger.error(f"Messages count: {len(request_params.get('messages', []))}")
                    
                    # Log message sizes
                    for i, msg in enumerate(request_params.get('messages', [])):
                        msg_size = len(json.dumps(msg, default=str))
                        logger.error(f"Message {i}: {msg_size:,} chars")
                
                # Check if this is a throttling error
                if error_code == 'ThrottlingException':
                    retry_count += 1
                    
                    logger.error(f"Bedrock throttling error (attempt {retry_count}/{max_retries}): {error_message}")
                    
                    # If we've reached the maximum number of retries, stop
                    if retry_count > max_retries:
                        logger.error(f"Maximum retries ({max_retries}) exceeded for throttling error")
                        yield {
                            'type': 'error',
                            'content': f"Bedrock API throttling error: Maximum retries exceeded. {error_message}"
                        }
                        return
                    
                    # Send a random thinking message and wait
                    thinking_message = random.choice(FRIENDLY_WAITING_MESSAGES) #nosemgrep No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock # nosec B311 - Using random for UI message selection, not cryptographic purposes
                    logger.debug(f"Showing thinking message: {thinking_message}")
                    yield {
                        'type': 'info',
                        'content': f"\n{thinking_message}..."
                    }
                    
                    # Wait for the configured delay
                    time.sleep(throttle_delay)
                    continue
                else:
                    # For non-throttling errors, raise immediately
                    logger.error(f"Bedrock API error: {error_code} - {error_message}")
                    yield {
                        'type': 'error',
                        'content': f"Bedrock API error: {error_message}"
                    }
                    return
            except Exception as e:
                logger.error(f"Error making API call: {e}")
                yield {
                    'type': 'error',
                    'content': f"An error occurred while calling Bedrock API: {str(e)}"
                }
                return
                
        # Variables to track conversation state
        current_tool_use = None
        accumulated_text = ""
        current_assistant_message = {"role": "assistant", "content": []}
        
        # WAFR FIX #4: Fallback Prevention - Track tool execution state
        tool_execution_failed = False
        failed_tool_names = []
        accumulated_citations = []  # Track citations for this response (not used for Claude models)
        current_content_block_index = 0  # Track which content block we're processing
        
        # Process the streaming response
        try:
            for event in response.get('stream', []):
                # Log the event type for debugging
                event_type = list(event.keys())[0] if event else "unknown"
                logger.debug(f"Received event type: {event_type}")
                
                # Handle message start
                if 'messageStart' in event:
                    role = event['messageStart']['role']
                    logger.debug(f"Message start: role={role}")
                    current_assistant_message = {"role": role, "content": []}
                    yield {
                        'type': 'start',
                        'role': role
                    }
                    
                # Handle content blocks (regular text responses)
                elif 'contentBlockDelta' in event:
                    content_block_index = event['contentBlockDelta'].get('contentBlockIndex', 0)
                    if 'delta' in event['contentBlockDelta']:
                        if 'text' in event['contentBlockDelta']['delta']:
                            text = event['contentBlockDelta']['delta']['text']
                            
                            # WAFR FIX #4: Fallback Prevention - Block fabricated responses
                            if tool_execution_failed and self._contains_fabricated_wafr_content(text, failed_tool_names):
                                logger.warning(f"FALLBACK_PREVENTION: Blocking potentially fabricated WAFR content after tool failure")
                                error_message = "I apologize, but I cannot provide WAFR analysis results because the required tools failed to execute properly. Please resolve the tool execution issues and try again."
                                yield {"type": "content", "content": error_message}
                                yield {"type": "stop", "stop_reason": "fabricated_content_blocked"}
                                return
                            
                            accumulated_text += text
                            logger.debug(f"Content delta: length={len(text)}, block_index={content_block_index}")
                            
                            # Ensure we have enough content blocks in the message
                            while len(current_assistant_message['content']) <= content_block_index:
                                current_assistant_message['content'].append({"text": ""})
                            
                            # Add text to the specific content block
                            if "text" in current_assistant_message['content'][content_block_index]:
                                current_assistant_message['content'][content_block_index]["text"] += text
                            else:
                                current_assistant_message['content'][content_block_index] = {"text": text}
                            
                            yield {
                                'type': 'content',
                                'content': text
                            }
                        elif 'citation' in event['contentBlockDelta']['delta']:
                            # Handle citation information from documents
                            # Note: Claude models don't support citations, so this code path should not be reached
                            citation_delta = event['contentBlockDelta']['delta']['citation']
                            logger.warning(f"CITATION_UNEXPECTED: Received citation delta from Claude model: {citation_delta}")
                            logger.warning(f"This suggests the model configuration may be incorrect or citations are enabled for a non-supporting model")
                            
                        elif 'toolUse' in event['contentBlockDelta']['delta']:
                            if 'input' in event['contentBlockDelta']['delta']['toolUse']:
                                tool_input_fragment = event['contentBlockDelta']['delta']['toolUse']['input']
                                if current_tool_use and current_tool_use.get('content_block_index') == content_block_index:
                                    current_tool_use['input'] += tool_input_fragment
                                    # COMMENTED OUT: Special POC funding logging
                                    # if current_tool_use['name'] == 'analyze_poc_funding_request':
                                    #     logger.debug(f"POC_FUNDING_TOOL: Received input fragment, total length: {len(current_tool_use['input'])}")
                                    # Only log every 100 characters to reduce noise for all tools
                                    if len(current_tool_use['input']) % 100 == 0:
                                        logger.debug(f"Tool input length: {len(current_tool_use['input'])}")
                                else:
                                    logger.error(f"TOOL_DEBUG: Received fragment but current_tool_use is None or wrong block index!")
                            
                # Handle content block start events (for tool use)
                elif 'contentBlockStart' in event:
                    content_block_index = event['contentBlockStart'].get('contentBlockIndex', 0)
                    current_content_block_index = content_block_index
                    
                    if 'start' in event['contentBlockStart'] and 'toolUse' in event['contentBlockStart']['start']:
                        tool_info = event['contentBlockStart']['start']['toolUse']
                        current_tool_use = {
                            'toolUseId': tool_info.get('toolUseId', 'unknown'),
                            'name': tool_info.get('name', 'unknown'),
                            'input': '',
                            'content_block_index': content_block_index
                        }
                        logger.debug(f"TOOL_DEBUG: Received tool use request with ID: {current_tool_use['toolUseId']}, block_index={content_block_index}")
                        logger.debug(f"Tool use start: name={current_tool_use['name']}, id={current_tool_use['toolUseId']}")
                        
                        # COMMENTED OUT: Special POC funding logging
                        # if current_tool_use['name'] == 'analyze_poc_funding_request':
                        #     logger.debug(f"POC_FUNDING_TOOL: Tool use started for POC funding analysis")
                        
                        # Ensure we have enough content blocks in the message
                        while len(current_assistant_message['content']) <= content_block_index:
                            current_assistant_message['content'].append({})
                        
                        # Add toolUse to the specific content block
                        tool_use_content = {
                            "toolUse": {
                                "toolUseId": current_tool_use['toolUseId'],
                                "name": current_tool_use['name'],
                                "input": {}  # Will be filled in as we receive input fragments
                            }
                        }
                        current_assistant_message['content'][content_block_index] = tool_use_content
                        
                # Handle content block stop events (for tool use)
                elif 'contentBlockStop' in event:
                    if current_tool_use:
                        logger.debug(f"Content block stop for tool: {current_tool_use['name']}")
                        logger.debug(f"Tool input complete, length: {len(current_tool_use['input'])}")
                        # Note: JSON parsing moved to messageStop to avoid race condition
                        
                # Handle message stop
                elif 'messageStop' in event:
                    stop_reason = event['messageStop'].get('stopReason')
                    logger.debug(f"Message stop: reason={stop_reason}")
                    
                    # COMMENTED OUT: Special POC funding max_tokens handling
                    if stop_reason == 'max_tokens' and current_tool_use:
                        logger.warning(f"Message stopped due to max_tokens while tool '{current_tool_use['name']}' was in progress")
                        logger.warning(f"Tool input received so far: {len(current_tool_use.get('input', ''))} characters")
                        # if current_tool_use['name'] == 'analyze_poc_funding_request':
                        #     logger.error(f"POC_FUNDING_TOOL: POC funding analysis was interrupted by token limit!")
                    
                    # Parse tool input JSON now that all fragments are guaranteed received
                    if current_tool_use:
                        # Update the tool input in the assistant message using the correct content block index
                        content_block_index = current_tool_use.get('content_block_index', 0)
                        if content_block_index < len(current_assistant_message['content']):
                            content_item = current_assistant_message['content'][content_block_index]
                            if "toolUse" in content_item and content_item["toolUse"]["toolUseId"] == current_tool_use['toolUseId']:
                                try:
                                    if current_tool_use['input'].strip():
                                        parsed_input = json.loads(current_tool_use['input'])
                                        content_item["toolUse"]["input"] = parsed_input
                                        logger.debug(f"Tool input parsed successfully for block {content_block_index}")
                                    else:
                                        # Empty input should be empty JSON object
                                        content_item["toolUse"]["input"] = {}
                                        logger.debug(f"Empty tool input, using default object for block {content_block_index}")
                                except json.JSONDecodeError as e:
                                    logger.error(f"Tool input JSON parse error: {e}")
                                    content_item["toolUse"]["input"] = {}
                    
                    # Add the assistant message to the conversation
                    if current_assistant_message['content']:
                        conversation_messages.append(current_assistant_message)
                    
                    # Handle max_tokens interruption during tool use - retry original request with higher limits
                    if stop_reason == 'max_tokens' and current_tool_use:
                        logger.warning(f"TOOL_RETRY: Tool '{current_tool_use['name']}' was interrupted by max_tokens, retrying with higher limits")
                        
                        # Check if we've already retried to prevent infinite loops
                        retry_count = getattr(self, '_current_retry_count', 0)
                        max_retries = 3  # Allow up to 3 retries for token limit issues
                        
                        logger.debug(f"TOOL_RETRY: Current retry count: {retry_count}, max: {max_retries}")
                        
                        if retry_count >= max_retries:
                            logger.error(f"TOOL_RETRY: Maximum retries ({max_retries}) reached for tool '{current_tool_use['name']}'")
                            # Reset retry count for next request
                            self._current_retry_count = 0
                            yield {
                                'type': 'error',
                                'content': f"Tool execution failed: '{current_tool_use['name']}' was interrupted by response length limits after {max_retries} retries. Please try with a shorter message or contact support."
                            }
                            return
                        
                        # Increment retry count
                        self._current_retry_count = retry_count + 1
                        logger.info(f"TOOL_RETRY: Starting retry attempt {self._current_retry_count}/{max_retries} for '{current_tool_use['name']}'")
                        
                        # Create retry parameters with increased token limits
                        retry_params = request_params.copy()
                        
                        # Significantly increase maxTokens for retry
                        if "inferenceConfig" in retry_params:
                            original_max_tokens = retry_params["inferenceConfig"]["maxTokens"]
                            # Be more generous with token increases
                            if retry_count == 1:
                                new_max_tokens = 8000  # First retry: jump to 8000
                            else:
                                new_max_tokens = 12000  # Second retry: even higher
                            retry_params["inferenceConfig"]["maxTokens"] = new_max_tokens
                            logger.debug(f"TOOL_RETRY: Increased maxTokens from {original_max_tokens} to {new_max_tokens}")
                        
                        # COMMENTED OUT: Special POC funding retry handling
                        # if current_tool_use['name'] == 'analyze_poc_funding_request':
                        #     logger.debug("TOOL_RETRY: Keeping balanced system prompt for POC funding retry")
                        
                        logger.debug(f"TOOL_RETRY: Retrying original request with enhanced parameters")
                        
                        # Mark that we're in a retry to prevent resetting retry count
                        self._in_retry = True
                        
                        try:
                            # Recursively retry the original request
                            for chunk in self._process_streaming_conversation(retry_params, chat_id, user_id):
                                yield chunk
                            
                            # Reset retry count on successful completion
                            self._current_retry_count = 0
                        finally:
                            # Always reset retry flag
                            self._in_retry = False
                        
                        return
                    
                    # Handle normal tool_use completion
                    elif stop_reason == 'tool_use' and current_tool_use:
                        # Log tool execution start
                        logger.debug(f"=== TOOL EXECUTION: {current_tool_use['name']} ===")
                        logger.debug(f"Tool input length: {len(current_tool_use.get('input', ''))}")
                        
                        # Handle tool use (allow empty input for tools with optional parameters)
                        logger.debug(f"Executing tool: {current_tool_use['name']}")
                        tool_name = current_tool_use.get('name', 'UNKNOWN')
                        logger.debug(f"TOOL_DEBUG: About to execute tool with name: '{tool_name}'")
                        logger.debug(f"TOOL_DEBUG: Checking if tool_name == 'update_conversation_stage': {tool_name == 'update_conversation_stage'}")
                        
                        # Don't show stage tool usage to user
                        if tool_name != "update_conversation_stage":
                            yield {
                                'type': 'info',
                                'content': f"Using tool {tool_name}...\n\n"
                            }
                        
                        try:
                            # Parse the JSON input, default to empty object if input is empty
                            input_str = current_tool_use['input'].strip()
                            if not input_str:
                                tool_input = {}
                                logger.debug(f"Tool input is empty, using default empty object: {{}}")
                            else:
                                tool_input = json.loads(input_str)
                                
                                # Fix for architecture_data being serialized as string by Claude
                                if isinstance(tool_input, dict) and 'architecture_data' in tool_input:
                                    if isinstance(tool_input['architecture_data'], str):
                                        try:
                                            tool_input['architecture_data'] = json.loads(tool_input['architecture_data'])
                                            logger.debug("Fixed architecture_data: converted from string to dict")
                                        except json.JSONDecodeError:
                                            logger.warning("Failed to parse architecture_data string as JSON")
                                
                                logger.debug(f"Tool input keys: {list(tool_input.keys()) if isinstance(tool_input, dict) else 'non-dict'}")
                            
                            # Execute the tool (using thread pool to avoid event loop conflicts)
                            if self.mcp_manager:
                                if tool_name == "update_conversation_stage":
                                    # Handle built-in stage tool - skip MCP execution
                                    logger.debug(f"STAGE_TOOL: Processing stage tool independently")
                                    stage = tool_input.get('stage') if isinstance(tool_input, dict) else None
                                    if stage:
                                        logger.debug(f"STAGE_TOOL: Updating conversation stage to {stage}")
                                        from .chat_service import update_conversation_stage
                                        try:
                                            update_conversation_stage(user_id, chat_id, stage)
                                            logger.debug(f"STAGE_TOOL: Successfully updated stage to {stage}")
                                            # Create MCP-compatible result
                                            class StageContent:
                                                def __init__(self, text):
                                                    self.text = text
                                            tool_result = {
                                                "content": [StageContent("Stage updated successfully")],
                                                "status": "success"
                                            }
                                        except Exception as e:
                                            logger.error(f"STAGE_TOOL: Failed to update stage: {e}")
                                            tool_result = {
                                                "content": [StageContent(f"Failed to update stage: {e}")],
                                                "status": "error"
                                            }
                                    else:
                                        tool_result = {
                                            "content": [StageContent("No stage provided")],
                                            "status": "error"
                                        }
                                else:
                                    # Handle MCP tools normally
                                    logger.debug(f"Calling MCP manager to execute tool: {tool_name}")
                                    
                                    # Run async MCP calls in a separate thread to avoid event loop conflicts
                                    def run_mcp_tool():
                                        logger.debug(f'calling MCPs with chat_id: {chat_id}')
                                        return asyncio.run(self.mcp_manager.execute_tool(
                                            tool_name, 
                                            tool_input,
                                            chat_id=chat_id  # Pass chat_id for connection pooling
                                        ))
                                    
                                    with concurrent.futures.ThreadPoolExecutor() as executor:
                                        future = executor.submit(run_mcp_tool)
                                        tool_result = future.result()
                                
                                logger.debug(f"Tool execution complete: status={tool_result.get('status', 'unknown')}")
                                
                                # Log tool result summary only (not full content to reduce overhead)
                                result_length = 0
                                if isinstance(tool_result.get('content'), list) and len(tool_result['content']) > 0:
                                    content_item = tool_result['content'][0]
                                    if hasattr(content_item, 'text'):
                                        result_length = len(content_item.text)
                                logger.debug(f"Tool result: status={tool_result.get('status', 'unknown')}, content_length={result_length}")

                                # WAFR FIX #1: Tool Execution Validation
                                # Validate tool execution and prevent hallucinated responses
                                tool_validation_result = self._validate_tool_execution(tool_name, tool_result)
                                if not tool_validation_result['is_valid']:
                                    logger.error(f"TOOL_VALIDATION_FAILED: {tool_validation_result['error_message']}")
                                    
                                    # WAFR FIX #4: Fallback Prevention - Mark tool execution as failed
                                    tool_execution_failed = True
                                    failed_tool_names.append(tool_name)
                                    
                                    # WAFR FIX #3: Error Transparency
                                    # Provide clear, actionable error messages to users
                                    error_message = self._generate_user_friendly_error_message(tool_name, tool_validation_result)
                                    
                                    # Return error immediately to prevent hallucinated responses
                                    error_response = {
                                        "role": "assistant",
                                        "content": [{"text": error_message}]
                                    }
                                    yield {"type": "content", "content": error_response["content"][0]["text"]}
                                    yield {"type": "stop", "stop_reason": "tool_execution_failed"}
                                    return

                                # Check if the tool result has an error status or contains error content
                                content_has_error = False
                                error_message = None
                                
                                # First check the tool result status
                                if tool_result.get('status') == 'error':
                                    content_has_error = True
                                    # Extract error message from content
                                    if isinstance(tool_result.get('content'), list) and len(tool_result['content']) > 0:
                                        content_item = tool_result['content'][0]
                                        if hasattr(content_item, 'text'):
                                            error_message = content_item.text
                                        else:
                                            error_message = str(content_item)
                                    else:
                                        error_message = "Tool execution failed"
                                    logger.debug(f"Tool returned error status: {error_message}")
                                
                                # Also check if content contains embedded error (for backward compatibility)
                                elif isinstance(tool_result.get('content'), list) and len(tool_result['content']) > 0:
                                    content_item = tool_result['content'][0]
                                    if hasattr(content_item, 'text'):
                                        content_text = content_item.text
                                        try:
                                            # Try to parse the content as JSON to check for embedded error
                                            content_json = json.loads(content_text)
                                            if isinstance(content_json, dict) and content_json.get('status') == 'error':
                                                content_has_error = True
                                                # Handle both flat and nested error message structures
                                                error_message = content_json.get('message')
                                                if not error_message and 'error' in content_json:
                                                    error_obj = content_json['error']
                                                    if isinstance(error_obj, dict):
                                                        error_message = error_obj.get('message')
                                                if not error_message:
                                                    error_message = 'Unknown error in tool execution'
                                                logger.debug(f"Tool content indicates error: {error_message}")
                                        except json.JSONDecodeError:
                                            # Not JSON, continue with normal processing
                                            pass
                                
                                # Create a tool result message
                                if content_has_error:
                                    # Create an error response that the LLM can see and respond to
                                    tool_result_message = {
                                        "role": "user",
                                        "content": [
                                            {
                                                "toolResult": {
                                                    "toolUseId": current_tool_use['toolUseId'],
                                                    "content": [{"text": error_message or "Error in tool execution"}],
                                                    "status": "error"
                                                }
                                            }
                                        ]
                                    }
                                    logger.debug(f"Created error tool result with message: {error_message}")
                                else:
                                    # Tool use ID validation
                                    logger.debug(f"ToolUseId: {current_tool_use['toolUseId'][:8]}...")
                                    tool_results_json = None
                                    tool_result_message = None
                                    # Check for special tool handling
                                    logger.debug(f"Checking for document upload: {current_tool_use['name']}")
                                    logger.debug(f"TOOL_DEBUG: Processing tool '{current_tool_use['name']}'")
                                    logger.debug(f"TOOL_DEBUG: document generation result: {tool_result}")
                                    if current_tool_use['name'] == "generate_diagram":
                                        # Handle the generate_diagram tool result    
                                        logger.debug(f"TOOL_DEBUG: Raw MCP tool result: {tool_result}")
                                        
                                        if tool_result.get('content') and len(tool_result['content']) > 0:
                                            content_text = tool_result['content'][0].text
                                            
                                            try:
                                                tool_results_json = json.loads(content_text)
                                                
                                                if isinstance(tool_results_json, dict) and tool_results_json.get('s3_url'):
                                                    # Store document and get reference
                                                    doc_reference = store_document_and_create_reference(
                                                        chat_id, 'diagram', tool_results_json, 'generate_diagram'
                                                    )
                                                    
                                                    tool_result_message = {
                                                        "role": "user",
                                                        "content": [
                                                            {
                                                                "toolResult": {
                                                                    "toolUseId": current_tool_use['toolUseId'],
                                                                    "content": [{"text": f"Architecture diagram generated successfully. {doc_reference}"}],
                                                                    "status": "success"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                    
                                                    # Return simple text reference - document will be available in Documents section
                                                    yield {
                                                        'type': 'content',
                                                        'content': f" Architecture diagram generated successfully. See Documents section below. \n\n"
                                                    }
                                                else:
                                                    error_message = tool_results_json.get('message', 'Unknown error')
                                                    yield {
                                                        'type': 'content',
                                                        'content': f" ![Diagram generation failed: {error_message}] \n\n"
                                                    }
                                                    
                                            except json.JSONDecodeError as e:
                                                logger.error(f"TOOL_DEBUG: Failed to parse JSON: {e}")
                                                yield {
                                                    'type': 'content',
                                                    'content': f" ![Diagram generation failed - invalid response format] \n\n"
                                                }
                                        else:
                                            logger.error(f"TOOL_DEBUG: No content in MCP tool result")
                                            yield {
                                                'type': 'content',
                                                'content': f" ![Diagram generation failed - no content returned] \n\n"
                                            }

                                    # ============================================================
                                    # WAFR TOOL RESULT COMPRESSION
                                    # These handlers compress large WAFR tool results to prevent
                                    # INPUT_TOO_LONG errors when Bedrock accumulates conversation context
                                    # ============================================================
                                    
                                    elif current_tool_use['name'] == "analyze_architecture_documents":
                                        # Compress architecture analysis results to prevent context overflow
                                        # The full result can be ~666KB which causes INPUT_TOO_LONG after first pillar
                                        logger.debug(f"WAFR_DEBUG: Compressing analyze_architecture_documents result")
                                        
                                        try:
                                            if tool_result.get('content') and len(tool_result['content']) > 0:
                                                content_text = tool_result['content'][0].text
                                                tool_results_json = json.loads(content_text)
                                                
                                                # Extract key summary info for compact result
                                                total_documents = tool_results_json.get('total_documents', 0)
                                                services_count = len(tool_results_json.get('identified_services', []))
                                                patterns_count = len(tool_results_json.get('architectural_patterns', []))
                                                
                                                # Get service names for summary (first 10)
                                                services_list = []
                                                for svc in tool_results_json.get('identified_services', [])[:10]:
                                                    if isinstance(svc, dict):
                                                        svc_name = svc.get('item', '').split(' - ')[0].replace('**', '').strip()
                                                        if svc_name:
                                                            services_list.append(svc_name)
                                                    elif isinstance(svc, str):
                                                        services_list.append(svc.split(' - ')[0].replace('**', '').strip())
                                                
                                                services_summary = ', '.join(services_list[:10])
                                                if services_count > 10:
                                                    services_summary += f" (+{services_count - 10} more)"
                                                
                                                # Create compact summary for Bedrock context
                                                compact_summary = (
                                                    f"Architecture analysis complete. "
                                                    f"Analyzed {total_documents} documents. "
                                                    f"Identified {services_count} AWS services: {services_summary}. "
                                                    f"Detected {patterns_count} architectural patterns. "
                                                    f"Full architecture_data is available for pillar assessments."
                                                )
                                                
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": compact_summary}],
                                                                "status": "success"
                                                            }
                                                        }
                                                    ]
                                                }
                                                
                                                logger.info(f"WAFR_DEBUG: Compressed architecture analysis from {len(content_text)} chars to {len(compact_summary)} chars")
                                                
                                                yield {
                                                    'type': 'content',
                                                    'content': f"✅ Architecture analysis complete: {total_documents} documents, {services_count} services identified"
                                                }
                                                
                                        except Exception as e:
                                            logger.error(f"WAFR_DEBUG: Failed to compress architecture analysis: {e}")
                                            # Fall through to default handling
                                            tool_result_message = None
                                    
                                    elif current_tool_use['name'] == "assess_pillar_compliance":
                                        # Compress pillar assessment results to prevent context overflow
                                        # Each pillar result can be large; we only need summary for next steps
                                        logger.debug(f"WAFR_DEBUG: Compressing assess_pillar_compliance result")
                                        
                                        try:
                                            if tool_result.get('content') and len(tool_result['content']) > 0:
                                                content_text = tool_result['content'][0].text
                                                tool_results_json = json.loads(content_text)
                                                
                                                # Extract key metrics for compact result
                                                pillar = tool_results_json.get('pillar', 'unknown')
                                                score = tool_results_json.get('score', 0)
                                                risk_level = tool_results_json.get('risk_level', 'Unknown')
                                                success = tool_results_json.get('success', False)
                                                
                                                # Get recommendation count
                                                recommendations = tool_results_json.get('recommendations', [])
                                                rec_count = len(recommendations)
                                                
                                                # Get top recommendation titles (first 3)
                                                top_recs = []
                                                for rec in recommendations[:3]:
                                                    if isinstance(rec, dict):
                                                        top_recs.append(rec.get('title', 'Unnamed'))
                                                    elif isinstance(rec, str):
                                                        top_recs.append(rec[:50])
                                                
                                                # Create compact summary for Bedrock context
                                                if success:
                                                    compact_summary = (
                                                        f"Pillar: {pillar} | Score: {score}% | Risk: {risk_level} | "
                                                        f"Recommendations: {rec_count}"
                                                    )
                                                    if top_recs:
                                                        compact_summary += f" | Top: {', '.join(top_recs)}"
                                                else:
                                                    error_msg = tool_results_json.get('error', 'Unknown error')
                                                    compact_summary = f"Pillar: {pillar} | Assessment failed: {error_msg}"
                                                
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": compact_summary}],
                                                                "status": "success" if success else "error"
                                                            }
                                                        }
                                                    ]
                                                }
                                                
                                                logger.info(f"WAFR_DEBUG: Compressed {pillar} assessment from {len(content_text)} chars to {len(compact_summary)} chars")
                                                
                                                # Yield progress update with clean format (no scores, just risk level)
                                                if success:
                                                    pillar_display = pillar.replace('_', ' ').title()
                                                    # Clean up risk_level to avoid "Risk Risk" duplication
                                                    risk_display = risk_level.replace(' Risk', '').replace(' risk', '')
                                                    # Add warning emoji for Medium or High risk
                                                    risk_indicator = " ⚠️" if risk_display.lower() in ['medium', 'high'] else ""
                                                    yield {
                                                        'type': 'content',
                                                        'content': f"✅ {pillar_display} — {risk_display} Risk{risk_indicator}\n"
                                                    }
                                                else:
                                                    yield {
                                                        'type': 'content',
                                                        'content': f"❌ {pillar.replace('_', ' ').title()} — Assessment failed\n"
                                                    }
                                                
                                        except Exception as e:
                                            logger.error(f"WAFR_DEBUG: Failed to compress pillar assessment: {e}")
                                            # Fall through to default handling
                                            tool_result_message = None
                                    
                                    elif current_tool_use['name'] == "generate_comprehensive_wafr_assessment":
                                        # Compress comprehensive assessment results
                                        logger.debug(f"WAFR_DEBUG: Compressing generate_comprehensive_wafr_assessment result")
                                        
                                        try:
                                            if tool_result.get('content') and len(tool_result['content']) > 0:
                                                content_text = tool_result['content'][0].text
                                                tool_results_json = json.loads(content_text)
                                                
                                                # Extract overall metrics
                                                overall_score = tool_results_json.get('overall_score', 0)
                                                overall_risk = tool_results_json.get('overall_risk_level', 'Unknown')
                                                pillars_assessed = len(tool_results_json.get('pillar_scores', {}))
                                                
                                                # Get pillar scores summary
                                                pillar_scores = tool_results_json.get('pillar_scores', {})
                                                pillar_summary = ', '.join([
                                                    f"{p.replace('_', ' ').title()[:3]}: {s}%"
                                                    for p, s in list(pillar_scores.items())[:6]
                                                ])
                                                
                                                # Create compact summary
                                                compact_summary = (
                                                    f"WAFR Assessment Complete | Overall: {overall_score}% ({overall_risk}) | "
                                                    f"Pillars: {pillars_assessed} | Scores: {pillar_summary}"
                                                )
                                                
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": compact_summary}],
                                                                "status": "success"
                                                            }
                                                        }
                                                    ]
                                                }
                                                
                                                logger.info(f"WAFR_DEBUG: Compressed comprehensive assessment from {len(content_text)} chars to {len(compact_summary)} chars")
                                                
                                                # Clean risk level display (remove "Risk" if already present)
                                                risk_display = overall_risk.replace(' Risk', '').replace(' risk', '')
                                                yield {
                                                    'type': 'content',
                                                    'content': f"✅ WAFR Assessment Complete — {risk_display} Risk\n\nGenerating professional DOCX report with detailed findings..."
                                                }
                                                
                                        except Exception as e:
                                            logger.error(f"WAFR_DEBUG: Failed to compress comprehensive assessment: {e}")
                                            tool_result_message = None
                                                                            
                                    elif current_tool_use['name'] == "generate_pricing_calculator_instructions":
                                        # Handle the generate_pricing_calculator_instructions tool result
                                        logger.debug(f"PRICING_DEBUG: Raw MCP tool result: {tool_result}")
                                        
                                        if tool_result.get('content') and len(tool_result['content']) > 0:
                                            content_text = tool_result['content'][0].text
                                            
                                            try:
                                                tool_results_json = json.loads(content_text)
                                                
                                                # Check if we got instructions from the MCP server
                                                if isinstance(tool_results_json, dict) and tool_results_json.get('instructions'):
                                                    instructions = tool_results_json['instructions']
                                                    
                                                    # Store instructions for this message ID
                                                    from ..models.chat import store_pricing_instructions
                                                    
                                                    store_pricing_instructions(user_id, chat_id, self.current_message_id, instructions)
                                                    
                                                    services_count = tool_results_json.get('services_count', 1)
                                                    actions_count = len(instructions.get('actions', []))
                                                    
                                                    tool_result_message = {
                                                        "role": "user",
                                                        "content": [
                                                            {
                                                                "toolResult": {
                                                                    "toolUseId": current_tool_use['toolUseId'],
                                                                    "content": [{
                                                                        "text": f"Service configuration stored. Added {services_count} service(s) with {actions_count} actions."
                                                                    }],
                                                                    "status": "success"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                        
                                            except Exception as e:
                                                logger.error(f"PRICING_DEBUG: Error processing pricing calculator result: {e}")
                                                
                                        if tool_result_message is None:
                                            # Fallback to standard response
                                            actual_content = tool_result['content'][0].text if tool_result.get('content') else "Pricing calculator job started"
                                            tool_result_message = {
                                                "role": "user",
                                                "content": [
                                                    {
                                                        "toolResult": {
                                                            "toolUseId": current_tool_use['toolUseId'],
                                                            "content": [{"text": actual_content}],
                                                            "status": "success"
                                                        }
                                                    }
                                                ]
                                            }
                                    elif current_tool_use['name'] == "create_pricing_calculator_link":
                                        # Handle the create_pricing_calculator_link tool result
                                        logger.debug(f"PRICING_LINK_DEBUG: Raw MCP tool result: {tool_result}")
                                        
                                        if tool_result.get('content') and len(tool_result['content']) > 0:
                                            content_text = tool_result['content'][0].text
                                            
                                            try:
                                                tool_results_json = json.loads(content_text)
                                                
                                                if isinstance(tool_results_json, dict) and tool_results_json.get('job_id'):
                                                    job_id = tool_results_json['job_id']
                                                    
                                                    # Get accumulated instructions from chat
                                                    from ..models.chat import get_pricing_instructions
                                                    accumulated_instructions = get_pricing_instructions(user_id, chat_id, self.current_message_id)
                                                    
                                                    if accumulated_instructions:
                                                        instructions = accumulated_instructions
                                                        
                                                        # Add sharing steps at the end
                                                        sharing_steps = [
                                                            {"act": "Click 'View Summary'"},
                                                            {"act": "Click 'Share' to generate the shareable link"},
                                                            {"act": "Accept terms and conditions if prompted. If not, don't do anything"},
                                                            {"act": "Click 'Copy public link' button"}
                                                        ]
                                                        
                                                        if 'actions' in instructions:
                                                            instructions['actions'].extend(sharing_steps)
                                                        
                                                        # Call Nova ACT API to execute accumulated instructions
                                                        import requests
                                                        try:
                                                            # Log the complete instructions being sent
                                                            logger.info(f"NOVA_INSTRUCTIONS: Sending complete instructions to Nova ACT API:")
                                                            logger.info(f"NOVA_INSTRUCTIONS: Chat ID: {chat_id}")
                                                            logger.info(f"NOVA_INSTRUCTIONS: Total actions: {len(instructions.get('actions', []))}")
                                                            for i, action in enumerate(instructions.get('actions', []), 1):
                                                                logger.info(f"NOVA_INSTRUCTIONS: Action {i}: {action}")
                                                            
                                                            # Forward session cookies for auth + CSRF
                                                            from flask import request as flask_request
                                                            nova_response = requests.post(
                                                                'http://localhost:5001/api/nova/execute',
                                                                json={
                                                                    'chat_id': chat_id,
                                                                    'instructions': instructions
                                                                },
                                                                cookies=flask_request.cookies,
                                                                timeout=10
                                                            )
                                                            
                                                            if nova_response.status_code == 200:
                                                                nova_data = nova_response.json()
                                                                actual_job_id = nova_data.get('job_id', job_id)
                                                                logger.info(f"PRICING_LINK_DEBUG: Started Nova ACT job {actual_job_id}")
                                                                
                                                                tool_result_message = {
                                                                    "role": "user",
                                                                    "content": [
                                                                        {
                                                                            "toolResult": {
                                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                                "content": [{"text": f"Pricing calculator link generation started. Job ID: {actual_job_id}. This will take 2-3 minutes to complete."}],
                                                                                "status": "success"
                                                                            }
                                                                        }
                                                                    ]
                                                                }
                                                            else:
                                                                logger.error(f"Nova ACT API failed: {nova_response.status_code}")
                                                                tool_result_message = {
                                                                    "role": "user",
                                                                    "content": [
                                                                        {
                                                                            "toolResult": {
                                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                                "content": [{"text": f"Failed to start pricing calculator generation. API returned status {nova_response.status_code}"}],
                                                                                "status": "error"
                                                                            }
                                                                        }
                                                                    ]
                                                                }
                                                                
                                                        except Exception as e:
                                                            logger.error(f"Error calling Nova ACT API: {e}")
                                                            tool_result_message = {
                                                                "role": "user",
                                                                "content": [
                                                                    {
                                                                        "toolResult": {
                                                                            "toolUseId": current_tool_use['toolUseId'],
                                                                            "content": [{"text": f"Error starting pricing calculator generation: {str(e)}"}],
                                                                            "status": "error"
                                                                        }
                                                                    }
                                                                ]
                                                            }
                                                    else:
                                                        tool_result_message = {
                                                            "role": "user",
                                                            "content": [
                                                                {
                                                                    "toolResult": {
                                                                        "toolUseId": current_tool_use['toolUseId'],
                                                                        "content": [{"text": "No accumulated pricing instructions found. Please configure services first using generate_pricing_calculator_instructions."}],
                                                                        "status": "error"
                                                                    }
                                                                }
                                                            ]
                                                        }
                                                else:
                                                    tool_result_message = {
                                                        "role": "user",
                                                        "content": [
                                                            {
                                                                "toolResult": {
                                                                    "toolUseId": current_tool_use['toolUseId'],
                                                                    "content": [{"text": "Invalid response from pricing calculator link tool"}],
                                                                    "status": "error"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                    
                                            except json.JSONDecodeError as e:
                                                logger.error(f"PRICING_LINK_DEBUG: Failed to parse JSON: {e}")
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": f"Failed to parse pricing calculator link response: {e}"}],
                                                                "status": "error"
                                                            }
                                                        }
                                                    ]
                                                }
                                        else:
                                            tool_result_message = {
                                                "role": "user",
                                                "content": [
                                                    {
                                                        "toolResult": {
                                                            "toolUseId": current_tool_use['toolUseId'],
                                                            "content": [{"text": "No content returned from pricing calculator link tool"}],
                                                            "status": "error"
                                                        }
                                                    }
                                                ]
                                            }
                                    elif current_tool_use['name'] == "generate_sow_document":
                                        # Handle SOW generation tool result
                                        logger.debug(f"SOW_DEBUG: SOW generation result: {tool_result}")
                                        try:
                                            tool_results_json = json.loads(tool_result['content'][0].text)
                                            
                                            if isinstance(tool_results_json, dict) and tool_results_json.get('s3_url'):
                                                # Store document and get reference
                                                doc_reference = store_document_and_create_reference(
                                                    chat_id, 'sow_document', tool_results_json, 'generate_sow_document'
                                                )
                                                
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": f"Statement of Work generated successfully. {doc_reference}"}],
                                                                "status": "success"
                                                            }
                                                        }
                                                    ]
                                                }
                                                
                                                # Return simple text reference - document will be available in Documents section
                                                yield {
                                                    'type': 'content',
                                                    'content': f" Statement of Work generated successfully. See Documents section below. "
                                                }
                                                
                                                # Store SOW metadata in chat context for SOW review
                                                if tool_results_json.get('status') == 'success':
                                                    from .chat_service import store_sow_metadata_in_chat
                                                    store_sow_metadata_in_chat(chat_id, tool_results_json)
                                                
                                        except Exception as e:
                                            logger.error(f"SOW_DEBUG: Failed to handle SOW tool result: {e}")
                                            # Don't fail the tool result, just log the error

                                    # Handle all document-generating MCP tools with the same pattern
                                    elif current_tool_use['name'] in ["generate_cost_report", "generate_funding_document", "edit_funding_document", "generate_professional_report"]:
                                        tool_name = current_tool_use['name']
                                        logger.debug(f"DOCUMENT_DEBUG: {tool_name} result: {tool_result}")
                                        
                                        # Map tool names to document types and display names
                                        doc_type_map = {
                                            'generate_cost_report': ('pricing_report', 'Cost Analysis Report'),
                                            'generate_funding_document': ('funding_document', 'Funding Document'),
                                            'edit_funding_document': ('funding_document', 'Funding Document'),
                                            'generate_professional_report': ('wafr_assessment', 'WAFR Assessment Report')
                                        }
                                        
                                        try:
                                            tool_results_json = json.loads(tool_result['content'][0].text)
                                            
                                            if isinstance(tool_results_json, dict) and tool_results_json.get('s3_url'):
                                                doc_type, display_name = doc_type_map.get(tool_name, ('document', 'Document'))
                                                
                                                # Store document and get reference (handles DynamoDB storage)
                                                doc_reference = store_document_and_create_reference(
                                                    chat_id, doc_type, tool_results_json, tool_name
                                                )
                                                
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": f"{display_name} generated successfully. {doc_reference}"}],
                                                                "status": "success"
                                                            }
                                                        }
                                                    ]
                                                }
                                                
                                                # Return simple text reference - document will be available in Documents section
                                                # Do NOT expose S3 URLs in chat output
                                                yield {
                                                    'type': 'content',
                                                    'content': f" {display_name} generated successfully. See Documents section below. "
                                                }
                                            else:
                                                # Fallback for non-structured responses
                                                actual_content = tool_result['content'][0].text
                                                tool_result_message = {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "toolResult": {
                                                                "toolUseId": current_tool_use['toolUseId'],
                                                                "content": [{"text": actual_content}],
                                                                "status": "success"
                                                            }
                                                        }
                                                    ]
                                                }
                                        except Exception as e:
                                            logger.error(f"DOCUMENT_DEBUG: Failed to process {tool_name} result: {e}")
                                            tool_result_message = None

                                    elif current_tool_use['name'] == "validate_and_store_cloudformation_templates":
                                        # Handle CloudFormation generation tool result - supports multiple files
                                        logger.debug(f"CFN_DEBUG: CloudFormation generation result: {tool_result}")
                                        try:
                                            # Parse the tool result content (which should be JSON with file metadata)
                                            tool_results_json = json.loads(tool_result['content'][0].text)
                                            logger.debug(f"CFN_DEBUG: parsed result: {tool_results_json}")
                                            
                                            # Check if this is a structured response with file metadata
                                            if isinstance(tool_results_json, dict) and tool_results_json.get('files'):
                                                logger.debug(f"CFN_DEBUG: found structured response with multiple files")
                                                
                                                # Create CloudFormation files dictionary for multiple files
                                                # Use individual keys so Object.values() works in frontend
                                                cfn_files = {}
                                                
                                                # Process each template file
                                                for index, template_file in enumerate(tool_results_json.get('files', [])):
                                                    file_info = {
                                                        "type": "cloudformation_template",
                                                        "name": template_file.get('name'),
                                                        "s3_url": template_file.get('s3_url'),
                                                        "s3_key": template_file.get('s3_key'),
                                                        "version_id": template_file.get('version_id'),
                                                        "file_size": template_file.get('size'),
                                                        "validation_status": template_file.get('validation_status')
                                                    }
                                                    # Use unique keys for each file so Object.values() works
                                                    cfn_files[f"file{index + 1}"] = file_info
                                                    
                                                    # Store each template as a document
                                                    doc_reference = store_document_and_create_reference(
                                                        chat_id, 'cloudformation_template', template_file, 'validate_and_store_cloudformation_templates'
                                                    )
                                                
                                                # Store cfn_files for later streaming (same as diagram_files)
                                                diagram_files = cfn_files
                                                
                                                # Return content with summary of validated templates
                                                template_count = tool_results_json.get('templates_validated', len(cfn_files))
                                                yield {
                                                    'type': 'content',
                                                    'content': f" Validated and stored {template_count} CloudFormation templates "
                                                }
                                                
                                        except Exception as e:
                                            logger.error(f"CFN_DEBUG: Failed to handle CloudFormation tool result: {e}")
                                            # Don't fail the tool result, just log the error

                                    elif current_tool_use['name'] == "generate_cloudformation_from_solution":
                                        # Handle CloudFormation generation from solution - same pattern as validation tool
                                        logger.debug(f"CFN_SOLUTION_DEBUG: CloudFormation solution generation result: {tool_result}")
                                        try:
                                            # Parse the tool result content (which should be JSON with file metadata)
                                            tool_results_json = json.loads(tool_result['content'][0].text)
                                            logger.debug(f"CFN_SOLUTION_DEBUG: parsed result: {tool_results_json}")
                                            
                                            # Check if this is a structured response with file metadata
                                            if isinstance(tool_results_json, dict) and tool_results_json.get('files'):
                                                logger.debug(f"CFN_SOLUTION_DEBUG: found structured response with multiple files")
                                                
                                                # Create CloudFormation files dictionary for multiple files
                                                cfn_files = {}
                                                
                                                # Process each template file
                                                for index, template_file in enumerate(tool_results_json.get('files', [])):
                                                    file_info = {
                                                        "type": "cloudformation_template",
                                                        "name": template_file.get('name'),
                                                        "s3_url": template_file.get('s3_url'),
                                                        "s3_key": template_file.get('s3_key'),
                                                        "version_id": template_file.get('version_id'),
                                                        "file_size": template_file.get('size'),
                                                        "validation_status": template_file.get('validation_status')
                                                    }
                                                    cfn_files[f"file{index + 1}"] = file_info
                                                
                                                # Store cfn_files for later streaming
                                                diagram_files = cfn_files
                                                
                                                # Return content with summary of generated templates
                                                templates_created = tool_results_json.get('templates_created', 0)
                                                services_processed = tool_results_json.get('services_processed', 0)
                                                yield {
                                                    'type': 'content',
                                                    'content': f" Generated {templates_created} of {services_processed} CloudFormation templates from recommended_solution "
                                                }
                                                
                                        except Exception as e:
                                            logger.error(f"CFN_SOLUTION_DEBUG: Failed to handle CloudFormation solution tool result: {e}")
                                            # Don't fail the tool result, just log the error
                                    
                                    if tool_result_message is None:
                                        logger.debug(f"TOOL_RESULT_DEBUG: tool_result_message is None, need to create default")
                                        logger.debug(f"TOOL_RESULT_DEBUG: Current tool name: {current_tool_use['name']}")
                                        logger.debug(f"TOOL_RESULT_DEBUG: Tool result content available: {bool(tool_result.get('content'))}")
                                        
                                        # Handle get_service_definition - replace previous result with placeholder to prevent context growth
                                        if current_tool_use['name'] == "get_service_definition":
                                            # Replace the previous service definition result with a minimal placeholder
                                            if hasattr(self, 'last_service_def_tool_id') and self.last_service_def_tool_id:
                                                for msg in conversation_messages:
                                                    if (msg.get('content', [{}])[0].get('toolResult', {}).get('toolUseId') == self.last_service_def_tool_id):
                                                        # Replace with minimal placeholder
                                                        msg['content'] = [{
                                                            "toolResult": {
                                                                "toolUseId": self.last_service_def_tool_id,
                                                                "content": [{"text": "Service definitions retrieved (content replaced to save tokens)"}],
                                                                "status": "success"
                                                            }
                                                        }]
                                                        logger.debug(f"Replaced previous service definition result with placeholder: {self.last_service_def_tool_id}")
                                                        break
                                            
                                            # Store this tool use ID for next time
                                            self.last_service_def_tool_id = current_tool_use['toolUseId']
                                        
                                        # For funding wizard and other tools, use the actual tool result content
                                        if current_tool_use['name'] == 'get_funding_eligibility' or tool_result.get('content'):
                                            if isinstance(tool_result.get('content'), list) and len(tool_result['content']) > 0:
                                                content_item = tool_result['content'][0]
                                                if hasattr(content_item, 'text'):
                                                    actual_content = content_item.text
                                                    
                                                    logger.debug(f"TOOL_RESULT_DEBUG: Using actual tool content: length={len(actual_content)}")
                                                    tool_result_message = {
                                                        "role": "user",
                                                        "content": [
                                                            {
                                                                "toolResult": {
                                                                    "toolUseId": current_tool_use['toolUseId'],
                                                                    "content": [{"text": actual_content}],
                                                                    "status": "success"
                                                                }
                                                            }
                                                        ]
                                                    }
                                        
                                        # Fallback to generic message if no content available
                                        if tool_result_message is None:
                                            tool_result_message = {
                                                "role": "user",
                                                "content": [
                                                    {
                                                        "toolResult": {
                                                            "toolUseId": current_tool_use['toolUseId'],
                                                            "content": [{"text": "Tool execution completed successfully."}],                                                    
                                                            "status": "success"
                                                        }
                                                    }
                                                ]
                                            }
                                
                                    # Yield the tool result
                                    yield {
                                        'type': 'tool_result',
                                        'content': f"Tool {current_tool_use['name']} executed successfully"
                                    }
                                
                                # Add the tool result message to the conversation
                                conversation_messages.append(tool_result_message)
                                
                                logger.debug(f"Added tool result to conversation for toolUseId: {current_tool_use['toolUseId']}")
                                logger.debug(f"Conversation now has {len(conversation_messages)} messages")                               
                                
                                
                                # Continue the conversation with all messages
                                continuation_params = request_params.copy()
                                continuation_params["messages"] = conversation_messages
                                
                                # Analyze conversation growth for token debugging
                                original_msg_count = len(request_params.get('messages', []))
                                continuation_msg_count = len(conversation_messages)
                                msg_growth = continuation_msg_count - original_msg_count
                                
                                # Estimate token growth
                                continuation_length = sum(len(str(msg.get('content', ''))) for msg in conversation_messages)
                                estimated_continuation_tokens = continuation_length // 4
                                
                                logger.debug(f"CONVERSATION_CONTINUATION_ANALYSIS:")
                                logger.debug(f"  Original messages: {original_msg_count}")
                                logger.debug(f"  Continuation messages: {continuation_msg_count} (+{msg_growth} new)")
                                logger.debug(f"  Estimated continuation tokens: ~{estimated_continuation_tokens}")
                                
                                if estimated_continuation_tokens > 150000:
                                    logger.error(f"  CRITICAL: Continuation approaching token limits!")
                                elif estimated_continuation_tokens > 100000:
                                    logger.warning(f"  HIGH: Continuation tokens very high")
                                
                                logger.debug(f"Continuing conversation with {len(conversation_messages)} messages")
                                
                                # Check if we should actually continue (avoid infinite recursion)
                                max_tool_cycles = 50  # Increased for CloudFormation template generation workflows
                                # Count tool use cycles (assistant messages that contain tool calls)
                                tool_cycle_count = len([msg for msg in conversation_messages 
                                                       if msg['role'] == 'assistant' and 
                                                       any(content.get('toolUse') for content in msg.get('content', []))])
                                current_depth = tool_cycle_count
                                
                                if current_depth >= max_tool_cycles:
                                    logger.warning(f"Reached maximum tool cycles {max_tool_cycles}, stopping recursion")
                                    yield {
                                        'type': 'info',
                                        'content': f"Tool execution completed. Conversation depth limit reached."
                                    }
                                    return
                                
                                # Recursively process the continuation with simple retry
                                retry_count = 0
                                while retry_count <= max_retries:
                                    try:
                                        # Recursively process the continuation
                                        logger.debug(f"Recursively process the continuation...")
                                        for chunk in self._process_streaming_conversation(continuation_params, chat_id, user_id):
                                            yield chunk
                                        
                                        # If successful, break out of the retry loop
                                        break
                                    except ClientError as e:
                                        error_code = e.response.get('Error', {}).get('Code', '')
                                        error_message = e.response.get('Error', {}).get('Message', '')
                                        
                                        # Check if this is a throttling error
                                        if error_code == 'ThrottlingException':
                                            retry_count += 1
                                            
                                            logger.error(f"Bedrock throttling error in continuation (attempt {retry_count}/{max_retries}): {error_message}")
                                            
                                            # If we've reached the maximum number of retries, stop
                                            if retry_count > max_retries:
                                                logger.error(f"Maximum retries ({max_retries}) exceeded for continuation throttling error")
                                                yield {
                                                    'type': 'error',
                                                    'content': f"Bedrock API throttling error: Maximum retries exceeded. {error_message}"
                                                }
                                                return
                                            
                                            # Send a random thinking message and wait
                                            thinking_message = random.choice(FRIENDLY_WAITING_MESSAGES) #nosemgrep No cryptography - generates random user experience messages for throttling or rate limiting scenarios in Bedrock # nosec B311 - Using random for UI message selection, not cryptographic purposes
                                            logger.debug(f"Showing thinking message during continuation: {thinking_message}")
                                            yield {
                                                'type': 'info',
                                                'content': f"\n{thinking_message}..."
                                            }
                                            
                                            # Wait for the configured delay
                                            time.sleep(throttle_delay)
                                            continue
                                        else:
                                            # For non-throttling errors, log and return
                                            logger.error(f"Error in continuation: {e}")
                                            yield {
                                                'type': 'error',
                                                'content': f"Error in continuation: {str(e)}"
                                            }
                                            return
                                    except Exception as e:
                                        logger.error(f"Error in continuation: {e}")
                                        yield {
                                            'type': 'error',
                                            'content': f"Error in continuation: {str(e)}"
                                        }
                                        return
                                
                                # Return after handling the tool use to avoid further processing
                                return
                                
                            else:
                                logger.error("MCP manager not available")
                                yield {
                                    'type': 'error',
                                    'content': "MCP manager not available"
                                }
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing tool input JSON: {e}")
                            yield {
                                'type': 'error',
                                'content': f"Error parsing tool input: {str(e)}"
                            }
                        except Exception as e:
                            logger.error(f"Error executing tool: {e}")
                            yield {
                                'type': 'error',
                                'content': f"Error executing tool: {str(e)}"
                            }
                    else:
                        # For any other stop reason, yield the stop event with citations
                        stop_response = {
                            'type': 'stop',
                            'stop_reason': stop_reason,
                            'content': accumulated_text
                        }
                        
                        # Include citations if any were found (not applicable for Claude models)
                        if accumulated_citations:
                            logger.warning(f"CITATION_UNEXPECTED: Claude model returned {len(accumulated_citations)} citations, which should not happen")
                            # Don't include citations in response for Claude models
                        
                        yield stop_response
                        
                # Handle metadata (usage, etc.)
                elif 'metadata' in event:
                    usage = event['metadata'].get('usage', {})
                    logger.debug(f"Metadata: input_tokens={usage.get('inputTokens', 'N/A')}, output_tokens={usage.get('outputTokens', 'N/A')}")
                    
                    # Log token usage to S3 for auditing
                    if self.token_usage_logger and usage and user_id:
                        input_tokens = usage.get('inputTokens', 0)
                        output_tokens = usage.get('outputTokens', 0)
                        self.token_usage_logger.log_usage(
                            user_id=user_id,
                            chat_id=chat_id,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            model_id=self.model_id
                        )
                    
                    yield {
                        'type': 'metadata',
                        'usage': usage
                    }
                    
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock API error: {error_code} - {error_message}")
            yield {
                'type': 'error',
                'content': f"Bedrock API error: {error_message}"
            }
        except Exception as e:
            logger.error(f"Error processing streaming response: {e}")
            yield {
                'type': 'error',
                'content': f"An error occurred while processing the response: {str(e)}"
            }
    
    # Alias for backward compatibility
    def send_message(self, messages, chat_id, user_id=None, system_prompt=None, guardrail_id=None, guardrail_version=None, tools=None, prompt_variables=None, file_metadata=None, assistant_persona=None):
        """Alias for send_message_stream for backward compatibility."""
        return self.send_message_stream(messages, chat_id, user_id, system_prompt, guardrail_id, guardrail_version, tools, prompt_variables, file_metadata, assistant_persona)
    # ========================================
    # WAFR-SPECIFIC ENHANCEMENTS
    # ========================================
    
    async def wafr_generate_report_content(
        self,
        chat_id: str,
        assessment_results: dict,
        architecture_data: dict
    ) -> dict:
        """
        Generate ENHANCED report content using the SAME data from chat.
        
        CRITICAL: This uses the EXACT SAME assessment_results that generated
        the chat response, ensuring perfect alignment.
        
        Args:
            chat_id: Chat session ID
            assessment_results: Complete assessment data (same as used for chat)
            architecture_data: Architecture data from document analysis
            
        Returns:
            Enhanced report content result
        """
        try:
            logger.info(f"🎨 Generating enhanced WAFR report content for chat_id: {chat_id}")
            
            # Build comprehensive report generation prompt
            system_prompt = self._build_wafr_report_enhancement_prompt()
            
            # Use the SAME assessment data that created the chat response
            user_message = self._build_report_enhancement_message(
                assessment_results=assessment_results,  # SAME data as chat
                architecture_data=architecture_data,    # SAME data as chat
                chat_response=assessment_results.get("chat_response", "")  # Include chat for alignment
            )
            
            # Prepare message for Bedrock
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_message
                        }
                    ]
                }
            ]
            
            # Single Claude call to enhance the existing assessment data
            logger.info("🤖 Calling Claude for report content enhancement...")
            
            # Log message size for debugging
            message_size = len(user_message)
            system_size = len(system_prompt)
            logger.debug(f"CONTENT_ENHANCEMENT: Message size: {message_size} chars, System prompt size: {system_size} chars")
            
            # Validate message content before sending
            if message_size > 100000:  # 100KB limit
                logger.warning(f"CONTENT_ENHANCEMENT: Large message size ({message_size} chars) - truncating")
                user_message = user_message[:50000] + "\n\n[Message truncated for processing]"
            
            # Use the existing send_message_stream method with same parameters as successful chat calls
            response_generator = self.send_message_stream(
                messages=messages,
                chat_id=chat_id,  # Use original chat_id, not modified
                user_id=None,     # Use None instead of "wafr-system" 
                system_prompt=system_prompt,
                tools=None  # No tools needed for content generation
            )
            
            # Collect the streaming response
            full_response = ""
            for chunk in response_generator:
                if chunk.get('type') == 'content':
                    full_response += chunk.get('content', '')
                elif chunk.get('type') == 'error':
                    raise Exception(f"Bedrock error: {chunk.get('content')}")
            
            # Parse the enhanced content response
            enhanced_content = self._parse_report_enhancement_response(full_response)
            
            logger.info("✅ WAFR report content enhancement completed successfully")
            
            return {
                "status": "success",
                "enhanced_content": enhanced_content,
                "business_impact": enhanced_content.get("expected_benefits", {}),
                "implementation_roadmap": enhanced_content.get("implementation_plan", {}),
                "correlation_id": f"wafr-report-enhancement-{chat_id}",
                "processing_metadata": {
                    "enhancement_method": "claude_bedrock",
                    "content_sections": list(enhanced_content.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ WAFR report content enhancement failed: {error_msg}")
            
            # Log additional debug info for parameter validation errors
            if "Parameter validation failed" in error_msg:
                logger.error(f"PARAMETER_VALIDATION_ERROR: System prompt length: {len(system_prompt) if 'system_prompt' in locals() else 'unknown'}")
                logger.error(f"PARAMETER_VALIDATION_ERROR: User message length: {len(user_message) if 'user_message' in locals() else 'unknown'}")
                logger.error(f"PARAMETER_VALIDATION_ERROR: Messages count: {len(messages) if 'messages' in locals() else 'unknown'}")
                
                # Log first 500 chars of user message to identify problematic content
                if 'user_message' in locals():
                    logger.error(f"PARAMETER_VALIDATION_ERROR: User message preview: {user_message[:500]}...")
                
                # Log system prompt preview
                if 'system_prompt' in locals():
                    logger.error(f"PARAMETER_VALIDATION_ERROR: System prompt preview: {system_prompt[:200]}...")
            
            return {
                "status": "error",
                "error": error_msg,
                "fallback_content": self._generate_fallback_report_content(assessment_results, architecture_data)
            }
    
    def _build_wafr_report_enhancement_prompt(self) -> str:
        """Build report enhancement prompt that preserves chat accuracy."""
        return """You are an AWS Well-Architected Framework expert specializing in professional report generation.

Your task: Enhance existing WAFR assessment data into comprehensive professional report content.

REQUIREMENTS:
- Keep all pillar scores EXACTLY as provided
- Maintain all identified services and architectural patterns  
- Preserve risk levels and priority classifications
- Add executive summary with business impact quantification
- Expand recommendations with implementation timelines
- Include cost savings estimates and operational improvements

OUTPUT FORMAT (JSON):
{
  "executive_summary": "Professional executive summary with business impact",
  "architecture_overview": "Enhanced architecture description with patterns",
  "pillar_detailed_analysis": {
    "operational_excellence": {
      "enhanced_findings": "Detailed professional analysis",
      "business_impact": "Quantified operational improvements"
    }
  },
  "risk_analysis": {
    "critical_risks": ["High-priority risks with mitigation strategies"],
    "medium_risks": ["Medium-priority risks"]
  },
  "expected_benefits": {
    "cost_savings": "Specific savings estimates",
    "performance_improvements": "Performance improvement metrics",
    "security_enhancements": "Security improvement metrics",
    "operational_efficiency": "Efficiency gains"
  },
  "implementation_plan": {
    "quick_wins_0_30_days": ["Immediate high-impact actions"],
    "strategic_improvements_1_3_months": ["Medium-term initiatives"],
    "transformation_3_12_months": ["Long-term architectural evolution"]
  }
}

Preserve all original assessment data and scores while enhancing content quality."""

    def _build_report_enhancement_message(
        self,
        assessment_results: dict,
        architecture_data: dict,
        chat_response: str
    ) -> str:
        """Build user message for report enhancement."""
        
        # Extract key data from assessment results
        pillar_assessments = assessment_results.get("pillar_assessments", {})
        overall_score = assessment_results.get("overall_score", 0)
        overall_risk_level = assessment_results.get("overall_risk_level", "unknown")
        
        # Extract architecture information
        architecture_type = architecture_data.get("architecture_type", "Architecture") if architecture_data else "Architecture"
        identified_services = architecture_data.get("identified_services", []) if architecture_data else []
        architectural_patterns = architecture_data.get("architectural_patterns", []) if architecture_data else []
        
        message = f"""Enhance this WAFR assessment data for professional report generation:

ASSESSMENT OVERVIEW:
- Overall Score: {overall_score:.1f}%
- Risk Level: {overall_risk_level}
- Architecture Type: {architecture_type}
- Identified Services: {', '.join(identified_services) if identified_services else 'None specified'}
- Architectural Patterns: {', '.join([p.get('pattern_type', str(p)) if isinstance(p, dict) else str(p) for p in architectural_patterns]) if architectural_patterns else 'None detected'}

PILLAR ASSESSMENT RESULTS:
"""
        
        # Add pillar details
        for pillar, data in pillar_assessments.items():
            pillar_name = pillar.replace("_", " ").title()
            score = data.get("score", 0)
            risk_level = data.get("risk_level", "unknown")
            recommendations = data.get("recommendations", [])
            
            message += f"""
{pillar_name}:
- Score: {score:.1f}%
- Risk Level: {risk_level}
- Key Recommendations: {len(recommendations)} items
"""
            
            # Add top recommendations
            if recommendations:
                for i, rec in enumerate(recommendations[:3], 1):
                    if isinstance(rec, dict):
                        rec_text = rec.get("description", str(rec))
                    else:
                        rec_text = str(rec)
                    message += f"  {i}. {rec_text}\n"
        
        # Add cleaned chat response for alignment reference
        if chat_response:
            # Clean chat response to remove problematic characters
            clean_chat_response = self._clean_text_for_bedrock(chat_response)
            # Limit chat response length to prevent oversized messages
            if len(clean_chat_response) > 2000:
                clean_chat_response = clean_chat_response[:2000] + "...[truncated]"
            
            message += f"""
CHAT RESPONSE (for alignment reference):
{clean_chat_response}

ENHANCEMENT REQUEST:
Please enhance this assessment data into comprehensive professional report content. 
Preserve all scores and core findings while adding business impact, detailed analysis, 
and implementation guidance. Return the enhanced content in the specified JSON format.
"""
        else:
            message += """
ENHANCEMENT REQUEST:
Please enhance this assessment data into comprehensive professional report content. 
Preserve all scores and core findings while adding business impact, detailed analysis, 
and implementation guidance. Return the enhanced content in the specified JSON format.
"""
        
        return message
    
    def _clean_text_for_bedrock(self, text: str) -> str:
        """Clean text to remove characters that might cause Bedrock parameter validation errors."""
        if not text:
            return ""
        
        # Remove emojis and special Unicode characters
        import re
        # Remove emojis (most common ranges)
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   u"\U00002702-\U000027B0"  # dingbats
                                   u"\U000024C2-\U0001F251"
                                   "]+", flags=re.UNICODE)
        
        cleaned = emoji_pattern.sub('', text)
        
        # Remove excessive markdown formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Remove bold
        cleaned = re.sub(r'##\s*', '', cleaned)  # Remove headers
        cleaned = re.sub(r'###\s*', '', cleaned)  # Remove subheaders
        
        # Replace escaped newlines with actual newlines
        cleaned = cleaned.replace('\\n', '\n')
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 consecutive newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Multiple spaces to single space
        
        return cleaned.strip()
    
    def _parse_report_enhancement_response(self, response_text: str) -> dict:
        """Parse Claude's report enhancement response."""
        try:
            # Clean up response text
            clean_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            enhanced_content = json.loads(clean_text)
            
            logger.info("✅ Successfully parsed enhanced report content")
            return enhanced_content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse enhanced content as JSON: {e}")
            logger.debug(f"Raw response: length={len(response_text)}")
            
            # Return structured fallback
            return {
                "executive_summary": "Enhanced WAFR assessment completed with detailed findings and recommendations.",
                "architecture_overview": "Architecture analysis completed with service identification and pattern recognition.",
                "pillar_detailed_analysis": {},
                "risk_analysis": {
                    "critical_risks": ["Assessment data parsing error - manual review recommended"],
                    "medium_risks": [],
                    "risk_mitigation_timeline": "Immediate review required"
                },
                "expected_benefits": {
                    "cost_savings": "Benefits analysis requires manual review",
                    "performance_improvements": "Performance analysis requires manual review",
                    "security_enhancements": "Security analysis requires manual review",
                    "operational_efficiency": "Operational analysis requires manual review"
                },
                "implementation_plan": {
                    "quick_wins_0_30_days": ["Review assessment data and recommendations"],
                    "strategic_improvements_1_3_months": ["Implement validated recommendations"],
                    "transformation_3_12_months": ["Execute long-term optimization plan"]
                },
                "parsing_error": str(e),
                "raw_response_preview": response_text[:1000] if response_text else "No response received"
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing enhanced content: {e}")
            return self._generate_fallback_report_content({}, {})
    
    def _generate_fallback_report_content(self, assessment_results: dict, architecture_data: dict) -> dict:
        """Generate fallback report content when Claude enhancement fails."""
        
        pillar_assessments = assessment_results.get("pillar_assessments", {})
        overall_score = assessment_results.get("overall_score", 0)
        architecture_type = architecture_data.get("architecture_type", "Architecture") if architecture_data else "Architecture"
        
        return {
            "executive_summary": f"WAFR assessment completed for {architecture_type} with overall score of {overall_score:.1f}%. Detailed findings and recommendations are available in the pillar-specific sections.",
            "architecture_overview": f"The assessed {architecture_type} demonstrates various AWS services and architectural patterns. Detailed analysis is available in the comprehensive assessment data.",
            "pillar_detailed_analysis": {
                pillar: {
                    "enhanced_findings": f"{pillar.replace('_', ' ').title()} assessment completed with score of {data.get('score', 0):.1f}%",
                    "business_impact": "Business impact analysis requires manual review",
                    "implementation_roadmap": {
                        "phase_1_0_30_days": ["Review pillar-specific recommendations"],
                        "phase_2_1_3_months": ["Implement priority improvements"],
                        "phase_3_3_12_months": ["Execute comprehensive optimization plan"]
                    }
                }
                for pillar, data in pillar_assessments.items()
            },
            "risk_analysis": {
                "critical_risks": ["Manual review of assessment data recommended"],
                "medium_risks": ["Validate all pillar recommendations"],
                "risk_mitigation_timeline": "Immediate to 12 months based on priority"
            },
            "expected_benefits": {
                "cost_savings": "Cost optimization opportunities identified - quantification requires detailed analysis",
                "performance_improvements": "Performance enhancement opportunities available",
                "security_enhancements": "Security improvements recommended based on assessment",
                "operational_efficiency": "Operational optimization opportunities identified"
            },
            "implementation_plan": {
                "quick_wins_0_30_days": ["Review all assessment recommendations", "Prioritize high-impact, low-effort improvements"],
                "strategic_improvements_1_3_months": ["Implement validated recommendations", "Monitor improvement metrics"],
                "transformation_3_12_months": ["Execute comprehensive optimization strategy", "Conduct follow-up assessment"]
            },
            "fallback_mode": True,
            "enhancement_status": "Manual enhancement recommended for optimal results"
        }