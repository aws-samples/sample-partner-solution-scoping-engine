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

"""S3 management module for cost analysis document storage."""

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


async def upload_pricing_report_to_s3(chat_id: str, report_content: str, filename: str = 'pricing', format: str = 'markdown') -> Dict[str, Any]:
    """Upload cost analysis report to S3.
    
    Args:
        chat_id: Unique chat identifier
        report_content: Content of the cost analysis report
        filename: Base filename for the report (without extension)
        format: Format of the report ('markdown' or 'csv')
        
    Returns:
        Dictionary containing S3 upload results
        
    Raises:
        Exception: If upload fails
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        # Construct S3 key following SERA pattern: {chatId}/pricing/pricing.{ext}
        # Always use 'pricing' as the base filename for consistency
        file_extension = 'md' if format == 'markdown' else 'csv'
        s3_key = f"{chat_id}/pricing/pricing.{file_extension}"
        
        # Get content size
        content_bytes = report_content.encode('utf-8')
        content_size = len(content_bytes)
        
        # Prepare metadata
        metadata = {
            "chat-id": chat_id,
            "document-type": "cost-analysis",
            "filename": filename,
            "format": format,
            "generation-timestamp": datetime.now().isoformat(),
            "file-size": str(content_size),
            "generated-by": "cost-analysis-mcp-server"
        }
        
        # Determine content type
        content_type = "text/markdown" if format == 'markdown' else "text/csv"
        
        logger.info(f"Uploading cost analysis report to S3: s3://{config['bucket']}/{s3_key}")
        
        # Upload content to S3
        response = s3_client.put_object(
            Bucket=config["bucket"],
            Key=s3_key,
            Body=content_bytes,
            ContentType=content_type,
            Metadata=metadata,
            ServerSideEncryption="AES256"
        )
        
        # Get version ID if versioning is enabled
        version_id = response.get('VersionId')
        
        # Construct S3 URL
        s3_url = f"s3://{config['bucket']}/{s3_key}"
        
        # Also upload generation metadata as a separate object
        metadata_key = f"{chat_id}/pricing/pricing.metadata.json"
        metadata_content = {
            "chat_id": chat_id,
            "document_type": "cost-analysis",
            "filename": "pricing",
            "format": format,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "version_id": version_id,
            "file_size": content_size,
            "generation_timestamp": datetime.now().isoformat(),
            "generated_by": "cost-analysis-mcp-server"
        }
        
        s3_client.put_object(
            Bucket=config["bucket"],
            Key=metadata_key,
            Body=json.dumps(metadata_content, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256"
        )
        
        logger.info(f"Cost analysis report uploaded successfully to {s3_url} (version: {version_id})")
        
        return {
            "s3_url": s3_url,
            "s3_key": s3_key,
            "version_id": version_id,
            "file_size": content_size,
            "bucket": config["bucket"],
            "metadata_key": metadata_key,
            "filename": filename,
            "format": format
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 upload failed with {error_code}: {error_msg}")
        raise Exception(f"S3 upload failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}", exc_info=True)
        raise Exception(f"Failed to upload cost analysis report to S3: {str(e)}")


async def download_pricing_report_from_s3(chat_id: str, filename: str = 'pricing', format: str = 'markdown', version_id: Optional[str] = None) -> str:
    """Download cost analysis report from S3.
    
    Args:
        chat_id: Unique chat identifier
        filename: Base filename for the report (without extension)
        format: Format of the report ('markdown' or 'csv')
        version_id: Optional specific version to download
        
    Returns:
        Content of the downloaded report
        
    Raises:
        Exception: If download fails
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        file_extension = 'md' if format == 'markdown' else 'csv'
        s3_key = f"{chat_id}/pricing/pricing.{file_extension}"
        
        logger.info(f"Downloading cost analysis report from S3: s3://{config['bucket']}/{s3_key}")
        
        # Prepare download parameters
        download_params = {
            "Bucket": config["bucket"],
            "Key": s3_key
        }
        
        if version_id:
            download_params["VersionId"] = version_id
            logger.info(f"Downloading specific version: {version_id}")
        
        # Download file content
        response = s3_client.get_object(**download_params)
        content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Cost analysis report downloaded successfully ({len(content)} characters)")
        
        return content
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 download failed with {error_code}: {error_msg}")
        
        if error_code == 'NoSuchKey':
            raise Exception(f"Cost analysis report '{filename}' not found for chat {chat_id}")
        else:
            raise Exception(f"S3 download failed: {error_msg}")
    
    except Exception as e:
        logger.error(f"Unexpected error during S3 download: {e}", exc_info=True)
        raise Exception(f"Failed to download cost analysis report from S3: {str(e)}")


async def list_pricing_reports(chat_id: str) -> Dict[str, Any]:
    """List all pricing reports for a chat in S3.
    
    Args:
        chat_id: Unique chat identifier
        
    Returns:
        Dictionary containing list of pricing reports
    """
    try:
        config = get_s3_config()
        s3_client = create_s3_client()
        
        pricing_prefix = f"{chat_id}/pricing/"
        
        # List all objects under the pricing prefix
        response = s3_client.list_objects_v2(
            Bucket=config["bucket"],
            Prefix=pricing_prefix,
            MaxKeys=100
        )
        
        reports = []
        for obj in response.get('Contents', []):
            key = obj['Key']
            # Skip metadata files
            if key.endswith('.metadata.json'):
                continue
                
            # Extract filename and format
            filename_with_ext = key.replace(pricing_prefix, '')
            if '.' in filename_with_ext:
                filename = filename_with_ext.rsplit('.', 1)[0]
                extension = filename_with_ext.rsplit('.', 1)[1]
                format_type = 'markdown' if extension == 'md' else 'csv' if extension == 'csv' else 'unknown'
            else:
                filename = filename_with_ext
                format_type = 'unknown'
            
            reports.append({
                "filename": filename,
                "format": format_type,
                "s3_key": key,
                "last_modified": obj['LastModified'].isoformat(),
                "size": obj['Size']
            })
        
        # Sort by last modified (newest first)
        reports.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return {
            "chat_id": chat_id,
            "pricing_prefix": pricing_prefix,
            "report_count": len(reports),
            "reports": reports
        }
        
    except ClientError as e:
        logger.error(f"Failed to list pricing reports: {e}")
        return {
            "chat_id": chat_id,
            "pricing_prefix": f"{chat_id}/pricing/",
            "report_count": 0,
            "reports": [],
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
            logger.warning(f"S3 bucket versioning is {versioning_status}, cost analysis report versioning may not work properly")
        
        logger.info(f"S3 access validated for bucket: {config['bucket']}")
        return True
        
    except Exception as e:
        logger.error(f"S3 access validation failed: {e}")
        return False