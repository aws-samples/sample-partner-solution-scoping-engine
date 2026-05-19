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
File routes for handling file uploads and document management.
"""
import logging
import uuid
import os
from backend.services.document_processor import DocumentProcessor
import boto3
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from backend.config.app_config import CustomerConfig
from ..models.chat import list_chats_for_user, update_chat_document
from ..middleware.auth_middleware import login_required, get_current_user

logger = logging.getLogger(__name__)

file_bp = Blueprint('file_bp', __name__)

import re
_VERSION_ID_RE = re.compile(r'^[A-Za-z0-9._\-]{1,128}$')

def _validate_version_id(version_id):
    """Validate S3 version ID format. Returns sanitized value or None."""
    if not version_id:
        return None
    if not _VERSION_ID_RE.match(version_id):
        return False  # sentinel for invalid
    return version_id

def get_s3_client():
    """Get an S3 client with the configured region."""
    return boto3.client('s3', region_name=CustomerConfig.get_aws_region())

def verify_chat_ownership(user_id, chat_id):
    """Verify the chat belongs to the current user. Returns True if owned, False otherwise."""
    if chat_id == 'static':
        return True
    chats_response = list_chats_for_user(user_id)
    chats = chats_response.get('chats', [])
    return any(c['chat_id'] == chat_id for c in chats)

@file_bp.route('/chats/<chat_id>/upload', methods=['POST'])
@login_required
def upload_file(chat_id):
    """Upload a file for a chat session."""
    current_user = get_current_user()
    
    try:
        user_id = current_user.user_id
        
        logger.debug(f"File upload request: chat_id={chat_id}, user={user_id}")
        
        # Check if the chat exists
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        if not chat:
            logger.warning(f"Upload to non-existent chat: chat_id={chat_id}, user={user_id}")
            return jsonify({"error": f"Chat with ID {chat_id} not found"}), 404
        
        # Check if file is in the request
        if 'file' not in request.files:
            logger.warning(f"Upload missing file: chat_id={chat_id}")
            return jsonify({"error": "No file part in the request"}), 400
            
        file = request.files['file']
        
        if file.filename == '':
            logger.warning(f"Upload empty filename: chat_id={chat_id}")
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if not CustomerConfig.is_extension_allowed(file_extension):
            allowed_extensions = CustomerConfig.get_allowed_extensions()
            logger.warning(f"Upload invalid extension: chat_id={chat_id}, file={file.filename[:30]}..., ext={file_extension}")
            return jsonify({
                "error": f"File type not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
            }), 400
            
        # Get upload option (read or save)
        option = request.form.get('option', 'save')
        
        # Secure the filename to prevent directory traversal attacks
        filename = secure_filename(file.filename)
        
        logger.debug(f"Processing upload: chat_id={chat_id}, filename={filename[:30]}..., option={option}")
        
        # Generate a unique filename to prevent collisions
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Get S3 bucket name from config
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        # Validate bucket name to prevent SSRF (even though it's from config)
        if not bucket_name or not isinstance(bucket_name, str) or '/' in bucket_name or ':' in bucket_name:
            logger.error(f"Invalid S3 bucket config: bucket={bucket_name[:50]}...")
            return jsonify({"error": "Invalid S3 bucket configuration"}), 500
        
        # Validate bucket name to prevent SSRF (even though it's from config)
        if not bucket_name or not isinstance(bucket_name, str) or '/' in bucket_name or ':' in bucket_name:
            logger.error(f"Invalid S3 bucket config: bucket={bucket_name[:50]}...")
            return jsonify({"error": "Invalid S3 bucket configuration"}), 500
        
        # Create S3 client
        s3 = get_s3_client()
        
        # Check if folder for chat_id exists, create if not
        try:
            s3.head_object(Bucket=bucket_name, Key=f"{chat_id}/")
        except:
            # Folder doesn't exist, create it
            s3.put_object(Bucket=bucket_name, Key=f"{chat_id}/")
        
        # Upload file to S3
        s3_key = f"{chat_id}/{unique_filename}"
        s3.upload_fileobj(file, bucket_name, s3_key)
        
        # Generate S3 URL for the file - with additional validation
        if not s3_key or not isinstance(s3_key, str) or '..' in s3_key or s3_key.startswith('/'):
            logger.error(f"Invalid S3 key: key={s3_key[:50]}...")
            return jsonify({"error": "Invalid file path generated"}), 500
        
        s3_url = f"s3://{bucket_name}/{s3_key}"  # nosemgrep: python.django.security.injection.tainted-url-host.tainted-url-host: bucket_name comes from validated config, not user input
        
        # Create document metadata
        document = {
            "name": filename,
            "timestamp": request.form.get('timestamp') or datetime.utcnow().isoformat(),
            "user_id": user_id,
            "location": s3_url
        }
        
        # Update chat with document metadata
        document_id = str(uuid.uuid4())
        success = update_chat_document(chat_id, document_id, document)
        
        if not success:
            logger.warning(f"Store document metadata failed: chat_id={chat_id}, filename={filename[:30]}...")
            return jsonify({"success": False, "error": "Failed to store document metadata"}), 500
        
        logger.info(f"File uploaded: chat_id={chat_id}, filename={filename[:30]}..., size={file_size}, option={option}")
        
        # If option is 'read', we need to process the file for the AI
        if option == 'read':
            # File reading logic not yet implemented
            # For now, just return success
            return jsonify({
                "success": True,
                "message": "File uploaded and will be processed for reading",
                "document": document
            })
        else:
            # Just save to library
            return jsonify({
                "success": True,
                "message": "File uploaded and saved to library",
                "document": document
            })
            
    except Exception as e:
        logger.error(f"Upload file failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to upload file"}), 500

@file_bp.route('/chats/<chat_id>/documents/<document_name>', methods=['GET'])
@login_required
def get_document_url(chat_id, document_name):
    """Get a presigned URL for a document."""
    current_user = get_current_user()
    
    try:
        user_id = current_user.user_id
        
        # Check if the chat exists and belongs to user
        if not verify_chat_ownership(user_id, chat_id):
            return jsonify({"error": f"Chat with ID {chat_id} not found"}), 404
        
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        # Get documents from chat
        documents = chat.get('documents', [])
        
        # Find the document
        document = next((d for d in documents if d.get('name') == document_name), None)
        
        if not document:
            return jsonify({"error": f"Document {document_name} not found"}), 404
        
        # Get S3 location
        s3_location = document.get('location')
        
        if not s3_location or not s3_location.startswith('s3://'):
            return jsonify({"error": "Invalid document location"}), 400
        
        # Parse S3 URL
        s3_parts = s3_location.replace('s3://', '').split('/', 1)
        bucket_name = s3_parts[0]
        key = s3_parts[1]
        
        # Validate bucket name against configured bucket to prevent SSRF
        expected_bucket = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        if bucket_name != expected_bucket:
            logger.error(f"Invalid bucket: got={bucket_name[:30]}..., expected={expected_bucket[:30]}...")
            return jsonify({"error": "Invalid document location"}), 400
        
        # Create S3 client
        s3 = get_s3_client()
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=3600
        )
        
        return jsonify({
            "url": presigned_url,
            "document": document
        })
    except Exception as e:
        logger.error(f"Get document URL failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get document URL"}), 500


@file_bp.route('/chats/<chat_id>/documents/diagram/s3_signedurl/<document_name>', methods=['GET'])
@login_required
def get_document_s3_signed_url(chat_id,document_name):
    """Get a signed URL for a document with S3."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Get bucket name from config
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        # Validate bucket name
        if not bucket_name or not isinstance(bucket_name, str) or '/' in bucket_name or ':' in bucket_name:
            logger.error(f"Invalid S3 bucket config: bucket={bucket_name[:50]}...")
            return jsonify({"error": "Invalid S3 bucket configuration"}), 500
            
        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
        
        # use DocumentProcessor to generate a signed url
        # nosemgrep: python.flask.security.injection.tainted-url-host.tainted-url-host
        # bucket_name comes from validated config, not user input
        s3_file=f"s3://{bucket_name}/{chat_id}/{document_name}/"  # nosemgrep: python.django.security.injection.tainted-url-host.tainted-url-host: bucket_name comes from validated config, not user input
        logger.debug(f"Generating S3 singed url for file: {s3_file}")
        presigned_url = DocumentProcessor.generate_s3_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/{document_name}/"
        })
    except Exception as e:
        logger.error(f"Get document URL failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get document URL"}), 500

