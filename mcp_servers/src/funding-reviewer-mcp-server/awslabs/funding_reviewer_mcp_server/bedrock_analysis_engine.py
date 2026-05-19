"""
Simplified Bedrock Analysis Engine for POC Funding Reviewer

This module provides direct Bedrock integration with minimal processing.
All analysis is performed by the LLM, not by code.
"""

import asyncio
import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from .config import ConfigManager, get_config
from .models import UploadedFile, FileType


@dataclass
class SimplifiedAnalysisRequest:
    """Simplified request for POC funding analysis."""
    sow_document: Optional[UploadedFile] = None
    architecture_diagram: Optional[UploadedFile] = None
    pricing_calculator_csv: Optional[UploadedFile] = None
    request_metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


@dataclass
class SimplifiedAnalysisResult:
    """Simplified result of POC funding analysis."""
    status: str
    analysis: Dict[str, Any]
    processing_time: float
    correlation_id: Optional[str] = None
    error: Optional[str] = None
    formatted_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary."""
        result = {
            "status": self.status,
            "analysis": self.analysis,
            "processing_time": self.processing_time
        }
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.error:
            result["error"] = self.error
        if self.formatted_response:
            result["formatted_response"] = self.formatted_response
        return result


class SimplifiedBedrockEngine:
    """Simplified Bedrock analysis engine with direct LLM integration."""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize the simplified Bedrock analysis engine."""
        self.config = config or get_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize Bedrock client
        self._initialize_bedrock_client()
        
        self.logger.info("SimplifiedBedrockEngine initialized successfully")
    
    def _initialize_bedrock_client(self) -> None:
        """Initialize direct Bedrock client."""
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.bedrock.region
            )
            self.logger.info(f"Bedrock client initialized for region: {self.config.bedrock.region}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {e}")
            self.bedrock_client = None
            raise
    
    async def analyze_poc_funding_request(
        self,
        request: SimplifiedAnalysisRequest,
        correlation_id: Optional[str] = None
    ) -> SimplifiedAnalysisResult:
        """
        Perform comprehensive POC funding analysis using Bedrock.
        
        Args:
            request: Analysis request with documents
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Analysis results from Bedrock
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting POC funding analysis (correlation_id: {correlation_id})")
            
            # Validate request
            if not any([request.sow_document, request.architecture_diagram, request.pricing_calculator_csv]):
                raise ValueError("At least one document must be provided for analysis")
            
            # Build system prompt and user message separately
            system_prompt = self._build_system_prompt(request)
            user_message = self._build_user_message(request)
            
            # Prepare multimodal content for Bedrock
            content = self._prepare_multimodal_content(request, user_message)
            
            # Call Bedrock with retry logic
            response_text = await self._call_bedrock_with_retry(content, system_prompt, correlation_id)
            
            # Parse the response
            analysis_result = self._parse_bedrock_response(response_text)
            
            # Generate formatted comprehensive response
            formatted_response = self.format_comprehensive_response(analysis_result)
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"POC funding analysis completed in {processing_time:.2f}s (correlation_id: {correlation_id})")
            
            return SimplifiedAnalysisResult(
                status="success",
                analysis=analysis_result,
                processing_time=processing_time,
                correlation_id=correlation_id,
                formatted_response=formatted_response
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"POC funding analysis failed after {processing_time:.2f}s: {error_msg} (correlation_id: {correlation_id})")
            
            return SimplifiedAnalysisResult(
                status="error",
                analysis={},
                processing_time=processing_time,
                correlation_id=correlation_id,
                error=error_msg
            )
    
    def _build_system_prompt(self, request: SimplifiedAnalysisRequest) -> str:
        """Build the system prompt for Bedrock containing the agent definition and instructions."""
        
        # Load reference documents
        reference_content = self._load_reference_documents()
        
        system_prompt = f"""You are an expert AWS Partner Solutions Architect specialized in POC funding compliance analysis.

REFERENCE MATERIALS:
{reference_content}

CORE RESPONSIBILITIES:
1. Validate partner eligibility requirements (MANDATORY FIRST)
2. Assess financial compliance and funding limits
3. Review document completeness and correlation
4. Evaluate architecture against Well-Architected Framework
5. Verify scope appropriateness for POC program
6. Provide actionable recommendations and next steps

ELIGIBILITY REQUIREMENTS (CHECK FIRST):
- Partner tier: Must meet minimum tier requirement (configure in your deployment)
- Opportunity stage: Must be at appropriate stage (configure in your deployment)
- Opportunity probability: Must meet minimum threshold (configure in your deployment)
- AWS Management Account ID: Required (in REQUEST METADATA)
- If ANY missing: Set status "Need More Information" with specific guidance

