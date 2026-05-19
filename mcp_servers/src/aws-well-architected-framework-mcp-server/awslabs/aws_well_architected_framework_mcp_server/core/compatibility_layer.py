#!/usr/bin/env python3
"""
WAFR Compatibility Layer
Ensures backward compatibility while enabling AI enhancements
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .feature_flags import get_feature_flags
from .bedrock_multimodal_engine import WAFRBedrockEngine
from .wafr_prompt_library import WAFRPromptLibrary

logger = logging.getLogger(__name__)

@dataclass
class AnalysisRequest:
    """Request for document analysis"""
    documents: List[Any]
    chat_id: Optional[str] = None
    assessment_context: Dict[str, Any] = None
    enable_ai: bool = True
    enable_vision: bool = True

@dataclass
class AnalysisResult:
    """Result from document analysis"""
    status: str
    method: str  # 'ai_enhanced', 'traditional', 'hybrid'
    architecture_data: Dict[str, Any]
    processing_time: float
    ai_insights: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class WAFRCompatibilityLayer:
    """
    Compatibility layer that provides seamless integration between
    traditional WAFR analysis and new AI enhancements
    """
    
    def __init__(self):
        """Initialize compatibility layer"""
        self.feature_flags = get_feature_flags()
        self.bedrock_engine = None
        self.prompt_library = WAFRPromptLibrary()
        
        # Initialize AI components if available
        self._initialize_ai_components()
        
        logger.info("🔄 WAFR Compatibility Layer initialized")
    
    def _initialize_ai_components(self):
        """Initialize AI components if enabled and available"""
        try:
            if self.feature_flags.is_enabled('ai_analysis'):
                self.bedrock_engine = WAFRBedrockEngine()
                logger.info("🤖 AI components initialized")
            else:
                logger.info("🚫 AI components disabled by feature flags")
        except Exception as e:
            logger.warning(f"⚠️ AI components initialization failed: {e}")
            self.bedrock_engine = None
    
    async def analyze_with_fallback(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Analyze documents with AI enhancement and graceful fallback
        
        Args:
            request: Analysis request with documents and context
            
        Returns:
            AnalysisResult with method used and results
        """
        start_time = time.time()
        
        try:
            # Check if AI analysis should be attempted
            should_use_ai = (
                request.enable_ai and
                self.feature_flags.is_enabled('ai_analysis', request.chat_id) and
                self.bedrock_engine is not None
            )
            
            if should_use_ai:
                logger.info(f"🤖 Attempting AI-enhanced analysis for chat_id: {request.chat_id}")
                
                try:
                    # Attempt AI-enhanced analysis
                    ai_result = await self._perform_ai_analysis(request)
                    
                    if ai_result.status == "success":
                        processing_time = time.time() - start_time
                        logger.info(f"✅ AI-enhanced analysis completed in {processing_time:.2f}s")
                        
                        return AnalysisResult(
                            status="success",
                            method="ai_enhanced",
                            architecture_data=ai_result.analysis_data,
                            processing_time=processing_time,
                            ai_insights={
                                'model_used': ai_result.model_used,
                                'confidence_score': ai_result.confidence_score,
                                'ai_processing_time': ai_result.processing_time
                            }
                        )
                    else:
                        # AI failed, fall back to traditional
                        logger.warning(f"⚠️ AI analysis failed: {ai_result.error}")
                        if self.feature_flags.should_use_fallback('ai_analysis'):
                            return await self._perform_traditional_analysis_with_fallback(request, ai_result.error)
                        else:
                            raise Exception(ai_result.error)
                
                except Exception as e:
                    logger.error(f"❌ AI analysis error: {e}")
                    
                    # Check if fallback is enabled
                    if self.feature_flags.should_use_fallback('ai_analysis'):
                        logger.info("🔄 Falling back to traditional analysis")
                        return await self._perform_traditional_analysis_with_fallback(request, str(e))
                    else:
                        raise e
            
            else:
                # Use traditional analysis directly
                logger.info("📄 Using traditional analysis method")
                return await self._perform_traditional_analysis(request)
        
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Analysis failed completely: {e}")
            
            return AnalysisResult(
                status="error",
                method="error",
                architecture_data={},
                processing_time=processing_time,
                error=str(e)
            )
    
    async def _perform_ai_analysis(self, request: AnalysisRequest) -> Any:
        """Perform AI-enhanced analysis using Bedrock"""
        
        # Build analysis prompt
        context = request.assessment_context or {}
        context['chat_id'] = request.chat_id
        
        analysis_prompt = self.prompt_library.build_architecture_analysis_prompt(context)
        
        # Check if vision analysis is enabled
        enable_vision = (
            request.enable_vision and
            self.feature_flags.is_enabled('vision_analysis', request.chat_id)
        )
        
        # Perform multimodal analysis
        return await self.bedrock_engine.analyze_documents_multimodal(
            documents=request.documents,
            analysis_prompt=analysis_prompt,
            enable_vision=enable_vision
        )
    
    async def _perform_traditional_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """Perform traditional WAFR analysis using DocumentAnalysisEngine"""
        start_time = time.time()
        
        try:
            # Import correct WAFR component
            from ..document_processing.analysis_engine import DocumentAnalysisEngine
            
            # Initialize DocumentAnalysisEngine
            analysis_engine = DocumentAnalysisEngine()
            
            # Extract document URLs and types from request
            documents = []
            document_types = []
            
            for doc in request.documents:
                if isinstance(doc, str):
                    # Document is already a URL/path
                    documents.append(doc)
                    # Infer type from extension
                    if doc.lower().endswith('.pdf'):
                        document_types.append('pdf')
                    elif doc.lower().endswith(('.png', '.jpg', '.jpeg')):
                        document_types.append(doc.lower().split('.')[-1])
                    else:
                        document_types.append('pdf')
                elif hasattr(doc, 'url'):
                    documents.append(doc.url)
                    document_types.append(getattr(doc, 'type', 'pdf'))
            
            # Use DocumentAnalysisEngine's analyze_documents method (ASYNC!)
            analysis_result = await analysis_engine.analyze_documents(documents, document_types)
            
            # Extract services from the result
            services_identified = analysis_result.get('identified_services', [])
            
            # Generate traditional analysis result
            result = {
                "status": "success",
                "analysis_method": "traditional",
                "document_count": len(documents),
                "services_identified": services_identified,  # ✅ Now populated!
                "architectural_patterns": analysis_result.get('architecture_patterns', []),
                "multi_az_detected": analysis_result.get('multi_az_detected', False),
                "confidence_score": analysis_result.get('confidence_score', 0.75),
                "summary": analysis_result.get('summary', 'Traditional analysis completed successfully')
            }
            
            processing_time = time.time() - start_time
            
            return AnalysisResult(
                status="success",
                method="traditional",
                architecture_data=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Traditional analysis failed: {e}", exc_info=True)
            
            return AnalysisResult(
                status="error",
                method="traditional",
                architecture_data={
                    "services_identified": [],  # Empty fallback
                    "summary": f"Analysis failed: {str(e)}"
                },
                processing_time=processing_time,
                error=str(e)
            )
    
    async def _perform_traditional_analysis_with_fallback(
        self, 
        request: AnalysisRequest, 
        ai_error: str
    ) -> AnalysisResult:
        """Perform traditional analysis as fallback from AI failure"""
        
        logger.info(f"🔄 Performing traditional analysis fallback (AI error: {ai_error})")
        
        result = await self._perform_traditional_analysis(request)
        
        # Mark as fallback and include AI error info
        if result.status == "success":
            result.method = "traditional_fallback"
            result.architecture_data["fallback_used"] = True
            result.architecture_data["ai_error"] = ai_error
            result.architecture_data["fallback_reason"] = "AI analysis failed, used traditional method"
        
        return result
    
    def _calculate_traditional_scores(self, analysis_result: Dict[str, Any]) -> Dict[str, int]:
        """Calculate traditional pillar scores based on analysis result"""
        # Base score on confidence and services detected
        confidence = analysis_result.get('confidence_score', 0.5)
        services_count = len(analysis_result.get('services_identified', []))
        
        # Calculate base score (50-80 range based on confidence and services)
        base_score = int(50 + (confidence * 20) + min(services_count * 2, 10))
        
        return {
            "operational_excellence": base_score,
            "security": base_score + 5,  # Slight variation
            "reliability": base_score,
            "performance_efficiency": base_score - 5,
            "cost_optimization": base_score - 10,
            "sustainability": base_score - 5
        }
    
    def _generate_traditional_findings(self, analysis_result: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate traditional findings based on analysis result"""
        services = analysis_result.get('services_identified', [])
        patterns = analysis_result.get('architectural_patterns', [])
        
        findings = {
            "operational_excellence": [f"Identified {len(services)} AWS services in architecture"],
            "security": ["Security analysis based on service detection"],
            "reliability": ["Reliability assessment from architectural patterns"],
            "performance_efficiency": ["Performance analysis from service configuration"],
            "cost_optimization": ["Cost optimization opportunities identified"],
            "sustainability": ["Sustainability assessment completed"]
        }
        
        # Add service-specific findings
        if services:
            findings["operational_excellence"].append(f"Services detected: {', '.join(services[:5])}")
        
        if patterns:
            findings["reliability"].append(f"Architectural patterns: {', '.join(patterns)}")
        
        return findings
    
    def _generate_traditional_recommendations(self, analysis_result: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate traditional recommendations based on analysis result"""
        services = analysis_result.get('services_identified', [])
        
        recommendations = {
            "operational_excellence": ["Implement comprehensive monitoring and automation"],
            "security": ["Review and enhance security configurations"],
            "reliability": ["Implement multi-AZ deployment for high availability"],
            "performance_efficiency": ["Optimize resource utilization and performance"],
            "cost_optimization": ["Review cost optimization opportunities"],
            "sustainability": ["Implement sustainable architecture practices"]
        }
        
        # Add service-specific recommendations
        if "EC2" in services:
            recommendations["cost_optimization"].append("Consider Reserved Instances for EC2")
        
        if "S3" in services:
            recommendations["cost_optimization"].append("Implement S3 lifecycle policies")
        
        if "RDS" in services:
            recommendations["reliability"].append("Enable RDS Multi-AZ for database reliability")
        
        return recommendations
    
    def get_analysis_capabilities(self, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current analysis capabilities for a context"""
        
        enabled_features = self.feature_flags.get_enabled_features(chat_id)
        
        return {
            'ai_analysis_available': 'ai_analysis' in enabled_features,
            'vision_analysis_available': 'vision_analysis' in enabled_features,
            'evidence_based_scoring': 'evidence_based_scoring' in enabled_features,
            'cross_document_correlation': 'cross_document_correlation' in enabled_features,
            'enhanced_recommendations': 'enhanced_recommendations' in enabled_features,
            'bedrock_engine_status': self.bedrock_engine.get_engine_status() if self.bedrock_engine else None,
            'fallback_available': True,  # Traditional analysis always available
            'enabled_features': enabled_features
        }
    
    def get_compatibility_status(self) -> Dict[str, Any]:
        """Get overall compatibility layer status"""
        
        return {
            'compatibility_layer_version': '1.0.0',
            'ai_components_initialized': self.bedrock_engine is not None,
            'feature_flags_loaded': len(self.feature_flags.get_all_features_status()),
            'prompt_library_loaded': True,
            'traditional_analysis_available': True,
            'ai_analysis_available': self.bedrock_engine is not None,
            'fallback_mechanisms': {
                'ai_to_traditional': True,
                'error_handling': True,
                'graceful_degradation': True
            }
        }