@file_bp.route('/chats/<chat_id>/documents/diagram/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_document_cf_signed_url(chat_id,document_name):
    """Get a signed URL for a document with cloudfront."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
        
        # use DocumentProcessor to generate a signed url
        s3_file=f"{chat_id}/{document_name}"
        logger.debug(f"Generating CF singed url for file: {s3_file}")
        presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/{document_name}/"
        })
    except Exception as e:
        logger.error(f"Get document URL failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get document URL"}), 500

@file_bp.route('/chats/<chat_id>/documents/sow/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_sow_cf_signed_url(chat_id, document_name):
    """Get a signed URL for a SOW document with cloudfront."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
            
        # use DocumentProcessor to generate a signed url
        s3_file = f"{chat_id}/{document_name}"
        logger.debug(f"Generating CF signed url for SOW file: {s3_file}")
        presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/{document_name}/"
        })
    except Exception as e:
        logger.error(f"Get SOW URL failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get SOW document URL"}), 500

@file_bp.route('/chats/<chat_id>/documents/pricing/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_pricing_cf_signed_url(chat_id, document_name):
    """Get a signed URL for a pricing document with cloudfront."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
            
        # use DocumentProcessor to generate a signed url
        s3_file = f"{chat_id}/pricing/{document_name}"
        logger.debug(f"Generating CF signed url for pricing file: {s3_file}")
        presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/pricing/{document_name}"
        })
    except Exception as e:
        logger.error(f"Get pricing URL failed: error={str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get pricing document URL"}), 500


@file_bp.route('/chats/<chat_id>/documents/cloudformation/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_cloudformation_cf_signed_url(chat_id, document_name):
    """Get a signed URL for a CloudFormation document with cloudfront."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
            
        # use DocumentProcessor to generate a signed url
        s3_file = f"{chat_id}/cloudformation/{document_name}"
        logger.debug(f"Generating CF signed url for CloudFormation file: {s3_file}")
        presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/cloudformation/{document_name}"
        })
    except Exception as e:
        logger.error(f"Error getting CloudFormation document URL: {e}", exc_info=True)
        return jsonify({"error": "Failed to get CloudFormation document URL"}), 500

