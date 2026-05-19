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
Notification service for sending SES emails for SA reviews.
"""

import logging
import boto3
from typing import List
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def send_sa_review_notification(chat_id: str, chat_name: str, user_email: str, sa_emails: List[str]):
        """Send email notification to SAs about new review request."""
        try:
            ses_client = boto3.client('ses', region_name=CustomerConfig.get_aws_region())
            
            subject = f"New SA Review Request: {chat_name}"
            
            html_body = f"""
            <html>
            <body>
                <h2>New Solutions Architect Review Request</h2>
                <p><strong>Chat:</strong> {chat_name}</p>
                <p><strong>Requested by:</strong> {user_email}</p>
                <p><strong>Chat ID:</strong> {chat_id}</p>
                <p>
                    <a href="{CustomerConfig.get_value('APP_BASE_URL', 'https://sera.example.com')}/sa-review" 
                       style="background-color: #FF9900; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Review Queue
                    </a>
                </p>
            </body>
            </html>
            """
            
            text_body = f"""
            New Solutions Architect Review Request
            
            Chat: {chat_name}
            Requested by: {user_email}
            Chat ID: {chat_id}
            
            View your review queue at: {CustomerConfig.get_value('APP_BASE_URL', 'https://sera.example.com')}/sa-review
            """
            
            for sa_email in sa_emails:
                ses_client.send_email(
                    Source=CustomerConfig.get_value('SES_FROM_EMAIL', 'noreply@sera.example.com'),
                    Destination={'ToAddresses': [sa_email]},
                    Message={
                        'Subject': {'Data': subject},
                        'Body': {
                            'Html': {'Data': html_body},
                            'Text': {'Data': text_body}
                        }
                    }
                )
                logger.info(f"Sent SA review notification to {sa_email} for chat {chat_id}")
                
        except Exception as e:
            logger.error(f"Failed to send SA review notification: {e}")
    
    @staticmethod
    def send_review_ready_notification(chat_id: str, chat_name: str, user_email: str, sa_email: str):
        """Send email notification when SA review is ready for user."""
        try:
            ses_client = boto3.client('ses', region_name=CustomerConfig.get_aws_region())
            
            subject = f"SA Review Complete: {chat_name}"
            
            html_body = f"""
            <html>
            <body>
                <h2>Solutions Architect Review Complete</h2>
                <p>Your chat <strong>{chat_name}</strong> has been reviewed and is ready for your review.</p>
                <p><strong>Reviewed by:</strong> {sa_email}</p>
                <p>
                    <a href="{CustomerConfig.get_value('APP_BASE_URL', 'https://sera.example.com')}/chat/{chat_id}" 
                       style="background-color: #FF9900; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Chat
                    </a>
                </p>
            </body>
            </html>
            """
            
            ses_client.send_email(
                Source=CustomerConfig.get_value('SES_FROM_EMAIL', 'noreply@sera.example.com'),
                Destination={'ToAddresses': [user_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': html_body}}
                }
            )
            logger.info(f"Sent review ready notification to {user_email} for chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to send review ready notification: {e}")
