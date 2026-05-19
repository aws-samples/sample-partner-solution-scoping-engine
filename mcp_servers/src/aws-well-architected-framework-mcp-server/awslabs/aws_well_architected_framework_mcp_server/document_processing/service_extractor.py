"""Service and configuration extraction for WAFR assessments"""

import json
import re
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from ..core.logger import setup_logger
from ..core.error_handler import DocumentProcessingError
from ..models.assessment import AWSService

logger = setup_logger(__name__)


class ServiceExtractor:
    """
    Extract and validate AWS services and configurations from document analysis.
    
    Provides comprehensive service identification, configuration extraction,
    and confidence scoring for WAFR assessments.
    """
    
    def __init__(self):
        """Initialize service extractor with AWS service catalog."""
        self.aws_service_catalog = self._load_aws_service_catalog()
        self.service_patterns = self._build_service_patterns()
        
    def extract_services_and_configurations(
        self,
        claude_analysis: Dict[str, Any],
        document_content: str = None
    ) -> List[AWSService]:
        """
        Extract AWS services and configurations from analysis results.
        
        Args:
            claude_analysis: Claude's analysis results
            document_content: Optional raw document content
            
        Returns:
            List of identified AWS services with configurations
        """
        try:
            logger.info("Extracting AWS services and configurations")
            
            # Extract services from structured analysis
            structured_services = self._extract_from_structured_analysis(claude_analysis)
            
            # Extract services from raw text if available
            text_services = []
            if document_content:
                text_services = self._extract_from_raw_text(document_content)
            
            # Combine and validate services
            all_services = self._combine_and_validate_services(
                structured_services, text_services
            )
            
            # Add configuration details
            enriched_services = self._enrich_with_configurations(
                all_services, claude_analysis, document_content
            )
            
            logger.info(f"Extracted {len(enriched_services)} AWS services")
            return enriched_services
            
        except Exception as e:
            logger.error(f"Error extracting services: {e}")
            raise DocumentProcessingError(f"Service extraction failed: {e}")
    
    def _load_aws_service_catalog(self) -> Dict[str, Any]:
        """Load AWS service catalog for validation."""
        
        try:
            # Try to load from existing catalog file
            catalog_path = Path(__file__).parent.parent / "aws_services_catalog.json"
            if catalog_path.exists():
                with open(catalog_path, 'r') as f:
                    existing_catalog = json.load(f)
                    # Check if it has the expected structure
                    if "services" in existing_catalog and isinstance(existing_catalog["services"], dict):
                        # Convert to our expected format
                        return self._convert_catalog_format(existing_catalog["services"])
        except Exception as e:
            logger.warning(f"Could not load service catalog: {e}")
        
        # Fallback to built-in catalog
        return self._get_builtin_service_catalog()
    
    def _convert_catalog_format(self, services_dict: Dict[str, List[str]]) -> Dict[str, Any]:
        """Convert existing catalog format to expected format."""
        
        converted_catalog = {}
        
        # Group services by category (simplified)
        service_categories = {
            "compute": ["EC2", "Lambda", "ECS", "EKS", "Fargate", "Batch"],
            "storage": ["S3", "EBS", "EFS", "FSx"],
            "database": ["RDS", "DynamoDB", "ElastiCache", "DocumentDB", "Neptune"],
            "networking": ["VPC", "ELB", "ALB", "NLB", "CloudFront", "Route53", "API Gateway"],
            "security": ["IAM", "KMS", "Cognito", "WAF", "Shield", "GuardDuty"]
        }
        
        for category, service_list in service_categories.items():
            converted_catalog[category] = {}
            for service_name in service_list:
                if service_name in services_dict:
                    converted_catalog[category][service_name] = {
                        "full_name": f"Amazon {service_name}" if service_name != "AWS Lambda" else "AWS Lambda",
                        "category": category,
                        "wafr_pillars": ["operational_excellence", "security", "reliability"],
                        "common_configs": ["basic_config"]
                    }
        
        return converted_catalog
    
    def _get_builtin_service_catalog(self) -> Dict[str, Any]:
        """Get built-in AWS service catalog."""
        
        return {
            "compute": {
                "EC2": {
                    "full_name": "Amazon Elastic Compute Cloud",
                    "category": "compute",
                    "wafr_pillars": ["operational_excellence", "security", "reliability", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["instance_type", "security_groups", "key_pairs", "user_data", "storage"]
                },
                "Lambda": {
                    "full_name": "AWS Lambda",
                    "category": "compute",
                    "wafr_pillars": ["operational_excellence", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["runtime", "memory", "timeout", "environment_variables", "triggers"]
                },
                "ECS": {
                    "full_name": "Amazon Elastic Container Service",
                    "category": "compute",
                    "wafr_pillars": ["operational_excellence", "reliability", "performance_efficiency"],
                    "common_configs": ["cluster", "task_definition", "service", "load_balancer"]
                },
                "EKS": {
                    "full_name": "Amazon Elastic Kubernetes Service",
                    "category": "compute",
                    "wafr_pillars": ["operational_excellence", "reliability", "performance_efficiency"],
                    "common_configs": ["cluster", "node_groups", "networking", "logging"]
                }
            },
            "storage": {
                "S3": {
                    "full_name": "Amazon Simple Storage Service",
                    "category": "storage",
                    "wafr_pillars": ["security", "reliability", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["bucket_policy", "encryption", "versioning", "lifecycle", "replication"]
                },
                "EBS": {
                    "full_name": "Amazon Elastic Block Store",
                    "category": "storage",
                    "wafr_pillars": ["reliability", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["volume_type", "size", "encryption", "snapshots"]
                },
                "EFS": {
                    "full_name": "Amazon Elastic File System",
                    "category": "storage",
                    "wafr_pillars": ["reliability", "performance_efficiency"],
                    "common_configs": ["performance_mode", "throughput_mode", "encryption"]
                }
            },
            "database": {
                "RDS": {
                    "full_name": "Amazon Relational Database Service",
                    "category": "database",
                    "wafr_pillars": ["security", "reliability", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["engine", "instance_class", "multi_az", "backup", "encryption"]
                },
                "DynamoDB": {
                    "full_name": "Amazon DynamoDB",
                    "category": "database",
                    "wafr_pillars": ["reliability", "performance_efficiency", "cost_optimization"],
                    "common_configs": ["billing_mode", "capacity", "encryption", "backup", "streams"]
                }
            },
            "networking": {
                "VPC": {
                    "full_name": "Amazon Virtual Private Cloud",
                    "category": "networking",
                    "wafr_pillars": ["security", "reliability"],
                    "common_configs": ["cidr_block", "subnets", "route_tables", "security_groups", "nacls"]
                },
                "ELB": {
                    "full_name": "Elastic Load Balancing",
                    "category": "networking",
                    "wafr_pillars": ["reliability", "performance_efficiency"],
                    "common_configs": ["type", "scheme", "listeners", "target_groups", "health_checks"]
                },
                "CloudFront": {
                    "full_name": "Amazon CloudFront",
                    "category": "networking",
                    "wafr_pillars": ["performance_efficiency", "cost_optimization"],
                    "common_configs": ["origins", "behaviors", "caching", "ssl_certificate"]
                }
            },
            "security": {
                "IAM": {
                    "full_name": "AWS Identity and Access Management",
                    "category": "security",
                    "wafr_pillars": ["security", "operational_excellence"],
                    "common_configs": ["users", "groups", "roles", "policies", "mfa"]
                },
                "KMS": {
                    "full_name": "AWS Key Management Service",
                    "category": "security",
                    "wafr_pillars": ["security"],
                    "common_configs": ["key_policy", "key_rotation", "aliases", "grants"]
                }
            }
        }
    
    def _build_service_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for service identification."""
        
        patterns = {}
        
        for category, services in self.aws_service_catalog.items():
            for service_name, service_info in services.items():
                service_patterns = [
                    service_name.lower(),
                    service_info["full_name"].lower(),
                    f"aws {service_name.lower()}",
                    f"amazon {service_name.lower()}"
                ]
                
                # Add common variations
                if service_name == "EC2":
                    service_patterns.extend([
                        "elastic compute cloud",
                        "ec2 instance",
                        "virtual machine",
                        "compute instance"
                    ])
                elif service_name == "S3":
                    service_patterns.extend([
                        "simple storage service",
                        "object storage",
                        "s3 bucket"
                    ])
                elif service_name == "RDS":
                    service_patterns.extend([
                        "relational database service",
                        "managed database",
                        "rds instance"
                    ])
                
                patterns[service_name] = service_patterns
        
        return patterns
    
    def _extract_from_structured_analysis(
        self,
        claude_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract services from Claude's structured analysis."""
        
        services = []
        extracted_data = claude_analysis.get("extracted_data", {})
        
        # Extract from aws_services section
        aws_services = extracted_data.get("aws_services", [])
        for service_item in aws_services:
            if isinstance(service_item, dict):
                service_name = service_item.get("item", "")
                confidence = service_item.get("confidence", 0.8)
            else:
                service_name = str(service_item)
                confidence = 0.8
            
            # Normalize and validate service name
            normalized_name = self._normalize_service_name(service_name)
            if normalized_name and self._is_valid_aws_service(normalized_name):
                services.append({
                    "service_name": normalized_name,
                    "confidence": confidence,
                    "source": "structured_analysis",
                    "raw_text": service_name
                })
        
        return services
    
    def _extract_from_raw_text(self, document_content: str) -> List[Dict[str, Any]]:
        """Extract services from raw document text using patterns."""
        
        services = []
        content_lower = document_content.lower()
        
        for service_name, patterns in self.service_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pattern, service_name)
                    
                    services.append({
                        "service_name": service_name,
                        "confidence": confidence,
                        "source": "text_pattern",
                        "raw_text": pattern,
                        "pattern_matched": pattern
                    })
                    break  # Only match once per service
        
        return services
    
    def _combine_and_validate_services(
        self,
        structured_services: List[Dict[str, Any]],
        text_services: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine and validate services from different sources."""
        
        # Create a map to combine services by name
        service_map = {}
        
        # Process structured services (higher priority)
        for service in structured_services:
            service_name = service["service_name"]
            service_map[service_name] = service
        
        # Process text services (lower priority, don't override)
        for service in text_services:
            service_name = service["service_name"]
            if service_name not in service_map:
                service_map[service_name] = service
            else:
                # Boost confidence if found in multiple sources
                existing_service = service_map[service_name]
                existing_service["confidence"] = min(1.0, existing_service["confidence"] + 0.1)
                existing_service["sources"] = existing_service.get("sources", [existing_service["source"]])
                if service["source"] not in existing_service["sources"]:
                    existing_service["sources"].append(service["source"])
        
        return list(service_map.values())
    
    def _enrich_with_configurations(
        self,
        services: List[Dict[str, Any]],
        claude_analysis: Dict[str, Any],
        document_content: str = None
    ) -> List[AWSService]:
        """Enrich services with configuration details."""
        
        enriched_services = []
        
        for service_data in services:
            service_name = service_data["service_name"]
            
            # Get service info from catalog
            service_info = self._get_service_info(service_name)
            
            # Extract configurations
            configurations = self._extract_service_configurations(
                service_name, claude_analysis, document_content
            )
            
            # Create AWSService object
            aws_service = AWSService(
                service_name=service_name,
                service_type=service_info.get("category", "unknown"),
                confidence_score=service_data["confidence"],
                identified_from=[service_data["source"]],
                configurations=configurations,
                pillar_relevance=self._get_pillar_relevance(service_name),
                best_practices=self._get_best_practices(service_name),
                potential_issues=self._identify_potential_issues(service_name, configurations)
            )
            
            enriched_services.append(aws_service)
        
        return enriched_services
    
    def _normalize_service_name(self, service_name: str) -> Optional[str]:
        """Normalize service name to standard format."""
        
        service_name = service_name.strip()
        
        # Common normalizations
        normalizations = {
            "amazon ec2": "EC2",
            "elastic compute cloud": "EC2",
            "ec2 instance": "EC2",
            "virtual machine": "EC2",
            "compute instance": "EC2",
            "amazon s3": "S3",
            "simple storage service": "S3",
            "object storage": "S3",
            "s3 bucket": "S3",
            "amazon rds": "RDS",
            "relational database service": "RDS",
            "managed database": "RDS",
            "rds instance": "RDS",
            "aws lambda": "Lambda",
            "lambda function": "Lambda",
            "amazon dynamodb": "DynamoDB",
            "dynamo db": "DynamoDB",
            "amazon vpc": "VPC",
            "virtual private cloud": "VPC",
            "elastic load balancer": "ELB",
            "application load balancer": "ALB",
            "network load balancer": "NLB",
            "amazon cloudfront": "CloudFront",
            "content delivery network": "CloudFront",
            "aws iam": "IAM",
            "identity and access management": "IAM",
            "aws kms": "KMS",
            "key management service": "KMS"
        }
        
        normalized = normalizations.get(service_name.lower())
        if normalized:
            return normalized
        
        # Try direct match with catalog
        for category, services in self.aws_service_catalog.items():
            if service_name.upper() in services:
                return service_name.upper()
        
        return None
    
    def _is_valid_aws_service(self, service_name: str) -> bool:
        """Check if service name is valid AWS service."""
        
        for category, services in self.aws_service_catalog.items():
            if service_name in services:
                return True
        return False
    
    def _calculate_pattern_confidence(self, pattern: str, service_name: str) -> float:
        """Calculate confidence score for pattern match."""
        
        # Base confidence
        confidence = 0.7
        
        # Boost for exact service name matches
        if pattern == service_name.lower():
            confidence = 0.95
        elif pattern.startswith("aws ") or pattern.startswith("amazon "):
            confidence = 0.9
        elif "service" in pattern:
            confidence = 0.85
        
        return confidence
    
    def _get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get service information from catalog."""
        
        for category, services in self.aws_service_catalog.items():
            if service_name in services:
                return services[service_name]
        
        return {"category": "unknown", "wafr_pillars": [], "common_configs": []}
    
    def _extract_service_configurations(
        self,
        service_name: str,
        claude_analysis: Dict[str, Any],
        document_content: str = None
    ) -> Dict[str, Any]:
        """Extract configuration details for specific service."""
        
        configurations = {}
        
        # Get common configurations for this service
        service_info = self._get_service_info(service_name)
        common_configs = service_info.get("common_configs", [])
        
        # Extract from Claude analysis
        raw_analysis = claude_analysis.get("raw_analysis", "")
        
        for config_type in common_configs:
            config_value = self._find_configuration_value(
                service_name, config_type, raw_analysis, document_content
            )
            if config_value:
                configurations[config_type] = config_value
        
        return configurations
    
    def _find_configuration_value(
        self,
        service_name: str,
        config_type: str,
        raw_analysis: str,
        document_content: str = None
    ) -> Optional[str]:
        """Find configuration value in text."""
        
        # Simple pattern matching for common configurations
        text_to_search = f"{raw_analysis} {document_content or ''}"
        text_lower = text_to_search.lower()
        
        # Configuration patterns
        config_patterns = {
            "instance_type": [r"instance[- ]type[:\s]+([a-z0-9]+\.[a-z0-9]+)", r"(t[0-9]\.[a-z0-9]+)", r"(m[0-9]\.[a-z0-9]+)"],
            "memory": [r"memory[:\s]+([0-9]+\s*[gmk]b)", r"([0-9]+\s*gb\s+memory)"],
            "runtime": [r"runtime[:\s]+([a-z0-9\.]+)", r"(python[0-9\.]*)", r"(nodejs[0-9\.]*)", r"(java[0-9]*)"],
            "engine": [r"engine[:\s]+([a-z0-9]+)", r"(mysql)", r"(postgresql)", r"(oracle)"],
            "encryption": [r"encryption[:\s]+([a-z0-9\-]+)", r"(aes-256)", r"(kms)"]
        }
        
        patterns = config_patterns.get(config_type, [])
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _get_pillar_relevance(self, service_name: str) -> Dict[str, List[str]]:
        """Get WAFR pillar relevance for service."""
        
        service_info = self._get_service_info(service_name)
        pillars = service_info.get("wafr_pillars", [])
        
        pillar_relevance = {}
        for pillar in pillars:
            pillar_relevance[pillar] = [f"{service_name} configuration and best practices"]
        
        return pillar_relevance
    
    def _get_best_practices(self, service_name: str) -> List[str]:
        """Get best practices for service."""
        
        # Service-specific best practices
        best_practices_map = {
            "EC2": [
                "Use appropriate instance types for workload",
                "Implement proper security groups",
                "Enable detailed monitoring",
                "Use IAM roles instead of access keys"
            ],
            "S3": [
                "Enable bucket encryption",
                "Configure bucket policies",
                "Enable versioning for critical data",
                "Use lifecycle policies for cost optimization"
            ],
            "RDS": [
                "Enable Multi-AZ for high availability",
                "Configure automated backups",
                "Use encryption at rest",
                "Implement proper security groups"
            ],
            "Lambda": [
                "Right-size memory allocation",
                "Use environment variables for configuration",
                "Implement proper error handling",
                "Monitor function performance"
            ]
        }
        
        return best_practices_map.get(service_name, [
            "Follow AWS Well-Architected Framework principles",
            "Implement proper security controls",
            "Monitor service performance and costs"
        ])
    
    def _identify_potential_issues(
        self,
        service_name: str,
        configurations: Dict[str, Any]
    ) -> List[str]:
        """Identify potential issues based on service and configurations."""
        
        issues = []
        
        # Service-specific issue detection
        if service_name == "EC2":
            if not configurations.get("security_groups"):
                issues.append("Security groups not configured")
            if not configurations.get("instance_type"):
                issues.append("Instance type not specified")
        
        elif service_name == "S3":
            if not configurations.get("encryption"):
                issues.append("Bucket encryption not configured")
            if not configurations.get("bucket_policy"):
                issues.append("Bucket policy not defined")
        
        elif service_name == "RDS":
            if not configurations.get("multi_az"):
                issues.append("Multi-AZ not enabled for high availability")
            if not configurations.get("encryption"):
                issues.append("Database encryption not configured")
        
        return issues
