"""
Visual Elements Generator for WAFR Reports.

This module generates visual elements like tables, charts, and formatted
content to enhance report readability and comprehension.
"""

import logging
from typing import Dict, List, Any, Optional
from .models import (
    EnhancedPillarAssessment,
    EnhancedRecommendation,
    CapabilityStatus,
    Priority,
    RiskLevel
)


logger = logging.getLogger(__name__)


class VisualElementsGenerator:
    """
    Generates visual elements for WAFR reports.
    
    Creates formatted tables, score summaries, capability matrices,
    and priority action plans with color coding and visual indicators.
    """
    
    def __init__(self):
        """Initialize the visual elements generator."""
        logger.info("✅ Visual elements generator initialized")
    
    def create_score_summary_table(
        self,
        pillar_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create formatted table with all pillar scores and risk levels.
        
        Args:
            pillar_scores: Dictionary mapping pillar names to score data
            
        Returns:
            Table data structure with headers and rows
        """
        logger.info("📊 Creating score summary table")
        
        headers = ["Pillar", "Score", "Risk Level", "Key Findings"]
        rows = []
        
        pillar_display_names = {
            "operational_excellence": "Operational Excellence",
            "security": "Security",
            "reliability": "Reliability",
            "performance_efficiency": "Performance Efficiency",
            "cost_optimization": "Cost Optimization",
            "sustainability": "Sustainability"
        }
        
        for pillar_key, pillar_data in pillar_scores.items():
            if isinstance(pillar_data, dict):
                score = pillar_data.get("score", 0)
                risk_level = pillar_data.get("risk_level", "unknown")
                
                # Get key findings
                key_findings = []
                if "detected_capabilities" in pillar_data:
                    cap_count = len(pillar_data["detected_capabilities"])
                    key_findings.append(f"{cap_count} capabilities detected")
                
                if "missing_capabilities" in pillar_data:
                    missing_count = len(pillar_data["missing_capabilities"])
                    if missing_count > 0:
                        key_findings.append(f"{missing_count} gaps identified")
                
                findings_text = ", ".join(key_findings) if key_findings else "Assessment complete"
                
                # Format score with indicator
                score_text = f"{score:.1f}/100 {self._get_score_indicator(score)}"
                risk_text = self.add_risk_indicator(risk_level)
                
                rows.append([
                    pillar_display_names.get(pillar_key, pillar_key.replace("_", " ").title()),
                    score_text,
                    risk_text,
                    findings_text
                ])
        
        logger.info(f"✅ Score summary table created with {len(rows)} pillars")
        
        return {
            "headers": headers,
            "rows": rows,
            "col_widths": [2.0, 1.5, 1.5, 2.5]  # Column widths in inches
        }
    
    def create_capability_matrix_table(
        self,
        pillar: str,
        capabilities: Dict[str, CapabilityStatus]
    ) -> Dict[str, Any]:
        """
        Create capability coverage matrix table.
        
        Args:
            pillar: Pillar name
            capabilities: Dictionary of capability statuses
            
        Returns:
            Table data structure with capability coverage
        """
        logger.info(f"📊 Creating capability matrix for {pillar}")
        
        headers = ["Capability", "Status", "Evidence", "Score Contribution"]
        rows = []
        
        for cap_name, cap_status in capabilities.items():
            if isinstance(cap_status, dict):
                status = cap_status.get("status", "unknown")
                evidence = cap_status.get("evidence", [])
                score_contrib = cap_status.get("score_contribution", 0)
                
                # Format status with indicator
                status_text = self._get_status_indicator(status)
                
                # Format evidence
                evidence_text = ", ".join(evidence[:3]) if evidence else "None"
                if len(evidence) > 3:
                    evidence_text += f" (+{len(evidence) - 3} more)"
                
                # Format score contribution
                contrib_text = f"+{score_contrib:.1f}" if score_contrib > 0 else "0.0"
                
                rows.append([
                    cap_name.replace("_", " ").title(),
                    status_text,
                    evidence_text,
                    contrib_text
                ])
            elif isinstance(cap_status, CapabilityStatus):
                status_text = self._get_status_indicator(cap_status.status)
                evidence_text = ", ".join(cap_status.evidence[:3]) if cap_status.evidence else "None"
                if len(cap_status.evidence) > 3:
                    evidence_text += f" (+{len(cap_status.evidence) - 3} more)"
                contrib_text = f"+{cap_status.score_contribution:.1f}" if cap_status.score_contribution > 0 else "0.0"
                
                rows.append([
                    cap_status.name.replace("_", " ").title(),
                    status_text,
                    evidence_text,
                    contrib_text
                ])
        
        logger.info(f"✅ Capability matrix created with {len(rows)} capabilities")
        
        return {
            "headers": headers,
            "rows": rows,
            "col_widths": [2.0, 1.2, 2.5, 1.3]
        }
    
    def create_priority_action_table(
        self,
        recommendations: List[EnhancedRecommendation]
    ) -> Dict[str, Any]:
        """
        Create prioritized action plan table.
        
        Args:
            recommendations: List of enhanced recommendations
            
        Returns:
            Table data structure with priority actions
        """
        logger.info("📊 Creating priority action table")
        
        headers = ["Priority", "Recommendation", "Effort", "Impact", "Affected Services"]
        rows = []
        
        # Sort recommendations by priority
        sorted_recs = sorted(
            recommendations,
            key=lambda r: r.get_priority_numeric() if hasattr(r, 'get_priority_numeric') 
                         else self._get_priority_value(r.get("priority", "medium")),
            reverse=True
        )
        
        for rec in sorted_recs[:15]:  # Top 15 recommendations
            if isinstance(rec, dict):
                priority = rec.get("priority", "medium")
                title = rec.get("title", "Untitled")
                effort = rec.get("estimated_effort", "medium")
                impact = rec.get("expected_score_improvement", 0)
                services = rec.get("affected_services", [])
                
                priority_text = self.add_priority_badge(priority)
                effort_text = effort.upper() if isinstance(effort, str) else "MEDIUM"
                impact_text = f"+{impact:.1f}" if impact > 0 else "TBD"
                services_text = ", ".join(services[:3]) if services else "Multiple"
                if len(services) > 3:
                    services_text += f" (+{len(services) - 3})"
                
                rows.append([
                    priority_text,
                    title[:60] + "..." if len(title) > 60 else title,
                    effort_text,
                    impact_text,
                    services_text
                ])
            elif isinstance(rec, EnhancedRecommendation):
                priority_text = self.add_priority_badge(rec.priority.value)
                effort_text = rec.estimated_effort.value.upper()
                impact_text = f"+{rec.expected_score_improvement:.1f}" if rec.expected_score_improvement > 0 else "TBD"
                services_text = ", ".join(rec.affected_services[:3]) if rec.affected_services else "Multiple"
                if len(rec.affected_services) > 3:
                    services_text += f" (+{len(rec.affected_services) - 3})"
                
                title = rec.title[:60] + "..." if len(rec.title) > 60 else rec.title
                
                rows.append([
                    priority_text,
                    title,
                    effort_text,
                    impact_text,
                    services_text
                ])
        
        logger.info(f"✅ Priority action table created with {len(rows)} recommendations")
        
        return {
            "headers": headers,
            "rows": rows,
            "col_widths": [1.3, 2.5, 0.8, 0.8, 1.6]
        }
    
    def create_missing_capabilities_table(
        self,
        missing_capabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create table of missing capabilities with importance.
        
        Args:
            missing_capabilities: List of missing capability data
            
        Returns:
            Table data structure
        """
        logger.info("📊 Creating missing capabilities table")
        
        headers = ["Capability", "Importance", "Potential Impact", "Example Services"]
        rows = []
        
        for cap in missing_capabilities[:10]:  # Top 10 missing capabilities
            name = cap.get("name", "Unknown")
            importance = cap.get("importance", "medium")
            impact = cap.get("score_impact", 0)
            services = cap.get("example_services", [])
            
            importance_text = self._get_importance_indicator(importance)
            impact_text = f"+{impact:.1f}" if impact > 0 else "TBD"
            services_text = ", ".join(services[:2]) if services else "Various"
            
            rows.append([
                name.replace("_", " ").title(),
                importance_text,
                impact_text,
                services_text
            ])
        
        logger.info(f"✅ Missing capabilities table created with {len(rows)} items")
        
        return {
            "headers": headers,
            "rows": rows,
            "col_widths": [2.0, 1.2, 1.3, 2.5]
        }
    
    def create_questions_assessed_summary(
        self,
        pillar_assessments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create summary of questions assessed per pillar.
        
        Args:
            pillar_assessments: Dictionary of pillar assessment data
            
        Returns:
            Table data structure
        """
        logger.info("📊 Creating questions assessed summary")
        
        headers = ["Pillar", "Questions Assessed", "Coverage", "Confidence"]
        rows = []
        
        pillar_display_names = {
            "operational_excellence": "Operational Excellence",
            "security": "Security",
            "reliability": "Reliability",
            "performance_efficiency": "Performance Efficiency",
            "cost_optimization": "Cost Optimization",
            "sustainability": "Sustainability"
        }
        
        for pillar_key, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                questions = pillar_data.get("questions_assessed", 0)
                total = pillar_data.get("total_questions_available", 0)
                coverage = pillar_data.get("question_coverage_percentage", 0)
                confidence = pillar_data.get("confidence_level", 0)
                
                coverage_text = f"{coverage:.0f}%" if coverage > 0 else "N/A"
                confidence_text = f"{confidence * 100:.0f}%" if confidence > 0 else "N/A"
                questions_text = f"{questions}" if total == 0 else f"{questions}/{total}"
                
                rows.append([
                    pillar_display_names.get(pillar_key, pillar_key.replace("_", " ").title()),
                    questions_text,
                    coverage_text,
                    confidence_text
                ])
        
        logger.info(f"✅ Questions assessed summary created with {len(rows)} pillars")
        
        return {
            "headers": headers,
            "rows": rows,
            "col_widths": [2.5, 1.5, 1.0, 1.0]
        }
    
    def add_risk_indicator(self, risk_level: str) -> str:
        """
        Get text indicator for risk level with color coding.
        
        Args:
            risk_level: Risk level (critical, high, medium, low)
            
        Returns:
            Formatted risk indicator text
        """
        risk_indicators = {
            "critical": "🔴 CRITICAL",
            "high": "🔴 HIGH",
            "medium": "🟡 MEDIUM",
            "low": "🟢 LOW"
        }
        return risk_indicators.get(risk_level.lower(), "⚪ UNKNOWN")
    
    def add_priority_badge(self, priority: str) -> str:
        """
        Get text badge for priority level.
        
        Args:
            priority: Priority level (critical, high, medium, low)
            
        Returns:
            Formatted priority badge text
        """
        priority_badges = {
            "critical": "🔴 CRITICAL",
            "high": "🟠 HIGH",
            "medium": "🟡 MEDIUM",
            "low": "🟢 LOW"
        }
        return priority_badges.get(priority.lower(), "⚪ NORMAL")
    
    def _get_score_indicator(self, score: float) -> str:
        """Get visual indicator for score value."""
        if score >= 80:
            return "🟢"
        elif score >= 60:
            return "🟡"
        else:
            return "🔴"
    
    def _get_status_indicator(self, status: str) -> str:
        """Get visual indicator for capability status."""
        status_indicators = {
            "present": "✅ Present",
            "partial": "🟡 Partial",
            "missing": "❌ Missing"
        }
        return status_indicators.get(status.lower(), "⚪ Unknown")
    
    def _get_importance_indicator(self, importance: str) -> str:
        """Get visual indicator for importance level."""
        importance_indicators = {
            "critical": "🔴 Critical",
            "high": "🟠 High",
            "medium": "🟡 Medium",
            "low": "🟢 Low"
        }
        return importance_indicators.get(importance.lower(), "⚪ Normal")
    
    def _get_priority_value(self, priority: str) -> int:
        """Get numeric value for priority sorting."""
        priority_values = {
            "critical": 100,
            "high": 75,
            "medium": 50,
            "low": 25
        }
        return priority_values.get(priority.lower(), 50)
    
    def format_percentage(self, value: float) -> str:
        """
        Format a percentage value.
        
        Args:
            value: Percentage value (0-100)
            
        Returns:
            Formatted percentage string
        """
        return f"{value:.1f}%"
    
    def format_score(self, score: float) -> str:
        """
        Format a score value.
        
        Args:
            score: Score value (0-100)
            
        Returns:
            Formatted score string
        """
        return f"{score:.1f}/100"
