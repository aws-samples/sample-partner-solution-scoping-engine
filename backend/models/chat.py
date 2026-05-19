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
Chat model module for database interactions.
"""

import json
import logging
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime
import uuid
from flask import current_app
from ..config.app_config import CustomerConfig

logger = logging.getLogger(__name__)



_dynamodb_client = None
_table_name = None

def get_dynamodb_client():
    """Get the DynamoDB client."""
    global _dynamodb_client, _table_name
    if _dynamodb_client is None:
        try:
            # Try to get table name from Flask app context first
            try:
                from flask import current_app
                _table_name = current_app.config['DYNAMODB_TABLE_NAME']
                region = current_app.config['AWS_REGION']
            except (RuntimeError, KeyError):
                # Fall back to CustomerConfig if not in Flask context
                _table_name = CustomerConfig.get_value('DYNAMODB_TABLE_NAME')
                region = CustomerConfig.get_value('AWS_REGION')
            
            logger.debug(f"DynamoDB table name from config: {_table_name}")
            
            if not _table_name:
                # Try to use the db_service function as fallback
                try:
                    from services.db_service import _get_table_name
                    _table_name = _get_table_name()
                    logger.debug(f"Got table name from db_service: {_table_name}")
                except Exception as fallback_error:
                    logger.error(f"Fallback to db_service failed: error={str(fallback_error)}")
                    raise ValueError("DynamoDB table name is not configured")
            
            if not _table_name:
                raise ValueError("DynamoDB table name is not configured")
                
            logger.debug(f"Using AWS region: {region}")
            
            # Create DynamoDB client - will automatically use instance role
            _dynamodb_client = boto3.client('dynamodb', region_name=region)
            logger.debug(f"Successfully initialized DynamoDB client for table: {_table_name}")
            return _dynamodb_client
        except Exception as e:
            logger.error(f"DynamoDB client init failed: error={str(e)}")
            raise
    return _dynamodb_client

def save_chat(chat_data: dict) -> dict:
    """
    Save a chat record to DynamoDB.
    
    Args:
        chat_data (dict): Chat data to save
        
    Returns:
        dict: The saved chat data
    """
    try:
        logger.debug(f"Saving chat: chat_id={chat_data.get('chat_id')}, user={chat_data.get('user_id')}, stage={chat_data.get('stage')}")
        client = get_dynamodb_client()
        table_name = _table_name
        
        # Convert Python types to DynamoDB types
        item = {
            'chat_id': {'S': chat_data['chat_id']},
            'user_id': {'S': chat_data['user_id']},
            'assistant_persona': {'S': chat_data['assistant_persona']},
            'customer_persona': {'S': chat_data['customer_persona']},
            'interaction_method': {'S': chat_data['interaction_method']},
            'timestamp': {'S': chat_data['timestamp']},
            'stage': {'S': chat_data['stage']},
            'created_at': {'S': chat_data['created_at']},
            'updated_at': {'S': chat_data['updated_at']}
        }
        
        # Handle chat_message_history - preserve existing messages if they exist
        if 'messages' in chat_data and chat_data['messages']:
            # Convert existing messages to DynamoDB format
            dynamo_messages = []
            for msg in chat_data['messages']:
                if isinstance(msg, dict) and 'M' in msg:
                    # Already in DynamoDB format
                    dynamo_messages.append(msg)
                elif isinstance(msg, dict):
                    # Convert from Python dict to DynamoDB format
                    dynamo_msg = {'M': {}}
                    for key, value in msg.items():
                        if isinstance(value, str):
                            dynamo_msg['M'][key] = {'S': value}
                        elif isinstance(value, (int, float)):
                            dynamo_msg['M'][key] = {'N': str(value)}
                        elif isinstance(value, bool):
                            dynamo_msg['M'][key] = {'BOOL': value}
                    dynamo_messages.append(dynamo_msg)
            item['chat_message_history'] = {'L': dynamo_messages}
        else:
            # Initialize empty list only if no messages provided
            item['chat_message_history'] = {'L': []}
        
        # Add chat_name if it exists
        if 'chat_name' in chat_data:
            item['chat_name'] = {'S': chat_data['chat_name']}
        
        # Add SA review fields if they exist
        if 'source_chat_id' in chat_data:
            item['source_chat_id'] = {'S': chat_data['source_chat_id']}
        if 'review_status' in chat_data:
            item['review_status'] = {'S': chat_data['review_status']}
        if 'sa_reviewer' in chat_data:
            item['sa_reviewer'] = {'S': chat_data['sa_reviewer']}
        if 'sa_review_started' in chat_data:
            item['sa_review_started'] = {'S': chat_data['sa_review_started']}
        if 'sa_last_activity' in chat_data:
            item['sa_last_activity'] = {'S': chat_data['sa_last_activity']}
        if 'review_status' in chat_data:
            item['review_status'] = {'S': chat_data['review_status']}
        
        # Add chat variables if they exist
        if 'chat_variables' in chat_data and chat_data['chat_variables']:
            # Convert dict to DynamoDB Map format
            variables_map = {}
            for key, value in chat_data['chat_variables'].items():
                if isinstance(value, str):
                    variables_map[key] = {'S': value}
                elif isinstance(value, (int, float)):
                    variables_map[key] = {'N': str(value)}
                elif isinstance(value, bool):
                    variables_map[key] = {'BOOL': value}
                # Add more type conversions as needed
            item['chat_variables'] = {'M': variables_map}
        
        # Add documents if they exist
        if 'documents' in chat_data and chat_data['documents']:
            # Convert dict to DynamoDB Map format
            documents_map = {}
            for doc_id, doc_data in chat_data['documents'].items():
                doc_map = {}
                for key, value in doc_data.items():
                    if isinstance(value, bool):
                        doc_map[key] = {'BOOL': value}
                    elif isinstance(value, str):
                        doc_map[key] = {'S': value}
                    elif isinstance(value, (int, float)):
                        doc_map[key] = {'N': str(value)}
                    elif value is None:
                        doc_map[key] = {'NULL': True}
                documents_map[doc_id] = {'M': doc_map}
            item['documents'] = {'M': documents_map}
        
        # Add approvals if they exist
        if 'approvals' in chat_data and chat_data['approvals']:
            approvals_list = []
            for approval in chat_data['approvals']:
                approval_map = {}
                for key, value in approval.items():
                    if isinstance(value, str):
                        approval_map[key] = {'S': value}
                    elif isinstance(value, list):
                        approval_map[key] = {'L': [{'S': item} for item in value]}
                approvals_list.append({'M': approval_map})
            item['approvals'] = {'L': approvals_list}
        
        response = client.put_item(
            TableName=table_name,
            Item=item
        )
        
        logger.info(f"Chat saved: chat_id={chat_data['chat_id'][:8]}..., user={chat_data.get('user_id', 'unknown')}")
        return chat_data
    except Exception as e:
        logger.error(f"Save chat failed: chat_id={chat_data.get('chat_id', 'unknown')[:8]}..., error={str(e)}", exc_info=True)
        raise

def get_chat(user_id: str, timestamp: str) -> dict:
    """
    Retrieve a chat record from DynamoDB.
    
    Args:
        user_id (str): The ID of the user
        timestamp (str): The timestamp of the chat
        
    Returns:
        dict: The chat record, or None if not found
    """
    try:
        logger.debug(f"Getting chat: user={user_id}, timestamp={timestamp}")
        client = get_dynamodb_client()
        response = client.get_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            }
        )
        item = response.get('Item')
        if item:
            # Convert DynamoDB types back to Python types
            result = {
                'user_id': item['user_id']['S'],
                'timestamp': item['timestamp']['S'],
                'chat_id': item['chat_id']['S'],
                'assistant_persona': item['assistant_persona']['S'],
                'customer_persona': item['customer_persona']['S'],
                'interaction_method': item['interaction_method']['S'],
                'stage': item['stage']['S'] if 'stage' in item else 'INITIAL',
                'messages': item.get('chat_message_history', {'L': []})['L'],
                'created_at': item.get('created_at', {'S': ''})['S'],
                'updated_at': item.get('updated_at', {'S': ''})['S'],
                'chat_name': item.get('chat_name', {'S': ''})['S'] if 'chat_name' in item else ''
            }
            
            logger.debug(f"Chat found: chat_id={result['chat_id']}, stage={result['stage']}")
            return result
        
        logger.debug(f"Chat not found: user={user_id}, timestamp={timestamp}")
        return None
    except Exception as e:
        logger.error(f"Get chat record failed: error={str(e)}")
        raise

def list_chats_for_user(user_id: str, limit: int = 50, sort_by: str = 'updated_at', last_evaluated_key: dict = None) -> dict:
    """
    List all chats for a user with pagination support.
    
    Args:
        user_id (str): The ID of the user
        limit (int, optional): Maximum number of chats to return (default: 50, max: 100)
        sort_by (str, optional): Field to sort by ('updated_at' or 'timestamp')
        last_evaluated_key (dict, optional): For pagination - the last key from previous query
        
    Returns:
        dict: Dictionary containing 'chats' list and optional 'last_evaluated_key' for pagination
    """
    try:
        # Enforce reasonable limits
        if limit is None or limit > 100:
            limit = 50
            logger.debug(f"Limiting query to {limit} items for performance")
        
        client = get_dynamodb_client()
        
        # Build query parameters
        query_params = {
            'TableName': _table_name,
            'KeyConditionExpression': 'user_id = :uid',
            'ExpressionAttributeValues': {
                ':uid': {'S': user_id}
            },
            'Limit': limit,
            'ScanIndexForward': False  # Sort in descending order (newest first)
        }
        
        # Add pagination support
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
            logger.debug(f"Continuing pagination from key: {last_evaluated_key}")
        
        logger.debug(f"Querying DynamoDB for user {user_id} with limit {limit}")
        response = client.query(**query_params)
        items = response.get('Items', [])
        
        logger.debug(f"Retrieved {len(items)} chat records from DynamoDB")
        
        # Convert DynamoDB types back to Python types
        result = []
        for item in items:
            try:
                # Skip non-chat records (like coach_config)
                if 'chat_id' not in item:
                    continue
                    
                # Check if chat_name exists in the item
                chat_name = ''
                if 'chat_name' in item:
                    chat_name = item['chat_name']['S']
                
                chat_item = {
                    'user_id': item['user_id']['S'],
                    'timestamp': item['timestamp']['S'],
                    'chat_id': item['chat_id']['S'],
                    'assistant_persona': item['assistant_persona']['S'],
                    'customer_persona': item['customer_persona']['S'],
                    'interaction_method': item['interaction_method']['S'],
                    'stage': item['stage']['S'] if 'stage' in item else 'INITIAL',
                    'messages': item.get('chat_message_history', {'L': []})['L'],
                    'created_at': item.get('created_at', {'S': ''})['S'],
                    'updated_at': item.get('updated_at', {'S': ''})['S'],
                    'chat_name': chat_name
                }
                
                # Add SA review fields if they exist
                if 'source_chat_id' in item:
                    chat_item['source_chat_id'] = item['source_chat_id']['S']
                if 'review_status' in item:
                    chat_item['review_status'] = item['review_status']['S']
                if 'sa_reviewer' in item:
                    chat_item['sa_reviewer'] = item['sa_reviewer']['S']
                if 'sa_review_started' in item:
                    chat_item['sa_review_started'] = item['sa_review_started']['S']
                if 'sa_last_activity' in item:
                    chat_item['sa_last_activity'] = item['sa_last_activity']['S']
                if 'review_status' in item:
                    chat_item['review_status'] = item['review_status']['S']
                if 'sa_review_completed' in item:
                    chat_item['sa_review_completed'] = item['sa_review_completed']['S']
                if 'sa_copy_chat_id' in item:
                    chat_item['sa_copy_chat_id'] = item['sa_copy_chat_id']['S']
                
                # Add approvals if they exist
                if 'approvals' in item:
                    logger.debug(f"Found approvals in item for chat {item.get('chat_id', {}).get('S', 'unknown')}")
                    approvals_list = []
                    for approval_item in item['approvals']['L']:
                        if 'M' in approval_item:
                            approval = {}
                            for key, value in approval_item['M'].items():
                                if 'S' in value:
                                    approval[key] = value['S']
                                elif 'L' in value:
                                    approval[key] = [list_item['S'] for list_item in value['L'] if 'S' in list_item]
                            approvals_list.append(approval)
                    chat_item['approvals'] = approvals_list
                    logger.debug(f"Added {len(approvals_list)} approvals to chat_item")
                else:
                    logger.debug(f"No approvals found in item for chat {item.get('chat_id', {}).get('S', 'unknown')}")
                
                # Add SOW metadata if present
                if 'sow_metadata' in item:
                    sow_meta = item['sow_metadata']['M']
                    chat_item['sow_metadata'] = {
                        'status': sow_meta.get('status', {}).get('S', ''),
                        'generated_date': sow_meta.get('generated_date', {}).get('S', ''),
                        'customer_name': sow_meta.get('customer_name', {}).get('S', ''),
                        'project_title': sow_meta.get('project_title', {}).get('S', ''),
                        'template_type': sow_meta.get('template_type', {}).get('S', ''),
                        's3_url': sow_meta.get('s3_url', {}).get('S', ''),
                        's3_key': sow_meta.get('s3_key', {}).get('S', ''),
                        'version_id': sow_meta.get('version_id', {}).get('S', ''),
                        'file_size': int(sow_meta.get('file_size', {}).get('N', '0') or '0'),
                        'generation_time': float(sow_meta.get('generation_time', {}).get('N', '0') or '0')
                    }
                result.append(chat_item)
            except KeyError as e:
                logger.error(f"RECENT-CHATS-FEATURE-TROUBLESHOOTING: Error converting item: {e}")
                logger.error(f"RECENT-CHATS-FEATURE-TROUBLESHOOTING: Problem item: {item}")
                # Continue processing other items
        
        # Sort the results (DynamoDB already sorted by timestamp, but we might want updated_at)
        if sort_by == 'updated_at':
            result.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        # Note: timestamp sorting is already handled by DynamoDB ScanIndexForward=False
            
        # Prepare response with pagination info
        response_data = {
            'chats': result,
            'count': len(result)
        }
        
        # Add pagination key if there are more results
        if 'LastEvaluatedKey' in response:
            response_data['last_evaluated_key'] = response['LastEvaluatedKey']
            logger.debug(f"More results available, pagination key provided")
        
        logger.debug(f"Returning {len(result)} chats for user {user_id}")
        return response_data
    except Exception as e:
        logger.error(f"Error listing chats for user: {e}", exc_info=True)
        raise

def save_chat_message(user_id: str, chat_id: str, message_data: dict) -> dict:
    """
    Save a message to a chat.
    
    Args:
        user_id (str): The ID of the user
        chat_id (str): The ID of the chat
        message_data (dict): The message data to save
        
    Returns:
        dict: The updated chat data
    """
    try:
        logger.debug(f"Saving message: chat_id={chat_id}, user={user_id}, role={message_data.get('role')}")
        
        # First we need to find the chat by its chat_id
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found for user {user_id}")
            
        # Now we have the chat with its timestamp, which is the range key
        timestamp = chat['timestamp']
        client = get_dynamodb_client()
        
        # Ensure message has required fields
        if 'message_id' not in message_data:
            message_data['message_id'] = str(uuid.uuid4())
        if 'message_timestamp' not in message_data:
            message_data['message_timestamp'] = datetime.utcnow().isoformat()
            
        # Check if content is a list or dict and convert to JSON string if needed
        import json
        if 'content' in message_data and not isinstance(message_data['content'], str):
            logger.debug(f"Converting non-string content to JSON string: {type(message_data['content'])}")
            message_data['content'] = json.dumps(message_data['content'])
            
        # Convert message to DynamoDB types
        dynamo_message = {
            'message_id': {'S': message_data['message_id']},
            'message_timestamp': {'S': message_data['message_timestamp']},
            'content': {'S': message_data.get('content', '')},
            'role': {'S': message_data.get('role', 'user')}
        }
        
        # Add citations to dynamo_message if it exists
        if 'citations' in message_data and message_data['citations']:
            # Convert citations to DynamoDB format
            citations_list = []
            
            if isinstance(message_data['citations'], list):
                for citation_item in message_data['citations']:
                    if isinstance(citation_item, dict):
                        citation_dict = {}
                        for k, v in citation_item.items():
                            if isinstance(v, str):
                                citation_dict[k] = {'S': v}
                            elif isinstance(v, dict):
                                # Handle nested objects like location
                                nested_dict = {}
                                for nk, nv in v.items():
                                    if isinstance(nv, str):
                                        nested_dict[nk] = {'S': nv}
                                    elif isinstance(nv, (int, float)):
                                        nested_dict[nk] = {'N': str(nv)}
                                citation_dict[k] = {'M': nested_dict}
                            elif isinstance(v, list):
                                # Handle lists like sourceContent
                                list_items = []
                                for item in v:
                                    if isinstance(item, str):
                                        list_items.append({'S': item})
                                    elif isinstance(item, dict):
                                        item_dict = {}
                                        for ik, iv in item.items():
                                            if isinstance(iv, str):
                                                item_dict[ik] = {'S': iv}
                                        list_items.append({'M': item_dict})
                                citation_dict[k] = {'L': list_items}
                        citations_list.append({'M': citation_dict})
            
            dynamo_message['citations'] = {'L': citations_list}
            
        # Update the chat with the new message
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET chat_message_history = list_append(if_not_exists(chat_message_history, :empty_list), :msg)',
            ExpressionAttributeValues={
                ':msg': {'L': [{'M': dynamo_message}]},
                ':empty_list': {'L': []}
            },
            ReturnValues='ALL_NEW'
        )
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        result = {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'assistant_persona': attributes['assistant_persona']['S'],
            'customer_persona': attributes['customer_persona']['S'],
            'interaction_method': attributes['interaction_method']['S'],
            'stage': attributes.get('stage', {'S': 'INITIAL'})['S'],
            'messages': attributes.get('chat_message_history', {'L': []})['L'],
            'created_at': attributes.get('created_at', {'S': ''})['S'],
            'updated_at': attributes.get('updated_at', {'S': ''})['S'],
            'chat_name': attributes.get('chat_name', {'S': ''})['S'] if 'chat_name' in attributes else ''
        }
        
        return result
    except Exception as e:
        logger.error(f"Save chat message failed: error={str(e)}")
        raise

def store_pricing_instructions(user_id: str, chat_id: str, message_id: str, instructions: dict):
    """Store pricing calculator instructions, accumulating with existing ones for this message thread."""
    from services.db_service import ddb_update_item, ddb_get_item
    try:
        chats_response = list_chats_for_user(user_id)
        chat = next((c for c in chats_response.get('chats', []) if c['chat_id'] == chat_id), None)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
            
        key = {'user_id': {'S': user_id}, 'timestamp': {'S': chat['timestamp']}}
        
        # Get existing item to check if pricing_calculator_instructions exists
        existing_item = ddb_get_item(key)
        
        if not existing_item or 'pricing_calculator_instructions' not in existing_item:
            # Create the map with the first message
            update_expression = "SET #pci = :new_map"
            expression_attribute_names = {'#pci': 'pricing_calculator_instructions'}
            expression_attribute_values = {
                ':new_map': {'M': {message_id: {'L': [{'S': json.dumps(instructions)}]}}}
            }
        else:
            # Append to existing message list
            update_expression = "SET #pci.#msg_id = list_append(if_not_exists(#pci.#msg_id, :empty_list), :instructions)"
            expression_attribute_names = {
                '#pci': 'pricing_calculator_instructions',
                '#msg_id': message_id
            }
            expression_attribute_values = {
                ':instructions': {'L': [{'S': json.dumps(instructions)}]},
                ':empty_list': {'L': []}
            }
        
        ddb_update_item(
            key=key,
            update_expression=update_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values
        )
        
        logger.debug(f"Stored pricing instructions for message {message_id}")
    except Exception as e:
        logger.error(f"Store pricing instructions failed: error={str(e)}")
        raise


def get_pricing_instructions(user_id: str, chat_id: str, message_id: str) -> dict:
    """Get accumulated pricing instructions for a specific message."""
    from services.db_service import ddb_get_item
    try:
        chats_response = list_chats_for_user(user_id)
        chat = next((c for c in chats_response.get('chats', []) if c['chat_id'] == chat_id), None)
        if not chat:
            return {'actions': []}
            
        key = {'user_id': {'S': user_id}, 'timestamp': {'S': chat['timestamp']}}
        item = ddb_get_item(key)
        
        if not item or 'pricing_calculator_instructions' not in item:
            return {'actions': []}
        
        # Get instructions for specific message_id
        instructions_map = item['pricing_calculator_instructions']['M']
        if message_id not in instructions_map:
            return {'actions': []}
        
        accumulated_actions = []
        for instruction_item in instructions_map[message_id]['L']:
            instruction = json.loads(instruction_item['S'])
            if 'actions' in instruction:
                accumulated_actions.extend(instruction['actions'])
        
        logger.debug(f"Retrieved {len(accumulated_actions)} pricing actions for message {message_id}")
        return {'actions': accumulated_actions}
    except Exception as e:
        logger.error(f"Get pricing instructions failed: error={str(e)}")
        return {'actions': []}


def update_conversation_stage(user_id: str, chat_id: str, stage: str) -> dict:
    """
    Update the conversation stage of a chat.
    
    Args:
        user_id (str): The ID of the user
        chat_id (str): The ID of the chat
        stage (str): The new conversation stage
        
    Returns:
        dict: The updated chat data
    """
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
        
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET stage = :stage',
            ExpressionAttributeValues={
                ':stage': {'S': stage}
            },
            ReturnValues='ALL_NEW'
        )
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        result = {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'assistant_persona': attributes['assistant_persona']['S'],
            'customer_persona': attributes['customer_persona']['S'],
            'interaction_method': attributes['interaction_method']['S'],
            'stage': attributes['stage']['S'],
            'messages': attributes.get('chat_message_history', {'L': []})['L'],
            'created_at': attributes.get('created_at', {'S': ''})['S'],
            'updated_at': attributes.get('updated_at', {'S': ''})['S'],
            'chat_name': attributes.get('chat_name', {'S': ''})['S'] if 'chat_name' in attributes else ''
        }
        
        return result
    except Exception as e:
        logger.error(f"Update conversation stage failed: error={str(e)}")
        raise

def delete_chat(user_id: str, timestamp: str) -> bool:
    """
    Delete a chat record and its S3 folder.
    
    Args:
        user_id (str): The ID of the user
        timestamp (str): The timestamp of the chat
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.debug(f"Deleting chat: user={user_id}, timestamp={timestamp}")
        
        # First get the chat to find the chat_id for S3 cleanup
        from ..services.db_service import ddb_get_item, ddb_delete_item, ddb_query
        
        response = ddb_get_item({
            'user_id': {'S': user_id},
            'timestamp': {'S': timestamp}
        })
        
        chat_id = None
        if response:
            chat_id = response.get('chat_id', {}).get('S')
        
        # Delete from DynamoDB
        ddb_delete_item({
            'user_id': {'S': user_id},
            'timestamp': {'S': timestamp}
        })
        
        # Delete S3 folder if chat_id exists
        if chat_id:
            try:
                bucket_name = CustomerConfig.get_value('S3_UPLOAD_BUCKET')
                logger.info(f"S3_UPLOAD_BUCKET from config: {bucket_name}")
                
                if bucket_name:
                    s3_client = boto3.client('s3')
                    
                    # List and delete all objects in the chat folder
                    response = s3_client.list_objects_v2(
                        Bucket=bucket_name,
                        Prefix=f"{chat_id}/"
                    )
                    
                    if 'Contents' in response:
                        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                        s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': objects_to_delete}
                        )
                        logger.info(f"Deleted {len(objects_to_delete)} S3 objects for chat {chat_id}")
                    else:
                        logger.info(f"No S3 objects found for chat {chat_id}")
                else:
                    logger.warning("S3_UPLOAD_BUCKET not configured, skipping S3 cleanup")
                    
            except Exception as s3_error:
                logger.error(f"Delete S3 folder failed: chat_id={chat_id}, error={str(s3_error)}")
                # Don't fail the whole operation if S3 cleanup fails
        
        logger.debug(f"Deleted chat record for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Delete chat record failed: error={str(e)}")
        raise

