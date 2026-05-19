"""
Evidence-Based Scoring Explainer for WAFR Report Content Improvement.

This module provides transparent breakdown of how WAFR pillar scores were calculated,
showing detected vs missing capabilities, evidence for each capability, and score
improvement potential.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from .logger import WAFRLogger


@dataclass
class CapabilityScore:
    """Represents scoring details for a single capability."""
    
    capability: str
    points_earned: float
    points_possible: float
    coverage: str  # e.g., "80%"
    status: str  # "Detected", "Partial", or "Missing"
    evidence: str
    gap: str
    improvement_potential: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "capability": self.capability,
            "points_earned": self.points_earned,
            "points_possible": self.points_possible,
            "coverage": self.coverage,
            "status": self.status,
            "evidence": self.evidence,
            "gap": self.gap,
            "improvement_potential": self.improvement_potential
        }


@dataclass
class ScoreBreakdown:
    """Represents complete score breakdown for a pillar."""
    
    baseline_score: float
    capability_scores: List[CapabilityScore]
    total_points_earned: float
    total_points_possible: float
    improvement_potential: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "baseline_score": self.baseline_score,
            "capability_scores": [cs.to_dict() for cs in self.capability_scores],
            "total_points_earned": self.total_points_earned,
            "total_points_possible": self.total_points_possible,
            "improvement_potential": self.improvement_potential
        }


class EvidenceBasedScoringExplainer:
    """
    Provides transparent, evidence-based explanations of WAFR pillar scores.
    
    This explainer breaks down scores into baseline + capability contributions,
    shows detected vs missing capabilities with evidence, and calculates
    improvement potential for each capability.
    """
    
    def __init__(self):
        """Initialize the EvidenceBasedScoringExplainer."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("EvidenceBasedScoringExplainer initialized")

    
    def explain_score(
        self,
        pillar_score: float,
        detected_capabilities: List[Dict[str, Any]],
        missing_capabilities: List[str],
        pillar: str
    ) -> ScoreBreakdown:
        """
        Generate detailed score breakdown with evidence and improvement potential.
        
        Args:
            pillar_score: Final score for the pillar (0-100)
            detected_capabilities: List of detected capabilities with coverage and evidence
            missing_capabilities: List of missing capability names
            pillar: WAFR pillar name
            
        Returns:
            ScoreBreakdown object with complete score explanation
        """
        self.logger.info(
            f"Explaining {pillar} pillar score: {pillar_score:.2f} with "
            f"{len(detected_capabilities)} detected and {len(missing_capabilities)} missing capabilities"
        )
        
        # Calculate baseline score (minimum score for having any architecture)
        baseline_score = 50.0
        
        # Create capability scores for detected capabilities
        capability_scores = []
        total_points_earned = baseline_score
        
        # Process detected capabilities
        for cap in detected_capabilities:
            capability_name = cap.get("name", "unknown")
            coverage = cap.get("coverage", 0.0)
            evidence_list = cap.get("evidence", [])
            
            # Calculate points for this capability
            # Each capability can contribute up to a certain amount based on pillar
            max_points = self._get_max_points_for_capability(capability_name, pillar)
            points_earned = max_points * coverage
            
            # Determine status based on coverage
            if coverage >= 0.80:
                status = "Detected"
            elif coverage >= 0.40:
                status = "Partial"
            else:
                status = "Missing"
            
            # Format evidence
            evidence_text = "; ".join(evidence_list) if evidence_list else "No specific evidence"
            
            # Identify gap
            if coverage < 1.0:
                gap = f"{int((1.0 - coverage) * 100)}% coverage gap"
            else:
                gap = "None"
            
            # Calculate improvement potential
            improvement_potential = max_points * (1.0 - coverage)
            
            capability_score = CapabilityScore(
                capability=capability_name.replace("_", " ").title(),
                points_earned=points_earned,
                points_possible=max_points,
                coverage=f"{int(coverage * 100)}%",
                status=status,
                evidence=evidence_text,
                gap=gap,
                improvement_potential=improvement_potential
            )
            
            capability_scores.append(capability_score)
            total_points_earned += points_earned
        
        # Process missing capabilities
        for cap_name in missing_capabilities:
            max_points = self._get_max_points_for_capability(cap_name, pillar)
            
            capability_score = CapabilityScore(
                capability=cap_name.replace("_", " ").title(),
                points_earned=0.0,
                points_possible=max_points,
                coverage="0%",
                status="Missing",
                evidence="Not detected in architecture",
                gap="Complete capability gap",
                improvement_potential=max_points
            )
            
            capability_scores.append(capability_score)
        
        # Calculate total improvement potential
        total_improvement = sum(cs.improvement_potential for cs in capability_scores)
        
        # Adjust total_points_earned to match pillar_score if needed
        # (accounting for rounding and scoring algorithm differences)
        if abs(total_points_earned - pillar_score) > 5.0:
            self.logger.warning(
                f"Score mismatch: calculated {total_points_earned:.2f} vs actual {pillar_score:.2f}"
            )
            total_points_earned = pillar_score
        
        score_breakdown = ScoreBreakdown(
            baseline_score=baseline_score,
            capability_scores=capability_scores,
            total_points_earned=total_points_earned,
            total_points_possible=100.0,
            improvement_potential=total_improvement
        )
        
        self.logger.info(
            f"Score breakdown complete: {len(capability_scores)} capabilities analyzed, "
            f"{total_improvement:.2f} points improvement potential"
        )
        
        return score_breakdown
    
    def create_capability_matrix(
        self,
        detected_capabilities: List[Dict[str, Any]],
        missing_capabilities: List[str]
    ) -> Dict[str, Any]:
        """
        Create visual capability coverage matrix.
        
        Args:
            detected_capabilities: List of detected capabilities with coverage
            missing_capabilities: List of missing capability names
            
        Returns:
            Dictionary with categorized capabilities and visual indicators
        """
        self.logger.info(
            f"Creating capability matrix: {len(detected_capabilities)} detected, "
            f"{len(missing_capabilities)} missing"
        )
        
        matrix = {
            "detected": [],  # >80% coverage
            "partial": [],   # 40-80% coverage
            "missing": []    # <40% coverage
        }
        
        # Process detected capabilities
        for cap in detected_capabilities:
            capability_name = cap.get("name", "unknown")
            coverage = cap.get("coverage", 0.0)
            evidence_list = cap.get("evidence", [])
            
            # Format capability entry
            coverage_pct = int(coverage * 100)
            services = self._extract_services_from_evidence(evidence_list)
            services_text = f" ({', '.join(services)})" if services else ""
            
            entry = {
                "name": capability_name.replace("_", " ").title(),
                "coverage": f"{coverage_pct}%",
                "indicator": self._get_indicator(coverage),
                "services": services,
                "display": f"{capability_name.replace('_', ' ').title()}: {coverage_pct}%{services_text}"
            }
            
            # Categorize by coverage
            if coverage >= 0.80:
                matrix["detected"].append(entry)
            elif coverage >= 0.40:
                matrix["partial"].append(entry)
            else:
                matrix["missing"].append(entry)
        
        # Process missing capabilities
        for cap_name in missing_capabilities:
            entry = {
                "name": cap_name.replace("_", " ").title(),
                "coverage": "0%",
                "indicator": "❌",
                "services": [],
                "display": f"{cap_name.replace('_', ' ').title()}: 0%"
            }
            matrix["missing"].append(entry)
        
        # Add summary statistics
        total_capabilities = len(detected_capabilities) + len(missing_capabilities)
        matrix["summary"] = {
            "total_capabilities": total_capabilities,
            "detected_count": len(matrix["detected"]),
            "partial_count": len(matrix["partial"]),
            "missing_count": len(matrix["missing"]),
            "overall_coverage": self._calculate_overall_coverage(detected_capabilities, missing_capabilities)
        }
        
        self.logger.info(
            f"Capability matrix created: {matrix['summary']['detected_count']} detected, "
            f"{matrix['summary']['partial_count']} partial, {matrix['summary']['missing_count']} missing"
        )
        
        return matrix
    
    def calculate_improvement_potential(
        self,
        missing_capabilities: List[str],
        partial_capabilities: List[Dict[str, Any]],
        pillar: str
    ) -> List[Dict[str, Any]]:
        """
        Calculate score improvement potential for missing/partial capabilities.
        
        Args:
            missing_capabilities: List of missing capability names
            partial_capabilities: List of partial capabilities with current coverage
            pillar: WAFR pillar name
            
        Returns:
            Sorted list of improvement opportunities by impact
        """
        self.logger.info(
            f"Calculating improvement potential for {pillar}: "
            f"{len(missing_capabilities)} missing, {len(partial_capabilities)} partial"
        )
        
        opportunities = []
        
        # Process missing capabilities (full improvement potential)
        for cap_name in missing_capabilities:
            max_points = self._get_max_points_for_capability(cap_name, pillar)
            effort = self._estimate_capability_effort(cap_name)
            
            opportunity = {
                "capability": cap_name.replace("_", " ").title(),
                "current_coverage": "0%",
                "target_coverage": "100%",
                "score_gain": max_points,
                "effort_hours": effort,
                "impact_per_hour": max_points / effort if effort > 0 else 0,
                "priority": self._calculate_priority(max_points, effort),
                "status": "Missing"
            }
            opportunities.append(opportunity)
        
        # Process partial capabilities (remaining improvement potential)
        for cap in partial_capabilities:
            capability_name = cap.get("name", "unknown")
            coverage = cap.get("coverage", 0.0)
            
            max_points = self._get_max_points_for_capability(capability_name, pillar)
            remaining_points = max_points * (1.0 - coverage)
            effort = self._estimate_capability_effort(capability_name) * (1.0 - coverage)
            
            opportunity = {
                "capability": capability_name.replace("_", " ").title(),
                "current_coverage": f"{int(coverage * 100)}%",
                "target_coverage": "100%",
                "score_gain": remaining_points,
                "effort_hours": effort,
                "impact_per_hour": remaining_points / effort if effort > 0 else 0,
                "priority": self._calculate_priority(remaining_points, effort),
                "status": "Partial"
            }
            opportunities.append(opportunity)
        
        # Sort by priority (high to low), then by impact per hour
        opportunities.sort(key=lambda x: (-x["priority"], -x["impact_per_hour"]))
        
        self.logger.info(
            f"Identified {len(opportunities)} improvement opportunities, "
            f"total potential: {sum(o['score_gain'] for o in opportunities):.2f} points"
        )
        
        return opportunities
    
    # Helper methods
    
    def _get_max_points_for_capability(self, capability: str, pillar: str) -> float:
        """Get maximum points a capability can contribute to a pillar score."""
        # Capability weights by pillar (normalized to sum to ~50 points available)
        capability_weights = {
            "operational_excellence": {
                "monitoring": 12.0,
                "logging": 10.0,
                "automation": 8.0,
                "incident_response": 10.0,
                "change_management": 10.0
            },
            "security": {
                "encryption": 15.0,
                "identity_access": 15.0,
                "network_security": 10.0,
                "data_protection": 10.0,
                "monitoring_detection": 10.0
            },
            "reliability": {
                "backup_recovery": 12.0,
                "fault_tolerance": 12.0,
                "monitoring": 10.0,
                "auto_scaling": 8.0,
                "disaster_recovery": 8.0
            },
            "performance_efficiency": {
                "caching": 10.0,
                "auto_scaling": 12.0,
                "monitoring": 10.0,
                "optimization": 10.0,
                "architecture_selection": 8.0
            },
            "cost_optimization": {
                "right_sizing": 12.0,
                "reserved_capacity": 10.0,
                "monitoring": 10.0,
                "lifecycle_policies": 8.0,
                "cost_allocation": 10.0
            },
            "sustainability": {
                "resource_efficiency": 12.0,
                "managed_services": 10.0,
                "optimization": 10.0,
                "lifecycle_policies": 8.0,
                "monitoring": 10.0
            }
        }
        
        pillar_key = pillar.lower().replace(" ", "_")
        pillar_weights = capability_weights.get(pillar_key, {})
        
        # Find matching capability (partial match)
        for cap_key, weight in pillar_weights.items():
            if cap_key in capability.lower() or capability.lower() in cap_key:
                return weight
        
        # Default weight for unknown capabilities
        return 5.0
    
    def _get_indicator(self, coverage: float) -> str:
        """Get visual indicator for coverage level."""
        if coverage >= 0.80:
            return "✅"
        elif coverage >= 0.40:
            return "⚠️"
        else:
            return "❌"
    
    def _extract_services_from_evidence(self, evidence_list: List[str]) -> List[str]:
        """Extract service names from evidence strings."""
        services = []
        service_keywords = [
            "Lambda", "DynamoDB", "S3", "API Gateway", "CloudWatch",
            "SNS", "SQS", "Step Functions", "CloudFront", "VPC",
            "WAF", "KMS", "IAM", "X-Ray", "ECS", "EKS", "RDS"
        ]
        
        for evidence in evidence_list:
            for service in service_keywords:
                if service.lower() in evidence.lower():
                    if service not in services:
                        services.append(service)
        
        return services
    
    def _calculate_overall_coverage(
        self,
        detected_capabilities: List[Dict[str, Any]],
        missing_capabilities: List[str]
    ) -> str:
        """Calculate overall capability coverage percentage."""
        if not detected_capabilities and not missing_capabilities:
            return "0%"
        
        total_capabilities = len(detected_capabilities) + len(missing_capabilities)
        
        # Calculate weighted coverage
        total_coverage = sum(cap.get("coverage", 0.0) for cap in detected_capabilities)
        overall_coverage = (total_coverage / total_capabilities) * 100 if total_capabilities > 0 else 0
        
        return f"{int(overall_coverage)}%"
    
    def _estimate_capability_effort(self, capability: str) -> float:
        """Estimate effort in hours to implement a capability."""
        effort_estimates = {
            "encryption": 2.0,
            "backup": 1.0,
            "monitoring": 4.0,
            "logging": 3.0,
            "waf": 8.0,
            "vpc": 16.0,
            "identity_access": 4.0,
            "network_security": 12.0,
            "fault_tolerance": 8.0,
            "auto_scaling": 4.0,
            "caching": 6.0,
            "right_sizing": 8.0,
            "automation": 12.0,
            "incident_response": 16.0
        }
        
        # Find matching capability
        for key, effort in effort_estimates.items():
            if key in capability.lower():
                return effort
        
        # Default effort
        return 8.0
    
    def _calculate_priority(self, score_gain: float, effort: float) -> int:
        """
        Calculate priority level (1-5, 5 being highest).
        
        Based on impact per hour ratio:
        - >2.0: Priority 5 (Critical - Quick wins)
        - 1.0-2.0: Priority 4 (High)
        - 0.5-1.0: Priority 3 (Medium)
        - 0.2-0.5: Priority 2 (Low)
        - <0.2: Priority 1 (Very Low)
        """
        if effort == 0:
            return 5
        
        impact_per_hour = score_gain / effort
        
        if impact_per_hour >= 2.0:
            return 5
        elif impact_per_hour >= 1.0:
            return 4
        elif impact_per_hour >= 0.5:
            return 3
        elif impact_per_hour >= 0.2:
            return 2
        else:
            return 1
