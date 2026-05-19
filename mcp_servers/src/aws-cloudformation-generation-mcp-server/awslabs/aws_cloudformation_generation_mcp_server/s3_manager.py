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

"""S3 management module for CloudFormation template storage with versioning."""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

from .models import TemplateFile, TemplateListItem


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


class CloudFormationS3Manager:
    """S3 manager for CloudFormation template storage and retrieval."""
    
    def __init__(self):
        """Initialize S3 manager with configuration."""
        self.config = get_s3_config()
        self.s3_config = Config(
            region_name=self.config["region"],
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=10
        )
        self.s3_client = boto3.client('s3', config=self.s3_config)
        
    def _get_template_s3_key(self, chat_id: str, template_name: str) -> str:
        """Generate S3 key for CloudFormation template.
        
        Args:
            chat_id: Chat session identifier
            template_name: Template filename
            
        Returns:
            S3 key path
        """
        return f"{chat_id}/cloudformation/{template_name}"
    
    def _get_metadata_s3_key(self, chat_id: str, template_name: str) -> str:
        """Generate S3 key for template metadata.
        
        Args:
            chat_id: Chat session identifier
            template_name: Template filename
            
        Returns:
            S3 key path for metadata
        """
        return f"{chat_id}/cloudformation/{template_name}.metadata.json"
    
    async def upload_template(
        self, 
        chat_id: str, 
        template_name: str, 
        content: str,
        project_name: str,
        validation_status: str = "aws_validated"
    ) -> TemplateFile:
        """Upload CloudFormation template to S3 with metadata.
        
        Args:
            chat_id: Chat session identifier
            template_name: Template filename
            content: Template content
            project_name: Project name for metadata
            validation_status: Validation status
            
        Returns:
            TemplateFile model with upload results
            
        Raises:
            Exception: If upload fails
        """
        try:
            s3_key = self._get_template_s3_key(chat_id, template_name)
            timestamp = datetime.now()
            
            # Calculate file size
            content_bytes = content.encode('utf-8')
            file_size = len(content_bytes)
            
            # Prepare metadata
            metadata = {
                "chat-id": str(chat_id),
                "project-name": str(project_name),
                "document-type": "cloudformation-template",
                "template-name": str(template_name),
                "validation-status": str(validation_status),
                "generation-timestamp": timestamp.isoformat(),
                "file-size": str(file_size),
                "generated-by": "aws-cloudformation-generation-mcp-server"
            }
            
            logger.info(f"Uploading CloudFormation template to S3: s3://{self.config['bucket']}/{s3_key}")
            
            # Upload template to S3
            response = self.s3_client.put_object(
                Bucket=self.config["bucket"],
                Key=s3_key,
                Body=content_bytes,
                ContentType="application/x-yaml",
                Metadata=metadata,
                ServerSideEncryption="AES256"
            )
            
            # Get version ID if versioning is enabled
            version_id = response.get('VersionId')
            
            # Construct S3 URL
            s3_url = f"s3://{self.config['bucket']}/{s3_key}"
            
            # Upload metadata as separate object
            await self._upload_template_metadata(
                chat_id, template_name, s3_key, s3_url, version_id, 
                file_size, project_name, validation_status, timestamp
            )
            
            logger.info(f"Template {template_name} uploaded successfully to {s3_url} (version: {version_id})")
            
            return TemplateFile(
                name=template_name,
                s3_url=s3_url,
                s3_key=s3_key,
                version_id=version_id,
                file_size=file_size,
                validation_status=validation_status
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 upload failed with {error_code}: {error_msg}")
            raise Exception(f"S3 upload failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}", exc_info=True)
            raise Exception(f"Failed to upload template to S3: {str(e)}")
    
    async def _upload_template_metadata(
        self,
        chat_id: str,
        template_name: str,
        s3_key: str,
        s3_url: str,
        version_id: Optional[str],
        file_size: int,
        project_name: str,
        validation_status: str,
        timestamp: datetime
    ) -> None:
        """Upload template metadata as separate JSON object.
        
        Args:
            chat_id: Chat session identifier
            template_name: Template filename
            s3_key: S3 key of template
            s3_url: S3 URL of template
            version_id: S3 version ID
            file_size: File size in bytes
            project_name: Project name
            validation_status: Validation status
            timestamp: Upload timestamp
        """
        metadata_key = self._get_metadata_s3_key(chat_id, template_name)
        metadata_content = {
            "chat_id": chat_id,
            "project_name": project_name,
            "template_name": template_name,
            "document_type": "cloudformation-template",
            "s3_key": s3_key,
            "s3_url": s3_url,
            "version_id": version_id,
            "file_size": file_size,
            "validation_status": validation_status,
            "generation_timestamp": timestamp.isoformat(),
            "generated_by": "aws-cloudformation-generation-mcp-server"
        }
        
        self.s3_client.put_object(
            Bucket=self.config["bucket"],
            Key=metadata_key,
            Body=json.dumps(metadata_content, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256"
        )
    
    async def upload_multiple_templates(
        self, 
        chat_id: str, 
        templates: Dict[str, str],
        project_name: str,
        validation_status: str = "aws_validated"
    ) -> List[TemplateFile]:
        """Upload multiple CloudFormation templates to S3.
        
        Args:
            chat_id: Chat session identifier
            templates: Dictionary mapping template names to content
            project_name: Project name for metadata
            validation_status: Validation status
            
        Returns:
            List of TemplateFile models
        """
        uploaded_files = []
        
        for template_name, content in templates.items():
            try:
                template_file = await self.upload_template(
                    chat_id, template_name, content, project_name, validation_status
                )
                uploaded_files.append(template_file)
            except Exception as e:
                logger.error(f"Failed to upload template {template_name}: {e}")
                # Continue with other templates even if one fails
                continue
        
        return uploaded_files
    
    async def download_template(
        self, 
        chat_id: str, 
        template_name: str, 
        version_id: Optional[str] = None
    ) -> str:
        """Download CloudFormation template content from S3.
        
        Args:
            chat_id: Chat session identifier
            template_name: Template filename
            version_id: Optional specific version to download
            
        Returns:
            Template content as string
            
        Raises:
            Exception: If download fails
        """
        try:
            s3_key = self._get_template_s3_key(chat_id, template_name)
            
            logger.info(f"Downloading template from S3: s3://{self.config['bucket']}/{s3_key}")
            
            # Prepare download parameters
            download_params = {
                "Bucket": self.config["bucket"],
                "Key": s3_key
            }
            
            if version_id:
                download_params["VersionId"] = version_id
                logger.info(f"Downloading specific version: {version_id}")
            
            # Download content
            response = self.s3_client.get_object(**download_params)
            content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Template {template_name} downloaded successfully ({len(content)} characters)")
            return content
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 download failed with {error_code}: {error_msg}")
            
            if error_code == 'NoSuchKey':
                raise Exception(f"Template {template_name} not found for chat {chat_id}")
            else:
                raise Exception(f"S3 download failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"Unexpected error during S3 download: {e}", exc_info=True)
            raise Exception(f"Failed to download template from S3: {str(e)}")
    
    async def list_templates(self, chat_id: str) -> List[TemplateListItem]:
        """List all CloudFormation templates for a chat session.
        
        Args:
            chat_id: Chat session identifier
            
        Returns:
            List of TemplateListItem models
        """
        try:
            prefix = f"{chat_id}/cloudformation/"
            
            logger.info(f"Listing templates for chat {chat_id}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.config["bucket"],
                Prefix=prefix,
                MaxKeys=100
            )
            
            templates = []
            for obj in response.get('Contents', []):
                # Skip metadata files
                if obj['Key'].endswith('.metadata.json'):
                    continue
                
                # Extract template name from S3 key
                template_name = obj['Key'].replace(prefix, '')
                if not template_name:  # Skip if empty
                    continue
                
                # Try to get metadata
                try:
                    metadata_response = self.s3_client.get_object(
                        Bucket=self.config["bucket"],
                        Key=self._get_metadata_s3_key(chat_id, template_name)
                    )
                    metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                    validation_status = metadata.get('validation_status', 'unknown')
                except:
                    validation_status = 'unknown'
                
                templates.append(TemplateListItem(
                    name=template_name,
                    s3_key=obj['Key'],
                    s3_url=f"s3://{self.config['bucket']}/{obj['Key']}",
                    version_id=obj.get('VersionId'),
                    size=obj['Size'],
                    last_modified=obj['LastModified'],
                    validation_status=validation_status
                ))
            
            # Sort by last modified (newest first)
            templates.sort(key=lambda x: x.last_modified, reverse=True)
            
            logger.info(f"Found {len(templates)} templates for chat {chat_id}")
            return templates
            
        except ClientError as e:
            logger.error(f"Failed to list templates: {e}")
            return []
        
        except Exception as e:
            logger.error(f"Unexpected error listing templates: {e}", exc_info=True)
            return []
    
    def validate_s3_access(self) -> bool:
        """Validate that S3 access is properly configured.
        
        Returns:
            True if S3 access is working, False otherwise
        """
        try:
            # Try to head the bucket
            self.s3_client.head_bucket(Bucket=self.config["bucket"])
            
            # Check if versioning is enabled
            versioning = self.s3_client.get_bucket_versioning(Bucket=self.config["bucket"])
            versioning_status = versioning.get('Status', 'Disabled')
            
            if versioning_status != 'Enabled':
                logger.warning(f"S3 bucket versioning is {versioning_status}, template versioning may not work properly")
            
            logger.info(f"S3 access validated for bucket: {self.config['bucket']}")
            return True
            
        except Exception as e:
            logger.error(f"S3 access validation failed: {e}")
            return False