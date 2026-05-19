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
SA Review model for managing Solutions Architect chat reviews and copying.
"""

import logging
import uuid
import boto3
import json
from datetime import datetime
from typing import Dict, Optional
from .chat import get_chat_by_chat_id, save_chat, save_chat_message, update_chat_review_status, update_chat_field, list_chats_for_user, get_chat_documents, update_chat_document
from ..services.chat_service import add_system_message_to_chat
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)

def bulk_copy_s3_folder_with_versions(original_chat_id: str, sa_copy_chat_id: str) -> Dict:
    """
    Copy entire S3 folder from original chat to SA copy, preserving version IDs where possible.
    
    Args:
        original_chat_id (str): Source chat ID
        sa_copy_chat_id (str): Destination chat ID
        
    Returns:
        Dict: Copy results with counts, errors, and version ID mapping
    """
    import time
    start_time = time.time()
    
    try:
        s3_client = boto3.client('s3', region_name=CustomerConfig.get_aws_region())
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        logger.info(f"S3_COPY_START: source={original_chat_id}, dest={sa_copy_chat_id}, bucket={bucket_name}")
        
        # List all objects in the original chat folder
        paginator = s3_client.get_paginator('list_object_versions')
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=f"{original_chat_id}/")
        
        copied_count = 0
        error_count = 0
        version_mapping = {}  # old_key -> {old_version_id: new_version_id}
        files_to_copy = []
        
        # Collect all files first
        for page in page_iterator:
            for obj in page.get('Versions', []):
                files_to_copy.append(obj)
        
        logger.info(f"S3_COPY_FILES_FOUND: count={len(files_to_copy)}")
        
        for obj in files_to_copy:
            try:
                original_key = obj['Key']
                new_key = original_key.replace(original_chat_id, sa_copy_chat_id, 1)
                old_version_id = obj.get('VersionId')
                file_size = obj.get('Size', 0)
                
                logger.debug(f"S3_COPY_FILE: key={original_key[len(original_chat_id)+1:][:50]}..., size={file_size}, old_ver={old_version_id}")
                
                # Copy with specific version ID
                copy_source = {
                    'Bucket': bucket_name, 
                    'Key': original_key,
                    'VersionId': old_version_id
                }
                
                response = s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=bucket_name,
                    Key=new_key,
                    ServerSideEncryption='AES256'
                )
                
                new_version_id = response.get('VersionId')
                
                # Track version mapping
                if original_key not in version_mapping:
                    version_mapping[original_key] = {}
                version_mapping[original_key][old_version_id] = new_version_id
                
                copied_count += 1
                logger.debug(f"S3_COPY_SUCCESS: new_key={new_key[len(sa_copy_chat_id)+1:][:50]}..., new_ver={new_version_id}")
                
            except Exception as e:
                logger.error(f"S3_COPY_FAILED: key={original_key[:50]}..., error={str(e)}")
                error_count += 1
        
        elapsed = time.time() - start_time
        logger.info(f"S3_COPY_COMPLETE: copied={copied_count}, errors={error_count}, elapsed={elapsed:.2f}s")
        
        return {
            'copied_count': copied_count,
            'error_count': error_count,
            'version_mapping': version_mapping,
            'status': 'success' if error_count == 0 else 'partial_success'
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"S3_COPY_EXCEPTION: error={str(e)}, elapsed={elapsed:.2f}s")
        return {'status': 'failed', 'error': str(e)}

def copy_chat_for_sa_review(original_chat_id: str, sa_user_id: str) -> Dict:
    """
    Create a copy of a chat for SA review purposes.
    
    This function:
    1. Gets the original chat data
    2. Creates a new chat ID for the SA copy
    3. Copies all chat data (messages, metadata, stage, variables, artifacts)
    4. Links the copy to the original chat
    5. Updates the original chat's SA review status
    
    Args:
        original_chat_id (str): The ID of the original chat to copy
        sa_user_id (str): The SA user ID who is creating the review
        
    Returns:
        Dict: The SA copy chat data
        
    Raises:
        ValueError: If original chat not found
        Exception: If copy creation fails
    """
    try:
        # Get the original chat
        original_chat = get_chat_by_chat_id(original_chat_id)
        
        if not original_chat:
            raise ValueError(f"Original chat {original_chat_id} not found")
        
        # Generate new chat ID for SA copy
        sa_copy_chat_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()
        
        logger.debug(f"Creating SA copy {sa_copy_chat_id} from original {original_chat_id} by SA {sa_user_id}")
        
        # Create SA copy with all original data
        sa_copy_data = {
            'chat_id': sa_copy_chat_id,
            'user_id': sa_user_id,  # SA becomes the owner of the copy
            'timestamp': current_time,
            
            # Copy all original chat metadata
            'assistant_persona': original_chat.get('assistant_persona', ''),
            'customer_persona': original_chat.get('customer_persona', ''),
            'interaction_method': original_chat.get('interaction_method', ''),
            'stage': original_chat.get('stage', 'INITIAL'),
            'chat_name': f"review: {original_chat.get('chat_name', f'Chat {original_chat_id}')}",
            
            # Copy timestamps
            'created_at': current_time,
            'updated_at': current_time,
            
            # SA Review specific fields
            'source_chat_id': original_chat_id,  # Link back to original
            'review_status': 'in_progress',
            'sa_reviewer': sa_user_id,
            'sa_review_started': current_time,
            'sa_last_activity': current_time,
            
            # Copy chat variables if they exist
            'chat_variables': original_chat.get('chat_variables', {}),
            
            # Copy documents/artifacts if they exist - ensure proper format
            'documents': original_chat.get('documents', {}),
            
            # Copy approvals if they exist
            'approvals': original_chat.get('approvals', []),
        }
        
        # Copy message history
        original_messages = original_chat.get('messages', [])
        logger.debug(f"Copying {len(original_messages)} messages from original chat")
        
        # Save the SA copy first (without messages)
        sa_copy = save_chat(sa_copy_data)
        
        # Bulk copy all S3 files from original to SA copy folder
        logger.debug(f"Starting bulk S3 copy from {original_chat_id} to {sa_copy_chat_id}")
        copy_result = bulk_copy_s3_folder_with_versions(original_chat_id, sa_copy_chat_id)
        logger.info(f"Bulk S3 copy result: {copy_result}")
        version_mapping = copy_result.get('version_mapping', {})
        logger.debug(f"Version mapping extracted: {version_mapping}")
        
        # Copy message history from original to SA copy
        original_messages = original_chat.get('messages', [])
        
        # Update documents metadata with new version IDs
        logger.info(f"DOC_UPDATE_START: doc_count={len(sa_copy_data.get('documents', {}))}, has_version_map={bool(version_mapping)}")
        
        if sa_copy_data.get('documents') and version_mapping:
            updated_docs = 0
            for doc_id, doc_data in sa_copy_data['documents'].items():
                if 's3_key' in doc_data and 'version_id' in doc_data:
                    s3_key = doc_data['s3_key']
                    old_version_id = doc_data['version_id']
                    doc_type = doc_data.get('document_type', 'unknown')
                    
                    logger.debug(f"DOC_UPDATE: doc_id={doc_id}, type={doc_type}, old_key={s3_key[:50]}...")
                    
                    # Update S3 key and URL to point to SA copy folder
                    new_s3_key = s3_key.replace(original_chat_id, sa_copy_chat_id)
                    doc_data['s3_key'] = new_s3_key
                    
                    if 's3_url' in doc_data:
                        doc_data['s3_url'] = doc_data['s3_url'].replace(original_chat_id, sa_copy_chat_id)
                    
                    # Update version ID if mapping exists
                    if s3_key in version_mapping and old_version_id in version_mapping[s3_key]:
                        new_version_id = version_mapping[s3_key][old_version_id]
                        doc_data['version_id'] = new_version_id
                        updated_docs += 1
                        logger.debug(f"DOC_VERSION_UPDATED: doc_id={doc_id}, old_ver={old_version_id}, new_ver={new_version_id}")
                    else:
                        logger.warning(f"DOC_VERSION_MISSING: doc_id={doc_id}, key={s3_key[:50]}..., old_ver={old_version_id} not in mapping")
            
            logger.info(f"DOC_UPDATE_COMPLETE: updated={updated_docs}/{len(sa_copy_data['documents'])}")
            
            # Save the updated SA copy with corrected documents
            sa_copy = save_chat(sa_copy_data)
            logger.info(f"DOC_METADATA_SAVED: chat_id={sa_copy_chat_id}")
            
            # Log final document state for verification
            for doc_id, doc_data in sa_copy_data['documents'].items():
                logger.debug(f"FINAL_DOC_STATE: doc_id={doc_id}, type={doc_data.get('document_type')}, s3_key={doc_data.get('s3_key', 'N/A')[:50]}..., version={doc_data.get('version_id', 'N/A')}")
        
        logger.debug(f"Copying {len(original_messages)} messages from original chat")
        
        if original_messages:
            
            # Copy each message to the SA copy
            for msg in original_messages:
                try:
                    # Handle DynamoDB format (this is how messages are actually stored)
                    if isinstance(msg, dict) and 'M' in msg:
                        message_data = {
                            'message_id': msg['M'].get('message_id', {}).get('S', str(uuid.uuid4())),
                            'role': msg['M'].get('role', {}).get('S', 'user'),
                            'content': msg['M'].get('content', {}).get('S', ''),
                            'message_timestamp': msg['M'].get('message_timestamp', {}).get('S', current_time)
                        }
                        
                        # Update S3 URLs in content to use SA copy chat ID and new version IDs
                        if message_data['content']:
                            updated_content = message_data['content'].replace(original_chat_id, sa_copy_chat_id)
                            
                            # Replace version IDs in content - simple string replacement
                            for original_s3_key, version_map in version_mapping.items():
                                for old_version_id, new_version_id in version_map.items():
                                    old_version_param = f"?versionId={old_version_id}"
                                    new_version_param = f"?versionId={new_version_id}"
                                    if old_version_param in updated_content:
                                        updated_content = updated_content.replace(old_version_param, new_version_param)
                                        logger.debug(f"Replaced version ID in content: {old_version_id} -> {new_version_id}")
                            
                            message_data['content'] = updated_content
                            
                            if updated_content != msg['M'].get('content', {}).get('S', ''):
                                logger.debug(f"Updated S3 URLs and version IDs in message content for SA copy")
                        
                        # Copy files field if it exists and rewrite S3 keys
                        if 'files' in msg['M']:
                            files_list = []
                            for file_item in msg['M']['files']['L']:
                                if 'M' in file_item:
                                    file_data = {}
                                    for key, value in file_item['M'].items():
                                        if key == 's3_key' and 'S' in value:
                                            # Rewrite S3 key from original_chat_id to sa_copy_chat_id
                                            original_s3_key = value['S']
                                            new_s3_key = original_s3_key.replace(original_chat_id, sa_copy_chat_id)
                                            file_data[key] = new_s3_key
                                            logger.debug(f"Rewriting S3 key: {original_s3_key} -> {new_s3_key}")
                                        elif key == 'version_id' and 'S' in value:
                                            old_version_id = value['S']
                                            # Find new version ID from mapping
                                            if original_s3_key in version_mapping and old_version_id in version_mapping[original_s3_key]:
                                                new_version_id = version_mapping[original_s3_key][old_version_id]
                                                file_data[key] = new_version_id
                                                logger.debug(f"Updated version ID: {old_version_id} -> {new_version_id}")
                                            else:
                                                file_data[key] = old_version_id
                                                logger.warning(f"No version mapping found for {original_s3_key}:{old_version_id}")
                                        elif 's3_url' in key and 'S' in value:
                                            # Rewrite S3 URL as well
                                            original_s3_url = value['S']
                                            new_s3_url = original_s3_url.replace(original_chat_id, sa_copy_chat_id)
                                            file_data[key] = new_s3_url
                                        else:
                                            # Copy other file metadata as-is
                                            file_data[key] = value.get('S') if 'S' in value else value.get('N') if 'N' in value else str(value)
                                    files_list.append(file_data)
                            
                            if files_list:
                                message_data['files'] = files_list
                                logger.debug(f"Copied {len(files_list)} files for message {message_data['message_id']}")
                    else:
                        logger.warning(f"Unexpected message format: {type(msg)}")
                        continue
                    
                    # Save the message to the SA copy
                    save_chat_message(sa_user_id, sa_copy_chat_id, message_data)
                    logger.debug(f"Copied message {message_data['message_id']} to SA copy")
                    
                except Exception as e:
                    logger.error(f"Copy message failed: error={str(e)}")
                    continue
            
            logger.info(f"MSG_COPY_COMPLETE: copied={len(original_messages)} messages to chat_id={sa_copy_chat_id}")
        else:
            logger.debug("MSG_COPY_SKIP: no messages in original chat")
        
        # Update the original chat's SA review status
        logger.debug(f"REVIEW_STATUS_UPDATE: original_chat={original_chat_id}, status=in_progress, reviewer={sa_user_id}")
        update_chat_review_status(
            original_chat_id,
            status='in_progress',
            sa_reviewer=sa_user_id,
            sa_copy_chat_id=sa_copy_chat_id
        )
        
        # Add SA Review Started system message to both chats with same message ID
        shared_message_id = str(uuid.uuid4())
        start_message = f"Solutions Architect review started by {sa_user_id}!"
        
        # Add to original chat
        add_system_message_to_chat(original_chat_id, start_message, shared_message_id)
        # Add to SA copy with same message ID
        add_system_message_to_chat(sa_copy_chat_id, start_message, shared_message_id)
        
        logger.info(f"SA_COPY_SUCCESS: sa_copy={sa_copy_chat_id}, original={original_chat_id}, docs={len(sa_copy_data.get('documents', {}))}, msgs={len(original_messages)}")
        
        return sa_copy
        
    except Exception as e:
        logger.error(f"SA_COPY_FAILED: original={original_chat_id}, error={str(e)}", exc_info=True)
        raise

def get_sa_copy_for_original(original_chat_id: str, sa_user_id: str) -> Optional[Dict]:
    """
    Get the SA copy chat for a given original chat and SA user.
    Only returns active SA copies (not cancelled or merged).
    
    Args:
        original_chat_id (str): The original chat ID
        sa_user_id (str): The SA user ID
        
    Returns:
        Optional[Dict]: The SA copy chat data if found and active, None otherwise
    """
    try:
        # We need to find the SA copy by looking for chats owned by the SA
        # that have source_chat_id = original_chat_id
        # For now, we'll implement a simple approach
        # Note: Could be optimized with a GSI on source_chat_id
        
        # Get all chats for the SA
        sa_chats_response = list_chats_for_user(sa_user_id)
        sa_chats = sa_chats_response.get('chats', [])
        
        # Find the one that's a copy of the original chat and is still active
        for chat in sa_chats:
            if (chat.get('source_chat_id') == original_chat_id and 
                chat.get('review_status') in ['in_progress']):
                logger.debug(f"Found active SA copy {chat.get('chat_id')} for original {original_chat_id}")
                return chat
        
        logger.debug(f"No active SA copy found for original {original_chat_id} by SA {sa_user_id}")
        return None
        
    except Exception as e:
        logger.error(f"Find SA copy failed: original={original_chat_id}, error={str(e)}")
        return None

def _execute_sa_review_action(
    sa_copy_chat_id: str, 
    sa_user_id: str, 
    action_config: Dict,
    comment: str = '',
    document_ids: list = None
) -> Dict:
    """
    Common function to execute SA review actions with different configurations.
    
    Args:
        sa_copy_chat_id (str): The SA copy chat ID
        sa_user_id (str): The SA user ID
        action_config (Dict): Configuration for the specific action
        comment (str): Optional comment from SA
        
    Returns:
        Dict: Action result information
    """
    try:
        # Get the SA copy
        sa_copy = get_chat_by_chat_id(sa_copy_chat_id)
        
        if not sa_copy:
            raise ValueError(f"SA copy {sa_copy_chat_id} not found")
        
        if sa_copy.get('user_id') != sa_user_id:
            raise ValueError(f"SA copy {sa_copy_chat_id} not owned by {sa_user_id}")
        
        # Check valid statuses for this action
        current_status = sa_copy.get('review_status')
        valid_statuses = action_config.get('valid_from_statuses', ['in_progress'])
        if current_status not in valid_statuses:
            raise ValueError(f"SA copy {sa_copy_chat_id} cannot be {action_config['action_name']} (current status: {current_status})")
        
        original_chat_id = sa_copy.get('source_chat_id')
        if not original_chat_id:
            raise ValueError(f"SA copy {sa_copy_chat_id} has no source_chat_id")
        
        current_time = datetime.utcnow().isoformat()
        
        # Update SA copy status
        update_chat_field(sa_copy_chat_id, 'review_status', action_config['sa_copy_status'])
        update_chat_field(sa_copy_chat_id, 'sa_last_activity', current_time)
        
        # Update original chat status
        original_update_args = {
            'status': action_config['original_status']
        }
        if action_config.get('clear_sa_reviewer'):
            original_update_args['sa_reviewer'] = None
            original_update_args['sa_copy_chat_id'] = None
        elif action_config.get('set_sa_reviewer'):
            original_update_args['sa_reviewer'] = sa_user_id
            
        update_chat_review_status(original_chat_id, **original_update_args)
        
        logger.info(f"SA review {sa_copy_chat_id} {action_config['action_name']} by {sa_user_id}")
        
        # Send notification if configured
        if action_config.get('send_notification'):
            logger.info(f"Attempting to send notification for SA review action: {action_config['action_name']}")
            try:
                from ..services.notification_service import NotificationService
                original_chat = get_chat_by_chat_id(original_chat_id)
                if original_chat:
                    user_email = original_chat.get('user_id')
                    # Validate email format
                    if '@' not in user_email or not user_email.endswith('.com'):
                        logger.warning(f"Invalid email format for user_id '{user_email}', skipping notification")
                    else:
                        logger.info(f"Sending review ready notification to {user_email} for chat {original_chat_id}")
                        NotificationService.send_review_ready_notification(
                            chat_id=original_chat_id,
                            chat_name=original_chat.get('chat_name', f'Chat {original_chat_id}'),
                            user_email=user_email,
                            sa_email=sa_user_id
                        )
                        logger.info(f"Successfully sent notification for SA review {action_config['action_name']}")
                else:
                    logger.warning(f"Original chat {original_chat_id} not found, cannot send notification")
            except Exception as e:
                logger.error(f"Failed to send notification for SA review {action_config['action_name']}: {e}", exc_info=True)
        
        # Add system message to both chats
        shared_message_id = str(uuid.uuid4())
        system_message = action_config['system_message_template'].format(sa_user_id=sa_user_id)
        if comment:
            system_message += f"\nComment: {comment}"
        
        # Add approved documents list if this is marking ready for merge or completing as-is
        if action_config.get('action_name') in ['marked_ready', 'completed'] and document_ids and len(document_ids) > 0:
            approval_id = str(uuid.uuid4())
            doc_links = []
            
            # Get chat key for atomic updates using the sa_copy already fetched at top of function
            # Use primary key directly - no GSI eventual consistency issues
            sa_key = {
                'user_id': {'S': sa_copy['user_id']},
                'timestamp': {'S': sa_copy['timestamp']}
            }
            
            from ..services.db_service import ddb_update_item, ddb_get_item
            
            # Do a strongly consistent get_item on the main table to get document metadata
            raw_item = ddb_get_item(sa_key)
            all_documents = {}
            if raw_item and 'documents' in raw_item:
                for doc_id_key, doc_data_raw in raw_item['documents']['M'].items():
                    d = {}
                    for k, v in doc_data_raw['M'].items():
                        if 'S' in v: d[k] = v['S']
                        elif 'N' in v: d[k] = float(v['N']) if '.' in v['N'] else int(v['N'])
                        elif 'BOOL' in v: d[k] = v['BOOL']
                        elif 'NULL' in v: d[k] = None
                    all_documents[doc_id_key] = d
            
            logger.info(f"APPROVE_START: document_ids={document_ids}, all_documents_keys={list(all_documents.keys())}")
            for doc_id in document_ids:
                logger.info(f"APPROVE_DOC: attempting doc_id={doc_id}")
                result = ddb_update_item(
                    key=sa_key,
                    update_expression='SET documents.#did.approved = :t, documents.#did.approved_by = :by, documents.#did.approved_timestamp = :ts, documents.#did.approval_id = :aid',
                    expression_attribute_values={
                        ':t': {'BOOL': True},
                        ':by': {'S': sa_user_id},
                        ':ts': {'S': current_time},
                        ':aid': {'S': approval_id}
                    },
                    expression_attribute_names={'#did': doc_id}
                )
                logger.info(f"APPROVE_DOC: doc_id={doc_id}, update_result={result}")
                
                # Build display name for system message
                doc_data = all_documents.get(doc_id, {})
                doc_type = doc_data.get('document_type', 'unknown')
                filename = doc_data.get('original_filename')
                if not filename:
                    s3_key = doc_data.get('s3_key', '')
                    if s3_key:
                        filename = s3_key.split('/')[-1]
                        if '.' in filename:
                            filename = filename.rsplit('.', 1)[0]
                
                display_names = {
                    'cloudformation_template': f"CFN: {filename}" if filename else 'CloudFormation Template',
                    'sow_document': 'SOW Document',
                    'diagram': 'Architecture Diagram',
                    'pricing_report': 'Pricing Report',
                    'funding_document': 'Funding Document',
                    'calculator_link': 'Calculator Link',
                }
                doc_links.append(display_names.get(doc_type, filename or doc_type))
            
            if doc_links:
                system_message += f"\n\nApproved documents:\n\n" + "\n\n".join(doc_links)
                
                # Append approval record atomically
                ddb_update_item(
                    key=sa_key,
                    update_expression='SET approvals = list_append(if_not_exists(approvals, :empty_list), :approval)',
                    expression_attribute_values={
                        ':empty_list': {'L': []},
                        ':approval': {'L': [{'M': {
                            'approval_id': {'S': approval_id},
                            'approved_by': {'S': sa_user_id},
                            'approved_timestamp': {'S': current_time},
                            'document_ids': {'L': [{'S': doc_id} for doc_id in document_ids]},
                            'action_type': {'S': action_config.get('action_name')},
                            'comment': {'S': comment}
                        }}]}
                    }
                )
        
        add_system_message_to_chat(original_chat_id, system_message, shared_message_id)
        add_system_message_to_chat(sa_copy_chat_id, system_message, shared_message_id)
        
        return {
            'sa_copy_chat_id': sa_copy_chat_id,
            'original_chat_id': original_chat_id,
            'status': action_config['sa_copy_status'],
            f"{action_config['action_name']}_at": current_time
        }
        
    except Exception as e:
        logger.error(f"Error executing SA review action {action_config['action_name']}: {e}", exc_info=True)
        raise

def mark_review_ready_for_user(sa_copy_chat_id: str, sa_user_id: str, comment: str = '', document_ids: list = None) -> Dict:
    """Mark an SA review as ready for the user to review and merge."""
    return _execute_sa_review_action(sa_copy_chat_id, sa_user_id, {
        'action_name': 'marked_ready',
        'sa_copy_status': 'ready_for_user',
        'original_status': 'ready_for_merge',
        'set_sa_reviewer': True,
        'send_notification': True,
        'system_message_template': 'Solutions Architect review ended. Changes ready for merge by {sa_user_id}'
    }, comment, document_ids)

def approve_documents_in_original_chat(original_chat_id: str, document_ids: list, approved_by: str, comment: str = '') -> Dict:
    """Approve specific documents in the original chat."""
    try:
        if not document_ids:
            return {'status': 'no_documents'}
        
        approved_count = 0
        current_time = datetime.utcnow().isoformat()
        approval_id = str(uuid.uuid4())
        
        # Get chat key for atomic updates
        original_chat = get_chat_by_chat_id(original_chat_id)
        if not original_chat or 'documents' not in original_chat:
            return {'status': 'no_documents'}
        
        chat_key = {
            'user_id': {'S': original_chat['user_id']},
            'timestamp': {'S': original_chat['timestamp']}
        }
        
        from ..services.db_service import ddb_update_item
        
        for doc_id in document_ids:
            if doc_id in original_chat['documents']:
                # Atomic update - no read-modify-write race
                ddb_update_item(
                    key=chat_key,
                    update_expression='SET documents.#did.approved = :t, documents.#did.approved_by = :by, documents.#did.approved_timestamp = :ts, documents.#did.approval_id = :aid',
                    expression_attribute_values={
                        ':t': {'BOOL': True},
                        ':by': {'S': approved_by},
                        ':ts': {'S': current_time},
                        ':aid': {'S': approval_id}
                    },
                    expression_attribute_names={'#did': doc_id}
                )
                approved_count += 1
                logger.info(f"Approved document {doc_id} in original chat")
        
        # Add approval record atomically
        if approved_count > 0:
            ddb_update_item(
                key=chat_key,
                update_expression='SET approvals = list_append(if_not_exists(approvals, :empty_list), :approval)',
                expression_attribute_values={
                    ':empty_list': {'L': []},
                    ':approval': {'L': [{'M': {
                        'approval_id': {'S': approval_id},
                        'approved_by': {'S': approved_by},
                        'approved_timestamp': {'S': current_time},
                        'document_ids': {'L': [{'S': doc_id} for doc_id in document_ids]},
                        'action_type': {'S': 'completed'},
                        'comment': {'S': comment}
                    }}]}
                }
            )
        
        return {
            'status': 'success',
            'approved_documents': approved_count,
            'approval_id': approval_id
        }
        
    except Exception as e:
        logger.error(f"Approve docs in original failed: error={str(e)}")
        return {'status': 'error', 'error': str(e)}

def complete_review_no_changes(sa_copy_chat_id: str, sa_user_id: str, comment: str = '', document_ids: list = None) -> Dict:
    """Complete an SA review with no changes needed - solution is approved as-is."""
    logger.info(f"complete_review_no_changes called with document_ids: {document_ids}")
    result = _execute_sa_review_action(sa_copy_chat_id, sa_user_id, {
        'action_name': 'completed',
        'sa_copy_status': 'complete_no_changes',
        'original_status': 'complete_no_changes',
        'set_sa_reviewer': True,
        'send_notification': True,
        'system_message_template': 'Solutions Architect review ended. Approved as-is by {sa_user_id}'
    }, comment, document_ids)
    
    # Approve the same documents in the original chat
    if result.get('original_chat_id') and document_ids:
        try:
            logger.info(f"Approving documents {document_ids} in original chat: {result['original_chat_id']}")
            approval_result = approve_documents_in_original_chat(
                result['original_chat_id'], 
                document_ids, 
                sa_user_id,
                comment
            )
            logger.info(f"Document approval result: {approval_result}")
        except Exception as e:
            logger.error(f"Approve docs failed: error={str(e)}")
    
    return result

def reassign_sa_review(sa_copy_chat_id: str, sa_user_id: str, comment: str = '') -> Dict:
    """Reassign an SA review back to requested status for another SA to pick up."""
    return _execute_sa_review_action(sa_copy_chat_id, sa_user_id, {
        'action_name': 'reassigned',
        'sa_copy_status': 'reassigned',
        'original_status': 'requested',
        'clear_sa_reviewer': True,
        'send_notification': True,
        'system_message_template': 'Solutions Architect review ended. Reassigned by {sa_user_id}'
    }, comment)

def reject_sa_review(sa_copy_chat_id: str, sa_user_id: str, comment: str = '') -> Dict:
    """Reject an SA review and set status to rejected."""
    return _execute_sa_review_action(sa_copy_chat_id, sa_user_id, {
        'action_name': 'rejected',
        'sa_copy_status': 'rejected',
        'original_status': 'rejected',
        'valid_from_statuses': ['in_progress', 'ready_for_user'],
        'send_notification': True,
        'system_message_template': 'Solutions Architect review ended. Rejected by {sa_user_id}'
    }, comment)

def get_user_notification_status(user_id: str, chat_id: str) -> Dict:
    """
    Check if a user has pending SA review notifications for a specific chat.
    
    Args:
        user_id (str): The user ID
        chat_id (str): The chat ID to check
        
    Returns:
        Dict: Notification status information
    """
    try:
        # Get the chat to check SA review status
        chat = get_chat_by_chat_id(chat_id)
        
        if not chat:
            return {'status': 'chat_not_found'}
        
        # Check if this is an SA copy - if so, don't show notifications
        if chat.get('source_chat_id'):
            return {'status': 'not_owner'}
        
        # Only show notifications for chats owned by this user
        if chat.get('user_id') != user_id:
            return {'status': 'not_owner'}
        
        review_status = chat.get('review_status', 'none')
        
        # Check if there's a pending notification
        if review_status == 'ready_for_merge':
            sa_reviewer = chat.get('sa_reviewer', 'Unknown SA')
            return {
                'status': 'ready_for_merge',
                'notification_type': 'changes_ready',
                'sa_reviewer': sa_reviewer,
                'sa_copy_chat_id': chat.get('sa_copy_chat_id'),
                'sa_review_completed': chat.get('sa_review_completed'),
                'message': f"Your solutions architect ({sa_reviewer}) has reviewed this chat and suggested improvements."
            }
        elif review_status == 'complete_no_changes':
            sa_reviewer = chat.get('sa_reviewer', 'Unknown SA')
            return {
                'status': 'complete_no_changes',
                'notification_type': 'approved_as_is',
                'sa_reviewer': sa_reviewer,
                'sa_review_completed': chat.get('sa_review_completed'),
                'message': f"Your solutions architect ({sa_reviewer}) has reviewed this chat and approved the solution."
            }
        else:
            return {'status': 'no_notification'}
        
    except Exception as e:
        logger.error(f"Get notification status failed: user={user_id}, chat={chat_id}, error={str(e)}")
        return {'status': 'error', 'error': str(e)}

def merge_sa_changes_to_original(original_chat_id: str, user_id: str) -> Dict:
    """
    Merge SA changes from the SA copy back to the original chat.
    
    Args:
        original_chat_id (str): The original chat ID
        user_id (str): The user ID (must be chat owner)
        
    Returns:
        Dict: Merge result information
        
    Raises:
        ValueError: If validation fails
    """
    try:
        # Get the original chat first
        original_chat = get_chat_by_chat_id(original_chat_id)
        if not original_chat:
            raise ValueError(f"Original chat {original_chat_id} not found")
        
        # Get SA copy chat ID from original chat
        sa_copy_chat_id = original_chat.get('sa_copy_chat_id')
        if not sa_copy_chat_id:
            raise ValueError(f"No SA copy found for chat {original_chat_id}")
        
        # Get the SA copy
        sa_copy = get_chat_by_chat_id(sa_copy_chat_id)
        if not sa_copy:
            raise ValueError(f"SA copy {sa_copy_chat_id} not found")
        
        if not original_chat:
            raise ValueError(f"Original chat {original_chat_id} not found")
        
        # Verify user owns the chat
        if original_chat.get('user_id') != user_id:
            raise ValueError(f"User {user_id} does not own chat {original_chat_id}")
        
        # Verify chat is ready for merge
        if original_chat.get('review_status') != 'ready_for_merge':
            raise ValueError(f"Chat {original_chat_id} is not ready for merge (status: {original_chat.get('review_status')})")
        
        current_time = datetime.utcnow().isoformat()
        
        # Merge logic: SA copy takes precedence, add original messages only if not in copy
        original_messages = original_chat.get('messages', [])
        sa_copy_messages = sa_copy.get('messages', [])
        
        # Create set of SA copy message IDs
        sa_copy_message_ids = set()
        for msg in sa_copy_messages:
            if isinstance(msg, dict) and 'M' in msg:
                msg_id = msg['M'].get('message_id', {}).get('S')
                if msg_id:
                    sa_copy_message_ids.add(msg_id)
        
        # Collect original messages that don't exist in SA copy
        unique_original_messages = []
        for msg in original_messages:
            if isinstance(msg, dict) and 'M' in msg:
                msg_id = msg['M'].get('message_id', {}).get('S')
                if msg_id and msg_id not in sa_copy_message_ids:
                    unique_original_messages.append(msg)
        
        # Initialize S3 client and bucket for document copying
        s3_client = boto3.client('s3')
        bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
        
        # Add new SA messages individually 
        original_message_ids = set()
        for msg in original_messages:
            if isinstance(msg, dict) and 'M' in msg:
                msg_id = msg['M'].get('message_id', {}).get('S')
                if msg_id:
                    original_message_ids.add(msg_id)
        
        # Get SA review start time for filtering new files
        sa_review_start_time = sa_copy.get('sa_review_started')
        if not sa_review_start_time:
            logger.warning("No SA review start time found, will copy all files")
            sa_review_start_time = "1970-01-01T00:00:00.000000"  # Fallback to copy all
        
        logger.debug(f"SA review started at: {sa_review_start_time}")
        
        # Convert to datetime for comparison
        sa_start_dt = datetime.fromisoformat(sa_review_start_time.replace('Z', '+00:00'))
        
        # Track version mappings for files copied during merge
        merge_version_mapping = {}
        documents_merged = 0
        
        # Get SA copy documents early for reference checking
        sa_copy_documents = sa_copy.get('documents', {})
        
        # Merge documents FIRST to build version mapping
        original_documents = original_chat.get('documents', {})
        
        if sa_copy_documents:
            documents_merged = 0
            for doc_id, doc_data in sa_copy_documents.items():
                # Check if document is new (not in original chat)
                if doc_id not in original_documents:
                    # Copy S3 file to original chat prefix
                    old_s3_key = doc_data.get('s3_key')
                    if old_s3_key and sa_copy_chat_id in old_s3_key:
                        new_s3_key = old_s3_key.replace(sa_copy_chat_id, original_chat_id)
                        try:
                            # Copy file in S3 with same encryption as source
                            copy_response = s3_client.copy_object(
                                Bucket=bucket_name,
                                CopySource={'Bucket': bucket_name, 'Key': old_s3_key},
                                Key=new_s3_key,
                                ServerSideEncryption='AES256'
                            )
                            new_version_id = copy_response.get('VersionId')
                            
                            # Update document metadata
                            updated_doc_data = doc_data.copy()
                            updated_doc_data['s3_key'] = new_s3_key
                            updated_doc_data['s3_url'] = f"s3://{bucket_name}/{new_s3_key}"
                            updated_doc_data['version_id'] = new_version_id
                            # Track version mapping for content replacement
                            if old_s3_key not in merge_version_mapping:
                                merge_version_mapping[old_s3_key] = {}
                            old_version_id = doc_data.get('version_id')
                            merge_version_mapping[old_s3_key][old_version_id] = new_version_id
                            
                            # Add document to original chat
                            success = update_chat_document(original_chat_id, doc_id, updated_doc_data)
                            documents_merged += 1
                            
                            logger.info(f"Merged new document: {doc_id} from SA copy")
                        except Exception as e:
                            logger.error(f"Merge document failed: doc_id={doc_id}, error={str(e)}")
            
            if documents_merged > 0:
                logger.info(f"Merged {documents_merged} documents from SA copy")
        
        # Process SA copy messages for S3 key updates
        processed_sa_messages = []
        
        for msg in sa_copy_messages:
            message_data = {
                'message_id': msg['M'].get('message_id', {}).get('S', str(uuid.uuid4())),
                'role': msg['M'].get('role', {}).get('S', 'assistant'),
                'content': msg['M'].get('content', {}).get('S', ''),
                'message_timestamp': msg['M'].get('message_timestamp', {}).get('S', current_time)
            }
            
            # Update S3 URLs in message content
            if message_data['content']:
                updated_content = message_data['content'].replace(sa_copy_chat_id, original_chat_id)
                
                # Replace version IDs in content using merge mapping
                for s3_key, version_map in merge_version_mapping.items():
                    for old_version_id, new_version_id in version_map.items():
                        old_version_param = f"?versionId={old_version_id}"
                        new_version_param = f"?versionId={new_version_id}"
                        if old_version_param in updated_content:
                            updated_content = updated_content.replace(old_version_param, new_version_param)
                
                message_data['content'] = updated_content
            
            # Update the original message structure with the processed content
            updated_msg = msg.copy()
            updated_msg['M']['content']['S'] = message_data['content']
            processed_sa_messages.append(updated_msg)
        
        # STEP 2: Copy other files created during SA review
        try:
            # List all objects in SA copy chat folder
            sa_prefix = f"{sa_copy_chat_id}/"
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=sa_prefix)
            
            if 'Contents' in response:
                other_files_copied = 0
                for obj in response['Contents']:
                    s3_key = obj['Key']
                    last_modified = obj['LastModified'].replace(tzinfo=None)
                    
                    # Skip if it's a document we already processed
                    is_tracked_document = False
                    for doc_data in sa_copy_documents.values():
                        if doc_data.get('s3_key') == s3_key:
                            is_tracked_document = True
                            break
                    
                    # Copy if created during SA review and not already tracked
                    if not is_tracked_document and last_modified > sa_start_dt:
                        new_s3_key = s3_key.replace(sa_copy_chat_id, original_chat_id)
                        try:
                            s3_client.copy_object(
                                Bucket=bucket_name,
                                CopySource={'Bucket': bucket_name, 'Key': s3_key},
                                Key=new_s3_key,
                                MetadataDirective='COPY',
                                ServerSideEncryption='AES256'
                            )
                            other_files_copied += 1
                            logger.info(f"Copied other file: {s3_key} -> {new_s3_key}")
                        except Exception as e:
                            logger.error(f"Copy file failed: key={s3_key[:50]}..., error={str(e)}")
                
                if other_files_copied > 0:
                    logger.info(f"Copied {other_files_copied} other files from SA copy")
        except Exception as e:
            logger.error(f"Copy other files failed: error={str(e)}")
        
        # STEP 3: Copy messages with updated S3 URLs and version IDs
        new_messages_count = 0
        for msg in sa_copy_messages:
            if isinstance(msg, dict) and 'M' in msg:
                msg_id = msg['M'].get('message_id', {}).get('S')
                if msg_id and msg_id not in original_message_ids:
                    # Convert and save new message
                    message_data = {
                        'message_id': msg_id,
                        'role': msg['M'].get('role', {}).get('S', 'user'),
                        'content': msg['M'].get('content', {}).get('S', ''),
                        'message_timestamp': msg['M'].get('message_timestamp', {}).get('S', current_time)
                    }
                    
                    save_chat_message(user_id, original_chat_id, message_data)
                    new_messages_count += 1
        
        logger.info(f"Added {new_messages_count} new messages from SA copy")
        logger.info(f"Merge version mapping: {merge_version_mapping}")
        
        # Update chat metadata if SA changed anything
        sa_copy_stage = sa_copy.get('stage')
        sa_copy_variables = sa_copy.get('chat_variables', {})
        
        logger.info(f"SA copy stage: {sa_copy_stage}, original stage: {original_chat.get('stage')}")
        logger.info(f"SA copy variables: {sa_copy_variables}")
        
        # Update original chat with SA changes
        
        if sa_copy_stage and sa_copy_stage != original_chat.get('stage'):
            update_chat_field(original_chat_id, 'stage', sa_copy_stage)
            logger.debug(f"Updated original chat stage to {sa_copy_stage}")
        
        # Merge chat variables if changed
        if sa_copy_variables and sa_copy_variables != original_chat.get('chat_variables', {}):
            update_chat_field(original_chat_id, 'chat_variables', sa_copy_variables)
            logger.debug(f"Updated chat variables from SA copy")
        
        
        # Approve only documents that were approved during SA review
        approved_docs = []
        
        if sa_copy_documents:
            approval_id = str(uuid.uuid4())
            
            for doc_id, doc_data in sa_copy_documents.items():
                # Only approve documents that were marked as approved in the SA copy
                if doc_data.get('approved', False):
                    # Document should already be merged - just add approval metadata
                    try:
                        # Get the already merged document from original chat
                        original_chat_updated = get_chat_by_chat_id(original_chat_id)
                        if original_chat_updated and 'documents' in original_chat_updated:
                            existing_doc = original_chat_updated['documents'].get(doc_id)
                            if existing_doc:
                                # Add approval metadata without changing s3_key, s3_url, or version_id
                                existing_doc['approved'] = True
                                existing_doc['approved_by'] = doc_data.get('approved_by')
                                existing_doc['approved_timestamp'] = doc_data.get('approved_timestamp')
                                existing_doc['approval_id'] = approval_id
                                
                                # Update the document with approval metadata only
                                update_chat_document(original_chat_id, doc_id, existing_doc)
                                
                                approved_docs.append({
                                    'type': existing_doc.get('document_type', 'unknown'),
                                    'url': existing_doc.get('s3_url', ''),
                                    'name': existing_doc.get('original_filename', f"{existing_doc.get('document_type', 'unknown')}.file")
                                })
                                
                                logger.info(f"Approved document: {doc_id}")
                    except Exception as e:
                        logger.error(f"Approve document failed: doc_id={doc_id}, error={str(e)}")
            
            if approved_docs:
                logger.info(f"Approved {len(approved_docs)} documents during merge")
        
        # Merge approvals from SA copy to original chat
        sa_copy_approvals = sa_copy.get('approvals', [])
        if sa_copy_approvals:
            logger.info(f"Merging {len(sa_copy_approvals)} approvals from SA copy to original chat")
            from ..services.db_service import ddb_update_item
            
            # Get original chat data for the update
            original_chat_updated = get_chat_by_chat_id(original_chat_id)
            if original_chat_updated:
                # Convert approvals to DynamoDB format
                approvals_ddb_format = []
                for approval in sa_copy_approvals:
                    approval_item = {'M': {}}
                    for key, value in approval.items():
                        if isinstance(value, str):
                            approval_item['M'][key] = {'S': value}
                        elif isinstance(value, list):
                            approval_item['M'][key] = {'L': [{'S': item} for item in value]}
                    approvals_ddb_format.append(approval_item)
                
                # Update original chat with approvals
                ddb_update_item(
                    key={
                        'user_id': {'S': original_chat_updated['user_id']},
                        'timestamp': {'S': original_chat_updated['timestamp']}
                    },
                    update_expression='SET approvals = :approvals',
                    expression_attribute_values={
                        ':approvals': {'L': approvals_ddb_format}
                    }
                )
                logger.info(f"Successfully merged {len(sa_copy_approvals)} approvals to original chat")
        
        # Update SA review status to merged
        update_chat_review_status(
            original_chat_id,
            status='merged',
            sa_reviewer=original_chat.get('sa_reviewer')
        )
        
        # Update SA copy status
        update_chat_field(sa_copy_chat_id, 'review_status', 'merged')
        
        logger.info(f"Successfully merged SA changes from {sa_copy_chat_id} to {original_chat_id}")
        
        return {
            'original_chat_id': original_chat_id,
            'sa_copy_chat_id': sa_copy_chat_id,
            'messages_merged': new_messages_count,
            'documents_merged': documents_merged,
            'documents_approved': len(approved_docs) if 'approved_docs' in locals() else 0,
            'approval_id': approval_id if 'approval_id' in locals() else None,
            'merged_at': current_time,
            'status': 'merged'
        }
        
    except Exception as e:
        logger.error(f"Error merging SA changes: {e}", exc_info=True)
        raise

def dismiss_sa_notification(chat_id: str, user_id: str) -> Dict:
    """
    Dismiss an SA review notification without merging changes.
    Works for both original chat owners and SA reviewers on their copies.
    
    Args:
        chat_id (str): The chat ID (original or SA copy)
        user_id (str): The user ID
        
    Returns:
        Dict: Dismissal result information
        
    Raises:
        ValueError: If validation fails
    """
    try:
        # Get the chat
        chat = get_chat_by_chat_id(chat_id)
        
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Check if this is an SA copy chat
        if chat.get('source_chat_id'):
            # This is an SA copy - verify SA owns it
            if chat.get('user_id') != user_id:
                raise ValueError(f"User {user_id} does not own SA copy {chat_id}")
            
            # For SA copy, just update the copy status
            update_chat_field(chat_id, 'review_status', 'dismissed')
            
            return {
                'sa_copy_chat_id': chat_id,
                'dismissed_at': datetime.utcnow().isoformat(),
                'status': 'dismissed'
            }
        else:
            # This is an original chat - verify user owns it
            if chat.get('user_id') != user_id:
                raise ValueError(f"User {user_id} does not own chat {chat_id}")
            
            # Verify there's a notification to dismiss
            review_status = chat.get('review_status', 'none')
            if review_status not in ['ready_for_merge', 'complete_no_changes']:
                raise ValueError(f"No SA notification to dismiss for chat {chat_id}")
            
            current_time = datetime.utcnow().isoformat()
            
            # Only change status to dismissed if it's ready_for_merge
            # For complete_no_changes, keep the status as is (already completed)
            if review_status == 'ready_for_merge':
                # Update original chat status to dismissed
                update_chat_review_status(chat_id, status='dismissed')
                
                # Update SA copy status if it exists
                sa_copy_chat_id = chat.get('sa_copy_chat_id')
                if sa_copy_chat_id:
                    update_chat_field(sa_copy_chat_id, 'review_status', 'dismissed')
                
                final_status = 'dismissed'
            else:
                # For complete_no_changes, just acknowledge dismissal without changing status
                final_status = review_status
            
            logger.info(f"SA notification dismissed for chat {chat_id} by user {user_id}")
            
            return {
                'original_chat_id': chat_id,
                'dismissed_at': current_time,
                'status': final_status
            }
        
    except Exception as e:
        logger.error(f"Error dismissing SA notification: {e}", exc_info=True)
        raise