@file_bp.route('/chats/<chat_id>/documents/wafr/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_wafr_cf_signed_url(chat_id, document_name):
    """Get a signed URL for a WAFR assessment document with cloudfront."""
    from flask import make_response
    
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Get query parameters
        version_id = _validate_version_id(request.args.get('version_id'))
        if version_id is False:
            return jsonify({"error": "Invalid version_id format"}), 400
        
        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
            
        # use DocumentProcessor to generate a signed url
        s3_file = f"{chat_id}/wafr/{document_name}"
        logger.debug(f"Generating CF signed url for WAFR file: {s3_file}, version_id: {version_id}")
        
        # Use version-specific method if version_id is provided
        if version_id:
            presigned_url = DocumentProcessor.get_cloudfront_signed_url_with_version(s3_file, version_id)
        else:
            presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        # Create response with cache-control headers to prevent browser caching
        response = make_response(jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/wafr/{document_name}"
        }))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error getting WAFR document URL: {e}", exc_info=True)
        return jsonify({"error": "Failed to get WAFR document URL"}), 500

@file_bp.route('/chats/<chat_id>/documents/uploads/cf_signedurl/<document_name>', methods=['GET'])
@login_required
def get_uploaded_file_cf_signed_url(chat_id, document_name):
    """Get a signed URL for an uploaded file with cloudfront."""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Get query parameters
        version_id = _validate_version_id(request.args.get('version_id'))
        if version_id is False:
            return jsonify({"error": "Invalid version_id format"}), 400
        
        # Validate chat_id and document_name
        if not chat_id or not document_name or '..' in chat_id or '..' in document_name:
            logger.error(f"Invalid params: chat_id={chat_id}, doc_name={document_name[:30]}...")
            return jsonify({"error": "Invalid document parameters"}), 400
            
        # use DocumentProcessor to generate a signed url for uploaded files
        s3_file = f"{chat_id}/uploads/{document_name}"
        logger.debug(f"UPLOADS_ROUTE_DEBUG: chat_id='{chat_id}', document_name='{document_name}', s3_file='{s3_file}', version_id='{version_id}'")
        
        # Use version-specific method if version_id is provided
        if version_id:
            presigned_url = DocumentProcessor.get_cloudfront_signed_url_with_version(s3_file, version_id)
        else:
            presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_file)
        
        return jsonify({
            "url": presigned_url,
            "uri": f"{chat_id}/uploads/{document_name}"
        })
    except Exception as e:
        logger.error(f"Error getting uploaded file URL: {e}", exc_info=True)
        return jsonify({"error": "Failed to get uploaded file URL"}), 500
        
