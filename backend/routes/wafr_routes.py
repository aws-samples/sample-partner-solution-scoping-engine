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
WAFR (AWS Well-Architected Framework) specific routes.
Provides backend endpoints for WAFR MCP server integration.
"""

import logging
from flask import Blueprint, request, jsonify
from backend.middleware.auth_middleware import login_required, get_current_user
from backend.services.bedrock_service import BedrockService
from backend.config.app_config import CustomerConfig
from backend.models.chat import get_chat_by_chat_id
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# Create WAFR blueprint
wafr_bp = Blueprint('wafr', __name__, url_prefix='/api/wafr')

def get_bedrock_service():
    """Get configured BedrockService instance."""
    try:
        # Get Bedrock configuration
        model_id = CustomerConfig.get_bedrock_model_id()
        region = CustomerConfig.get_aws_region()
        
        # Create Bedrock client with retry configuration
        retry_config = CustomerConfig.get_bedrock_retry_config()
        config = Config(
            region_name=region,
            retries={
                'max_attempts': retry_config.get('max_retries', 30),
                'mode': 'adaptive'
            }
        )
        
        # Use AWS profile if configured
        use_profile = CustomerConfig.get_value('BEDROCK_USE_PROFILE', False)
        if use_profile:
            profile_name = CustomerConfig.get_bedrock_aws_profile()
            session = boto3.Session(profile_name=profile_name)
            client = session.client('bedrock-runtime', config=config)
        else:
            client = boto3.client('bedrock-runtime', config=config)
        
        return BedrockService(client, model_id)
        
    except Exception as e:
        logger.error(f"BedrockService init failed: error={str(e)}")
        raise

@wafr_bp.route('/enhance-report-content', methods=['POST'])
@login_required
def enhance_report_content():
    """
    Enhance WAFR report content using Claude.
    
    This endpoint provides enhanced content generation for WAFR reports
    while preserving the accuracy of the original chat responses.
    """
    try:
        current_user = get_current_user()
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'No JSON data provided'
            }), 400
        
        # Validate required parameters
        chat_id = data.get('chat_id')
        assessment_results = data.get('assessment_results')
        architecture_data = data.get('architecture_data', {})
        
        if not chat_id:
            return jsonify({
                'status': 'error',
                'error': 'chat_id is required'
            }), 400
        
        if not assessment_results:
            return jsonify({
                'status': 'error',
                'error': 'assessment_results is required'
            }), 400
        
        # Validate user can access the chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({'status': 'error', 'error': 'Chat not found'}), 404
        
        if not current_user.can_access_chat(chat['user_id']):
            return jsonify({'status': 'error', 'error': 'Access denied'}), 403
        
        logger.info(f"🎨 Processing WAFR report content enhancement for chat_id: {chat_id}")
        
        # Get BedrockService instance
        bedrock_service = get_bedrock_service()
        
        # Generate enhanced report content
        import asyncio
        result = asyncio.run(bedrock_service.wafr_generate_report_content(
            chat_id=chat_id,
            assessment_results=assessment_results,
            architecture_data=architecture_data
        ))
        
        logger.info(f"✅ WAFR report content enhancement completed for chat_id: {chat_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"WAFR enhancement failed: error={str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to enhance WAFR report content'
        }), 500

@wafr_bp.route('/wafr/health', methods=['GET'])
@login_required
def wafr_health():
    """Health check endpoint for WAFR services."""
    try:
        # Test BedrockService initialization
        bedrock_service = get_bedrock_service()
        
        return jsonify({
            'status': 'healthy',
            'service': 'wafr-backend',
            'bedrock_model': bedrock_service.model_id,
            'capabilities': [
                'report_content_enhancement',
                'claude_integration',
                'assessment_preservation'
            ]
        })
        
    except Exception as e:
        logger.error(f"WAFR health check failed: error={str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500