FINANCIAL COMPLIANCE:
- Configure maximum funding limits and calculation rules for your deployment
- Calculate percentage and apply cap appropriately
- Check for program combination restrictions

DOCUMENT ANALYSIS APPROACH:
- SOW-FIRST: Extract requirements, then evaluate architecture against SOW needs (not generic best practices)
- Cross-reference services between SOW, architecture diagram, and cost breakdown
- Identify missing services and misalignments between documents
- Customer signatures are OPTIONAL (do not flag as missing)

ARCHITECTURE EVALUATION:
- Multi-AZ detection: Look for AZ labels, distributed resources, load balancers
- AWS service icons vs generic shapes
- Well-Architected pillars scored against SOW requirements:
  * If SOW specifies single AZ: Score reliability appropriately for single AZ
  * If SOW indicates POC scope: Adjust expectations for pilot-level features
  * Base scores on observable evidence, not assumptions

SCOPE VALIDATION:
- Must include actual AWS implementation and testing (not assessment-only)
- Verify POC-appropriate scale and deliverables
- Reject pure assessment or consulting scopes

COST ANALYSIS:
- Check REQUEST METADATA for pricing calculator URLs (aws_pricing_url, pricing_calculator_url, etc.)
- Validate service alignment across all cost documents
- Ensure pricing matches POC scale and requirements

REQUIRED ANALYSIS:
Provide your analysis in the following comprehensive JSON structure. Analyze ALL provided documents directly - do not rely on extracted text summaries.

{{
  "program_identification": {{
    "program_name": "string",
    "program_type": "string", 
    "eligibility_confirmed": boolean,
    "notes": "string"
  }},
  "eligibility_check": {{
    "partner_tier_valid": boolean,
    "partner_tier": "string or null",
    "stage_valid": boolean,
    "probability_valid": boolean,
    "aws_account_valid": boolean,
    "opportunity_stage": "string or null",
    "opportunity_probability": "number or null",
    "aws_account_id": "string or null",
    "missing_information": ["string"],
    "eligibility_issues": ["string"],
    "eligibility_recommendations": ["string"],
    "overall_eligibility": "Eligible|Not Eligible|Missing Information",
    "detailed_status": "string - comprehensive explanation of eligibility status",
    "missing_info_guidance": "string - specific guidance on how to obtain missing information"
  }},
  "financial_assessment": {{
    "requested_amount": number,
    "calculated_limit": number,
    "within_limits": boolean,
    "funding_calculation_method": "string",
    "twelve_month_spend": number,
    "percentage_of_spend": number,
    "cap_applied": boolean,
    "issues": ["string"],
    "recommendations": ["string"],
    "detailed_analysis": "string - comprehensive financial assessment explanation",
    "cost_optimization_suggestions": ["string"]
  }},
  "document_review": {{
    "sow_complete": boolean,
    "diagram_complete": boolean,
    "csv_complete": boolean,
    "sow_issues": ["string"],
    "diagram_issues": ["string"],
    "csv_issues": ["string"],
    "overall_completeness": "Complete|Incomplete|Partially Complete",
    "sow_analysis": {{
      "completeness_details": "string",
      "key_requirements": ["string"],
      "missing_elements": ["string"],
      "strengths": ["string"]
    }},
    "diagram_analysis": {{
      "completeness_details": "string", 
      "architectural_strengths": ["string"],
      "missing_components": ["string"],
      "design_concerns": ["string"]
    }},
    "csv_analysis": {{
      "completeness_details": "string",
      "cost_breakdown_quality": "string",
      "service_coverage": "string",
      "pricing_concerns": ["string"]
    }}
  }},
  "document_correlation": {{
    "services_aligned": boolean,
    "costs_aligned": boolean,
    "scope_aligned": boolean,
    "sow_requirements": "string",
    "diagram_aligns_with_sow": boolean,
    "services_in_csv_missing_from_diagram": ["string"],
    "services_in_diagram_missing_from_csv": ["string"],
    "service_mismatches": ["string"],
    "correlation_score": number,
    "detailed_correlation_analysis": "string - comprehensive explanation of document alignment",
    "alignment_strengths": ["string"],
    "alignment_gaps": ["string"],
    "correlation_recommendations": ["string"]
  }},
  "scope_verification": {{
    "includes_implementation": boolean,
    "includes_testing": boolean,
    "assessment_only": boolean,
    "scope_appropriate": boolean,
    "implementation_activities": ["string"],
    "testing_activities": ["string"],
    "concerns": ["string"],
    "recommendations": ["string"],
    "scope_appropriateness_analysis": "string - detailed scope assessment",
    "poc_suitability": "string - explanation of POC program fit",
    "deliverables_assessment": ["string"]
  }},
  "well_architected_validation": {{
    "overall_score": number,
    "compliance_status": "Compliant|Non-Compliant|Needs Improvement",
    "multi_az_detected": boolean,
    "multi_az_evidence": ["string"],
    "aws_service_icons_used": boolean,
    "availability_zones_identified": number,
    "security_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "strengths": ["string"],
      "improvements_needed": ["string"]
    }},
    "reliability_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "multi_az_assessment": "string",
      "high_availability_features": ["string"],
      "reliability_concerns": ["string"]
    }},
    "performance_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "performance_optimizations": ["string"],
      "scaling_considerations": ["string"]
    }},
    "cost_optimization_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "cost_efficiency_opportunities": ["string"],
      "pricing_model_recommendations": ["string"]
    }},
    "operational_excellence_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "operational_improvements": ["string"],
      "monitoring_recommendations": ["string"]
    }},
    "sustainability_pillar": {{
      "score": number, 
      "status": "string", 
      "findings": ["string"],
      "sustainability_opportunities": ["string"],
      "resource_efficiency_suggestions": ["string"]
    }},
    "critical_issues": ["string"],
    "recommendations": ["string"],
    "architecture_summary": "string - overall architecture assessment"
  }},
  "review_summary": {{
    "status": "Approved|Approved with Conditions|Rejected|Need More Information",
    "key_findings": ["string"],
    "missing_eligibility_info": ["string"],
    "eligibility_guidance": "string",
    "action_items": [{{
      "category": "string",
      "description": "string", 
      "priority": "High|Medium|Low",
      "requirement": "Required|Recommended",
      "timeline": "string",
      "responsible_party": "string"
    }}],
    "clarifying_questions": ["string"],
    "approval_confidence": number,
    "next_steps": ["string"],
    "comprehensive_summary": "string - detailed executive summary of the entire analysis",
    "decision_rationale": "string - explanation of the approval/rejection decision",
    "risk_assessment": ["string"],
    "success_factors": ["string"]
  }},
  "formatted_response": {{
    "executive_summary": "string - brief overview for stakeholders",
    "detailed_findings": "string - comprehensive analysis narrative",
    "recommendations_summary": "string - prioritized recommendations",
    "next_steps_guidance": "string - clear action plan"
  }}
}}

