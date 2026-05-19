# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""
Document management routes for approval workflow and access control.
"""

import logging
from flask import Blueprint, request, jsonify
from ..models.chat import get_chat_documents, get_chat_document, approve_document, get_chat_by_chat_id
from ..services.document_processor import DocumentProcessor
from ..middleware.auth_middleware import login_required, get_current_user

logger = logging.getLogger(__name__)

document_bp = Blueprint('document_bp', __name__)

def _verify_document_access(chat_id):
    """Verify the current user owns the chat or is an SA reviewer with a support relationship."""
    current_user = get_current_user()
    chat = get_chat_by_chat_id(chat_id)
    if not chat:
        return False, (jsonify({'success': False, 'error': 'Chat not found'}), 404)
    # Owner check
    if chat.get('user_id') == current_user.user_id:
        return True, None
    # SA review copy check
    if chat.get('source_chat_id') and chat.get('sa_reviewer') == current_user.user_id:
        return True, None
    # Solutions architect with support relationship and active review
    if current_user.is_solutions_architect():
        from ..models.support_relationship import user_supports_seller
        if user_supports_seller(current_user.user_id, chat.get('user_id', '')):
            if chat.get('review_status') in ('requested', 'in_progress'):
                return True, None
    return False, (jsonify({'success': False, 'error': 'Chat not found'}), 404)

@document_bp.route('/chats/<chat_id>/documents', methods=['GET'])
@login_required
def get_chat_documents_api(chat_id):
    """Get all documents for a chat."""
    try:
        allowed, error_response = _verify_document_access(chat_id)
        if not allowed:
            return error_response

        logger.debug(f"Getting documents: chat_id={chat_id}")
        documents = get_chat_documents(chat_id)
        logger.debug(f"Documents retrieved: chat_id={chat_id}, count={len(documents)}")
        return jsonify({
            'success': True,
            'documents': documents
        })
    except Exception as e:
        logger.error(f"Get documents failed: error={str(e)}")
        return jsonify({'success': False, 'error': 'Operation failed'}), 500

@document_bp.route('/chats/<chat_id>/documents/<document_id>', methods=['GET'])
@login_required
def get_document_api(chat_id, document_id):
    """Get specific document metadata."""
    try:
        allowed, error_response = _verify_document_access(chat_id)
        if not allowed:
            return error_response

        document = get_chat_document(chat_id, document_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        return jsonify({
            'success': True,
            'document': document
        })
    except Exception as e:
        logger.error(f"Get document failed: error={str(e)}")
        return jsonify({'success': False, 'error': 'Operation failed'}), 500

@document_bp.route('/chats/<chat_id>/documents/<document_id>/approve', methods=['POST'])
@login_required
def approve_document_api(chat_id, document_id):
    """Approve a document for download access."""
    try:
        current_user = get_current_user()
        user_id = current_user.user_id if current_user else 'unknown'

        allowed, error_response = _verify_document_access(chat_id)
        if not allowed:
            return error_response
        
        logger.debug(f"Approving document: chat_id={chat_id}, doc_id={document_id}, approver={user_id}")
        
        success = approve_document(chat_id, document_id, user_id)
        if success:
            logger.info(f"Document approved: chat_id={chat_id}, doc_id={document_id}, approver={user_id}")
            return jsonify({'success': True, 'message': 'Document approved'})
        else:
            logger.warning(f"Document approval failed: chat_id={chat_id}, doc_id={document_id}")
            return jsonify({'success': False, 'error': 'Failed to approve document'}), 400
            
    except Exception as e:
        logger.error(f"Approve document failed: error={str(e)}")
        return jsonify({'success': False, 'error': 'Operation failed'}), 500

@document_bp.route('/chats/<chat_id>/documents/<document_id>/download', methods=['GET'])
@login_required
def download_document_api(chat_id, document_id):
    """Get download URL for approved documents only."""
    try:
        current_user = get_current_user()

        allowed, error_response = _verify_document_access(chat_id)
        if not allowed:
            return error_response
        
        document = get_chat_document(chat_id, document_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Check approval status - solutions architects can access any document
        # SA reviewers can also access unapproved documents in their review copies
        # Users can always download their own uploaded files regardless of approval status
        chat = get_chat_by_chat_id(chat_id)
        is_sa_review_copy = chat and chat.get('source_chat_id') and chat.get('user_id') == current_user.user_id
        is_user_uploaded = document.get('tool_name') == 'user_uploaded'
        
        if (not current_user.is_solutions_architect() and 
            not document.get('approved', False) and 
            not is_sa_review_copy and
            not is_user_uploaded):
            return jsonify({'success': False, 'error': 'Document not approved for download'}), 403
        
        # Generate CloudFront signed URL
        version_id = document.get('version_id')
        s3_key = document.get('s3_key')
        
        if s3_key and version_id:
            download_url = DocumentProcessor.get_cloudfront_signed_url_with_version(s3_key, version_id)
            return jsonify({
                'success': True,
                'download_url': download_url,
                'document_type': document.get('document_type'),
                'file_size': document.get('file_size')
            })
        else:
            return jsonify({'success': False, 'error': 'Document URL not available'}), 400
            
    except Exception as e:
        logger.error(f"Get download URL failed: error={str(e)}")
        return jsonify({'success': False, 'error': 'Operation failed'}), 500

