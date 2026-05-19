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
File content reader utility for extracting text from uploaded files.
"""
import logging
import boto3
import io
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FileContentReader:
    """Utility class for reading content from uploaded files."""
    
    def __init__(self, s3_client=None):
        """Initialize the file content reader."""
        self.s3_client = s3_client or boto3.client('s3')
    
    def read_file_content(self, s3_url: str, file_type: str, max_size: int = 1024 * 1024) -> Optional[str]:
        """
        Read content from a file stored in S3.
        
        Args:
            s3_url (str): S3 URL of the file
            file_type (str): MIME type of the file
            max_size (int): Maximum file size to read (default 1MB)
            
        Returns:
            Optional[str]: File content as text, or None if unable to read
        """
        try:
            # Parse S3 URL
            if not s3_url.startswith('s3://'):
                logger.error(f"Invalid S3 URL: {s3_url}")
                return None
                
            # Extract bucket and key
            s3_parts = s3_url.replace('s3://', '').split('/', 1)
            if len(s3_parts) != 2:
                logger.error(f"Invalid S3 URL format: {s3_url}")
                return None
                
            bucket_name, s3_key = s3_parts
            
            # Check file size first
            try:
                head_response = self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                file_size = head_response.get('ContentLength', 0)
                
                if file_size > max_size:
                    logger.warning(f"File too large ({file_size} bytes), skipping content extraction")
                    return f"[File too large to read: {file_size} bytes]"
                    
            except Exception as e:
                logger.error(f"Error checking file size: {e}")
                return None
            
            # Download file content
            response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            file_content = response['Body'].read()
            
            # Extract text based on file type
            if file_type.startswith('text/') or file_type == 'application/json':
                # Plain text files
                try:
                    return file_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        return file_content.decode('latin-1')
                    except UnicodeDecodeError:
                        return "[Unable to decode text file]"
                        
            elif file_type == 'text/csv' or s3_key.lower().endswith('.csv'):
                # CSV files
                try:
                    content = file_content.decode('utf-8')
                    # Limit CSV content to first 50 lines for context
                    lines = content.split('\n')[:50]
                    return '\n'.join(lines) + ('\n... [truncated]' if len(content.split('\n')) > 50 else '')
                except UnicodeDecodeError:
                    return "[Unable to decode CSV file]"
                    
            elif file_type == 'application/pdf' or s3_key.lower().endswith('.pdf'):
                # PDF files - basic text extraction
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                    text_content = ""
                    
                    # Extract text from first 10 pages
                    for page_num in range(min(10, len(pdf_reader.pages))):
                        page = pdf_reader.pages[page_num]
                        text_content += page.extract_text() + "\n"
                    
                    return text_content[:5000] + ('\n... [truncated]' if len(text_content) > 5000 else '')
                    
                except ImportError:
                    logger.warning("PyPDF2 not available for PDF text extraction")
                    return "[PDF file - text extraction not available]"
                except Exception as e:
                    logger.error(f"Error extracting PDF text: {e}")
                    return "[Error reading PDF file]"
                    
            else:
                # Unsupported file type
                return f"[Binary file: {file_type}]"
                
        except Exception as e:
            logger.error(f"Error reading file content from {s3_url}: {e}")
            return None
    
    def get_file_summary(self, file_metadata: Dict[str, Any]) -> str:
        """
        Get a summary of the file for inclusion in messages.
        
        Args:
            file_metadata (dict): File metadata including s3_url, type, etc.
            
        Returns:
            str: File summary for the message
        """
        filename = file_metadata.get('original_filename', 'Unknown')
        file_type = file_metadata.get('type', 'Unknown')
        file_size = file_metadata.get('file_size', 'Unknown')
        s3_url = file_metadata.get('s3_url', '')
        
        summary = f"\n--- File: {filename} ---\n"
        summary += f"Type: {file_type}\n"
        summary += f"Size: {file_size} bytes\n"
        summary += f"Location: {s3_url}\n"
        
        # Try to read content for supported file types
        content = self.read_file_content(s3_url, file_type)
        if content:
            summary += f"Content:\n{content}\n"
        else:
            summary += "Content: [Unable to read file content]\n"
            
        summary += "--- End of File ---\n"
        
        return summary