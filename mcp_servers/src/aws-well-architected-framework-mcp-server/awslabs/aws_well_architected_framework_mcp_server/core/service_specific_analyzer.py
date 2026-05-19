"""
Service-Specific Analyzer for WAFR Report Content Improvement.

This module maps generic capability recommendations to specific detected services,
generating actionable, service-specific recommendations with concrete configuration changes.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from .logger import WAFRLogger


@dataclass
class ConfigurationChange:
    """Represents a specific configuration change for a service."""
    
    service: str  # e.g., "DynamoDB:bookings"
    current_state: str
    desired_state: str
    cli_command: str
    console_steps: List[str]
    validation_command: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "service": self.service,
            "current_state": self.current_state,
            "desired_state": self.desired_state,
            "cli_command": self.cli_command,
            "console_steps": self.console_steps,
            "validation_command": self.validation_command
        }


@dataclass
class ServiceSpecificRecommendation:
    """Represents a service-specific recommendation with implementation details."""
    
    title: str
    affected_services: List[str]
    configuration_changes: List[ConfigurationChange]
    capability_addressed: str
    score_improvement: float
    effort_hours: float
    cost_impact: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "affected_services": self.affected_services,
            "configuration_changes": [cc.to_dict() for cc in self.configuration_changes],
            "capability_addressed": self.capability_addressed,
            "score_improvement": self.score_improvement,
            "effort_hours": self.effort_hours,
            "cost_impact": self.cost_impact
        }


class ServiceSpecificAnalyzer:
    """
    Analyzes detected services and generates service-specific recommendations.
    
    This analyzer maps generic capability gaps to specific AWS services in the
    architecture, providing concrete configuration changes, CLI commands, and
    console navigation steps.
    """
    
    # Service-Capability Mapping: Which services should have which capabilities
    SERVICE_CAPABILITY_MAP = {
        # Compute Services
        "Lambda": {
            "capabilities": ["monitoring", "error_handling", "security", "performance"],
            "reliability": ["error_handling", "retry_logic", "dead_letter_queue"],
            "security": ["iam_roles", "encryption", "vpc_integration"],
            "performance": ["memory_optimization", "concurrency_limits"],
            "operational_excellence": ["monitoring", "logging", "tracing"],
            "cost_optimization": ["right_sizing", "reserved_concurrency"]
        },
        
        # Database Services
        "DynamoDB": {
            "capabilities": ["backup_recovery", "encryption", "monitoring", "scaling"],
            "reliability": ["point_in_time_recovery", "backup", "multi_az"],
            "security": ["encryption_at_rest", "encryption_in_transit", "iam_access"],
            "performance": ["auto_scaling", "dax_caching", "global_tables"],
            "cost_optimization": ["on_demand_pricing", "reserved_capacity", "auto_scaling"],
            "operational_excellence": ["cloudwatch_metrics", "cloudwatch_alarms"]
        },
        
        # Storage Services
        "S3": {
            "capabilities": ["backup_recovery", "encryption", "versioning", "lifecycle"],
            "reliability": ["versioning", "cross_region_replication", "lifecycle_policies"],
            "security": ["encryption_at_rest", "bucket_policies", "access_logging"],
            "performance": ["transfer_acceleration", "cloudfront_integration"],
            "cost_optimization": ["intelligent_tiering", "lifecycle_policies", "storage_classes"],
            "sustainability": ["intelligent_tiering", "lifecycle_policies"]
        },
        
        # API Services
        "API Gateway": {
            "capabilities": ["throttling", "authorization", "monitoring", "caching"],
            "reliability": ["throttling", "retry_logic"],
            "security": ["iam_authorization", "api_keys", "waf_integration", "resource_policies"],
            "performance": ["caching", "compression"],
            "operational_excellence": ["cloudwatch_logs", "x_ray_tracing", "access_logging"],
            "cost_optimization": ["caching", "usage_plans"]
        },
        
        # Monitoring Services
        "CloudWatch": {
            "capabilities": ["monitoring", "alerting", "logging"],
            "reliability": ["alarms", "composite_alarms"],
            "operational_excellence": ["dashboards", "log_insights", "metrics"],
            "security": ["log_encryption", "log_retention"]
        },
        
        # Messaging Services
        "SNS": {
            "capabilities": ["dead_letter_queue", "encryption", "monitoring"],
            "reliability": ["message_durability", "delivery_retries"],
            "security": ["encryption_at_rest", "encryption_in_transit", "access_policies"],
            "operational_excellence": ["cloudwatch_metrics", "delivery_status_logging"]
        },
        
        "SQS": {
            "capabilities": ["dead_letter_queue", "encryption", "monitoring"],
            "reliability": ["message_retention", "dead_letter_queue", "visibility_timeout"],
            "security": ["encryption_at_rest", "encryption_in_transit", "access_policies"],
            "operational_excellence": ["cloudwatch_metrics", "message_tracing"]
        },
        
        # Orchestration Services
        "Step Functions": {
            "capabilities": ["error_handling", "retry_logic", "monitoring"],
            "reliability": ["error_handling", "retry_policies", "catch_blocks"],
            "operational_excellence": ["cloudwatch_logs", "x_ray_tracing", "execution_history"],
            "security": ["iam_roles", "encryption"]
        },
        
        # CDN Services
        "CloudFront": {
            "capabilities": ["caching", "security", "monitoring"],
            "performance": ["edge_caching", "compression", "http2"],
            "security": ["waf_integration", "ssl_tls", "signed_urls", "origin_access_identity"],
            "reliability": ["origin_failover", "health_checks"],
            "cost_optimization": ["cache_optimization", "compression"]
        },
        
        # Network Services
        "VPC": {
            "capabilities": ["network_isolation", "security_groups", "network_acls"],
            "security": ["private_subnets", "security_groups", "network_acls", "flow_logs"],
            "reliability": ["multi_az", "nat_gateway_redundancy"]
        },
        
        "WAF": {
            "capabilities": ["web_application_firewall", "rate_limiting", "ip_filtering"],
            "security": ["managed_rules", "custom_rules", "rate_limiting", "geo_blocking"],
            "operational_excellence": ["logging", "metrics"]
        },
        
        # Security Services
        "KMS": {
            "capabilities": ["encryption_key_management", "key_rotation"],
            "security": ["customer_managed_keys", "key_rotation", "key_policies"],
            "operational_excellence": ["cloudwatch_metrics", "cloudtrail_logging"]
        },
        
        "IAM": {
            "capabilities": ["identity_access_management", "least_privilege"],
            "security": ["roles", "policies", "mfa", "password_policy"],
            "operational_excellence": ["access_analyzer", "credential_report"]
        },
        
        # Tracing Services
        "X-Ray": {
            "capabilities": ["distributed_tracing", "performance_analysis"],
            "operational_excellence": ["service_map", "trace_analysis", "annotations"],
            "performance": ["bottleneck_identification", "latency_analysis"]
        }
    }
    
    # Pattern-aware capability expectations
    PATTERN_CAPABILITY_EXPECTATIONS = {
        "serverless": {
            "required_services": ["Lambda", "API Gateway", "DynamoDB"],
            "optional_services": ["S3", "SNS", "SQS", "Step Functions", "CloudWatch", "X-Ray"],
            "emphasized_capabilities": ["managed_services", "auto_scaling", "event_driven"]
        },
        "microservices": {
            "required_services": ["API Gateway", "CloudWatch"],
            "optional_services": ["ECS", "EKS", "ALB", "Service Discovery", "App Mesh"],
            "emphasized_capabilities": ["service_isolation", "api_management", "observability"]
        },
        "event_driven": {
            "required_services": ["SNS", "SQS", "EventBridge"],
            "optional_services": ["Lambda", "Step Functions", "Kinesis"],
            "emphasized_capabilities": ["message_durability", "event_processing", "async_communication"]
        }
    }
    
    def __init__(self):
        """Initialize the ServiceSpecificAnalyzer."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("ServiceSpecificAnalyzer initialized")
    
    def analyze_service_gaps(
        self,
        detected_services: List[str],
        missing_capabilities: List[str],
        pillar: str,
        detected_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze which services should have which missing capabilities.
        
        Args:
            detected_services: List of AWS services detected in architecture
            missing_capabilities: List of capabilities that are missing
            pillar: WAFR pillar being assessed
            detected_patterns: Optional list of architectural patterns
            
        Returns:
            Dictionary with service gaps categorized by type
        """
        self.logger.info(
            f"Analyzing service gaps for {pillar} pillar: "
            f"{len(detected_services)} services, {len(missing_capabilities)} missing capabilities"
        )
        
        configuration_gaps = []  # Service exists but lacks capability
        service_gaps = []  # Capability requires new service
        
        # Normalize service names (handle variations)
        normalized_services = [self._normalize_service_name(s) for s in detected_services]
        
        for capability in missing_capabilities:
            # Find which detected services should have this capability
            services_needing_capability = []
            
            for service in normalized_services:
                if self._service_should_have_capability(service, capability, pillar):
                    services_needing_capability.append(service)
            
            if services_needing_capability:
                # Configuration gap: service exists but lacks capability
                configuration_gaps.append({
                    "capability": capability,
                    "affected_services": services_needing_capability,
                    "gap_type": "configuration"
                })
            else:
                # Service gap: capability requires a service not in architecture
                recommended_services = self._get_services_for_capability(capability, pillar)
                if recommended_services:
                    service_gaps.append({
                        "capability": capability,
                        "recommended_services": recommended_services,
                        "gap_type": "service"
                    })
        
        return {
            "configuration_gaps": configuration_gaps,
            "service_gaps": service_gaps,
            "total_gaps": len(configuration_gaps) + len(service_gaps)
        }
    
    def _normalize_service_name(self, service: str) -> str:
        """Normalize service name to match SERVICE_CAPABILITY_MAP keys."""
        # Handle common variations
        service_mappings = {
            "lambda": "Lambda",
            "dynamodb": "DynamoDB",
            "s3": "S3",
            "api gateway": "API Gateway",
            "apigateway": "API Gateway",
            "cloudwatch": "CloudWatch",
            "sns": "SNS",
            "sqs": "SQS",
            "step functions": "Step Functions",
            "stepfunctions": "Step Functions",
            "cloudfront": "CloudFront",
            "vpc": "VPC",
            "waf": "WAF",
            "kms": "KMS",
            "iam": "IAM",
            "x-ray": "X-Ray",
            "xray": "X-Ray"
        }
        
        normalized = service.strip().lower()
        return service_mappings.get(normalized, service)
    
    def _service_should_have_capability(
        self,
        service: str,
        capability: str,
        pillar: str
    ) -> bool:
        """Check if a service should have a specific capability for a pillar."""
        if service not in self.SERVICE_CAPABILITY_MAP:
            return False
        
        service_caps = self.SERVICE_CAPABILITY_MAP[service]
        
        # Check pillar-specific capabilities
        pillar_key = pillar.lower().replace(" ", "_")
        if pillar_key in service_caps:
            pillar_capabilities = service_caps[pillar_key]
            # Check if capability matches any in the list
            for cap in pillar_capabilities:
                if capability.lower() in cap.lower() or cap.lower() in capability.lower():
                    return True
        
        # Check general capabilities
        if "capabilities" in service_caps:
            general_capabilities = service_caps["capabilities"]
            for cap in general_capabilities:
                if capability.lower() in cap.lower() or cap.lower() in capability.lower():
                    return True
        
        return False
    
    def _get_services_for_capability(
        self,
        capability: str,
        pillar: str
    ) -> List[str]:
        """Get list of services that can provide a capability."""
        recommended_services = []
        
        pillar_key = pillar.lower().replace(" ", "_")
        
        for service, service_caps in self.SERVICE_CAPABILITY_MAP.items():
            # Check pillar-specific capabilities
            if pillar_key in service_caps:
                pillar_capabilities = service_caps[pillar_key]
                for cap in pillar_capabilities:
                    if capability.lower() in cap.lower() or cap.lower() in capability.lower():
                        recommended_services.append(service)
                        break
        
        return recommended_services
    
    def generate_service_recommendations(
        self,
        service_gaps: Dict[str, Any],
        pillar: str
    ) -> List[ServiceSpecificRecommendation]:
        """
        Generate service-specific recommendations from service gaps.
        
        Args:
            service_gaps: Output from analyze_service_gaps
            pillar: WAFR pillar being assessed
            
        Returns:
            List of ServiceSpecificRecommendation objects
        """
        self.logger.info(f"Generating service-specific recommendations for {pillar} pillar")
        
        recommendations = []
        
        # Process configuration gaps (service exists but lacks capability)
        for gap in service_gaps.get("configuration_gaps", []):
            capability = gap["capability"]
            affected_services = gap["affected_services"]
            
            # Generate recommendation for each affected service
            for service in affected_services:
                config_changes = self._generate_configuration_changes(
                    service,
                    capability,
                    pillar
                )
                
                if config_changes:
                    recommendation = ServiceSpecificRecommendation(
                        title=self._generate_recommendation_title(service, capability),
                        affected_services=[service],
                        configuration_changes=config_changes,
                        capability_addressed=capability,
                        score_improvement=self._estimate_score_improvement(capability, pillar),
                        effort_hours=self._estimate_effort(service, capability),
                        cost_impact=self._estimate_cost_impact(service, capability)
                    )
                    recommendations.append(recommendation)
        
        # Process service gaps (capability requires new service)
        for gap in service_gaps.get("service_gaps", []):
            capability = gap["capability"]
            recommended_services = gap["recommended_services"]
            
            if recommended_services:
                # Recommend the most appropriate service
                primary_service = recommended_services[0]
                config_changes = self._generate_new_service_configuration(
                    primary_service,
                    capability,
                    pillar
                )
                
                if config_changes:
                    recommendation = ServiceSpecificRecommendation(
                        title=f"Add {primary_service} for {capability.replace('_', ' ').title()}",
                        affected_services=[primary_service],
                        configuration_changes=config_changes,
                        capability_addressed=capability,
                        score_improvement=self._estimate_score_improvement(capability, pillar),
                        effort_hours=self._estimate_effort(primary_service, capability, is_new=True),
                        cost_impact=self._estimate_cost_impact(primary_service, capability, is_new=True)
                    )
                    recommendations.append(recommendation)
        
        self.logger.info(f"Generated {len(recommendations)} service-specific recommendations")
        return recommendations
    
    def _generate_recommendation_title(self, service: str, capability: str) -> str:
        """Generate a clear, actionable recommendation title."""
        capability_titles = {
            "point_in_time_recovery": f"Enable {service} Point-in-Time Recovery",
            "backup": f"Configure {service} Automated Backups",
            "encryption_at_rest": f"Enable {service} Encryption at Rest",
            "encryption_in_transit": f"Enable {service} Encryption in Transit",
            "monitoring": f"Configure {service} Monitoring and Alarms",
            "logging": f"Enable {service} Logging",
            "waf_integration": f"Add WAF Protection to {service}",
            "vpc_integration": f"Configure {service} VPC Integration",
            "dead_letter_queue": f"Add Dead Letter Queue to {service}",
            "error_handling": f"Implement {service} Error Handling",
            "auto_scaling": f"Configure {service} Auto Scaling",
            "caching": f"Enable {service} Caching"
        }
        
        return capability_titles.get(
            capability,
            f"Implement {capability.replace('_', ' ').title()} for {service}"
        )
    
    def _generate_configuration_changes(
        self,
        service: str,
        capability: str,
        pillar: str
    ) -> List[ConfigurationChange]:
        """Generate specific configuration changes for a service-capability pair."""
        # This will be expanded with specific configurations for each service-capability combination
        # For now, return a template
        
        changes = []
        
        # DynamoDB specific configurations
        if service == "DynamoDB" and "point_in_time_recovery" in capability.lower():
            changes.append(ConfigurationChange(
                service=f"{service}:table-name",
                current_state="Point-in-Time Recovery disabled",
                desired_state="Point-in-Time Recovery enabled",
                cli_command="aws dynamodb update-continuous-backups --table-name TABLE_NAME --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true",
                console_steps=[
                    "Navigate to DynamoDB console",
                    "Select your table",
                    "Click 'Backups' tab",
                    "Click 'Enable' under Point-in-time recovery"
                ],
                validation_command="aws dynamodb describe-continuous-backups --table-name TABLE_NAME"
            ))
        
        elif service == "DynamoDB" and "encryption" in capability.lower():
            changes.append(ConfigurationChange(
                service=f"{service}:table-name",
                current_state="Default encryption (AWS owned key)",
                desired_state="Encryption with AWS managed or customer managed KMS key",
                cli_command="aws dynamodb update-table --table-name TABLE_NAME --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=KEY_ID",
                console_steps=[
                    "Navigate to DynamoDB console",
                    "Select your table",
                    "Click 'Additional settings' tab",
                    "Under 'Encryption', click 'Manage encryption'",
                    "Select 'AWS managed key' or 'Customer managed key'"
                ],
                validation_command="aws dynamodb describe-table --table-name TABLE_NAME --query 'Table.SSEDescription'"
            ))
        
        # S3 specific configurations
        elif service == "S3" and "encryption" in capability.lower():
            changes.append(ConfigurationChange(
                service=f"{service}:bucket-name",
                current_state="No default encryption",
                desired_state="Default encryption enabled with KMS",
                cli_command="aws s3api put-bucket-encryption --bucket BUCKET_NAME --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\",\"KMSMasterKeyID\":\"KEY_ID\"}}]}'",
                console_steps=[
                    "Navigate to S3 console",
                    "Select your bucket",
                    "Click 'Properties' tab",
                    "Under 'Default encryption', click 'Edit'",
                    "Select 'AWS-KMS' and choose a key"
                ],
                validation_command="aws s3api get-bucket-encryption --bucket BUCKET_NAME"
            ))
        
        # Lambda specific configurations
        elif service == "Lambda" and "dead_letter_queue" in capability.lower():
            changes.append(ConfigurationChange(
                service=f"{service}:function-name",
                current_state="No dead letter queue configured",
                desired_state="Dead letter queue configured with SQS or SNS",
                cli_command="aws lambda update-function-configuration --function-name FUNCTION_NAME --dead-letter-config TargetArn=arn:aws:sqs:REGION:ACCOUNT:QUEUE_NAME",
                console_steps=[
                    "Navigate to Lambda console",
                    "Select your function",
                    "Click 'Configuration' tab",
                    "Click 'Asynchronous invocation'",
                    "Under 'Dead-letter queue service', select SQS or SNS",
                    "Choose or create a queue/topic"
                ],
                validation_command="aws lambda get-function-configuration --function-name FUNCTION_NAME --query 'DeadLetterConfig'"
            ))
        
        # API Gateway specific configurations
        elif service == "API Gateway" and "waf" in capability.lower():
            changes.append(ConfigurationChange(
                service=f"{service}:api-name",
                current_state="No WAF protection",
                desired_state="WAF Web ACL associated",
                cli_command="aws wafv2 associate-web-acl --web-acl-arn WEB_ACL_ARN --resource-arn API_GATEWAY_ARN",
                console_steps=[
                    "Navigate to WAF & Shield console",
                    "Create or select a Web ACL",
                    "Click 'Associated AWS resources'",
                    "Click 'Add AWS resources'",
                    "Select your API Gateway stage"
                ],
                validation_command="aws wafv2 get-web-acl-for-resource --resource-arn API_GATEWAY_ARN"
            ))
        
        # Generic fallback for unmatched capabilities
        if not changes:
            capability_display = capability.replace('_', ' ').title()
            changes.append(ConfigurationChange(
                service=service,
                current_state=f"{capability_display} not configured",
                desired_state=f"{capability_display} enabled and configured",
                cli_command=f"# Configure {capability_display} for {service} using AWS CLI or SDK",
                console_steps=[
                    f"Navigate to {service} console",
                    f"Select your {service} resource",
                    f"Configure {capability_display} settings",
                    "Review and apply changes"
                ],
                validation_command=f"# Verify {capability_display} configuration for {service}"
            ))
        
        return changes
    
    def _generate_new_service_configuration(
        self,
        service: str,
        capability: str,
        pillar: str
    ) -> List[ConfigurationChange]:
        """Generate configuration for adding a new service."""
        # Template for new service recommendations
        changes = []
        
        if service == "WAF":
            changes.append(ConfigurationChange(
                service=service,
                current_state="WAF not deployed",
                desired_state="WAF Web ACL created and associated with API Gateway",
                cli_command="aws wafv2 create-web-acl --name MyWebACL --scope REGIONAL --default-action Allow={} --rules file://rules.json",
                console_steps=[
                    "Navigate to WAF & Shield console",
                    "Click 'Create web ACL'",
                    "Choose 'Regional' for API Gateway",
                    "Add managed rule groups (Core rule set, Known bad inputs)",
                    "Add rate limiting rule",
                    "Associate with API Gateway"
                ],
                validation_command="aws wafv2 list-web-acls --scope REGIONAL"
            ))
        
        elif service == "VPC":
            changes.append(ConfigurationChange(
                service=service,
                current_state="Resources not in VPC",
                desired_state="VPC created with private subnets and security groups",
                cli_command="aws ec2 create-vpc --cidr-block 10.0.0.0/16",
                console_steps=[
                    "Navigate to VPC console",
                    "Click 'Create VPC'",
                    "Choose 'VPC and more' for guided setup",
                    "Configure subnets (public and private)",
                    "Configure NAT gateways for private subnets",
                    "Update Lambda/RDS to use VPC"
                ],
                validation_command="aws ec2 describe-vpcs"
            ))
        
        return changes
    
    def _estimate_score_improvement(self, capability: str, pillar: str) -> float:
        """Estimate score improvement from implementing a capability."""
        # Base improvements by capability importance
        capability_weights = {
            "encryption": 8.0,
            "backup": 10.0,
            "monitoring": 7.0,
            "waf": 12.0,
            "vpc": 15.0,
            "dead_letter_queue": 5.0,
            "auto_scaling": 8.0,
            "logging": 6.0
        }
        
        for key, weight in capability_weights.items():
            if key in capability.lower():
                return weight
        
        return 5.0  # Default improvement
    
    def _estimate_effort(self, service: str, capability: str, is_new: bool = False) -> float:
        """Estimate effort in hours to implement a capability."""
        if is_new:
            # New service requires more effort
            service_effort = {
                "WAF": 4.0,
                "VPC": 16.0,
                "KMS": 2.0
            }
            return service_effort.get(service, 8.0)
        
        # Configuration change effort
        capability_effort = {
            "encryption": 1.0,
            "backup": 0.5,
            "monitoring": 2.0,
            "waf": 4.0,
            "dead_letter_queue": 1.0,
            "logging": 1.0
        }
        
        for key, effort in capability_effort.items():
            if key in capability.lower():
                return effort
        
        return 2.0  # Default effort
    
    def _estimate_cost_impact(self, service: str, capability: str, is_new: bool = False) -> str:
        """Estimate cost impact of implementing a capability."""
        if is_new:
            service_costs = {
                "WAF": "$5/month + $1 per million requests",
                "VPC": "$0.045/hour per NAT Gateway (~$32/month)",
                "KMS": "$1/month per key + $0.03 per 10,000 requests"
            }
            return service_costs.get(service, "Varies based on usage")
        
        capability_costs = {
            "encryption": "$0 (included in service pricing)",
            "backup": "Storage costs for backups",
            "monitoring": "$0 (included in CloudWatch free tier for basic metrics)",
            "waf": "$5/month + $1 per million requests",
            "dead_letter_queue": "Minimal SQS/SNS costs",
            "logging": "CloudWatch Logs storage costs"
        }
        
        for key, cost in capability_costs.items():
            if key in capability.lower():
                return cost
        
        return "Minimal additional cost"
