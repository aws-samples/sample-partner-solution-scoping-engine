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
Routes for the Solution Architect Review page.
"""
import logging
from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import sa_only, get_current_user

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/reviews', methods=['GET'])
@sa_only
def get_chats_for_review():
    """Gets chats in SOLUTION_PROPOSED or SOLUTION_FINALIZED state for review."""
    logger.debug("Fetching chats for SA review.")
    # Return empty list or not implemented message until properly implemented
    return jsonify({"message": "This endpoint is not yet implemented", "chats": []}), 501

@admin_bp.route('/reviews/<chat_id>/feedback', methods=['POST'])
@sa_only
def submit_feedback(chat_id):
    """Allows an SA to submit feedback (approve/reject) for a chat/solution."""
    current_user = get_current_user()
    
    data = request.json
    feedback_type = data.get('feedback_type') # e.g., "approved" or "rejected"
    comments = data.get('comments') # Optional comments, especially if rejected
    reviewer_id = current_user.user_id
    
    logger.debug(f"Submitting feedback: chat_id={chat_id}, reviewer={reviewer_id}, type={feedback_type}")
    if feedback_type not in ["approved", "rejected"]:
        logger.warning(f"Invalid feedback type: type={feedback_type}, chat_id={chat_id}")
        return jsonify({"error": "Invalid feedback type"}), 400

    if feedback_type == "rejected" and not comments:
        logger.warning(f"Rejection without comments: chat_id={chat_id}, reviewer={reviewer_id}")
        # Depending on requirements, you might enforce comments for rejection
        # return jsonify({"error": "Comments are required for rejection"}), 400

    # Not yet implemented:
    # 1. Validate the chat_id and its current stage.
    # 2. Store the feedback (e.g., update chat metadata in DynamoDB).
    # 3. Potentially trigger notifications.
    # success = admin_service.submit_chat_feedback(chat_id, reviewer_id, feedback_type, comments)
    success = True # Placeholder

    if success:
        logger.info(f"Feedback submitted: chat_id={chat_id}, reviewer={reviewer_id}, type={feedback_type}")
        return jsonify({"message": "Feedback submitted"}), 200
    else:
        # Handle potential errors (e.g., chat not found, already reviewed, DB error)
        logger.error(f"Submit feedback failed: chat_id={chat_id}, reviewer={reviewer_id}")
        return jsonify({"error": "Failed to submit feedback"}), 500 