"""Scoring data models for WAFR enterprise scoring."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class ScoreComponent:
    """
    Individual component contributing to a pillar score.
    
    Represents a single capability's contribution with full transparency.
    """
    
    name: str  # Capability name
    points: float  # Points contributed to score
    weight: float  # Capability weight (0.0-1.0)
    coverage: float  # Coverage level (0.0-1.0)
    confidence: float  # Detection confidence (0.0-1.0)
    evidence: List[str]  # Services providing this capability
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "points": round(self.points, 2),
            "weight": self.weight,
            "coverage": round(self.coverage, 2),
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence
        }


@dataclass
class ScoreBreakdown:
    """
    Detailed breakdown of how a pillar score was calculated.
    
    Provides complete transparency into scoring logic.
    """
    
    baseline_score: float  # Starting score (30-40)
    capability_points: float  # Total points from capabilities
    complexity_adjustment: float  # Adjustment for architecture complexity
    raw_score: float  # Score before capping
    final_score: float  # Final score after capping
    components: List[ScoreComponent]  # Individual capability contributions
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of score calculation.
        
        Returns:
            Formatted string explaining the score
        """
        lines = [
            f"Score Breakdown:",
            f"  Baseline: {self.baseline_score:.1f} points",
            f"  Capabilities: +{self.capability_points:.1f} points",
            f"  Complexity: {self.complexity_adjustment:+.1f} points",
            f"  Raw Score: {self.raw_score:.1f}",
            f"  Final Score: {self.final_score:.1f}%",
            "",
            "Capability Contributions:"
        ]
        
        for component in sorted(self.components, key=lambda c: c.points, reverse=True):
            lines.append(
                f"  • {component.name}: +{component.points:.1f} points "
                f"({component.coverage:.0%} coverage, {component.confidence:.0%} confidence)"
            )
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "baseline_score": round(self.baseline_score, 2),
            "capability_points": round(self.capability_points, 2),
            "complexity_adjustment": round(self.complexity_adjustment, 2),
            "raw_score": round(self.raw_score, 2),
            "final_score": round(self.final_score, 2),
            "components": [c.to_dict() for c in self.components]
        }