ANALYSIS WORKFLOW:
1. ELIGIBILITY VALIDATION (FIRST): Check REQUEST METADATA for all required fields
2. DOCUMENT ANALYSIS: Extract requirements from SOW, analyze architecture, review costs
3. CORRELATION CHECK: Cross-reference services and scope across all documents
4. WELL-ARCHITECTED ASSESSMENT: Score against SOW requirements with evidence
5. COMPLIANCE DETERMINATION: Provide status, findings, and actionable next steps

CRITICAL SUCCESS FACTORS:
- Base all assessments on observable evidence, not assumptions
- Score architecture against SOW requirements, not generic best practices
- Provide specific evidence for multi-AZ detection and service identification. Some time the diagrams has the zones described using AWS naming convention, for example: (us-east-1, us-east-2, ...) or (us-east-1a, us-east-1b, ...), sometimes the diagrams just say private/public subnet 1, private/public subnet 2, or (az1, az2, ...). Find a pattern that can represent multi-az for high avialability. If it is not clear call it out on the feedback.
- Include detailed guidance for missing information collection
- Ensure implementation focus (reject assessment-only scopes)
- Return comprehensive JSON response with actionable recommendations

IMPORTANT: This AI provides advisory guidance only. Partner Solutions Architects retain final decision authority and must ensure compliance with all program requirements."""
        
        return system_prompt

    def _build_user_message(self, request: SimplifiedAnalysisRequest) -> str:
        """Build the user message containing the specific request details and file references."""
        
        user_message = "Analyze this POC funding request for compliance:\n\n"
        
        # Add document information
        user_message += "DOCUMENTS PROVIDED:\n"
        if request.sow_document:
            user_message += f"- SOW Document: {request.sow_document.filename}\n"
        if request.pricing_calculator_csv:
            user_message += f"- Pricing Calculator CSV: {request.pricing_calculator_csv.filename}\n"
        if request.architecture_diagram:
            user_message += f"- Architecture Diagram: {request.architecture_diagram.filename}\n"
        
        # Add request metadata
        user_message += f"\nREQUEST METADATA:\n{json.dumps(request.request_metadata, indent=2) if request.request_metadata else 'No metadata provided'}\n"
        
        user_message += "\nPerform comprehensive analysis following your system instructions. Return ONLY the JSON response."
        
        return user_message
    
    def _load_reference_documents(self) -> str:
        """Load reference documents for analysis context."""
        try:
            reference_content = []
            
            # Get the directory where this module is located
            current_dir = Path(__file__).parent.parent.parent
            
            # Try to load POC general guidance using configured path
            guidance_path = self.config.reference_docs.general_guidance_path
            
            # Try multiple possible locations for the guidance file
            possible_guidance_paths = [
                Path(guidance_path),  # Relative to current working directory
                current_dir / guidance_path,  # Relative to project root
                Path(__file__).parent.parent.parent / guidance_path  # Explicit project root
            ]
            
            guidance_loaded = False
            for path in possible_guidance_paths:
                try:
                    if path.exists():
                        with open(path, 'r', encoding='utf-8') as f:
                            guidance_content = f.read()
                            reference_content.append("=== POC GENERAL GUIDANCE ===\n" + guidance_content)
                            self.logger.info(f"Loaded POC general guidance from {path}")
                            guidance_loaded = True
                            break
                except Exception as e:
                    self.logger.debug(f"Could not read guidance from {path}: {e}")
                    continue
            
            if not guidance_loaded:
                self.logger.warning(f"POC general guidance not found at any of the expected locations: {[str(p) for p in possible_guidance_paths]}")
            
            # Try to load project template reference using configured path
            template_path = self.config.reference_docs.project_template_path
            
            # Try multiple possible locations for the template file
            possible_template_paths = [
                Path(template_path),  # Relative to current working directory
                current_dir / template_path,  # Relative to project root
                Path(__file__).parent.parent.parent / template_path  # Explicit project root
            ]
            
            template_found = False
            for path in possible_template_paths:
                try:
                    if path.exists():
                        # For DOCX files, we'll provide a reference note since we can't easily read the content
                        # In a more advanced implementation, we could use python-docx to extract text
                        template_content = f"Project template available at: {path}\n"
                        template_content += "Template provides standard POC project structure and deliverable examples.\n"
                        template_content += "Use this template as a reference for expected POC project format and content structure.\n"
                        template_content += "The template includes sections for: Executive Summary, Project Scope, Technical Architecture, "
                        template_content += "Implementation Plan, Success Criteria, Timeline, and Deliverables."
                        reference_content.append("=== POC PROJECT PLAN TEMPLATE REFERENCE ===\n" + template_content)
                        self.logger.info(f"Added project template reference for {path}")
                        template_found = True
                        break
                except Exception as e:
                    self.logger.debug(f"Could not access template at {path}: {e}")
                    continue
            
            if not template_found:
                self.logger.warning(f"Project template not found at any of the expected locations: {[str(p) for p in possible_template_paths]}")
            
            if reference_content:
                combined_content = "\n\n".join(reference_content)
                self.logger.info(f"Loaded {len(reference_content)} reference document(s) for analysis context")
                return combined_content
            else:
                self.logger.warning("No reference documents available - proceeding with standard POC funding analysis")
                return "No reference documents available - proceeding with standard POC funding analysis."
                
        except Exception as e:
            self.logger.error(f"Error loading reference documents: {e}")
            return "Reference documents unavailable - proceeding with standard POC funding analysis."
    
    def _prepare_multimodal_content(self, request: SimplifiedAnalysisRequest, user_message: str) -> List[Dict[str, Any]]:
        """Prepare multimodal content for Bedrock API user message."""
        content = []
        
        # Add the user message text
        content.append({
            "text": user_message
        })
        
        # Add documents in order of importance
        if request.sow_document:
            content.append(self._prepare_document_content(request.sow_document))
        
        if request.architecture_diagram:
            content.append(self._prepare_image_content(request.architecture_diagram))
        
        if request.pricing_calculator_csv:
            content.append(self._prepare_text_content(request.pricing_calculator_csv))
        
        return content
    
    def _sanitize_filename_for_bedrock(self, filename: str) -> str:
        """Sanitize filename like the backend does."""
        import re
        import os
        
        if not filename:
            return "document"
        
        # Remove file extension - get just the base name
        base_name = os.path.splitext(filename)[0]
        
        # Only allow alphanumeric, whitespace, hyphens, parentheses, square brackets
        # Replace any other characters with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '_', base_name)
        
        # Remove multiple consecutive whitespace and replace with single space
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Ensure we have a valid filename (not empty after sanitization)
        if not sanitized or sanitized.isspace():
            sanitized = "document"
            
        self.logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}' (extension removed)")
        return sanitized
    
    def _prepare_document_content(self, file: UploadedFile) -> Dict[str, Any]:
        """Prepare document for Bedrock using the same approach as the working backend."""
        file_type = file.get_file_type()
        
        # Use the same format mapping as the backend
        format_map = {
            FileType.PDF: "pdf",
            FileType.DOCX: "docx"
        }
        
        doc_format = format_map.get(file_type, "pdf")
        
        return {
            "document": {
                "name": self._sanitize_filename_for_bedrock(file.filename),
                "format": doc_format,
                "source": {
                    "bytes": file.content  # Raw bytes like the backend - let Boto3 handle encoding
                }
            }
        }
    
    def _prepare_image_content(self, file: UploadedFile) -> Dict[str, Any]:
        """Prepare image using the same format as the backend."""
        file_type = file.get_file_type()
        
        # Use the same format mapping as the backend
        format_map = {
            FileType.JPG: 'jpeg',
            FileType.JPEG: 'jpeg', 
            FileType.PNG: 'png',
            FileType.GIF: 'gif',
            FileType.WEBP: 'webp'
        }
        
        image_format = format_map.get(file_type, 'jpeg')
        
        return {
            "image": {
                "format": image_format,
                "source": {
                    "bytes": file.content  # Raw bytes like the backend - let Boto3 handle encoding
                }
            }
        }
    
    def _prepare_text_content(self, file: UploadedFile) -> Dict[str, Any]:
        """Prepare CSV/text file for Bedrock."""
        try:
            # Decode CSV content and add as text content block
            csv_content = file.content.decode('utf-8')
            return {
                "text": f"\n\nCSV FILE CONTENT ({file.filename}):\n{csv_content}"
            }
        except UnicodeDecodeError:
            # If can't decode as text, treat as document with proper format
            return {
                "document": {
                    "name": self._sanitize_filename_for_bedrock(file.filename),
                    "format": "txt",  # Treat as text document
                    "source": {
                        "bytes": file.content  # Raw bytes
                    }
                }
            }
    
    async def _call_bedrock_with_retry(self, content: List[Dict[str, Any]], system_prompt: str, correlation_id: Optional[str] = None) -> str:
        """Call Bedrock streaming API with retry logic."""
        max_retries = self.config.bedrock.max_retries
        backoff_factor = self.config.bedrock.retry_backoff_factor
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"Bedrock streaming call attempt {attempt + 1}/{max_retries + 1}")
                
                response = await self._call_bedrock_direct(content, system_prompt)
                if response:
                    self.logger.info(f"Bedrock streaming call successful, received {len(response)} characters")
                    return response
                
                raise Exception("Bedrock streaming call returned empty response")
                
            except Exception as e:
                self.logger.warning(f"Bedrock attempt {attempt + 1} failed: {e} (correlation_id: {correlation_id})")
                
                if attempt == max_retries:
                    raise Exception(f"Bedrock analysis failed after {max_retries + 1} attempts: {e}")
                
                # Exponential backoff
                wait_time = backoff_factor ** attempt
                self.logger.info(f"Retrying in {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
        
        raise Exception("Bedrock analysis failed - maximum retries exceeded")
    
    async def _call_bedrock_direct(self, content: List[Dict[str, Any]], system_prompt: str) -> Optional[str]:
        """Call Bedrock using Converse Stream API with proper system/user message separation."""
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized")
        
        try:
            self.logger.debug(f"Calling Bedrock Converse Stream API with model: {self.config.bedrock.model_id}")
            
            # Use converse_stream API with proper system prompt separation
            response = self.bedrock_client.converse_stream(
                modelId=self.config.bedrock.model_id,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                system=[{
                    "text": system_prompt
                }],
                inferenceConfig={
                    "maxTokens": self.config.bedrock.max_tokens,
                    "temperature": self.config.bedrock.temperature
                }
            )
            
            # Collect streaming response
            full_response = ""
            
            # Process the streaming response
            if 'stream' in response:
                for event in response['stream']:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']
                        if 'delta' in delta and 'text' in delta['delta']:
                            chunk = delta['delta']['text']
                            full_response += chunk
                            self.logger.debug(f"Received chunk: {len(chunk)} characters")
                    elif 'messageStop' in event:
                        self.logger.debug("Stream completed")
                        break
                    elif 'contentBlockStop' in event:
                        self.logger.debug("Content block completed")
                        continue
            
            if full_response.strip():
                self.logger.debug(f"Complete response received: {len(full_response)} characters")
                return full_response.strip()
            
            return None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"Bedrock API error ({error_code}): {error_message}")
        except Exception as e:
            raise Exception(f"Bedrock streaming call failed: {e}")
    
    def _parse_bedrock_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Bedrock response into structured analysis result."""
        try:
            # Clean up response text
            clean_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            analysis_result = json.loads(clean_text)
            
            # Validate required structure
            required_keys = [
                "program_identification", "eligibility_check", "financial_assessment",
                "document_review", "document_correlation", "scope_verification",
                "well_architected_validation", "review_summary"
            ]
            
            for key in required_keys:
                if key not in analysis_result:
                    self.logger.warning(f"Missing required analysis section: {key}")
                    analysis_result[key] = {"error": f"Analysis section '{key}' not provided"}
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Bedrock response as JSON: {e}")
            self.logger.debug(f"Raw response: length={len(response_text)}")
            
            # Return error structure
            return {
                "program_identification": {"error": "Failed to parse analysis response"},
                "eligibility_check": {"error": "Failed to parse analysis response"},
                "financial_assessment": {"error": "Failed to parse analysis response"},
                "document_review": {"error": "Failed to parse analysis response"},
                "document_correlation": {"error": "Failed to parse analysis response"},
                "scope_verification": {"error": "Failed to parse analysis response"},
                "well_architected_validation": {"error": "Failed to parse analysis response"},
                "review_summary": {
                    "status": "Error",
                    "key_findings": ["Analysis response could not be parsed"],
                    "action_items": [],
                    "clarifying_questions": ["Please retry the analysis"],
                    "approval_confidence": 0.0,
                    "next_steps": ["Contact support if issue persists"]
                },
                "raw_response": response_text[:1000] if response_text else "No response received"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error parsing Bedrock response: {e}")
            return {
                "program_identification": {"error": "Unexpected parsing error"},
                "eligibility_check": {"error": "Unexpected parsing error"},
                "financial_assessment": {"error": "Unexpected parsing error"},
                "document_review": {"error": "Unexpected parsing error"},
                "document_correlation": {"error": "Unexpected parsing error"},
                "scope_verification": {"error": "Unexpected parsing error"},
                "well_architected_validation": {"error": "Unexpected parsing error"},
                "review_summary": {
                    "status": "Error",
                    "key_findings": [f"Parsing error: {str(e)}"],
                    "action_items": [],
                    "clarifying_questions": [],
                    "approval_confidence": 0.0,
                    "next_steps": ["Retry analysis or contact support"]
                }
            }
    
    def format_comprehensive_response(self, analysis_result: Dict[str, Any]) -> str:
        """Format the JSON analysis result into a comprehensive narrative response."""
        try:
            # Extract key sections
            program_id = analysis_result.get("program_identification", {})
            eligibility = analysis_result.get("eligibility_check", {})
            financial = analysis_result.get("financial_assessment", {})
            doc_review = analysis_result.get("document_review", {})
            correlation = analysis_result.get("document_correlation", {})
            scope = analysis_result.get("scope_verification", {})
            well_arch = analysis_result.get("well_architected_validation", {})
            summary = analysis_result.get("review_summary", {})
            
            # Build comprehensive response
            response = "# POC Funding Compliance Analysis Results\n\n"
            
            # 1. Program Identification
            response += "## 1. Program Identification\n"
            response += f"- **Program Name**: {program_id.get('program_name', 'Partner Proof of Concept (POC)')}\n"
            response += f"- **Program Type**: {program_id.get('program_type', 'POC Funding')}\n"
            eligibility_status = "✅ Confirmed" if program_id.get('eligibility_confirmed', False) else "❌ Cannot confirm eligibility due to missing required information"
            response += f"- **Eligibility Status**: {eligibility_status}\n\n"
            
            # 2. Eligibility Check
            response += "## 2. Eligibility Check\n"
            overall_eligibility = eligibility.get('overall_eligibility', 'Missing Information')
            response += f"**Current Status**: {overall_eligibility}\n\n"
            
            if eligibility.get('missing_information'):
                response += "**Missing Required Information**:\n"
                for item in eligibility.get('missing_information', []):
                    response += f"- {item}\n"
                response += "\n"
            
            if eligibility.get('eligibility_issues'):
                response += "**Eligibility Issues Identified**:\n"
                for issue in eligibility.get('eligibility_issues', []):
                    response += f"- {issue}\n"
                response += "\n"
            
            if eligibility.get('eligibility_recommendations'):
                response += "**Eligibility Recommendations**:\n"
                for rec in eligibility.get('eligibility_recommendations', []):
                    response += f"- {rec}\n"
                response += "\n"
            
            # 3. Financial Assessment
            response += "## 3. Financial Assessment\n"
            response += "**Funding Request Analysis**:\n"
            response += f"- **Requested Amount**: ${financial.get('requested_amount', 0):,.0f}\n"
            response += f"- **Calculated Funding Limit**: ${financial.get('calculated_limit', 0):,.2f}\n"
            within_limits = "✅ Yes" if financial.get('within_limits', False) else "❌ No"
            response += f"- **Within Limits**: {within_limits}\n"
            response += f"- **Funding Calculation Method**: {financial.get('funding_calculation_method', 'Not specified')}\n"
            response += f"- **Projected 12-Month AWS Spend**: ${financial.get('twelve_month_spend', 0):,.2f}\n"
            response += f"- **Percentage of Spend**: {financial.get('percentage_of_spend', 0):.2f}%\n"
            cap_applied = "Yes" if financial.get('cap_applied', False) else "No"
            response += f"- **Cap Applied**: {cap_applied}\n\n"
            
            if financial.get('recommendations'):
                response += "**Financial Recommendations**:\n"
                for rec in financial.get('recommendations', []):
                    response += f"- {rec}\n"
                response += "\n"
            
            # 4. Document Review
            response += "## 4. Document Review\n"
            
            # SOW Analysis
            sow_analysis = doc_review.get('sow_analysis', {})
            if sow_analysis:
                sow_complete = "✅ Complete" if doc_review.get('sow_complete', False) else "❌ Incomplete"
                response += f"#### SOW Document Analysis\n**Completeness**: {sow_complete}\n"
                
                if sow_analysis.get('key_requirements'):
                    response += "**Key SOW Requirements**:\n"
                    for req in sow_analysis.get('key_requirements', []):
                        response += f"- {req}\n"
                
                if doc_review.get('sow_issues'):
                    response += "**Issues Identified**:\n"
                    for issue in doc_review.get('sow_issues', []):
                        response += f"- {issue}\n"
                response += "\n"
            
            # Architecture Diagram Analysis
            diagram_analysis = doc_review.get('diagram_analysis', {})
            if diagram_analysis:
                diagram_complete = "✅ Complete" if doc_review.get('diagram_complete', False) else "❌ Incomplete"
                response += f"#### Architecture Diagram Analysis\n**Completeness**: {diagram_complete}\n"
                
                if diagram_analysis.get('architectural_strengths'):
                    response += "**Architecture Strengths**:\n"
                    for strength in diagram_analysis.get('architectural_strengths', []):
                        response += f"- {strength}\n"
                
                if doc_review.get('diagram_issues'):
                    response += "**Issues Identified**:\n"
                    for issue in doc_review.get('diagram_issues', []):
                        response += f"- {issue}\n"
                response += "\n"
            
            # CSV Analysis
            csv_analysis = doc_review.get('csv_analysis', {})
            if csv_analysis:
                csv_complete = "✅ Complete" if doc_review.get('csv_complete', False) else "❌ Incomplete"
                response += f"#### Pricing Calculator Analysis\n**Completeness**: {csv_complete}\n"
                
                if doc_review.get('csv_issues'):
                    response += "**Issues Identified**:\n"
                    for issue in doc_review.get('csv_issues', []):
                        response += f"- {issue}\n"
                response += "\n"
            
            # 5. Document Correlation
            response += "## 5. Document Correlation\n"
            correlation_score = correlation.get('correlation_score', 0)
            response += f"**Overall Alignment**: Score {correlation_score}/10\n"
            services_aligned = "✅ Yes" if correlation.get('services_aligned', False) else "❌ Needs improvement"
            costs_aligned = "✅ Yes" if correlation.get('costs_aligned', False) else "❌ Needs improvement"
            scope_aligned = "✅ Yes" if correlation.get('scope_aligned', False) else "❌ Needs improvement"
            response += f"- **Services Aligned**: {services_aligned}\n"
            response += f"- **Costs Aligned**: {costs_aligned}\n"
            response += f"- **Scope Aligned**: {scope_aligned}\n\n"
            
            if correlation.get('service_mismatches'):
                response += "**Service Mismatches**:\n"
                for mismatch in correlation.get('service_mismatches', []):
                    response += f"- {mismatch}\n"
                response += "\n"
            
            # 6. Scope Verification
            response += "## 6. Scope Verification\n"
            scope_appropriate = "✅ Appropriate for POC funding" if scope.get('scope_appropriate', False) else "❌ Not appropriate"
            response += f"**Scope Appropriateness**: {scope_appropriate}\n"
            includes_impl = "✅ Yes" if scope.get('includes_implementation', False) else "❌ No"
            includes_test = "✅ Yes" if scope.get('includes_testing', False) else "❌ No"
            assessment_only = "❌ No" if not scope.get('assessment_only', True) else "✅ Yes"
            response += f"- **Includes Implementation**: {includes_impl}\n"
            response += f"- **Includes Testing**: {includes_test}\n"
            response += f"- **Assessment Only**: {assessment_only}\n\n"
            
            if scope.get('implementation_activities'):
                response += "**Implementation Activities**:\n"
                for activity in scope.get('implementation_activities', []):
                    response += f"- {activity}\n"
                response += "\n"
            
            if scope.get('testing_activities'):
                response += "**Testing Activities**:\n"
                for activity in scope.get('testing_activities', []):
                    response += f"- {activity}\n"
                response += "\n"
            
            # 7. Well-Architected Framework Validation
            response += "## 7. Well-Architected Framework Validation\n"
            overall_score = well_arch.get('overall_score', 0)
            compliance_status = well_arch.get('compliance_status', 'Unknown')
            response += f"**Overall Score**: {overall_score}/10 - {compliance_status}\n\n"
            
            # Pillar breakdown
            pillars = ['security_pillar', 'reliability_pillar', 'performance_pillar', 
                      'cost_optimization_pillar', 'operational_excellence_pillar', 'sustainability_pillar']
            pillar_names = ['Security', 'Reliability', 'Performance', 'Cost Optimization', 
                           'Operational Excellence', 'Sustainability']
            
            response += "**Pillar Breakdown**:\n"
            for pillar, name in zip(pillars, pillar_names):
                pillar_data = well_arch.get(pillar, {})
                score = pillar_data.get('score', 0)
                status = pillar_data.get('status', 'Unknown')
                response += f"- **{name}**: {score}/10 - {status}\n"
                
                if pillar_data.get('findings'):
                    for finding in pillar_data.get('findings', [])[:2]:  # Limit to first 2 findings
                        response += f"  - {finding}\n"
            response += "\n"
            
            # Multi-AZ Detection
            multi_az = "✅ Detected" if well_arch.get('multi_az_detected', False) else "❌ Not detected"
            response += f"**Multi-AZ Deployment**: {multi_az}\n"
            if well_arch.get('multi_az_evidence'):
                response += "**Evidence**:\n"
                for evidence in well_arch.get('multi_az_evidence', []):
                    response += f"- {evidence}\n"
            response += "\n"
            
            # 8. Review Summary & Recommendations
            response += "## 8. Review Summary & Recommendations\n"
            status = summary.get('status', 'Unknown')
            response += f"**Status**: {status}\n\n"
            
            if summary.get('key_findings'):
                response += "**Key Findings**:\n"
                for finding in summary.get('key_findings', []):
                    response += f"- {finding}\n"
                response += "\n"
            
            # Action Items
            if summary.get('action_items'):
                response += "**Critical Action Items**:\n"
                high_priority = [item for item in summary.get('action_items', []) if item.get('priority') == 'High']
                medium_priority = [item for item in summary.get('action_items', []) if item.get('priority') == 'Medium']
                
                if high_priority:
                    response += "**High Priority (Required)**:\n"
                    for i, item in enumerate(high_priority, 1):
                        response += f"{i}. **{item.get('description', 'No description')}** ({item.get('category', 'General')})\n"
                    response += "\n"
                
                if medium_priority:
                    response += "**Medium Priority (Recommended)**:\n"
                    for i, item in enumerate(medium_priority, len(high_priority) + 1):
                        response += f"{i}. **{item.get('description', 'No description')}** ({item.get('category', 'General')})\n"
                    response += "\n"
            
            # Clarifying Questions
            if summary.get('clarifying_questions'):
                response += "**Clarifying Questions**:\n"
                for question in summary.get('clarifying_questions', []):
                    response += f"- {question}\n"
                response += "\n"
            
            # Next Steps
            if summary.get('next_steps'):
                response += "**Next Steps**:\n"
                for i, step in enumerate(summary.get('next_steps', []), 1):
                    response += f"{i}. {step}\n"
                response += "\n"
            
            # Approval Confidence
            confidence = summary.get('approval_confidence', 0)
            response += f"**Approval Confidence**: {confidence}/10"
            
            if eligibility.get('overall_eligibility') == 'Missing Information':
                response += " (pending required eligibility information)"
            
            response += "\n\n"
            
            # Final Summary
            if summary.get('comprehensive_summary'):
                response += f"**Executive Summary**: {summary.get('comprehensive_summary')}\n"
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error formatting comprehensive response: {e}")
            return f"Error formatting analysis response: {str(e)}"

    def get_engine_status(self) -> Dict[str, Any]:
        """Get the current status of the analysis engine."""
        return {
            "bedrock_client_available": self.bedrock_client is not None,
            "model_id": self.config.bedrock.model_id,
            "region": self.config.bedrock.region,
            "max_retries": self.config.bedrock.max_retries,
            "timeout_seconds": self.config.bedrock.timeout_seconds,
            "engine_type": "SimplifiedBedrockEngine",
            "streaming_enabled": True,
            "api_method": "converse_stream"
        }