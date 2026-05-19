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

"""S3 management module for POC funding document retrieval."""

import logging
import os
from typing import Dict, Optional, Tuple, TYPE_CHECKING
from urllib.parse import urlparse

import boto3
import requests
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from .config import ConfigManager

logger = logging.getLogger(__name__)


class S3Manager:
    """Manages file operations for POC funding document retrieval from S3 URLs and public URLs."""
    
    def __init__(self, region: str = "us-east-1", config: Optional['ConfigManager'] = None):
        """Initialize S3Manager with AWS region.
        
        Args:
            region: AWS region to use (fallback if config not provided)
            config: Optional ConfigManager instance to get region from
        """
        # Determine region in order of preference:
        # 1. From ConfigManager (which loads from POC_FUNDING_AWS_REGION or AWS_REGION env vars)
        # 2. From standard AWS environment variables
        # 3. From provided region parameter
        # 4. Default to us-east-1
        
        if config and hasattr(config, 'bedrock') and hasattr(config.bedrock, 'region'):
            self.region = config.bedrock.region
            logger.info(f"Using AWS region from ConfigManager: {self.region}")
        elif os.getenv('AWS_REGION'):
            self.region = os.getenv('AWS_REGION')
            logger.info(f"Using AWS region from AWS_REGION environment variable: {self.region}")
        elif os.getenv('AWS_DEFAULT_REGION'):
            self.region = os.getenv('AWS_DEFAULT_REGION')
            logger.info(f"Using AWS region from AWS_DEFAULT_REGION environment variable: {self.region}")
        else:
            self.region = region
            logger.info(f"Using fallback AWS region: {self.region}")
            
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """Initialize S3 client with proper configuration."""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            logger.info(f"S3 client initialized for region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def parse_s3_url(self, s3_url: str) -> Tuple[str, str]:
        """Parse S3 URL to extract bucket and key.
        
        Args:
            s3_url: S3 URL in format s3://bucket/key
            
        Returns:
            Tuple of (bucket, key)
            
        Raises:
            ValueError: If URL format is invalid
        """
        try:
            parsed = urlparse(s3_url)
            if parsed.scheme != 's3':
                raise ValueError(f"Invalid S3 URL scheme: {parsed.scheme}")
            
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            if not bucket or not key:
                raise ValueError(f"Invalid S3 URL format: {s3_url}")
            
            return bucket, key
        except Exception as e:
            logger.error(f"Failed to parse S3 URL {s3_url}: {e}")
            raise ValueError(f"Invalid S3 URL format: {s3_url}")
    
    def download_file_content(self, url: str) -> bytes:
        """Download file content from S3 URL or public HTTP/HTTPS URL.
        
        Args:
            url: S3 URL (s3://bucket/key) or public URL (http://... or https://...)
            
        Returns:
            File content as bytes
            
        Raises:
            ValueError: If URL is invalid or file cannot be downloaded
        """
        parsed_url = urlparse(url)
        
        if parsed_url.scheme == 's3':
            return self._download_from_s3(url)
        elif parsed_url.scheme in ('http', 'https'):
            return self._download_from_public_url(url)
        else:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}. Only s3://, http://, and https:// are supported.")
    
    def _download_from_s3(self, s3_url: str) -> bytes:
        """Download file content from S3.
        
        Args:
            s3_url: S3 URL to download from
            
        Returns:
            File content as bytes
        """
        try:
            bucket, key = self.parse_s3_url(s3_url)
            
            logger.info(f"Downloading file from S3: {bucket}/{key}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            logger.info(f"Successfully downloaded {len(content)} bytes from S3: {s3_url}")
            return content
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise ValueError(f"File not found in S3: {s3_url}")
            elif error_code == 'NoSuchBucket':
                raise ValueError(f"S3 bucket not found: {bucket}")
            elif error_code == 'AccessDenied':
                raise ValueError(f"Access denied to S3 file: {s3_url}")
            else:
                raise ValueError(f"S3 error downloading {s3_url}: {e}")
        except Exception as e:
            logger.error(f"Failed to download file from S3 {s3_url}: {e}")
            raise ValueError(f"Failed to download file from S3: {e}")
    
    def _download_from_public_url(self, url: str) -> bytes:
        """Download file content from public HTTP/HTTPS URL.
        
        Args:
            url: Public HTTP/HTTPS URL to download from
            
        Returns:
            File content as bytes
        """
        try:
            logger.info(f"Downloading file from public URL: {url}")
            
            # Set reasonable timeout and headers
            headers = {
                'User-Agent': 'POC-Funding-Reviewer-MCP-Server/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()  # Raises HTTPError for bad responses
            
            # Check content length if available
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > 50:  # 50MB limit for public downloads
                    raise ValueError(f"File too large: {size_mb:.1f}MB (max 50MB)")
            
            # Download content with size limit
            content = b''
            max_size = 50 * 1024 * 1024  # 50MB limit
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
                    if len(content) > max_size:
                        raise ValueError(f"File too large: exceeds 50MB limit")
            
            logger.info(f"Successfully downloaded {len(content)} bytes from public URL: {url}")
            return content
            
        except requests.exceptions.Timeout:
            raise ValueError(f"Timeout downloading from public URL: {url}")
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"HTTP error downloading from public URL {url}: {e}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error downloading from public URL {url}: {e}")
        except Exception as e:
            logger.error(f"Failed to download file from public URL {url}: {e}")
            raise ValueError(f"Failed to download file from public URL: {e}")
    
    def get_file_metadata(self, url: str) -> Dict[str, any]:
        """Get file metadata from S3 URL or public HTTP/HTTPS URL.
        
        Args:
            url: S3 URL or public URL to get metadata for
            
        Returns:
            Dictionary with file metadata
        """
        parsed_url = urlparse(url)
        
        if parsed_url.scheme == 's3':
            return self._get_s3_metadata(url)
        elif parsed_url.scheme in ('http', 'https'):
            return self._get_public_url_metadata(url)
        else:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")
    
    def _get_s3_metadata(self, s3_url: str) -> Dict[str, any]:
        """Get file metadata from S3.
        
        Args:
            s3_url: S3 URL to get metadata for
            
        Returns:
            Dictionary with file metadata
        """
        try:
            bucket, key = self.parse_s3_url(s3_url)
            
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            return {
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'source': 's3'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise ValueError(f"File not found in S3: {s3_url}")
            else:
                raise ValueError(f"S3 error getting metadata for {s3_url}: {e}")
        except Exception as e:
            logger.error(f"Failed to get file metadata from S3 {s3_url}: {e}")
            raise ValueError(f"Failed to get file metadata from S3: {e}")
    
    def _get_public_url_metadata(self, url: str) -> Dict[str, any]:
        """Get file metadata from public HTTP/HTTPS URL using HEAD request.
        
        Args:
            url: Public URL to get metadata for
            
        Returns:
            Dictionary with file metadata
        """
        try:
            logger.info(f"Getting metadata for public URL: {url}")
            
            headers = {
                'User-Agent': 'POC-Funding-Reviewer-MCP-Server/1.0'
            }
            
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            return {
                'size': int(response.headers.get('content-length', 0)),
                'content_type': response.headers.get('content-type', 'application/octet-stream'),
                'last_modified': response.headers.get('last-modified'),
                'etag': response.headers.get('etag', '').strip('"'),
                'source': 'public_url'
            }
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get metadata for public URL {url}: {e}")
            # Return minimal metadata if HEAD request fails
            return {
                'size': 0,
                'content_type': 'application/octet-stream',
                'last_modified': None,
                'etag': '',
                'source': 'public_url'
            }