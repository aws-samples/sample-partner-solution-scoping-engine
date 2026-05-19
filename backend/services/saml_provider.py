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
SAML authentication provider implementation.
"""
import logging
from typing import Dict, Optional
from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from flask import request, url_for
from abc import ABC, abstractmethod
from ..models.user import User
from ..config.app_config import CustomerConfig

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

logger = logging.getLogger(__name__)


class SAMLProvider(AuthProvider):
    """SAML authentication provider using python3-saml."""
    
    def __init__(self):
        self.settings = self._load_saml_settings()
        self.group_mappings = CustomerConfig.get_saml_group_mappings()
    
    def _load_saml_settings(self) -> Dict:
        """Load SAML settings from configuration."""
        saml_config = CustomerConfig.get_saml_settings()
        
        # Convert our config format to python3-saml format
        settings = {
            "strict": saml_config.get("strict", True),
            "debug": saml_config.get("debug", False),
            "sp": {
                "entityId": saml_config["sp"]["entityId"],
                "assertionConsumerService": {
                    "url": saml_config["sp"]["assertionConsumerService"]["url"],
                    "binding": saml_config["sp"]["assertionConsumerService"]["binding"]
                },
                "singleLogoutService": {
                    "url": saml_config["sp"]["singleLogoutService"]["url"],
                    "binding": saml_config["sp"]["singleLogoutService"]["binding"]
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": saml_config["sp"].get("x509cert", ""),
                "privateKey": saml_config["sp"].get("privateKey", "")
            },
            "idp": {
                "entityId": saml_config["idp"]["entityId"],
                "singleSignOnService": {
                    "url": saml_config["idp"]["singleSignOnService"]["url"],
                    "binding": saml_config["idp"]["singleSignOnService"]["binding"]
                },
                "singleLogoutService": {
                    "url": saml_config["idp"]["singleLogoutService"]["url"],
                    "binding": saml_config["idp"]["singleLogoutService"]["binding"]
                },
                "x509cert": saml_config["idp"]["x509cert"]
            }
        }
        
        return settings
    
    def _init_saml_request(self, request_obj) -> Dict:
        """Initialize SAML request data structure for python3-saml."""
        url_data = urlparse(request_obj.url)
        return {
            'https': 'on' if request_obj.scheme == 'https' else 'off',
            'http_host': request_obj.host,
            'server_port': url_data.port,
            'script_name': request_obj.path,
            'get_data': request_obj.args.copy(),
            'post_data': request_obj.form.copy()
        }
    
    def get_login_url(self, **kwargs) -> str:
        """Get the SAML SSO URL for login initiation."""
        try:
            req = self._init_saml_request(request)
            auth = OneLogin_Saml2_Auth(req, self.settings)
            
            # Optional relay state for post-auth redirect
            relay_state = kwargs.get('relay_state')
            
            sso_url = auth.login(return_to=relay_state)
            logger.debug(f"Generated SAML SSO URL: {sso_url}")
            return sso_url
            
        except Exception as e:
            logger.error(f"Error generating SAML login URL: {e}", exc_info=True)
            raise
    
    def handle_callback(self, request_data: Dict) -> Optional[User]:
        """Handle SAML assertion callback."""
        try:
            req = self._init_saml_request(request)
            auth = OneLogin_Saml2_Auth(req, self.settings)
            
            # Process the SAML Response
            auth.process_response()
            
            errors = auth.get_errors()
            if len(errors) == 0:
                # Successfully authenticated
                user_data = self._extract_user_from_assertion(auth)
                if user_data:
                    logger.debug(f"SAML authentication successful for user: {user_data.user_id}")
                    return user_data
                else:
                    logger.warning("Failed to extract user data from SAML assertion")
                    return None
            else:
                logger.error(f"SAML authentication errors: {errors}")
                logger.error(f"Last error reason: {auth.get_last_error_reason()}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing SAML callback: {e}", exc_info=True)
            return None
    
    def _extract_user_from_assertion(self, auth: OneLogin_Saml2_Auth) -> Optional[User]:
        """Extract user information from SAML assertion."""
        try:
            # Get user attributes
            attributes = auth.get_attributes()
            name_id = auth.get_nameid()
            
            logger.debug(f"SAML NameID: {name_id}")
            logger.debug(f"SAML Attributes: {attributes}")
            
            # Extract basic user info
            user_id = name_id or attributes.get('email', [''])[0]
            email = attributes.get('email', [name_id])[0] if name_id else ""
            first_name = attributes.get('firstName', attributes.get('givenName', ['']))[0]
            last_name = attributes.get('lastName', attributes.get('surname', ['']))[0]
            
            # Extract groups and map them
            raw_groups = attributes.get('groups', attributes.get('memberOf', []))
            mapped_groups = self._map_groups(raw_groups)
            
            if not user_id or not email:
                logger.error("Missing required user ID or email in SAML assertion")
                return None
            
            user = User(
                user_id=user_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                groups=mapped_groups,
                attributes=attributes
            )
            
            logger.debug(f"Created user from SAML assertion: {user}")
            return user
            
        except Exception as e:
            logger.error(f"Error extracting user from SAML assertion: {e}", exc_info=True)
            return None
    
    def _map_groups(self, raw_groups: list) -> list:
        """Map SAML groups to application roles using group mappings."""
        mapped_groups = []
        
        for group in raw_groups:
            # Check if this is a GUID that needs mapping
            if group in self.group_mappings:
                mapped_group = self.group_mappings[group]
                mapped_groups.append(mapped_group)
                logger.debug(f"Mapped SAML group {group} to {mapped_group}")
            else:
                # Use the group name as-is if not in mappings
                mapped_groups.append(group)
                logger.debug(f"Using SAML group as-is: {group}")
        
        logger.debug(f"Final mapped groups: {mapped_groups}")
        return mapped_groups
    
    def get_logout_url(self, **kwargs) -> Optional[str]:
        """Get the SAML SLO URL for logout."""
        try:
            req = self._init_saml_request(request)
            auth = OneLogin_Saml2_Auth(req, self.settings)
            
            # Optional return URL after logout
            return_to = kwargs.get('return_to')
            
            slo_url = auth.logout(return_to=return_to)
            logger.debug(f"Generated SAML SLO URL: {slo_url}")
            return slo_url
            
        except Exception as e:
            logger.error(f"Error generating SAML logout URL: {e}", exc_info=True)
            return None
    
    def validate_token(self, token: str) -> Optional[User]:
        """SAML doesn't use tokens, so this is not applicable."""
        logger.warning("Token validation not applicable for SAML provider")
        return None