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
OAuth2/OIDC authentication provider implementation.
"""
import logging
import secrets
import json
import base64
from typing import Dict, Optional
from urllib.parse import urlencode
import requests
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749.errors import OAuth2Error
from flask import request, session, url_for, current_app
from abc import ABC, abstractmethod
from ..models.user import User

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
from ..models.user import User
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)


class OAuth2Provider(AuthProvider):
    """OAuth2/OIDC authentication provider using authlib."""
    
    def __init__(self):
        self.oauth_config = self._load_oauth2_settings()
        self.group_mappings = CustomerConfig.get_value('OAUTH2_GROUP_MAPPINGS', {})
        self.oauth = OAuth(current_app) if current_app else OAuth()
        self.client = None
        self._setup_oauth_client()
    
    def _load_oauth2_settings(self) -> Dict:
        """Load OAuth2 settings from configuration."""
        # Check if OAuth2 settings exist in config
        oauth_settings = CustomerConfig.get_value('OAUTH2_SETTINGS', {})
        
        if not oauth_settings:
            logger.warning("No OAUTH2_SETTINGS found in configuration")
            return {}
        
        # For Amazon Cognito, convert config to authlib format
        if oauth_settings.get('provider') == 'cognito':
            user_pool_id = oauth_settings.get('user_pool_id')
            region = oauth_settings.get('region')
            
            if not user_pool_id or not region:
                logger.error("Missing user_pool_id or region for Cognito configuration")
                return {}
            
            # Build the authority URL for Cognito
            authority = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
            
            # Convert to authlib-compatible format
            converted_settings = {
                "client_id": oauth_settings.get('client_id'),
                "client_secret": oauth_settings.get('client_secret'),
                "authority": authority,
                "server_metadata_url": f"{authority}/.well-known/openid-configuration",
                "end_session_endpoint": oauth_settings.get('end_session_endpoint'),
                "client_kwargs": {
                    "scope": " ".join(oauth_settings.get('scopes', ['openid', 'email', 'profile']))
                }
            }
            
            logger.debug(f"Configured Cognito OAuth2 with authority: {authority}")
            return converted_settings
        
        # For other providers, return as-is
        return oauth_settings
    
    def _setup_oauth_client(self):
        """Setup OAuth client with authlib."""
        if not self.oauth_config.get('client_id'):
            logger.warning("OAuth2 client not configured - client_id missing")
            self.client = None
            return
        
        # Reinitialize OAuth with current app context if needed
        if current_app and not hasattr(self.oauth, '_app'):
            self.oauth = OAuth(current_app)
        
        try:
            # Register OAuth client using Cognito-style configuration
            register_kwargs = {
                'name': 'sera_oauth',
                'client_id': self.oauth_config['client_id'],
                'client_secret': self.oauth_config['client_secret'],
                'client_kwargs': self.oauth_config.get('client_kwargs', {})
            }
            
            # Add authority or server_metadata_url
            if 'authority' in self.oauth_config:
                register_kwargs['authority'] = self.oauth_config['authority']
            
            if 'server_metadata_url' in self.oauth_config:
                register_kwargs['server_metadata_url'] = self.oauth_config['server_metadata_url']
            
            # Add individual endpoints if provided (fallback)
            if 'authorization_endpoint' in self.oauth_config:
                register_kwargs['authorize_url'] = self.oauth_config['authorization_endpoint']
            if 'token_endpoint' in self.oauth_config:
                register_kwargs['access_token_url'] = self.oauth_config['token_endpoint']
            if 'userinfo_endpoint' in self.oauth_config:
                register_kwargs['userinfo_endpoint'] = self.oauth_config['userinfo_endpoint']
            
            logger.debug(f"Registering OAuth client with: {register_kwargs}")
            
            self.client = self.oauth.register(**register_kwargs)
            
            logger.debug("OAuth2 client configured successfully")
            
        except Exception as e:
            logger.error(f"Error setting up OAuth2 client: {e}", exc_info=True)
            self.client = None
            # If we're not in app context, we can't register the client now
            # It will be registered lazily when needed
            if not current_app:
                logger.warning("No Flask app context - OAuth2 client will be registered lazily")
                return
    
    def get_login_url(self, **kwargs) -> str:
        """Get the OAuth2 authorization URL for login initiation."""
        try:
            # Ensure client is initialized
            if not self.client:
                self._setup_oauth_client()
            
            if not self.client:
                raise ValueError("OAuth2 client not configured")
            
            # Generate state for CSRF protection with timestamp
            state = secrets.token_urlsafe(32)
            import time
            session['oauth_state'] = state
            session['oauth_state_timestamp'] = time.time()
            
            logger.debug(f"Generated OAuth state: {state[:8]}... (timestamp: {session['oauth_state_timestamp']})")
            
            # Get redirect URI from config or use default callback
            oauth_config = CustomerConfig.get_value('OAUTH2_SETTINGS', {})
            redirect_uri = (
                kwargs.get('redirect_uri') or 
                oauth_config.get('redirect_uri')
            )
            
            # Ensure redirect_uri is properly configured
            if not redirect_uri:
                logger.error("No redirect_uri configured in OAUTH2_SETTINGS")
                raise ValueError("OAuth2 redirect_uri not configured. Please set redirect_uri in OAUTH2_SETTINGS.")
            
            logger.debug(f"Using redirect URI: {redirect_uri}")
            
            # Generate authorization URL - use authorize_redirect which returns a Response object
            response = self.client.authorize_redirect(
                redirect_uri=redirect_uri,
                state=state
            )
            
            # Extract the location from the response
            auth_url = response.location if hasattr(response, 'location') else str(response.headers.get('Location'))
            
            logger.debug(f"Generated OAuth2 authorization URL")
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating OAuth2 login URL: {e}", exc_info=True)
            raise
    
    def handle_callback(self, request_data: Dict) -> Optional[User]:
        """Handle OAuth2 authorization callback."""
        try:
            if not self.client:
                logger.error("OAuth2 client not configured")
                return None
            
            # Verify state parameter for CSRF protection
            received_state = request.args.get('state')
            stored_state = session.pop('oauth_state', None)
            state_timestamp = session.pop('oauth_state_timestamp', None)
            
            logger.info(f"OAuth callback state validation:")
            logger.info(f"  Received state: {received_state[:8] if received_state else 'None'}...")
            logger.info(f"  Stored state: {stored_state[:8] if stored_state else 'None'}...")
            logger.info(f"  State timestamp: {state_timestamp}")
            
            if not received_state:
                logger.error("OAuth2 callback missing state parameter")
                return None
                
            if not stored_state:
                logger.error("OAuth2 stored state not found - session may have expired during login")
                return None
                
            if received_state != stored_state:
                logger.error(f"OAuth2 state mismatch - received: {received_state[:8]}..., stored: {stored_state[:8]}...")
                return None
                
            # Check if state is too old (more than 10 minutes)
            if state_timestamp:
                import time
                age = time.time() - state_timestamp
                logger.info(f"OAuth state age: {age:.1f} seconds")
                if age > 600:  # 10 minutes
                    logger.error(f"OAuth2 state expired - age: {age:.1f} seconds")
                    return None
            
            # Exchange authorization code for access token
            token = self.client.authorize_access_token()
            
            if not token:
                logger.error("Failed to obtain OAuth2 access token")
                return None
            
            # Get user info from userinfo endpoint or ID token
            user_data = self._extract_user_from_token(token)
            
            if user_data:
                logger.debug(f"OAuth2 authentication successful for user: {user_data.user_id}")
                return user_data
            else:
                logger.warning("Failed to extract user data from OAuth2 token")
                return None
                
        except OAuth2Error as e:
            logger.error(f"OAuth2 error during callback: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing OAuth2 callback: {e}", exc_info=True)
            return None
    
    def _decode_jwt_payload(self, jwt_token: str) -> Optional[Dict]:
        """Manually decode JWT token payload without signature verification."""
        try:
            # Split the JWT token into parts
            parts = jwt_token.split('.')
            if len(parts) != 3:
                logger.error("Invalid JWT token format")
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            
            # Add padding if needed for base64 decoding
            padding = len(payload) % 4
            if padding:
                payload += '=' * (4 - padding)
            
            # Decode base64 and parse JSON
            decoded_bytes = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded_bytes.decode('utf-8'))
            
            logger.debug(f"Decoded JWT payload: {payload_data}")
            return payload_data
            
        except Exception as e:
            logger.error(f"Error decoding JWT token: {e}")
            return None

    def _extract_user_from_token(self, token: Dict) -> Optional[User]:
        """Extract user information from OAuth2 token."""
        try:
            logger.debug(f"OAuth2 token keys: {list(token.keys())}")
            
            # For Cognito, try to manually decode the ID token first as it contains groups
            userinfo = None
            if 'id_token' in token:
                try:
                    # Try authlib parsing first
                    userinfo = self.client.parse_id_token(token)
                    logger.debug(f"ID token userinfo (authlib): {userinfo}")
                except Exception as e:
                    logger.warning(f"Failed to parse ID token with authlib: {e}")
                    # Fallback to manual JWT decoding
                    try:
                        userinfo = self._decode_jwt_payload(token['id_token'])
                        if userinfo:
                            logger.debug(f"ID token userinfo (manual decode): {userinfo}")
                    except Exception as e2:
                        logger.warning(f"Failed to manually decode ID token: {e2}")
            
            # Fallback to userinfo endpoint if ID token parsing failed
            if not userinfo and hasattr(self.client, 'userinfo'):
                try:
                    userinfo = self.client.userinfo(token=token)
                    logger.debug(f"Userinfo endpoint response: {userinfo}")
                except Exception as e:
                    logger.warning(f"Failed to get userinfo: {e}")
            
            if not userinfo:
                logger.error("No user information available from OAuth2 token")
                return None
            
            logger.debug(f"OAuth2 userinfo: {userinfo}")
            
            # Extract basic user info - prefer username over GUID
            user_id = (
                userinfo.get('cognito:username') or
                userinfo.get('preferred_username') or 
                userinfo.get('username') or 
                userinfo.get('email') or 
                userinfo.get('sub')
            )
            email = userinfo.get('email', '')
            first_name = userinfo.get('given_name', userinfo.get('firstName', ''))
            last_name = userinfo.get('family_name', userinfo.get('lastName', ''))
            
            # Extract groups/roles - Cognito uses 'cognito:groups'
            raw_groups = userinfo.get('cognito:groups', userinfo.get('groups', userinfo.get('roles', [])))
            if isinstance(raw_groups, str):
                raw_groups = [raw_groups]
            
            logger.debug(f"Raw groups from token: {raw_groups}")
            mapped_groups = self._map_groups(raw_groups)
            
            if not user_id or not email:
                logger.error("Missing required user ID or email in OAuth2 userinfo")
                return None
            
            user = User(
                user_id=user_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                groups=mapped_groups,
                attributes=userinfo
            )
            
            logger.debug(f"Created user from OAuth2 token: {user}")
            return user
            
        except Exception as e:
            logger.error(f"Error extracting user from OAuth2 token: {e}", exc_info=True)
            return None
    
    def _map_groups(self, raw_groups: list) -> list:
        """Map OAuth2 groups to application roles using group mappings."""
        mapped_groups = []
        
        for group in raw_groups:
            # Check if this is a GUID that needs mapping
            if group in self.group_mappings:
                mapped_group = self.group_mappings[group]
                mapped_groups.append(mapped_group)
                logger.debug(f"Mapped OAuth2 group {group} to {mapped_group}")
            else:
                # Use the group name as-is if not in mappings
                mapped_groups.append(group)
                logger.debug(f"Using OAuth2 group as-is: {group}")
        
        logger.debug(f"Final mapped groups: {mapped_groups}")
        return mapped_groups
    
    def get_logout_url(self, **kwargs) -> Optional[str]:
        """Get the OAuth2 logout URL if supported by the provider."""
        try:
            # Check if provider supports logout endpoint
            logout_endpoint = self.oauth_config.get('end_session_endpoint')
            
            if not logout_endpoint:
                logger.debug("OAuth2 provider does not support logout endpoint")
                return None
            
            # Build logout URL with optional post-logout redirect
            params = {}
            
            # Add client_id (required for Cognito logout)
            client_id = self.oauth_config.get('client_id')
            if client_id:
                params['client_id'] = client_id
            
            post_logout_redirect = kwargs.get('post_logout_redirect_uri')
            if post_logout_redirect:
                params['logout_uri'] = post_logout_redirect  # Cognito uses logout_uri, not post_logout_redirect_uri
            
            # Add ID token hint if available
            id_token = session.get('oauth_id_token')
            if id_token:
                params['id_token_hint'] = id_token
            
            logout_url = logout_endpoint
            if params:
                logout_url += '?' + urlencode(params)
            
            logger.debug(f"Generated OAuth2 logout URL: {logout_url}")
            return logout_url
            
        except Exception as e:
            logger.error(f"Error generating OAuth2 logout URL: {e}", exc_info=True)
            return None
    
    def validate_token(self, token: str) -> Optional[User]:
        """Validate an OAuth2 access token."""
        try:
            if not self.client:
                logger.error("OAuth2 client not configured")
                return None
            
            # Make request to userinfo endpoint with token
            userinfo_endpoint = self.oauth_config.get('userinfo_endpoint')
            if not userinfo_endpoint:
                logger.error("No userinfo endpoint configured for token validation")
                return None
            
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                userinfo = response.json()
                return self._extract_user_from_token({'userinfo': userinfo})
            else:
                logger.warning(f"Token validation failed with status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error validating OAuth2 token: {e}", exc_info=True)
            return None