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
Support relationship model for managing dynamic SA-to-seller assignments.
"""

import logging
import boto3
from flask import current_app

logger = logging.getLogger(__name__)

_dynamodb_client = None
_support_table_name = None

def get_support_table():
    """Get the DynamoDB support relationship table."""
    from ..config.app_config import CustomerConfig
    dynamodb = boto3.resource('dynamodb', region_name=CustomerConfig.get_aws_region())
    table_name = CustomerConfig.get_config().get('DYNAMODB_RELATIONSHIPS_TABLE_NAME')
    return dynamodb.Table(table_name)

def get_dynamodb_client():
    """Get the DynamoDB client for support relationships."""
    global _dynamodb_client, _support_table_name
    if _dynamodb_client is None:
        try:
            from ..config.app_config import CustomerConfig
            _support_table_name = CustomerConfig.get_value('DYNAMODB_RELATIONSHIPS_TABLE_NAME')
            region = CustomerConfig.get_value('AWS_REGION')
            
            logger.debug(f"Support relationships table name: {_support_table_name}")
            logger.debug(f"Using AWS region: {region}")
            
            # Create DynamoDB client
            _dynamodb_client = boto3.client('dynamodb', region_name=region)
            logger.debug(f"Successfully initialized DynamoDB client for support table: {_support_table_name}")
            return _dynamodb_client
        except Exception as e:
            logger.error(f"DynamoDB client init failed: table={_support_table_name}, error={str(e)}")
            raise
    return _dynamodb_client

def get_support_team(seller_id: str) -> list:
    """
    Get all support team members for a given seller.
    
    Args:
        seller_id (str): The seller's user ID
        
    Returns:
        list: List of support member objects with id and role
    """
    try:
        logger.debug(f"Getting support team: seller={seller_id}")
        client = get_dynamodb_client()
        
        response = client.query(
            TableName=_support_table_name,
            KeyConditionExpression='seller_id = :seller_id',
            ExpressionAttributeValues={
                ':seller_id': {'S': seller_id}
            }
        )
        
        support_members = []
        for item in response.get('Items', []):
            support_member = {
                'support_member_id': item['support_member_id']['S'],
                'support_member_role': item.get('support_member_role', {}).get('S', 'solution_architect')
            }
            support_members.append(support_member)
        
        logger.info(f"Support team query: seller={seller_id}, members={len(support_members)}")
        return support_members
        
    except Exception as e:
        logger.error(f"Get support team failed: seller={seller_id}, error={str(e)}")
        return []

def get_supported_sellers(support_member_id: str) -> list:
    """
    Get all sellers supported by a given support team member.
    
    Args:
        support_member_id (str): The support member's user ID
        
    Returns:
        list: List of seller user IDs
    """
    try:
        logger.debug(f"Getting supported sellers: support_member={support_member_id}")
        client = get_dynamodb_client()
        
        # Since we don't have a GSI, we need to scan the table
        # This is not ideal for large datasets, but works for initial implementation
        response = client.scan(
            TableName=_support_table_name,
            FilterExpression='support_member_id = :support_member_id',
            ExpressionAttributeValues={
                ':support_member_id': {'S': support_member_id}
            }
        )
        
        supported_sellers = []
        for item in response.get('Items', []):
            seller_id = item['seller_id']['S']
            supported_sellers.append(seller_id)
        
        logger.debug(f"Supported sellers query: support_member={support_member_id}, sellers={len(supported_sellers)}")
        return supported_sellers
        
    except Exception as e:
        logger.error(f"Get supported sellers failed: support_member={support_member_id}, error={str(e)}")
        return []

def user_supports_seller(support_user_id: str, seller_id: str) -> bool:
    """
    Check if a support user supports a specific seller.
    
    Args:
        support_user_id (str): The support user's ID
        seller_id (str): The seller's user ID
        
    Returns:
        bool: True if support user supports the seller, False otherwise
    """
    try:
        logger.debug(f"Checking support relationship: support_user={support_user_id}, seller={seller_id}")
        client = get_dynamodb_client()
        
        response = client.get_item(
            TableName=_support_table_name,
            Key={
                'seller_id': {'S': seller_id},
                'support_member_id': {'S': support_user_id}
            }
        )
        
        exists = 'Item' in response
        logger.info(f"Support check result: support_user={support_user_id}, seller={seller_id}, exists={exists}")
        return exists
        
    except Exception as e:
        logger.error(f"Support check failed: support_user={support_user_id}, seller={seller_id}, error={str(e)}")
        return False

def add_support_relationship(seller_id: str, support_member_id: str) -> bool:
    """
    Add a support relationship between a seller and support member.
    
    Args:
        seller_id (str): The seller's user ID
        support_member_id (str): The support member's user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_dynamodb_client()
        
        client.put_item(
            TableName=_support_table_name,
            Item={
                'seller_id': {'S': seller_id},
                'support_member_id': {'S': support_member_id}
            }
        )
        
        logger.debug(f"Added support relationship: {support_member_id} supports {seller_id}")
        return True
        
    except Exception as e:
        logger.error(f"Add support relationship failed: seller={seller_id}, member={support_member_id}, error={str(e)}")
        return False

def remove_support_relationship(seller_id: str, support_member_id: str) -> bool:
    """
    Remove a support relationship between a seller and support member.
    
    Args:
        seller_id (str): The seller's user ID
        support_member_id (str): The support member's user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_dynamodb_client()
        
        client.delete_item(
            TableName=_support_table_name,
            Key={
                'seller_id': {'S': seller_id},
                'support_member_id': {'S': support_member_id}
            }
        )
        
        logger.debug(f"Removed support relationship: {support_member_id} no longer supports {seller_id}")
        return True
        
    except Exception as e:
        logger.error(f"Remove support relationship failed: seller={seller_id}, member={support_member_id}, error={str(e)}")
        return False

def add_support_member(seller_id: str, support_member_id: str, support_member_role: str = 'solution_architect'):
    """Add a support member for a seller."""
    try:
        table = get_support_table()
        
        table.put_item(
            Item={
                'seller_id': seller_id,
                'support_member_id': support_member_id,
                'support_member_role': support_member_role
            }
        )
        
        logger.info(f"Added support member {support_member_id} for seller {seller_id}")
        
    except Exception as e:
        logger.error(f"Add support member failed: seller={seller_id}, member={support_member_id}, error={str(e)}")
        raise

def remove_support_member(seller_id: str, support_member_id: str):
    """Remove a support member for a seller."""
    try:
        table = get_support_table()
        
        table.delete_item(
            Key={
                'seller_id': seller_id,
                'support_member_id': support_member_id
            }
        )
        
        logger.info(f"Removed support member {support_member_id} for seller {seller_id}")
        
    except Exception as e:
        logger.error(f"Remove support member failed: seller={seller_id}, member={support_member_id}, error={str(e)}")
        raise
