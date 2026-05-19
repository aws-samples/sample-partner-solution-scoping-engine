# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""S3 management module for AWS diagram storage with versioning."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

delete_file_when_uploading_to_s3 = os.getenv('DELETE_LOCAL_FILE_WHEN_S3', 'False')

logger = logging.getLogger(__name__)


def get_s3_config() -> Dict[str, str]:
    """Get S3 configuration from SERA CustomerConfig or environment fallback."""
    try:
        # Try to import SERA CustomerConfig first
        # Calculate the correct path to backend from MCP server location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_path = os.path.join(current_dir, '..', '..', '..', '..', '..', 'backend')
        sys.path.append(backend_path)
        # Import after path modification
        from config.app_config import CustomerConfig
        
        # Load configuration if not already loaded
        if not CustomerConfig._config:
            CustomerConfig.load_config()
        
        return {
            "bucket": CustomerConfig.get_sow_s3_bucket(),
            "region": CustomerConfig.get_aws_region(),
        }
    except Exception:
        # Fallback to environment variables
        return {
            "bucket": os.getenv("S3_UPLOAD_BUCKET"),
            "region": os.getenv("AWS_REGION"),
        }

def create_s3_client():
    """Create S3 client with appropriate configuration."""
    config = get_s3_config()
    return boto3.client('s3', region_name=config["region"])


async def upload_diagram_to_s3(chat_id: str, png_path: str) -> Dict[str, Any]:
    """Upload AWS diagram PNG to S3 with versioning and metadata.
    
    Args:
        chat_id: Unique chat identifier
        png_path: Local path to the PNG file
        
    Returns:
        Dictionary containing S3 upload results
        
    Raises:
        Exception: If upload fails
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        # Construct S3 key following SERA pattern: {chatId}/diagram.png
        #add timestap as suffix as part of the name of the Diagram.png              
        timestamp = datetime.now()        
        s3_key = f"{chat_id}/diagram/diagram.png"
        
        # Get file size
        file_size = os.path.getsize(png_path)
        
        # Prepare metadata - ensure all values are strings to avoid encoding errors
        metadata = {
            "chat-id": str(chat_id),
            "document-type": "diagram",
            "generation-timestamp": timestamp.isoformat(),
            "file-size": str(file_size),
            "generated-by": "aws-diagram-mcp-server"
        }
        
        logger.info(f"Uploading diagram to S3: s3://{config['bucket']}/{s3_key}")
        
        # Upload file to S3
        with open(png_path, 'rb') as f:
            response = s3_client.put_object(
                Bucket=config["bucket"],
                Key=s3_key,
                Body=f,
                ContentType="image/png",
                Metadata=metadata,
                ServerSideEncryption="AES256"
            )
        
        # Get version ID if versioning is enabled
        version_id = response.get('VersionId')
        
        # Construct S3 URL
        s3_url = f"s3://{config['bucket']}/{s3_key}"
        
        # Also upload generation metadata as a separate object
        metadata_key = f"{chat_id}/diagram/diagram.metadata.json"
        metadata_content = {
            "chat_id": chat_id,
            "document_type": "diagram",
            "s3_key": s3_key,
            "s3_url": s3_url,
            "version_id": version_id,
            "file_size": file_size,
            "generation_timestamp": datetime.now().isoformat(),
            "generated_by": "aws-diagram-mcp-server"
        }
        
        s3_client.put_object(
            Bucket=config["bucket"],
            Key=metadata_key,
            Body=json.dumps(metadata_content, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256"
        )
        
        # delete local file if delete_file_when_uploading_to_s3 is True
        if delete_file_when_uploading_to_s3 == 'True':
            logger.info(f"Deleting local file {png_path}")
            os.remove(png_path)
            logger.info(f"Local file {png_path} deleted successfully")

        logger.info(f"Diagram uploaded successfully to {s3_url} (version: {version_id})")

        return {
            "s3_url": s3_url,
            "s3_key": s3_key,
            "version_id": f"{version_id}",
            "file_size": f"{file_size}",
            "bucket": config["bucket"],
            "metadata_key": metadata_key
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 upload failed with {error_code}: {error_msg}")
        raise Exception(f"S3 upload failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}", exc_info=True)
        raise Exception(f"Failed to upload diagram to S3: {str(e)}")


async def download_diagram_from_s3(chat_id: str, local_path: str, version_id: Optional[str] = None) -> str:
    """Download AWS diagram PNG from S3.
    
    Args:
        chat_id: Unique chat identifier
        local_path: Local path where the file should be saved
        version_id: Optional specific version to download
        
    Returns:
        Path to the downloaded file
        
    Raises:
        Exception: If download fails
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        s3_key = f"{chat_id}/diagram/diagram.png"
        
        logger.info(f"Downloading diagram from S3: s3://{config['bucket']}/{s3_key}")
        
        # Prepare download parameters
        download_params = {
            "Bucket": config["bucket"],
            "Key": s3_key
        }
        
        if version_id:
            download_params["VersionId"] = version_id
            logger.info(f"Downloading specific version: {version_id}")
        
        # Download file
        with open(local_path, 'wb') as f:
            s3_client.download_fileobj(
                Fileobj=f,
                **download_params
            )
        
        # Verify download
        if not os.path.exists(local_path):
            raise Exception(f"File was not downloaded to {local_path}")
        
        file_size = os.path.getsize(local_path)
        logger.info(f"Diagram downloaded successfully: {local_path} ({file_size} bytes)")
        
        return local_path
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 download failed with {error_code}: {error_msg}")
        
        if error_code == 'NoSuchKey':
            raise Exception(f"Diagram not found for chat {chat_id}")
        else:
            raise Exception(f"S3 download failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error during S3 download: {e}", exc_info=True)
        raise Exception(f"Failed to download diagram from S3: {str(e)}")


