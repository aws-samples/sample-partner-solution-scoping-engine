"""
Message processing utilities for different personas.
Handles message formatting before storage in DynamoDB.
"""
import logging
import re

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Centralized message processing for different personas."""
    
    @classmethod
    def process_user_message_with_files(cls, message, intent, processed_files, file_metadata, assistant_persona_id):
        """
        Process user message with files based on assistant persona.
        
        Args:
            message (str): Original user message
            intent (str): Message intent (e.g., 'poc_funding_review')
            processed_files (list): List of processed file metadata
            file_metadata (dict): File classification metadata
            assistant_persona_id (str): Assistant persona identifier
            
        Returns:
            str: Enhanced message formatted for the specific persona
        """
        if not processed_files:
            return message
        
        # Get persona-specific enhancer
        enhancer = cls._get_persona_enhancer(assistant_persona_id)
        
        # Process message with the appropriate enhancer
        enhanced_message = enhancer.enhance_message(message, intent, processed_files, file_metadata)
        
        logger.info(f"MESSAGE_PROCESSOR: Enhanced message for persona '{assistant_persona_id}' (intent: {intent})")
        return enhanced_message
    
    @classmethod
    def _get_persona_enhancer(cls, assistant_persona_id):
        """Get the appropriate message enhancer for the persona."""
        enhancers = {
            'apn_funding_assistant': APNFundingEnhancer(),
            'aws_solutions_assistant': AWSSolutionsEnhancer(),
            'aws_well_architected_framework_assistant': WAFREnhancer(),
        }
        
        return enhancers.get(assistant_persona_id, DefaultEnhancer())


class BaseMessageEnhancer:
    """Base class for persona-specific message enhancement."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance the message based on persona-specific logic."""
        return message
    
    def _create_file_links(self, processed_files):
        """Create file links from processed files metadata."""
        file_links = []
        
        for file_info in processed_files:
            display_filename = file_info.get('original_display_filename') or file_info.get('original_filename')
            s3_url = file_info.get('s3_url')
            version_id = file_info.get('version_id')
            
            if display_filename and s3_url:
                # Check if this is an image file for inline display
                file_extension = display_filename.split('.')[-1].lower() if '.' in display_filename else ''
                image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']
                
                if file_extension in image_extensions:
                    file_link = f"![{display_filename}]({s3_url}?versionId={version_id})"
                else:
                    file_link = f"[{display_filename}]({s3_url}?versionId={version_id})"
                
                file_links.append(file_link)
        
        return file_links


class APNFundingEnhancer(BaseMessageEnhancer):
    """Message enhancer for APN Funding Assistant persona."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message with POC funding document structure."""
        if intent != 'poc_funding_review':
            return self._enhance_general_message(message, processed_files)
            
        if not file_metadata or not processed_files:
            logger.warning(f"POC_FUNDING_WARNING: POC funding intent received but no file metadata or processed files")
            return message + f"\n\nThis is a POC funding analysis request. Please upload the required documents if you haven't already."
        
        logger.info(f"POC_FILE_METADATA: Creating enhanced message with frontend classifications for MCP tool")
        
        # Create a mapping of filename to S3 URL from processed_files
        classified_files = {}
        
        for file_info in processed_files:
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
        
        logger.info(f"POC_FILE_METADATA: Using frontend classifications - Classified files: {list(classified_files.keys())}")
        
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
    
    def _enhance_general_message(self, message, processed_files):
        """Enhance general (non-POC) messages with file information."""
        if not processed_files:
            return message
        
        file_links = self._create_file_links(processed_files)
        
        if file_links:
            file_count = len(processed_files)
            file_list = ", ".join(file_links)
            upload_message = f"📎 Uploaded {file_count} file(s): {file_list}"
            
            if message and message.strip():
                return f"{message}\n\n{upload_message}"
            else:
                return upload_message
        
        return message


class AWSSolutionsEnhancer(BaseMessageEnhancer):
    """Message enhancer for AWS Solutions Assistant persona."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message for AWS Solutions Assistant with clean file presentation."""
        if not processed_files:
            return message
        
        file_links = self._create_file_links(processed_files)
        
        if file_links:
            file_count = len(processed_files)
            
            # Create a clean, professional file list
            enhanced_message = message if message and message.strip() else "I have uploaded files for analysis."
            enhanced_message += f"\n\n**Uploaded Files ({file_count}):**\n"
            
            for i, file_link in enumerate(file_links, 1):
                enhanced_message += f"{i}. {file_link}\n"
        
        return enhanced_message


class WAFREnhancer(BaseMessageEnhancer):
    """Message enhancer for AWS Well-Architected Framework Assistant persona."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message with WAFR document structure (clean user-facing content only)."""
        # Even if no files in THIS message, add instruction to check for existing documents
        if not processed_files:
            # Check if this looks like a WAFR assessment request
            message_lower = message.lower() if message else ""
            wafr_keywords = ['wafr', 'well-architected', 'assessment', 'analyze', 'review', 'pillar']
            if any(keyword in message_lower for keyword in wafr_keywords):
                logger.info("WAFR_FILE_METADATA: WAFR request detected without files - adding auto-fetch instruction")
                # Add instruction to use auto-fetch capability
                enhanced_message = message + "\n\n**Note:** If documents were previously uploaded in this chat, use analyze_architecture_documents with the chat_id to auto-fetch them."
                return enhanced_message
            return message
            
        logger.info("WAFR_FILE_METADATA: Creating enhanced message for WAFR analysis")
        
        # Create clean user-facing message with file links (no hidden metadata)
        file_links = self._create_file_links(processed_files)
        
        if file_links:
            # Enhanced message with clean user-facing content only
            if not message.strip():
                enhanced_message = "Please perform a comprehensive WAFR assessment of the uploaded architecture documents."
            else:
                enhanced_message = message
            
            # Add clean file presentation
            file_count = len(processed_files)
            enhanced_message += f"\n\n**Architecture Documents ({file_count}):**\n"
            
            for i, file_link in enumerate(file_links, 1):
                enhanced_message += f"{i}. {file_link}\n"
            
            logger.info(f"WAFR_FILE_METADATA: Enhanced message with {len(processed_files)} document links")
            return enhanced_message
        
        return message


class DefaultEnhancer(BaseMessageEnhancer):
    """Default message enhancer for other personas."""
    
    def enhance_message(self, message, intent, processed_files, file_metadata):
        """Enhance message with simple file list."""
        if not processed_files:
            return message
        
        file_links = self._create_file_links(processed_files)
        
        if file_links:
            file_count = len(processed_files)
            file_list = ", ".join(file_links)
            upload_message = f"📎 Uploaded {file_count} file(s): {file_list}"
            
            if message and message.strip():
                return f"{message}\n\n{upload_message}"
            else:
                return upload_message
        
        return message