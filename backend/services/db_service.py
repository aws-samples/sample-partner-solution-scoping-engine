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
Service for interacting with the database.
"""
import logging
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from backend.config.app_config import CustomerConfig

logger = logging.getLogger(__name__)

_dynamodb_client = None
_table_name = None

class DBService:
    def __init__(self):
        self.client = boto3.client('dynamodb', region_name=CustomerConfig.get_aws_region())
        self.table_name = CustomerConfig.get_value('DYNAMODB_TABLE_NAME')

def _get_dynamodb_client():
    """Initializes and returns the DynamoDB client."""
    global _dynamodb_client, _table_name
    if _dynamodb_client is None:
        try:
            config = CustomerConfig()
            
            region = config.get_value('AWS_REGION')
            _table_name = config.get_value('DYNAMODB_TABLE_NAME')
            if not region or not _table_name:
                logger.error("DynamoDB region or table name not configured.")
                raise ValueError("DynamoDB not configured")
            
            logger.debug(f"Initializing DynamoDB client in region {region}")
            _dynamodb_client = boto3.client('dynamodb', region_name=region)
            logger.debug(f"Successfully initialized DynamoDB client for table: {_table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB client: {e}", exc_info=True)
            _dynamodb_client = None
            _table_name = None
            raise
    return _dynamodb_client

def _get_table_name():
    """Returns the configured DynamoDB table name."""
    global _table_name
    if _table_name is None:
        _get_dynamodb_client()  # This will initialize _table_name
    return _table_name

# --- DynamoDB Chat Functions (Example Wrappers) ---

def ddb_save_item(item):
    """Saves an item to the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        logger.debug(f"Saving item to DynamoDB: {item.get('pk', 'N/A')}")
        response = client.put_item(
            TableName=_table_name,
            Item=item
        )
        logger.debug(f"Successfully saved item. Response metadata: {response.get('ResponseMetadata')}")
        return True
    except Exception as e:
        logger.error(f"Failed to save item to DynamoDB: {e}", exc_info=True)
        return False

def ddb_get_item(key):
    """Gets an item from the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        # logger.debug(f"Getting item from DynamoDB with key: {key}") # Commented out to reduce log noise
        response = client.get_item(
            TableName=_table_name,
            Key=key,
            ConsistentRead=True
        )
        item = response.get('Item')
        if item:
            # logger.debug(f"Successfully retrieved item: {key}") # TURNED OFF
            return item
        else:
            # logger.warning(f"Item not found in DynamoDB with key: {key}") # Commented out to reduce log noise
            return None
    except Exception as e:
        logger.error(f"Failed to get item from DynamoDB: {e}", exc_info=True)
        return None

def ddb_query(key_condition_expression, expression_attribute_values, scan_index_forward=True, expression_attribute_names=None):
    """Query items from the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        # logger.debug(f"Querying DynamoDB with condition: {key_condition_expression}") # Commented out to reduce log noise
        
        query_params = {
            'TableName': _table_name,
            'KeyConditionExpression': key_condition_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'ScanIndexForward': scan_index_forward
        }
        
        if expression_attribute_names:
            query_params['ExpressionAttributeNames'] = expression_attribute_names
            
        response = client.query(**query_params)
        items = response.get('Items', [])
        # logger.debug(f"Successfully queried {len(items)} items from DynamoDB") # Commented out to reduce log noise
        return items
    except Exception as e:
        logger.error(f"Failed to query DynamoDB: {e}", exc_info=True)
        return []

def ddb_delete_item(key):
    """Delete an item from the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        response = client.delete_item(
            TableName=_table_name,
            Key=key
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete item from DynamoDB: {e}", exc_info=True)
        return False

def ddb_update_item(key, update_expression, expression_attribute_values, expression_attribute_names=None):
    """Update an item in the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        
        update_params = {
            'TableName': _table_name,
            'Key': key,
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values
        }
        
        if expression_attribute_names:
            update_params['ExpressionAttributeNames'] = expression_attribute_names
            
        response = client.update_item(**update_params)
        return True
    except Exception as e:
        logger.error(f"Failed to update item in DynamoDB: {e}", exc_info=True)
        return False

