"""
Executive Summary Generator for WAFR Reports.

This module generates comprehensive executive summaries with key findings,
priority recommendations, and business impact analysis.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from .models import (
    ExecutiveSummary,
    KeyFinding,
    EnhancedRecommendation,
    EnhancedPillarAssessment,
    RiskLevel,
    Priority
)


logger = logging.getLogger(__name__)


class ExecutiveSummaryGenerator:
    """
    Generates executive summaries for WAFR assessment reports.
    
    Creates concise, high-level overviews with key findings, metrics,
    and priority recommendations for executive stakeholders.
    """
    
    def __init__(self):
        """Initialize the executive summary generator."""
        logger.info("✅ Executive summary generator initialized")
    
    def generate_executive_summary(
        self,
        assessment_data: Dict[str, Any]
    ) -> ExecutiveSummary:
        """
        Generate comprehensive executive summary from assessment data.
        
        Args:
            assessment_data: Complete assessment results
            
        Returns:
            ExecutiveSummary object with all key information
        """
        logger.info("📊 Generating executive summary")
        
        # Extract overall metrics
        overall_score = assessment_data.get("overall_score", 0)
        overall_risk_level = self._parse_risk_level(
            assessment_data.get("overall_risk_level", "medium")
        )
        architecture_confidence = assessment_data.get("overall_confidence", 0.5)
        assessment_date = assessment_data.get("timestamp", datetime.now().isoformat())
        
        # Extract architecture overview
        doc_analysis = assessment_data.get("document_analysis", {})
        services_analyzed = len(doc_analysis.get("identified_services", []))
        patterns_detected = doc_analysis.get("architectural_patterns", [])
        architecture_name = doc_analysis.get("architecture_name", "Architecture Assessment")
        
        # Extract pillar data
        pillar_assessments = assessment_data.get("pillar_assessments", {})
        
        # Identify top strengths and weaknesses
        top_strengths = self._identify_top_strengths(pillar_assessments)
        top_weaknesses = self._identify_top_weaknesses(pillar_assessments)
        
        # Identify critical risks
        critical_risks = self._identify_critical_risks(pillar_assessments, overall_score)
        
        # Select top priority actions
        all_recommendations = self._collect_all_recommendations(pillar_assessments)
        top_priority_actions = self._select_top_priority_actions(all_recommendations)
        
        # Calculate effort and impact
        estimated_total_effort = self._estimate_total_effort(top_priority_actions)
        expected_score_improvement = self._calculate_expected_improvement(top_priority_actions)
        
        # Build pillar summary
        pillar_scores = {}
        pillar_risk_levels = {}
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                pillar_scores[pillar_name] = pillar_data.get("score", 0)
                pillar_risk_levels[pillar_name] = pillar_data.get("risk_level", "unknown")
        
        # Create executive summary
        summary = ExecutiveSummary(
            overall_score=overall_score,
            overall_risk_level=overall_risk_level,
            architecture_confidence=architecture_confidence,
            assessment_date=assessment_date,
            services_analyzed=services_analyzed,
            patterns_detected=patterns_detected,
            architecture_name=architecture_name,
            top_strengths=top_strengths,
            top_weaknesses=top_weaknesses,
            critical_risks=critical_risks,
            top_priority_actions=top_priority_actions,
            estimated_total_effort=estimated_total_effort,
            expected_score_improvement=expected_score_improvement,
            pillar_scores=pillar_scores,
            pillar_risk_levels=pillar_risk_levels
        )
        
        logger.info(
            f"✅ Executive summary generated: {len(top_strengths)} strengths, "
            f"{len(top_weaknesses)} weaknesses, {len(top_priority_actions)} priority actions"
        )
        
        return summary
    
    def _identify_top_strengths(
        self,
        pillar_assessments: Dict[str, Any],
        count: int = 3
    ) -> List[KeyFinding]:
        """
        Identify top strengths across all pillars.
        
        Args:
            pillar_assessments: Dictionary of pillar assessment data
            count: Number of top strengths to identify
            
        Returns:
            List of KeyFinding objects representing strengths
        """
        logger.info(f"🔍 Identifying top {count} strengths")
        
        strengths = []
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if not isinstance(pillar_data, dict):
                continue
            
            score = pillar_data.get("score", 0)
            detected_caps = pillar_data.get("detected_capabilities", [])
            
            # High scores are strengths
            if score >= 80:
                finding = KeyFinding(
                    title=f"Strong {pillar_name.replace('_', ' ').title()} Implementation",
                    description=f"Achieved {score:.1f}/100 score with {len(detected_caps)} capabilities implemented",
                    pillar=pillar_name,
                    impact="high",
                    finding_type="strength"
                )
                strengths.append((score, finding))
            
            # Many detected capabilities are strengths
            elif len(detected_caps) >= 5:
                finding = KeyFinding(
                    title=f"Comprehensive {pillar_name.replace('_', ' ').title()} Coverage",
                    description=f"Implemented {len(detected_caps)} key capabilities",
                    pillar=pillar_name,
                    impact="medium",
                    finding_type="strength"
                )
                strengths.append((score, finding))
        
        # Sort by score and return top N
        strengths.sort(key=lambda x: x[0], reverse=True)
        result = [finding for _, finding in strengths[:count]]
        
        logger.info(f"✅ Identified {len(result)} strengths")
        return result
    
    def _identify_top_weaknesses(
        self,
        pillar_assessments: Dict[str, Any],
        count: int = 3
    ) -> List[KeyFinding]:
        """
        Identify top weaknesses across all pillars.
        
        Args:
            pillar_assessments: Dictionary of pillar assessment data
            count: Number of top weaknesses to identify
            
        Returns:
            List of KeyFinding objects representing weaknesses
        """
        logger.info(f"🔍 Identifying top {count} weaknesses")
        
        weaknesses = []
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if not isinstance(pillar_data, dict):
                continue
            
            score = pillar_data.get("score", 0)
            missing_caps = pillar_data.get("missing_capabilities", [])
            
            # Low scores are weaknesses
            if score < 60:
                finding = KeyFinding(
                    title=f"Critical {pillar_name.replace('_', ' ').title()} Gaps",
                    description=f"Score of {score:.1f}/100 indicates significant gaps with {len(missing_caps)} missing capabilities",
                    pillar=pillar_name,
                    impact="high",
                    finding_type="weakness"
                )
                weaknesses.append((100 - score, finding))  # Sort by severity
            
            # Many missing capabilities are weaknesses
            elif len(missing_caps) >= 3:
                finding = KeyFinding(
                    title=f"Incomplete {pillar_name.replace('_', ' ').title()} Implementation",
                    description=f"Missing {len(missing_caps)} important capabilities",
                    pillar=pillar_name,
                    impact="medium",
                    finding_type="weakness"
                )
                weaknesses.append((len(missing_caps) * 10, finding))
        
        # Sort by severity and return top N
        weaknesses.sort(key=lambda x: x[0], reverse=True)
        result = [finding for _, finding in weaknesses[:count]]
        
        logger.info(f"✅ Identified {len(result)} weaknesses")
        return result
    
    def _identify_critical_risks(
        self,
        pillar_assessments: Dict[str, Any],
        overall_score: float
    ) -> List[str]:
        """
        Identify critical risks that require immediate attention.
        
        Args:
            pillar_assessments: Dictionary of pillar assessment data
            overall_score: Overall assessment score
            
        Returns:
            List of critical risk descriptions
        """
        logger.info("🔍 Identifying critical risks")
        
        risks = []
        
        # Overall score risk
        if overall_score < 50:
            risks.append(
                f"Overall architecture score of {overall_score:.1f}/100 indicates "
                "significant risks across multiple pillars requiring immediate attention"
            )
        
        # Pillar-specific risks
        for pillar_name, pillar_data in pillar_assessments.items():
            if not isinstance(pillar_data, dict):
                continue
            
            score = pillar_data.get("score", 0)
            risk_level = pillar_data.get("risk_level", "unknown")
            
            if score < 50 or risk_level in ["critical", "high"]:
                pillar_display = pillar_name.replace("_", " ").title()
                risks.append(
                    f"{pillar_display} pillar shows {risk_level} risk with score of {score:.1f}/100"
                )
        
        # Limit to most critical risks
        result = risks[:5]
        
        logger.info(f"✅ Identified {len(result)} critical risks")
        return result
    
    def _collect_all_recommendations(
        self,
        pillar_assessments: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Collect all recommendations from all pillars.
        
        Args:
            pillar_assessments: Dictionary of pillar assessment data
            
        Returns:
            List of all recommendations
        """
        all_recommendations = []
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                recommendations = pillar_data.get("recommendations", [])
                for rec in recommendations:
                    if isinstance(rec, dict):
                        # Add pillar context if not present
                        if "pillar" not in rec:
                            rec["pillar"] = pillar_name
                        all_recommendations.append(rec)
        
        return all_recommendations
    
    def _select_top_priority_actions(
        self,
        recommendations: List[Dict[str, Any]],
        count: int = 5
    ) -> List[EnhancedRecommendation]:
        """
        Select top priority recommendations for executive summary.
        
        Args:
            recommendations: List of all recommendations
            count: Number of top recommendations to select
            
        Returns:
            List of top priority EnhancedRecommendation objects
        """
        logger.info(f"🔍 Selecting top {count} priority actions")
        
        # Sort by priority and expected impact
        def get_priority_score(rec):
            priority_values = {
                "critical": 100,
                "high": 75,
                "medium": 50,
                "low": 25
            }
            priority = rec.get("priority", "medium")
            priority_score = priority_values.get(priority.lower() if isinstance(priority, str) else "medium", 50)
            
            impact = rec.get("expected_score_improvement", 0)
            
            return priority_score + impact
        
        sorted_recs = sorted(recommendations, key=get_priority_score, reverse=True)
        
        # Convert to EnhancedRecommendation objects
        top_recs = []
        for rec in sorted_recs[:count]:
            if isinstance(rec, EnhancedRecommendation):
                top_recs.append(rec)
            elif isinstance(rec, dict):
                # Create EnhancedRecommendation from dict
                try:
                    enhanced_rec = self._dict_to_enhanced_recommendation(rec)
                    top_recs.append(enhanced_rec)
                except Exception as e:
                    logger.warning(f"⚠️ Could not convert recommendation to EnhancedRecommendation: {e}")
        
        logger.info(f"✅ Selected {len(top_recs)} priority actions")
        return top_recs
    
    def _dict_to_enhanced_recommendation(self, rec_dict: Dict[str, Any]) -> EnhancedRecommendation:
        """Convert dictionary to EnhancedRecommendation object."""
        from .models import Priority, EffortLevel
        
        # Parse priority
        priority_str = rec_dict.get("priority", "medium")
        if isinstance(priority_str, str):
            try:
                priority = Priority(priority_str.lower())
            except ValueError:
                priority = Priority.MEDIUM
        else:
            priority = Priority.MEDIUM
        
        # Parse effort
        effort_str = rec_dict.get("estimated_effort", "medium")
        if isinstance(effort_str, str):
            try:
                effort = EffortLevel(effort_str.lower())
            except ValueError:
                effort = EffortLevel.MEDIUM
        else:
            effort = EffortLevel.MEDIUM
        
        return EnhancedRecommendation(
            id=rec_dict.get("id", "unknown"),
            title=rec_dict.get("title", "Untitled"),
            description=rec_dict.get("description", ""),
            pillar=rec_dict.get("pillar", "unknown"),
            priority=priority,
            capability=rec_dict.get("capability", "unknown"),
            affected_services=rec_dict.get("affected_services", []),
            estimated_effort=effort,
            estimated_time=rec_dict.get("estimated_time", ""),
            expected_score_improvement=rec_dict.get("expected_score_improvement", 0),
            business_impact=rec_dict.get("business_impact", ""),
            gap_size=rec_dict.get("gap_size", 0),
            priority_score=rec_dict.get("priority_score", 0),
            confidence=rec_dict.get("confidence", 1.0)
        )
    
    def _estimate_total_effort(self, recommendations: List[EnhancedRecommendation]) -> str:
        """
        Estimate total effort for implementing recommendations.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            Formatted effort estimate string
        """
        if not recommendations:
            return "No recommendations"
        
        effort_hours = {
            "low": 4,
            "medium": 16,
            "high": 40
        }
        
        total_hours = 0
        for rec in recommendations:
            if isinstance(rec, EnhancedRecommendation):
                effort_key = rec.estimated_effort.value
            elif isinstance(rec, dict):
                effort_key = rec.get("estimated_effort", "medium")
            else:
                effort_key = "medium"
            
            total_hours += effort_hours.get(effort_key, 16)
        
        if total_hours < 40:
            return f"{total_hours} hours (1 week)"
        elif total_hours < 160:
            weeks = total_hours / 40
            return f"{total_hours} hours ({weeks:.1f} weeks)"
        else:
            months = total_hours / 160
            return f"{total_hours} hours ({months:.1f} months)"
    
    def _calculate_expected_improvement(
        self,
        recommendations: List[EnhancedRecommendation]
    ) -> float:
        """
        Calculate expected score improvement from recommendations.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            Total expected score improvement
        """
        total_improvement = 0.0
        
        for rec in recommendations:
            if isinstance(rec, EnhancedRecommendation):
                total_improvement += rec.expected_score_improvement
            elif isinstance(rec, dict):
                total_improvement += rec.get("expected_score_improvement", 0)
        
        return total_improvement
    
    def _parse_risk_level(self, risk_level_str: str) -> RiskLevel:
        """Parse risk level string to RiskLevel enum."""
        try:
            return RiskLevel(risk_level_str.lower())
        except ValueError:
            return RiskLevel.MEDIUM
