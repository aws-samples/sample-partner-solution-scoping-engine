"""Enhanced Claude Bedrock client with comprehensive multimodal support"""

import base64
import json
import logging
from typing import Dict, List, Optional, Any, Union
import boto3
from botocore.exceptions import ClientError

from .enhanced_document_processor import FileType, UploadedFile
from ..consts import get_aws_region

logger = logging.getLogger(__name__)


class EnhancedBedrockClient:
    """Enhanced Claude Bedrock client with comprehensive multimodal capabilities."""
    
    def __init__(self, region_name: str = None):
        """Initialize enhanced Bedrock client."""
        self.region_name = region_name or get_aws_region()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
        self.model_id = "us.anthropic.claude-sonnet-4-6"
        self.max_tokens = 20000
        self.temperature = 0  # Set to 0 for deterministic/consistent results
        
    async def analyze_document(
        self,
        file: UploadedFile,
        analysis_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Analyze document using Claude's multimodal capabilities.
        
        Args:
            file: UploadedFile object with content and metadata
            analysis_prompt: Custom analysis prompt
            
        Returns:
            Analysis results with extracted information
        """
        try:
            file_type = file.get_file_type()
            logger.info(f"Analyzing {file_type.value if file_type else 'unknown'} document: {file.filename}")
            
            # Prepare message based on file type
            if file_type in [FileType.PDF, FileType.PNG, FileType.JPG, FileType.JPEG, FileType.GIF, FileType.WEBP, FileType.DOCX]:
                message = self._prepare_multimodal_message(file, analysis_prompt)
            else:
                message = self._prepare_text_message(file, analysis_prompt)
            
            # Call Claude via Bedrock
            response = await self._call_claude(message)
            
            # Process and structure the response
            analysis_result = self._process_claude_response(response, file_type)
            
            logger.info(f"Document analysis completed for {file.filename}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing document {file.filename}: {e}")
            raise Exception(f"Document analysis failed: {e}")
    
    def _prepare_multimodal_message(
        self,
        file: UploadedFile,
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare multimodal message for Claude."""
        
        file_type = file.get_file_type()
        
        # Default comprehensive analysis prompt
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this document for AWS Well-Architected Framework assessment. Extract and identify:
            
            **AWS Services & Resources:**
            - All AWS services mentioned, configured, or depicted
            - Service configurations and settings
            - Resource relationships and dependencies
            
            **Architecture Patterns:**
            - Architectural patterns (microservices, serverless, 3-tier, etc.)
            - Design principles and best practices
            - Anti-patterns or potential issues
            
            **Security Analysis:**
            - Security boundaries (VPCs, security groups, IAM)
            - Encryption configurations
            - Access controls and authentication methods
            - Network security measures
            
            **Performance Considerations:**
            - Performance optimization configurations
            - Caching strategies
            - Load balancing and scaling approaches
            - Database performance considerations
            
            **Cost Optimization:**
            - Cost-related configurations
            - Resource sizing and utilization
            - Reserved instances or savings plans
            - Cost monitoring and optimization strategies
            
            **Operational Excellence:**
            - Monitoring and logging configurations
            - Automation and deployment practices
            - Incident response procedures
            - Change management processes
            
            **Reliability & Availability:**
            - High availability configurations
            - Disaster recovery strategies
            - Backup and restore procedures
            - Fault tolerance mechanisms
            
            **Sustainability:**
            - Resource efficiency measures
            - Environmental impact considerations
            - Sustainable architecture practices
            
            For visual diagrams, describe:
            - Service topology and connections
            - Data flow directions and processing
            - Network architecture and boundaries
            - Any visible best practices or concerns
            
            Provide structured output with confidence scores for each identified element.
            """
        
        # Determine media type
        media_type_map = {
            FileType.PDF: "application/pdf",
            FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            FileType.PNG: "image/png",
            FileType.JPG: "image/jpeg",
            FileType.JPEG: "image/jpeg",
            FileType.GIF: "image/gif",
            FileType.WEBP: "image/webp"
        }
        
        media_type = media_type_map.get(file_type, "application/octet-stream")
        encoded_content = base64.b64encode(file.content).decode('utf-8')
        
        message = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "document" if file_type in [FileType.PDF, FileType.DOCX] else "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded_content
                        }
                    },
                    {
                        "type": "text",
                        "text": analysis_prompt
                    }
                ]
            }
        ]
        
        return message
    
    def _prepare_text_message(
        self,
        file: UploadedFile,
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare text-only message for Claude."""
        
        # Decode content
        try:
            content = file.content.decode('utf-8')
        except UnicodeDecodeError:
            content = file.content.decode('utf-8', errors='ignore')
        
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this text document for AWS Well-Architected Framework assessment. Extract:
            
            1. AWS Services: All mentioned AWS services and configurations
            2. Architecture Patterns: Described patterns and designs
            3. Security Measures: Security configurations and practices
            4. Performance Optimizations: Performance-related configurations
            5. Cost Considerations: Cost optimization strategies
            6. Operational Practices: Monitoring, logging, automation
            7. Reliability Features: HA, DR, backup strategies
            8. Sustainability Aspects: Resource efficiency measures
            
            Provide structured analysis with confidence scores.
            """
        
        full_prompt = f"{analysis_prompt}\n\nDocument Content:\n{content}"
        
        message = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": full_prompt
                    }
                ]
            }
        ]
        
        return message
    
    async def _call_claude(self, message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call Claude via Bedrock with enhanced error handling."""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": message
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            return response_body
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Bedrock API error {error_code}: {error_message}")
            raise Exception(f"Bedrock API error: {error_message}")
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {e}")
            raise Exception(f"Claude API call failed: {e}")
    
    def _process_claude_response(
        self,
        response: Dict[str, Any],
        file_type: Optional[FileType]
    ) -> Dict[str, Any]:
        """Process Claude response into structured format."""
        try:
            # Extract content from Claude response
            content = response.get('content', [])
            if content and isinstance(content, list):
                analysis_text = content[0].get('text', '')
            else:
                analysis_text = str(response)
            
            # Structure the response
            result = {
                "status": "success",
                "file_type": file_type.value if file_type else "unknown",
                "analysis": {
                    "raw_response": analysis_text,
                    "structured_data": self._extract_structured_data(analysis_text)
                },
                "metadata": {
                    "model_id": self.model_id,
                    "processing_time": response.get('usage', {}).get('total_tokens', 0)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Claude response: {e}")
            return {
                "status": "error",
                "error": str(e),
                "raw_response": str(response)
            }
    
    def _extract_structured_data(self, analysis_text: str) -> Dict[str, Any]:
        """Extract structured data from analysis text."""
        # Basic structured extraction - can be enhanced with more sophisticated parsing
        return {
            "aws_services": self._extract_aws_services(analysis_text),
            "architecture_patterns": self._extract_patterns(analysis_text),
            "security_findings": self._extract_security_findings(analysis_text),
            "recommendations": self._extract_recommendations(analysis_text)
        }
    
    def _extract_aws_services(self, text: str) -> List[str]:
        """Extract AWS service mentions from text."""
        # Simple regex-based extraction - can be enhanced
        import re
        aws_services = re.findall(r'\b(?:AWS\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b', text)
        return list(set(aws_services[:10]))  # Limit to top 10
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract architecture patterns from text."""
        patterns = []
        pattern_keywords = ['microservices', 'serverless', '3-tier', 'event-driven', 'monolithic']
        for keyword in pattern_keywords:
            if keyword.lower() in text.lower():
                patterns.append(keyword)
        return patterns
    
    def _extract_security_findings(self, text: str) -> List[str]:
        """Extract security-related findings."""
        findings = []
        security_keywords = ['encryption', 'IAM', 'VPC', 'security group', 'authentication']
        for keyword in security_keywords:
            if keyword.lower() in text.lower():
                findings.append(f"Found {keyword} configuration")
        return findings
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract recommendations from text."""
        # Simple extraction - look for recommendation patterns
        import re
        recommendations = re.findall(r'(?:recommend|suggest|should|consider)[\s\w]*', text, re.IGNORECASE)
        return recommendations[:5]  # Limit to top 5