def ddb_scan(filter_expression=None, expression_attribute_values=None, expression_attribute_names=None):
    """Scan items from the configured DynamoDB chat table."""
    try:
        client = _get_dynamodb_client()
        
        scan_params = {
            'TableName': _table_name
        }
        
        if filter_expression:
            scan_params['FilterExpression'] = filter_expression
        if expression_attribute_values:
            scan_params['ExpressionAttributeValues'] = expression_attribute_values
        if expression_attribute_names:
            scan_params['ExpressionAttributeNames'] = expression_attribute_names
            
        # Handle pagination
        all_items = []
        last_evaluated_key = None
        
        while True:
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = client.scan(**scan_params)
            
            if response.get('Items'):
                all_items.extend(response['Items'])
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
                
        return all_items
    except Exception as e:
        logger.error(f"Failed to scan DynamoDB: {e}", exc_info=True)
        return []

# Add other DDB functions as needed

# --- RDS Functions (if not using ORM directly) ---

# def rds_execute_query(query, params=None):
#     """Executes a query against the configured RDS database."""
#     conn = None
#     cursor = None
#     try:
#         # Get connection from pool or create new
#         # conn = ...
#         cursor = conn.cursor()
#         logger.debug(f"Executing RDS query: {query} with params: {params}")
#         cursor.execute(query, params)
#         results = cursor.fetchall() # Or fetchone()
#         conn.commit() # If it's an INSERT/UPDATE/DELETE
#         logger.debug("RDS query executed successfully.")
#         return results
#     except Exception as e:
#         logger.error(f"Failed to execute RDS query: {e}", exc_info=True)
#         if conn:
#             conn.rollback()
#         return None
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             # Return connection to pool or close
#             pass 

def get_coach_config(user_id):
    """Get coach configuration for a user"""
    try:
        key = {
            'user_id': {'S': user_id},
            'timestamp': {'S': 'coach_config'}
        }
        
        response = ddb_get_item(key)
        
        if response and 'config_data' in response:
            config_data = response['config_data']
            if config_data:
                # Convert DynamoDB format to regular dict
                return {
                    'userName': config_data.get('M', {}).get('userName', {}).get('S', ''),
                    'userRole': config_data.get('M', {}).get('userRole', {}).get('S', ''),
                    'insights': config_data.get('M', {}).get('insights', {}).get('S', ''),
                    'debounceSeconds': int(config_data.get('M', {}).get('debounceSeconds', {}).get('N', '2')),
                    'maxWaitSeconds': int(config_data.get('M', {}).get('maxWaitSeconds', {}).get('N', '30'))
                }
        return None
        
    except Exception as e:
        logger.error(f"Error getting coach config for user {user_id}: {str(e)}")
        return None

def save_coach_config(user_id, config_data):
    """Save coach configuration for a user"""
    try:
        item = {
            'user_id': {'S': user_id},
            'timestamp': {'S': 'coach_config'},
            'config_data': {
                'M': {
                    'userName': {'S': config_data.get('userName', '')},
                    'userRole': {'S': config_data.get('userRole', '')},
                    'insights': {'S': config_data.get('insights', '')},
                    'debounceSeconds': {'N': str(config_data.get('debounceSeconds', 2))},
                    'maxWaitSeconds': {'N': str(config_data.get('maxWaitSeconds', 30))}
                }
            },
            'updated_at': {'S': datetime.now().isoformat()}
        }
        
        ddb_save_item(item)
        logger.info(f"Coach config saved for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving coach config for user {user_id}: {str(e)}")
        return False


def get_user_id_from_chat_id(chat_id):
    """Get user_id from chat_id by finding the chat record"""
    try:
        client = _get_dynamodb_client()
        table_name = _get_table_name()
        logger.debug(f"🔍 Searching for chat_id {chat_id} in table {table_name}")
        
        # Handle pagination to scan all records
        last_evaluated_key = None
        while True:
            scan_kwargs = {
                'TableName': table_name,
                'FilterExpression': 'attribute_exists(chat_id) AND chat_id = :chat_id',
                'ExpressionAttributeValues': {
                    ':chat_id': {'S': chat_id}
                }
            }
            
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
            
            response = client.scan(**scan_kwargs)
            
            logger.debug(f"🔍 DynamoDB scan page returned {response['Count']} items")
            
            if response['Items']:
                user_id_field = response['Items'][0]['user_id']['S']
                logger.debug(f"🔍 Found user_id_field: {user_id_field}")
                # Return user email if it's not a bot record
                if '@' in user_id_field and not user_id_field.startswith('bot_'):
                    logger.debug(f"🔍 Returning user_id: {user_id_field}")
                    return user_id_field
            
            # Check if there are more pages
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
                
        logger.debug(f"🔍 No valid user_id found for chat {chat_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting user_id for chat {chat_id}: {e}")
        return None