@dataclass
class PillarScore:
    """
    Detailed pillar score with complete transparency.
    
    Represents the score for one of the six WAFR pillars with full
    breakdown of how the score was calculated.
    """
    
    pillar_name: str  # Pillar name (security, reliability, etc.)
    final_score: float  # Final score (0-100)
    baseline_score: float  # Starting baseline score
    capability_contributions: Dict[str, float]  # Capability → points added
    complexity_adjustment: float  # Adjustment for architecture complexity
    confidence_level: float  # Overall confidence in this score (0.0-1.0)
    evidence: List[str]  # What was detected that influenced score
    missing_capabilities: List[str]  # What's missing that would improve score
    
    # Detailed breakdown
    breakdown: Optional[ScoreBreakdown] = None
    
    # Metadata
    calculation_timestamp: Optional[str] = None
    raw_score: float = 0.0  # Score before capping (for transparency)
    
    def get_score_range(self) -> str:
        """
        Get qualitative score range.
        
        Returns:
            String describing score level (Excellent, Good, Fair, Poor)
        """
        if self.final_score >= 80:
            return "Excellent"
        elif self.final_score >= 65:
            return "Good"
        elif self.final_score >= 50:
            return "Fair"
        else:
            return "Poor"
    
    def get_confidence_level_text(self) -> str:
        """
        Get qualitative confidence level.
        
        Returns:
            String describing confidence (High, Medium, Low)
        """
        if self.confidence_level >= 0.8:
            return "High"
        elif self.confidence_level >= 0.6:
            return "Medium"
        else:
            return "Low"
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of pillar score.
        
        Returns:
            Formatted string with score summary
        """
        lines = [
            f"=== {self.pillar_name.upper()} PILLAR ===",
            f"Score: {self.final_score:.1f}% ({self.get_score_range()})",
            f"Confidence: {self.confidence_level:.0%} ({self.get_confidence_level_text()})",
            "",
            f"Baseline: {self.baseline_score:.1f} points",
            f"Capability Contributions: +{sum(self.capability_contributions.values()):.1f} points",
            f"Complexity Adjustment: {self.complexity_adjustment:+.1f} points",
            "",
            "Detected Capabilities:"
        ]
        
        for cap_name, points in sorted(
            self.capability_contributions.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  • {cap_name}: +{points:.1f} points")
        
        if self.missing_capabilities:
            lines.append("")
            lines.append("Missing/Low Coverage Capabilities:")
            for missing in self.missing_capabilities:
                lines.append(f"  • {missing}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "pillar_name": self.pillar_name,
            "final_score": round(self.final_score, 2),
            "score_range": self.get_score_range(),
            "baseline_score": round(self.baseline_score, 2),
            "capability_contributions": {
                k: round(v, 2) for k, v in self.capability_contributions.items()
            },
            "complexity_adjustment": round(self.complexity_adjustment, 2),
            "confidence_level": round(self.confidence_level, 2),
            "confidence_text": self.get_confidence_level_text(),
            "evidence": self.evidence,
            "missing_capabilities": self.missing_capabilities,
            "calculation_timestamp": self.calculation_timestamp
        }
        
        if self.breakdown:
            result["breakdown"] = self.breakdown.to_dict()
        
        return result
    
    def compare_to(self, other: 'PillarScore') -> Dict[str, Any]:
        """
        Compare this score to another score for the same pillar.
        
        Args:
            other: Another PillarScore for the same pillar
            
        Returns:
            Dictionary with comparison details
        """
        if self.pillar_name != other.pillar_name:
            raise ValueError(f"Cannot compare different pillars: {self.pillar_name} vs {other.pillar_name}")
        
        score_diff = self.final_score - other.final_score
        
        return {
            "pillar": self.pillar_name,
            "current_score": round(self.final_score, 2),
            "previous_score": round(other.final_score, 2),
            "difference": round(score_diff, 2),
            "improvement": score_diff > 0,
            "current_range": self.get_score_range(),
            "previous_range": other.get_score_range(),
            "range_changed": self.get_score_range() != other.get_score_range()
        }


@dataclass
class AssessmentScore:
    """
    Complete assessment score across all six pillars.
    
    Aggregates pillar scores and provides overall assessment metrics.
    """
    
    pillar_scores: Dict[str, PillarScore]  # Pillar name → PillarScore
    
    # Overall metrics
    overall_score: float = 0.0
    overall_confidence: float = 0.0
    assessment_timestamp: Optional[str] = None
    
    # Architecture metadata
    total_services: int = 0
    detected_patterns: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate overall metrics."""
        if self.pillar_scores:
            # Calculate overall score as average of pillar scores
            self.overall_score = sum(
                score.final_score for score in self.pillar_scores.values()
            ) / len(self.pillar_scores)
            
            # Calculate overall confidence as average
            # FIX Issue 4: Ensure confidence_level is properly used, with fallback
            confidence_values = []
            for score in self.pillar_scores.values():
                # Use confidence_level if set, otherwise calculate from capability evidence
                if hasattr(score, 'confidence_level') and score.confidence_level > 0:
                    confidence_values.append(score.confidence_level)
                elif hasattr(score, 'capability_contributions') and score.capability_contributions:
                    # Fallback: estimate confidence from capability coverage
                    # More capabilities = higher confidence
                    cap_count = len(score.capability_contributions)
                    estimated_confidence = min(0.95, 0.5 + (cap_count * 0.1))
                    confidence_values.append(estimated_confidence)
                else:
                    # Default confidence based on score
                    if score.final_score >= 80:
                        confidence_values.append(0.85)
                    elif score.final_score >= 60:
                        confidence_values.append(0.7)
                    else:
                        confidence_values.append(0.5)
            
            self.overall_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
    
    def get_overall_range(self) -> str:
        """
        Get qualitative overall score range.
        
        Returns:
            String describing overall score level
        """
        if self.overall_score >= 80:
            return "Excellent"
        elif self.overall_score >= 65:
            return "Good"
        elif self.overall_score >= 50:
            return "Fair"
        else:
            return "Poor"
    
    def get_strongest_pillars(self, count: int = 3) -> List[Tuple[str, float]]:
        """
        Get the strongest performing pillars.
        
        Args:
            count: Number of pillars to return
            
        Returns:
            List of (pillar_name, score) tuples
        """
        sorted_pillars = sorted(
            self.pillar_scores.items(),
            key=lambda x: x[1].final_score,
            reverse=True
        )
        return [(name, score.final_score) for name, score in sorted_pillars[:count]]
    
    def get_weakest_pillars(self, count: int = 3) -> List[Tuple[str, float]]:
        """
        Get the weakest performing pillars.
        
        Args:
            count: Number of pillars to return
            
        Returns:
            List of (pillar_name, score) tuples
        """
        sorted_pillars = sorted(
            self.pillar_scores.items(),
            key=lambda x: x[1].final_score
        )
        return [(name, score.final_score) for name, score in sorted_pillars[:count]]
    
    def get_summary(self) -> str:
        """
        Get human-readable summary of assessment.
        
        Returns:
            Formatted string with assessment summary
        """
        lines = [
            "=== WAFR ASSESSMENT SUMMARY ===",
            f"Overall Score: {self.overall_score:.1f}% ({self.get_overall_range()})",
            f"Overall Confidence: {self.overall_confidence:.0%}",
            f"Services Analyzed: {self.total_services}",
            "",
            "Pillar Scores:"
        ]
        
        for pillar_name in ['security', 'reliability', 'performance', 
                            'cost_optimization', 'operational_excellence', 'sustainability']:
            if pillar_name in self.pillar_scores:
                score = self.pillar_scores[pillar_name]
                lines.append(
                    f"  • {pillar_name.replace('_', ' ').title()}: "
                    f"{score.final_score:.1f}% ({score.get_score_range()})"
                )
        
        lines.append("")
        lines.append("Strongest Areas:")
        for pillar, score in self.get_strongest_pillars(3):
            lines.append(f"  ✓ {pillar.replace('_', ' ').title()}: {score:.1f}%")
        
        lines.append("")
        lines.append("Areas for Improvement:")
        for pillar, score in self.get_weakest_pillars(3):
            lines.append(f"  ⚠ {pillar.replace('_', ' ').title()}: {score:.1f}%")
        
        if self.detected_patterns:
            lines.append("")
            lines.append("Detected Patterns:")
            for pattern in self.detected_patterns:
                lines.append(f"  • {pattern}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_score": round(self.overall_score, 2),
            "overall_range": self.get_overall_range(),
            "overall_confidence": round(self.overall_confidence, 2),
            "assessment_timestamp": self.assessment_timestamp,
            "total_services": self.total_services,
            "detected_patterns": self.detected_patterns,
            "pillar_scores": {
                name: score.to_dict() for name, score in self.pillar_scores.items()
            },
            "strongest_pillars": [
                {"pillar": name, "score": round(score, 2)}
                for name, score in self.get_strongest_pillars(3)
            ],
            "weakest_pillars": [
                {"pillar": name, "score": round(score, 2)}
                for name, score in self.get_weakest_pillars(3)
            ]
        }
