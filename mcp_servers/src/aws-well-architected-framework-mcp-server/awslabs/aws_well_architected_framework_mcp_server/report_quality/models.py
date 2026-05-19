"""
Enhanced data models for WAFR report quality enhancement.

This module defines the data structures used for generating enterprise-grade
WAFR assessment reports with comprehensive content and professional formatting.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from abc import ABC, abstractmethod


# ============================================================================
# Enums and Constants
# ============================================================================

class Priority(str, Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EffortLevel(str, Enum):
    """Implementation effort estimates."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityStatusType(str, Enum):
    """Status of a capability in the architecture."""
    PRESENT = "present"
    PARTIAL = "partial"
    MISSING = "missing"


class RiskLevel(str, Enum):
    """Risk level classifications."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# Documentation and Implementation Models
# ============================================================================

@dataclass
class DocumentationLink:
    """
    AWS documentation reference link.
    
    Provides structured information about documentation resources
    with relevance scoring for prioritization.
    """
    title: str
    url: str
    description: str
    relevance: str = "high"  # "high", "medium", "low"
    link_type: str = "documentation"  # "documentation", "whitepaper", "blog", "guide"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "relevance": self.relevance,
            "link_type": self.link_type
        }


@dataclass
class ImplementationStep:
    """
    Single implementation step with detailed guidance.
    
    Provides concrete, actionable instructions for implementing
    a recommendation with validation guidance.
    """
    step_number: int
    title: str
    description: str
    aws_cli_commands: List[str] = field(default_factory=list)
    console_instructions: str = ""
    terraform_example: str = ""
    validation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description
        }
        
        if self.aws_cli_commands:
            result["aws_cli_commands"] = self.aws_cli_commands
        if self.console_instructions:
            result["console_instructions"] = self.console_instructions
        if self.terraform_example:
            result["terraform_example"] = self.terraform_example
        if self.validation:
            result["validation"] = self.validation
        
        return result


@dataclass
class ImplementationGuidance:
    """
    Complete implementation guidance for a recommendation.
    
    Provides step-by-step instructions, effort estimates,
    and testing/rollback guidance.
    """
    steps: List[ImplementationStep] = field(default_factory=list)
    estimated_effort: str = ""  # "2-4 hours", "1-2 days", etc.
    prerequisites: List[str] = field(default_factory=list)
    testing_guidance: str = ""
    rollback_plan: str = ""
    expected_score_improvement: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "estimated_effort": self.estimated_effort,
            "prerequisites": self.prerequisites,
            "testing_guidance": self.testing_guidance,
            "rollback_plan": self.rollback_plan,
            "expected_score_improvement": round(self.expected_score_improvement, 2)
        }


@dataclass
class ServiceTargeting:
    """
    Service-specific targeting for recommendations.
    
    Identifies which services need improvements and what
    specific changes are required.
    """
    services_needing_capability: List[str] = field(default_factory=list)
    services_with_capability: List[str] = field(default_factory=list)
    services_to_add: List[str] = field(default_factory=list)
    configuration_changes: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "services_needing_capability": self.services_needing_capability,
            "services_with_capability": self.services_with_capability,
            "services_to_add": self.services_to_add,
            "configuration_changes": self.configuration_changes
        }


# ============================================================================
# Enhanced Recommendation Model
# ============================================================================

@dataclass
class EnhancedRecommendation:
    """
    Enhanced recommendation with comprehensive implementation guidance.
    
    Extends basic recommendations with detailed implementation steps,
    service-specific targeting, AWS documentation links, and impact estimates.
    """
    # Core identification
    id: str
    title: str
    description: str
    
    # Classification
    pillar: str
    priority: Priority
    capability: str
    
    # Service context (enhanced)
    affected_services: List[str] = field(default_factory=list)
    service_targeting: Optional[ServiceTargeting] = None
    
    # Implementation guidance (new)
    implementation_guidance: Optional[ImplementationGuidance] = None
    
    # Documentation and references (new)
    aws_documentation_links: List[DocumentationLink] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    
    # Impact and effort
    estimated_effort: EffortLevel = EffortLevel.MEDIUM
    estimated_time: str = ""
    expected_score_improvement: float = 0.0
    business_impact: str = ""
    
    # Metadata
    gap_size: float = 0.0
    priority_score: float = 0.0
    confidence: float = 1.0
    
    def get_priority_numeric(self) -> int:
        """Get numeric priority for sorting (higher is more urgent)."""
        priority_map = {
            Priority.CRITICAL: 100,
            Priority.HIGH: 75,
            Priority.MEDIUM: 50,
            Priority.LOW: 25
        }
        return priority_map.get(self.priority, 50)
    
    def get_effort_numeric(self) -> int:
        """Get numeric effort for sorting (lower is easier)."""
        effort_map = {
            EffortLevel.LOW: 1,
            EffortLevel.MEDIUM: 2,
            EffortLevel.HIGH: 3
        }
        return effort_map.get(self.estimated_effort, 2)
    
    def get_roi_score(self) -> float:
        """Calculate ROI score (score improvement / effort)."""
        effort = self.get_effort_numeric()
        return self.expected_score_improvement / effort if effort > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pillar": self.pillar,
            "priority": self.priority.value,
            "priority_numeric": self.get_priority_numeric(),
            "capability": self.capability,
            "affected_services": self.affected_services,
            "estimated_effort": self.estimated_effort.value,
            "effort_numeric": self.get_effort_numeric(),
            "estimated_time": self.estimated_time,
            "expected_score_improvement": round(self.expected_score_improvement, 2),
            "roi_score": round(self.get_roi_score(), 2),
            "business_impact": self.business_impact,
            "best_practices": self.best_practices,
            "gap_size": round(self.gap_size, 2),
            "priority_score": round(self.priority_score, 2),
            "confidence": round(self.confidence, 2)
        }
        
        if self.service_targeting:
            result["service_targeting"] = self.service_targeting.to_dict()
        
        if self.implementation_guidance:
            result["implementation_guidance"] = self.implementation_guidance.to_dict()
        
        if self.aws_documentation_links:
            result["aws_documentation_links"] = [
                link.to_dict() for link in self.aws_documentation_links
            ]
        
        return result


# ============================================================================
# Capability Models
# ============================================================================

@dataclass
class DetectedCapability:
    """
    Capability that was detected in the architecture.
    
    Includes evidence of detection and score contribution.
    """
    name: str
    status: CapabilityStatusType
    evidence: List[str] = field(default_factory=list)
    score_contribution: float = 0.0
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "evidence": self.evidence,
            "score_contribution": round(self.score_contribution, 2),
            "description": self.description
        }


@dataclass
class MissingCapability:
    """
    Capability that is expected but not detected.
    
    Includes importance explanation and potential score impact.
    """
    name: str
    pillar: str
    importance: str  # "critical", "high", "medium", "low"
    description: str
    example_services: List[str] = field(default_factory=list)
    score_impact: float = 0.0
    why_important: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "pillar": self.pillar,
            "importance": self.importance,
            "description": self.description,
            "example_services": self.example_services,
            "score_impact": round(self.score_impact, 2),
            "why_important": self.why_important
        }


@dataclass
class CapabilityStatus:
    """
    Status of a capability with evidence and contribution.
    
    Used for capability coverage matrices in reports.
    """
    name: str
    status: str  # "present", "partial", "missing"
    evidence: List[str] = field(default_factory=list)
    score_contribution: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "evidence": self.evidence,
            "score_contribution": round(self.score_contribution, 2)
        }


# ============================================================================
# Score Breakdown Model
# ============================================================================

@dataclass
class ScoreBreakdown:
    """
    Detailed breakdown of pillar score calculation.
    
    Shows baseline score, capability contributions, and adjustments.
    """
    baseline_score: float
    capability_contributions: Dict[str, float] = field(default_factory=dict)
    adjustments: Dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "baseline_score": round(self.baseline_score, 2),
            "capability_contributions": {
                k: round(v, 2) for k, v in self.capability_contributions.items()
            },
            "adjustments": {
                k: round(v, 2) for k, v in self.adjustments.items()
            },
            "final_score": round(self.final_score, 2)
        }


# ============================================================================
# Enhanced Pillar Assessment Model
# ============================================================================

@dataclass
class EnhancedPillarAssessment:
    """
    Enhanced pillar assessment with comprehensive details.
    
    Extends basic pillar assessment with detected/missing capabilities,
    questions assessed tracking, and enhanced recommendations.
    """
    # Core fields
    pillar: str
    score: float
    risk_level: RiskLevel
    
    # Score breakdown
    score_breakdown: ScoreBreakdown
    
    # Capabilities (enhanced)
    detected_capabilities: List[DetectedCapability] = field(default_factory=list)
    missing_capabilities: List[MissingCapability] = field(default_factory=list)
    
    # Assessment metadata (new)
    questions_assessed: int = 0
    total_questions_available: int = 0
    question_coverage_percentage: float = 0.0
    confidence_level: float = 0.0
    
    # Evidence and analysis
    evidence: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[EnhancedRecommendation] = field(default_factory=list)
    
    # Documentation
    pillar_documentation_links: List[DocumentationLink] = field(default_factory=list)
    
    def get_capability_coverage_percentage(self) -> float:
        """Calculate percentage of expected capabilities that are present."""
        total_capabilities = len(self.detected_capabilities) + len(self.missing_capabilities)
        if total_capabilities == 0:
            return 0.0
        
        present_count = sum(
            1 for cap in self.detected_capabilities
            if cap.status == CapabilityStatusType.PRESENT
        )
        
        return (present_count / total_capabilities) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pillar": self.pillar,
            "score": round(self.score, 2),
            "risk_level": self.risk_level.value,
            "score_breakdown": self.score_breakdown.to_dict(),
            "detected_capabilities": [cap.to_dict() for cap in self.detected_capabilities],
            "missing_capabilities": [cap.to_dict() for cap in self.missing_capabilities],
            "questions_assessed": self.questions_assessed,
            "total_questions_available": self.total_questions_available,
            "question_coverage_percentage": round(self.question_coverage_percentage, 2),
            "capability_coverage_percentage": round(self.get_capability_coverage_percentage(), 2),
            "confidence_level": round(self.confidence_level, 2),
            "evidence": self.evidence,
            "gaps": self.gaps,
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "pillar_documentation_links": [link.to_dict() for link in self.pillar_documentation_links]
        }


# ============================================================================
# Executive Summary Models
# ============================================================================

@dataclass
class KeyFinding:
    """
    Key finding for executive summary.
    
    Represents a significant strength or weakness in the architecture.
    """
    title: str
    description: str
    pillar: str
    impact: str  # "high", "medium", "low"
    finding_type: str = "weakness"  # "strength" or "weakness"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "pillar": self.pillar,
            "impact": self.impact,
            "finding_type": self.finding_type
        }


@dataclass
class ExecutiveSummary:
    """
    Executive summary for WAFR assessment report.
    
    Provides high-level overview with key findings, metrics,
    and priority recommendations for executive stakeholders.
    """
    # Overall metrics
    overall_score: float
    overall_risk_level: RiskLevel
    architecture_confidence: float
    assessment_date: str
    
    # Architecture overview
    services_analyzed: int
    patterns_detected: List[str] = field(default_factory=list)
    architecture_name: str = ""
    
    # Key findings
    top_strengths: List[KeyFinding] = field(default_factory=list)
    top_weaknesses: List[KeyFinding] = field(default_factory=list)
    critical_risks: List[str] = field(default_factory=list)
    
    # Recommendations
    top_priority_actions: List[EnhancedRecommendation] = field(default_factory=list)
    estimated_total_effort: str = ""
    expected_score_improvement: float = 0.0
    
    # Pillar summary
    pillar_scores: Dict[str, float] = field(default_factory=dict)
    pillar_risk_levels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_score": round(self.overall_score, 2),
            "overall_risk_level": self.overall_risk_level.value,
            "architecture_confidence": round(self.architecture_confidence, 2),
            "assessment_date": self.assessment_date,
            "services_analyzed": self.services_analyzed,
            "patterns_detected": self.patterns_detected,
            "architecture_name": self.architecture_name,
            "top_strengths": [finding.to_dict() for finding in self.top_strengths],
            "top_weaknesses": [finding.to_dict() for finding in self.top_weaknesses],
            "critical_risks": self.critical_risks,
            "top_priority_actions": [rec.to_dict() for rec in self.top_priority_actions],
            "estimated_total_effort": self.estimated_total_effort,
            "expected_score_improvement": round(self.expected_score_improvement, 2),
            "pillar_scores": {k: round(v, 2) for k, v in self.pillar_scores.items()},
            "pillar_risk_levels": self.pillar_risk_levels
        }


# ============================================================================
# Base Interfaces for Components
# ============================================================================

class ContentEnricher(ABC):
    """
    Abstract base class for content enrichment components.
    
    Content enrichers analyze assessment data and add additional
    information like missing capabilities or service specificity.
    """
    
    @abstractmethod
    def enrich(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich assessment data with additional information.
        
        Args:
            assessment_data: Raw assessment data
            
        Returns:
            Enriched assessment data
        """
        pass


class RecommendationEnhancer(ABC):
    """
    Abstract base class for recommendation enhancement components.
    
    Recommendation enhancers add implementation guidance, documentation
    links, and service-specific targeting to recommendations.
    """
    
    @abstractmethod
    def enhance(self, recommendation: Dict[str, Any]) -> EnhancedRecommendation:
        """
        Enhance a recommendation with additional details.
        
        Args:
            recommendation: Basic recommendation data
            
        Returns:
            Enhanced recommendation with implementation guidance
        """
        pass


class ReportFormatter(ABC):
    """
    Abstract base class for report formatting components.
    
    Report formatters convert assessment data into formatted
    documents (DOCX, PDF, etc.) with professional styling.
    """
    
    @abstractmethod
    def format(self, assessment_data: Dict[str, Any], output_path: str) -> str:
        """
        Format assessment data into a professional report.
        
        Args:
            assessment_data: Complete assessment data
            output_path: Path where report should be saved
            
        Returns:
            Path to generated report file
        """
        pass
