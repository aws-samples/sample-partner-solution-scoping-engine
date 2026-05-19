"""
Implementation Guidance Generator for WAFR Report Quality Enhancement.

This module generates step-by-step implementation instructions for recommendations
with service-specific customization, CLI commands, and validation steps.
"""

import logging
from typing import List, Dict, Optional, Any
from .models import (
    ImplementationGuidance,
    ImplementationStep,
    EffortLevel
)

logger = logging.getLogger(__name__)


class ImplementationGuidanceGenerator:
    """
    Generates detailed implementation guidance for WAFR recommendations.
    
    Features:
    - Template-based guidance for common capabilities
    - Service-specific customization
    - Step-by-step instructions with validation
    - AWS CLI command examples
    - Console instruction alternatives
    - Effort estimation based on complexity
    """
    
    def __init__(self):
        """Initialize the guidance generator with templates."""
        self._load_capability_templates()
        self._load_service_customizations()
    
    def _load_capability_templates(self):
        """Load implementation templates for common capabilities."""
        self.capability_templates = {
            "encryption": {
                "steps": [
                    {
                        "title": "Enable encryption at rest",
                        "description": "Configure encryption for data storage services using AWS KMS",
                        "cli_template": "aws {service} modify-{resource} --{resource}-identifier {id} --storage-encrypted --kms-key-id {key_id}",
                        "console": "Navigate to service console → Select resource → Modify → Enable encryption → Select KMS key",
                        "validation": "Verify encryption status in service console or using describe commands"
                    },
                    {
                        "title": "Enable encryption in transit",
                        "description": "Configure SSL/TLS for data transmission",
                        "cli_template": "aws {service} modify-{resource} --{resource}-identifier {id} --enable-ssl",
                        "console": "Navigate to service console → Security settings → Enable SSL/TLS",
                        "validation": "Test connections using SSL/TLS protocols"
                    },
                    {
                        "title": "Configure encryption for backups",
                        "description": "Ensure automated backups are encrypted",
                        "console": "Navigate to backup settings → Enable encryption for automated backups",
                        "validation": "Verify backup encryption in backup console"
                    }
                ],
                "prerequisites": [
                    "AWS KMS key created and accessible",
                    "Appropriate IAM permissions for encryption operations",
                    "Service supports encryption (check service documentation)"
                ],
                "testing": "Test data access with encryption enabled. Verify performance impact is acceptable.",
                "rollback": "Disable encryption if issues occur. Note: Some services cannot disable encryption once enabled.",
                "effort": EffortLevel.MEDIUM,
                "estimated_time": "2-4 hours"
            },
            
            "backup_recovery": {
                "steps": [
                    {
                        "title": "Enable automated backups",
                        "description": "Configure automated backup schedule and retention",
                        "cli_template": "aws {service} modify-{resource} --{resource}-identifier {id} --backup-retention-period 7 --preferred-backup-window 03:00-04:00",
                        "console": "Navigate to service console → Backup settings → Enable automated backups → Set retention period",
                        "validation": "Verify backup schedule in service console"
                    },
                    {
                        "title": "Configure backup encryption",
                        "description": "Ensure backups are encrypted using KMS",
                        "console": "Navigate to backup settings → Enable encryption → Select KMS key",
                        "validation": "Verify backup encryption status"
                    },
                    {
                        "title": "Test backup restoration",
                        "description": "Perform test restore to verify backup integrity",
                        "cli_template": "aws {service} restore-{resource}-from-backup --{resource}-identifier test-restore --backup-identifier {backup_id}",
                        "console": "Navigate to backups → Select backup → Restore → Create test instance",
                        "validation": "Verify restored data integrity and completeness"
                    },
                    {
                        "title": "Set up cross-region backup replication",
                        "description": "Configure backup replication to another region for disaster recovery",
                        "console": "Navigate to backup settings → Enable cross-region replication → Select target region",
                        "validation": "Verify backups appear in target region"
                    }
                ],
                "prerequisites": [
                    "Sufficient storage quota for backups",
                    "KMS key available in target regions",
                    "IAM permissions for backup operations"
                ],
                "testing": "Perform full restore test in non-production environment. Measure RTO and RPO.",
                "rollback": "Disable automated backups if storage costs are prohibitive. Ensure manual backups are taken.",
                "effort": EffortLevel.MEDIUM,
                "estimated_time": "3-6 hours"
            },
            
            "monitoring_alerting": {
                "steps": [
                    {
                        "title": "Enable detailed monitoring",
                        "description": "Enable detailed CloudWatch metrics for the service",
                        "cli_template": "aws cloudwatch put-metric-alarm --alarm-name {alarm_name} --metric-name {metric} --namespace AWS/{service} --statistic Average --period 300 --threshold {threshold} --comparison-operator GreaterThanThreshold",
                        "console": "Navigate to CloudWatch → Metrics → Select service → Enable detailed monitoring",
                        "validation": "Verify metrics are being collected in CloudWatch"
                    },
                    {
                        "title": "Create CloudWatch alarms",
                        "description": "Set up alarms for critical metrics (CPU, memory, errors)",
                        "cli_template": "aws cloudwatch put-metric-alarm --alarm-name {name} --alarm-actions {sns_topic_arn} --metric-name {metric} --threshold {value}",
                        "console": "Navigate to CloudWatch → Alarms → Create alarm → Select metric → Set threshold → Add SNS topic",
                        "validation": "Test alarm by triggering threshold condition"
                    },
                    {
                        "title": "Configure SNS notifications",
                        "description": "Set up SNS topic and subscriptions for alarm notifications",
                        "cli_template": "aws sns create-topic --name {topic_name} && aws sns subscribe --topic-arn {arn} --protocol email --notification-endpoint {email}",
                        "console": "Navigate to SNS → Create topic → Add subscriptions → Confirm subscriptions",
                        "validation": "Send test notification to verify delivery"
                    },
                    {
                        "title": "Enable CloudWatch Logs",
                        "description": "Configure application and service logs to CloudWatch Logs",
                        "console": "Navigate to service console → Logging → Enable CloudWatch Logs → Select log group",
                        "validation": "Verify logs are appearing in CloudWatch Logs"
                    }
                ],
                "prerequisites": [
                    "SNS topic created for notifications",
                    "Email addresses or endpoints for notifications",
                    "IAM permissions for CloudWatch operations"
                ],
                "testing": "Trigger test alarms to verify notification delivery. Check log aggregation is working.",
                "rollback": "Disable alarms if false positives are excessive. Adjust thresholds as needed.",
                "effort": EffortLevel.LOW,
                "estimated_time": "2-4 hours"
            },
            
            "scaling": {
                "steps": [
                    {
                        "title": "Create Auto Scaling group",
                        "description": "Set up Auto Scaling group with desired capacity and scaling policies",
                        "cli_template": "aws autoscaling create-auto-scaling-group --auto-scaling-group-name {name} --launch-template {template} --min-size {min} --max-size {max} --desired-capacity {desired}",
                        "console": "Navigate to EC2 → Auto Scaling Groups → Create → Configure launch template and capacity",
                        "validation": "Verify Auto Scaling group is created and instances are launching"
                    },
                    {
                        "title": "Configure scaling policies",
                        "description": "Set up target tracking or step scaling policies",
                        "cli_template": "aws autoscaling put-scaling-policy --auto-scaling-group-name {name} --policy-name {policy} --policy-type TargetTrackingScaling --target-tracking-configuration {config}",
                        "console": "Navigate to Auto Scaling group → Automatic scaling → Create scaling policy → Select metric and target",
                        "validation": "Monitor scaling activities in Auto Scaling console"
                    },
                    {
                        "title": "Configure health checks",
                        "description": "Set up health checks to replace unhealthy instances",
                        "console": "Navigate to Auto Scaling group → Health checks → Enable ELB health checks",
                        "validation": "Terminate an instance manually and verify replacement"
                    },
                    {
                        "title": "Test scaling behavior",
                        "description": "Generate load to test scale-out and scale-in behavior",
                        "validation": "Monitor CloudWatch metrics and Auto Scaling activities during load test"
                    }
                ],
                "prerequisites": [
                    "Launch template or configuration created",
                    "Load balancer configured (if using ELB health checks)",
                    "CloudWatch alarms for scaling metrics",
                    "IAM role for Auto Scaling"
                ],
                "testing": "Perform load testing to verify scaling behavior. Measure scale-out and scale-in times.",
                "rollback": "Set Auto Scaling group to fixed capacity if issues occur. Investigate scaling policies.",
                "effort": EffortLevel.MEDIUM,
                "estimated_time": "3-5 hours"
            },
            
            "managed_services": {
                "steps": [
                    {
                        "title": "Identify migration candidates",
                        "description": "Identify self-managed services that can be migrated to AWS managed services",
                        "validation": "Document current services and their managed service equivalents"
                    },
                    {
                        "title": "Plan migration strategy",
                        "description": "Develop migration plan with minimal downtime",
                        "validation": "Review migration plan with stakeholders"
                    },
                    {
                        "title": "Set up managed service",
                        "description": "Provision AWS managed service with appropriate configuration",
                        "console": "Navigate to service console → Create resource → Configure settings → Launch",
                        "validation": "Verify managed service is running and accessible"
                    },
                    {
                        "title": "Migrate data and configuration",
                        "description": "Transfer data and configuration to managed service",
                        "validation": "Verify data integrity after migration"
                    },
                    {
                        "title": "Update application connections",
                        "description": "Update application to connect to managed service",
                        "validation": "Test application functionality with managed service"
                    },
                    {
                        "title": "Decommission self-managed service",
                        "description": "After validation period, decommission old infrastructure",
                        "validation": "Verify no dependencies remain on old service"
                    }
                ],
                "prerequisites": [
                    "Managed service supports required features",
                    "Migration tools available (DMS, SCT, etc.)",
                    "Downtime window approved (if needed)",
                    "Rollback plan documented"
                ],
                "testing": "Run parallel systems during transition. Perform comprehensive testing before cutover.",
                "rollback": "Keep self-managed service running during transition. Revert connections if issues occur.",
                "effort": EffortLevel.HIGH,
                "estimated_time": "1-3 days"
            },
            
            "identity_access": {
                "steps": [
                    {
                        "title": "Review current IAM policies",
                        "description": "Audit existing IAM policies for overly permissive access",
                        "console": "Navigate to IAM → Policies → Review policy permissions",
                        "validation": "Document policies that need tightening"
                    },
                    {
                        "title": "Implement least privilege",
                        "description": "Update IAM policies to follow least privilege principle",
                        "cli_template": "aws iam create-policy --policy-name {name} --policy-document file://policy.json",
                        "console": "Navigate to IAM → Policies → Create policy → Define permissions → Create",
                        "validation": "Test application functionality with new policies"
                    },
                    {
                        "title": "Enable MFA for privileged users",
                        "description": "Require multi-factor authentication for administrative access",
                        "console": "Navigate to IAM → Users → Security credentials → Assign MFA device",
                        "validation": "Verify MFA is required for privileged operations"
                    },
                    {
                        "title": "Implement IAM roles for services",
                        "description": "Use IAM roles instead of access keys for service authentication",
                        "cli_template": "aws iam create-role --role-name {name} --assume-role-policy-document file://trust-policy.json",
                        "console": "Navigate to IAM → Roles → Create role → Select service → Attach policies",
                        "validation": "Verify services can assume roles successfully"
                    }
                ],
                "prerequisites": [
                    "IAM Access Analyzer enabled",
                    "Current IAM policies documented",
                    "MFA devices available for users"
                ],
                "testing": "Test all application functions with new IAM policies. Verify no unauthorized access.",
                "rollback": "Keep old policies available. Revert if application breaks.",
                "effort": EffortLevel.MEDIUM,
                "estimated_time": "4-8 hours"
            },
            
            "network_security": {
                "steps": [
                    {
                        "title": "Review security group rules",
                        "description": "Audit security groups for overly permissive rules",
                        "console": "Navigate to VPC → Security Groups → Review inbound/outbound rules",
                        "validation": "Document rules that need tightening"
                    },
                    {
                        "title": "Implement least privilege network access",
                        "description": "Update security groups to allow only necessary traffic",
                        "cli_template": "aws ec2 authorize-security-group-ingress --group-id {id} --protocol tcp --port {port} --cidr {cidr}",
                        "console": "Navigate to Security Groups → Edit inbound rules → Add specific rules → Remove broad rules",
                        "validation": "Test application connectivity with new rules"
                    },
                    {
                        "title": "Enable VPC Flow Logs",
                        "description": "Enable flow logs for network traffic monitoring",
                        "cli_template": "aws ec2 create-flow-logs --resource-type VPC --resource-ids {vpc_id} --traffic-type ALL --log-destination-type cloud-watch-logs --log-group-name {log_group}",
                        "console": "Navigate to VPC → Flow Logs → Create flow log → Select destination",
                        "validation": "Verify flow logs are being captured"
                    },
                    {
                        "title": "Implement network segmentation",
                        "description": "Use private subnets for backend resources",
                        "console": "Navigate to VPC → Subnets → Create private subnets → Update route tables",
                        "validation": "Verify resources in private subnets cannot be accessed directly from internet"
                    }
                ],
                "prerequisites": [
                    "VPC and subnets configured",
                    "CloudWatch Logs group for flow logs",
                    "Network architecture documented"
                ],
                "testing": "Test application connectivity from all required sources. Verify blocked access is actually blocked.",
                "rollback": "Keep old security group rules documented. Revert if connectivity breaks.",
                "effort": EffortLevel.MEDIUM,
                "estimated_time": "3-6 hours"
            }
        }
    
    def _load_service_customizations(self):
        """Load service-specific customization rules."""
        self.service_customizations = {
            "RDS": {
                "encryption": {
                    "cli_example": "aws rds modify-db-instance --db-instance-identifier mydb --storage-encrypted --kms-key-id arn:aws:kms:region:account:key/key-id",
                    "notes": "Encryption cannot be enabled on existing RDS instances. Create encrypted snapshot and restore."
                },
                "backup_recovery": {
                    "cli_example": "aws rds modify-db-instance --db-instance-identifier mydb --backup-retention-period 7 --preferred-backup-window 03:00-04:00",
                    "notes": "Automated backups are enabled by default. Configure retention period and backup window."
                }
            },
            "DynamoDB": {
                "encryption": {
                    "cli_example": "aws dynamodb update-table --table-name mytable --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=key-id",
                    "notes": "DynamoDB encryption at rest can be enabled on existing tables."
                },
                "backup_recovery": {
                    "cli_example": "aws dynamodb update-continuous-backups --table-name mytable --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true",
                    "notes": "Enable point-in-time recovery for continuous backups."
                }
            },
            "S3": {
                "encryption": {
                    "cli_example": "aws s3api put-bucket-encryption --bucket mybucket --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}'",
                    "notes": "S3 default encryption applies to new objects. Existing objects need to be re-uploaded or copied."
                },
                "versioning": {
                    "cli_example": "aws s3api put-bucket-versioning --bucket mybucket --versioning-configuration Status=Enabled",
                    "notes": "Enable versioning before enabling MFA Delete for additional protection."
                }
            },
            "Lambda": {
                "monitoring_alerting": {
                    "cli_example": "aws lambda update-function-configuration --function-name myfunction --tracing-config Mode=Active",
                    "notes": "Enable X-Ray tracing for distributed tracing. Configure CloudWatch Logs retention."
                },
                "encryption": {
                    "cli_example": "aws lambda update-function-configuration --function-name myfunction --kms-key-arn arn:aws:kms:region:account:key/key-id",
                    "notes": "Use KMS to encrypt environment variables. Store secrets in Secrets Manager."
                }
            },
            "EC2": {
                "scaling": {
                    "cli_example": "aws autoscaling create-auto-scaling-group --auto-scaling-group-name myasg --launch-template LaunchTemplateName=mytemplate --min-size 2 --max-size 10 --desired-capacity 2",
                    "notes": "Create launch template first. Configure health checks and scaling policies."
                },
                "monitoring_alerting": {
                    "cli_example": "aws ec2 monitor-instances --instance-ids i-1234567890abcdef0",
                    "notes": "Enable detailed monitoring for 1-minute metrics. Standard monitoring is 5-minute intervals."
                }
            }
        }
    
    def generate_guidance(
        self,
        capability: str,
        services: List[str],
        architecture_context: Optional[Dict[str, Any]] = None
    ) -> ImplementationGuidance:
        """
        Generate detailed implementation guidance for a capability.
        
        Args:
            capability: Capability name (e.g., "encryption", "backup_recovery")
            services: List of affected services
            architecture_context: Optional context about the architecture
            
        Returns:
            Complete implementation guidance with steps and estimates
        """
        logger.info(f"Generating implementation guidance for capability: {capability}")
        
        # Get base template
        template = self.capability_templates.get(capability)
        if not template:
            logger.warning(f"No template found for capability: {capability}")
            return self._generate_generic_guidance(capability, services)
        
        # Generate customized steps
        steps = []
        for idx, step_template in enumerate(template["steps"], 1):
            step = self._customize_step(
                step_template,
                services,
                idx,
                architecture_context
            )
            steps.append(step)
        
        # Calculate effort and score improvement
        effort = template.get("effort", EffortLevel.MEDIUM)
        estimated_time = template.get("estimated_time", "3-6 hours")
        score_improvement = self._estimate_score_improvement(capability, services)
        
        guidance = ImplementationGuidance(
            steps=steps,
            estimated_effort=estimated_time,
            prerequisites=template.get("prerequisites", []),
            testing_guidance=template.get("testing", ""),
            rollback_plan=template.get("rollback", ""),
            expected_score_improvement=score_improvement
        )
        
        logger.info(f"Generated {len(steps)} implementation steps for {capability}")
        return guidance
    
    def _customize_step(
        self,
        step_template: Dict[str, Any],
        services: List[str],
        step_number: int,
        architecture_context: Optional[Dict[str, Any]]
    ) -> ImplementationStep:
        """
        Customize a step template for specific services.
        
        Args:
            step_template: Step template dictionary
            services: List of affected services
            step_number: Step number in sequence
            architecture_context: Optional architecture context
            
        Returns:
            Customized implementation step
        """
        # Get primary service for customization
        primary_service = services[0] if services else None
        
        # Customize CLI commands
        cli_commands = []
        if "cli_template" in step_template and primary_service:
            # Get service-specific CLI example if available
            service_custom = self.service_customizations.get(primary_service, {})
            capability_custom = service_custom.get(step_template.get("title", "").lower().replace(" ", "_"))
            
            if capability_custom and "cli_example" in capability_custom:
                cli_commands.append(capability_custom["cli_example"])
            else:
                # Use template
                cli_commands.append(step_template["cli_template"])
        
        # Customize console instructions
        console_instructions = step_template.get("console", "")
        if primary_service and console_instructions:
            console_instructions = console_instructions.replace("{service}", primary_service)
        
        # Add service-specific notes to description
        description = step_template["description"]
        if primary_service:
            service_custom = self.service_customizations.get(primary_service, {})
            capability_custom = service_custom.get(step_template.get("title", "").lower().replace(" ", "_"))
            if capability_custom and "notes" in capability_custom:
                description += f"\n\nNote: {capability_custom['notes']}"
        
        return ImplementationStep(
            step_number=step_number,
            title=step_template["title"],
            description=description,
            aws_cli_commands=cli_commands,
            console_instructions=console_instructions,
            terraform_example="",  # Could be added in future
            validation=step_template.get("validation", "")
        )
    
    def _estimate_score_improvement(
        self,
        capability: str,
        services: List[str]
    ) -> float:
        """
        Estimate score improvement from implementing a capability.
        
        Args:
            capability: Capability name
            services: List of affected services
            
        Returns:
            Estimated score improvement (0-10 scale)
        """
        # Base improvements by capability importance
        base_improvements = {
            "encryption": 8.0,
            "backup_recovery": 7.0,
            "monitoring_alerting": 6.0,
            "scaling": 6.0,
            "identity_access": 8.0,
            "network_security": 7.0,
            "managed_services": 5.0
        }
        
        base = base_improvements.get(capability, 5.0)
        
        # Adjust based on number of services affected
        service_multiplier = min(len(services) * 0.1, 0.5)  # Up to 50% boost
        
        return min(base * (1 + service_multiplier), 10.0)
    
    def _generate_generic_guidance(
        self,
        capability: str,
        services: List[str]
    ) -> ImplementationGuidance:
        """
        Generate generic guidance when no template is available.
        
        Args:
            capability: Capability name
            services: List of affected services
            
        Returns:
            Generic implementation guidance
        """
        steps = [
            ImplementationStep(
                step_number=1,
                title=f"Research {capability} implementation",
                description=f"Review AWS documentation for implementing {capability} with {', '.join(services[:3])}",
                validation="Document implementation approach"
            ),
            ImplementationStep(
                step_number=2,
                title=f"Implement {capability}",
                description=f"Configure {capability} for affected services",
                validation="Verify capability is functioning as expected"
            ),
            ImplementationStep(
                step_number=3,
                title="Test and validate",
                description="Test the implementation in non-production environment",
                validation="Confirm all functionality works correctly"
            )
        ]
        
        return ImplementationGuidance(
            steps=steps,
            estimated_effort="4-8 hours",
            prerequisites=["Review AWS documentation", "Plan implementation approach"],
            testing_guidance="Test in non-production environment before production deployment",
            rollback_plan="Document current configuration before making changes",
            expected_score_improvement=5.0
        )
