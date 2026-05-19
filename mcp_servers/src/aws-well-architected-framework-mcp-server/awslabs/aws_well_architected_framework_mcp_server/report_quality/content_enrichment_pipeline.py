"""
Content Enrichment Pipeline for WAFR Report Quality Enhancement.

This module orchestrates the content enrichment process, coordinating
the Missing Capability Analyzer, Questions Assessed Counter, and Service
Specificity Analyzer to enhance assessment data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.logger import WAFRLogger
from .missing_capability_analyzer import MissingCapabilityAnalyzer
from .questions_assessed_counter import QuestionsAssessedCounter
from .service_specificity_analyzer import ServiceSpecificityAnalyzer
from .models import (
    EnhancedPillarAssessment,
    DetectedCapability,
    ScoreBreakdown,
    RiskLevel,
    CapabilityStatusType
)


class ContentEnrichmentPipeline:
    """
    Orchestrates content enrichment for WAFR assessments.
    
    This pipeline coordinates multiple analyzers to enhance assessment data with:
    - Missing capability identification
    - Questions assessed tracking
    - Service-specific targeting
    
    Example:
        pipeline = ContentEnrichmentPipeline()
        
        enriched_data = pipeline.enrich_assessment(
            assessment_data={
                "pillar": "security",
                "score": 75.0,
                "detected_capabilities": ["encryption", "identity_access"],
                "architecture_services": ["Lambda", "DynamoDB", "S3"]
            }
        )
        # Returns: Enhanced assessment with missing capabilities and metrics
    """
    
    def __init__(self):
        """Initialize the content enrichment pipeline."""
        self.logger = WAFRLogger(__name__)
        
        # Initialize component analyzers
        self.missing_capability_analyzer = MissingCapabilityAnalyzer()
        self.questions_counter = QuestionsAssessedCounter()
        self.service_specificity_analyzer = ServiceSpecificityAnalyzer()
        
        self.logger.info("ContentEnrichmentPipeline initialized")
    
    def enrich_pillar_assessment(
        self,
        pillar: str,
        assessment_data: Dict[str, Any],
        questions_assessed: Optional[int] = None,
        assessment_method: Optional[str] = None
    ) -> EnhancedPillarAssessment:
        """
        Enrich a single pillar assessment with comprehensive details.
        
        Args:
            pillar: WAFR pillar name
            assessment_data: Raw assessment data from pillar assessment
            questions_assessed: Number of questions assessed (optional)
            assessment_method: Assessment method used (optional)
            
        Returns:
            EnhancedPillarAssessment with all enrichments
        """
        self.logger.info(f"Enriching pillar assessment: {pillar}")
        
        # Extract core data
        score = assessment_data.get("score", 0.0)
        detected_capabilities_raw = assessment_data.get("detected_capabilities", [])
        architecture_services = assessment_data.get("architecture_services", [])
        detected_patterns = assessment_data.get("detected_patterns", [])
        score_breakdown_raw = assessment_data.get("score_breakdown", {})
        
        # Convert detected capabilities to proper format
        detected_capabilities = self._convert_detected_capabilities(
            detected_capabilities_raw,
            pillar
        )
        
        # Extract capability names for analysis
        detected_capability_names = [
            cap.name if isinstance(cap, DetectedCapability) else cap
            for cap in detected_capabilities_raw
        ]
        
        # Step 1: Identify missing capabilities
        missing_capabilities = self.missing_capability_analyzer.analyze_pillar_gaps(
            pillar=pillar,
            detected_capabilities=detected_capability_names,
            architecture_services=architecture_services,
            detected_patterns=detected_patterns
        )
        
        self.logger.info(
            f"Found {len(missing_capabilities)} missing capabilities for {pillar}"
        )
        
        # Step 2: Track questions assessed
        if questions_assessed is not None:
            self.questions_counter.set_question_count(
                pillar=pillar,
                count=questions_assessed,
                assessment_method=assessment_method
            )
        
        coverage_metrics = self.questions_counter.get_coverage_metrics(pillar)
        
        # Step 3: Create score breakdown
        score_breakdown = self._create_score_breakdown(
            score_breakdown_raw,
            score
        )
        
        # Step 4: Determine risk level
        risk_level = self._determine_risk_level(score)
        
        # Step 5: Extract evidence and gaps
        evidence = assessment_data.get("evidence", [])
        gaps = [cap.description for cap in missing_capabilities]
        
        # Step 6: Get confidence level
        confidence_level = score_breakdown_raw.get("confidence_level", 0.8)
        
        # Create enhanced pillar assessment
        enhanced_assessment = EnhancedPillarAssessment(
            pillar=pillar,
            score=score,
            risk_level=risk_level,
            score_breakdown=score_breakdown,
            detected_capabilities=detected_capabilities,
            missing_capabilities=missing_capabilities,
            questions_assessed=coverage_metrics.questions_assessed,
            total_questions_available=coverage_metrics.total_questions_available,
            question_coverage_percentage=coverage_metrics.coverage_percentage,
            confidence_level=confidence_level,
            evidence=evidence,
            gaps=gaps,
            recommendations=[],  # Will be populated by recommendation engine
            pillar_documentation_links=[]  # Will be populated by documentation linker
        )
        
        self.logger.info(
            f"Enriched {pillar} assessment: "
            f"score={score:.2f}, "
            f"detected_caps={len(detected_capabilities)}, "
            f"missing_caps={len(missing_capabilities)}, "
            f"questions={coverage_metrics.questions_assessed}"
        )
        
        return enhanced_assessment
    
    def enrich_comprehensive_assessment(
        self,
        pillar_assessments: Dict[str, Dict[str, Any]],
        architecture_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, EnhancedPillarAssessment]:
        """
        Enrich all pillar assessments in a comprehensive assessment.
        
        Args:
            pillar_assessments: Dictionary of pillar assessments
            architecture_data: Optional architecture data
            
        Returns:
            Dictionary of enhanced pillar assessments
        """
        self.logger.info(
            f"Enriching comprehensive assessment with {len(pillar_assessments)} pillars"
        )
        
        enhanced_assessments = {}
        
        for pillar, assessment_data in pillar_assessments.items():
            # Get questions assessed from data sources
            data_sources = assessment_data.get("data_sources", {})
            questions_assessed = data_sources.get("questions_assessed", 0)
            assessment_method = data_sources.get("assessment_method", "hybrid")
            
            # Enrich pillar assessment
            enhanced_assessment = self.enrich_pillar_assessment(
                pillar=pillar,
                assessment_data=assessment_data,
                questions_assessed=questions_assessed,
                assessment_method=assessment_method
            )
            
            enhanced_assessments[pillar] = enhanced_assessment
        
        # Log summary
        summary = self.questions_counter.get_assessment_summary()
        self.logger.info(
            f"Assessment enrichment complete: "
            f"{summary['total_questions_assessed']} questions assessed, "
            f"{summary['overall_coverage_percentage']:.1f}% coverage"
        )
        
        return enhanced_assessments
    
    def enrich_recommendations_with_service_targeting(
        self,
        recommendations: List[Dict[str, Any]],
        all_services: List[str],
        detected_capabilities: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich recommendations with service-specific targeting.
        
        Args:
            recommendations: List of recommendation dictionaries
            all_services: All services in architecture
            detected_capabilities: Map of capabilities to services
            
        Returns:
            List of enriched recommendations with service targeting
        """
        self.logger.info(
            f"Enriching {len(recommendations)} recommendations with service targeting"
        )
        
        enriched_recommendations = []
        
        for rec in recommendations:
            capability = rec.get("capability", "")
            
            if capability:
                # Identify affected services
                service_targeting = self.service_specificity_analyzer.identify_affected_services(
                    capability=capability,
                    all_services=all_services,
                    detected_capabilities=detected_capabilities
                )
                
                # Add service targeting to recommendation
                rec["service_targeting"] = service_targeting.to_dict()
                rec["affected_services"] = service_targeting.services_needing_capability
                rec["services_to_add"] = service_targeting.services_to_add
                rec["configuration_changes"] = service_targeting.configuration_changes
                
                self.logger.debug(
                    f"Recommendation for {capability}: "
                    f"{len(service_targeting.services_needing_capability)} services affected"
                )
            
            enriched_recommendations.append(rec)
        
        return enriched_recommendations
    
    def _convert_detected_capabilities(
        self,
        capabilities_raw: List,
        pillar: str
    ) -> List[DetectedCapability]:
        """
        Convert raw capability data to DetectedCapability objects.
        
        Args:
            capabilities_raw: Raw capability data (strings or dicts)
            pillar: Pillar name
            
        Returns:
            List of DetectedCapability objects
        """
        detected_capabilities = []
        
        for cap in capabilities_raw:
            if isinstance(cap, DetectedCapability):
                detected_capabilities.append(cap)
            elif isinstance(cap, dict):
                detected_capabilities.append(
                    DetectedCapability(
                        name=cap.get("name", ""),
                        status=CapabilityStatusType(cap.get("status", "present")),
                        evidence=cap.get("evidence", []),
                        score_contribution=cap.get("score_contribution", 0.0),
                        description=cap.get("description", "")
                    )
                )
            elif isinstance(cap, str):
                detected_capabilities.append(
                    DetectedCapability(
                        name=cap,
                        status=CapabilityStatusType.PRESENT,
                        evidence=[],
                        score_contribution=0.0,
                        description=""
                    )
                )
        
        return detected_capabilities
    
    def _create_score_breakdown(
        self,
        breakdown_raw: Dict[str, Any],
        final_score: float
    ) -> ScoreBreakdown:
        """
        Create ScoreBreakdown object from raw data.
        
        Args:
            breakdown_raw: Raw score breakdown data
            final_score: Final pillar score
            
        Returns:
            ScoreBreakdown object
        """
        return ScoreBreakdown(
            baseline_score=breakdown_raw.get("baseline_score", 0.0),
            capability_contributions=breakdown_raw.get("capability_contributions", {}),
            adjustments=breakdown_raw.get("adjustments", {}),
            final_score=final_score
        )
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """
        Determine risk level based on score.
        
        Args:
            score: Pillar score (0-100)
            
        Returns:
            RiskLevel enum value
        """
        if score >= 80:
            return RiskLevel.LOW
        elif score >= 60:
            return RiskLevel.MEDIUM
        elif score >= 40:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def get_enrichment_summary(self) -> Dict[str, Any]:
        """
        Get summary of enrichment pipeline execution.
        
        Returns:
            Dictionary with enrichment statistics
        """
        questions_summary = self.questions_counter.get_assessment_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "questions_assessed": questions_summary,
            "components": {
                "missing_capability_analyzer": "active",
                "questions_assessed_counter": "active",
                "service_specificity_analyzer": "active"
            }
        }
    
    def reset(self) -> None:
        """Reset the pipeline state."""
        self.questions_counter.reset()
        self.logger.info("Content enrichment pipeline reset")


# Global instance for easy access
content_enrichment_pipeline = ContentEnrichmentPipeline()
