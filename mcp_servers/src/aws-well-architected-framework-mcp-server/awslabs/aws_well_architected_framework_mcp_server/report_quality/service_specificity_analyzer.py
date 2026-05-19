"""
Service Specificity Analyzer for WAFR Report Quality Enhancement.

This module identifies which specific services need improvements rather than
listing all services generically. It provides service-specific configuration
recommendations.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from ..core.logger import WAFRLogger
from ..core.service_categorizer import service_categorizer, ServiceCategory
from .models import ServiceTargeting


class ServiceSpecificityAnalyzer:
    """
    Analyzes which specific services need capabilities.
    
    This component identifies:
    1. Services that should have a capability but don't (configuration gaps)
    2. Services that need to be added to provide a capability (service gaps)
    3. Specific configuration changes needed per service
    
    Example:
        analyzer = ServiceSpecificityAnalyzer()
        
        targeting = analyzer.identify_affected_services(
            capability="backup_recovery",
            all_services=["Lambda", "DynamoDB", "RDS", "S3", "IAM"],
            detected_capabilities={"encryption": ["S3", "RDS"]}
        )
        # Returns: ServiceTargeting with specific services needing backup
    """
    
    # Service-capability mapping: which service types should have which capabilities
    SERVICE_CAPABILITY_REQUIREMENTS = {
        "backup_recovery": {
            "applicable_categories": [
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE
            ],
            "not_applicable_categories": [
                ServiceCategory.COMPUTE,  # Lambda doesn't need backup
                ServiceCategory.SECURITY,  # IAM doesn't need backup
                ServiceCategory.NETWORKING,  # VPC doesn't need backup
                ServiceCategory.MONITORING
            ],
            "configuration_templates": {
                "database": "Enable automated backups with {retention_days} day retention and point-in-time recovery",
                "storage": "Enable versioning and configure lifecycle policies for backup retention"
            }
        },
        "encryption": {
            "applicable_categories": [
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE,
                ServiceCategory.COMPUTE
            ],
            "not_applicable_categories": [
                ServiceCategory.MONITORING,
                ServiceCategory.NETWORKING
            ],
            "configuration_templates": {
                "database": "Enable encryption at rest using AWS KMS customer managed keys",
                "storage": "Enable default encryption with SSE-KMS and enforce encryption in transit",
                "compute": "Encrypt EBS volumes and enable encryption for data in transit"
            }
        },
        "monitoring_alerting": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE,
                ServiceCategory.NETWORKING
            ],
            "not_applicable_categories": [],
            "configuration_templates": {
                "compute": "Configure CloudWatch metrics, alarms for CPU/memory, and enable detailed monitoring",
                "database": "Enable Performance Insights and configure alarms for connection count and latency",
                "storage": "Configure metrics for request rates, error rates, and storage capacity",
                "networking": "Enable VPC Flow Logs and configure alarms for traffic anomalies"
            }
        },
        "scaling": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE
            ],
            "not_applicable_categories": [
                ServiceCategory.STORAGE,  # S3 scales automatically
                ServiceCategory.SECURITY,
                ServiceCategory.MONITORING
            ],
            "configuration_templates": {
                "compute": "Configure Auto Scaling groups with target tracking policies",
                "database": "Enable auto-scaling for read replicas and configure capacity units"
            }
        },
        "caching": {
            "applicable_categories": [
                ServiceCategory.DATABASE,
                ServiceCategory.NETWORKING,  # CloudFront
                ServiceCategory.COMPUTE
            ],
            "not_applicable_categories": [
                ServiceCategory.SECURITY,
                ServiceCategory.MONITORING,
                ServiceCategory.STORAGE
            ],
            "configuration_templates": {
                "database": "Implement ElastiCache or DAX for frequently accessed data",
                "networking": "Configure CloudFront with appropriate cache behaviors and TTLs",
                "compute": "Implement application-level caching for API responses"
            }
        },
        "redundancy": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE
            ],
            "not_applicable_categories": [
                ServiceCategory.SECURITY,
                ServiceCategory.MONITORING
            ],
            "configuration_templates": {
                "compute": "Deploy across multiple Availability Zones with load balancing",
                "database": "Enable Multi-AZ deployment for high availability",
                "storage": "Use S3 Standard storage class with cross-region replication"
            }
        },
        "identity_access": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE,
                ServiceCategory.NETWORKING
            ],
            "not_applicable_categories": [],
            "configuration_templates": {
                "compute": "Use IAM roles for EC2/Lambda with least privilege policies",
                "database": "Implement IAM database authentication and fine-grained access control",
                "storage": "Configure bucket policies and IAM policies with least privilege",
                "networking": "Implement security groups and NACLs with least privilege rules"
            }
        },
        "network_security": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.NETWORKING
            ],
            "not_applicable_categories": [
                ServiceCategory.STORAGE,  # S3 doesn't use VPC
                ServiceCategory.MONITORING
            ],
            "configuration_templates": {
                "compute": "Deploy in private subnets with security groups restricting inbound traffic",
                "database": "Place in private subnets with security groups allowing only application access",
                "networking": "Configure VPC with public/private subnets and NAT gateways"
            }
        },
        "observability": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.NETWORKING,
                ServiceCategory.INTEGRATION
            ],
            "not_applicable_categories": [],
            "configuration_templates": {
                "compute": "Enable X-Ray tracing and structured logging to CloudWatch",
                "database": "Enable query logging and performance monitoring",
                "networking": "Enable VPC Flow Logs and API Gateway logging",
                "integration": "Enable CloudWatch Logs for Lambda and Step Functions"
            }
        },
        "managed_services": {
            "applicable_categories": [
                ServiceCategory.COMPUTE,
                ServiceCategory.DATABASE,
                ServiceCategory.STORAGE
            ],
            "not_applicable_categories": [],
            "configuration_templates": {
                "compute": "Migrate to Lambda or Fargate for serverless compute",
                "database": "Use DynamoDB or Aurora Serverless for managed database",
                "storage": "Use S3 for object storage instead of self-managed solutions"
            }
        }
    }
    
    def __init__(self):
        """Initialize the service specificity analyzer."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("ServiceSpecificityAnalyzer initialized")
    
    def identify_affected_services(
        self,
        capability: str,
        all_services: List[str],
        detected_capabilities: Dict[str, List[str]]
    ) -> ServiceTargeting:
        """
        Identify specific services that need a capability.
        
        Args:
            capability: The capability being recommended
            all_services: All services in the architecture
            detected_capabilities: Map of capabilities to services providing them
            
        Returns:
            ServiceTargeting with specific services and configuration changes
        """
        self.logger.info(
            f"Identifying affected services for capability: {capability}"
        )
        
        # Get capability requirements
        requirements = self.SERVICE_CAPABILITY_REQUIREMENTS.get(capability, {})
        if not requirements:
            self.logger.warning(
                f"No service requirements defined for capability: {capability}"
            )
            return ServiceTargeting()
        
        # Categorize all services
        categorized_services = service_categorizer.categorize_services(all_services)
        
        # Get services that already have this capability
        services_with_capability = detected_capabilities.get(capability, [])
        services_with_capability_set = set(services_with_capability)
        
        # Identify services that should have this capability
        services_needing_capability = []
        configuration_changes = {}
        
        applicable_categories = requirements.get("applicable_categories", [])
        not_applicable_categories = requirements.get("not_applicable_categories", [])
        config_templates = requirements.get("configuration_templates", {})
        
        for categorized_service in categorized_services:
            service_name = categorized_service.service_name
            
            # Skip if service already has the capability
            if service_name in services_with_capability_set:
                continue
            
            # Check if service should have this capability
            should_have_capability = False
            primary_category = None
            
            for category in categorized_service.categories:
                if category in applicable_categories:
                    should_have_capability = True
                    primary_category = category
                    break
                elif category in not_applicable_categories:
                    should_have_capability = False
                    break
            
            if should_have_capability and primary_category:
                services_needing_capability.append(service_name)
                
                # Generate specific configuration change
                category_key = primary_category.value
                if category_key in config_templates:
                    config_change = config_templates[category_key]
                    # Customize for specific service if needed
                    config_change = self._customize_configuration(
                        config_change,
                        service_name,
                        capability
                    )
                    configuration_changes[service_name] = config_change
        
        # Identify services to add (if capability requires new services)
        services_to_add = self._identify_services_to_add(
            capability,
            all_services,
            services_needing_capability
        )
        
        self.logger.info(
            f"Capability {capability}: {len(services_needing_capability)} services need it, "
            f"{len(services_with_capability)} already have it, "
            f"{len(services_to_add)} services to add"
        )
        
        return ServiceTargeting(
            services_needing_capability=services_needing_capability,
            services_with_capability=services_with_capability,
            services_to_add=services_to_add,
            configuration_changes=configuration_changes
        )
    
    def _customize_configuration(
        self,
        template: str,
        service_name: str,
        capability: str
    ) -> str:
        """
        Customize configuration template for specific service.
        
        Args:
            template: Configuration template
            service_name: Name of the service
            capability: Capability being configured
            
        Returns:
            Customized configuration string
        """
        # Service-specific customizations
        service_lower = service_name.lower()
        
        # Customize based on service type
        if "dynamodb" in service_lower:
            if "backup" in capability:
                return "Enable point-in-time recovery (PITR) for DynamoDB table"
            elif "encryption" in capability:
                return "Enable encryption at rest using AWS managed or customer managed KMS keys"
        
        elif "rds" in service_lower or "aurora" in service_lower:
            if "backup" in capability:
                return "Configure automated backups with 7-30 day retention and enable automated snapshots"
            elif "encryption" in capability:
                return "Enable encryption at rest for RDS instance using KMS"
        
        elif "s3" in service_lower:
            if "backup" in capability:
                return "Enable S3 versioning and configure lifecycle policies for backup retention"
            elif "encryption" in capability:
                return "Enable default bucket encryption with SSE-KMS and enforce HTTPS"
        
        elif "lambda" in service_lower:
            if "monitoring" in capability or "observability" in capability:
                return "Enable X-Ray tracing and configure CloudWatch Logs with appropriate retention"
            elif "encryption" in capability:
                return "Encrypt environment variables using KMS and enable VPC encryption"
        
        # Return template with service name if no specific customization
        return template.replace("{service}", service_name)
    
    def _identify_services_to_add(
        self,
        capability: str,
        existing_services: List[str],
        services_needing_capability: List[str]
    ) -> List[str]:
        """
        Identify new services that should be added to provide a capability.
        
        Args:
            capability: Capability name
            existing_services: Services already in architecture
            services_needing_capability: Services that need the capability
            
        Returns:
            List of services to add
        """
        services_to_add = []
        existing_services_lower = [s.lower() for s in existing_services]
        
        # Capability-specific service recommendations
        if capability == "monitoring_alerting" or capability == "observability":
            if not any("cloudwatch" in s for s in existing_services_lower):
                services_to_add.append("CloudWatch")
            if not any("x-ray" in s or "xray" in s for s in existing_services_lower):
                services_to_add.append("X-Ray")
        
        elif capability == "caching":
            has_cache = any(
                "elasticache" in s or "dax" in s or "cloudfront" in s
                for s in existing_services_lower
            )
            if not has_cache:
                # Recommend based on existing services
                if any("dynamodb" in s for s in existing_services_lower):
                    services_to_add.append("DAX")
                else:
                    services_to_add.append("ElastiCache")
        
        elif capability == "backup_recovery":
            if not any("backup" in s for s in existing_services_lower):
                services_to_add.append("AWS Backup")
        
        elif capability == "encryption":
            if not any("kms" in s for s in existing_services_lower):
                services_to_add.append("AWS KMS")
        
        elif capability == "identity_access":
            if not any("iam" in s for s in existing_services_lower):
                services_to_add.append("IAM")
        
        elif capability == "network_security":
            if not any("vpc" in s for s in existing_services_lower):
                services_to_add.append("VPC")
            if not any("waf" in s for s in existing_services_lower):
                services_to_add.append("WAF")
        
        return services_to_add
    
    def get_service_priority(
        self,
        service_name: str,
        capability: str,
        all_services: List[str]
    ) -> str:
        """
        Determine priority level for addressing a service's capability gap.
        
        Args:
            service_name: Name of the service
            capability: Capability that's missing
            all_services: All services in architecture
            
        Returns:
            Priority level: "critical", "high", "medium", "low"
        """
        # Categorize the service
        categorized = service_categorizer.categorize_service(service_name)
        
        # Critical priorities
        if capability in ["encryption", "identity_access", "backup_recovery"]:
            if ServiceCategory.DATABASE in categorized.categories:
                return "critical"
            elif ServiceCategory.STORAGE in categorized.categories:
                return "critical"
        
        # High priorities
        if capability in ["monitoring_alerting", "redundancy", "network_security"]:
            if ServiceCategory.COMPUTE in categorized.categories:
                return "high"
            elif ServiceCategory.DATABASE in categorized.categories:
                return "high"
        
        # Medium priorities
        if capability in ["caching", "scaling", "observability"]:
            return "medium"
        
        # Default to medium
        return "medium"
