"""Claude Bedrock client for multimodal document analysis"""

import base64
import json
from typing import Dict, List, Optional, Any, Union
import boto3
from botocore.exceptions import ClientError

from ..core.logger import setup_logger
from ..core.error_handler import DocumentProcessingError
from ..consts import get_aws_region
from .drawio_decoder import DrawioDecoder

logger = setup_logger(__name__)


class ClaudeBedrockClient:
    """
    Claude Bedrock client for multimodal document analysis.
    
    Provides comprehensive document processing capabilities using Claude's
    advanced multimodal understanding through Amazon Bedrock.
    """
    
    def __init__(self, region_name: str = None):
        """Initialize Claude Bedrock client."""
        from botocore.config import Config
        
        self.region_name = region_name or get_aws_region()
        
        # Issue 5 Fix: Add timeout configuration to prevent slow API calls from blocking
        bedrock_config = Config(
            read_timeout=120,  # 2 minutes max for reading response
            connect_timeout=10,  # 10 seconds to establish connection
            retries={
                'max_attempts': 2,  # Reduce retries for faster failure
                'mode': 'adaptive'
            }
        )
        
        self.bedrock_client = boto3.client(
            'bedrock-runtime', 
            region_name=self.region_name,
            config=bedrock_config
        )
        self.model_id = "us.anthropic.claude-sonnet-4-6"
        
    async def analyze_document(
        self,
        document_content: Union[str, bytes],
        document_type: str,
        analysis_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Analyze document using Claude's multimodal capabilities.
        
        Args:
            document_content: Document content (text or binary)
            document_type: Document type (pdf, txt, png, jpeg)
            analysis_prompt: Custom analysis prompt
            
        Returns:
            Analysis results with extracted information
        """
        try:
            logger.info(f"Analyzing {document_type} document with Claude")
            
            # Prepare message based on document type
            if document_type.lower() in ['pdf', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp']:
                message = await self._prepare_multimodal_message(
                    document_content, document_type, analysis_prompt
                )
            else:
                message = await self._prepare_text_message(
                    document_content, analysis_prompt
                )
            
            # Call Claude via Bedrock
            response = await self._call_claude(message)
            
            # Process and structure the response
            analysis_result = await self._process_claude_response(response, document_type)
            
            logger.info(f"Document analysis completed for {document_type}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            raise DocumentProcessingError(f"Document analysis failed: {e}")
    
    async def _prepare_multimodal_message(
        self,
        document_content: bytes,
        document_type: str,
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare multimodal message for Claude."""
        
        # Default analysis prompt for architecture documents
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this document for AWS Well-Architected Framework assessment.
            
            CRITICAL EVIDENCE-BASED IDENTIFICATION RULES:
            =============================================
            1. ONLY identify AWS services that have EXPLICIT evidence in the document:
               - CloudFormation resource types (AWS::ServiceName::ResourceType)
               - Terraform resource types (aws_service_name)
               - Explicit service names mentioned in text
               - Clear visual icons/labels in architecture diagrams
            
            2. DO NOT infer or assume services based on:
               - Common architectural patterns (e.g., don't assume Lambda just because serverless is mentioned)
               - Services that "typically" accompany detected services
               - Best practice recommendations
            
            3. For each AWS service identified, you MUST provide:
               - Service name
               - Evidence type: "CFN_RESOURCE" | "TERRAFORM_RESOURCE" | "TEXT_MENTION" | "DIAGRAM_ICON"
               - Exact evidence: The specific resource type, text quote, or description
               - Confidence: "HIGH" (explicit resource type) | "MEDIUM" (clear text mention) | "LOW" (visual only)
            
            4. If a service is commonly associated with a pattern but NOT explicitly present,
               list it under "POTENTIAL_SERVICES" (not "IDENTIFIED_SERVICES")
            
            EXTRACT THE FOLLOWING:
            ======================
            1. AWS Services (with evidence as described above)
            
            2. Architecture Patterns - ONLY claim patterns with evidence:
               - Multi-Tier: Requires explicit separation of presentation/logic/data layers
               - Microservices: Requires multiple independent services with separate deployments
               - Serverless: Requires Lambda, Fargate, or similar serverless compute
               - Event-Driven: Requires SNS, SQS, EventBridge, or Kinesis
               - Do NOT claim patterns without supporting evidence
            
            3. Security Features - Look for SPECIFIC configurations:
               - Bedrock Guardrails (ContentPolicyConfig, SensitiveInformationPolicyConfig)
               - WAF Rules (AWS::WAFv2::WebACL, rate limiting, managed rules)
               - VPC Endpoints (AWS::EC2::VPCEndpoint, PrivateLink)
               - VPC Flow Logs (AWS::EC2::FlowLog)
               - KMS encryption configurations
               - Cognito advanced security (AdvancedSecurityMode)
               - CloudFront signed URLs (KeyGroup, PublicKey)
            
            4. Sustainability Features - Look for:
               - Graviton/ARM instances (m7g, c7g, r7g, t4g, m6g, c6g instance types)
               - S3 lifecycle policies (Transition rules to IA/Glacier)
               - Auto Scaling configurations
            
            5. Reliability Features - Look for:
               - Multi-AZ deployments (MultiAZ: true, AvailabilityZones)
               - DynamoDB Point-in-Time Recovery (PointInTimeRecoveryEnabled)
               - Backup configurations
               - ElastiCache automatic failover
            
            6. Data Flows and Network Topology
            
            7. Operational Elements (CloudWatch, logging, monitoring)
            
            OUTPUT FORMAT:
            ==============
            Provide structured output with:
            - IDENTIFIED_SERVICES: Services with explicit evidence
            - POTENTIAL_SERVICES: Services that might exist but lack explicit evidence
            - ARCHITECTURE_PATTERNS: Only patterns with supporting evidence
            - SECURITY_FEATURES: Specific security configurations found
            - SUSTAINABILITY_FEATURES: Efficiency configurations found
            - RELIABILITY_FEATURES: HA/DR configurations found
            - CONFIDENCE_SCORES: For each identified element
            """
        
        # Encode document content and set media type
        if document_type.lower() == 'pdf':
            media_type = "application/pdf"
        elif document_type.lower() == 'docx':
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif document_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            media_type = f"image/{document_type.lower()}"
        else:
            raise DocumentProcessingError(f"Unsupported document type: {document_type}")
        
        encoded_content = base64.b64encode(document_content).decode('utf-8')
        
        # Format message based on document type
        if document_type.lower() in ['pdf', 'docx']:
            # Documents use document type
            message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
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
        else:
            # Images use image type
            message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
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
    
    async def _prepare_text_message(
        self,
        document_content: Union[str, bytes],
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare text-only message for Claude."""
        
        if isinstance(document_content, bytes):
            text_content = document_content.decode('utf-8', errors='ignore')
        else:
            text_content = document_content
        
        # Check if this is a draw.io/diagrams.net XML file
        if DrawioDecoder.is_drawio_file(document_content):
            logger.info("🎨 Detected draw.io diagram file - decoding compressed content...")
            decoded_text, metadata = DrawioDecoder.decode_drawio(document_content)
            
            # Use the decoded content instead of raw XML
            document_content = decoded_text
            
            # Add metadata context to the prompt
            services_found = metadata.get('identified_services', [])
            patterns_found = metadata.get('architectural_patterns', [])
            
            if services_found or patterns_found:
                logger.info(f"✅ Draw.io decode successful: {len(services_found)} services, {len(patterns_found)} patterns")
            else:
                logger.warning("⚠️ Draw.io file decoded but no AWS services found in labels")
        else:
            document_content = text_content
        
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this text/IaC document for AWS Well-Architected Framework assessment.
            
            CRITICAL EVIDENCE-BASED IDENTIFICATION RULES:
            =============================================
            1. For CloudFormation templates, extract ONLY services with explicit AWS::* resource types
            2. For Terraform templates, extract ONLY services with explicit aws_* resource types
            3. DO NOT infer services that are not explicitly defined
            4. DO NOT assume services based on architectural patterns
            
            For each AWS service, provide:
            - Service name
            - Evidence type: "CFN_RESOURCE" | "TERRAFORM_RESOURCE" | "TEXT_MENTION"
            - Exact evidence: Resource type or text quote
            - Confidence: "HIGH" (explicit resource) | "MEDIUM" (text mention) | "LOW" (inferred)
            
            EXTRACT:
            ========
            1. AWS Services with explicit evidence (CloudFormation AWS::* or Terraform aws_*)
            2. Architecture Patterns (only with supporting evidence)
            3. Security Features:
               - Bedrock Guardrails (ContentPolicyConfig, blockedInputMessaging)
               - WAF Rules (WebACL, RateBasedStatement, ManagedRuleGroupStatement)
               - VPC Endpoints (VPCEndpoint, PrivateDnsEnabled)
               - VPC Flow Logs (FlowLog, LogDestination)
               - Encryption (KMS keys, SSE configurations)
               - Cognito Advanced Security (AdvancedSecurityMode)
            4. Sustainability Features:
               - Graviton instances (m7g, c7g, r7g, t4g, m6g, c6g, t4g)
               - S3 Lifecycle rules (Transition, ExpirationInDays)
            5. Reliability Features:
               - Multi-AZ (MultiAZ, AvailabilityZones)
               - PITR (PointInTimeRecoveryEnabled)
               - Automatic failover configurations
            6. Configuration details for each resource
            
            OUTPUT FORMAT:
            ==============
            - IDENTIFIED_SERVICES: Only services with explicit evidence
            - POTENTIAL_SERVICES: Services that might exist but lack evidence
            - SECURITY_CONFIGURATIONS: Specific security settings found
            - SUSTAINABILITY_CONFIGURATIONS: Efficiency settings found
            - RELIABILITY_CONFIGURATIONS: HA/DR settings found
            """
        
        message = [
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": f"{analysis_prompt}\n\nDocument Content:\n{document_content}"
                    }
                ]
            }
        ]
        
        return message
    
    async def _call_claude(self, message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call Claude via Bedrock API."""
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,  # Keep original for comprehensive analysis
            "temperature": 0,  # Set to 0 for deterministic/consistent results
            "messages": message
        }
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            return response_body
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise DocumentProcessingError(f"Bedrock API call failed: {e}")
    
    async def _process_claude_response(
        self,
        response: Dict[str, Any],
        document_type: str
    ) -> Dict[str, Any]:
        """Process Claude's response into structured format."""
        
        try:
            # Extract content from Claude's response
            content = response.get('content', [])
            if not content:
                raise DocumentProcessingError("Empty response from Claude")
            
            # Get the text content
            text_content = ""
            for item in content:
                if item.get('type') == 'text':
                    text_content += item.get('text', '')
            
            # Structure the analysis result
            analysis_result = {
                "document_type": document_type,
                "raw_analysis": text_content,
                "extracted_data": await self._extract_structured_data(text_content),
                "confidence_score": 0.8,  # Default confidence
                "processing_metadata": {
                    "model_id": self.model_id,
                    "region": self.region_name,
                    "tokens_used": response.get('usage', {}).get('output_tokens', 0)
                }
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing Claude response: {e}")
            raise DocumentProcessingError(f"Response processing failed: {e}")
    
    async def _extract_structured_data(self, text_content: str) -> Dict[str, Any]:
        """Extract structured data from Claude's text response."""
        
        # Initialize structured data
        structured_data = {
            "aws_services": [],
            "architectural_patterns": [],
            "security_boundaries": [],
            "data_flows": [],
            "compliance_indicators": [],
            "performance_elements": [],
            "cost_elements": [],
            "operational_elements": []
        }
        
        # Simple extraction logic (can be enhanced with more sophisticated parsing)
        lines = text_content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections
            if "aws services" in line.lower():
                current_section = "aws_services"
            elif "architecture" in line.lower() and "pattern" in line.lower():
                current_section = "architectural_patterns"
            elif "security" in line.lower():
                current_section = "security_boundaries"
            elif "data flow" in line.lower():
                current_section = "data_flows"
            elif "compliance" in line.lower():
                current_section = "compliance_indicators"
            elif "performance" in line.lower():
                current_section = "performance_elements"
            elif "cost" in line.lower():
                current_section = "cost_elements"
            elif "operational" in line.lower():
                current_section = "operational_elements"
            elif current_section and line.startswith(('-', '*', '•')):
                # Extract list items
                item = line.lstrip('-*•').strip()
                if item and current_section in structured_data:
                    structured_data[current_section].append({
                        "item": item,
                        "confidence": 0.8
                    })
        
        return structured_data


class DocumentValidator:
    """Validate document formats and content."""
    
    SUPPORTED_FORMATS = {
        'pdf': ['application/pdf'],
        'txt': ['text/plain', 'text/txt'],
        'png': ['image/png'],
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg']
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def validate_document(
        cls,
        document_content: bytes,
        document_type: str,
        filename: str = None
    ) -> Dict[str, Any]:
        """
        Validate document format and content.
        
        Args:
            document_content: Document binary content
            document_type: Expected document type
            filename: Optional filename for additional validation
            
        Returns:
            Validation result with status and details
        """
        validation_result = {
            "valid": True,
            "document_type": document_type.lower(),
            "file_size": len(document_content),
            "errors": [],
            "warnings": []
        }
        
        # Check file size
        if len(document_content) > cls.MAX_FILE_SIZE:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"File size {len(document_content)} exceeds maximum {cls.MAX_FILE_SIZE}"
            )
        
        # Check document type support
        if document_type.lower() not in cls.SUPPORTED_FORMATS:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Unsupported document type: {document_type}"
            )
        
        # Basic content validation
        if len(document_content) == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Empty document content")
        
        # PDF-specific validation
        if document_type.lower() == 'pdf':
            if not document_content.startswith(b'%PDF'):
                validation_result["warnings"].append(
                    "Document may not be a valid PDF file"
                )
        
        # Image-specific validation
        if document_type.lower() in ['png', 'jpg', 'jpeg']:
            # Basic image header validation
            if document_type.lower() == 'png' and not document_content.startswith(b'\x89PNG'):
                validation_result["warnings"].append(
                    "Document may not be a valid PNG file"
                )
            elif document_type.lower() in ['jpg', 'jpeg'] and not document_content.startswith(b'\xff\xd8'):
                validation_result["warnings"].append(
                    "Document may not be a valid JPEG file"
                )
        
        return validation_result
