#!/usr/bin/env python3
"""
Enterprise Integration Layer for WAFR Assessment

This module integrates enterprise enhancements into the WAFR assessment workflow:
1. Enhanced Recommendation Engine (architecture-specific with AWS docs)
2. Score Transparency Engine (user-friendly output)

All SERA reports are human-reviewed, so this focuses on providing better
recommendations and clearer score explanations.

Author: Enterprise WAFR Team
Version: 2.0.0 (Simplified)
Date: 2025-11-13
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import enterprise modules
from ..core.enhanced_recommendation_engine import enhanced_recommendation_engine
from ..core.score_transparency_engine import get_transparency_engine

logger = logging.getLogger(__name__)

class EnterpriseWAFRIntegration:
    """
    Integration layer that enhances WAFR assessments.
    
    Provides:
    - Architecture-specific recommendations with AWS documentation links
    - User-friendly score transparency (no technical jargon)
    """
    
    def __init__(self):
        self.recommendation_engine = enhanced_recommendation_engine
        self.transparency_engine = get_transparency_engine()
        logger.info("🚀 Enterprise WAFR Integration initialized")
    
    def enhance_pillar_assessment(
        self,
        pillar: str,
        pillar_score: float,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        detected_services: List[str]
    ) -> Dict[str, Any]:
        """
        Enhance a pillar assessment with enterprise features.
        
        Args:
            pillar: Pillar name
            pillar_score: Calculated score (0.0 to 1.0)
            detected_capabilities: List of detected capabilities
            missing_capabilities: List of missing capabilities
            detected_services: List of detected AWS services
            
        Returns:
            Enhanced pillar assessment with recommendations and transparency
        """
        
        logger.info(f"🔧 Enhancing {pillar} assessment with enterprise modules")
        
        # Generate architecture-specific recommendations
        current_coverage = len(detected_capabilities) / (len(detected_capabilities) + len(missing_capabilities)) if (len(detected_capabilities) + len(missing_capabilities)) > 0 else 0
        
        recommendations = self.recommendation_engine.generate_recommendations(
            pillar=pillar,
            detected_capabilities=detected_capabilities,
            missing_capabilities=missing_capabilities,
            detected_services=detected_services,
            current_coverage=current_coverage
        )
        
        # Generate user-friendly transparency report
        transparency_report = self.transparency_engine.format_simple_pillar_report(
            pillar=pillar,
            score=pillar_score,
            detected_capabilities=detected_capabilities,
            missing_capabilities=missing_capabilities,
            detected_services=detected_services
        )
        
        # Format recommendations for output
        formatted_recommendations = []
        for rec in recommendations:
            formatted_recommendations.append({
                "title": rec.title,
                "description": rec.description,
                "priority": rec.priority.value,
                "effort": rec.effort.value,
                "implementation_steps": rec.implementation_steps,
                "configuration_examples": rec.configuration_examples,
                "aws_documentation_links": rec.aws_documentation_links,
                "expected_impact": rec.expected_impact,
                "cost_impact": rec.cost_impact,
                "aws_services": rec.aws_services
            })
        
        return {
            "pillar": pillar,
            "score": int(pillar_score * 100),
            "detected_capabilities": detected_capabilities,
            "missing_capabilities": missing_capabilities,
            "recommendations": formatted_recommendations,
            "transparency_report": transparency_report,
            "recommendation_count": len(recommendations)
        }
    


# Global instance
enterprise_integration = EnterpriseWAFRIntegration()
