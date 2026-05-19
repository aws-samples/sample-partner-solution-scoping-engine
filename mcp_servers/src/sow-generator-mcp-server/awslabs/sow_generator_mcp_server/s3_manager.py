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

"""S3 management module for SOW document storage with versioning."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


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


async def upload_html_to_s3(chat_id: str, html_content: str) -> Dict[str, Any]:
    """Upload HTML content to S3.
    
    Args:
        chat_id: Unique chat identifier
        html_content: HTML content string
        
    Returns:
        Dictionary containing S3 upload results
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        s3_key = f"{chat_id}/sow/StatementOfWork.html"
        
        metadata = {
            "chat-id": chat_id,
            "document-type": "sow_document",
            "generation-timestamp": datetime.now().isoformat(),
            "file-size": str(len(html_content.encode('utf-8'))),
            "generated-by": "sow-generator-mcp-server"
        }
        
        logger.info(f"Uploading HTML to S3: s3://{config['bucket']}/{s3_key}")
        
        response = s3_client.put_object(
            Bucket=config["bucket"],
            Key=s3_key,
            Body=html_content.encode('utf-8'),
            ContentType="text/html",
            Metadata=metadata,
            ServerSideEncryption="AES256"
        )
        
        return {
            "s3_url": f"s3://{config['bucket']}/{s3_key}",
            "s3_key": s3_key,
            "version_id": response.get('VersionId'),
            "file_size": len(html_content.encode('utf-8'))
        }
        
    except Exception as e:
        logger.error(f"Failed to upload HTML to S3: {e}")
        raise


