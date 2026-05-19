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
SA Review routes for handling Solutions Architect review workflow.
"""

import logging
from flask import Blueprint, request, jsonify
from ..services.notification_service import NotificationService
from ..config.app_config import CustomerConfig
from ..middleware.auth_middleware import login_required, get_current_user
from ..models.sa_review import (
    get_user_notification_status,
    merge_sa_changes_to_original,
    dismiss_sa_notification,
    mark_review_ready_for_user,
    complete_review_no_changes,
    reassign_sa_review,
    reject_sa_review
)

logger = logging.getLogger(__name__)

# Create blueprint for SA review routes
sa_review_bp = Blueprint('sa_review', __name__)

def _verify_sa_review_access(chat_id):
    """Verify the current user is the SA reviewer for this chat, the chat owner, or an SA with a support relationship."""
    from ..models.chat import get_chat_by_chat_id
    from ..models.support_relationship import user_supports_seller
    current_user = get_current_user()
    chat = get_chat_by_chat_id(chat_id)
    if not chat:
        return False
    if chat.get('user_id') == current_user.user_id:
        return True
    if chat.get('sa_reviewer') == current_user.user_id:
        return True
    if current_user.is_solutions_architect():
        if user_supports_seller(current_user.user_id, chat.get('user_id', '')):
            return True
    return False

@sa_review_bp.route('/sa-review/preview-approval/<chat_id>', methods=['GET'])
@login_required
def preview_approval_documents(chat_id):
    """Get list of documents that will be approved when completing SA review (ready for user or approve as-is)."""
    
    try:
        current_user = get_current_user()
        
        if not _verify_sa_review_access(chat_id):
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        # Get all documents from the SA copy chat
        from ..models.chat import get_chat_documents
        all_documents = get_chat_documents(chat_id)
        
        if not all_documents:
            return jsonify({
                'success': True,
                'documents': []
            })
        
        # Group documents by type and filename, find latest of each
        doc_groups = {}
        for doc_id, doc_data in all_documents.items():
            doc_type = doc_data.get('document_type', 'unknown')
            
            # Extract filename from S3 key if original_filename is null
            filename = doc_data.get('original_filename')
            if not filename:
                s3_key = doc_data.get('s3_key', '')
                if s3_key:
                    filename = s3_key.split('/')[-1]  # Get last part after /
            
            # Remove file extension for grouping
            if filename and '.' in filename:
                filename_no_ext = filename.rsplit('.', 1)[0]
            else:
                filename_no_ext = filename
            
            created_time = doc_data.get('created_timestamp')
            
            if created_time:
                # For CloudFormation templates, group by filename; for others, group by type
                if doc_type == 'cloudformation_template':
                    group_key = f"{doc_type}_{filename_no_ext}"
                else:
                    group_key = doc_type
                
                if group_key not in doc_groups or created_time > doc_groups[group_key]['created_timestamp']:
                    doc_groups[group_key] = {
                        'doc_id': doc_id,
                        'doc_data': doc_data,
                        'created_timestamp': created_time
                    }
        
        # Format documents for frontend modal as document references
        documents_to_approve = []
        for group_key, doc_info in doc_groups.items():
            doc_data = doc_info['doc_data']
            doc_id = doc_info['doc_id']
            
            # Extract filename from S3 key if original_filename is null
            filename = doc_data.get('original_filename')
            if not filename:
                s3_key = doc_data.get('s3_key', '')
                if s3_key:
                    filename = s3_key.split('/')[-1]  # Get last part after /
                    if '.' in filename:
                        filename = filename.rsplit('.', 1)[0]
            
            # Use proper display name logic
            doc_type = doc_data.get('document_type', 'unknown')
            if doc_type == 'cloudformation_template':
                display_name = f"CFN: {filename}" if filename else 'CloudFormation Template'
            elif doc_type == 'sow_document':
                display_name = 'SOW Document'
            elif doc_type == 'diagram':
                display_name = 'Architecture Diagram'
            elif doc_type == 'pricing_report':
                display_name = 'Pricing Report'
            elif doc_type == 'funding_document':
                display_name = 'Funding Document'
            else:
                display_name = filename or doc_type
            
            # Create document reference
            from ..models.chat import create_document_reference_for_message
            doc_reference = create_document_reference_for_message(doc_id, display_name)
            
            documents_to_approve.append({
                'doc_id': doc_id,
                'type': doc_type,
                'name': filename,
                'display_name': display_name,
                'reference': doc_reference,
                'created_timestamp': doc_data.get('created_timestamp'),
                'file_size': doc_data.get('file_size', 0)
            })
        
        return jsonify({
            'success': True,
            'documents': documents_to_approve,
            'count': len(documents_to_approve)
        })
        
    except Exception as e:
        logger.error(f"Error getting approval preview for chat {chat_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/notification/<chat_id>', methods=['GET'])
@login_required
def get_notification_status(chat_id):
    """Get SA review notification status for a specific chat."""
    
    try:
        current_user = get_current_user()
        
        if not _verify_sa_review_access(chat_id):
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        # Get notification status
        notification_status = get_user_notification_status(current_user.user_id, chat_id)
        
        return jsonify({
            'success': True,
            'chat_id': chat_id,
            'notification': notification_status
        })
        
    except Exception as e:
        logger.error(f"Error getting notification status for chat {chat_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/merge', methods=['POST'])
@login_required
def merge_sa_changes():
    """Merge SA changes from SA copy to original chat."""
    
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        chat_id = data.get('chat_id')
        if not chat_id:
            return jsonify({
                'success': False,
                'error': 'chat_id is required'
            }), 400
        
        # Merge SA changes
        merge_result = merge_sa_changes_to_original(chat_id, current_user.user_id)
        
        return jsonify({
            'success': True,
            'merge_result': merge_result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error merging SA changes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/dismiss', methods=['POST'])
@login_required
def dismiss_notification():
    """Dismiss SA review notification without merging changes."""
    
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        chat_id = data.get('chat_id')
        if not chat_id:
            return jsonify({
                'success': False,
                'error': 'chat_id is required'
            }), 400
        
        # Dismiss notification
        dismiss_result = dismiss_sa_notification(chat_id, current_user.user_id)
        
        return jsonify({
            'success': True,
            'dismiss_result': dismiss_result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error dismissing SA notification: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/start/<original_chat_id>', methods=['POST'])
@login_required
def start_sa_review(original_chat_id):
    """Start SA review by creating a copy and returning the copy chat ID."""
    
    try:
        current_user = get_current_user()
        logger.info(f"Starting SA review for chat {original_chat_id} by user {current_user.user_id}")
        
        # Verify user is an SA with support relationship to chat owner
        if not current_user.is_solutions_architect():
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        from ..models.chat import get_chat_by_chat_id
        original_chat = get_chat_by_chat_id(original_chat_id)
        if not original_chat:
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        from ..models.support_relationship import user_supports_seller
        if not user_supports_seller(current_user.user_id, original_chat.get('user_id', '')):
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        # Check if SA copy already exists
        from ..models.sa_review import get_sa_copy_for_original, copy_chat_for_sa_review
        
        existing_copy = get_sa_copy_for_original(original_chat_id, current_user.user_id)
        
        if existing_copy:
            logger.info(f"Found existing SA copy {existing_copy['chat_id']} for original {original_chat_id}")
            # Return existing copy
            return jsonify({
                'success': True,
                'sa_copy_chat_id': existing_copy['chat_id'],
                'original_chat_id': original_chat_id,
                'action': 'existing_copy'
            })
        
        # Create new SA copy
        logger.info(f"Creating new SA copy for original {original_chat_id}")
        sa_copy = copy_chat_for_sa_review(original_chat_id, current_user.user_id)
        logger.info(f"Successfully created SA copy {sa_copy['chat_id']} for original {original_chat_id}")
        
        return jsonify({
            'success': True,
            'sa_copy_chat_id': sa_copy['chat_id'],
            'original_chat_id': original_chat_id,
            'action': 'new_copy'
        })
        
    except ValueError as e:
        logger.error(f"Start SA review validation failed: original={original_chat_id}, error={str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error starting SA review for {original_chat_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/cancel-request', methods=['POST'])
@login_required
def cancel_sa_review_request():
    """Cancel a pending SA review request."""
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        comment = data.get('comment', '').strip()
        
        if not chat_id:
            return jsonify({'success': False, 'error': 'Chat ID is required'}), 400
        
        # Sanitize comment to prevent stored XSS
        if comment:
            from markupsafe import escape
            comment = str(escape(comment))[:2000]
        
        # Get the chat and verify ownership
        from ..models.chat import get_chat_by_chat_id
        from ..services.db_service import ddb_update_item
        from datetime import datetime
        
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
            
        # Verify user owns this chat
        if chat['user_id'] != current_user.user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            
        # Allow cancelling if status is 'requested' or 'in_progress'
        review_status = chat.get('review_status')
        if review_status not in ['requested', 'in_progress']:
            return jsonify({'success': False, 'error': 'Cannot cancel - review not in requested or in_progress status'}), 400
        
        # Set the review_status to 'cancelled'
        ddb_update_item(
            key={
                'user_id': {'S': chat['user_id']},
                'timestamp': {'S': chat['timestamp']}
            },
            update_expression='SET review_status = :status, updated_at = :updated_at',
            expression_attribute_values={
                ':status': {'S': 'cancelled'},
                ':updated_at': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Add system message to chat
        from ..services.chat_service import add_system_message_to_chat
        
        if review_status == 'in_progress':
            # If review was in progress, add "Solutions Architect Review ended" message
            system_message = f"Solutions Architect review ended. Cancelled by {current_user.user_id}"
            if comment:
                system_message += f"\nComment: {comment}"
        else:
            # If review was just requested, add regular cancel message
            system_message = "Review request cancelled"
            if comment:
                system_message += f" - Comment: {comment}"
                
        add_system_message_to_chat(chat_id, system_message)
        
        logger.info(f"SA review request cancelled for chat {chat_id} by user {current_user.user_id}")
        
        return jsonify({
            'success': True,
            'system_message': system_message,
            'chat_id': chat_id,
            'message': 'Review request cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling SA review request: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@sa_review_bp.route('/sa-review/request', methods=['POST'])
@login_required
def request_sa_review():
    """Request SA review for a chat (sets status to 'requested')."""
    
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        chat_id = data.get('chat_id')
        comment = data.get('comment', '').strip()
        
        if not chat_id:
            return jsonify({
                'success': False,
                'error': 'chat_id is required'
            }), 400
        
        # Sanitize comment to prevent stored XSS
        if comment:
            from markupsafe import escape
            comment = str(escape(comment))[:2000]
        
        # Update chat status to requested using db service
        from ..services.db_service import ddb_update_item
        from ..models.chat import get_chat_by_chat_id
        from datetime import datetime
        
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
        
        # Verify the current user owns this chat
        if chat.get('user_id') != current_user.user_id:
            return jsonify({'success': False, 'error': 'Chat not found'}), 404
            
        # Update only the review_status field
        ddb_update_item(
            key={
                'user_id': {'S': chat['user_id']},
                'timestamp': {'S': chat['timestamp']}
            },
            update_expression='SET review_status = :status, updated_at = :updated_at',
            expression_attribute_values={
                ':status': {'S': 'requested'},
                ':updated_at': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        # Add system message to chat
        from ..services.chat_service import add_system_message_to_chat
        system_message = "Review requested from Solutions Architect"
        if comment:
            system_message += f" - Comment: {comment}"
        add_system_message_to_chat(chat_id, system_message)
        
        logger.info(f"SA review requested for chat {chat_id} by user {current_user.user_id}")
        
        # Send notification to assigned SA reviewers
        try:
            from ..models.support_relationship import get_support_team
            support_team = get_support_team(current_user.user_id)
            assigned_sas = [member['support_member_id'] for member in support_team]
            
            if assigned_sas:
                NotificationService.send_sa_review_notification(
                    chat_id=chat_id,
                    chat_name=chat.get('chat_name', f'Chat {chat_id}'),
                    user_email=current_user.user_id,
                    sa_emails=assigned_sas
                )
        except Exception as e:
            logger.error(f"Send SA notification failed: error={str(e)}")
        
        return jsonify({
            'success': True,
            'system_message': system_message,
            'chat_id': chat_id,
            'status': 'requested'
        })
        
    except Exception as e:
        logger.error(f"Error requesting SA review for chat: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sa_review_bp.route('/sa-review/actions', methods=['POST'])
@login_required
def sa_review_actions():
    """Handle SA review actions (mark ready, complete no changes, cancel)."""
    
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        action = data.get('action')
        sa_copy_chat_id = data.get('sa_copy_chat_id')
        
        if not action:
            return jsonify({
                'success': False,
                'error': 'action is required'
            }), 400
        
        if not sa_copy_chat_id:
            return jsonify({
                'success': False,
                'error': 'sa_copy_chat_id is required'
            }), 400
        
        # Get comment and document IDs from request data
        comment = data.get('comment', '').strip()
        document_ids = data.get('documentIds', [])
        
        # Sanitize comment to prevent stored XSS
        if comment:
            from markupsafe import escape
            comment = str(escape(comment))[:2000]
        
        # Execute the requested action
        if action == 'mark_ready':
            result = mark_review_ready_for_user(sa_copy_chat_id, current_user.user_id, comment, document_ids)
        elif action == 'complete_no_changes':
            result = complete_review_no_changes(sa_copy_chat_id, current_user.user_id, comment, document_ids)
        elif action == 'reject':
            result = reject_sa_review(sa_copy_chat_id, current_user.user_id, comment)
        elif action == 'reassign':
            result = reassign_sa_review(sa_copy_chat_id, current_user.user_id, comment)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown action: {action}'
            }), 400
        
        return jsonify({
            'success': True,
            'action': action,
            'result': result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error executing SA review action: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
