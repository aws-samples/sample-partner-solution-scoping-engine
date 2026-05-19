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

import os
import boto3
import logging
import datetime
from datetime import UTC
from botocore.exceptions import ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from ..config.app_config import CustomerConfig

# Configure logging
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    A class for processing documents, including uploading to S3 and generating signed URLs.
    """
    
    @classmethod
    def sanitize_filename_for_bedrock(cls, filename):
        """
        Sanitize filename to meet Bedrock's document naming requirements for Converse Stream API.
        
        Bedrock document naming requirements:
        - Only alphanumeric characters, whitespace, hyphens, parentheses, square brackets allowed
        - No consecutive whitespace characters allowed
        - Must be suitable for all document types (PDF, DOCX, XLSX, PPTX, RTF, TXT, etc.)
        - Remove file extension to present just the base name
        
        Args:
            filename (str): Original filename to sanitize
            
        Returns:
            str: Sanitized filename without extension that meets Bedrock requirements
        """
        import re
        import os
        
        if not filename:
            return "document"
        
        # Remove file extension - get just the base name
        base_name = os.path.splitext(filename)[0]
        
        # Only allow alphanumeric, whitespace, hyphens, parentheses, square brackets
        # Replace any other characters with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '_', base_name)
        
        # Remove multiple consecutive whitespace and replace with single space
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Ensure we have a valid filename (not empty after sanitization)
        if not sanitized or sanitized.isspace():
            sanitized = "document"
            
        logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}' (extension removed)")
        return sanitized
    
    @classmethod
    def format_file_for_bedrock(cls, file_obj):
        """
        Format a file object for Bedrock ContentBlock format.
        
        Args:
            file_obj (dict): File object with keys: name, content, content_type, size, too_large
            
        Returns:
            dict or None: ContentBlock formatted for Bedrock, or None if file should be skipped
        """
        import base64
        
        file_name = file_obj.get('name', 'Unknown')
        file_content = file_obj.get('content', b'')
        content_type = file_obj.get('content_type', 'application/octet-stream')
        file_size = file_obj.get('size', 0)
        too_large = file_obj.get('too_large', False)
        
        logger.debug(f"Formatting file for Bedrock: {file_name}, content_type: {content_type}, size: {file_size}, too_large: {too_large}")
        
        # Skip files that are too large for Bedrock
        if too_large:
            file_size_mb = file_size / (1024 * 1024)
            logger.debug(f"Skipped large file {file_name} for Bedrock processing")
            return {
                "text": f"\n[File {file_name} ({file_size_mb:.2f}MB) was uploaded to the chat but is too large to process directly. The file has been saved and can be downloaded later. Please let me know if you have questions about this file.]"
            }
        
        # Handle different file types for Bedrock ContentBlock format
        if content_type.startswith('image/'):
            return cls._format_image_for_bedrock(file_name, file_content, content_type)
        elif content_type == 'application/pdf':
            return cls._format_document_for_bedrock(file_name, file_content, 'PDF')
        elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            return cls._format_document_for_bedrock(file_name, file_content, 'DOCX/DOC')
        elif content_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
            return cls._format_document_for_bedrock(file_name, file_content, 'XLSX/XLS')
        elif content_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint']:
            return cls._format_document_for_bedrock(file_name, file_content, 'PPTX/PPT')
        elif content_type in ['application/rtf', 'text/rtf']:
            return cls._format_document_for_bedrock(file_name, file_content, 'RTF')
        elif (content_type.startswith('text/') or 
              content_type in ['text/plain', 'text/csv', 'text/markdown', 'application/json'] or
              (content_type == 'application/octet-stream' and 
               file_name.lower().endswith(('.md', '.txt', '.csv', '.json')))):
            return cls._format_document_for_bedrock(file_name, file_content, 'text')
        else:
            # For other file types, add as text description
            file_size_mb = len(file_content) / (1024 * 1024)
            logger.debug(f"Added file description for {file_name} to Bedrock message")
            return {
                "text": f"\n[Attached file: {file_name} ({content_type}, {file_size_mb:.2f}MB)]\nNote: This file type cannot be directly processed, but I can help you with questions about it."
            }
    
    @classmethod
    def _format_image_for_bedrock(cls, file_name, file_content, content_type):
        """
        Format an image file for Bedrock image ContentBlock.
        
        Args:
            file_name (str): Name of the file
            file_content (bytes): File content
            content_type (str): MIME type of the file
            
        Returns:
            dict or None: Image ContentBlock or None if encoding fails
        """
        import base64
        
        try:
            # Validate file content
            if not file_content or len(file_content) == 0:
                logger.error(f"Empty file content for {file_name}")
                return None
            
            # Map content type to Bedrock format
            format_map = {
                'image/jpeg': 'jpeg',
                'image/jpg': 'jpeg', 
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp'
            }
            bedrock_format = format_map.get(content_type.lower(), 'jpeg')
            
            logger.debug(f"Successfully prepared image {file_name} ({bedrock_format}): {len(file_content)} bytes")
            return {
                "image": {
                    "format": bedrock_format,
                    "source": {
                        "bytes": file_content  # Raw bytes - let Boto3 handle base64 encoding
                    }
                }
            }
        except Exception as e:
            logger.error(f"Failed to base64 encode image {file_name}: {e}")
            return None
    
    @classmethod
    def _format_document_for_bedrock(cls, file_name, file_content, doc_type):
        """
        Format a document file for Bedrock document ContentBlock with citations enabled.
        
        Args:
            file_name (str): Name of the file
            file_content (bytes): File content
            doc_type (str): Type of document for logging (PDF, DOCX, etc.)
            
        Returns:
            dict or None: Document ContentBlock or None if encoding fails
        """
        import base64
        
        try:
            # Validate file content
            if not file_content or len(file_content) == 0:
                logger.error(f"Empty file content for {file_name}")
                return None
            
            # Sanitize filename for Bedrock
            sanitized_name = cls.sanitize_filename_for_bedrock(file_name)
            logger.debug(f"Sanitized filename for Bedrock: '{file_name}' -> '{sanitized_name}'")
            
            # Map document types to Bedrock format values
            format_map = {
                'PDF': 'pdf',
                'DOCX/DOC': 'docx',
                'XLSX/XLS': 'xlsx', 
                'PPTX/PPT': 'pptx',
                'RTF': 'rtf',
                'text': 'txt'
            }
            bedrock_format = format_map.get(doc_type, 'txt')  # Default to txt for unknown types
            
            # Check if citations are enabled in configuration
            citations_enabled = CustomerConfig.get_value('BEDROCK_CITATIONS_ENABLED', False)
            
            # Create document block with raw bytes (Boto3 will handle base64 encoding)
            document_block = {
                "document": {
                    "name": sanitized_name,
                    "format": bedrock_format,
                    "source": {
                        "bytes": file_content  # Raw bytes - let Boto3 handle base64 encoding
                    }
                }
            }
            
            logger.debug(f"Successfully prepared {doc_type} {file_name}: {len(file_content)} bytes")
            
            # Add citations configuration if enabled
            if citations_enabled:
                document_block["document"]["citations"] = {
                    "enabled": True
                }
                document_block["document"]["context"] = f"This is a {doc_type} document titled '{file_name}'. When referencing information from this document in your response, please cite it appropriately. The document contains relevant information that should be used to inform your answers."
                logger.debug(f"Citations enabled for document {sanitized_name}")
            else:
                logger.debug(f"Citations disabled for document {sanitized_name}")
            
            logger.debug(f"Added {doc_type} document {sanitized_name} to Bedrock message with format: {bedrock_format} and citations enabled")
            return document_block
            
        except Exception as e:
            logger.error(f"Failed to base64 encode {doc_type} {file_name}: {e}")
            return None
    
    @classmethod
    def normalize_filename_for_classification(cls, filename):
        """
        Normalize filename for consistent classification mapping.
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Normalized filename using secure_filename transformation
        """
        from werkzeug.utils import secure_filename
        return secure_filename(filename)

    @classmethod
    def sanitize_s3_tag_value(cls, value):
        """
        Sanitize tag value for S3 compatibility.
        
        AWS S3 tag values can contain: letters, numbers, spaces, and + - = . _ : / @
        Invalid characters like parentheses () will be replaced with underscores.
        
        Args:
            value (str): Original tag value
            
        Returns:
            str: Sanitized tag value safe for S3 tags
        """
        if not value:
            return value
        
        # Convert to string and replace invalid characters
        sanitized = str(value)
        
        # Replace invalid characters with underscores
        # AWS allows: letters, numbers, spaces, + - = . _ : / @
        invalid_chars = '()[]{}|\\`~!#$%^&*"\'<>?;,'
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length to 256 characters (AWS limit)
        return sanitized[:256]

    @classmethod
    def upload_file_objects_to_s3(cls, uploaded_files, chat_id, file_classifications=None):
        """
        Upload multiple file objects to S3 and prepare them for Bedrock processing.
        
        Args:
            uploaded_files (list): List of file objects from Flask request
            chat_id (str): Chat ID to use as prefix path in S3
            file_classifications (dict): Optional dict mapping filenames to document types
            
        Returns:
            tuple: (processed_files, file_objects) where:
                - processed_files: List of file metadata for DynamoDB storage
                - file_objects: List of file objects for Bedrock processing
                
        Raises:
            Exception: For any errors during upload
        """
        from werkzeug.utils import secure_filename
        from datetime import datetime
        import boto3
        
        logger.debug(f"Uploading {len(uploaded_files)} files for chat_id: {chat_id}")
        logger.debug(f"Received file_classifications: {file_classifications}")
        
        # Get S3 bucket name from config
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        if not bucket_name:
            raise Exception("S3 bucket not configured")
        
        # Create S3 client
        s3 = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        
        processed_files = []
        file_objects = []
        
        for file in uploaded_files:
            if file.filename:
                try:
                    # Preserve original filename for display and classification lookup
                    original_display_filename = file.filename
                    
                    # Apply secure_filename transformation for storage
                    secure_original_filename = secure_filename(file.filename)
                    
                    # Validate file extension
                    file_extension = os.path.splitext(secure_original_filename)[1].lower()
                    if not CustomerConfig.is_extension_allowed(file_extension):
                        logger.warning(f"Skipping file with disallowed extension: {secure_original_filename}")
                        continue
                    
                    # Get document classification from frontend - try both original and secure filenames
                    document_classification = None
                    if file_classifications:
                        # First try original filename (what frontend sends)
                        if original_display_filename in file_classifications:
                            document_classification = file_classifications[original_display_filename]
                            logger.debug(f"Found classification for original filename '{original_display_filename}': {document_classification}")
                        # Fallback to secure filename
                        elif secure_original_filename in file_classifications:
                            document_classification = file_classifications[secure_original_filename]
                            logger.debug(f"Found classification for secure filename '{secure_original_filename}': {document_classification}")
                        else:
                            logger.warning(f"No classification found for file '{original_display_filename}' (secure: '{secure_original_filename}')")
                            logger.debug(f"Available classification keys: {list(file_classifications.keys())}")
                    
                    # Use secure filename for S3 storage
                    # Format: chat_id/uploads/secure_name.ext
                    s3_key = f"{chat_id}/uploads/{secure_original_filename}"
                    
                    # Read file content for Bedrock
                    file_content = file.read()
                    file_size = len(file_content)
                    
                    # Reset file pointer and upload to S3 for storage with tags
                    file.seek(0)
                    
                    # Prepare S3 tags
                    s3_tags = {
                        'ChatId': chat_id,
                        'UploadDate': datetime.utcnow().isoformat(),
                        'OriginalFilename': cls.sanitize_s3_tag_value(original_display_filename)
                    }
                    
                    # Add document classification tag if available
                    if document_classification:
                        s3_tags['DocumentType'] = cls.sanitize_s3_tag_value(document_classification)
                        logger.debug(f"Adding S3 tag DocumentType={cls.sanitize_s3_tag_value(document_classification)} for {original_display_filename}")
                    
                    # Convert tags to S3 format - URL encode values for S3 compatibility
                    from urllib.parse import quote
                    tag_string = '&'.join([f'{quote(str(k), safe="")}={quote(str(v), safe="")}' for k, v in s3_tags.items()])
                    
                    # Determine the correct content type based on file extension BEFORE upload
                    # This ensures S3 stores the file with the correct Content-Type for browser preview
                    detected_content_type = file.content_type or 'application/octet-stream'
                    
                    # Override content type for common file extensions that browsers might not detect correctly
                    filename_lower = secure_original_filename.lower()
                    if filename_lower.endswith('.md'):
                        detected_content_type = 'text/markdown'
                    elif filename_lower.endswith('.txt'):
                        detected_content_type = 'text/plain'
                    elif filename_lower.endswith('.csv'):
                        detected_content_type = 'text/csv'
                    elif filename_lower.endswith('.json'):
                        detected_content_type = 'application/json'
                    elif filename_lower.endswith('.pdf'):
                        detected_content_type = 'application/pdf'
                    elif filename_lower.endswith('.docx'):
                        detected_content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    elif filename_lower.endswith('.doc'):
                        detected_content_type = 'application/msword'
                    elif filename_lower.endswith('.xlsx'):
                        detected_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    elif filename_lower.endswith('.xls'):
                        detected_content_type = 'application/vnd.ms-excel'
                    elif filename_lower.endswith('.pptx'):
                        detected_content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    elif filename_lower.endswith('.ppt'):
                        detected_content_type = 'application/vnd.ms-powerpoint'
                    elif filename_lower.endswith('.png'):
                        detected_content_type = 'image/png'
                    elif filename_lower.endswith('.jpg') or filename_lower.endswith('.jpeg'):
                        detected_content_type = 'image/jpeg'
                    elif filename_lower.endswith('.gif'):
                        detected_content_type = 'image/gif'
                    elif filename_lower.endswith('.svg'):
                        detected_content_type = 'image/svg+xml'
                    elif filename_lower.endswith('.bmp'):
                        detected_content_type = 'image/bmp'
                    elif filename_lower.endswith('.webp'):
                        detected_content_type = 'image/webp'
                    elif filename_lower.endswith('.xml'):
                        detected_content_type = 'application/xml'
                    elif filename_lower.endswith('.html') or filename_lower.endswith('.htm'):
                        detected_content_type = 'text/html'
                    elif filename_lower.endswith('.yaml') or filename_lower.endswith('.yml'):
                        detected_content_type = 'application/x-yaml'
                    
                    logger.debug(f"Content type for upload: original='{file.content_type}', detected='{detected_content_type}', filename='{original_display_filename}'")
                    
                    s3.upload_fileobj(
                        file, 
                        bucket_name, 
                        s3_key, 
                        ExtraArgs={
                            'ServerSideEncryption': 'AES256',
                            'Tagging': tag_string,
                            'ContentType': detected_content_type  # Set correct Content-Type for browser preview
                        }
                    )
                    
                    # Get version ID from the upload response
                    response = s3.head_object(Bucket=bucket_name, Key=s3_key)
                    version_id = response.get('VersionId')
                    
                    # Check file size limits for Bedrock (max 20MB for documents, 5MB for images)
                    max_size = 20 * 1024 * 1024  # 20MB for documents
                    if detected_content_type.startswith('image/'):
                        max_size = 5 * 1024 * 1024  # 5MB for images

                    # Create file metadata for DynamoDB storage
                    file_metadata = {
                        'file_size': str(file_size),
                        's3_key': s3_key,  # This now includes uploads/ prefix
                        's3_url': f"s3://{bucket_name}/{s3_key}",
                        'type': detected_content_type,  # Use the corrected content type
                        'version_id': version_id,
                        'original_filename': secure_original_filename,  # Secure filename for storage
                        'original_display_filename': original_display_filename,  # Original filename for display
                        'upload_timestamp': datetime.utcnow().isoformat(),
                        'document_classification': document_classification  # Frontend classification
                    }
                    
                    logger.debug(f"Content type detection: original='{file.content_type}', detected='{detected_content_type}', filename='{original_display_filename}'")
                    
                    # Create file object for Bedrock (with actual content)
                    file_for_bedrock = {
                        'name': original_display_filename,  # Use original display filename for Bedrock
                        'content': file_content,
                        'content_type': detected_content_type,
                        'size': file_size,
                        'too_large': file_size > max_size,
                        'document_classification': document_classification  # Include classification for Bedrock
                    }
                    
                    if file_size > max_size:
                        logger.warning(f"File {original_display_filename} ({file_size} bytes) exceeds Bedrock limit ({max_size} bytes)")
                        # Still create the file object but mark it as too large
                        file_for_bedrock['content'] = b''  # Don't send large files to Bedrock
                    
                    processed_files.append(file_metadata)
                    file_objects.append(file_for_bedrock)
                    
                    # Log the complete file processing
                    logger.debug(f"FILE_UPLOAD_COMPLETE: {original_display_filename}")
                    logger.debug(f"  Original Display Name: {original_display_filename}")
                    logger.debug(f"  Secure Storage Name: {secure_original_filename}")
                    logger.debug(f"  S3 Location: {s3_key}")
                    logger.debug(f"  Size: {file_size} bytes")
                    logger.debug(f"  Content Type: {file.content_type}")
                    logger.debug(f"  Version ID: {version_id}")
                    logger.debug(f"  Document Classification: {document_classification}")
                    logger.debug(f"  Will send to Bedrock: {not file_for_bedrock.get('too_large', False)}")
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    # Continue with other files
                    
        logger.debug(f"Successfully processed {len(processed_files)} files for chat_id: {chat_id}")
        
        # Log final classification mapping for debugging
        for file_info in processed_files:
            display_name = file_info.get('original_display_filename', 'Unknown')
            storage_name = file_info.get('original_filename', 'Unknown')
            classification = file_info.get('document_classification', 'None')
            logger.debug(f"FINAL_FILE_MAPPING: '{display_name}' -> '{storage_name}' -> '{classification}'")
        
        return processed_files, file_objects
    
    @classmethod
    def upload_local_file_to_s3(cls,bucket_name, local_file_path, chat_id):
        """
        Upload a file to the S3 bucket configured in the application.
        
        Args:
            local_file_path (str): Path to the local file to upload
            chat_id (str): Chat ID to use as prefix path in S3
            
        Returns:
            dict: Response containing status and message
            
        Raises:
            FileNotFoundError: If the local file does not exist
            Exception: For any other errors during upload
        """
        logger.debug(f"Executing upload_file_to_s3(local_file_path='{local_file_path}', chat_id='{chat_id}')")
        
        # Validate if file exists
        if not os.path.isfile(local_file_path):
            logger.error(f"File not found: {local_file_path}")
            raise FileNotFoundError(f"File not found: {local_file_path}")
        
        logger.debug(f"File exists: {local_file_path}")        
        try:                        
            region = CustomerConfig.get_value('AWS_REGION')
            logger.debug(f"Using S3 bucket: {bucket_name} in region: {region}")
            
            # Create S3 client
            s3_client = boto3.client('s3', region_name=region)
            logger.debug(f"S3 client created for region: {region}")
            
            # Extract filename from path
            file_name = os.path.basename(local_file_path)
            logger.debug(f"Extracted filename: {file_name}")
            
            # Create S3 key with chat_id as prefix
            s3_key = f"{chat_id}/{file_name}"
            logger.debug(f"S3 key created: {s3_key}")
            
            # Upload file to S3
            logger.debug(f"Uploading file {file_name} to S3 bucket {bucket_name} with key {s3_key}")
            s3_client.upload_file(local_file_path, bucket_name, s3_key, ExtraArgs={'ContentType': 'image/png', 'ServerSideEncryption': 'AES256'})
            logger.debug(f"File uploaded to S3 successfully")
            
            # Generate S3 URI for the uploaded file
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            logger.debug(f"Generated S3 URI: {s3_uri}")
            
            # Check if we should delete the local file after upload
            delete_local_file_config = CustomerConfig.get_value('DELETE_LOCAL_FILE_AFTER_BACKUP_S3', True)
            
            # Convert to boolean if it's a string
            if isinstance(delete_local_file_config, str):
                delete_local_file = delete_local_file_config.lower() == 'true'
            else:
                delete_local_file = bool(delete_local_file_config)
                
            logger.debug(f"DELETE_LOCAL_FILE_AFTER_BACKUP_S3 configuration: {delete_local_file_config} (parsed as {delete_local_file})")
            
            if delete_local_file:
                # Remove local file after successful upload
                os.remove(local_file_path)
                logger.debug(f"File {file_name} uploaded successfully and removed from local storage")
            else:
                logger.debug(f"File {file_name} uploaded successfully. Local file kept at {local_file_path}")
            
            result = {
                "status": "success",
                "message": "File uploaded successfully",
                "s3_uri": s3_uri
            }
            logger.debug(f"Returning result: {result}")
            return result
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise Exception(f"Error uploading file to S3: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error during file upload: {str(e)}")
    
    @classmethod
    def generate_s3_signed_url(cls, s3_uri):
        """
        Generate a signed URL for the S3 object.

        Args:
            s3_uri (str): S3 URI of the object

        Returns:
            str: Signed URL for the S3 object

        Raises:
            Exception: If there's an error generating the signed URL
        """
        logger.debug(f"Executing get_signed_url(s3_uri='{s3_uri}')")
        
        try:
            # Get S3 bucket name from configuration
            bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
            region = CustomerConfig.get_aws_region()
            logger.debug(f"Using S3 bucket: {bucket_name} in region: {region}")

            # Create S3 client
            s3_client = boto3.client('s3', region_name=region)
            logger.debug(f"S3 client created for region: {region}")

            # Extract filename from path
            file_name = os.path.basename(s3_uri)
            logger.debug(f"Extracted filename: {file_name}")

            # Parse the S3 URI to extract the key
            if s3_uri.startswith('s3://'):
                parts = s3_uri.replace('s3://', '').split('/', 1)
                if len(parts) > 1:
                    s3_key = parts[1]
                else:
                    s3_key = file_name
            else:
                s3_key = s3_uri
                
            logger.debug(f"Extracted S3 key: {s3_key}")

            # Get signed URL expiration time from config (in minutes)
            signed_url_time = CustomerConfig.get_value('SINGED_URL_TIME', '60')
            
            try:
                # Convert to integer minutes, then to seconds
                minutes = int(signed_url_time)
                expires_in = minutes * 60  # Convert minutes to seconds
            except (ValueError, TypeError):
                # If conversion fails, use default of 60 minutes (3600 seconds)
                logger.warning(f"Invalid SINGED_URL_TIME value: '{signed_url_time}', using default of 60 minutes")
                expires_in = 3600
                        
            logger.debug(f"Using signed URL expiration time: {signed_url_time} minutes ({expires_in} seconds)")
            
            # Generate signed URL
            logger.debug(f"Generating presigned URL for bucket: {bucket_name}, key: {s3_key}")
            signed_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            logger.debug(f"Generated presigned URL: {signed_url}")

            return signed_url

        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            raise Exception(f"Error generating signed URL: {str(e)}")
    
    @classmethod
    def get_cloudfront_signed_url(cls, s3_uri):
        """
        Generate a CloudFront signed URL for the S3 object.

        Args:
            s3_uri (str): S3 URI of the object

        Returns:
            str: CloudFront signed URL for the S3 object

        Raises:
            Exception: If there's an error generating the signed URL
        """
        logger.debug(f"Executing get_cloudfront_signed_url(s3_uri='{s3_uri}')")
        
        try:
            # Parse the S3 URI to extract the key
            if s3_uri.startswith('s3://'):
                parts = s3_uri.replace('s3://', '').split('/', 1)
                if len(parts) > 1:
                    key = parts[1]
                else:
                    key = ''
            else:
                key = s3_uri
                
            logger.debug(f"Extracted key from S3 URI: {key}")
                
            # Get CloudFront distribution domain from configuration
            # Ensure config is loaded before accessing values
            try:
                # Try to get the config first to ensure it's loaded
                config = CustomerConfig.get_config()
                if not config:
                    logger.debug("Config not loaded, attempting to load it")
                    CustomerConfig.load_config()
                
                cloudfront_domain = CustomerConfig.get_value('CLOUDFRONT_DOMAIN')
                logger.debug(f"Using CloudFront domain: {cloudfront_domain}")
                if not cloudfront_domain:
                    logger.error("CloudFront domain not configured")
                    raise ValueError("CloudFront domain not configured")
            except Exception as e:
                logger.error(f"Error accessing configuration: {str(e)}")
                raise ValueError(f"Error accessing configuration: {str(e)}")
                
            # Get CloudFront key pair ID and private key path
            key_pair_id = CustomerConfig.get_value('CLOUDFRONT_KEY_PAIR_ID')
            private_key_path = CustomerConfig.get_value('CLOUDFRONT_PRIVATE_KEY_PATH')
            
            logger.debug(f"Using CloudFront key pair ID: {key_pair_id}")
            logger.debug(f"Using CloudFront private key path: {private_key_path}")
            
            if not key_pair_id or not private_key_path:
                logger.error("CloudFront key pair ID or private key path not configured")
                raise ValueError("CloudFront key pair ID or private key path not configured")
            
            # Read private key
            logger.debug(f"Reading private key from: {private_key_path}")
            with open(private_key_path, 'rb') as key_file:
                private_key = key_file.read()
            logger.debug("Private key read successfully")
            
            # Create CloudFront signer
            def rsa_signer(message):
                logger.debug("Creating RSA signature")
                key = load_pem_private_key(private_key, password=None, backend=default_backend())
                return key.sign(message, padding.PKCS1v15(), hashes.SHA1())  # nosemgrep: python.cryptography.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1: CloudFront URL signing requires SHA1 for compatibility # nosec B303 - SHA1 required by AWS CloudFront URL signing specification
            
            # Create CloudFront signer
            logger.debug(f"Creating CloudFront signer with key pair ID: {key_pair_id}")
            signer = CloudFrontSigner(key_pair_id, rsa_signer)
            
            # Get signed URL expiration time from config (in minutes)
            signed_url_time = CustomerConfig.get_value('SINGED_URL_TIME', '60')
            
            try:
                # Convert to integer minutes, then to hours
                minutes = int(signed_url_time)
                hours = minutes / 60.0  # Convert minutes to hours
            except (ValueError, TypeError):
                # If conversion fails, use default of 60 minutes (1 hour)
                logger.warning(f"Invalid SINGED_URL_TIME value: '{signed_url_time}', using default of 60 minutes")
                hours = 1.0
                
            logger.debug(f"Using signed URL expiration time: {signed_url_time} minutes ({hours} hours)")
            
            # Set expiration time
            expire_date = datetime.datetime.now(UTC) + datetime.timedelta(hours=hours)
            logger.debug(f"Setting expiration time to: {expire_date}")
            
            # Generate the signed URL
            url = f'{cloudfront_domain}/{key}'
            logger.debug(f"CLOUDFRONT_DEBUG: domain='{cloudfront_domain}', key='{key}', full_url='{url}'")
            logger.debug(f"Generating CloudFront signed URL for: {url}")
            signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)
            logger.debug(f"Generated CloudFront signed URL: {signed_url}")
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating CloudFront signed URL: {str(e)}")
            raise Exception(f"Error generating CloudFront signed URL: {str(e)}")
            
    @classmethod
    def get_cloudfront_signed_url_with_version(cls, s3_uri, version_id):
        """
        Generate a CloudFront signed URL for a specific version of an S3 object.

        Args:
            s3_uri (str): S3 URI of the object
            version_id (str): Version ID of the S3 object

        Returns:
            str: CloudFront signed URL for the specific version of the S3 object

        Raises:
            Exception: If there's an error generating the signed URL
        """
        logger.debug(f"Executing get_cloudfront_signed_url_with_version(s3_uri='{s3_uri}', version_id='{version_id}')")
        
        try:
            # Parse the S3 URI to extract the key
            if s3_uri.startswith('s3://'):
                parts = s3_uri.replace('s3://', '').split('/', 1)
                if len(parts) > 1:
                    key = parts[1]
                else:
                    key = ''
            else:
                key = s3_uri
                
            logger.debug(f"Extracted key from S3 URI: {key}")
                
            # Get CloudFront distribution domain from configuration
            # Ensure config is loaded before accessing values
            try:
                # Try to get the config first to ensure it's loaded
                config = CustomerConfig.get_config()
                if not config:
                    logger.debug("Config not loaded, attempting to load it")
                    CustomerConfig.load_config()
                
                cloudfront_domain = CustomerConfig.get_value('CLOUDFRONT_DOMAIN')
                logger.debug(f"Using CloudFront domain: {cloudfront_domain}")
                if not cloudfront_domain:
                    logger.error("CloudFront domain not configured")
                    raise ValueError("CloudFront domain not configured")
            except Exception as e:
                logger.error(f"Error accessing configuration: {str(e)}")
                raise ValueError(f"Error accessing configuration: {str(e)}")
                
            # Get CloudFront key pair ID and private key path
            key_pair_id = CustomerConfig.get_value('CLOUDFRONT_KEY_PAIR_ID')
            private_key_path = CustomerConfig.get_value('CLOUDFRONT_PRIVATE_KEY_PATH')
            
            logger.debug(f"Using CloudFront key pair ID: {key_pair_id}")
            logger.debug(f"Using CloudFront private key path: {private_key_path}")
            
            if not key_pair_id or not private_key_path:
                logger.error("CloudFront key pair ID or private key path not configured")
                raise ValueError("CloudFront key pair ID or private key path not configured")
            
            # Read private key
            logger.debug(f"Reading private key from: {private_key_path}")
            with open(private_key_path, 'rb') as key_file:
                private_key = key_file.read()
            logger.debug("Private key read successfully")
            
            # Create CloudFront signer
            def rsa_signer(message):
                logger.debug("Creating RSA signature")
                key = load_pem_private_key(private_key, password=None, backend=default_backend())
                return key.sign(message, padding.PKCS1v15(), hashes.SHA1()) # nosemgrep: python.cryptography.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1: CloudFront URL signing requires SHA1 for compatibility # nosec B303 - SHA1 required by AWS CloudFront URL signing specification. 
            
            # Create CloudFront signer
            logger.debug(f"Creating CloudFront signer with key pair ID: {key_pair_id}")
            signer = CloudFrontSigner(key_pair_id, rsa_signer)
            
            # Get signed URL expiration time from config (in minutes)
            signed_url_time = CustomerConfig.get_value('SINGED_URL_TIME', '60')
            
            try:
                # Convert to integer minutes, then to hours
                minutes = int(signed_url_time)
                hours = minutes / 60.0  # Convert minutes to hours
            except (ValueError, TypeError):
                # If conversion fails, use default of 60 minutes (1 hour)
                logger.warning(f"Invalid SINGED_URL_TIME value: '{signed_url_time}', using default of 60 minutes")
                hours = 1.0
                
            logger.debug(f"Using signed URL expiration time: {signed_url_time} minutes ({hours} hours)")
            
            # Set expiration time
            expire_date = datetime.datetime.now(UTC) + datetime.timedelta(hours=hours)
            logger.debug(f"Setting expiration time to: {expire_date}")
            
            # Generate the signed URL with version ID if provided
            if version_id:
                url = f'{cloudfront_domain}/{key}?versionId={version_id}'
            else:
                url = f'{cloudfront_domain}/{key}'
                
            logger.debug(f"Generating CloudFront signed URL with version ID: {url}")
            signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)
            logger.debug(f"Generated CloudFront signed URL with version: {signed_url}")
            
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating CloudFront signed URL with version: {str(e)}")
            raise Exception(f"Error generating CloudFront signed URL with version: {str(e)}")