async def download_html_from_s3(chat_id: str) -> str:
    """Download HTML content from S3.
    
    Args:
        chat_id: Unique chat identifier
        
    Returns:
        HTML content as string
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        s3_key = f"{chat_id}/sow/StatementOfWork.html"
        
        logger.info(f"Downloading HTML from S3: s3://{config['bucket']}/{s3_key}")
        
        response = s3_client.get_object(Bucket=config["bucket"], Key=s3_key)
        html_content = response['Body'].read().decode('utf-8')
        
        return html_content
        
    except Exception as e:
        logger.error(f"Failed to download HTML from S3: {e}")
        raise


async def upload_sow_to_s3(chat_id: str, file_path: str) -> Dict[str, Any]:
    """Upload SOW document to S3 with versioning and metadata.
    
    Args:
        chat_id: Unique chat identifier
        file_path: Local path to the document file
        
    Returns:
        Dictionary containing S3 upload results
        
    Raises:
        Exception: If upload fails
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        # Determine file extension from input file
        file_extension = os.path.splitext(file_path)[1]
        # Construct S3 key following SERA pattern: {chatId}/sow/ScopeOfWork.{ext}
        s3_key = f"{chat_id}/sow/StatementOfWork{file_extension}"
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Prepare metadata
        metadata = {
            "chat-id": chat_id,
            "document-type": "sow_document",
            "generation-timestamp": datetime.now().isoformat(),
            "file-size": str(file_size),
            "generated-by": "sow-generator-mcp-server"
        }
        
        logger.info(f"Uploading SOW to S3: s3://{config['bucket']}/{s3_key}")
        
        # Determine content type based on file extension
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if file_extension == ".docx" else "application/pdf"
        
        # Upload file to S3
        with open(file_path, 'rb') as f:
            response = s3_client.put_object(
                Bucket=config["bucket"],
                Key=s3_key,
                Body=f,
                ContentType=content_type,
                Metadata=metadata,
                ServerSideEncryption="AES256"
            )
        
        # Get version ID if versioning is enabled
        version_id = response.get('VersionId')
        
        # Construct S3 URL
        s3_url = f"s3://{config['bucket']}/{s3_key}"
        
        # Also upload generation metadata as a separate object
        metadata_key = f"{chat_id}/sow/StatementOfWork.metadata.json"
        metadata_content = {
            "chat_id": chat_id,
            "document_type": "sow_document",
            "s3_key": s3_key,
            "s3_url": s3_url,
            "version_id": version_id,
            "file_size": file_size,
            "generation_timestamp": datetime.now().isoformat(),
            "generated_by": "sow-generator-mcp-server"
        }
        
        s3_client.put_object(
            Bucket=config["bucket"],
            Key=metadata_key,
            Body=json.dumps(metadata_content, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256"
        )
        
        logger.info(f"SOW uploaded successfully to {s3_url} (version: {version_id})")
        
        return {
            "s3_url": s3_url,
            "s3_key": s3_key,
            "version_id": version_id,
            "file_size": file_size,
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
        raise Exception(f"Failed to upload SOW to S3: {str(e)}")


async def download_sow_from_s3(chat_id: str, local_path: str, version_id: Optional[str] = None) -> str:
    """Download SOW PDF from S3.
    
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
        
        s3_key = f"{chat_id}/sow/StatementOfWork.pdf"
        
        logger.info(f"Downloading SOW from S3: s3://{config['bucket']}/{s3_key}")
        
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
        logger.info(f"SOW downloaded successfully: {local_path} ({file_size} bytes)")
        
        return local_path
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 download failed with {error_code}: {error_msg}")
        
        if error_code == 'NoSuchKey':
            raise Exception(f"SOW document not found for chat {chat_id}")
        else:
            raise Exception(f"S3 download failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error during S3 download: {e}", exc_info=True)
        raise Exception(f"Failed to download SOW from S3: {str(e)}")


async def list_sow_versions(chat_id: str) -> Dict[str, Any]:
    """List all versions of a SOW document in S3.
    
    Args:
        chat_id: Unique chat identifier
        
    Returns:
        Dictionary containing version information
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        s3_key = f"{chat_id}/sow/StatementOfWork.pdf"
        
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
        logger.error(f"Failed to list SOW versions: {e}")
        return {
            "chat_id": chat_id,
            "s3_key": f"{chat_id}/sow/StatementOfWork.pdf",
            "version_count": 0,
            "versions": [],
            "error": str(e)
        }


async def download_text_from_s3(s3_key: str) -> Optional[str]:
    """Download text content from S3.
    
    Args:
        s3_key: S3 key of the file to download
        
    Returns:
        Text content of the file, or None if file doesn't exist
        
    Raises:
        Exception: If download fails for reasons other than file not found
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        logger.info(f"Downloading text file from S3: s3://{config['bucket']}/{s3_key}")
        
        response = s3_client.get_object(Bucket=config["bucket"], Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Successfully downloaded text file ({len(content)} characters)")
        return content
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            logger.info(f"File not found in S3: {s3_key}")
            return None
        else:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to download text from S3: {error_code} - {error_msg}")
            raise Exception(f"S3 download failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error downloading text from S3: {e}", exc_info=True)
        raise Exception(f"Failed to download text from S3: {str(e)}")


async def download_binary_from_s3(s3_key: str) -> Optional[bytes]:
    """Download binary content from S3.
    
    Args:
        s3_key: S3 key of the file to download
        
    Returns:
        Binary content of the file, or None if file doesn't exist
        
    Raises:
        Exception: If download fails for reasons other than file not found
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        logger.info(f"Downloading binary file from S3: s3://{config['bucket']}/{s3_key}")
        
        response = s3_client.get_object(Bucket=config["bucket"], Key=s3_key)
        content = response['Body'].read()
        
        logger.info(f"Successfully downloaded binary file ({len(content)} bytes)")
        return content
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'NoSuchKey':
            logger.info(f"File not found in S3: {s3_key}")
            return None
        else:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to download binary from S3: {error_code} - {error_msg}")
            raise Exception(f"S3 download failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error downloading binary from S3: {e}", exc_info=True)
        raise Exception(f"Failed to download binary from S3: {str(e)}")


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
            logger.warning(f"S3 bucket versioning is {versioning_status}, SOW versioning may not work properly")
        
        logger.info(f"S3 access validated for bucket: {config['bucket']}")
        return True
        
    except Exception as e:
        logger.error(f"S3 access validation failed: {e}")
        return False