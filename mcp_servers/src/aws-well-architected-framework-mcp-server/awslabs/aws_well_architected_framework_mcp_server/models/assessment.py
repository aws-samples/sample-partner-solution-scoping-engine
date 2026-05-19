"""Assessment data models for WAFR MCP Server"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field


class PillarName(str, Enum):
    """WAFR pillar names."""
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE_EFFICIENCY = "performance_efficiency"
    COST_OPTIMIZATION = "cost_optimization"
    SUSTAINABILITY = "sustainability"


class RiskLevel(str, Enum):
    """Risk classification levels."""
    HIGH = "HRI"  # High Risk Issues
    MEDIUM = "MRI"  # Medium Risk Issues
    LOW = "LRI"  # Low Risk Issues


class AssessmentStatus(str, Enum):
    """Assessment status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentInfo:
    """Document processing information with Claude Citations API support."""
    
    document_id: str
    filename: str
    file_type: str  # "pdf", "txt", "png", "jpeg" for primary analysis
    file_size: int
    upload_timestamp: datetime
    
    processing_status: str = "uploaded"  # "uploaded", "processing", "completed", "failed"
    extracted_data: Optional[Dict[str, Any]] = None
    
    # Claude Citations API results
    text_analysis: Optional[Dict[str, Any]] = None
    chart_analysis: Optional[Dict[str, Any]] = None
    visual_analysis: Optional[Dict[str, Any]] = None  # embedded images and diagrams
    
    # Service identification results
    identified_services: List[str] = field(default_factory=list)
    architectural_patterns: List[str] = field(default_factory=list)
    configuration_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    processing_errors: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class AWSService:
    """AWS service identification and configuration."""
    
    service_name: str
    service_type: str  # "compute", "storage", "database", etc.
    confidence_score: float
    
    identified_from: List[str] = field(default_factory=list)  # "document", "diagram", "live_scan"
    configurations: Dict[str, Any] = field(default_factory=dict)
    
    # WAFR relevance
    pillar_relevance: Dict[str, List[str]] = field(default_factory=dict)
    best_practices: List[str] = field(default_factory=list)
    potential_issues: List[str] = field(default_factory=list)


@dataclass
class Finding:
    """Individual assessment finding."""
    
    finding_id: str
    title: str
    description: str
    pillar: PillarName
    
    risk_level: RiskLevel
    confidence_score: float
    
    affected_services: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    
    # Impact assessment
    business_impact: str = ""
    technical_impact: str = ""
    financial_impact: Optional[float] = None
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    implementation_effort: str = ""  # "low", "medium", "high"
    
    # Documentation links
    aws_documentation_links: List[str] = field(default_factory=list)
    best_practice_links: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Finding to dictionary for serialization."""
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "description": self.description,
            "pillar": self.pillar.value if isinstance(self.pillar, PillarName) else str(self.pillar),
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "confidence_score": self.confidence_score,
            "affected_services": self.affected_services,
            "evidence": self.evidence,
            "business_impact": self.business_impact,
            "technical_impact": self.technical_impact,
            "financial_impact": self.financial_impact,
            "recommendations": self.recommendations,
            "implementation_effort": self.implementation_effort,
            "aws_documentation_links": self.aws_documentation_links,
            "best_practice_links": self.best_practice_links
        }


@dataclass
class Recommendation:
    """Actionable recommendation."""
    
    recommendation_id: str
    title: str
    description: str
    
    pillar: PillarName
    priority: int  # 1 = highest priority
    
    # Implementation details
    implementation_steps: List[str] = field(default_factory=list)
    estimated_effort_hours: Optional[int] = None
    estimated_cost: Optional[float] = None
    
    # Benefits
    expected_benefits: List[str] = field(default_factory=list)
    risk_reduction: RiskLevel = RiskLevel.LOW
    
    # Dependencies
    prerequisites: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Documentation
    aws_documentation_links: List[str] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Recommendation to dictionary for serialization."""
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "pillar": self.pillar.value if isinstance(self.pillar, PillarName) else str(self.pillar),
            "priority": self.priority,
            "implementation_steps": self.implementation_steps,
            "estimated_effort_hours": self.estimated_effort_hours,
            "estimated_cost": self.estimated_cost,
            "expected_benefits": self.expected_benefits,
            "risk_reduction": self.risk_reduction.value if isinstance(self.risk_reduction, RiskLevel) else str(self.risk_reduction),
            "prerequisites": self.prerequisites,
            "dependencies": self.dependencies,
            "aws_documentation_links": self.aws_documentation_links,
            "code_examples": self.code_examples
        }


@dataclass
class PillarAssessment:
    """Individual pillar assessment results."""
    
    pillar_name: PillarName
    score: float  # 0.0 to 100.0
    grade: str  # "A", "B", "C", "D", "F"
    status: AssessmentStatus = AssessmentStatus.NOT_STARTED
    
    findings: List[Finding] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    
    # Assessment metadata
    assessment_timestamp: Optional[datetime] = None
    assessment_duration_seconds: Optional[float] = None
    
    # AWS API integration data
    aws_api_data: Optional[Dict[str, Any]] = None
    wellarchitected_answers: Optional[Dict[str, Any]] = None
    
    # Quantitative metrics
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    
    def get_total_findings(self) -> int:
        """Get total number of findings."""
        return len(self.findings)
    
    def get_risk_summary(self) -> Dict[str, int]:
        """Get risk level summary."""
        return {
            "high": self.high_risk_count,
            "medium": self.medium_risk_count,
            "low": self.low_risk_count,
            "total": self.get_total_findings()
        }


