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
Unified authentication service with pluggable providers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from flask import session, request, redirect, url_for
from ..models.user import User
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""
    
    @abstractmethod
    def get_login_url(self, **kwargs) -> str:
        """Get the URL to redirect to for login."""
        pass
    
    @abstractmethod
    def handle_callback(self, request_data: Dict) -> Optional[User]:
        """Handle the authentication callback and return user if successful."""
        pass
    
    @abstractmethod
    def get_logout_url(self, **kwargs) -> Optional[str]:
        """Get the URL to redirect to for logout (if IdP supports SLO)."""
        pass
    
    @abstractmethod
    def validate_token(self, token: str) -> Optional[User]:
        """Validate a token and return user if valid."""
        pass


class AuthService:
    """Main authentication service that manages providers."""
    
    def __init__(self):
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize authentication providers based on configuration."""
        auth_type = CustomerConfig.get_auth_type()
        
        if auth_type in ['saml', 'both']:
            try:
                from .saml_provider import SAMLProvider
                self.providers['saml'] = SAMLProvider()
                logger.debug("SAML authentication provider initialized")
            except ImportError as e:
                logger.error(f"Failed to initialize SAML provider: {e}")
                logger.warning("SAML authentication will be unavailable. Consider installing xmlsec dependencies or using OAuth2.")
                # Continue without SAML if it fails
        
        if auth_type in ['oauth2', 'both']:
            try:
                from .oauth2_provider import OAuth2Provider
                self.providers['oauth2'] = OAuth2Provider()
                logger.debug("OAuth2 authentication provider initialized")
            except ImportError as e:
                logger.error(f"Failed to initialize OAuth2 provider: {e}")
                logger.warning("OAuth2 authentication will be unavailable.")
        
        if not self.providers:
            logger.error(f"No valid authentication providers could be initialized for auth_type: {auth_type}")
            
            # Only allow running without auth in development mode
            if CustomerConfig.is_development_mode():
                logger.warning("DEVELOPMENT MODE: Authentication will be disabled. App will run without authentication.")
                logger.warning("SECURITY WARNING: This should NEVER happen in production!")
            else:
                logger.critical("PRODUCTION MODE: Cannot run without authentication providers!")
                raise ValueError(f"Authentication provider initialization failed and production mode requires authentication")
    
    def get_provider(self, provider_name: str = None) -> Optional[AuthProvider]:
        """Get a specific provider or the default one."""
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name]
        
        # Return the first available provider as default
        if self.providers:
            return next(iter(self.providers.values()))
        
        logger.warning("No authentication providers available")
        return None
    
    def initiate_login(self, provider_name: str = None, **kwargs) -> str:
        """Initiate login with specified or default provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            logger.error("Cannot initiate login: no authentication providers available")
            return "/login?error=no_auth_provider"
        return provider.get_login_url(**kwargs)
    
    def handle_callback(self, provider_name: str = None, request_data: Dict = None) -> Tuple[bool, Optional[User], str]:
        """
        Handle authentication callback.
        
        Returns:
            Tuple of (success, user, error_message)
        """
        try:
            provider = self.get_provider(provider_name)
            user = provider.handle_callback(request_data or {})
            
            if user:
                self._create_session(user)
                logger.debug(f"User {user.user_id} authenticated successfully via {provider_name or 'default'}")
                return True, user, ""
            else:
                logger.warning(f"Authentication failed for provider {provider_name or 'default'}")
                return False, None, "Authentication failed"
                
        except Exception as e:
            logger.error(f"Error during authentication callback: {e}", exc_info=True)
            return False, None, f"Authentication error: {str(e)}"
    
    def logout(self, provider_name: str = None, **kwargs) -> Optional[str]:
        """
        Logout user and return IdP logout URL if available.
        
        Returns:
            Optional logout URL for IdP redirect
        """
        try:
            # Clear local session
            session.clear()
            logger.debug("Local session cleared")
            
            # Get IdP logout URL if supported
            provider = self.get_provider(provider_name)
            logout_url = provider.get_logout_url(**kwargs)
            
            return logout_url
            
        except Exception as e:
            logger.error(f"Error during logout: {e}", exc_info=True)
            return None
    
    def get_current_user(self) -> Optional[User]:
        """Get the currently authenticated user based on AUTH_MODE configuration."""
        try:
            auth_mode = CustomerConfig.get_value('AUTH_MODE', 'alb')
            
            if auth_mode == 'alb':
                # Production mode: ONLY accept ALB Cognito headers
                user = self._get_user_from_alb_headers()
                if user:
                    # Create/update session with ALB user data
                    self._create_session(user)
                    return user
                else:
                    logger.debug("ALB auth mode: No ALB headers found")
                    return None
            
            elif auth_mode == 'oauth2':
                # Development mode: Use backend OAuth2 session
                if 'user_data' in session:
                    return User.from_dict(session['user_data'])
                else:
                    logger.debug("OAuth2 auth mode: No session found")
                    return None
            
            else:
                logger.error(f"Invalid AUTH_MODE: {auth_mode}. Must be 'alb' or 'oauth2'")
                return None
            
            # In development mode with no providers, create/return test user session
            # Only if ENABLE_DEV_AUTH_BYPASS is explicitly set to True
            if not self.providers and CustomerConfig.is_development_mode() and CustomerConfig.get_value('ENABLE_DEV_AUTH_BYPASS', False):
                # Create test user session if it doesn't exist
                if 'dev_mode_user_created' not in session:
                    # Get test user configuration from config
                    test_user_config = CustomerConfig.get_dev_test_user_config()
                    test_user = User(
                        user_id=test_user_config['user_id'],
                        email=test_user_config['email'],
                        first_name=test_user_config['first_name'],
                        last_name=test_user_config['last_name'],
                        groups=test_user_config['groups']
                    )
                    self._create_session(test_user)
                    session['dev_mode_user_created'] = True
                    logger.debug("Development mode: created test_user session")
                    logger.warning("SECURITY WARNING: Authentication bypass is enabled!")
                
                return User.from_dict(session['user_data'])
            
            return None
        except Exception as e:
            logger.error(f"Error getting current user: {e}", exc_info=True)
            return None
    
    def is_authenticated(self) -> bool:
        """Check if current user is authenticated."""
        # If no providers are available and we're in development mode with explicit bypass enabled, allow access
        if not self.providers and CustomerConfig.is_development_mode() and CustomerConfig.get_value('ENABLE_DEV_AUTH_BYPASS', False):
            logger.debug("Development mode with explicit auth bypass: allowing access without authentication")
            return True
        
        return self.get_current_user() is not None
    
    def _create_session(self, user: User):
        """Create a session for the authenticated user."""
        session['user_data'] = user.to_dict()
        session['user_id'] = user.user_id
        session['user_email'] = user.email
        session['user_first_name'] = user.first_name
        session['group_membership'] = user.groups
        session.permanent = True
        
        logger.debug(f"Session created for user {user.user_id}")
    
    def _get_user_from_alb_headers(self) -> Optional[User]:
        """
        Extract user from ALB Cognito headers if present.
        
        Returns:
            User object if ALB headers are present and valid, None otherwise
        """
        try:
            from .alb_auth_provider import ALBAuthProvider
            alb_provider = ALBAuthProvider()
            
            # Check if request has ALB authentication headers
            if alb_provider.is_alb_authenticated_request(request.headers):
                user = alb_provider.get_user_from_headers(request.headers)
                if user:
                    logger.debug(f"User authenticated via ALB: {user.email[:30]}...")
                    return user
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting user from ALB headers: {str(e)[:50]}...", exc_info=True)
            return None


# Global auth service instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service