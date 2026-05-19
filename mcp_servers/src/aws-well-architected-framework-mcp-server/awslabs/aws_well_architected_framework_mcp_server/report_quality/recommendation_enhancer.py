"""
Recommendation Enhancer for WAFR Report Quality Enhancement.

This module enhances basic recommendations with implementation guidance,
AWS documentation links, and service-specific targeting.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from .models import (
    EnhancedRecommendation,
    Priority,
    EffortLevel,
    ServiceTargeting
)
from .aws_documentation_linker import AWSDocumentationLinker
from .implementation_guidance_generator import ImplementationGuidanceGenerator
from .service_specificity_analyzer import ServiceSpecificityAnalyzer

logger = logging.getLogger(__name__)


class RecommendationEnhancer:
    """
    Enhances basic recommendations with comprehensive implementation details.
    
    Features:
    - Adds AWS documentation links
    - Generates implementation guidance
    - Adds service-specific targeting
    - Calculates effort estimates and score improvements
    - Adds business impact descriptions
    """
    
    def __init__(self):
        """Initialize the recommendation enhancer with required components."""
        self.doc_linker = AWSDocumentationLinker()
        self.guidance_generator = ImplementationGuidanceGenerator()
        self.service_analyzer = ServiceSpecificityAnalyzer()
        logger.info("Recommendation enhancer initialized")
    
    def enhance_recommendation(
        self,
        recommendation: Dict[str, Any],
        all_services: List[str],
        detected_capabilities: Dict[str, List[str]],
        architecture_context: Optional[Dict[str, Any]] = None
    ) -> EnhancedRecommendation:
        """
        Enhance a basic recommendation with comprehensive details.
        
        Args:
            recommendation: Basic recommendation data
            all_services: All services in the architecture
            detected_capabilities: Map of capabilities to services providing them
            architecture_context: Optional architecture context
            
        Returns:
            Enhanced recommendation with implementation guidance and documentation
        """
        logger.info(f"Enhancing recommendation: {recommendation.get('title', 'Unknown')}")
        
        # Extract basic fields
        rec_id = recommendation.get('id', str(uuid.uuid4()))
        title = recommendation.get('title', 'Untitled Recommendation')
        description = recommendation.get('description', '')
        pillar = recommendation.get('pillar', 'unknown')
        capability = recommendation.get('capability', 'unknown')
        
        # Parse priority
        priority_str = recommendation.get('priority', 'medium')
        priority = self._parse_priority(priority_str)
        
        # Get service-specific targeting
        service_targeting = self.service_analyzer.identify_affected_services(
            capability=capability,
            all_services=all_services,
            detected_capabilities=detected_capabilities
        )
        
        # Generate implementation guidance
        implementation_guidance = self.guidance_generator.generate_guidance(
            capability=capability,
            services=service_targeting.services_needing_capability or all_services[:3],
            architecture_context=architecture_context
        )
        
        # Get AWS documentation links
        pattern = architecture_context.get('primary_pattern') if architecture_context else None
        aws_docs = self.doc_linker.get_comprehensive_links(
            pillar=pillar,
            capability=capability,
            services=service_targeting.services_needing_capability[:2],
            pattern=pattern
        )
        
        # Parse effort level
        effort = self._parse_effort(recommendation.get('effort', 'medium'))
        
        # Generate business impact description
        business_impact = self._generate_business_impact(
            capability=capability,
            pillar=pillar,
            services=service_targeting.services_needing_capability
        )
        
        # Create enhanced recommendation
        enhanced = EnhancedRecommendation(
            id=rec_id,
            title=title,
            description=description,
            pillar=pillar,
            priority=priority,
            capability=capability,
            affected_services=service_targeting.services_needing_capability,
            service_targeting=service_targeting,
            implementation_guidance=implementation_guidance,
            aws_documentation_links=aws_docs,
            best_practices=self._get_best_practices(capability),
            estimated_effort=effort,
            estimated_time=implementation_guidance.estimated_effort,
            expected_score_improvement=implementation_guidance.expected_score_improvement,
            business_impact=business_impact,
            gap_size=recommendation.get('gap_size', 0.0),
            priority_score=recommendation.get('priority_score', 0.0),
            confidence=recommendation.get('confidence', 1.0)
        )
        
        logger.info(f"Enhanced recommendation with {len(implementation_guidance.steps)} steps and {len(aws_docs)} documentation links")
        return enhanced
    
    def enhance_recommendations_batch(
        self,
        recommendations: List[Dict[str, Any]],
        all_services: List[str],
        detected_capabilities: Dict[str, List[str]],
        architecture_context: Optional[Dict[str, Any]] = None
    ) -> List[EnhancedRecommendation]:
        """
        Enhance multiple recommendations in batch.
        
        Args:
            recommendations: List of basic recommendations
            all_services: All services in the architecture
            detected_capabilities: Map of capabilities to services
            architecture_context: Optional architecture context
            
        Returns:
            List of enhanced recommendations
        """
        logger.info(f"Enhancing {len(recommendations)} recommendations in batch")
        
        enhanced_recs = []
        for rec in recommendations:
            try:
                enhanced = self.enhance_recommendation(
                    recommendation=rec,
                    all_services=all_services,
                    detected_capabilities=detected_capabilities,
                    architecture_context=architecture_context
                )
                enhanced_recs.append(enhanced)
            except Exception as e:
                logger.error(f"Error enhancing recommendation {rec.get('title')}: {e}")
                # Continue with other recommendations
        
        logger.info(f"Successfully enhanced {len(enhanced_recs)} recommendations")
        return enhanced_recs
    
    def _parse_priority(self, priority_str: str) -> Priority:
        """Parse priority string to Priority enum."""
        priority_map = {
            'critical': Priority.CRITICAL,
            'high': Priority.HIGH,
            'medium': Priority.MEDIUM,
            'low': Priority.LOW
        }
        return priority_map.get(priority_str.lower(), Priority.MEDIUM)
    
    def _parse_effort(self, effort_str: str) -> EffortLevel:
        """Parse effort string to EffortLevel enum."""
        effort_map = {
            'low': EffortLevel.LOW,
            'medium': EffortLevel.MEDIUM,
            'high': EffortLevel.HIGH
        }
        return effort_map.get(effort_str.lower(), EffortLevel.MEDIUM)
    
    def _generate_business_impact(
        self,
        capability: str,
        pillar: str,
        services: List[str]
    ) -> str:
        """
        Generate business impact description for a recommendation.
        
        Args:
            capability: Capability name
            pillar: Pillar name
            services: Affected services
            
        Returns:
            Business impact description
        """
        impact_templates = {
            "encryption": "Protects sensitive data from unauthorized access, ensuring compliance with data protection regulations and maintaining customer trust.",
            "backup_recovery": "Ensures business continuity by enabling rapid recovery from data loss or system failures, minimizing downtime and revenue impact.",
            "monitoring_alerting": "Enables proactive issue detection and faster incident response, reducing mean time to resolution and improving system reliability.",
            "scaling": "Ensures application can handle variable workloads efficiently, maintaining performance during peak usage while optimizing costs during low usage.",
            "identity_access": "Strengthens security posture by ensuring only authorized users and services can access resources, reducing risk of security breaches.",
            "network_security": "Protects infrastructure from network-based attacks and unauthorized access, maintaining system integrity and availability.",
            "managed_services": "Reduces operational overhead and maintenance burden, allowing team to focus on business value rather than infrastructure management.",
            "caching": "Improves user experience through faster response times and reduces infrastructure costs by decreasing backend load.",
            "cost_monitoring": "Provides visibility into spending patterns, enabling cost optimization and preventing budget overruns."
        }
        
        base_impact = impact_templates.get(
            capability,
            f"Improves {pillar} posture by implementing {capability} best practices."
        )
        
        if services:
            service_count = len(services)
            if service_count == 1:
                base_impact += f" Affects {services[0]} service."
            elif service_count <= 3:
                base_impact += f" Affects {', '.join(services)} services."
            else:
                base_impact += f" Affects {service_count} services across the architecture."
        
        return base_impact
    
    def _get_best_practices(self, capability: str) -> List[str]:
        """
        Get best practices for a capability.
        
        Args:
            capability: Capability name
            
        Returns:
            List of best practice recommendations
        """
        best_practices = {
            "encryption": [
                "Use AWS KMS for centralized key management",
                "Enable encryption for data at rest and in transit",
                "Rotate encryption keys regularly",
                "Use separate keys for different data classifications"
            ],
            "backup_recovery": [
                "Follow the 3-2-1 backup rule (3 copies, 2 different media, 1 offsite)",
                "Test backup restoration procedures regularly",
                "Automate backup processes to ensure consistency",
                "Implement cross-region backup replication for disaster recovery"
            ],
            "monitoring_alerting": [
                "Set up alerts for critical metrics and thresholds",
                "Use composite alarms to reduce alert fatigue",
                "Implement escalation procedures for critical alerts",
                "Review and tune alert thresholds regularly"
            ],
            "scaling": [
                "Use target tracking scaling policies for predictable scaling",
                "Set appropriate cooldown periods to prevent flapping",
                "Monitor scaling activities and adjust policies as needed",
                "Test scaling behavior under load"
            ],
            "identity_access": [
                "Follow principle of least privilege",
                "Use IAM roles instead of long-term access keys",
                "Enable MFA for privileged accounts",
                "Regularly review and audit IAM policies"
            ],
            "network_security": [
                "Use security groups as virtual firewalls",
                "Implement network segmentation with private subnets",
                "Enable VPC Flow Logs for traffic analysis",
                "Use AWS WAF for application-layer protection"
            ],
            "managed_services": [
                "Evaluate managed service capabilities against requirements",
                "Plan migration with minimal disruption",
                "Leverage managed service features for automation",
                "Monitor managed service costs and optimize usage"
            ]
        }
        
        return best_practices.get(capability, [
            "Review AWS documentation for implementation guidance",
            "Test changes in non-production environment first",
            "Monitor impact after implementation",
            "Document configuration for future reference"
        ])
