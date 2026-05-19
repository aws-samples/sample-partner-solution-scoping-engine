"""Recommendation data models for WAFR enterprise scoring."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ImplementationEffort(str, Enum):
    """Implementation effort estimates."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ImplementationStep:
    """
    A single implementation step for a recommendation.
    
    Provides concrete, actionable guidance.
    """
    
    step_number: int
    description: str
    aws_service: Optional[str] = None
    configuration_example: Optional[Dict[str, Any]] = None
    documentation_link: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "step_number": self.step_number,
            "description": self.description
        }
        
        if self.aws_service:
            result["aws_service"] = self.aws_service
        if self.configuration_example:
            result["configuration_example"] = self.configuration_example
        if self.documentation_link:
            result["documentation_link"] = self.documentation_link
        
        return result


@dataclass
class EnhancedRecommendation:
    """
    Detailed, actionable recommendation for architecture improvement.
    
    Provides capability-specific, service-specific guidance with
    implementation steps and impact estimates.
    """
    
    # Core identification
    id: str  # Unique recommendation ID
    title: str  # Short, descriptive title
    description: str  # Detailed description of the recommendation
    
    # Classification
    pillar: str  # WAFR pillar (security, reliability, etc.)
    priority: RecommendationPriority  # Priority level
    capability_addressed: str  # Which capability this improves
    
    # Service context
    affected_services: List[str]  # Specific services to modify
    missing_services: List[str] = field(default_factory=list)  # Services to add
    
    # Implementation guidance
    implementation_steps: List[ImplementationStep] = field(default_factory=list)
    implementation_effort: ImplementationEffort = ImplementationEffort.MEDIUM
    estimated_time: Optional[str] = None  # e.g., "2-4 hours", "1-2 days"
    
    # Impact estimates
    estimated_score_improvement: float = 0.0  # Expected points gained
    risk_reduction: Optional[str] = None  # e.g., "High", "Medium", "Low"
    business_impact: Optional[str] = None  # Business value description
    
    # Additional context
    aws_documentation_links: List[str] = field(default_factory=list)
    configuration_examples: Dict[str, Any] = field(default_factory=dict)
    best_practices: List[str] = field(default_factory=list)
    
    # Pattern awareness
    pattern_specific: bool = False  # Is this pattern-specific?
    applicable_patterns: List[str] = field(default_factory=list)
    
    # Metadata
    recommendation_type: str = "capability"  # capability, service, pattern, general
    confidence: float = 1.0  # Confidence in this recommendation (0.0-1.0)
    
    def get_priority_score(self) -> int:
        """
        Get numeric priority score for sorting.
        
        Returns:
            Priority score (higher is more urgent)
        """
        priority_scores = {
            RecommendationPriority.CRITICAL: 100,
            RecommendationPriority.HIGH: 75,
            RecommendationPriority.MEDIUM: 50,
            RecommendationPriority.LOW: 25
        }
        return priority_scores.get(self.priority, 50)
    
    def get_effort_score(self) -> int:
        """
        Get numeric effort score for sorting.
        
        Returns:
            Effort score (lower is easier)
        """
        effort_scores = {
            ImplementationEffort.LOW: 1,
            ImplementationEffort.MEDIUM: 2,
            ImplementationEffort.HIGH: 3
        }
        return effort_scores.get(self.implementation_effort, 2)
    
    def get_roi_score(self) -> float:
        """
        Get return on investment score.
        
        Balances score improvement against implementation effort.
        
        Returns:
            ROI score (higher is better value)
        """
        effort_divisor = self.get_effort_score()
        return self.estimated_score_improvement / effort_divisor if effort_divisor > 0 else 0.0
    
    def format_for_report(self) -> str:
        """
        Format recommendation for inclusion in reports.
        
        Returns:
            Formatted string suitable for DOCX reports
        """
        lines = [
            f"### {self.title}",
            "",
            f"**Priority:** {self.priority.value.upper()}",
            f"**Pillar:** {self.pillar.replace('_', ' ').title()}",
            f"**Capability:** {self.capability_addressed.replace('_', ' ').title()}",
            f"**Effort:** {self.implementation_effort.value.title()}",
            f"**Expected Improvement:** +{self.estimated_score_improvement:.1f} points",
            "",
            "**Description:**",
            self.description,
            ""
        ]
        
        if self.affected_services:
            lines.append("**Affected Services:**")
            for service in self.affected_services:
                lines.append(f"  • {service}")
            lines.append("")
        
        if self.implementation_steps:
            lines.append("**Implementation Steps:**")
            for step in self.implementation_steps:
                lines.append(f"{step.step_number}. {step.description}")
                if step.configuration_example:
                    lines.append(f"   Configuration: {step.configuration_example}")
            lines.append("")
        
        if self.best_practices:
            lines.append("**Best Practices:**")
            for practice in self.best_practices:
                lines.append(f"  • {practice}")
            lines.append("")
        
        if self.aws_documentation_links:
            lines.append("**Documentation:**")
            for link in self.aws_documentation_links:
                lines.append(f"  • {link}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pillar": self.pillar,
            "priority": self.priority.value,
            "priority_score": self.get_priority_score(),
            "capability_addressed": self.capability_addressed,
            "affected_services": self.affected_services,
            "missing_services": self.missing_services,
            "implementation_steps": [step.to_dict() for step in self.implementation_steps],
            "implementation_effort": self.implementation_effort.value,
            "effort_score": self.get_effort_score(),
            "estimated_time": self.estimated_time,
            "estimated_score_improvement": round(self.estimated_score_improvement, 2),
            "roi_score": round(self.get_roi_score(), 2),
            "risk_reduction": self.risk_reduction,
            "business_impact": self.business_impact,
            "aws_documentation_links": self.aws_documentation_links,
            "configuration_examples": self.configuration_examples,
            "best_practices": self.best_practices,
            "pattern_specific": self.pattern_specific,
            "applicable_patterns": self.applicable_patterns,
            "recommendation_type": self.recommendation_type,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class RecommendationSet:
    """
    Collection of recommendations with filtering and sorting capabilities.
    
    Provides methods to organize and prioritize recommendations.
    """
    
    recommendations: List[EnhancedRecommendation] = field(default_factory=list)
    
    # Metadata
    generation_timestamp: Optional[str] = None
    total_estimated_improvement: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        self.total_estimated_improvement = sum(
            r.estimated_score_improvement for r in self.recommendations
        )
    
    def filter_by_pillar(self, pillar: str) -> 'RecommendationSet':
        """
        Filter recommendations by pillar.
        
        Args:
            pillar: Pillar name to filter by
            
        Returns:
            New RecommendationSet with filtered recommendations
        """
        filtered = [r for r in self.recommendations if r.pillar == pillar]
        return RecommendationSet(
            recommendations=filtered,
            generation_timestamp=self.generation_timestamp
        )
    
    def filter_by_priority(self, min_priority: RecommendationPriority) -> 'RecommendationSet':
        """
        Filter recommendations by minimum priority.
        
        Args:
            min_priority: Minimum priority level
            
        Returns:
            New RecommendationSet with filtered recommendations
        """
        min_score = min_priority.value
        priority_order = ['low', 'medium', 'high', 'critical']
        min_index = priority_order.index(min_score)
        
        filtered = [
            r for r in self.recommendations
            if priority_order.index(r.priority.value) >= min_index
        ]
        
        return RecommendationSet(
            recommendations=filtered,
            generation_timestamp=self.generation_timestamp
        )
    
    def filter_by_effort(self, max_effort: ImplementationEffort) -> 'RecommendationSet':
        """
        Filter recommendations by maximum effort.
        
        Args:
            max_effort: Maximum effort level
            
        Returns:
            New RecommendationSet with filtered recommendations
        """
        max_score = max_effort.value
        effort_order = ['low', 'medium', 'high']
        max_index = effort_order.index(max_score)
        
        filtered = [
            r for r in self.recommendations
            if effort_order.index(r.implementation_effort.value) <= max_index
        ]
        
        return RecommendationSet(
            recommendations=filtered,
            generation_timestamp=self.generation_timestamp
        )
    
    def sort_by_priority(self, descending: bool = True) -> 'RecommendationSet':
        """
        Sort recommendations by priority.
        
        Args:
            descending: If True, highest priority first
            
        Returns:
            New RecommendationSet with sorted recommendations
        """
        sorted_recs = sorted(
            self.recommendations,
            key=lambda r: r.get_priority_score(),
            reverse=descending
        )
        
        return RecommendationSet(
            recommendations=sorted_recs,
            generation_timestamp=self.generation_timestamp
        )
    
    def sort_by_roi(self, descending: bool = True) -> 'RecommendationSet':
        """
        Sort recommendations by ROI (return on investment).
        
        Args:
            descending: If True, highest ROI first
            
        Returns:
            New RecommendationSet with sorted recommendations
        """
        sorted_recs = sorted(
            self.recommendations,
            key=lambda r: r.get_roi_score(),
            reverse=descending
        )
        
        return RecommendationSet(
            recommendations=sorted_recs,
            generation_timestamp=self.generation_timestamp
        )
    
    def get_quick_wins(self, count: int = 5) -> List[EnhancedRecommendation]:
        """
        Get quick win recommendations (high impact, low effort).
        
        Args:
            count: Number of recommendations to return
            
        Returns:
            List of quick win recommendations
        """
        # Filter to low/medium effort
        low_effort = self.filter_by_effort(ImplementationEffort.MEDIUM)
        
        # Sort by score improvement
        sorted_recs = sorted(
            low_effort.recommendations,
            key=lambda r: r.estimated_score_improvement,
            reverse=True
        )
        
        return sorted_recs[:count]
    
    def get_critical_recommendations(self) -> List[EnhancedRecommendation]:
        """
        Get all critical priority recommendations.
        
        Returns:
            List of critical recommendations
        """
        return [
            r for r in self.recommendations
            if r.priority == RecommendationPriority.CRITICAL
        ]
    
    def get_by_capability(self, capability: str) -> List[EnhancedRecommendation]:
        """
        Get recommendations for a specific capability.
        
        Args:
            capability: Capability name
            
        Returns:
            List of recommendations addressing that capability
        """
        return [
            r for r in self.recommendations
            if r.capability_addressed == capability
        ]
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of recommendations.
        
        Returns:
            Formatted string with recommendation summary
        """
        lines = [
            "=== RECOMMENDATIONS SUMMARY ===",
            f"Total Recommendations: {len(self.recommendations)}",
            f"Total Estimated Improvement: +{self.total_estimated_improvement:.1f} points",
            ""
        ]
        
        # Count by priority
        priority_counts = {}
        for rec in self.recommendations:
            priority_counts[rec.priority.value] = priority_counts.get(rec.priority.value, 0) + 1
        
        lines.append("By Priority:")
        for priority in ['critical', 'high', 'medium', 'low']:
            count = priority_counts.get(priority, 0)
            if count > 0:
                lines.append(f"  • {priority.title()}: {count}")
        
        # Count by pillar
        pillar_counts = {}
        for rec in self.recommendations:
            pillar_counts[rec.pillar] = pillar_counts.get(rec.pillar, 0) + 1
        
        lines.append("")
        lines.append("By Pillar:")
        for pillar, count in sorted(pillar_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  • {pillar.replace('_', ' ').title()}: {count}")
        
        # Quick wins
        quick_wins = self.get_quick_wins(3)
        if quick_wins:
            lines.append("")
            lines.append("Top Quick Wins:")
            for rec in quick_wins:
                lines.append(
                    f"  • {rec.title} "
                    f"(+{rec.estimated_score_improvement:.1f} points, {rec.implementation_effort.value} effort)"
                )
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_recommendations": len(self.recommendations),
            "total_estimated_improvement": round(self.total_estimated_improvement, 2),
            "generation_timestamp": self.generation_timestamp,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "quick_wins": [r.to_dict() for r in self.get_quick_wins(5)],
            "critical_recommendations": [r.to_dict() for r in self.get_critical_recommendations()]
        }