@file_bp.route('/chats/<chat_id>/documents/cf_signedurl/<path:file_path>', methods=['GET'])
@login_required
def get_file_cf_signed_url_with_version(chat_id,file_path):
    """
    Get a signed URL for any file with cloudfront, supporting version ID.
    
    Path format: <key-prefix-path>/<file-name>.<extension>
    Query parameters:
    - version_id: The version ID of the file (required)
    """
    from flask import make_response
    
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404

        # Get query parameters
        version_id = _validate_version_id(request.args.get('version_id'))
        if version_id is False:
            return jsonify({"error": "Invalid version_id format"}), 400
        
        # Validate chat_id and file_path
        if not file_path or '..' in file_path or file_path.startswith('/'):
            logger.error(f"Invalid file_path: {file_path}")
            return jsonify({"error": "Invalid file path"}), 400
            
        if chat_id and ('..' in chat_id or chat_id.startswith('/')):
            logger.error(f"Invalid chat_id: {chat_id}")
            return jsonify({"error": "Invalid chat ID"}), 400
            
        # Construct the S3 key path
        if chat_id:
            # Check if file_path already starts with chat_id
            if file_path.startswith(f"{chat_id}/"):
                s3_key = file_path
            else:
                # Fix for SA review merge: detect if file_path contains an SA copy chat ID
                # SA copy chat IDs are UUIDs, so look for UUID pattern at start of file_path
                import re
                uuid_pattern = r'^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/'
                match = re.match(uuid_pattern, file_path)
                
                if match:
                    sa_copy_chat_id = match.group(1)
                    # Extract the actual file path after the SA copy chat ID
                    actual_file_path = file_path[len(sa_copy_chat_id) + 1:]
                    logger.info(f"Detected SA copy reference: {sa_copy_chat_id} -> correcting to {chat_id}")
                    s3_key = f"{chat_id}/{actual_file_path}"
                else:
                    s3_key = f"{chat_id}/{file_path}"
        else:
            s3_key = file_path
            
        logger.debug(f"FILE_DOWNLOAD_DEBUG: chat_id='{chat_id}', file_path='{file_path}', constructed_s3_key='{s3_key}', version_id='{version_id}'")
        logger.debug(f"Generating CF signed url for file: {s3_key} with version: {version_id}")
        
        # Use DocumentProcessor to generate a signed url with or without version
        if version_id:
            presigned_url = DocumentProcessor.get_cloudfront_signed_url_with_version(s3_key, version_id)
        else:
            # No version_id specified, use latest version
            presigned_url = DocumentProcessor.get_cloudfront_signed_url(s3_key)
        
        # Create response with cache-control headers to prevent browser caching
        response = make_response(jsonify({
            "url": presigned_url,
            "uri": s3_key,
        }))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error getting versioned document URL: {e}", exc_info=True)
        return jsonify({"error": "Failed to get versioned document URL"}), 500

