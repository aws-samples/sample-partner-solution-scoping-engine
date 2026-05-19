"""Enhanced Claude Bedrock client with Quality Requirements"""

import base64
import json
import logging
from typing import Dict, List, Optional, Any, Union
import boto3
from botocore.exceptions import ClientError

from .enhanced_document_processor import FileType, UploadedFile
from ..consts import get_aws_region

logger = logging.getLogger(__name__)


class QualityEnhancedBedrockClient:
    """Enhanced Claude Bedrock client with comprehensive quality requirements."""
    
    def __init__(self, region_name: str = None):
        """Initialize enhanced Bedrock client with quality focus."""
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
        Analyze document with quality requirements enforcement.
        
        Args:
            file: UploadedFile object with content and metadata
            analysis_prompt: Custom analysis prompt (uses quality-enhanced default)
            
        Returns:
            High-quality analysis results with architecture-specific recommendations
        """
        try:
            file_type = file.get_file_type()
            logger.info(f"Analyzing {file_type.value if file_type else 'unknown'} document: {file.filename}")
            
            # Prepare message with quality-enhanced prompts
            if file_type in [FileType.PDF, FileType.PNG, FileType.JPG, FileType.JPEG, FileType.GIF, FileType.WEBP, FileType.DOCX]:
                message = self._prepare_quality_multimodal_message(file, analysis_prompt)
            else:
                message = self._prepare_quality_text_message(file, analysis_prompt)
            
            # Call Claude via Bedrock
            response = await self._call_claude(message)
            
            # Process with quality validation
            analysis_result = self._process_quality_response(response, file_type)
            
            logger.info(f"Quality-enhanced analysis completed for {file.filename}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in quality-enhanced analysis {file.filename}: {e}")
            raise Exception(f"Quality-enhanced analysis failed: {e}")
    
    def _prepare_quality_multimodal_message(
        self,
        file: UploadedFile,
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare multimodal message with quality requirements."""
        
        file_type = file.get_file_type()
        
        # Enhanced analysis prompt with quality requirements
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this document for AWS Well-Architected Framework assessment with HIGH QUALITY REQUIREMENTS:

            **ANALYSIS QUALITY REQUIREMENTS**:
            - Provide architecture-specific recommendations, not generic advice
            - Reference specific AWS services found in the uploaded documents
            - Consider the business context (e.g., airline booking system needs high availability)
            - Include compliance requirements relevant to the industry
            - Provide concrete implementation steps, not just high-level suggestions
            - Show specific cost estimates and optimization opportunities

            **DETAILED ANALYSIS REQUIRED:**

            **AWS Services & Resources (Architecture-Specific)**:
            - Identify ALL AWS services with their specific configurations (instance types, storage sizes, network settings)
            - Note service versions, regions, availability zones
            - Document exact service relationships and data flows with protocols and ports
            - Identify missing services that should be present for this specific architecture
            - Reference actual service names, ARNs, and configurations found in documents

            **Business Context Analysis**:
            - Determine business domain from application context (e-commerce, healthcare, financial, etc.)
            - Identify performance requirements from architecture patterns (real-time, batch, streaming)
            - Assess availability requirements from redundancy patterns (99.9%, 99.99%, 99.999%)
            - Evaluate security requirements from data sensitivity (PII, PHI, financial data)
            - Consider regulatory environment based on industry vertical

            **Industry-Specific Compliance Requirements**:
            - Healthcare: HIPAA, HITECH compliance requirements with specific controls
            - Financial: SOX, PCI-DSS, regulatory requirements with implementation details
            - Government: FedRAMP, FISMA compliance needs with security controls
            - Retail: PCI-DSS for payment processing with specific requirements
            - Education: FERPA compliance for student data protection

            **Architecture-Specific Security Analysis**:
            - Security boundaries specific to this architecture (VPC design, subnet isolation)
            - Encryption configurations for the specific data types identified
            - Access controls tailored to the business roles and data sensitivity
            - Network security measures appropriate for the traffic patterns shown

            **Performance Analysis (Context-Aware)**:
            - Performance optimization for the specific workload patterns identified
            - Caching strategies appropriate for the data access patterns
            - Load balancing configurations for the specific traffic requirements
            - Database performance tuning for the identified query patterns

            **Concrete Cost Optimization**:
            - Specific cost estimates based on identified resource configurations
            - Right-sizing recommendations with exact instance type changes
            - Reserved instance opportunities with ROI calculations
            - Cost monitoring strategies for the specific services identified

            **Concrete Implementation Recommendations**:
            - Specific service configurations to implement (exact parameter values)
            - Step-by-step implementation procedures with AWS CLI commands
            - Configuration templates and Infrastructure as Code examples
            - Migration strategies with specific timelines and dependencies

            **Business Impact Assessment**:
            - Availability impact of current architecture on business operations
            - Performance implications for specific user experience scenarios
            - Security risks specific to the business domain and data types
            - Cost optimization opportunities with specific ROI calculations and timelines

            For visual diagrams, provide:
            - Detailed service topology with specific connection types and protocols
            - Data flow analysis with volume estimates and processing requirements
            - Network architecture assessment with specific security and performance implications
            - Identification of architecture anti-patterns with specific remediation steps

            **OUTPUT REQUIREMENTS**:
            - Reference specific services, configurations, and settings found in the documents
            - Provide concrete next steps with implementation details
            - Include cost implications with specific estimates where possible
            - Consider business context in all recommendations
            - Provide confidence scores for each recommendation with justification

            Provide structured output that demonstrates deep understanding of the specific architecture and business context.
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
    
    def _prepare_quality_text_message(
        self,
        file: UploadedFile,
        analysis_prompt: str = None
    ) -> List[Dict[str, Any]]:
        """Prepare text-only message with quality requirements."""
        
        # Decode content
        try:
            content = file.content.decode('utf-8')
        except UnicodeDecodeError:
            content = file.content.decode('utf-8', errors='ignore')
        
        if not analysis_prompt:
            analysis_prompt = """
            Analyze this text document for AWS Well-Architected Framework assessment with QUALITY REQUIREMENTS:
            
            **QUALITY REQUIREMENTS**:
            - Architecture-specific recommendations (not generic advice)
            - Reference specific AWS services and configurations mentioned
            - Consider business context and industry compliance needs
            - Provide concrete implementation steps with exact parameters
            - Include specific cost optimization opportunities
            
            **ANALYSIS FOCUS**:
            1. AWS Services: All mentioned services with specific configurations and versions
            2. Architecture Patterns: Specific patterns with business context considerations
            3. Security Measures: Tailored to the data types and compliance requirements identified
            4. Performance Optimizations: Specific to the workload patterns described
            5. Cost Considerations: Concrete optimization strategies with ROI estimates
            6. Operational Practices: Specific monitoring, logging, automation for this architecture
            7. Reliability Features: HA, DR, backup strategies appropriate for the business requirements
            8. Sustainability Aspects: Resource efficiency measures specific to the identified services
            
            Provide structured analysis with confidence scores and concrete implementation guidance.
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
    
    def _process_quality_response(
        self,
        response: Dict[str, Any],
        file_type: Optional[FileType]
    ) -> Dict[str, Any]:
        """Process Claude response with quality validation."""
        try:
            # Extract content from Claude response
            content = response.get('content', [])
            if content and isinstance(content, list):
                analysis_text = content[0].get('text', '')
            else:
                analysis_text = str(response)
            
            # Quality validation
            quality_metrics = self._validate_analysis_quality(analysis_text)
            
            # Structure the response with quality metrics
            result = {
                "status": "success",
                "file_type": file_type.value if file_type else "unknown",
                "analysis": {
                    "raw_response": analysis_text,
                    "structured_data": self._extract_structured_data(analysis_text),
                    "quality_metrics": quality_metrics
                },
                "metadata": {
                    "model_id": self.model_id,
                    "processing_time": response.get('usage', {}).get('total_tokens', 0),
                    "quality_score": quality_metrics.get("overall_score", 0)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing quality response: {e}")
            return {
                "status": "error",
                "error": str(e),
                "raw_response": str(response)
            }
    
    def _validate_analysis_quality(self, analysis_text: str) -> Dict[str, Any]:
        """Validate analysis quality against requirements."""
        
        quality_checks = {
            "architecture_specific": self._check_architecture_specific(analysis_text),
            "service_references": self._check_service_references(analysis_text),
            "business_context": self._check_business_context(analysis_text),
            "concrete_steps": self._check_concrete_steps(analysis_text),
            "cost_analysis": self._check_cost_analysis(analysis_text)
        }
        
        # Calculate overall quality score
        scores = [check["score"] for check in quality_checks.values()]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "overall_score": overall_score,
            "quality_checks": quality_checks,
            "meets_requirements": overall_score >= 0.7
        }
    
    def _check_architecture_specific(self, text: str) -> Dict[str, Any]:
        """Check if recommendations are architecture-specific."""
        specific_indicators = ["specific", "configuration", "instance type", "subnet", "vpc", "arn:", "region"]
        generic_indicators = ["generally", "typically", "usually", "consider using"]
        
        specific_count = sum(1 for indicator in specific_indicators if indicator.lower() in text.lower())
        generic_count = sum(1 for indicator in generic_indicators if indicator.lower() in text.lower())
        
        score = min(1.0, specific_count / max(1, specific_count + generic_count))
        
        return {
            "score": score,
            "specific_references": specific_count,
            "generic_references": generic_count
        }
    
    def _check_service_references(self, text: str) -> Dict[str, Any]:
        """Check for specific AWS service references."""
        aws_services = ["ec2", "s3", "rds", "lambda", "vpc", "iam", "cloudfront", "elb", "route53"]
        service_count = sum(1 for service in aws_services if service.lower() in text.lower())
        
        score = min(1.0, service_count / 5)  # Expect at least 5 service references
        
        return {
            "score": score,
            "services_referenced": service_count
        }
    
    def _check_business_context(self, text: str) -> Dict[str, Any]:
        """Check for business context considerations."""
        business_indicators = ["business", "compliance", "regulatory", "industry", "availability", "performance requirements"]
        context_count = sum(1 for indicator in business_indicators if indicator.lower() in text.lower())
        
        score = min(1.0, context_count / 3)  # Expect at least 3 business context references
        
        return {
            "score": score,
            "context_references": context_count
        }
    
    def _check_concrete_steps(self, text: str) -> Dict[str, Any]:
        """Check for concrete implementation steps."""
        concrete_indicators = ["configure", "set", "enable", "create", "deploy", "implement", "step", "command"]
        step_count = sum(1 for indicator in concrete_indicators if indicator.lower() in text.lower())
        
        score = min(1.0, step_count / 5)  # Expect at least 5 concrete action words
        
        return {
            "score": score,
            "concrete_actions": step_count
        }
    
    def _check_cost_analysis(self, text: str) -> Dict[str, Any]:
        """Check for cost analysis and optimization."""
        cost_indicators = ["cost", "pricing", "savings", "optimization", "reserved", "spot", "budget"]
        cost_count = sum(1 for indicator in cost_indicators if indicator.lower() in text.lower())
        
        score = min(1.0, cost_count / 2)  # Expect at least 2 cost references
        
        return {
            "score": score,
            "cost_references": cost_count
        }
    
    def _extract_structured_data(self, analysis_text: str) -> Dict[str, Any]:
        """Extract structured data from analysis text."""
        return {
            "aws_services": self._extract_aws_services(analysis_text),
            "architecture_patterns": self._extract_patterns(analysis_text),
            "security_findings": self._extract_security_findings(analysis_text),
            "recommendations": self._extract_recommendations(analysis_text),
            "cost_optimizations": self._extract_cost_optimizations(analysis_text)
        }
    
    def _extract_aws_services(self, text: str) -> List[str]:
        """Extract AWS service mentions from text."""
        import re
        aws_services = re.findall(r'\b(?:AWS\s+)?([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b', text)
        return list(set(aws_services[:10]))
    
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
        import re
        recommendations = re.findall(r'(?:recommend|suggest|should|consider)[\s\w]*', text, re.IGNORECASE)
        return recommendations[:5]
    
    def _extract_cost_optimizations(self, text: str) -> List[str]:
        """Extract cost optimization opportunities."""
        optimizations = []
        cost_keywords = ['reserved instance', 'spot instance', 'right-sizing', 'cost optimization']
        for keyword in cost_keywords:
            if keyword.lower() in text.lower():
                optimizations.append(f"Cost optimization: {keyword}")
        return optimizations
