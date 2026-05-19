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
Routes for handling authentication.
"""
import logging
from flask import Blueprint, request, jsonify, redirect, url_for, session
from ..services.auth_service import get_auth_service
from ..middleware.auth_middleware import login_required, get_current_user
from ..models.user import User
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/auth', methods=['GET', 'POST'])
def auth():
    """Handle authentication initiation."""
    try:
        auth_service = get_auth_service()
        
        # Check if user is already authenticated
        if auth_service.is_authenticated():
            # Get return URL or default to home
            return_to = request.args.get('return_to', '/')
            
            # Validate that the return_to URL is safe (internal to the application)
            # It should either be a relative path starting with / or a URL to the same host
            from urllib.parse import urlparse, urljoin
            
            # Make sure return_to is a relative path or a URL to our domain
            if return_to.startswith('/') and not return_to.startswith('//'):
                # It's a relative path, make sure it doesn't contain protocol indicators
                if '://' not in return_to:
                    # URL encode the path to prevent any manipulation
                    from urllib.parse import quote
                    safe_return_to = quote(return_to)
                    return redirect(safe_return_to)
            
            # If we get here, the return_to URL is not safe, redirect to home
            logger.warning(f"Potentially unsafe redirect URL detected: {return_to}")
            return redirect('/')
        
        # Get provider from query parameter (saml or oauth2)
        provider = request.args.get('provider')
        
        # Initiate login with appropriate provider
        login_url = auth_service.initiate_login(provider_name=provider)
        
        logger.debug(f"Redirecting to authentication provider: {provider or 'default'}")
        return redirect(login_url)
        
    except Exception as e:
        logger.error(f"Error initiating authentication: {e}", exc_info=True)
        return jsonify({"error": "Authentication initiation failed"}), 500 

@auth_bp.route('/callback')
def callback():
    """Handles the callback from the Identity Provider."""
    try:
        auth_service = get_auth_service()
        
        # Get provider from query parameter
        provider = request.args.get('provider')
        logger.info(f"OAuth callback received: provider={provider}")
        logger.debug(f"Callback has {len(request.args)} parameters")
        
        # Handle the callback
        success, user, error_message = auth_service.handle_callback(
            provider_name=provider,
            request_data=request.args.to_dict()
        )
        
        if success and user:
            logger.info(f"User authenticated: user_id={user.user_id}, provider={provider}")
            
            # Redirect to frontend
            frontend_url = CustomerConfig.get_frontend_url()
            logger.debug(f"Redirecting to: {frontend_url[:50]}...")
            return redirect(frontend_url)
        else:
            logger.error(f"Auth callback failed: provider={provider}, error={str(error_message)[:50]}...")
            
            # Instead of showing JSON error, redirect back to login with error parameter
            return redirect(f'/api/auth?provider=oauth2&error=callback_failed&message={error_message}')
            
    except Exception as e:
        logger.error(f"Auth callback exception: provider={provider}, error={str(e)}", exc_info=True)
        
        # Redirect back to login instead of showing error page
        return redirect('/api/auth?provider=oauth2&error=exception')

@auth_bp.route('/logout')
def logout():
    """Logs the user out."""
    try:
        auth_service = get_auth_service()
        current_user = auth_service.get_current_user()
        
        if current_user:
            logger.debug(f"Logging out user: {current_user.user_id[:20]}...")
        
        # Clear session
        session.clear()
        
        # Check AUTH_MODE to determine logout flow
        auth_mode = CustomerConfig.get_value('AUTH_MODE', 'alb')
        
        if auth_mode == 'alb':
            # ALB Cognito authentication - clear ALB cookies and redirect to Cognito logout
            cognito_domain = CustomerConfig.get_value('COGNITO_DOMAIN')
            client_id = CustomerConfig.get_value('COGNITO_CLIENT_ID')
            frontend_url = CustomerConfig.get_frontend_url()
            
            # logout_uri must match configured LogoutURLs in Cognito (ends with /logged-out)
            logout_uri = f"{frontend_url}/logged-out"
            logout_url = f"https://{cognito_domain}/logout?client_id={client_id}&logout_uri={logout_uri}"
            
            # Create response with redirect to Cognito logout
            response = redirect(logout_url)
            
            # Clear ALB authentication session cookies by setting expiry to -1
            # ALB uses cookies named AWSELBAuthSessionCookie-0 through AWSELBAuthSessionCookie-3
            for i in range(4):
                cookie_name = f"AWSELBAuthSessionCookie-{i}"
                response.set_cookie(cookie_name, '', max_age=-1, expires=-1)
            
            logger.info(f"ALB auth mode: cleared ALB cookies and redirecting to Cognito logout")
            return response
        
        elif auth_mode == 'oauth2':
            # OAuth2 authentication - use provider logout
            provider = request.args.get('provider', 'oauth2')
            frontend_url = CustomerConfig.get_frontend_url()
            logout_redirect_uri = f"{frontend_url}/logged-out"
            logout_url = auth_service.logout(
                provider_name=provider,
                post_logout_redirect_uri=logout_redirect_uri
            )
            
            if logout_url:
                logger.debug(f"OAuth2 auth mode: redirecting to provider logout")
                return redirect(logout_url)
            else:
                logger.debug("OAuth2 auth mode: local logout completed")
                return jsonify({"message": "Logged out successfully"})
        
        else:
            logger.error(f"Invalid AUTH_MODE: {auth_mode}")
            return jsonify({"error": "Invalid authentication configuration"}), 500
            
    except Exception as e:
        logger.error(f"Error during logout: {str(e)[:50]}...", exc_info=True)
        return jsonify({"error": "Logout error"}), 500

@auth_bp.route('/auth/auth-status')
def auth_status():
    """Checks if the user is currently authenticated."""
    logger.info("AUTH_STATUS ROUTE CALLED - This should appear in logs if route is reached")
    try:
        auth_service = get_auth_service()
        current_user = auth_service.get_current_user()
        
        if current_user:
            logger.debug(f"Auth status check: User {current_user.user_id} is authenticated.")
            return jsonify({
                "authenticated": True,
                "user": {
                    "id": current_user.user_id,
                    "email": current_user.email,
                    "first_name": current_user.first_name,
                    "last_name": current_user.last_name,
                    "display_name": current_user.display_name,
                    "groups": current_user.groups,
                    "is_sales_person": current_user.is_sales_person(),
                    "is_solutions_architect": current_user.is_solutions_architect(),
                    "is_sa_manager": current_user.is_sa_manager(),
                    "can_review_sow": current_user.can_review_sow(),
                    "is_solutions_architect": current_user.is_solutions_architect()
                }
            })
        else:
            logger.debug("Auth status check: User is not authenticated.")
            return jsonify({"authenticated": False}), 401
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}", exc_info=True)
        return jsonify({"authenticated": False, "error": "Auth status check failed"}), 500

# @auth_bp.route('/test', methods=['GET'])
# def auth_test():
#     """Test route to check if auth blueprint routing works."""
#     logger.info("AUTH_TEST ROUTE CALLED - This should appear in logs if route is reached")
#     return jsonify({"message": "Auth blueprint test route works"})

@auth_bp.route('/user/is-sa', methods=['GET'])
@login_required
def is_solutions_architect():
    """Check if current user is a solutions architect."""
    try:
        current_user = get_current_user()
        return jsonify({
            'is_sa': current_user.is_solutions_architect()
        })
    except Exception as e:
        return jsonify({'is_sa': False}), 500 