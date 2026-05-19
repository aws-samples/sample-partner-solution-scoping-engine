"""
Recommendations Section Generator for WAFR Reports.

This module generates formatted recommendations sections with implementation
guidance, affected services, and AWS documentation links.
"""

import logging
from typing import Dict, List, Any, Optional
from .professional_document_formatter import ProfessionalDocumentFormatter
from .visual_elements_generator import VisualElementsGenerator
from .models import EnhancedRecommendation, Priority


logger = logging.getLogger(__name__)


class RecommendationsSectionGenerator:
    """
    Generates formatted recommendations sections for WAFR reports.
    
    Creates properly structured recommendation content with implementation
    guidance, service targeting, and documentation links - no raw dictionaries.
    """
    
    def __init__(self, formatter: ProfessionalDocumentFormatter, visual_gen: VisualElementsGenerator):
        """
        Initialize the recommendations section generator.
        
        Args:
            formatter: Document formatter instance
            visual_gen: Visual elements generator instance
        """
        self.formatter = formatter
        self.visual_gen = visual_gen
        logger.info("✅ Recommendations section generator initialized")
    
    def generate_recommendations_section(
        self,
        all_recommendations: List[Any],
        group_by_priority: bool = True
    ):
        """
        Generate comprehensive recommendations section.
        
        Args:
            all_recommendations: List of all recommendations from all pillars
            group_by_priority: Whether to group recommendations by priority level
        """
        logger.info(f"📊 Generating recommendations section with {len(all_recommendations)} recommendations")
        
        # Add section heading
        self.formatter.add_section_heading("Recommendations", level=1)
        
        # Add introduction
        self.formatter.add_paragraph(
            "The following recommendations are prioritized actions to improve your architecture's "
            "alignment with AWS Well-Architected Framework best practices. Each recommendation "
            "includes implementation guidance, affected services, and expected impact."
        )
        self.formatter.add_paragraph("")  # Spacing
        
        if group_by_priority:
            self._generate_grouped_recommendations(all_recommendations)
        else:
            self._generate_sequential_recommendations(all_recommendations)
        
        logger.info("✅ Recommendations section generated")
    
    def _generate_grouped_recommendations(self, recommendations: List[Any]):
        """Generate recommendations grouped by priority level."""
        # Group recommendations by priority
        priority_groups = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for rec in recommendations:
            priority = self._get_recommendation_priority(rec)
            if priority in priority_groups:
                priority_groups[priority].append(rec)
        
        # Generate each priority group
        priority_order = ["critical", "high", "medium", "low"]
        priority_labels = {
            "critical": "Critical Priority Recommendations",
            "high": "High Priority Recommendations",
            "medium": "Medium Priority Recommendations",
            "low": "Low Priority Recommendations"
        }
        
        for priority in priority_order:
            recs = priority_groups[priority]
            if recs:
                # Add priority group heading
                self.formatter.add_section_heading(priority_labels[priority], level=2)
                self.formatter.add_paragraph(
                    f"{len(recs)} recommendation(s) in this priority level:"
                )
                self.formatter.add_paragraph("")  # Spacing
                
                # Generate each recommendation
                for idx, rec in enumerate(recs, 1):
                    self._generate_single_recommendation(rec, f"{priority.upper()}-{idx}")
    
    def _generate_sequential_recommendations(self, recommendations: List[Any]):
        """Generate recommendations in sequential order."""
        # Sort by priority
        sorted_recs = sorted(
            recommendations,
            key=lambda r: self._get_priority_numeric(self._get_recommendation_priority(r)),
            reverse=True
        )
        
        for idx, rec in enumerate(sorted_recs, 1):
            self._generate_single_recommendation(rec, f"REC-{idx}")
    
    def _generate_single_recommendation(self, recommendation: Any, rec_id: str):
        """
        Generate formatted content for a single recommendation.
        
        Args:
            recommendation: Recommendation data (dict or EnhancedRecommendation)
            rec_id: Recommendation identifier for display
        """
        # Extract recommendation data
        if isinstance(recommendation, EnhancedRecommendation):
            title = recommendation.title
            priority = recommendation.priority.value
            description = recommendation.description
            pillar = recommendation.pillar
            affected_services = recommendation.affected_services
            implementation_guidance = recommendation.implementation_guidance
            aws_docs = recommendation.aws_documentation_links
            effort = recommendation.estimated_effort.value
            estimated_time = recommendation.estimated_time
            expected_improvement = recommendation.expected_score_improvement
            business_impact = recommendation.business_impact
            service_targeting = recommendation.service_targeting
        elif isinstance(recommendation, dict):
            title = recommendation.get("title", "Untitled Recommendation")
            priority = recommendation.get("priority", "medium")
            description = recommendation.get("description", "No description available")
            pillar = recommendation.get("pillar", "unknown")
            affected_services = recommendation.get("affected_services", [])
            implementation_guidance = recommendation.get("implementation_guidance")
            aws_docs = recommendation.get("aws_documentation_links", [])
            effort = recommendation.get("estimated_effort", "medium")
            estimated_time = recommendation.get("estimated_time", "")
            expected_improvement = recommendation.get("expected_score_improvement", 0)
            business_impact = recommendation.get("business_impact", "")
            service_targeting = recommendation.get("service_targeting")
        else:
            logger.warning(f"⚠️ Unknown recommendation type: {type(recommendation)}")
            return
        
        # Add recommendation heading with ID
        self.formatter.add_section_heading(f"{rec_id}: {title}", level=3)
        
        # Add priority badge
        priority_text = self.visual_gen.add_priority_badge(priority)
        self.formatter.add_paragraph(f"Priority: {priority_text}")
        
        # Add pillar
        pillar_display = pillar.replace("_", " ").title()
        self.formatter.add_paragraph(f"Pillar: {pillar_display}")
        
        # Add description
        self.formatter.add_paragraph("")  # Spacing
        self.formatter.add_paragraph("Description:")
        self.formatter.add_paragraph(description)
        
        # Add business impact if available
        if business_impact:
            self.formatter.add_paragraph("")  # Spacing
            self.formatter.add_paragraph("Business Impact:")
            self.formatter.add_paragraph(business_impact)
        
        # Add affected services
        self._add_affected_services(affected_services, service_targeting)
        
        # Add implementation guidance
        self._add_implementation_guidance(implementation_guidance)
        
        # Add AWS documentation links
        self._add_aws_documentation(aws_docs)
        
        # Add effort and impact estimates
        self._add_estimates(effort, estimated_time, expected_improvement)
        
        # Add separator
        self.formatter.add_horizontal_line()
        self.formatter.add_paragraph("")  # Spacing
    
    def _add_affected_services(
        self,
        affected_services: List[str],
        service_targeting: Optional[Any]
    ):
        """Add affected services section."""
        self.formatter.add_paragraph("")  # Spacing
        self.formatter.add_section_heading("Affected Services", level=4)
        
        if affected_services:
            self.formatter.add_paragraph(
                f"This recommendation applies to the following {len(affected_services)} service(s):"
            )
            self.formatter.add_bullet_list(affected_services)
            
            # Add service-specific configuration changes if available
            if service_targeting:
                if isinstance(service_targeting, dict):
                    config_changes = service_targeting.get("configuration_changes", {})
                    if config_changes:
                        self.formatter.add_paragraph("")  # Spacing
                        self.formatter.add_paragraph("Service-Specific Configuration Changes:")
                        for service, change in config_changes.items():
                            self.formatter.add_paragraph(f"• {service}: {change}")
                elif hasattr(service_targeting, 'configuration_changes'):
                    if service_targeting.configuration_changes:
                        self.formatter.add_paragraph("")  # Spacing
                        self.formatter.add_paragraph("Service-Specific Configuration Changes:")
                        for service, change in service_targeting.configuration_changes.items():
                            self.formatter.add_paragraph(f"• {service}: {change}")
        else:
            self.formatter.add_paragraph("Applies to multiple services in your architecture.")
    
    def _add_implementation_guidance(self, implementation_guidance: Optional[Any]):
        """Add implementation guidance section."""
        self.formatter.add_paragraph("")  # Spacing
        self.formatter.add_section_heading("Implementation Guidance", level=4)
        
        if implementation_guidance:
            if isinstance(implementation_guidance, dict):
                steps = implementation_guidance.get("steps", [])
                prerequisites = implementation_guidance.get("prerequisites", [])
                testing = implementation_guidance.get("testing_guidance", "")
                rollback = implementation_guidance.get("rollback_plan", "")
            elif hasattr(implementation_guidance, 'steps'):
                steps = implementation_guidance.steps
                prerequisites = implementation_guidance.prerequisites
                testing = implementation_guidance.testing_guidance
                rollback = implementation_guidance.rollback_plan
            else:
                steps = []
                prerequisites = []
                testing = ""
                rollback = ""
            
            # Add prerequisites
            if prerequisites:
                self.formatter.add_paragraph("Prerequisites:")
                self.formatter.add_bullet_list(prerequisites)
                self.formatter.add_paragraph("")  # Spacing
            
            # Add implementation steps
            if steps:
                self.formatter.add_paragraph("Implementation Steps:")
                
                for step in steps:
                    if isinstance(step, dict):
                        step_num = step.get("step_number", 0)
                        step_title = step.get("title", "")
                        step_desc = step.get("description", "")
                        cli_commands = step.get("aws_cli_commands", [])
                        console_instructions = step.get("console_instructions", "")
                        validation = step.get("validation", "")
                    elif hasattr(step, 'step_number'):
                        step_num = step.step_number
                        step_title = step.title
                        step_desc = step.description
                        cli_commands = step.aws_cli_commands
                        console_instructions = step.console_instructions
                        validation = step.validation
                    else:
                        continue
                    
                    # Step heading
                    self.formatter.add_paragraph(f"{step_num}. {step_title}")
                    
                    # Step description
                    if step_desc:
                        self.formatter.add_paragraph(f"   {step_desc}")
                    
                    # CLI commands
                    if cli_commands:
                        self.formatter.add_paragraph("   AWS CLI:")
                        for cmd in cli_commands:
                            self.formatter.add_paragraph(f"   $ {cmd}")
                    
                    # Console instructions
                    if console_instructions:
                        self.formatter.add_paragraph(f"   Console: {console_instructions}")
                    
                    # Validation
                    if validation:
                        self.formatter.add_paragraph(f"   Validation: {validation}")
                    
                    self.formatter.add_paragraph("")  # Spacing between steps
            
            # Add testing guidance
            if testing:
                self.formatter.add_paragraph("Testing:")
                self.formatter.add_paragraph(testing)
                self.formatter.add_paragraph("")  # Spacing
            
            # Add rollback plan
            if rollback:
                self.formatter.add_paragraph("Rollback Plan:")
                self.formatter.add_paragraph(rollback)
        else:
            self.formatter.add_paragraph(
                "Refer to AWS documentation for detailed implementation steps."
            )
    
    def _add_aws_documentation(self, aws_docs: List[Any]):
        """Add AWS documentation links section."""
        self.formatter.add_paragraph("")  # Spacing
        self.formatter.add_section_heading("AWS Documentation", level=4)
        
        if aws_docs:
            self.formatter.add_paragraph("Relevant AWS documentation:")
            
            for doc in aws_docs[:3]:  # Top 3 links
                if isinstance(doc, dict):
                    title = doc.get("title", "Documentation")
                    url = doc.get("url", "")
                    description = doc.get("description", "")
                elif hasattr(doc, 'title'):
                    title = doc.title
                    url = doc.url
                    description = doc.description
                else:
                    continue
                
                # Add link
                para = self.formatter.add_paragraph("")
                self.formatter.add_hyperlink(para, title, url)
                if description:
                    self.formatter.add_paragraph(f"  {description}")
        else:
            self.formatter.add_paragraph("Refer to AWS Well-Architected Framework documentation.")
    
    def _add_estimates(
        self,
        effort: str,
        estimated_time: str,
        expected_improvement: float
    ):
        """Add effort and impact estimates section."""
        self.formatter.add_paragraph("")  # Spacing
        self.formatter.add_section_heading("Estimates", level=4)
        
        # Effort level
        effort_display = effort.upper() if isinstance(effort, str) else "MEDIUM"
        self.formatter.add_paragraph(f"Effort Level: {effort_display}")
        
        # Estimated time
        if estimated_time:
            self.formatter.add_paragraph(f"Estimated Time: {estimated_time}")
        
        # Expected improvement
        if expected_improvement > 0:
            self.formatter.add_paragraph(
                f"Expected Score Improvement: +{expected_improvement:.1f} points"
            )
    
    def _get_recommendation_priority(self, recommendation: Any) -> str:
        """Extract priority from recommendation."""
        if isinstance(recommendation, EnhancedRecommendation):
            return recommendation.priority.value
        elif isinstance(recommendation, dict):
            return recommendation.get("priority", "medium")
        return "medium"
    
    def _get_priority_numeric(self, priority: str) -> int:
        """Get numeric value for priority sorting."""
        priority_values = {
            "critical": 100,
            "high": 75,
            "medium": 50,
            "low": 25
        }
        return priority_values.get(priority.lower(), 50)
