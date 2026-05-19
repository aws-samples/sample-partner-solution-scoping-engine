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
Chat variables module for managing conversation variables.
"""

import logging
from datetime import datetime
from .chat import get_dynamodb_client, list_chats_for_user, _table_name

logger = logging.getLogger(__name__)

def get_chat_variables(user_id: str, chat_id: str) -> dict:
    """
    Get variables for a chat session.
    
    Args:
        user_id (str): ID of the user
        chat_id (str): ID of the chat
        
    Returns:
        dict: Dictionary of chat variables
    """
    try:
        logger.debug(f"Getting chat variables: chat_id={chat_id}, user={user_id}")
        # First we need to find the chat by its chat_id
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        if not chat:
            logger.warning(f"Chat not found for variables: chat_id={chat_id}, user={user_id}")
            return {}
            
        # Now we have the chat with its timestamp, which is the range key
        timestamp = chat['timestamp']
        client = get_dynamodb_client()
        
        # Get the table name from the client if _table_name is None
        table_name = _table_name
        if table_name is None:
            from flask import current_app
            table_name = current_app.config.get('DYNAMODB_TABLE_NAME')
            if not table_name:
                raise ValueError("DynamoDB table name is not configured")
            logger.debug(f"Using table name from app config: {table_name}")
        
        # Get the item
        response = client.get_item(
            TableName=table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            }
        )
        
        item = response.get('Item', {})
        
        # Initialize variables dict
        variables = {}
        
        # Add stage if present
        if 'stage' in item:
            variables['stage'] = item['stage']['S']
        
        # Add other variables from chat_variables map
        if 'chat_variables' in item:
            logger.debug(f"Found chat_variables map with {len(item['chat_variables']['M'])} variables")
            logger.debug(f"Variable keys in DynamoDB: {list(item['chat_variables']['M'].keys())}")
            
            for var_name, var_value in item['chat_variables']['M'].items():
                # Convert underscores back to hyphens for variable names
                original_var_name = var_name.replace('_', '-')
                
                # DynamoDB stores values with type indicators
                if 'S' in var_value:  # String type
                    variables[original_var_name] = var_value['S']
                elif 'N' in var_value:  # Number type
                    variables[original_var_name] = var_value['N']
                elif 'BOOL' in var_value:  # Boolean type
                    variables[original_var_name] = var_value['BOOL']
        else:
            logger.debug(f"No chat_variables map found for chat {chat_id}")
        
        logger.debug(f"Retrieved {len(variables)} variables for chat {chat_id}")
        logger.debug(f"Variable keys: {list(variables.keys())}")
        
        return variables
    except Exception as e:
        logger.error(f"Error getting chat variables: {e}", exc_info=True)
        return {}

def update_chat_variables(user_id: str, chat_id: str, variables: dict) -> dict:
    """
    Update variables for a chat session.
    
    Args:
        user_id (str): ID of the user
        chat_id (str): ID of the chat
        variables (dict): Dictionary of variables to update
        
    Returns:
        dict: Updated chat data
    """
    logger.debug(f"Updating chat variables: chat_id={chat_id}, user={user_id}, var_count={len(variables)}")
    try:
        # First we need to find the chat by its chat_id
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found for user {user_id}")
            
        # Now we have the chat with its timestamp, which is the range key
        timestamp = chat['timestamp']
        client = get_dynamodb_client()
        
        # Get the table name from the client if _table_name is None
        table_name = _table_name
        if table_name is None:
            from flask import current_app
            table_name = current_app.config.get('DYNAMODB_TABLE_NAME')
            if not table_name:
                raise ValueError("DynamoDB table name is not configured")
            logger.debug(f"Using table name from app config: {table_name}")
        
        # Create update expression parts
        update_expressions = []
        expression_attr_values = {}
        expression_attr_names = {}
        
        # Add stage update if present in variables
        if 'stage' in variables:
            update_expressions.append('stage = :stage')
            expression_attr_values[':stage'] = {'S': variables['stage']}
            # Remove from variables dict since we're handling it separately
            del variables['stage']
        
        # If there are other variables, add them to a chat_variables map
        if variables:
            # Get the current item to check if chat_variables exists
            response = client.get_item(
                TableName=table_name,
                Key={
                    'user_id': {'S': user_id},
                    'timestamp': {'S': timestamp}
                }
            )
            
            item = response.get('Item', {})
            
            if 'chat_variables' not in item:
                # For new chat_variables map, we don't need expression attribute names
                # Create new chat_variables map
                update_expressions.append('chat_variables = :vars')
                
                # Convert variables to DynamoDB format
                dynamo_vars = {}
                for var_name, var_value in variables.items():
                    # Replace hyphens with underscores for DynamoDB compatibility
                    safe_var_name = var_name.replace('-', '_')
                    dynamo_vars[safe_var_name] = {'S': str(var_value)}
                
                expression_attr_values[':vars'] = {'M': dynamo_vars}
                
                # Log the operation
                logger.debug(f"Creating new chat_variables map with {len(variables)} variables")
                logger.debug(f"Variable keys: {list(variables.keys())}")
            else:
                # Update existing chat_variables map
                for var_name, var_value in variables.items():
                    # Replace hyphens with underscores for DynamoDB compatibility
                    safe_var_name = var_name.replace('-', '_')
                    update_expressions.append(f'chat_variables.#var_{safe_var_name} = :val_{safe_var_name}')
                    expression_attr_values[f':val_{safe_var_name}'] = {'S': str(var_value)}
                    expression_attr_names[f'#var_{safe_var_name}'] = safe_var_name
                
                # Log the operation
                logger.debug(f"Updating existing chat_variables map with {len(variables)} variables")
                logger.debug(f"Variable keys: {list(variables.keys())}")
                logger.debug(f"Expression attribute names: {expression_attr_names}")
        
        # If no updates, return early
        if not update_expressions:
            logger.warning("No variables to update")
            return chat
        
        # Build the update expression
        update_expression = 'SET ' + ', '.join(update_expressions)
        
        # Execute the update
        update_params = {
            'TableName': table_name,
            'Key': {
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attr_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        # Add expression attribute names if we have any
        if expression_attr_names:
            update_params['ExpressionAttributeNames'] = expression_attr_names
        
        response = client.update_item(**update_params)
        logger.debug("Successfully updated chat variables in DynamoDB")
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        return {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'assistant_persona': attributes['assistant_persona']['S'],
            'customer_persona': attributes['customer_persona']['S'],
            'interaction_method': attributes['interaction_method']['S'],
            'stage': attributes.get('stage', {'S': 'INITIAL'})['S'],
            'messages': attributes.get('chat_message_history', {'L': []})['L'],
            'created_at': attributes.get('created_at', {'S': ''})['S'],
            'updated_at': attributes.get('updated_at', {'S': ''})['S']
        }
    except Exception as e:
        logger.error(f"Error updating chat variables: {e}", exc_info=True)
        raise
