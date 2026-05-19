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
User model for handling authentication and session management.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class User:
    """User model for authentication and session management."""
    
    def __init__(self, user_id: str, email: str, first_name: str = "", last_name: str = "", 
                 groups: List[str] = None, attributes: Dict = None):
        self.user_id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.groups = groups or []
        self.attributes = attributes or {}
        self.created_at = datetime.utcnow()
        self.last_login = datetime.utcnow()
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self) -> str:
        """Get the user's display name (full name or email)."""
        return self.full_name if self.full_name else self.email
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role/group."""
        return role in self.groups
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.groups for role in roles)
    
    def is_sales_person(self) -> bool:
        """Check if user is a sales person."""
        return self.has_any_role(['sera_sales_person', 'sera_sales_manager'])
    
    def is_solutions_architect(self) -> bool:
        """Check if user is a solutions architect."""
        return self.has_any_role(['sera_solutions_architect', 'sera_sa_manager', 'sera_cross_customer_solutions_architect'])
    
    def is_sa_manager(self) -> bool:
        """Check if user is a SA manager."""
        return self.has_role('sera_sa_manager')
    
    def can_review_sow(self) -> bool:
        """Check if user can review SOW documents."""
        return self.has_any_role(['sera_solutions_architect', 'sera_sa_manager'])
    
    def has_supported_sellers(self) -> bool:
        """
        Check if user has any support relationships (assigned sellers).
        
        Returns:
            bool: True if user has any support relationships, False otherwise
        """
        try:
            from .support_relationship import get_supported_sellers
            supported_sellers = get_supported_sellers(self.user_id)
            return len(supported_sellers) > 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Supported sellers check failed: user={self.user_id}, error={str(e)}")
            return False
    
    def can_access_chat(self, chat_owner_id: str) -> bool:
        """
        Check if user can access a specific chat.
        
        Args:
            chat_owner_id (str): The user ID who owns the chat
            
        Returns:
            bool: True if user can access the chat, False otherwise
        """
        # User can always access their own chats
        if self.user_id == chat_owner_id:
            return True
        
        # Check if user supports this chat owner
        try:
            from .support_relationship import user_supports_seller
            return user_supports_seller(self.user_id, chat_owner_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Support check failed: user={self.user_id}, owner={chat_owner_id}, error={str(e)}")
            return False
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary for session storage."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'groups': self.groups,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create user from dictionary (session data)."""
        user = cls(
            user_id=data['user_id'],
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            groups=data.get('groups', []),
            attributes=data.get('attributes', {})
        )
        
        if 'created_at' in data:
            user.created_at = datetime.fromisoformat(data['created_at'])
        if 'last_login' in data:
            user.last_login = datetime.fromisoformat(data['last_login'])
            
        return user
    
    def __repr__(self) -> str:
        return f"User(user_id='{self.user_id}', email='{self.email}', groups={self.groups})"