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
SOW Review routes for Statement of Work document management and approval workflow.
"""
import logging
import boto3
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from botocore.exceptions import ClientError
import tempfile
import os

# Import SERA modules
from ..config.app_config import CustomerConfig
from ..models.chat import get_chat, list_chats_for_user, update_conversation_stage
from ..middleware.auth_middleware import sow_reviewer, get_current_user

logger = logging.getLogger(__name__)

sow_bp = Blueprint('sow_bp', __name__)


@sow_bp.route('/sow-reviews', methods=['GET'])
@sow_reviewer
def get_sows_for_review():
    """Gets chats with SOW documents in review state for approval."""
    logger.debug("Fetching SOWs for review.")
    
    try:
        # Get pagination parameters
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get user from session/auth context
        # user_id = get_current_user_id()  # Not yet implemented
        user_id = "admin_user"  # Placeholder
        
        # Query chats that have SOWs generated (look for SOW metadata instead of stages)
        all_chats_response = list_chats_for_user(user_id, limit=1000)  # Get all chats for user
        all_chats = all_chats_response.get('chats', [])
        
        sows = []
        for chat in all_chats:
            # Look for SOW metadata directly in chat item (stored by MCP server)
            sow_metadata = chat.get('sow_metadata', {})
            
            # Only include chats that have SOW documents generated
            if sow_metadata and sow_metadata.get('status') in ['generated', 'review', 'approved', 'rejected']:
                sow_data = {
                    "chat_id": chat['chatId'],
                    "chat_name": chat.get('chatName', f"Chat {chat['chatId'][:8]}"),
                    "customer_name": sow_metadata.get('customer_name', 'Unknown Customer'),
                    "project_title": sow_metadata.get('project_title', chat.get('chatName', 'AWS Project')),
                    "stage": f"SOW_{sow_metadata.get('status', 'generated').upper()}",
                    "created_by": chat.get('userId', 'Unknown User'),
                    "sow_generated_date": sow_metadata.get('generated_date', chat.get('lastModified', datetime.utcnow().isoformat())),
                    "estimated_project_cost": sow_metadata.get('estimated_cost', 0.0),
                    "template_type": sow_metadata.get('template_type', 'aws_map'),
                    "partner_name": sow_metadata.get('partner_name', CustomerConfig.get_sow_default_partner().get('name', 'ExamplePartner')),
                    "feedback": sow_metadata.get('feedback'),
                }
                
                # Build S3 URL using proper settings
                s3_settings = CustomerConfig.get_sow_s3_settings()
                s3_key = s3_settings['folder_structure'].format(chat_id=chat['chatId']) + s3_settings['file_name']
                sow_data["s3_url"] = f"s3://{CustomerConfig.get_sow_s3_bucket()}/{s3_key}"
                sow_data["review_required"] = True
                
                sows.append(sow_data)
        
        # Apply pagination
        total_count = len(sows)
        paginated_sows = sows[offset:offset + limit]
        
        response_data = {
            "sows": paginated_sows,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching SOWs for review: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch SOWs for review"}), 500


@sow_bp.route('/sow-reviews/<chat_id>/feedback', methods=['POST'])
@sow_reviewer
def submit_sow_feedback(chat_id):
    """Allows authorized users to submit feedback (approve/reject) for a SOW document."""
    current_user = get_current_user()
    
    data = request.json
    feedback_type = data.get('feedback_type') # e.g., "approved" or "rejected"
    comments = data.get('comments') # Optional comments, especially if rejected
    reviewer_id = current_user.user_id
    
    logger.debug(f"Submitting SOW feedback for chat {chat_id} by {reviewer_id}: {feedback_type}")
    
    # Validate input
    if feedback_type not in ["approved", "rejected"]:
        logger.warning("Invalid feedback type provided.")
        return jsonify({"error": "Invalid feedback type. Must be 'approved' or 'rejected'"}), 400

    if feedback_type == "rejected" and not comments:
        logger.warning("Rejection feedback submitted without comments.")
        return jsonify({"error": "Comments are required for rejection"}), 400

    try:
        # Check if user has permission to review SOWs
        # user_role = get_user_role(reviewer_id)  # Not yet implemented
        user_role = "sera_solutions_architect"  # Placeholder
        
        if not CustomerConfig.can_user_review_sow(user_role):
            return jsonify({"error": "Insufficient permissions to review SOWs"}), 403
        
        # Not yet implemented:
        # 1. Validate the chat_id and its current stage
        # 2. Store the feedback in DynamoDB chat metadata
        # 3. Update chat stage based on feedback
        # 4. Store SOW review history
        # 5. Trigger notifications if configured
        
        # Placeholder implementation
        review_data = {
            "chat_id": chat_id,
            "reviewer_id": reviewer_id,
            "feedback_type": feedback_type,
            "comments": comments,
            "review_timestamp": datetime.utcnow().isoformat(),
            "reviewer_role": user_role
        }
        
        # Update SOW metadata status instead of chat stage
        if feedback_type == "approved":
            new_sow_status = "approved"
        else:
            new_sow_status = "rejected"
            
        # TODO: Update SOW metadata in chat context
        # This should update the sow_metadata.status and add the review information
        # without changing the main conversation stage
        
        logger.info(f"SOW feedback submitted: chat_id={chat_id}, reviewer={reviewer_id}, type={feedback_type}, status={new_sow_status}")
        
        return jsonify({
            "message": "SOW feedback submitted successfully",
            "new_sow_status": new_sow_status,
            "review_data": review_data
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to submit SOW feedback for chat {chat_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to submit SOW feedback"}), 500


@sow_bp.route('/sow-reviews/<chat_id>/download', methods=['GET'])
@sow_reviewer
def download_sow(chat_id):
    """Download the SOW PDF document from S3."""
    try:
        # Get optional version parameter
        version_id = request.args.get('version_id')
        
        # Construct S3 key
        s3_settings = CustomerConfig.get_sow_s3_settings()
        s3_key = s3_settings['folder_structure'].format(chat_id=chat_id) + s3_settings['file_name']
        
        # Get S3 configuration
        s3_bucket = CustomerConfig.get_sow_s3_bucket()
        aws_region = CustomerConfig.get_aws_region()
        
        # Create S3 client
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # Prepare download parameters
        download_params = {
            'Bucket': s3_bucket,
            'Key': s3_key
        }
        
        if version_id:
            download_params['VersionId'] = version_id
            logger.debug(f"Downloading SOW version {version_id} for chat {chat_id}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
        
        try:
            # Download from S3
            s3_client.download_file(
                Bucket=s3_bucket,
                Key=s3_key,
                Filename=temp_path,
                ExtraArgs={"VersionId": version_id} if version_id else None
            )
            
            # Generate filename for download
            filename = f"SOW_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Return file for download
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                return jsonify({"error": f"SOW document not found for chat {chat_id}"}), 404
            elif error_code == 'NoSuchVersion':
                return jsonify({"error": f"SOW version {version_id} not found"}), 404
            else:
                logger.error(f"S3 download SOW failed: error={str(e)}")
                return jsonify({"error": "Failed to download SOW document"}), 500
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"Error downloading SOW for chat {chat_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to download SOW document"}), 500


@sow_bp.route('/sow-reviews/<chat_id>/versions', methods=['GET'])
@sow_reviewer
def get_sow_versions(chat_id):
    """Get all versions of a SOW document from S3."""
    try:
        # Get S3 configuration
        s3_bucket = CustomerConfig.get_sow_s3_bucket()
        aws_region = CustomerConfig.get_aws_region()
        
        # Construct S3 key
        s3_settings = CustomerConfig.get_sow_s3_settings()
        s3_key = s3_settings['folder_structure'].format(chat_id=chat_id) + s3_settings['file_name']
        
        # Create S3 client
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # List object versions
        response = s3_client.list_object_versions(
            Bucket=s3_bucket,
            Prefix=s3_key,
            MaxKeys=50
        )
        
        versions = []
        for version in response.get('Versions', []):
            if version['Key'] == s3_key:
                versions.append({
                    "version_id": version['VersionId'],
                    "last_modified": version['LastModified'].isoformat(),
                    "size": version['Size'],
                    "is_latest": version.get('IsLatest', False),
                    "download_url": f"/api/sow-reviews/{chat_id}/download?version_id={version['VersionId']}"
                })
        
        # Sort by last modified (newest first)
        versions.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return jsonify({
            "chat_id": chat_id,
            "s3_key": s3_key,
            "version_count": len(versions),
            "versions": versions
        })
        
    except ClientError as e:
        logger.error(f"S3 list SOW versions failed: error={str(e)}")
        return jsonify({"error": "Failed to list SOW versions"}), 500
    except Exception as e:
        logger.error(f"Error listing SOW versions for chat {chat_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to list SOW versions"}), 500


@sow_bp.route('/sow-reviews/<chat_id>/metadata', methods=['GET'])
@sow_reviewer
def get_sow_metadata(chat_id):
    """Get SOW generation metadata from S3."""
    try:
        # Get S3 configuration
        s3_bucket = CustomerConfig.get_sow_s3_bucket()
        aws_region = CustomerConfig.get_aws_region()
        
        # Construct metadata S3 key
        s3_settings = CustomerConfig.get_sow_s3_settings()
        metadata_key = s3_settings['folder_structure'].format(chat_id=chat_id) + s3_settings['metadata_file_name']
        
        # Create S3 client
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # Download metadata
        response = s3_client.get_object(Bucket=s3_bucket, Key=metadata_key)
        metadata_content = response['Body'].read().decode('utf-8')
        metadata = json.loads(metadata_content)
        
        return jsonify(metadata)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            return jsonify({"error": f"SOW metadata not found for chat {chat_id}"}), 404
        else:
            logger.error(f"S3 get SOW metadata failed: error={str(e)}")
            return jsonify({"error": "Failed to retrieve SOW metadata"}), 500
    except Exception as e:
        logger.error(f"Error getting SOW metadata for chat {chat_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOW metadata"}), 500


@sow_bp.route('/sow-reviews/stats', methods=['GET'])
@sow_reviewer
def get_sow_review_stats():
    """Get statistics about SOW reviews and document generation."""
    try:
        # TODO: Implement actual database queries
        # This is placeholder data
        stats = {
            "total_sows_generated": 45,
            "pending_review": 3,
            "approved_this_month": 12,
            "rejected_this_month": 2,
            "average_review_time_hours": 4.2,
            "templates_used": {
                "aws_map": 35,
                "aws_modernization": 7,
                "custom": 3
            },
            "top_reviewers": [
                {"name": "John Doe", "reviews_completed": 15},
                {"name": "Jane Smith", "reviews_completed": 12}
            ]
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting SOW review stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOW statistics"}), 500


@sow_bp.route('/sow-config', methods=['GET'])
@sow_reviewer
def get_sow_configuration():
    """Get SOW configuration for frontend components."""
    try:
        sow_config = CustomerConfig.get_sow_config()
        
        # Return relevant config for frontend
        frontend_config = {
            "enabled": CustomerConfig.is_sow_enabled(),
            "templates": CustomerConfig.get_sow_templates(),
            "labor_rates": CustomerConfig.get_sow_labor_rates(),
            "default_partner": CustomerConfig.get_sow_default_partner(),
            "review_settings": CustomerConfig.get_sow_review_settings(),
            "pdf_settings": CustomerConfig.get_sow_pdf_settings()
        }
        
        return jsonify(frontend_config)
        
    except Exception as e:
        logger.error(f"Error getting SOW configuration: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve SOW configuration"}), 500