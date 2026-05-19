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
Service responsible for logging token usage to the audit database (RDS).
"""
import logging
import datetime
# from ..models.audit import TokenUsageAudit # Import the RDS model
# from ..database import db # Import the SQLAlchemy db instance

logger = logging.getLogger(__name__)

def log_token_usage(customer_id, user_id, chat_id, model_invoked, usage_data, cost=None, request_details=None, response_metadata=None):
    """Logs a record of token usage to the audit database.

    Args:
        customer_id (str): Identifier for the customer/tenant.
        user_id (str): Identifier for the user who initiated the request.
        chat_id (str): Identifier for the chat session.
        model_invoked (str): Name or identifier of the AI model used.
        usage_data (dict): Dictionary containing token counts, typically like
                           {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}.
                           Structure might vary based on the AI model provider.
        cost (float, optional): Calculated cost for the invocation. Defaults to None.
        request_details (str, optional): Snippets or summary of the request. Defaults to None.
        response_metadata (str, optional): Metadata from the model response. Defaults to None.
    """
    try:
        input_tokens = usage_data.get('input_tokens')
        output_tokens = usage_data.get('output_tokens')
        total_tokens = usage_data.get('total_tokens')

        # Basic validation
        if not all([customer_id, user_id, chat_id, model_invoked]):
            logger.warning("Attempted to log token usage with missing identifiers.")
            return False

        logger.debug(f"Logging token usage for chat {chat_id}, user {user_id}, model {model_invoked}")
        logger.debug(f"Usage Data: {usage_data}, Cost: {cost}")

        # Create and save the TokenUsageAudit record
        # audit_record = TokenUsageAudit(
        #     timestamp=datetime.datetime.utcnow(),
        #     customer_id=customer_id,
        #     user_id=user_id,
        #     chat_id=chat_id,
        #     model_invoked=model_invoked,
        #     input_tokens=input_tokens,
        #     output_tokens=output_tokens,
        #     total_tokens=total_tokens,
        #     cost=cost,
        #     request_details=request_details,
        #     response_metadata=response_metadata
        # )
        # db.session.add(audit_record)
        # db.session.commit()
        
        # Placeholder - print to log instead of DB write
        logger.info(f"AUDIT LOGGED: chat_id={chat_id}, model={model_invoked}, input_tokens={input_tokens}, output_tokens={output_tokens}")

        return True

    except Exception as e:
        logger.error(f"Failed to log token usage to audit database: {e}", exc_info=True)
        # Handle database errors (e.g., rollback session if using SQLAlchemy)
        # try:
        #     db.session.rollback()
        # except Exception as rollback_e:
        #     logger.error(f"Error rolling back audit log session: {rollback_e}")
        return False 