def delete_chat_by_id(user_id: str, chat_id: str) -> bool:
    """
    Delete a chat record by its chat_id and any associated SA copies.
    
    Args:
        user_id (str): The ID of the user
        chat_id (str): The ID of the chat
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First we need to find the chat by its chat_id
        chats_response = list_chats_for_user(user_id)
        chats = chats_response.get('chats', [])
        chat = next((c for c in chats if c['chat_id'] == chat_id), None)
        
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found for user {user_id}")
            
        # Now we have the chat with its timestamp, which is the range key
        timestamp = chat['timestamp']
        
        # Check if this chat has an SA copy and delete it
        sa_copy_chat_id = chat.get('sa_copy_chat_id')
        if sa_copy_chat_id:
            logger.info(f"Found SA copy {sa_copy_chat_id} for chat {chat_id}, deleting it")
            try:
                client = get_dynamodb_client()
                scan_response = client.scan(
                    TableName=_table_name,
                    FilterExpression='chat_id = :chat_id',
                    ExpressionAttributeValues={':chat_id': {'S': sa_copy_chat_id}}
                )
                
                for sa_item in scan_response.get('Items', []):
                    sa_user_id = sa_item['user_id']['S']
                    sa_timestamp = sa_item['timestamp']['S']
                    logger.info(f"Deleting SA copy: user_id={sa_user_id}, timestamp={sa_timestamp}")
                    delete_chat(sa_user_id, sa_timestamp)
                    
            except Exception as sa_error:
                logger.error(f"Delete SA copy failed: sa_copy={sa_copy_chat_id}, error={str(sa_error)}")
        
        # Delete the original chat
        return delete_chat(user_id, timestamp)
    except Exception as e:
        logger.error(f"Delete chat by ID failed: error={str(e)}")
        raise

# Future: CRUD operations on chat history
# - create_new_chat(user_id, initial_metadata)
# - update_chat_metadata(chat_id, metadata) 


def update_chat_name(user_id: str, chat_id: str, new_name: str) -> dict:
    """
    Update the name of a chat.
    
    Args:
        user_id (str): The ID of the user
        chat_id (str): The ID of the chat
        new_name (str): The new name for the chat
        
    Returns:
        dict: The updated chat data
    """
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
        
        # Update the chat name and updated_at timestamp
        current_time = datetime.utcnow().isoformat()
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET chat_name = :name, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':name': {'S': new_name},
                ':updated_at': {'S': current_time}
            },
            ReturnValues='ALL_NEW'
        )
        
        logger.info(f"Chat name updated: chat_id={chat_id}, new_name={new_name[:30]}...")
        
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
            'updated_at': attributes['updated_at']['S'],
            'chat_name': attributes['chat_name']['S']
        }
    except Exception as e:
        logger.error(f"Update chat name failed: error={str(e)}")
        raise
def save_feedback(user_id: str, chat_id: str, feedback_data: dict) -> dict:
    """
    Save feedback data to a chat record.
    
    Args:
        user_id (str): The ID of the user
        chat_id (str): The ID of the chat
        feedback_data (dict): The feedback data to save
        
    Returns:
        dict: The updated chat data
    """
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
        
        # Convert feedback data to DynamoDB format
        dynamo_feedback = {
            'type': {'S': feedback_data.get('type', '')},
            'provider': {'S': feedback_data.get('provider', '')},
            'detail': {'S': feedback_data.get('detail', '')}
        }
        
        # Update the chat with the feedback data
        current_time = datetime.utcnow().isoformat()
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET feedback = :feedback, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':feedback': {'M': dynamo_feedback},
                ':updated_at': {'S': current_time}
            },
            ReturnValues='ALL_NEW'
        )
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        result = {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'assistant_persona': attributes['assistant_persona']['S'],
            'customer_persona': attributes['customer_persona']['S'],
            'interaction_method': attributes['interaction_method']['S'],
            'stage': attributes.get('stage', {'S': 'INITIAL'})['S'],
            'messages': attributes.get('chat_message_history', {'L': []})['L'],
            'created_at': attributes.get('created_at', {'S': ''})['S'],
            'updated_at': attributes['updated_at']['S'],
            'chat_name': attributes.get('chat_name', {'S': ''})['S'] if 'chat_name' in attributes else ''
        }
        
        # Add feedback to result if it exists
        if 'feedback' in attributes:
            result['feedback'] = {
                'type': attributes['feedback']['M']['type']['S'],
                'provider': attributes['feedback']['M']['provider']['S'],
                'detail': attributes['feedback']['M']['detail']['S']
            }
            
        return result
    except Exception as e:
        logger.error(f"Save feedback failed: error={str(e)}")
        raise
def save_sa_feedback(user_id, chat_id, sa_feedback):
    """
    Save Solutions Architect feedback for a chat.
    
    Args:
        user_id (str): The user ID
        chat_id (str): The chat ID
        sa_feedback (dict): The SA feedback data with architect_name, type, and detail
        
    Returns:
        dict: The updated chat item
        
    Raises:
        ValueError: If the chat is not found
    """
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
        
        # Get the current timestamp
        current_time = datetime.now().isoformat()
        
        # Add timestamp to the feedback
        sa_feedback['timestamp'] = current_time
        
        # Convert feedback data to DynamoDB format
        dynamo_feedback = {k: {'S': v} for k, v in sa_feedback.items()}
        
        # Update the chat item in DynamoDB
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET sa_review = :sa_review, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':sa_review': {'M': dynamo_feedback},
                ':updated_at': {'S': current_time}
            },
            ReturnValues='ALL_NEW'
        )
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        result = {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'assistant_persona': attributes['assistant_persona']['S'],
            'customer_persona': attributes['customer_persona']['S'],
            'interaction_method': attributes['interaction_method']['S'],
            'stage': attributes.get('stage', {'S': 'INITIAL'})['S'],
            'created_at': attributes.get('created_at', {'S': ''})['S'],
            'updated_at': attributes['updated_at']['S']
        }
        
        # Add sa_review to result
        if 'sa_review' in attributes:
            result['sa_review'] = {k: v['S'] for k, v in attributes['sa_review']['M'].items()}
            
        return result
    except Exception as e:
        logger.error(f"Error saving SA feedback: {e}", exc_info=True)
        raise

def create_document_metadata(document_type, s3_url, s3_key, version_id, file_size, original_filename=None, tool_name=None):
    """
    Create standardized document metadata with approval workflow fields.
    
    Args:
        document_type (str): Type of document (diagram, sow_document, pricing_report, etc.)
        s3_url (str): S3 URL for the document
        s3_key (str): S3 key for the document
        version_id (str): S3 version ID
        file_size (str): File size in bytes
        original_filename (str): Original filename if applicable
        tool_name (str): Name of the MCP tool that generated this
    
    Returns:
        dict: Standardized document metadata
    """
    from datetime import datetime
    
    return {
        'document_type': document_type,
        's3_url': s3_url,
        's3_key': s3_key,
        'version_id': version_id,
        'file_size': file_size,
        'original_filename': original_filename,
        'tool_name': tool_name,
        'created_timestamp': datetime.now().isoformat(),
        'approved': False,
        'approved_by': None,
        'approved_timestamp': None,
        'version_number': 1
    }

def update_chat_document(chat_id, document_id, document_metadata):
    """
    Update or add document metadata for a chat.
    
    Args:
        chat_id (str): The ID of the chat
        document_id (str): The ID of the document
        document_metadata (dict): Metadata for the document
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the current chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            logger.warning(f"Chat not found: chat_id={chat_id}")
            return False
        
        # Initialize documents dictionary if it doesn't exist
        if 'documents' not in chat:
            chat['documents'] = {}
        
        # Add or update the document metadata
        chat['documents'][document_id] = document_metadata
        
        # Save the updated chat using the standard save function
        save_chat(chat)
        return True
    except Exception as e:
        logger.error(f"Update document metadata failed: error={str(e)}")
        return False