async def list_diagram_versions(chat_id: str) -> Dict[str, Any]:
    """List all versions of an AWS diagram in S3.
    
    Args:
        chat_id: Unique chat identifier
        
    Returns:
        Dictionary containing version information
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        s3_key = f"{chat_id}/diagram/diagram.png"
        
        # List object versions
        response = s3_client.list_object_versions(
            Bucket=config["bucket"],
            Prefix=s3_key,
            MaxKeys=50
        )
        
        versions = []
        for version in response.get('Versions', []):
            if version['Key'] == s3_key:
                versions.append({
                    "version_id": version['VersionId'],
                    "last_modified": version['LastModified'].isoformat(),
                    "size": version['Size'],
                    "is_latest": version.get('IsLatest', False)
                })
        
        # Sort by last modified (newest first)
        versions.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return {
            "chat_id": chat_id,
            "s3_key": s3_key,
            "version_count": len(versions),
            "versions": versions
        }
        
    except ClientError as e:
        logger.error(f"Failed to list diagram versions: {e}")
        return {
            "chat_id": chat_id,
            "s3_key": f"{chat_id}/diagram/diagram.png",
            "version_count": 0,
            "versions": [],
            "error": str(e)
        }


def validate_s3_access() -> bool:
    """Validate that S3 access is properly configured.
    
    Returns:
        True if S3 access is working, False otherwise
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        # Try to head the bucket
        s3_client.head_bucket(Bucket=config["bucket"])
        
        # Check if versioning is enabled
        versioning = s3_client.get_bucket_versioning(Bucket=config["bucket"])
        versioning_status = versioning.get('Status', 'Disabled')
        
        if versioning_status != 'Enabled':
            logger.warning(f"S3 bucket versioning is {versioning_status}, diagram versioning may not work properly")
        
        logger.info(f"S3 access validated for bucket: {config['bucket']}")
        return True
        
    except Exception as e:
        logger.error(f"S3 access validation failed: {e}")
        return False