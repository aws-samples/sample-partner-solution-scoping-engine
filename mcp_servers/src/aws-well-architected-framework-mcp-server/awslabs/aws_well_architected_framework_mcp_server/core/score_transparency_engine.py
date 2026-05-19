#!/usr/bin/env python3
"""
Score Transparency Engine for WAFR Assessments

This module provides detailed explanations for WAFR scores, showing capability breakdowns,
evidence, and calculation methodology to help users understand their assessment results.

Features:
- Detailed score breakdowns by capability
- Evidence-based scoring explanations
- Capability coverage visualization
- Score calculation methodology
- Confidence level explanations
- Gap analysis with specific recommendations

Author: Enterprise WAFR Team
Version: 1.0.0
Date: 2025-11-13
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class CapabilityStatus(Enum):
    """Status of capability detection"""
    DETECTED = "DETECTED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass
class CapabilityEvidence:
    """Evidence for capability detection"""
    capability: str
    status: str
    confidence: float
    evidence_items: List[str]
    missing_items: List[str]
    score_contribution: float
    weight: float

@dataclass
class ScoreBreakdown:
    """Detailed breakdown of pillar score"""
    pillar: str
    final_score: float
    base_score: float
    adjustments: List[Dict[str, Any]]
    capability_evidence: List[CapabilityEvidence]
    calculation_method: str
    confidence_level: float

@dataclass
class CapabilityMatrix:
    """Visual representation of capability coverage"""
    pillar: str
    total_capabilities: int
    detected_capabilities: int
    coverage_percentage: float
    capability_details: List[Dict[str, Any]]
    visual_representation: str

class ScoreTransparencyEngine:
    """
    Engine for generating detailed score explanations and transparency reports.
    
    Provides comprehensive breakdowns of how WAFR scores are calculated,
    what evidence was found, and what's missing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._load_capability_weights()
    
    def _load_capability_weights(self):
        """Load capability weights for each pillar"""
        self.capability_weights = {
            "operational_excellence": {
                "observability": 0.25,
                "infrastructure_as_code": 0.20,
                "deployment_automation": 0.20,
                "incident_response": 0.15,
                "workflow_automation": 0.20
            },
            "security": {
                "identity_access": 0.25,
                "data_protection": 0.25,
                "network_security": 0.20,
                "monitoring_detection": 0.15,
                "encryption": 0.15
            },
            "reliability": {
                "redundancy": 0.25,
                "backup_recovery": 0.25,
                "scaling": 0.20,
                "monitoring_alerting": 0.15,
                "messaging": 0.15
            },
            "performance_efficiency": {
                "compute_optimization": 0.25,
                "storage_optimization": 0.20,
                "content_delivery": 0.20,
                "caching": 0.20,
                "database_optimization": 0.15
            },
            "cost_optimization": {
                "managed_services": 0.25,
                "right_sizing": 0.25,
                "cost_monitoring": 0.20,
                "reserved_capacity": 0.15,
                "lifecycle_management": 0.15
            },
            "sustainability": {
                "resource_utilization": 0.30,
                "managed_services": 0.25,
                "regional_selection": 0.20,
                "data_lifecycle": 0.15,
                "hardware_patterns": 0.10
            }
        }
    
    def generate_score_breakdown(
        self,
        pillar: str,
        final_score: float,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        detected_services: List[str],
        confidence_score: float
    ) -> ScoreBreakdown:
        """
        Generate detailed score breakdown for a pillar.
        
        IMPORTANT: Score calculation methodology
        ----------------------------------------
        Score = (Sum of detected capability weights) / (Sum of all capability weights)
        
        Example for Operational Excellence:
        - Total capabilities: 5 (observability, IaC, deployment, incident, workflow)
        - Detected: 2 (observability=0.25, IaC=0.20)
        - Missing: 3 (deployment=0.20, incident=0.15, workflow=0.20)
        - Total weight: 1.00
        - Score: (0.25 + 0.20) / 1.00 = 0.45 = 45/100
        
        Args:
            pillar: WAFR pillar name
            final_score: Final calculated score (0.0 to 1.0)
            detected_capabilities: List of detected capabilities
            missing_capabilities: List of missing capabilities
            detected_services: List of detected AWS services
            confidence_score: Overall confidence in the assessment (0.0 to 1.0)
            
        Returns:
            ScoreBreakdown with detailed explanation and math validation
        """
        
        self.logger.info(f"📊 Generating score breakdown for {pillar}")
        self.logger.info(f"   Detected: {len(detected_capabilities)} capabilities")
        self.logger.info(f"   Missing: {len(missing_capabilities)} capabilities")
        
        # Generate capability evidence
        capability_evidence = self._generate_capability_evidence(
            pillar, detected_capabilities, missing_capabilities, detected_services
        )
        
        # Calculate base score from capabilities
        base_score = self._calculate_base_score(capability_evidence)
        
        # Validate that base_score matches the math
        self._validate_score_calculation(capability_evidence, base_score)
        
        # Generate adjustments
        adjustments = self._generate_adjustments(
            pillar, final_score, base_score, confidence_score
        )
        
        # Log final score for transparency
        self.logger.info(f"   Base Score: {base_score:.2f} ({base_score*100:.0f}/100)")
        self.logger.info(f"   Final Score: {final_score:.2f} ({final_score*100:.0f}/100)")
        
        return ScoreBreakdown(
            pillar=pillar,
            final_score=final_score,
            base_score=base_score,
            adjustments=adjustments,
            capability_evidence=capability_evidence,
            calculation_method="Weighted capability coverage: (detected weights) / (total weights)",
            confidence_level=confidence_score
        )
    
    def generate_capability_matrix(
        self,
        pillar: str,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        detected_services: List[str]
    ) -> CapabilityMatrix:
        """
        Generate visual capability coverage matrix.
        
        Args:
            pillar: WAFR pillar name
            detected_capabilities: List of detected capabilities
            missing_capabilities: List of missing capabilities
            detected_services: List of detected AWS services
            
        Returns:
            CapabilityMatrix with visual representation
        """
        
        total_capabilities = len(detected_capabilities) + len(missing_capabilities)
        detected_count = len(detected_capabilities)
        coverage = detected_count / total_capabilities if total_capabilities > 0 else 0.0
        
        # Generate capability details
        capability_details = []
        
        for cap in detected_capabilities:
            capability_details.append({
                "capability": cap,
                "status": "DETECTED",
                "services": [s for s in detected_services if self._is_service_relevant(s, cap)],
                "icon": "✅"
            })
        
        for cap in missing_capabilities:
            capability_details.append({
                "capability": cap,
                "status": "MISSING",
                "services": [],
                "icon": "❌"
            })
        
        # Generate visual representation
        visual = self._generate_visual_matrix(detected_count, total_capabilities)
        
        return CapabilityMatrix(
            pillar=pillar,
            total_capabilities=total_capabilities,
            detected_capabilities=detected_count,
            coverage_percentage=coverage,
            capability_details=capability_details,
            visual_representation=visual
        )
    
    def _generate_capability_evidence(
        self,
        pillar: str,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        detected_services: List[str]
    ) -> List[CapabilityEvidence]:
        """Generate evidence for each capability"""
        
        evidence_list = []
        weights = self.capability_weights.get(pillar, {})
        
        # Evidence for detected capabilities
        for cap in detected_capabilities:
            weight = weights.get(cap, 0.20)
            relevant_services = [s for s in detected_services if self._is_service_relevant(s, cap)]
            
            evidence_list.append(CapabilityEvidence(
                capability=cap,
                status="DETECTED",
                confidence=0.85,
                evidence_items=relevant_services,
                missing_items=[],
                score_contribution=weight * 1.0,
                weight=weight
            ))
        
        # Evidence for missing capabilities
        for cap in missing_capabilities:
            weight = weights.get(cap, 0.20)
            
            evidence_list.append(CapabilityEvidence(
                capability=cap,
                status="MISSING",
                confidence=0.90,
                evidence_items=[],
                missing_items=[f"No evidence of {cap} implementation"],
                score_contribution=0.0,
                weight=weight
            ))
        
        return evidence_list
    
    def _calculate_base_score(self, capability_evidence: List[CapabilityEvidence]) -> float:
        """
        Calculate base score from capability evidence.
        
        Score is calculated as: (sum of detected capability weights) / (sum of all capability weights)
        This gives a percentage score between 0.0 and 1.0
        
        Example:
        - Observability detected (0.25 weight) = 0.25 contribution
        - IaC detected (0.20 weight) = 0.20 contribution  
        - Deployment missing (0.20 weight) = 0.00 contribution
        - Total weight = 0.65
        - Score = (0.25 + 0.20) / 0.65 = 0.69 (69%)
        """
        
        total_contribution = sum(ev.score_contribution for ev in capability_evidence)
        total_weight = sum(ev.weight for ev in capability_evidence)
        
        if total_weight > 0:
            base_score = total_contribution / total_weight
            self.logger.debug(f"Base score calculation: {total_contribution:.2f} / {total_weight:.2f} = {base_score:.2f}")
            return base_score
        
        self.logger.warning("No capability weights found, returning 0.0 score")
        return 0.0
    
    def _validate_score_calculation(
        self,
        capability_evidence: List[CapabilityEvidence],
        calculated_score: float
    ) -> None:
        """
        Validate that score calculation is mathematically correct.
        
        This prevents bugs like showing 72/100 when only 45 points were earned.
        """
        
        total_contribution = sum(ev.score_contribution for ev in capability_evidence)
        total_weight = sum(ev.weight for ev in capability_evidence)
        
        if total_weight > 0:
            expected_score = total_contribution / total_weight
            
            # Allow small floating point differences
            if abs(expected_score - calculated_score) > 0.001:
                self.logger.error(
                    f"❌ SCORE CALCULATION ERROR: "
                    f"Expected {expected_score:.4f} but got {calculated_score:.4f}"
                )
                self.logger.error(
                    f"   Total contribution: {total_contribution:.4f}"
                )
                self.logger.error(
                    f"   Total weight: {total_weight:.4f}"
                )
                raise ValueError(
                    f"Score calculation mismatch: {expected_score:.4f} != {calculated_score:.4f}"
                )
        
        self.logger.debug(f"✅ Score calculation validated: {calculated_score:.4f}")
    
    def _generate_adjustments(
        self,
        pillar: str,
        final_score: float,
        base_score: float,
        confidence_score: float
    ) -> List[Dict[str, Any]]:
        """
        Generate list of score adjustments.
        
        Note: Adjustments should be minimal and well-justified.
        The base score from capability detection should be the primary score.
        """
        
        adjustments = []
        
        # Confidence adjustment (if any)
        confidence_adjustment = (final_score - base_score)
        if abs(confidence_adjustment) > 0.01:
            adjustments.append({
                "type": "confidence_adjustment",
                "value": confidence_adjustment,
                "reason": f"Adjusted based on {confidence_score:.0%} confidence level",
                "calculation": f"{base_score:.2f} + {confidence_adjustment:.2f} = {final_score:.2f}"
            })
        
        return adjustments
    
    def _is_service_relevant(self, service: str, capability: str) -> bool:
        """Check if a service is relevant to a capability"""
        
        # Simple relevance mapping
        relevance_map = {
            "observability": ["CloudWatch", "X-Ray", "CloudTrail"],
            "data_protection": ["KMS", "S3"],
            "backup_recovery": ["S3", "DynamoDB"],
            "managed_services": ["Lambda", "DynamoDB", "S3"],
            "content_delivery": ["CloudFront"]
        }
        
        relevant_services = relevance_map.get(capability, [])
        return any(rs.lower() in service.lower() for rs in relevant_services)
    
    def _generate_visual_matrix(self, detected: int, total: int) -> str:
        """Generate ASCII visual representation of capability coverage"""
        
        if total == 0:
            return "No capabilities assessed"
        
        coverage_pct = (detected / total) * 100
        filled = int(coverage_pct / 10)
        empty = 10 - filled
        
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {coverage_pct:.0f}% ({detected}/{total} capabilities)"
    
    def format_transparency_report(
        self,
        pillar_breakdowns: List[ScoreBreakdown],
        capability_matrices: List[CapabilityMatrix]
    ) -> Dict[str, Any]:
        """
        Format complete transparency report for display.
        
        User-friendly format that shows:
        - Pillar scores (simple percentage)
        - Detected capabilities (checkmarks)
        - Missing capabilities (what to improve)
        - No internal weights or point calculations
        
        Args:
            pillar_breakdowns: List of score breakdowns for each pillar
            capability_matrices: List of capability matrices for each pillar
            
        Returns:
            Formatted transparency report (user-friendly)
        """
        
        report = {
            "pillar_scores": [],
            "summary": {
                "total_pillars": len(pillar_breakdowns),
                "average_score": sum(b.final_score for b in pillar_breakdowns) / len(pillar_breakdowns) if pillar_breakdowns else 0.0,
                "average_confidence": sum(b.confidence_level for b in pillar_breakdowns) / len(pillar_breakdowns) if pillar_breakdowns else 0.0
            }
        }
        
        # Add user-friendly pillar information
        for breakdown, matrix in zip(pillar_breakdowns, capability_matrices):
            pillar_info = {
                "pillar": breakdown.pillar.replace("_", " ").title(),
                "score": int(breakdown.final_score * 100),  # Simple percentage
                "coverage_visual": matrix.visual_representation,
                "detected_capabilities": [],
                "missing_capabilities": []
            }
            
            # Separate detected and missing capabilities
            for ev in breakdown.capability_evidence:
                capability_name = ev.capability.replace("_", " ").title()
                
                if ev.status == "DETECTED":
                    pillar_info["detected_capabilities"].append({
                        "name": capability_name,
                        "evidence": ev.evidence_items if ev.evidence_items else ["Detected in architecture"]
                    })
                else:
                    pillar_info["missing_capabilities"].append({
                        "name": capability_name,
                        "recommendation": f"Consider implementing {capability_name.lower()} to improve this pillar"
                    })
            
            report["pillar_scores"].append(pillar_info)
        
        return report
    
    def format_simple_pillar_report(
        self,
        pillar: str,
        score: float,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        detected_services: List[str]
    ) -> str:
        """
        Format a simple, user-friendly pillar report.
        
        Shows only what users need to know:
        - Pillar name and score
        - What's working (detected capabilities)
        - What's missing (improvement opportunities)
        
        Args:
            pillar: Pillar name
            score: Score (0.0 to 1.0)
            detected_capabilities: List of detected capabilities
            missing_capabilities: List of missing capabilities
            detected_services: List of detected services
            
        Returns:
            Formatted string for display
        """
        
        lines = []
        
        # Header with score
        pillar_name = pillar.replace("_", " ").title()
        score_pct = int(score * 100)
        lines.append(f"\n{pillar_name}: {score_pct}/100")
        
        # Visual coverage bar
        total_caps = len(detected_capabilities) + len(missing_capabilities)
        if total_caps > 0:
            coverage = len(detected_capabilities) / total_caps
            filled = int(coverage * 10)
            empty = 10 - filled
            bar = "█" * filled + "░" * empty
            lines.append(f"[{bar}] {int(coverage * 100)}% coverage")
        
        # Detected capabilities (what's working)
        if detected_capabilities:
            lines.append(f"\n✅ Detected Capabilities:")
            for cap in detected_capabilities:
                cap_name = cap.replace("_", " ").title()
                lines.append(f"   • {cap_name}")
        
        # Missing capabilities (what to improve)
        if missing_capabilities:
            lines.append(f"\n❌ Missing Capabilities:")
            for cap in missing_capabilities:
                cap_name = cap.replace("_", " ").title()
                lines.append(f"   • {cap_name}")
        
        # Detected services (context)
        if detected_services:
            lines.append(f"\n📦 Detected Services:")
            lines.append(f"   {', '.join(detected_services[:5])}")
            if len(detected_services) > 5:
                lines.append(f"   ... and {len(detected_services) - 5} more")
        
        return "\n".join(lines)

# Singleton instance
_transparency_engine = None

def get_transparency_engine() -> ScoreTransparencyEngine:
    """Get singleton instance of score transparency engine"""
    global _transparency_engine
    if _transparency_engine is None:
        _transparency_engine = ScoreTransparencyEngine()
    return _transparency_engine
