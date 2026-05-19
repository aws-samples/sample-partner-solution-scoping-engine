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
Routes for handling persona-related operations.
"""
import logging
from flask import Blueprint, jsonify, request, make_response
from ..config.personas import PersonaManager
from ..middleware.auth_middleware import login_required

logger = logging.getLogger(__name__)

persona_bp = Blueprint('persona_bp', __name__)
persona_manager = PersonaManager()

@persona_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer."""
    try:
        logger.debug("Health check request received")
        return make_response(jsonify({"status": "healthy"}), 200)
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return make_response(jsonify({"status": "unhealthy", "error": "Health check failed"}), 500)

@persona_bp.route('/personas', methods=['GET'])
@login_required
def get_personas():
    """Get available assistant and customer personas."""
    try:
        # logger.debug("Received GET request for /personas")
        # logger.debug(f"Request headers: {dict(request.headers)}")
        # logger.debug(f"Request args: {request.args}")
        # logger.debug(f"Request cookies: {request.cookies}")
        
        # Get current authenticated user
        from ..middleware.auth_middleware import get_current_user
        current_user = get_current_user()
        
        if current_user:
            user_groups = current_user.groups
        else:
            user_groups = ["sera_sales_person"]  # Default group for unauthenticated access
        
        logger.debug("Fetching accessible assistant personas")
        assistant_personas = persona_manager.get_accessible_assistant_personas(user_groups)
        logger.debug(f"Found {len(assistant_personas)} assistant personas")
        
        logger.debug("Fetching customer personas")
        customer_personas = persona_manager.get_all_customer_personas()
        logger.debug(f"Found {len(customer_personas)} customer personas")
        
        # Filter active personas
        active_assistant_personas = {
            pid: persona for pid, persona in assistant_personas.items()
            if persona.active == 'YES'
        }
        active_customer_personas = {
            pid: persona for pid, persona in customer_personas.items()
            if persona.active == 'YES'
        }
        
        logger.debug(f"Found {len(active_assistant_personas)} active assistant personas")
        logger.debug(f"Found {len(active_customer_personas)} active customer personas")
        
        personas = {
            'assistants': [
                {
                    'label': persona.name,
                    'value': pid,
                    'description': persona.short_description,
                    'enabled': persona.active == 'YES'
                }
                for pid, persona in active_assistant_personas.items()
            ],
            'customers': [
                {
                    'label': persona.name,
                    'value': pid,
                    'description': persona.short_description,
                    'enabled': persona.active == 'YES'
                }
                for pid, persona in active_customer_personas.items()
            ]
        }
        
        logger.debug("Preparing response")
        response = make_response(jsonify(personas))
        response.headers['Content-Type'] = 'application/json'
        # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:7001'
        # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
        # response.headers['Access-Control-Allow-Origin'] = 'https://your-domain.com'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
        
        # Manually set a test cookie to verify cookie functionality
        response.set_cookie('test_cookie', 'test_value', httponly=False, secure=False, samesite='Lax')
        
        logger.debug("Sending response")
        return response
    except Exception as e:
        logger.error(f"Error fetching personas: {e}", exc_info=True)
        error_response = make_response(jsonify({"error": "Failed to fetch personas"}), 500)
        error_response.headers['Content-Type'] = 'application/json'
        # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
        error_response.headers['Access-Control-Allow-Origin'] = 'http://localhost:7001'
        # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
        # error_response.headers['Access-Control-Allow-Origin'] = 'https://your-domain.com'
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        error_response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization' 
        return error_response 