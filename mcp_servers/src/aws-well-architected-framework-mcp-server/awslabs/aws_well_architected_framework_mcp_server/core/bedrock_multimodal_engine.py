#!/usr/bin/env python3
"""
WAFR Bedrock Multimodal Engine
Enhanced AI-powered analysis using Amazon Bedrock for document and image processing
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from ..consts import get_aws_region

logger = logging.getLogger(__name__)

@dataclass
class BedrockAnalysisResult:
    """Result from Bedrock multimodal analysis"""
    status: str
    analysis_data: Dict[str, Any]
    processing_time: float
    model_used: str
    confidence_score: float
    error: Optional[str] = None

class WAFRBedrockEngine:
    """
    Enhanced Bedrock engine for WAFR document and image analysis
    Supports multimodal analysis with vision capabilities
    """
    
    def __init__(self, region_name: str = None):
        """Initialize Bedrock engine"""
        self.region_name = region_name or get_aws_region()
        self.bedrock_client = None
        self.bedrock_runtime = None
        
        # Model configurations
        self.text_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.vision_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        # Initialize clients
        self._initialize_clients()
        
        logger.info(f"🤖 WAFR Bedrock Engine initialized (region: {region_name})")
    
    def _initialize_clients(self):
        """Initialize Bedrock clients"""
        try:
            # Initialize Bedrock clients
            self.bedrock_client = boto3.client('bedrock', region_name=self.region_name)
            self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region_name)
            
            logger.info("✅ Bedrock clients initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Bedrock clients: {e}")
            # Don't raise exception - allow graceful degradation
    
    async def analyze_documents_multimodal(
        self,
        documents: List[Any],
        analysis_prompt: str,
        enable_vision: bool = True
    ) -> BedrockAnalysisResult:
        """
        Perform multimodal analysis of documents using Bedrock
        
        Args:
            documents: List of document objects with content and metadata
            analysis_prompt: Structured prompt for analysis
            enable_vision: Enable vision analysis for images/diagrams
            
        Returns:
            BedrockAnalysisResult with analysis data
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        try:
            logger.info(f"🔍 Starting Bedrock multimodal analysis (correlation_id: {correlation_id})")
            
            if not self.bedrock_runtime:
                raise Exception("Bedrock runtime not available")
            
            # Process documents by type
            text_content = []
            image_content = []
            
            for doc in documents:
                if self._is_image_document(doc):
                    if enable_vision:
                        image_content.append(doc)
                else:
                    text_content.append(doc)
            
            # Perform analysis
            analysis_results = {}
            
            # Text analysis
            if text_content:
                text_result = await self._analyze_text_content(text_content, analysis_prompt)
                analysis_results.update(text_result)
            
            # Vision analysis
            if image_content and enable_vision:
                vision_result = await self._analyze_image_content(image_content, analysis_prompt)
                analysis_results.update(vision_result)
            
            # Combine and enhance results
            enhanced_results = self._enhance_analysis_results(analysis_results)
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Bedrock analysis completed in {processing_time:.2f}s")
            
            return BedrockAnalysisResult(
                status="success",
                analysis_data=enhanced_results,
                processing_time=processing_time,
                model_used=self.text_model,
                confidence_score=enhanced_results.get('confidence_score', 0.85)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Bedrock analysis failed: {e}")
            
            return BedrockAnalysisResult(
                status="error",
                analysis_data={},
                processing_time=processing_time,
                model_used="none",
                confidence_score=0.0,
                error=str(e)
            )
    
    async def _analyze_text_content(self, documents: List[Any], prompt: str) -> Dict[str, Any]:
        """Analyze text content using Bedrock CONVERSE STREAM API (funding reviewer approach)"""
        try:
            # Prepare user content with documents
            user_content = []
            
            # Add user message
            user_content.append({
                "text": "Please analyze these documents following the instructions in the system prompt."
            })
            
            # Add documents in native format
            for doc in documents:
                content = getattr(doc, 'content', b'')
                filename = getattr(doc, 'filename', 'unknown')
                
                # Determine document format
                if filename.lower().endswith('.pdf'):
                    doc_format = "pdf"
                elif filename.lower().endswith('.docx'):
                    doc_format = "docx"
                else:
                    doc_format = "pdf"  # default
                
                # Add document in native format (funding reviewer approach)
                if isinstance(content, bytes):
                    user_content.append({
                        "document": {
                            "format": doc_format,
                            "name": filename.replace('.pdf', '').replace('.docx', ''),
                            "source": {
                                "bytes": content
                            }
                        }
                    })
            
            logger.info(f"🚀 Calling Bedrock Converse Stream API for text analysis (funding reviewer approach)")
            logger.debug(f"System prompt length: {len(prompt)}")
            logger.debug(f"User content blocks: {len(user_content)}")
            
            # Use converse_stream API (funding reviewer approach)
            response = self.bedrock_runtime.converse_stream(
                modelId=self.text_model,
                messages=[{
                    "role": "user",
                    "content": user_content
                }],
                system=[{"text": prompt}],
                inferenceConfig={
                    "maxTokens": 4000,
                    "temperature": 0  # Set to 0 for deterministic/consistent results
                }
            )
            
            # Collect streaming response (funding reviewer approach)
            analysis_text = ""
            if 'stream' in response:
                for event in response['stream']:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']
                        if 'delta' in delta and 'text' in delta['delta']:
                            chunk = delta['delta']['text']
                            analysis_text += chunk
                    elif 'messageStop' in event:
                        logger.debug("Stream completed")
                        break
            
            logger.info(f"✅ Received {len(analysis_text)} characters from Bedrock stream")
            
            # Parse structured response
            return self._parse_analysis_response(analysis_text, "text")
            
        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            return {"text_analysis_error": str(e)}
    
    async def _analyze_image_content(self, documents: List[Any], prompt: str) -> Dict[str, Any]:
        """Analyze image content using Bedrock CONVERSE STREAM API (funding reviewer approach)"""
        try:
            vision_results = []
            
            for doc in documents:
                # Prepare image for analysis
                image_data = self._prepare_image_data(doc)
                
                # Prepare user content with native image format (funding reviewer approach)
                user_content = [
                    {
                        "text": "Please analyze this architecture diagram following the instructions in the system prompt."
                    },
                    {
                        "image": {
                            "format": image_data['media_type'].split('/')[-1],  # jpeg, png, etc.
                            "source": {
                                "bytes": base64.b64decode(image_data['data'])  # Convert back to bytes
                            }
                        }
                    }
                ]
                
                logger.info(f"🚀 Calling Bedrock Converse Stream API for image analysis (funding reviewer approach)")
                
                # Use converse_stream API (funding reviewer approach)
                response = self.bedrock_runtime.converse_stream(
                    modelId=self.vision_model,
                    messages=[{
                        "role": "user",
                        "content": user_content
                    }],
                    system=[{"text": prompt}],
                    inferenceConfig={
                        "maxTokens": 2000,
                        "temperature": 0  # Set to 0 for deterministic/consistent results
                    }
                )
                
                # Collect streaming response (funding reviewer approach)
                analysis_text = ""
                if 'stream' in response:
                    for event in response['stream']:
                        if 'contentBlockDelta' in event:
                            delta = event['contentBlockDelta']
                            if 'delta' in delta and 'text' in delta['delta']:
                                chunk = delta['delta']['text']
                                analysis_text += chunk
                        elif 'messageStop' in event:
                            break
                
                logger.info(f"✅ Received {len(analysis_text)} characters from Bedrock stream for image")
                
                vision_results.append({
                    'filename': getattr(doc, 'filename', 'unknown'),
                    'analysis': self._parse_analysis_response(analysis_text, "vision")
                })
            
            return {"vision_analysis": vision_results}
            
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"vision_analysis_error": str(e)}
    
    def _is_image_document(self, doc: Any) -> bool:
        """Check if document is an image"""
        filename = getattr(doc, 'filename', '').lower()
        content_type = getattr(doc, 'content_type', '').lower()
        
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        image_types = ['image/']
        
        return (
            any(filename.endswith(ext) for ext in image_extensions) or
            any(content_type.startswith(img_type) for img_type in image_types)
        )
    
    def _prepare_image_data(self, doc: Any) -> Dict[str, str]:
        """Prepare image data for Bedrock"""
        content = getattr(doc, 'content', b'')
        content_type = getattr(doc, 'content_type', 'image/png')
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Convert to base64
        base64_data = base64.b64encode(content).decode('utf-8')
        
        return {
            'data': base64_data,
            'media_type': content_type
        }
    
    def _parse_analysis_response(self, response_text: str, analysis_type: str) -> Dict[str, Any]:
        """Parse Claude's analysis response using FUNDING REVIEWER APPROACH"""
        try:
            # Initialize result structure
            result = {
                'identified_services': [],
                'architecture_patterns': [],
                'security_findings': [],
                'performance_insights': [],
                'cost_optimization_opportunities': [],
                'reliability_considerations': [],
                'sustainability_recommendations': [],
                'multi_az_detected': False,
                'multi_az_evidence': [],
                'evidence_based_findings': True,
                'analysis_type': analysis_type
            }
            
            # FUNDING REVIEWER APPROACH: Parse by sections using ### headers
            sections = response_text.split('###')
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                # Extract section title and content
                lines = section.split('\n', 1)
                if len(lines) < 2:
                    continue
                
                title = lines[0].strip().lower()
                content = lines[1].strip()
                
                # Parse different sections using funding reviewer logic
                if 'aws services' in title:
                    result['identified_services'] = self._extract_list_items_funding_style(content)
                    logger.info(f"🎯 Found AWS Services section: {len(result['identified_services'])} services")
                elif 'architecture patterns' in title:
                    result['architecture_patterns'] = self._extract_list_items_funding_style(content)
                elif 'infrastructure components' in title:
                    # Add infrastructure components that are AWS services
                    infra_items = self._extract_list_items_funding_style(content)
                    for item in infra_items:
                        if any(svc in item.lower() for svc in ['ec2', 's3', 'rds', 'lambda', 'vpc', 'elb', 'cloudwatch']):
                            result['identified_services'].append(item)
                elif 'security elements' in title:
                    result['security_findings'] = self._extract_list_items_funding_style(content)
                    # Add security services to identified services
                    for item in result['security_findings']:
                        if any(svc in item.lower() for svc in ['iam', 'cognito', 'kms', 'waf', 'shield']):
                            result['identified_services'].append(item)
                elif 'multi-az detection' in title:
                    multi_az_items = self._extract_list_items_funding_style(content)
                    if multi_az_items and not any('not specified' in item.lower() for item in multi_az_items):
                        result['multi_az_detected'] = True
                        result['multi_az_evidence'] = multi_az_items
                elif 'operational elements' in title:
                    ops_items = self._extract_list_items_funding_style(content)
                    for item in ops_items:
                        if any(svc in item.lower() for svc in ['cloudwatch', 'cloudtrail', 'x-ray', 'systems manager']):
                            result['identified_services'].append(item)
            
            # Remove duplicates from identified_services
            result['identified_services'] = list(set(result['identified_services']))
            
            logger.info(f"✅ Section-based extraction: {len(result['identified_services'])} AWS services, {len(result['architecture_patterns'])} patterns")
            
            # Fallback: Extract services using regex if still empty
            if not result['identified_services']:
                result['identified_services'] = self._extract_services(response_text)
                logger.info(f"📝 Fallback regex extraction: {len(result['identified_services'])} services")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            return {
                'identified_services': [],
                'architecture_patterns': [],
                'security_findings': [],
                'performance_insights': [],
                'cost_optimization_opportunities': [],
                'reliability_considerations': [],
                'sustainability_recommendations': [],
                'multi_az_detected': False,
                'multi_az_evidence': [],
                'evidence_based_findings': False,
                'analysis_type': analysis_type,
                'parsing_error': str(e)
            }
    
    def _extract_list_items_funding_style(self, content: str) -> list:
        """Extract list items using funding reviewer approach"""
        items = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet points, numbers, and other list markers (funding reviewer approach)
            import re
            cleaned_line = re.sub(r'^[-*•\d.)\s]+', '', line).strip()
            if cleaned_line and cleaned_line.lower() != 'not specified in document':
                items.append(cleaned_line)
        
        return items
    
    def _extract_services(self, text: str) -> List[str]:
        """Extract AWS services from analysis text"""
        services = []
        aws_services = [
            'EC2', 'S3', 'RDS', 'Lambda', 'CloudFront', 'Route53',
            'ELB', 'ALB', 'NLB', 'VPC', 'IAM', 'CloudWatch',
            'DynamoDB', 'ElastiCache', 'ECS', 'EKS', 'Fargate',
            'API Gateway', 'SNS', 'SQS', 'Step Functions'
        ]
        
        text_lower = text.lower()
        for service in aws_services:
            if service.lower() in text_lower:
                services.append(service)
        
        return list(set(services))
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract architectural patterns from analysis text"""
        patterns = []
        pattern_keywords = {
            'Microservices': ['microservice', 'microservices', 'service-oriented'],
            'Serverless': ['serverless', 'lambda', 'event-driven'],
            'Multi-tier': ['multi-tier', 'three-tier', 'n-tier'],
            'Event-driven': ['event-driven', 'event sourcing', 'pub/sub'],
            'CQRS': ['cqrs', 'command query'],
            'Circuit Breaker': ['circuit breaker', 'fault tolerance'],
            'Load Balancing': ['load balancer', 'load balancing', 'alb', 'elb']
        }
        
        text_lower = text.lower()
        for pattern, keywords in pattern_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                patterns.append(pattern)
        
        return patterns
    
    def _extract_confidence_indicators(self, text: str) -> Dict[str, Any]:
        """Extract confidence indicators from analysis"""
        indicators = {
            'explicit_evidence': 'evidence' in text.lower() or 'shown in' in text.lower(),
            'specific_references': 'figure' in text.lower() or 'diagram' in text.lower(),
            'quantitative_metrics': any(word in text.lower() for word in ['metric', 'measure', 'count', 'number']),
            'uncertainty_markers': any(word in text.lower() for word in ['might', 'could', 'possibly', 'appears'])
        }
        
        # Calculate overall confidence
        confidence_score = sum(indicators.values()) / len(indicators)
        indicators['overall_confidence'] = confidence_score
        
        return indicators
    
    def _enhance_analysis_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance and combine analysis results"""
        enhanced = {
            'analysis_timestamp': time.time(),
            'analysis_method': 'bedrock_multimodal',
            'identified_services': [],
            'architectural_patterns': [],
            'multi_az_detected': False,
            'multi_az_evidence': [],
            'evidence_based_findings': True,
            'cross_document_correlation': {},
            'confidence_score': 0.0
        }
        
        # Combine services from all analyses
        all_services = set()
        all_patterns = set()
        confidence_scores = []
        
        # Check top-level keys first (direct from _parse_analysis_response)
        if 'identified_services' in results:
            all_services.update(results['identified_services'])
        if 'architecture_patterns' in results:
            all_patterns.update(results['architecture_patterns'])
        if 'multi_az_detected' in results and results['multi_az_detected']:
            enhanced['multi_az_detected'] = True
            enhanced['multi_az_evidence'].append("Detected in analysis")
        
        # Also check nested dictionaries (for vision_analysis, etc.)
        for key, value in results.items():
            if isinstance(value, dict):
                if 'identified_services' in value:
                    all_services.update(value['identified_services'])
                if 'architectural_patterns' in value:
                    all_patterns.update(value['architectural_patterns'])
                if 'multi_az_detected' in value and value['multi_az_detected']:
                    enhanced['multi_az_detected'] = True
                    enhanced['multi_az_evidence'].append(f"Detected in {key}")
                if 'confidence_indicators' in value:
                    conf = value['confidence_indicators'].get('overall_confidence', 0.5)
                    confidence_scores.append(conf)
        
        enhanced['identified_services'] = list(all_services)
        enhanced['architectural_patterns'] = list(all_patterns)
        
        # Calculate overall confidence
        if confidence_scores:
            enhanced['confidence_score'] = sum(confidence_scores) / len(confidence_scores)
        else:
            enhanced['confidence_score'] = 0.75  # Default for successful analysis
        
        # Add cross-document correlation
        enhanced['cross_document_correlation'] = {
            'documents_analyzed': len([k for k in results.keys() if not k.endswith('_error')]),
            'consistency_score': enhanced['confidence_score'] * 100,
            'alignment_indicators': {
                'service_consistency': len(all_services) > 0,
                'pattern_consistency': len(all_patterns) > 0
            }
        }
        
        # Add original results for reference
        enhanced['detailed_analysis'] = results
        
        return enhanced
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get engine status and capabilities"""
        return {
            'engine_type': 'bedrock_multimodal',
            'region': self.region_name,
            'text_model': self.text_model,
            'vision_model': self.vision_model,
            'clients_initialized': self.bedrock_runtime is not None,
            'capabilities': {
                'text_analysis': True,
                'vision_analysis': True,
                'multimodal_fusion': True,
                'evidence_extraction': True
            }
        }