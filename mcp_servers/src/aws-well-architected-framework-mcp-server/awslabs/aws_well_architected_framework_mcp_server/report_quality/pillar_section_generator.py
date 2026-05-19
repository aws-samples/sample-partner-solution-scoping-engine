"""
Pillar Section Generator for WAFR Reports.

This module generates comprehensive pillar sections with detailed analysis,
capability coverage, and recommendations.
"""

import logging
from typing import Dict, List, Any, Optional
from .professional_document_formatter import ProfessionalDocumentFormatter
from .visual_elements_generator import VisualElementsGenerator


logger = logging.getLogger(__name__)


class PillarSectionGenerator:
    """
    Generates comprehensive pillar sections for WAFR reports.
    
    Creates detailed sections for each pillar including score breakdown,
    detected/missing capabilities, risk assessment, and recommendations.
    """
    
    PILLAR_DISPLAY_NAMES = {
        "operational_excellence": "Operational Excellence",
        "security": "Security",
        "reliability": "Reliability",
        "performance_efficiency": "Performance Efficiency",
        "cost_optimization": "Cost Optimization",
        "sustainability": "Sustainability"
    }
    
    PILLAR_DESCRIPTIONS = {
        "operational_excellence": "The ability to run and monitor systems to deliver business value and continually improve supporting processes and procedures.",
        "security": "The ability to protect information, systems, and assets while delivering business value through risk assessments and mitigation strategies.",
        "reliability": "The ability of a system to recover from infrastructure or service disruptions, dynamically acquire computing resources to meet demand, and mitigate disruptions.",
        "performance_efficiency": "The ability to use computing resources efficiently to meet system requirements and maintain that efficiency as demand changes and technologies evolve.",
        "cost_optimization": "The ability to run systems to deliver business value at the lowest price point.",
        "sustainability": "The ability to continually improve sustainability impacts by reducing energy consumption and increasing efficiency across all components of a workload."
    }
    
    def __init__(self, formatter: ProfessionalDocumentFormatter, visual_gen: VisualElementsGenerator):
        """
        Initialize the pillar section generator.
        
        Args:
            formatter: Document formatter instance
            visual_gen: Visual elements generator instance
        """
        self.formatter = formatter
        self.visual_gen = visual_gen
        logger.info("✅ Pillar section generator initialized")
    
    def generate_pillar_section(
        self,
        pillar_name: str,
        pillar_data: Dict[str, Any]
    ):
        """
        Generate comprehensive section for a single pillar.
        
        Args:
            pillar_name: Name of the pillar
            pillar_data: Pillar assessment data
        """
        logger.info(f"📊 Generating section for pillar: {pillar_name}")
        
        display_name = self.PILLAR_DISPLAY_NAMES.get(pillar_name, pillar_name.replace("_", " ").title())
        
        # Add pillar heading
        self.formatter.add_section_heading(display_name, level=1)
        
        # Add pillar description
        description = self.PILLAR_DESCRIPTIONS.get(pillar_name, "")
        if description:
            self.formatter.add_paragraph(description)
            self.formatter.add_paragraph("")  # Spacing
        
        # Add score overview
        self._add_score_overview(pillar_name, pillar_data)
        
        # Add detailed score breakdown
        self._add_score_breakdown(pillar_name, pillar_data)
        
        # Add detected capabilities
        self._add_detected_capabilities(pillar_name, pillar_data)
        
        # Add missing capabilities
        self._add_missing_capabilities(pillar_name, pillar_data)
        
        # Add risk assessment
        self._add_risk_assessment(pillar_name, pillar_data)
        
        # Add capability coverage matrix
        self._add_capability_coverage_matrix(pillar_name, pillar_data)
        
        # Add questions assessed
        self._add_questions_assessed(pillar_name, pillar_data)
        
        # Add AWS documentation links
        self._add_documentation_links(pillar_name, pillar_data)
        
        # Page break after pillar section
        self.formatter.add_page_break()
        
        logger.info(f"✅ Pillar section generated for: {pillar_name}")
    
    def _add_score_overview(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add score overview section."""
        self.formatter.add_section_heading("Score Overview", level=2)
        
        score = pillar_data.get("score", 0)
        risk_level = pillar_data.get("risk_level", "unknown")
        
        # Add score with visual indicator
        score_text = f"Score: {score:.1f}/100 {self.visual_gen._get_score_indicator(score)}"
        self.formatter.add_paragraph(score_text)
        
        # Add risk level with indicator
        risk_text = f"Risk Level: {self.visual_gen.add_risk_indicator(risk_level)}"
        self.formatter.add_paragraph(risk_text)
        
        # Add confidence level if available
        if "confidence_level" in pillar_data:
            confidence = pillar_data["confidence_level"]
            confidence_pct = confidence * 100
            self.formatter.add_paragraph(f"Confidence Level: {confidence_pct:.0f}%")
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_score_breakdown(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add detailed score breakdown section."""
        self.formatter.add_section_heading("Score Breakdown", level=2)
        
        score_breakdown = pillar_data.get("score_breakdown", {})
        
        if isinstance(score_breakdown, dict):
            # Baseline score
            baseline = score_breakdown.get("baseline_score", 0)
            self.formatter.add_paragraph(f"Baseline Score: {baseline:.1f}")
            
            # Capability contributions
            contributions = score_breakdown.get("capability_contributions", {})
            if contributions:
                self.formatter.add_paragraph("Capability Contributions:")
                contrib_items = [
                    f"{cap.replace('_', ' ').title()}: +{score:.1f}"
                    for cap, score in contributions.items()
                ]
                self.formatter.add_bullet_list(contrib_items)
            
            # Adjustments
            adjustments = score_breakdown.get("adjustments", {})
            if adjustments:
                self.formatter.add_paragraph("Adjustments:")
                adj_items = [
                    f"{adj.replace('_', ' ').title()}: {score:+.1f}"
                    for adj, score in adjustments.items()
                ]
                self.formatter.add_bullet_list(adj_items)
            
            # Final score
            final_score = score_breakdown.get("final_score", pillar_data.get("score", 0))
            self.formatter.add_paragraph(f"Final Score: {final_score:.1f}/100")
        else:
            self.formatter.add_paragraph("Score breakdown not available.")
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_detected_capabilities(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add detected capabilities section."""
        self.formatter.add_section_heading("Detected Capabilities", level=2)
        
        detected_caps = pillar_data.get("detected_capabilities", [])
        
        if detected_caps:
            self.formatter.add_paragraph(
                f"The following {len(detected_caps)} capabilities were detected in your architecture:"
            )
            
            for cap in detected_caps:
                if isinstance(cap, dict):
                    cap_name = cap.get("name", "Unknown")
                    status = cap.get("status", "unknown")
                    evidence = cap.get("evidence", [])
                    score_contrib = cap.get("score_contribution", 0)
                    
                    # Capability name with status
                    cap_text = f"{cap_name.replace('_', ' ').title()} - {self.visual_gen._get_status_indicator(status)}"
                    self.formatter.add_paragraph(cap_text)
                    
                    # Evidence
                    if evidence:
                        evidence_text = f"  Evidence: {', '.join(evidence[:3])}"
                        if len(evidence) > 3:
                            evidence_text += f" (+{len(evidence) - 3} more)"
                        self.formatter.add_paragraph(evidence_text)
                    
                    # Score contribution
                    if score_contrib > 0:
                        self.formatter.add_paragraph(f"  Score Contribution: +{score_contrib:.1f}")
                    
                    self.formatter.add_paragraph("")  # Spacing between capabilities
        else:
            self.formatter.add_paragraph("No capabilities detected.")
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_missing_capabilities(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add missing capabilities section."""
        self.formatter.add_section_heading("Missing Capabilities", level=2)
        
        missing_caps = pillar_data.get("missing_capabilities", [])
        
        if missing_caps:
            self.formatter.add_paragraph(
                f"The following {len(missing_caps)} capabilities are expected but not detected:"
            )
            
            for cap in missing_caps:
                if isinstance(cap, dict):
                    cap_name = cap.get("name", "Unknown")
                    importance = cap.get("importance", "medium")
                    why_important = cap.get("why_important", "")
                    example_services = cap.get("example_services", [])
                    score_impact = cap.get("score_impact", 0)
                    
                    # Capability name with importance
                    cap_text = f"{cap_name.replace('_', ' ').title()} - {self.visual_gen._get_importance_indicator(importance)}"
                    self.formatter.add_paragraph(cap_text)
                    
                    # Why important
                    if why_important:
                        self.formatter.add_paragraph(f"  Why Important: {why_important}")
                    
                    # Example services
                    if example_services:
                        services_text = f"  Example Services: {', '.join(example_services[:3])}"
                        self.formatter.add_paragraph(services_text)
                    
                    # Potential impact
                    if score_impact > 0:
                        self.formatter.add_paragraph(f"  Potential Score Improvement: +{score_impact:.1f}")
                    
                    self.formatter.add_paragraph("")  # Spacing between capabilities
        else:
            self.formatter.add_paragraph("No missing capabilities identified. All expected capabilities are present.")
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_risk_assessment(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add risk assessment and implications section."""
        self.formatter.add_section_heading("Risk Assessment", level=2)
        
        score = pillar_data.get("score", 0)
        risk_level = pillar_data.get("risk_level", "unknown")
        
        # Risk level explanation
        risk_explanations = {
            "critical": "CRITICAL risk indicates severe gaps that could lead to system failures, security breaches, or significant business impact. Immediate action is required.",
            "high": "HIGH risk indicates significant gaps that could impact system reliability, security, or performance. Priority attention is needed.",
            "medium": "MEDIUM risk indicates moderate gaps that should be addressed to improve system quality and reduce potential issues.",
            "low": "LOW risk indicates minor gaps or areas for optimization. The system meets most best practices."
        }
        
        explanation = risk_explanations.get(risk_level.lower(), "Risk level assessment not available.")
        self.formatter.add_paragraph(explanation)
        
        # Score-based implications
        if score < 50:
            self.formatter.add_paragraph(
                "⚠️ The low score indicates fundamental gaps in this pillar that require immediate attention. "
                "Multiple critical capabilities are missing or improperly implemented."
            )
        elif score < 70:
            self.formatter.add_paragraph(
                "The moderate score indicates room for improvement. Several important capabilities "
                "are missing or only partially implemented."
            )
        elif score < 85:
            self.formatter.add_paragraph(
                "The good score indicates solid implementation with some areas for enhancement. "
                "Most capabilities are present with a few gaps to address."
            )
        else:
            self.formatter.add_paragraph(
                "The excellent score indicates strong implementation of best practices. "
                "Continue monitoring and maintaining these capabilities."
            )
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_capability_coverage_matrix(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add capability coverage matrix table."""
        self.formatter.add_section_heading("Capability Coverage Matrix", level=2)
        
        # Build capability status dictionary
        capabilities = {}
        
        # Add detected capabilities
        for cap in pillar_data.get("detected_capabilities", []):
            if isinstance(cap, dict):
                cap_name = cap.get("name", "Unknown")
                capabilities[cap_name] = {
                    "status": cap.get("status", "present"),
                    "evidence": cap.get("evidence", []),
                    "score_contribution": cap.get("score_contribution", 0)
                }
        
        # Add missing capabilities
        for cap in pillar_data.get("missing_capabilities", []):
            if isinstance(cap, dict):
                cap_name = cap.get("name", "Unknown")
                if cap_name not in capabilities:
                    capabilities[cap_name] = {
                        "status": "missing",
                        "evidence": [],
                        "score_contribution": 0
                    }
        
        if capabilities:
            # Generate table
            table_data = self.visual_gen.create_capability_matrix_table(pillar_name, capabilities)
            
            # Add table to document
            self.formatter.create_table(
                headers=table_data["headers"],
                rows=table_data["rows"],
                col_widths=table_data.get("col_widths")
            )
        else:
            self.formatter.add_paragraph("No capability data available.")
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_questions_assessed(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add questions assessed section."""
        self.formatter.add_section_heading("Assessment Coverage", level=2)
        
        questions_assessed = pillar_data.get("questions_assessed", 0)
        total_questions = pillar_data.get("total_questions_available", 0)
        coverage_pct = pillar_data.get("question_coverage_percentage", 0)
        
        if total_questions > 0:
            self.formatter.add_paragraph(
                f"Questions Assessed: {questions_assessed} out of {total_questions} available questions"
            )
            self.formatter.add_paragraph(f"Coverage: {coverage_pct:.0f}%")
        else:
            self.formatter.add_paragraph(f"Questions Assessed: {questions_assessed}")
        
        # Coverage explanation
        if coverage_pct >= 80:
            self.formatter.add_paragraph(
                "✅ Excellent coverage - The assessment evaluated most available WAFR questions for this pillar."
            )
        elif coverage_pct >= 50:
            self.formatter.add_paragraph(
                "✓ Good coverage - The assessment evaluated a majority of WAFR questions for this pillar."
            )
        elif coverage_pct > 0:
            self.formatter.add_paragraph(
                "⚠️ Limited coverage - Additional information could improve assessment accuracy."
            )
        else:
            self.formatter.add_paragraph(
                "Assessment based on architecture analysis and capability detection."
            )
        
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_documentation_links(self, pillar_name: str, pillar_data: Dict[str, Any]):
        """Add AWS documentation links section."""
        self.formatter.add_section_heading("AWS Documentation References", level=2)
        
        doc_links = pillar_data.get("pillar_documentation_links", [])
        
        if doc_links:
            self.formatter.add_paragraph("Relevant AWS documentation for this pillar:")
            
            for link in doc_links[:5]:  # Top 5 links
                if isinstance(link, dict):
                    title = link.get("title", "Documentation")
                    url = link.get("url", "")
                    description = link.get("description", "")
                    
                    # Add link with description
                    para = self.formatter.add_paragraph("")
                    self.formatter.add_hyperlink(para, title, url)
                    if description:
                        self.formatter.add_paragraph(f"  {description}")
        else:
            # Add default WAFR documentation link
            display_name = self.PILLAR_DISPLAY_NAMES.get(pillar_name, pillar_name)
            para = self.formatter.add_paragraph("")
            self.formatter.add_hyperlink(
                para,
                f"AWS Well-Architected Framework - {display_name}",
                f"https://docs.aws.amazon.com/wellarchitected/latest/framework/{pillar_name}.html"
            )
        
        self.formatter.add_paragraph("")  # Spacing
