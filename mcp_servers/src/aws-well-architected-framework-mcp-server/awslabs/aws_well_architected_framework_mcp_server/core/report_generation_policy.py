"""
Report generation policy for enterprise-grade WAFR assessments.

This module provides quality gates and policy evaluation for WAFR report generation,
ensuring reports meet minimum quality standards before being generated.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of policy decisions."""
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class QualityLevel(Enum):
    """Quality levels for assessments."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


@dataclass
class AssessmentQualityInput:
    """
    Input data for assessment quality evaluation.
    
    Contains all metrics needed to evaluate whether a WAFR assessment
    meets quality standards for report generation.
    """
    chat_id: str
    confidence_score: float = 0.5
    capability_detection_rate: float = 0.0
    zero_capability_incidents: int = 0
    overall_quality_score: float = 0.5
    detected_services_count: int = 0
    total_capabilities_detected: int = 0
    pillar_scores: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    """
    Result of policy evaluation.
    
    Contains the decision, reasoning, and any required actions or warnings.
    """
    decision_type: DecisionType
    quality_level: QualityLevel
    allowed: bool
    reason: str
    review_required: bool = False
    watermark_text: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    required_actions: List[str] = field(default_factory=list)


class ReportGenerationPolicy:
    """
    Enterprise-grade policy engine for WAFR report generation.
    
    Evaluates assessment quality and determines whether reports should be
    generated, blocked, or flagged for review.
    """
    
    # Quality thresholds
    MIN_CONFIDENCE_SCORE = 0.3
    MIN_QUALITY_SCORE = 0.3
    MIN_SERVICES_COUNT = 1
    MIN_CAPABILITIES_COUNT = 1
    
    def __init__(self, environment: str = "production"):
        """
        Initialize policy engine.
        
        Args:
            environment: Deployment environment (production, staging, development)
        """
        self.environment = environment
        self.strict_mode = environment == "production"
        logger.info(f"Initialized ReportGenerationPolicy for {environment} environment")
    
    def evaluate_report_generation_policy(
        self, 
        quality_input: AssessmentQualityInput
    ) -> PolicyDecision:
        """
        Evaluate whether a report should be generated based on quality metrics.
        
        Args:
            quality_input: Assessment quality metrics
            
        Returns:
            PolicyDecision with approval status and reasoning
        """
        warnings = []
        required_actions = []
        
        # Determine quality level
        quality_level = self._determine_quality_level(quality_input)
        
        # Check for blocking conditions
        blocking_reasons = []
        
        # Check confidence score
        if quality_input.confidence_score < self.MIN_CONFIDENCE_SCORE:
            if self.strict_mode:
                blocking_reasons.append(
                    f"Confidence score ({quality_input.confidence_score:.2f}) below minimum ({self.MIN_CONFIDENCE_SCORE})"
                )
            else:
                warnings.append(f"Low confidence score: {quality_input.confidence_score:.2f}")
        
        # Check for zero capabilities (indicates analysis failure)
        if quality_input.zero_capability_incidents > 0 and quality_input.total_capabilities_detected == 0:
            if self.strict_mode:
                blocking_reasons.append("No capabilities detected - analysis may have failed")
            else:
                warnings.append("No capabilities detected in assessment")
                required_actions.append("Review document analysis results")
        
        # Check services count
        if quality_input.detected_services_count < self.MIN_SERVICES_COUNT:
            warnings.append(f"Low service count: {quality_input.detected_services_count}")
            required_actions.append("Verify documents contain AWS service information")
        
        # Check validation errors
        if quality_input.validation_errors:
            for error in quality_input.validation_errors[:3]:  # Limit to first 3
                warnings.append(f"Validation issue: {error}")
        
        # Make decision
        if blocking_reasons:
            return PolicyDecision(
                decision_type=DecisionType.BLOCKED,
                quality_level=quality_level,
                allowed=False,
                reason="; ".join(blocking_reasons),
                review_required=False,
                warnings=warnings,
                required_actions=required_actions
            )
        
        # Check if review is required
        review_required = quality_level in [QualityLevel.POOR, QualityLevel.ACCEPTABLE]
        
        # Determine watermark for lower quality reports
        watermark_text = None
        if quality_level == QualityLevel.POOR:
            watermark_text = "DRAFT - Review Required"
        elif quality_level == QualityLevel.ACCEPTABLE:
            watermark_text = "Preliminary Assessment"
        
        # Approved with or without warnings
        if warnings:
            return PolicyDecision(
                decision_type=DecisionType.APPROVED_WITH_WARNINGS,
                quality_level=quality_level,
                allowed=True,
                reason=f"Assessment approved with {len(warnings)} warning(s)",
                review_required=review_required,
                watermark_text=watermark_text,
                warnings=warnings,
                required_actions=required_actions
            )
        
        return PolicyDecision(
            decision_type=DecisionType.APPROVED,
            quality_level=quality_level,
            allowed=True,
            reason="Assessment meets all quality standards",
            review_required=review_required,
            watermark_text=watermark_text,
            warnings=[],
            required_actions=[]
        )
    
    def _determine_quality_level(self, quality_input: AssessmentQualityInput) -> QualityLevel:
        """
        Determine the quality level based on input metrics.
        
        Args:
            quality_input: Assessment quality metrics
            
        Returns:
            QualityLevel enum value
        """
        score = quality_input.overall_quality_score
        confidence = quality_input.confidence_score
        capabilities = quality_input.total_capabilities_detected
        
        # Calculate composite score with adjusted weights
        # FIX Issue 7: Reduced capability divisor from 20 to 10 (more realistic)
        # and adjusted thresholds to be more achievable
        composite = (score * 0.4) + (confidence * 0.3) + (min(capabilities / 10, 1.0) * 0.3)
        
        # FIX Issue 7: Lowered thresholds to be more achievable
        # EXCELLENT: 0.85 -> 0.70 (achievable with good assessment)
        # GOOD: 0.70 -> 0.55
        # ACCEPTABLE: 0.50 -> 0.40
        # POOR: 0.30 -> 0.25
        if composite >= 0.70:
            return QualityLevel.EXCELLENT
        elif composite >= 0.55:
            return QualityLevel.GOOD
        elif composite >= 0.40:
            return QualityLevel.ACCEPTABLE
        elif composite >= 0.25:
            return QualityLevel.POOR
        else:
            return QualityLevel.INSUFFICIENT


def get_report_policy(environment: str = "production") -> ReportGenerationPolicy:
    """
    Get a configured report generation policy instance.
    
    Args:
        environment: Deployment environment
        
    Returns:
        Configured ReportGenerationPolicy instance
    """
    return ReportGenerationPolicy(environment=environment)


def get_report_generation_policy() -> ReportGenerationPolicy:
    """
    Get default report generation policy.
    
    Returns:
        ReportGenerationPolicy instance with default settings
    """
    return ReportGenerationPolicy()
