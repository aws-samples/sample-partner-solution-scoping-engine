"""
ALB Authentication Provider - Extracts user information from ALB Cognito headers.

When ALB is configured with Cognito authentication, it injects headers containing
user information into every request. This provider decodes those headers.
"""

import logging
import jwt
import json
import boto3
from typing import Optional, Dict, Any, List
from ..models.user import User
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)


class ALBAuthProvider:
    """Provider for extracting user information from ALB Cognito headers."""
    
    def _get_user_groups(self, username: str, user_pool_id: str) -> List[str]:
        """
        Fetch user's Cognito groups via API call.
        
        Args:
            username: Cognito username
            user_pool_id: User pool ID
            
        Returns:
            List of group names
        """
        try:
            region = CustomerConfig.get_value('AWS_REGION', 'us-east-1')
            cognito_client = boto3.client('cognito-idp', region_name=region)
            
            response = cognito_client.admin_list_groups_for_user(
                UserPoolId=user_pool_id,
                Username=username
            )
            
            groups = [group['GroupName'] for group in response.get('Groups', [])]
            logger.debug(f"Fetched {len(groups)} groups for user {username[:20]}...")
            return groups
            
        except Exception as e:
            logger.error(f"Failed to fetch groups for user: {str(e)[:50]}...")
            return []
    
    def get_user_from_headers(self, headers: Dict[str, str]) -> Optional[User]:
        """
        Extract user information from ALB-injected Cognito headers.
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            User object if headers are valid, None otherwise
        """
        try:
            # ALB injects x-amzn-oidc-data header with JWT containing user claims
            oidc_data = headers.get('x-amzn-oidc-data') or headers.get('X-Amzn-Oidc-Data')
            
            if not oidc_data:
                logger.debug("No ALB OIDC data header found")
                return None
            
            # Decode JWT without signature verification (ALB already verified it)
            claims = jwt.decode(
                oidc_data,
                options={"verify_signature": False}
            )
            
            logger.debug(f"Decoded ALB JWT claims for user: {claims.get('email', 'unknown')[:20]}...")
            
            # Determine group source based on IdP configuration
            groups = []
            enable_external_idp = CustomerConfig.get_value('ENABLE_EXTERNAL_IDP', 'false').lower() == 'true'
            
            if enable_external_idp:
                # Federated IdP user - groups are in custom:groups JWT claim
                custom_groups = claims.get('custom:groups', '[]')
                groups = json.loads(custom_groups) if isinstance(custom_groups, str) else (custom_groups if isinstance(custom_groups, list) else [])
                logger.debug(f"Using federated IdP groups from JWT: {groups}")
            else:
                # Native Cognito user - fetch groups via API
                cognito_username = claims.get('cognito:username') or claims.get('username')
                user_pool_id = CustomerConfig.get_value('COGNITO_USER_POOL_ID')
                if cognito_username and user_pool_id:
                    groups = self._get_user_groups(cognito_username, user_pool_id)
                    logger.debug(f"Fetched native Cognito groups via API: {groups}")
                else:
                    logger.warning(f"Cannot fetch groups - username={cognito_username}, pool_id={user_pool_id}")
            
            # Extract user information from claims
            # Use email as user_id for consistency with existing OAuth2 data model
            user = User(
                user_id=claims.get('email'),
                email=claims.get('email'),
                first_name=claims.get('given_name', ''),
                last_name=claims.get('family_name', ''),
                groups=groups,
                attributes={
                    'cognito_username': claims.get('cognito:username'),
                    'email_verified': claims.get('email_verified', False)
                }
            )
            
            logger.debug(f"User extracted from ALB headers: user_id={user.user_id[:20]}..., groups={user.groups}")
            
            return user
            
        except jwt.DecodeError as e:
            logger.error(f"Failed to decode ALB OIDC JWT: {str(e)[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Error extracting user from ALB headers: {str(e)[:50]}...", exc_info=True)
            return None
    
    def is_alb_authenticated_request(self, headers: Dict[str, str]) -> bool:
        """
        Check if request came through ALB with Cognito authentication.
        
        Args:
            headers: Request headers dictionary
            
        Returns:
            True if ALB authentication headers are present
        """
        return bool(headers.get('x-amzn-oidc-data') or headers.get('X-Amzn-Oidc-Data'))