@file_bp.route('/diagram-code/<chat_id>', methods=['GET'])
@login_required
def get_diagram_code(chat_id):
    """Get diagram code for a chat"""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404
        
        # Get S3 bucket and key
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        s3_key = f"{chat_id}/diagram_code.py"
        
        # Download from S3
        s3_client = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        diagram_code = response['Body'].read().decode('utf-8')
        
        return jsonify({"code": diagram_code})
        
    except Exception as e:
        error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            return jsonify({"error": "Diagram code not found"}), 404
        logger.error(f"Error getting diagram code: {e}")
        return jsonify({"error": "Failed to get diagram code"}), 500

@file_bp.route('/diagram-code/<chat_id>', methods=['PUT'])
@login_required
def update_diagram_code(chat_id):
    """Update diagram code for a chat"""
    try:
        current_user = get_current_user()
        if not verify_chat_ownership(current_user.user_id, chat_id):
            return jsonify({"error": "Chat not found"}), 404
        
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({"error": "Code is required"}), 400
        
        # Save to S3
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        s3_key = f"{chat_id}/diagram_code.py"
        
        s3_client = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=data['code'].encode('utf-8'),
            ContentType='text/plain'
        )
        
        return jsonify({"message": "Diagram code updated successfully"})
        
    except Exception as e:
        logger.error(f"Error updating diagram code: {e}")
        return jsonify({"error": "Failed to update diagram code"}), 500

# File Classification Routes
@file_bp.route('/file-classification/config', methods=['GET'])
@login_required
def get_file_classification_config():
    """Get file classification configuration for the frontend."""
    try:
        # Get configuration from app config
        file_classification_config = current_app.config.get('FILE_CLASSIFICATION_CONFIG', {})
        
        if not file_classification_config:
            logger.warning("FILE_CLASSIFICATION_CONFIG not found in app config")
            return jsonify({
                'success': False,
                'error': 'File classification configuration not found'
            }), 404
        
        logger.debug(f"Serving file classification config with {len(file_classification_config.get('rules', {}))} rules")
        
        return jsonify({
            'success': True,
            'config': file_classification_config
        })
        
    except Exception as e:
        logger.error(f"Error getting file classification config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/file-classification/config/<assistant_persona>', methods=['GET'])
@login_required
def get_assistant_classification_config(assistant_persona):
    """Get file classification configuration for a specific assistant persona."""
    try:
        # Validate persona against registry
        from ..config.personas import PersonaManager
        persona_manager = PersonaManager()
        if assistant_persona not in persona_manager.assistant_personas:
            return jsonify({
                'success': False,
                'error': f'Invalid assistant persona: {assistant_persona}'
            }), 400

        # Get configuration from app config
        file_classification_config = current_app.config.get('FILE_CLASSIFICATION_CONFIG', {})
        
        if not file_classification_config:
            return jsonify({
                'success': False,
                'error': 'File classification configuration not found'
            }), 404
        
        # Get assistant-specific config
        assistant_configs = file_classification_config.get('assistant_configs', {})
        assistant_config = assistant_configs.get(assistant_persona, assistant_configs.get('default', {}))
        
        # Combine rules with assistant config
        response_config = {
            'rules': file_classification_config.get('rules', {}),
            'assistant_config': assistant_config,
            'document_type_mapping': file_classification_config.get('document_type_mapping', {})
        }
        
        logger.debug(f"Serving classification config for assistant: {assistant_persona}")
        
        return jsonify({
            'success': True,
            'config': response_config
        })
        
    except Exception as e:
        logger.error(f"Error getting assistant classification config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500