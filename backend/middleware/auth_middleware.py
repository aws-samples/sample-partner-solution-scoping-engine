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
Authentication middleware and decorators for route protection.
"""
import logging
from functools import wraps
from typing import List, Union, Optional
from flask import session, request, jsonify, redirect, url_for, current_app
from ..services.auth_service import get_auth_service
from ..models.user import User

logger = logging.getLogger(__name__)


VALID_ROLES = [
    'sera_sales_person', 'sera_sales_manager',
    'sera_solutions_architect', 'sera_sa_manager', 'sera_cross_customer_solutions_architect'
]


def login_required(f):
    """
    Decorator that requires user to be authenticated and have at least one valid role.
    
    Returns 401 if not authenticated, 403 if no valid role assigned.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_service = get_auth_service()
        
        if not auth_service.is_authenticated():
            logger.warning(f"Unauthenticated access attempt to {request.endpoint}")
            
            # For API requests, return JSON error
            if request.is_json or request.headers.get('Accept', '').startswith('application/json'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401
            
            # For web requests, redirect to login
            return redirect(url_for('auth_bp.auth'))
        
        # Check that user has at least one valid role
        current_user = auth_service.get_current_user()
        if current_user and not current_user.has_any_role(VALID_ROLES):
            logger.warning(f"No valid role for user {current_user.user_id} accessing {request.endpoint}. Groups: {current_user.groups}")
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Your account has not been assigned a role. Please contact your administrator.'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def role_required(required_roles: Union[str, List[str]]):
    """
    Decorator that requires user to have specific role(s).
    
    Args:
        required_roles: Single role string or list of roles (user needs ANY of them)
    
    Returns 403 if user doesn't have required role.
    """
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    def decorator(f):
        @wraps(f)
        @login_required  # Also requires authentication
        def decorated_function(*args, **kwargs):
            auth_service = get_auth_service()
            current_user = auth_service.get_current_user()
            
            if not current_user:
                logger.error("User should be authenticated but current_user is None")
                return jsonify({'error': 'Authentication error'}), 401
            
            if not current_user.has_any_role(required_roles):
                logger.warning(f"Access denied for user {current_user.user_id} to {request.endpoint}. "
                             f"Required roles: {required_roles}, User roles: {current_user.groups}")
                
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'You need one of these roles: {", ".join(required_roles)}'
                }), 403
            
            # Log successful authorization for security audit
            logger.info(f"Access granted: user={current_user.user_id}, endpoint={request.endpoint}, roles={current_user.groups}")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def sales_only(f):
    """Decorator for sales person only routes."""
    return role_required(['sera_sales_person', 'sera_sales_manager'])(f)


def sa_only(f):
    """Decorator for solutions architect only routes."""
    return role_required(['sera_solutions_architect', 'sera_sa_manager', 'sera_cross_customer_solutions_architect'])(f)


def sa_manager_only(f):
    """Decorator for SA manager only routes."""
    return role_required(['sera_sa_manager'])(f)


def sow_reviewer(f):
    """Decorator for SOW review capable users."""
    return role_required(['sera_solutions_architect', 'sera_sa_manager'])(f)


def get_current_user() -> Optional[User]:
    """
    Utility function to get the current authenticated user.
    
    Returns:
        User object if authenticated, None if not authenticated
        
    Raises:
        Exception: If there's an error with the authentication service
    """
    auth_service = get_auth_service()
    return auth_service.get_current_user()


def require_ownership_or_sa(resource_user_id_func):
    """
    Decorator that requires user to either own the resource or be a solutions architect.
    
    Args:
        resource_user_id_func: Function that extracts the user_id from request parameters
                               e.g., lambda: kwargs.get('user_id') or request.args.get('user_id')
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            if not current_user:
                return jsonify({'error': 'Authentication error'}), 401
            
            # Solutions architects can access resources from sellers they support
            if current_user.is_solutions_architect():
                return f(*args, **kwargs)
            
            # Otherwise, check ownership
            try:
                resource_user_id = resource_user_id_func(*args, **kwargs)
                
                if resource_user_id and current_user.user_id != resource_user_id:
                    logger.warning(f"Access denied: User {current_user.user_id} tried to access "
                                 f"resource owned by {resource_user_id}")
                    return jsonify({
                        'error': 'Access denied',
                        'message': 'You can only access your own resources'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error checking resource ownership: {e}", exc_info=True)
                return jsonify({'error': 'Access control error'}), 500
        
        return decorated_function
    return decorator


class AuthMiddleware:
    """Authentication middleware class for Flask app."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the auth middleware with Flask app."""
        app.before_request(self.before_request)
        app.teardown_appcontext(self.teardown)
    
    def before_request(self):
        """Process request before routing to check authentication for protected routes."""
        # Skip auth checks for auth-related endpoints
        if request.endpoint in ['auth_bp.auth', 'auth_bp.callback', 'auth_bp.logout', 'auth_bp.status']:
            return
        
        # Skip auth checks for health checks
        if request.endpoint in ['persona_bp.health_check']:
            return
        
        # Skip auth checks for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return
        
        # For now, we'll let individual routes handle authentication
        # This allows for gradual migration
        pass
    
    def teardown(self, exception):
        """Clean up after request."""
        pass