@dataclass
class RiskSummary:
    """Overall risk assessment summary."""
    
    total_risks: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    
    total_financial_impact: float = 0.0
    highest_priority_risks: List[Finding] = field(default_factory=list)
    
    # Risk distribution by pillar
    pillar_risk_distribution: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def get_risk_score(self) -> float:
        """Calculate overall risk score (0-100, lower is better)."""
        if self.total_risks == 0:
            return 0.0
        
        # Weight risks: High=10, Medium=5, Low=1
        weighted_score = (
            self.high_risk_count * 10 +
            self.medium_risk_count * 5 +
            self.low_risk_count * 1
        )
        
        # Normalize to 0-100 scale (assuming max 50 total risks)
        max_possible_score = 50 * 10  # 50 high risks
        return min(100.0, (weighted_score / max_possible_score) * 100)


@dataclass
class ImplementationRoadmap:
    """Implementation roadmap for recommendations."""
    
    phases: List[Dict[str, Any]] = field(default_factory=list)
    total_estimated_time_weeks: int = 0
    total_estimated_cost: float = 0.0
    
    # Dependencies and sequencing
    critical_path: List[str] = field(default_factory=list)
    parallel_tracks: List[List[str]] = field(default_factory=list)
    
    # Resource requirements
    required_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)


@dataclass
class WAFRAssessment:
    """Complete WAFR assessment data model."""
    
    assessment_id: str
    chat_id: str
    timestamp: datetime
    
    # Input data
    uploaded_documents: List[DocumentInfo] = field(default_factory=list)
    solution_description: Optional[str] = None
    aws_environment_data: Optional[Dict[str, Any]] = None
    
    # Analysis results
    identified_services: List[AWSService] = field(default_factory=list)
    architectural_patterns: List[str] = field(default_factory=list)
    
    # Pillar assessments
    operational_excellence: Optional[PillarAssessment] = None
    security: Optional[PillarAssessment] = None
    reliability: Optional[PillarAssessment] = None
    performance_efficiency: Optional[PillarAssessment] = None
    cost_optimization: Optional[PillarAssessment] = None
    sustainability: Optional[PillarAssessment] = None
    
    # Overall results
    overall_score: float = 0.0
    grade_classification: str = "F"
    risk_summary: Optional[RiskSummary] = None
    implementation_roadmap: Optional[ImplementationRoadmap] = None
    
    # Assessment metadata
    assessment_status: AssessmentStatus = AssessmentStatus.NOT_STARTED
    assessment_duration_seconds: Optional[float] = None
    
    def get_all_pillars(self) -> List[PillarAssessment]:
        """Get all pillar assessments."""
        pillars = []
        for pillar_attr in [
            'operational_excellence', 'security', 'reliability',
            'performance_efficiency', 'cost_optimization', 'sustainability'
        ]:
            pillar = getattr(self, pillar_attr)
            if pillar:
                pillars.append(pillar)
        return pillars
    
    def get_pillar_by_name(self, pillar_name: PillarName) -> Optional[PillarAssessment]:
        """Get pillar assessment by name."""
        pillar_mapping = {
            PillarName.OPERATIONAL_EXCELLENCE: self.operational_excellence,
            PillarName.SECURITY: self.security,
            PillarName.RELIABILITY: self.reliability,
            PillarName.PERFORMANCE_EFFICIENCY: self.performance_efficiency,
            PillarName.COST_OPTIMIZATION: self.cost_optimization,
            PillarName.SUSTAINABILITY: self.sustainability
        }
        return pillar_mapping.get(pillar_name)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall assessment score."""
        pillars = self.get_all_pillars()
        if not pillars:
            return 0.0
        
        total_score = sum(pillar.score for pillar in pillars)
        return total_score / len(pillars)
    
    def get_grade_classification(self) -> str:
        """Get letter grade based on overall score."""
        score = self.overall_score
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class AssessmentRequest(BaseModel):
    """Request model for WAFR assessment."""
    
    chat_id: str = Field(..., description="Unique chat session identifier")
    solution_text: Optional[str] = Field(None, description="Optional solution description text")
    uploaded_documents: List[str] = Field(default_factory=list, description="List of uploaded document paths/URLs")
    aws_credentials: Optional[Dict[str, str]] = Field(None, description="Optional AWS credentials for live scanning")
    assessment_scope: List[str] = Field(default_factory=lambda: ["all"], description="List of WAFR pillars to assess or ['all']")
    include_live_scan: bool = Field(False, description="Whether to scan live AWS environment")
    
    # Optional parameters
    business_requirements: Optional[str] = Field(None, description="Business requirements and context")
    compliance_requirements: Optional[List[str]] = Field(None, description="List of compliance requirements")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True