def get_chat_document(chat_id, document_id):
    """
    Get document metadata for a specific document in a chat.
    
    Args:
        chat_id (str): The ID of the chat
        document_id (str): The ID of the document
    
    Returns:
        dict: Document metadata or None if not found
    """
    try:
        # Get the current chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat or 'documents' not in chat:
            return None
        
        # Return the document metadata if it exists
        return chat['documents'].get(document_id)
    except Exception as e:
        logger.error(f"Get document metadata failed: error={str(e)}")
        return None

def approve_document(chat_id, document_id, approved_by):
    """
    Approve a document for download access.
    
    Args:
        chat_id (str): The ID of the chat
        document_id (str): The ID of the document
        approved_by (str): User ID who approved the document
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from datetime import datetime
        
        chat = get_chat_by_chat_id(chat_id)
        if not chat or 'documents' not in chat or document_id not in chat['documents']:
            logger.warning(f"Document not found for approval: chat_id={chat_id}, doc_id={document_id[:8]}...")
            return False
        
        # Update approval status
        chat['documents'][document_id]['approved'] = True
        chat['documents'][document_id]['approved_by'] = approved_by
        chat['documents'][document_id]['approved_timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Document approved: chat_id={chat_id}, doc_id={document_id[:8]}..., approved_by={approved_by}")
        
        # Save updated chat
        return save_chat(chat)
    except Exception as e:
        logger.error(f"Approve document failed: error={str(e)}")
        return False

def get_chat_documents(chat_id):
    """
    Get all document metadata for a chat.
    
    Args:
        chat_id (str): The ID of the chat
    
    Returns:
        dict: Dictionary of document IDs to metadata
    """
    try:
        # Get the current chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat or 'documents' not in chat:
            return {}
        
        # Return all documents
        return chat['documents']
    except Exception as e:
        logger.error(f"Get chat documents failed: error={str(e)}")
        return {}

def get_chat_by_chat_id(chat_id: str) -> dict:
    """
    Get a chat by chat_id using the chat-id-gsi (works for any user).
    
    Args:
        chat_id (str): The chat ID to find
        
    Returns:
        dict: Chat data if found, None if not found
    """
    try:
        client = get_dynamodb_client()
        
        # Use the existing chat-id-gsi to find the chat
        response = client.query(
            TableName=_table_name,
            IndexName='chat-id-gsi',
            KeyConditionExpression='chat_id = :chat_id',
            ExpressionAttributeValues={
                ':chat_id': {'S': chat_id}
            },
            Limit=1
        )
        
        items = response.get('Items', [])
        if not items:
            return None
            
        item = items[0]
        
        # Convert DynamoDB types back to Python types
        chat_item = {
            'user_id': item['user_id']['S'],
            'timestamp': item['timestamp']['S'],
            'chat_id': item['chat_id']['S'],
            'assistant_persona': item['assistant_persona']['S'],
            'customer_persona': item['customer_persona']['S'],
            'interaction_method': item['interaction_method']['S'],
            'stage': item['stage']['S'] if 'stage' in item else 'INITIAL',
            'messages': item.get('chat_message_history', {'L': []})['L'],
            'created_at': item.get('created_at', {'S': ''})['S'],
            'updated_at': item.get('updated_at', {'S': ''})['S'],
            'chat_name': item.get('chat_name', {'S': ''})['S'] if 'chat_name' in item else ''
        }
        
        
        # Add SA review fields if they exist
        if 'source_chat_id' in item:
            chat_item['source_chat_id'] = item['source_chat_id']['S']
        if 'review_status' in item:
            chat_item['review_status'] = item['review_status']['S']
        if 'sa_reviewer' in item:
            chat_item['sa_reviewer'] = item['sa_reviewer']['S']
        if 'sa_review_started' in item:
            chat_item['sa_review_started'] = item['sa_review_started']['S']
        if 'sa_last_activity' in item:
            chat_item['sa_last_activity'] = item['sa_last_activity']['S']
        if 'review_status' in item:
            chat_item['review_status'] = item['review_status']['S']
        if 'sa_review_completed' in item:
            chat_item['sa_review_completed'] = item['sa_review_completed']['S']
        if 'sa_copy_chat_id' in item:
            chat_item['sa_copy_chat_id'] = item['sa_copy_chat_id']['S']
        
        # Add documents if they exist
        if 'documents' in item:
            chat_item['documents'] = {}
            for doc_id, doc_data in item['documents']['M'].items():
                doc_dict = {}
                for key, value in doc_data['M'].items():
                    if 'S' in value:
                        doc_dict[key] = value['S']
                    elif 'N' in value:
                        doc_dict[key] = float(value['N']) if '.' in value['N'] else int(value['N'])
                    elif 'BOOL' in value:
                        doc_dict[key] = value['BOOL']
                    elif 'NULL' in value:
                        doc_dict[key] = None
                chat_item['documents'][doc_id] = doc_dict
        
        # Add approvals if they exist
        if 'approvals' in item:
            logger.debug(f"Found approvals in get_chat_by_chat_id for chat {chat_id}")
            approvals_list = []
            for approval_item in item['approvals']['L']:
                if 'M' in approval_item:
                    approval = {}
                    for key, value in approval_item['M'].items():
                        if 'S' in value:
                            approval[key] = value['S']
                        elif 'L' in value:
                            approval[key] = [list_item['S'] for list_item in value['L'] if 'S' in list_item]
                    approvals_list.append(approval)
            chat_item['approvals'] = approvals_list
            logger.debug(f"Added {len(approvals_list)} approvals to chat_item in get_chat_by_chat_id")
        
        return chat_item
        
    except Exception as e:
        logger.error(f"Error getting chat by chat_id: {e}", exc_info=True)
        raise

def get_all_chats_needing_sa_review(limit: int = 50, last_evaluated_key: dict = None) -> dict:
    """
    Get all chats from all users that have requested SA review.
    Efficiently queries chats with sa_review_status = 'requested'.
    
    Args:
        limit (int): Maximum number of chats to return
        last_evaluated_key (dict, optional): For pagination
        
    Returns:
        dict: Dictionary containing 'chats' list and optional 'last_evaluated_key'
    """
    try:
        from ..services.db_service import ddb_scan
        
        # Scan for chats with review_status = 'requested'
        logger.debug(f"Scanning for chats with review_status = 'requested'")
        items = ddb_scan(
            filter_expression='review_status = :status',
            expression_attribute_values={':status': {'S': 'requested'}}
        )
        
        logger.debug(f"Retrieved {len(items)} chats needing SA review")
        
        # Convert items to expected format
        all_chats = []
        for item in items:
            try:
                chat_item = {
                    'user_id': item.get('user_id', {}).get('S', ''),
                    'timestamp': item.get('timestamp', {}).get('S', ''),
                    'chat_id': item.get('chat_id', {}).get('S', ''),
                    'assistant_persona': item.get('assistant_persona', {}).get('S', ''),
                    'customer_persona': item.get('customer_persona', {}).get('S', ''),
                    'interaction_method': item.get('interaction_method', {}).get('S', ''),
                    'stage': item.get('stage', {}).get('S', ''),
                    'messages': item.get('chat_message_history', {}).get('L', []),
                    'created_at': item.get('created_at', {}).get('S', ''),
                    'updated_at': item.get('updated_at', {}).get('S', ''),
                    'chat_name': item.get('chat_name', {}).get('S', ''),
                    'review_status': item.get('review_status', {}).get('S', '')
                }
                all_chats.append(chat_item)
            except Exception as e:
                logger.error(f"Convert item failed: error={str(e)}")
                continue
        
        # Sort by updated_at descending (most recent first)
        all_chats.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        response_data = {
            'chats': all_chats[:limit],
            'count': len(all_chats[:limit])
        }
        
        logger.debug(f"Returning {len(all_chats[:limit])} chats needing SA review")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting chats needing SA review: {e}", exc_info=True)
        raise

def update_chat_field(chat_id: str, field_name: str, field_value: str) -> dict:
    """
    Update a specific field in a chat.
    
    Args:
        chat_id (str): The chat ID to update
        field_name (str): The field name to update
        field_value (str): The new field value
        
    Returns:
        dict: The updated chat item
        
    Raises:
        ValueError: If the chat is not found
    """
    try:
        # First find the chat using chat_id
        chat = get_chat_by_chat_id(chat_id)
        
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found")
            
        # Get the user_id and timestamp from the found chat
        user_id = chat['user_id']
        timestamp = chat['timestamp']
        
        client = get_dynamodb_client()
        
        # Get the current timestamp
        current_time = datetime.utcnow().isoformat()
        
        # Update the specific field
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression=f'SET {field_name} = :field_value, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':field_value': {'S': field_value},
                ':updated_at': {'S': current_time}
            },
            ReturnValues='ALL_NEW'
        )
        
        logger.debug(f"Updated field {field_name} to {field_value} for chat {chat_id}")
        
        # Return simplified result
        return {
            'chat_id': chat_id,
            'field_updated': field_name,
            'new_value': field_value,
            'updated_at': current_time
        }
        
    except Exception as e:
        logger.error(f"Error updating field {field_name} for chat {chat_id}: {e}", exc_info=True)
        raise

def update_chat_review_status(chat_id: str, status: str, sa_reviewer: str = None, sa_copy_chat_id: str = None) -> dict:
    """
    Update the SA review status of a chat.
    
    Args:
        chat_id (str): The chat ID to update
        status (str): The new SA review status
        sa_reviewer (str, optional): The SA reviewer user ID
        sa_copy_chat_id (str, optional): The SA copy chat ID
        
    Returns:
        dict: The updated chat item
        
    Raises:
        ValueError: If the chat is not found
    """
    try:
        # First find the chat using chat_id
        chat = get_chat_by_chat_id(chat_id)
        
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found")
            
        # Get the user_id and timestamp from the found chat
        user_id = chat['user_id']
        timestamp = chat['timestamp']
        
        client = get_dynamodb_client()
        
        # Get the current timestamp
        current_time = datetime.utcnow().isoformat()
        
        # Build update expression and attribute values
        update_expression_parts = ['SET review_status = :status, updated_at = :updated_at']
        expression_attribute_values = {
            ':status': {'S': status},
            ':updated_at': {'S': current_time}
        }
        
        # Add optional fields if provided
        if sa_reviewer:
            update_expression_parts.append('sa_reviewer = :sa_reviewer')
            expression_attribute_values[':sa_reviewer'] = {'S': sa_reviewer}
            
            # Set review started time for new reviews
            if status == 'in_progress':
                update_expression_parts.append('sa_review_started = :sa_review_started')
                update_expression_parts.append('sa_last_activity = :sa_last_activity')
                expression_attribute_values[':sa_review_started'] = {'S': current_time}
                expression_attribute_values[':sa_last_activity'] = {'S': current_time}
        
        if sa_copy_chat_id:
            update_expression_parts.append('sa_copy_chat_id = :sa_copy_chat_id')
            expression_attribute_values[':sa_copy_chat_id'] = {'S': sa_copy_chat_id}
        
        # Set completion time for completed reviews
        if status in ['ready_for_merge', 'complete_no_changes', 'merged', 'cancelled']:
            update_expression_parts.append('sa_review_completed = :sa_review_completed')
            expression_attribute_values[':sa_review_completed'] = {'S': current_time}
        
        update_expression = ', '.join(update_expression_parts)
        
        # Update the chat item in DynamoDB
        response = client.update_item(
            TableName=_table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        
        # Convert DynamoDB types back to Python types
        attributes = response.get('Attributes', {})
        result = {
            'user_id': attributes['user_id']['S'],
            'timestamp': attributes['timestamp']['S'],
            'chat_id': attributes['chat_id']['S'],
            'review_status': attributes.get('review_status', {'S': 'none'})['S'],
            'updated_at': attributes['updated_at']['S']
        }
        
        # Add optional fields if present
        if 'sa_reviewer' in attributes:
            result['sa_reviewer'] = attributes['sa_reviewer']['S']
        if 'sa_copy_chat_id' in attributes:
            result['sa_copy_chat_id'] = attributes['sa_copy_chat_id']['S']
        if 'sa_review_started' in attributes:
            result['sa_review_started'] = attributes['sa_review_started']['S']
        if 'sa_review_completed' in attributes:
            result['sa_review_completed'] = attributes['sa_review_completed']['S']
            
        logger.debug(f"Updated SA review status for chat {chat_id} to {status}")
        return result
        
    except Exception as e:
        logger.error(f"Error updating SA review status for chat {chat_id}: {e}", exc_info=True)
        raise

def get_chat_messages(user_id, chat_id):
    """Get all messages for a specific chat"""
    try:
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return []
        return chat.get('messages', [])
    except Exception as e:
        logger.error(f"Get chat messages failed: chat_id={chat_id}, error={str(e)}")
        return []

def create_document_reference_for_message(document_id, document_type):
    """
    Create a document reference string to embed in chat messages instead of file content.
    
    Args:
        document_id (str): Document ID to reference
        document_type (str): Type of document for display
    
    Returns:
        str: Document reference string to insert in message
    """
    return f"[document_ref:{document_id}:{document_type}]"

def store_wafr_metadata_in_dynamodb(chat_id: str, wafr_metadata: dict) -> bool:
    """
    Store WAFR document metadata in DynamoDB following the same pattern as cost-analysis server.
    
    This function directly updates the chat record with WAFR document fields.
    The bedrock service will automatically handle storing in the documents field.
    
    Args:
        chat_id: Chat session ID
        wafr_metadata: WAFR document metadata containing:
            - s3_url: S3 URL of the document
            - s3_key: S3 key of the document
            - version_id: S3 version ID (optional)
            - file_size: File size in bytes
            - generation_time: Time taken to generate the document
            
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Storing WAFR document data for chat_id: {chat_id}")
        
        # First find the chat by chat_id using GSI (same as cost-analysis server)
        client = get_dynamodb_client()
        table_name = _table_name
        
        gsi_response = client.query(
            TableName=table_name,
            IndexName='chat-id-gsi',
            KeyConditionExpression='chat_id = :chat_id',
            ExpressionAttributeValues={
                ':chat_id': {'S': chat_id}
            },
            Limit=1
        )
        
        if not gsi_response['Items']:
            logger.warning(f'Chat not found in DynamoDB: chat_id={chat_id}')
            return False
        
        # Get the user_id and timestamp from the found chat record
        chat_record = gsi_response['Items'][0]
        user_id = chat_record['user_id']['S']
        timestamp = chat_record['timestamp']['S']
        
        logger.info(f'Found chat record - user_id: {user_id}, timestamp: {timestamp}')
        
        # Prepare WAFR data (same pattern as cost-analysis server)
        wafr_data = {
            'wafr_report_s3_key': {'S': wafr_metadata.get('s3_key', '')},
            'wafr_report_s3_url': {'S': wafr_metadata.get('s3_url', '')},
            'wafr_generation_timestamp': {'S': datetime.now().isoformat()},
        }
        
        # Add optional fields if present
        if wafr_metadata.get('version_id'):
            wafr_data['wafr_report_version_id'] = {'S': wafr_metadata['version_id']}
        if wafr_metadata.get('file_size'):
            wafr_data['wafr_report_file_size'] = {'N': str(wafr_metadata['file_size'])}
        if wafr_metadata.get('generation_time'):
            wafr_data['wafr_generation_time'] = {'N': str(wafr_metadata['generation_time'])}
        
        # Update the chat record with WAFR data using correct primary key
        update_expression = 'SET ' + ', '.join([f'{k} = :{k}' for k in wafr_data.keys()])
        expression_attribute_values = {f':{k}': v for k, v in wafr_data.items()}
        
        response = client.update_item(
            TableName=table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f'WAFR data saved to DynamoDB for chat_id: {chat_id}')
        return True
        
    except Exception as e:
        logger.error(f'Save WAFR data failed: error={str(e)}')
        return False