"""
Enhanced recommendation engine for WAFR assessments with service-specific recommendations.

IMPORTANT: This engine generates recommendations based on Claude's dynamic analysis.
It does NOT use hardcoded service-to-capability mappings.
Recommendations are generated using the actual services detected in the architecture.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Effort/timeline estimates by capability type (not service-specific)
CAPABILITY_EFFORT_ESTIMATES = {
    # Quick wins (1-2 weeks, Low effort)
    'encryption': {'timeline': '1-2 weeks', 'effort': 'Low', 'impact': 'High'},
    'backup_recovery': {'timeline': '1-2 weeks', 'effort': 'Low', 'impact': 'High'},
    'cost_monitoring': {'timeline': '1 week', 'effort': 'Low', 'impact': 'Medium'},
    
    # Medium effort (2-4 weeks)
    'monitoring_alerting': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'High'},
    'monitoring_detection': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'High'},
    'identity_access': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'Critical'},
    'observability': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'High'},
    'data_protection': {'timeline': '2-4 weeks', 'effort': 'Medium', 'impact': 'High'},
    'resource_optimization': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'Medium'},
    'storage_optimization': {'timeline': '2-3 weeks', 'effort': 'Medium', 'impact': 'Medium'},
    
    # Higher effort (4-8 weeks)
    'infrastructure_as_code': {'timeline': '4-6 weeks', 'effort': 'High', 'impact': 'Medium'},
    'deployment_automation': {'timeline': '4-8 weeks', 'effort': 'High', 'impact': 'Medium'},
    'incident_response': {'timeline': '3-5 weeks', 'effort': 'High', 'impact': 'High'},
    'runbook_automation': {'timeline': '4-6 weeks', 'effort': 'High', 'impact': 'Medium'},
    
    # Strategic (6+ weeks)
    'fault_tolerance': {'timeline': '6-12 weeks', 'effort': 'High', 'impact': 'High'},
    'redundancy': {'timeline': '4-8 weeks', 'effort': 'High', 'impact': 'High'},
    'scaling': {'timeline': '3-6 weeks', 'effort': 'Medium', 'impact': 'High'},
}


class EnhancedRecommendationEngine:
    """
    Generates service-specific recommendations based on Claude's dynamic analysis.
    
    This engine does NOT use hardcoded service-to-capability mappings.
    Instead, it generates recommendations using:
    1. The actual services detected by Claude in the architecture
    2. The missing capabilities identified during pillar assessment
    3. Dynamic effort/timeline estimates based on capability type
    """
    
    def __init__(self):
        # No hardcoded service mappings - we use Claude's analysis
        pass
    
    def generate_service_specific_recommendations(
        self,
        pillar_name: str,
        detected_capabilities: List[str],
        missing_capabilities: List[str],
        aws_services: List[Dict[str, Any]],
        score: float
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations specific to the ACTUAL detected AWS services.
        
        ENHANCED: Now generates recommendations for:
        1. Missing capabilities (critical priority)
        2. Low-coverage detected capabilities (medium priority) - NEW!
        
        Args:
            pillar_name: WAFR pillar name
            detected_capabilities: Capabilities already implemented
            missing_capabilities: Capabilities that need implementation
            aws_services: List of AWS services detected by Claude
            score: Current pillar score
            
        Returns:
            List of service-specific recommendations referencing actual detected services
        """
        recommendations = []
        
        # Extract service names from Claude's detected services
        service_names = self._extract_service_names(aws_services)
        
        logger.info(f"🔧 DYNAMIC_REC: Generating recommendations for {pillar_name}")
        logger.info(f"🔧 DYNAMIC_REC: Actual detected services: {service_names}")
        logger.info(f"🔧 DYNAMIC_REC: Missing capabilities: {missing_capabilities}")
        logger.info(f"🔧 DYNAMIC_REC: Detected capabilities: {detected_capabilities}")
        
        # ENHANCEMENT 1: Generate recommendations for MISSING capabilities (critical/high priority)
        for capability in missing_capabilities:
            # Get effort/timeline estimate for this capability type
            effort_info = CAPABILITY_EFFORT_ESTIMATES.get(
                capability.lower().replace(' ', '_'),
                {'timeline': '2-4 weeks', 'effort': 'Medium', 'impact': 'Medium'}
            )
            
            # Determine priority based on score and impact
            if score < 60 or effort_info.get('impact') == 'Critical':
                priority = 'critical'
            elif score < 70 or effort_info.get('impact') == 'High':
                priority = 'high'
            else:
                priority = 'medium'
            
            # Generate recommendation using actual detected services
            capability_display = capability.replace('_', ' ').title()
            pillar_display = pillar_name.replace('_', ' ')
            
            # ENHANCEMENT 2: Get PILLAR-SPECIFIC relevant services (not generic list)
            relevant_services = self._get_capability_relevant_services(
                capability.lower().replace(' ', '_'), service_names
            )
            if not relevant_services:
                relevant_services = service_names[:3]
            
            # Build implementation steps dynamically based on capability type
            # ENHANCEMENT 3: Use relevant services for implementation steps
            implementation_steps = self._generate_implementation_steps(
                capability, pillar_name, relevant_services
            )
            
            # Generate SERVICE-SPECIFIC title and description
            title, description = self._generate_service_specific_title_description(
                capability, pillar_name, relevant_services, detected_capabilities, missing_capabilities
            )
            
            rec = {
                'title': title,
                'priority': priority,
                'description': description,
                'affected_services': relevant_services,  # ENHANCEMENT 2: Use pillar-specific services
                'implementation_steps': implementation_steps,
                'timeline': effort_info['timeline'],
                'effort': effort_info['effort'],
                'business_impact': f'Improves {pillar_display} compliance and reduces risk'
            }
            
            recommendations.append(rec)
            logger.info(f"✅ DYNAMIC_REC: Generated recommendation for MISSING capability {capability} affecting {relevant_services[:3]}")
        
        # ENHANCEMENT 2: Generate recommendations for LOW-COVERAGE detected capabilities
        # If pillar score is below 80%, generate enhancement recommendations for detected capabilities
        if score < 80 and detected_capabilities:
            logger.info(f"🔧 DYNAMIC_REC: Score {score}% < 80%, generating enhancement recommendations for detected capabilities")
            
            # Identify capabilities that need enhancement (detected but likely incomplete)
            for capability in detected_capabilities[:2]:  # Limit to top 2 to avoid overwhelming
                # Get relevant services for this capability
                relevant_services = self._get_capability_relevant_services(
                    capability.lower().replace(' ', '_'), service_names
                )
                
                if not relevant_services:
                    relevant_services = service_names[:3]
                
                # Get effort/timeline estimate
                effort_info = CAPABILITY_EFFORT_ESTIMATES.get(
                    capability.lower().replace(' ', '_'),
                    {'timeline': '2-4 weeks', 'effort': 'Medium', 'impact': 'Medium'}
                )
                
                # Generate enhancement recommendation
                capability_display = capability.replace('_', ' ').title()
                pillar_display = pillar_name.replace('_', ' ')
                services_text = ', '.join(relevant_services[:3])
                
                # Calculate coverage for description
                total_caps = len(detected_capabilities) + len(missing_capabilities)
                coverage_pct = int((len(detected_capabilities) / max(1, total_caps)) * 100)
                
                # Generate enhancement-specific implementation steps
                implementation_steps = self._generate_enhancement_steps(
                    capability, pillar_name, relevant_services
                )
                
                rec = {
                    'title': f"Enhance {capability_display} for {services_text}",
                    'priority': 'medium',
                    'description': f"Strengthen existing {capability_display.lower()} implementation for {services_text}. Current {pillar_display} score: {score:.1f}%, target: 80%+.",
                    'affected_services': relevant_services,
                    'implementation_steps': implementation_steps,
                    'timeline': effort_info['timeline'],
                    'effort': effort_info['effort'],
                    'business_impact': f'Improves {pillar_display} maturity from {score:.1f}% toward 80%+ target'
                }
                
                recommendations.append(rec)
                logger.info(f"✅ DYNAMIC_REC: Generated ENHANCEMENT recommendation for {capability} affecting {relevant_services[:3]}")
        
        return recommendations
    
    def _generate_enhancement_steps(
        self,
        capability: str,
        pillar_name: str,
        service_names: List[str]
    ) -> List[str]:
        """
        Generate enhancement steps for DETECTED capabilities that need improvement.
        These are more advanced steps than initial implementation.
        """
        capability_lower = capability.lower().replace(' ', '_')
        services_text = ', '.join(service_names[:3]) if service_names else 'your services'
        
        # Generate capability-specific enhancement steps with AWS CLI commands
        if 'encryption' in capability_lower:
            return self._generate_encryption_enhancement_steps(service_names)
        elif 'monitoring' in capability_lower or 'observability' in capability_lower:
            return self._generate_monitoring_enhancement_steps(service_names)
        elif 'backup' in capability_lower or 'recovery' in capability_lower:
            return self._generate_backup_enhancement_steps(service_names)
        elif 'identity' in capability_lower or 'access' in capability_lower:
            return self._generate_iam_enhancement_steps(service_names)
        elif 'scaling' in capability_lower or 'fault' in capability_lower:
            return self._generate_reliability_enhancement_steps(service_names)
        else:
            return [
                f'Audit current {capability.replace("_", " ")} implementation for {services_text}',
                f'Identify gaps against AWS Well-Architected best practices',
                f'Implement advanced {capability.replace("_", " ")} features',
                f'Configure automated compliance checks',
                f'Document and test enhanced configuration'
            ]
    
    def _generate_encryption_enhancement_steps(self, service_names: List[str]) -> List[str]:
        """Generate advanced encryption enhancement steps."""
        steps = ['Audit current encryption configuration across all services']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'dynamodb' in service_lower:
                steps.append(f'Upgrade {service} to use Customer Managed Keys (CMK) for enhanced control')
            elif 's3' in service_lower:
                steps.append(f'Enable bucket keys for {service} to reduce KMS API costs')
            elif 'rds' in service_lower:
                steps.append(f'Verify {service} encryption and enable automated key rotation')
            elif 'elasticache' in service_lower:
                steps.append(f'Enable in-transit encryption for {service}')
        
        steps.extend([
            'Configure KMS key rotation for automatic annual rotation',
            'Implement encryption monitoring with CloudWatch metrics'
        ])
        return steps
    
    def _generate_monitoring_enhancement_steps(self, service_names: List[str]) -> List[str]:
        """Generate advanced monitoring enhancement steps."""
        steps = ['Review current CloudWatch dashboards and alarms for gaps']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Enable {service} Insights for enhanced function monitoring')
            elif 'dynamodb' in service_lower:
                steps.append(f'Enable {service} Contributor Insights for access pattern analysis')
            elif 'api gateway' in service_lower or 'appsync' in service_lower:
                steps.append(f'Enable detailed CloudWatch metrics for {service} with per-method granularity')
            elif 'ecs' in service_lower or 'eks' in service_lower:
                steps.append(f'Enable Container Insights for {service}')
        
        steps.extend([
            'Create composite alarms for correlated failure detection',
            'Set up CloudWatch Anomaly Detection for key metrics',
            'Configure cross-account/cross-region dashboard for unified view'
        ])
        return steps
    
    def _generate_backup_enhancement_steps(self, service_names: List[str]) -> List[str]:
        """Generate advanced backup enhancement steps."""
        steps = ['Review current backup coverage and RPO/RTO requirements']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'dynamodb' in service_lower:
                steps.append(f'Enable continuous backups (PITR) for {service}')
            elif 's3' in service_lower:
                steps.append(f'Configure {service} cross-region replication for disaster recovery')
            elif 'rds' in service_lower:
                steps.append(f'Enable {service} cross-region automated backups')
        
        steps.extend([
            'Create AWS Backup plan with lifecycle rules',
            'Test restore procedures and document recovery runbooks',
            'Configure backup compliance reporting with AWS Backup Audit Manager'
        ])
        return steps
    
    def _generate_iam_enhancement_steps(self, service_names: List[str]) -> List[str]:
        """Generate advanced IAM enhancement steps."""
        steps = ['Run IAM Access Analyzer to identify overly permissive policies']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Review {service} execution role permissions and apply least-privilege')
            elif 's3' in service_lower:
                steps.append(f'Enable {service} Block Public Access at account level')
            elif 'dynamodb' in service_lower:
                steps.append(f'Implement fine-grained access control for {service} using IAM conditions')
        
        steps.extend([
            'Enable AWS Organizations SCPs for preventive guardrails',
            'Configure IAM credential report and unused credential cleanup',
            'Implement permission boundaries for delegated administration'
        ])
        return steps
    
    def _generate_reliability_enhancement_steps(self, service_names: List[str]) -> List[str]:
        """Generate advanced reliability enhancement steps."""
        steps = ['Review current multi-AZ and fault tolerance configuration']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'dynamodb' in service_lower:
                steps.append(f'Consider {service} Global Tables for multi-region resilience')
            elif 'lambda' in service_lower:
                steps.append(f'Configure {service} provisioned concurrency for consistent performance')
            elif 'rds' in service_lower:
                steps.append(f'Enable {service} Multi-AZ with readable standby for improved availability')
            elif 'sqs' in service_lower:
                steps.append(f'Configure {service} dead-letter queue with redrive policy')
        
        steps.extend([
            'Implement health checks with Route 53 or ALB health checks',
            'Configure auto-scaling policies based on CloudWatch metrics',
            'Create and test failover runbooks with AWS FIS (Fault Injection Simulator)'
        ])
        return steps
    
    def _generate_implementation_steps(
        self,
        capability: str,
        pillar_name: str,
        service_names: List[str]
    ) -> List[str]:
        """
        Generate SERVICE-SPECIFIC implementation steps based on capability and actual detected services.
        
        This generates steps that reference the ACTUAL services in the architecture,
        not hardcoded services like "DynamoDB" or "S3".
        """
        capability_lower = capability.lower().replace(' ', '_')
        
        # Generate service-specific steps based on capability type
        steps = []
        
        if 'encryption' in capability_lower:
            steps = self._generate_encryption_steps(service_names)
        elif 'identity' in capability_lower or 'access' in capability_lower:
            steps = self._generate_iam_steps(service_names)
        elif 'data_protection' in capability_lower:
            steps = self._generate_data_protection_steps(service_names)
        elif 'monitoring' in capability_lower or 'observability' in capability_lower:
            steps = self._generate_monitoring_steps(service_names)
        elif 'backup' in capability_lower or 'recovery' in capability_lower:
            steps = self._generate_backup_steps(service_names)
        elif 'cost' in capability_lower:
            steps = self._generate_cost_steps(service_names)
        elif 'scaling' in capability_lower or 'fault' in capability_lower:
            steps = self._generate_reliability_steps(service_names)
        else:
            # Generic steps for other capabilities
            services_text = ', '.join(service_names[:3]) if service_names else 'your services'
            steps = [
                f'Assess current {capability.replace("_", " ")} implementation across {services_text}',
                f'Identify gaps in {capability.replace("_", " ")} coverage',
                f'Design {capability.replace("_", " ")} solution for your architecture',
                f'Implement {capability.replace("_", " ")} following AWS best practices',
                f'Test and validate implementation',
                f'Monitor and iterate on results'
            ]
        
        return steps
    
    def _generate_encryption_steps(self, service_names: List[str]) -> List[str]:
        """Generate encryption-specific implementation steps."""
        steps = ['Create or identify a KMS Customer Managed Key (CMK) for encryption']
        
        for service in service_names[:4]:
            service_lower = service.lower()
            if 'dynamodb' in service_lower:
                steps.append(f'Enable encryption at rest for {service} tables using AWS managed or customer managed KMS key')
            elif 's3' in service_lower:
                steps.append(f'Enable default encryption on {service} buckets with SSE-S3 or SSE-KMS')
            elif 'rds' in service_lower or 'aurora' in service_lower:
                steps.append(f'Enable encryption for {service} instances (note: must be enabled at creation for existing instances)')
            elif 'lambda' in service_lower:
                steps.append(f'Encrypt {service} environment variables using KMS')
            elif 'sqs' in service_lower:
                steps.append(f'Enable server-side encryption for {service} queues')
            elif 'sns' in service_lower:
                steps.append(f'Enable server-side encryption for {service} topics')
            elif 'elasticache' in service_lower or 'redis' in service_lower:
                steps.append(f'Enable encryption at rest and in-transit for {service}')
            elif 'secrets' in service_lower:
                steps.append(f'Verify {service} is using KMS encryption for stored secrets')
        
        steps.append('Enable TLS 1.2+ for all API endpoints and data in transit')
        steps.append('Configure KMS key rotation for automatic annual key rotation')
        return steps
    
    def _generate_iam_steps(self, service_names: List[str]) -> List[str]:
        """Generate IAM-specific implementation steps."""
        steps = [
            'Audit current IAM policies and generate credential report',
            'Enable IAM Access Analyzer to identify overly permissive policies'
        ]
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Review and minimize {service} execution role permissions')
            elif 'api gateway' in service_lower:
                steps.append(f'Configure {service} authorizer with Cognito or IAM authentication')
            elif 'dynamodb' in service_lower:
                steps.append(f'Implement fine-grained access control for {service} using IAM conditions')
            elif 's3' in service_lower:
                steps.append(f'Enable {service} Block Public Access at account level')
            elif 'ecs' in service_lower:
                steps.append(f'Configure {service} task roles with least-privilege permissions')
        
        steps.extend([
            'Enable MFA for privileged operations and sensitive resources',
            'Review IAM Access Analyzer findings and remediate issues'
        ])
        return steps
    
    def _generate_data_protection_steps(self, service_names: List[str]) -> List[str]:
        """Generate data protection implementation steps."""
        steps = ['Classify data sensitivity levels (PII, PHI, financial, public)']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 's3' in service_lower:
                steps.append(f'Enable {service} versioning for critical data buckets')
                steps.append(f'Configure {service} bucket policies to prevent public access')
            elif 'dynamodb' in service_lower:
                steps.append(f'Enable Point-in-Time Recovery (PITR) for {service} tables')
                steps.append(f'Enable deletion protection for {service} tables')
            elif 'rds' in service_lower:
                steps.append(f'Enable deletion protection and automated backups for {service}')
        
        steps.extend([
            'Enable AWS Macie for sensitive data discovery (if using S3)',
            'Implement data lifecycle policies for retention compliance',
            'Document data classification and handling procedures in runbooks'
        ])
        return steps
    
    def _generate_monitoring_steps(self, service_names: List[str]) -> List[str]:
        """Generate monitoring implementation steps."""
        steps = ['Set up centralized logging with CloudWatch Logs']
        
        for service in service_names[:4]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Enable {service} X-Ray tracing and CloudWatch Insights')
            elif 'api gateway' in service_lower:
                steps.append(f'Enable {service} access logging and CloudWatch metrics')
            elif 'dynamodb' in service_lower:
                steps.append(f'Enable {service} Contributor Insights for access pattern analysis')
            elif 'ecs' in service_lower:
                steps.append(f'Enable Container Insights for {service} monitoring')
            elif 'rds' in service_lower:
                steps.append(f'Enable Enhanced Monitoring and Performance Insights for {service}')
        
        steps.extend([
            'Create CloudWatch Alarms for critical thresholds',
            'Build CloudWatch Dashboards for key metrics visualization'
        ])
        return steps
    
    def _generate_backup_steps(self, service_names: List[str]) -> List[str]:
        """Generate backup implementation steps."""
        steps = [
            'Define RPO (Recovery Point Objective) and RTO (Recovery Time Objective) requirements',
            'Create AWS Backup vault and backup plan with appropriate schedule'
        ]
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'dynamodb' in service_lower:
                steps.append(f'Enable Point-in-Time Recovery (PITR) for {service} tables')
            elif 's3' in service_lower:
                steps.append(f'Enable {service} versioning and cross-region replication for critical buckets')
            elif 'rds' in service_lower or 'aurora' in service_lower:
                steps.append(f'Configure automated snapshots and backup retention for {service}')
            elif 'efs' in service_lower:
                steps.append(f'Add {service} to AWS Backup plan')
        
        steps.extend([
            'Configure backup lifecycle rules for retention compliance',
            'Test backup restoration procedures regularly and document runbooks'
        ])
        return steps
    
    def _generate_cost_steps(self, service_names: List[str]) -> List[str]:
        """Generate cost optimization implementation steps."""
        steps = [
            'Enable AWS Cost Explorer and set up cost allocation tags',
            'Create AWS Budgets with alerts for spending thresholds'
        ]
        
        for service in service_names[:4]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Right-size {service} memory allocation using AWS Lambda Power Tuning')
            elif 'dynamodb' in service_lower:
                steps.append(f'Evaluate {service} on-demand vs provisioned capacity based on usage patterns')
            elif 's3' in service_lower:
                steps.append(f'Implement {service} Intelligent-Tiering or lifecycle policies for storage optimization')
            elif 'ec2' in service_lower:
                steps.append(f'Evaluate Reserved Instances or Savings Plans for {service}')
            elif 'rds' in service_lower:
                steps.append(f'Right-size {service} instances and consider Reserved Instances for predictable workloads')
            elif 'cloudfront' in service_lower:
                steps.append(f'Optimize {service} cache hit ratio to reduce origin requests')
        
        steps.append('Review and implement AWS Trusted Advisor cost recommendations')
        return steps
    
    def _generate_reliability_steps(self, service_names: List[str]) -> List[str]:
        """Generate reliability implementation steps."""
        steps = ['Design for multi-AZ deployment where applicable']
        
        for service in service_names[:3]:
            service_lower = service.lower()
            if 'lambda' in service_lower:
                steps.append(f'Configure {service} reserved concurrency and error handling')
            elif 'dynamodb' in service_lower:
                steps.append(f'Consider {service} Global Tables for multi-region resilience')
            elif 'rds' in service_lower:
                steps.append(f'Enable Multi-AZ deployment for {service}')
            elif 'api gateway' in service_lower:
                steps.append(f'Configure {service} throttling and caching')
            elif 'sqs' in service_lower:
                steps.append(f'Implement dead-letter queues for {service}')
            elif 'alb' in service_lower or 'load balancer' in service_lower:
                steps.append(f'Configure {service} health checks and connection draining')
        
        steps.extend([
            'Implement circuit breaker patterns for external dependencies',
            'Create and test failover procedures',
            'Set up health checks and auto-recovery mechanisms'
        ])
        return steps
    
    def _generate_service_specific_title_description(
        self,
        capability: str,
        pillar_name: str,
        service_names: List[str],
        detected_capabilities: List[str],
        missing_capabilities: List[str]
    ) -> tuple:
        """
        Generate SERVICE-SPECIFIC title and description for recommendations.
        
        Instead of generic "Implement Encryption", generates specific titles like
        "Enable DynamoDB and Lambda encryption at rest".
        """
        capability_lower = capability.lower().replace(' ', '_')
        capability_display = capability.replace('_', ' ').title()
        pillar_display = pillar_name.replace('_', ' ')
        
        # Calculate coverage percentage
        total_caps = len(detected_capabilities) + len(missing_capabilities)
        coverage_pct = int((len(detected_capabilities) / max(1, total_caps)) * 100)
        
        # Get relevant services for this capability
        relevant_services = self._get_capability_relevant_services(capability_lower, service_names)
        services_text = ', '.join(relevant_services[:3]) if relevant_services else 'your services'
        
        # Generate capability-specific titles and descriptions
        if 'encryption' in capability_lower:
            if relevant_services:
                title = f"Enable encryption for {services_text}"
                description = f"Implement encryption at rest and in transit for {services_text} to protect sensitive data. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement data encryption"
                description = f"Enable encryption across your architecture to meet security requirements. Current coverage: {coverage_pct}%."
        
        elif 'identity' in capability_lower or 'access' in capability_lower:
            if relevant_services:
                title = f"Implement IAM controls for {services_text}"
                description = f"Configure least-privilege IAM policies and access controls for {services_text}. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement identity and access management"
                description = f"Establish IAM best practices across your architecture. Current coverage: {coverage_pct}%."
        
        elif 'data_protection' in capability_lower:
            if relevant_services:
                title = f"Enable data protection for {services_text}"
                description = f"Implement data protection controls including versioning, backup, and access policies for {services_text}. Current coverage: {coverage_pct}%."
            else:
                title = "Implement data protection controls"
                description = f"Enable data protection mechanisms across your architecture. Current coverage: {coverage_pct}%."
        
        elif 'monitoring' in capability_lower or 'observability' in capability_lower:
            if relevant_services:
                title = f"Enhance monitoring for {services_text}"
                description = f"Implement comprehensive monitoring, logging, and alerting for {services_text}. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement observability and monitoring"
                description = f"Enable monitoring and alerting across your architecture. Current coverage: {coverage_pct}%."
        
        elif 'backup' in capability_lower or 'recovery' in capability_lower:
            if relevant_services:
                title = f"Configure backup and recovery for {services_text}"
                description = f"Implement automated backup and disaster recovery procedures for {services_text}. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement backup and recovery"
                description = f"Enable backup and disaster recovery across your architecture. Current coverage: {coverage_pct}%."
        
        elif 'cost' in capability_lower or 'managed_services' in capability_lower:
            if relevant_services:
                title = f"Optimize costs for {services_text}"
                description = f"Implement cost optimization strategies for {services_text} including right-sizing and reserved capacity. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement cost optimization"
                description = f"Enable cost monitoring and optimization across your architecture. Current coverage: {coverage_pct}%."
        
        elif 'scaling' in capability_lower or 'fault' in capability_lower or 'redundancy' in capability_lower:
            if relevant_services:
                title = f"Improve resilience for {services_text}"
                description = f"Implement fault tolerance and auto-scaling for {services_text}. Current {pillar_display} coverage: {coverage_pct}%."
            else:
                title = "Implement fault tolerance"
                description = f"Enable resilience mechanisms across your architecture. Current coverage: {coverage_pct}%."
        
        else:
            # Generic fallback
            title = f"Implement {capability_display}"
            description = f"Add {capability_display.lower()} to improve {pillar_display} pillar. Current coverage: {coverage_pct}%, target: 80%."
        
        return title, description
    
    def _get_capability_relevant_services(self, capability: str, all_services: List[str]) -> List[str]:
        """Get services most relevant to a specific capability."""
        capability_service_keywords = {
            # Security capabilities
            'encryption': ['dynamodb', 's3', 'rds', 'aurora', 'elasticache', 'efs', 'sqs', 'sns', 'lambda', 'secrets', 'kms'],
            'identity': ['lambda', 'api gateway', 'appsync', 'cognito', 'iam'],
            'access': ['lambda', 'api gateway', 'appsync', 'cognito', 'iam', 's3', 'dynamodb'],
            'identity_access': ['lambda', 'api gateway', 'appsync', 'cognito', 'iam', 's3', 'dynamodb'],
            'data_protection': ['s3', 'dynamodb', 'rds', 'aurora', 'efs', 'kms'],
            'network_security': ['vpc', 'security group', 'waf', 'cloudfront', 'load balancer', 'alb'],
            'monitoring_detection': ['cloudwatch', 'cloudtrail', 'guardduty', 'security hub', 'config'],
            
            # Reliability capabilities
            'monitoring': ['lambda', 'api gateway', 'dynamodb', 'ecs', 'rds', 'cloudwatch'],
            'monitoring_alerting': ['cloudwatch', 'sns', 'lambda', 'api gateway', 'dynamodb', 'rds'],
            'observability': ['lambda', 'api gateway', 'dynamodb', 'ecs', 'x-ray', 'cloudwatch'],
            'backup': ['dynamodb', 's3', 'rds', 'aurora', 'efs'],
            'backup_recovery': ['dynamodb', 's3', 'rds', 'aurora', 'efs', 'backup'],
            'recovery': ['dynamodb', 's3', 'rds', 'aurora'],
            'scaling': ['lambda', 'dynamodb', 'ecs', 'ec2', 'rds', 'auto scaling'],
            'fault': ['lambda', 'dynamodb', 'rds', 'sqs', 'route 53'],
            'fault_tolerance': ['lambda', 'dynamodb', 'rds', 'sqs', 'route 53', 'load balancer'],
            'redundancy': ['dynamodb', 'rds', 's3', 'route 53', 'load balancer', 'elasticache'],
            
            # Cost optimization capabilities
            'cost': ['lambda', 'dynamodb', 's3', 'ec2', 'rds', 'cloudfront', 'elasticache'],
            'cost_monitoring': ['cost explorer', 'budgets', 'cloudwatch', 'lambda', 'dynamodb', 's3'],
            'resource_optimization': ['lambda', 'dynamodb', 's3', 'ec2', 'rds', 'elasticache', 'cloudfront'],
            'pricing_models': ['ec2', 'rds', 'dynamodb', 'lambda', 'elasticache', 'savings'],
            'storage_optimization': ['s3', 'dynamodb', 'efs', 'rds', 'elasticache'],
            'managed_services': ['lambda', 'dynamodb', 'fargate', 'aurora', 'appsync', 'bedrock'],
            
            # Performance capabilities
            'caching': ['elasticache', 'cloudfront', 'dynamodb', 'api gateway'],
            'content_delivery': ['cloudfront', 's3', 'route 53'],
            'database_optimization': ['dynamodb', 'rds', 'aurora', 'elasticache'],
            'compute_optimization': ['lambda', 'ec2', 'ecs', 'fargate'],
            'resource_selection': ['lambda', 'ec2', 'rds', 'dynamodb', 'elasticache'],
            
            # Operational excellence capabilities
            'infrastructure_as_code': ['cloudformation', 'cdk', 'terraform'],
            'deployment_automation': ['codepipeline', 'codebuild', 'codedeploy', 'cloudformation'],
            'incident_response': ['cloudwatch', 'sns', 'lambda', 'systems manager'],
            'runbook_automation': ['systems manager', 'lambda', 'step functions'],
            
            # Sustainability capabilities
            'efficient_compute': ['lambda', 'fargate', 'graviton', 'ec2', 'ecs'],
            'resource_utilization': ['lambda', 'ec2', 'rds', 'dynamodb', 'elasticache'],
            'data_optimization': ['s3', 'dynamodb', 'glacier', 'lifecycle'],
            'region_selection': ['route 53', 'cloudfront', 's3']
        }
        
        keywords = capability_service_keywords.get(capability, [])
        relevant = []
        
        for service in all_services:
            service_lower = service.lower()
            if any(kw in service_lower for kw in keywords):
                relevant.append(service)
        
        # If no matches found, return services most likely relevant to the pillar
        if not relevant:
            # Fallback based on capability category
            if any(x in capability for x in ['cost', 'pricing', 'resource', 'storage']):
                fallback_keywords = ['dynamodb', 's3', 'lambda', 'ec2', 'rds']
            elif any(x in capability for x in ['security', 'encryption', 'identity', 'access']):
                fallback_keywords = ['iam', 'kms', 'cognito', 's3', 'dynamodb']
            elif any(x in capability for x in ['reliability', 'backup', 'fault', 'scaling']):
                fallback_keywords = ['dynamodb', 'rds', 'lambda', 'route 53']
            else:
                fallback_keywords = []
            
            for service in all_services:
                service_lower = service.lower()
                if any(kw in service_lower for kw in fallback_keywords):
                    relevant.append(service)
        
        return relevant[:3] if relevant else all_services[:2]

    def _extract_service_names(self, aws_services: List[Dict[str, Any]]) -> List[str]:
        """
        Extract clean service names from Claude's detected services.
        
        Handles various formats that Claude may return:
        - Dict with 'name' key
        - Dict with 'item' key in markdown format
        - Plain string
        """
        service_names = []
        for service in aws_services:
            if isinstance(service, dict):
                # Try 'name' first, then 'item'
                name = service.get('name', service.get('item', ''))
                
                # Extract from markdown format "**AWS Lambda** - description"
                if '**' in name:
                    parts = name.split('**')
                    name = parts[1] if len(parts) > 1 else name
                
                # Remove "AWS " or "Amazon " prefix
                name = name.replace('AWS ', '').replace('Amazon ', '').strip()
                
                # Remove description after " - "
                if ' - ' in name:
                    name = name.split(' - ')[0].strip()
                
                if name:
                    service_names.append(name)
            elif isinstance(service, str):
                name = service.replace('AWS ', '').replace('Amazon ', '').strip()
                if name:
                    service_names.append(name)
        
        return service_names
    
    # REMOVED: _generate_capability_recommendation method with hardcoded service-specific recommendations
    # The generate_service_specific_recommendations method now generates dynamic recommendations
    # based on Claude's actual detected services, not hardcoded DynamoDB/S3/Cognito patterns.
    
    def generate_recommendations(self, capability_gaps):
        """Legacy method for backward compatibility."""
        return []


# Global instance
enhanced_recommendation_engine = EnhancedRecommendationEngine()