"""AWS Documentation and Best Practices Client

This module provides integration with AWS documentation, best practices,
and compliance frameworks for comprehensive WAFR assessments.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from .core.logger import setup_logger
from .core.error_handler import AWSIntegrationError, handle_graceful_degradation

logger = setup_logger(__name__)


class AWSDocumentationClient:
    """
    Client for accessing AWS documentation and best practices.
    
    Provides real-time access to AWS service documentation, best practices,
    and compliance framework mappings for accurate WAFR assessments.
    """
    
    def __init__(self):
        """Initialize AWS documentation client."""
        self.base_urls = {
            "docs": "https://docs.aws.amazon.com",
            "wellarchitected": "https://docs.aws.amazon.com/wellarchitected/latest/framework",
            "architecture_center": "https://aws.amazon.com/architecture",
            "whitepapers": "https://docs.aws.amazon.com/whitepapers/latest"
        }
        
        # Cache for documentation to avoid repeated requests
        self.doc_cache = {}
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours
        
        # Load built-in documentation mappings
        self.service_docs = self._load_service_documentation_mappings()
        self.best_practices = self._load_best_practices_mappings()
        self.compliance_frameworks = self._load_compliance_mappings()
        
        logger.info("Initialized AWS Documentation Client")
    
    async def get_service_documentation(self, service: str, topic: str = "overview") -> Dict[str, Any]:
        """
        Get AWS service documentation.
        
        Args:
            service: AWS service name (e.g., "ec2", "s3", "lambda")
            topic: Documentation topic (overview, security, best_practices, etc.)
            
        Returns:
            Service documentation with links and content
        """
        try:
            logger.info(f"Retrieving documentation for {service} - {topic}")
            
            cache_key = f"{service}_{topic}"
            
            # Check cache first
            if self._is_cache_valid(cache_key):
                logger.info(f"Returning cached documentation for {service}")
                return self.doc_cache[cache_key]["data"]
            
            # Get service documentation mapping
            service_info = self.service_docs.get(service.lower(), {})
            if not service_info:
                return self._get_fallback_documentation(service, topic)
            
            # Build documentation response
            documentation = {
                "service": service,
                "topic": topic,
                "last_updated": datetime.utcnow().isoformat(),
                "documentation_links": self._build_documentation_links(service, topic, service_info),
                "best_practices": self._get_service_best_practices(service),
                "security_guidance": self._get_security_guidance(service),
                "cost_optimization": self._get_cost_optimization_guidance(service),
                "compliance_notes": self._get_compliance_notes(service)
            }
            
            # Cache the result
            self._cache_documentation(cache_key, documentation)
            
            logger.info(f"Retrieved documentation for {service} with {len(documentation['documentation_links'])} links")
            return documentation
            
        except Exception as e:
            logger.error(f"Error retrieving documentation for {service}: {e}")
            return handle_graceful_degradation(e, "service_documentation", {
                "service": service,
                "topic": topic,
                "error": str(e),
                "documentation_links": []
            })
    
    async def get_best_practices(self, pillar: str, services: List[str]) -> Dict[str, Any]:
        """
        Get best practices for specific WAFR pillar and services.
        
        Args:
            pillar: WAFR pillar name
            services: List of AWS services
            
        Returns:
            Best practices guidance with implementation details
        """
        try:
            logger.info(f"Retrieving best practices for {pillar} pillar with {len(services)} services")
            
            pillar_practices = self.best_practices.get(pillar.lower(), {})
            
            best_practices = {
                "pillar": pillar,
                "services": services,
                "last_updated": datetime.utcnow().isoformat(),
                "general_practices": pillar_practices.get("general", []),
                "service_specific": {},
                "implementation_guides": [],
                "aws_documentation_links": []
            }
            
            # Get service-specific best practices
            for service in services:
                service_practices = pillar_practices.get("services", {}).get(service.lower(), [])
                if service_practices:
                    best_practices["service_specific"][service] = service_practices
            
            # Add pillar-specific documentation links
            best_practices["aws_documentation_links"] = self._get_pillar_documentation_links(pillar)
            
            # Add implementation guides
            best_practices["implementation_guides"] = self._get_implementation_guides(pillar, services)
            
            logger.info(f"Retrieved {len(best_practices['general_practices'])} general practices for {pillar}")
            return best_practices
            
        except Exception as e:
            logger.error(f"Error retrieving best practices for {pillar}: {e}")
            return handle_graceful_degradation(e, "best_practices", {
                "pillar": pillar,
                "services": services,
                "error": str(e),
                "general_practices": []
            })
    
    async def get_compliance_mapping(self, framework: str, services: List[str]) -> Dict[str, Any]:
        """
        Map services to compliance framework requirements.
        
        Args:
            framework: Compliance framework (SOC2, HIPAA, PCI-DSS, GDPR)
            services: List of AWS services
            
        Returns:
            Compliance mapping with requirements and controls
        """
        try:
            logger.info(f"Retrieving compliance mapping for {framework} with {len(services)} services")
            
            framework_info = self.compliance_frameworks.get(framework.upper(), {})
            
            compliance_mapping = {
                "framework": framework,
                "services": services,
                "last_updated": datetime.utcnow().isoformat(),
                "framework_overview": framework_info.get("overview", ""),
                "service_mappings": {},
                "required_controls": [],
                "aws_compliance_resources": framework_info.get("aws_resources", [])
            }
            
            # Map each service to framework requirements
            for service in services:
                service_mapping = self._get_service_compliance_mapping(service, framework, framework_info)
                if service_mapping:
                    compliance_mapping["service_mappings"][service] = service_mapping
            
            # Get required controls
            compliance_mapping["required_controls"] = framework_info.get("controls", [])
            
            logger.info(f"Mapped {len(compliance_mapping['service_mappings'])} services to {framework}")
            return compliance_mapping
            
        except Exception as e:
            logger.error(f"Error retrieving compliance mapping for {framework}: {e}")
            return handle_graceful_degradation(e, "compliance_mapping", {
                "framework": framework,
                "services": services,
                "error": str(e),
                "service_mappings": {}
            })
    
    def _load_service_documentation_mappings(self) -> Dict[str, Any]:
        """Load service documentation mappings."""
        
        return {
            "ec2": {
                "service_name": "Amazon EC2",
                "base_url": "https://docs.aws.amazon.com/ec2/latest/userguide",
                "topics": {
                    "overview": "/concepts.html",
                    "security": "/ec2-security.html",
                    "best_practices": "/ec2-best-practices.html",
                    "monitoring": "/monitoring_ec2.html"
                }
            },
            "s3": {
                "service_name": "Amazon S3",
                "base_url": "https://docs.aws.amazon.com/s3/latest/userguide",
                "topics": {
                    "overview": "/Welcome.html",
                    "security": "/security.html",
                    "best_practices": "/security-best-practices.html",
                    "cost_optimization": "/optimizing-costs.html"
                }
            },
            "lambda": {
                "service_name": "AWS Lambda",
                "base_url": "https://docs.aws.amazon.com/lambda/latest/dg",
                "topics": {
                    "overview": "/welcome.html",
                    "security": "/lambda-security.html",
                    "best_practices": "/best-practices.html",
                    "performance": "/performance.html"
                }
            },
            "rds": {
                "service_name": "Amazon RDS",
                "base_url": "https://docs.aws.amazon.com/rds/latest/userguide",
                "topics": {
                    "overview": "/Welcome.html",
                    "security": "/UsingWithRDS.html",
                    "best_practices": "/CHAP_BestPractices.html",
                    "backup": "/CHAP_CommonTasks.BackupRestore.html"
                }
            },
            "iam": {
                "service_name": "AWS IAM",
                "base_url": "https://docs.aws.amazon.com/iam/latest/userguide",
                "topics": {
                    "overview": "/introduction.html",
                    "security": "/best-practices.html",
                    "policies": "/access_policies.html",
                    "roles": "/id_roles.html"
                }
            },
            "vpc": {
                "service_name": "Amazon VPC",
                "base_url": "https://docs.aws.amazon.com/vpc/latest/userguide",
                "topics": {
                    "overview": "/what-is-amazon-vpc.html",
                    "security": "/VPC_Security.html",
                    "best_practices": "/vpc-security-best-practices.html",
                    "networking": "/VPC_Networking.html"
                }
            }
        }
    
    def _load_best_practices_mappings(self) -> Dict[str, Any]:
        """Load best practices mappings by pillar."""
        
        return {
            "operational_excellence": {
                "general": [
                    "Implement Infrastructure as Code (IaC)",
                    "Use version control for all configurations",
                    "Automate deployment processes",
                    "Implement comprehensive monitoring and logging",
                    "Establish incident response procedures"
                ],
                "services": {
                    "ec2": [
                        "Use Auto Scaling groups for resilience",
                        "Implement proper tagging strategy",
                        "Use Systems Manager for patch management"
                    ],
                    "lambda": [
                        "Implement proper error handling",
                        "Use environment variables for configuration",
                        "Monitor function performance and errors"
                    ]
                }
            },
            "security": {
                "general": [
                    "Implement defense in depth",
                    "Use least privilege access",
                    "Enable encryption at rest and in transit",
                    "Implement strong identity foundation",
                    "Automate security best practices"
                ],
                "services": {
                    "s3": [
                        "Enable bucket encryption",
                        "Configure bucket policies",
                        "Enable access logging",
                        "Use versioning for critical data"
                    ],
                    "iam": [
                        "Use roles instead of users for applications",
                        "Implement MFA for privileged operations",
                        "Regularly rotate access keys",
                        "Use policy conditions for additional security"
                    ]
                }
            },
            "reliability": {
                "general": [
                    "Design for failure",
                    "Implement fault isolation",
                    "Use multiple Availability Zones",
                    "Implement automated recovery",
                    "Test recovery procedures regularly"
                ],
                "services": {
                    "rds": [
                        "Enable Multi-AZ deployments",
                        "Configure automated backups",
                        "Use read replicas for scaling",
                        "Monitor database performance"
                    ],
                    "ec2": [
                        "Distribute instances across AZs",
                        "Use Elastic Load Balancing",
                        "Implement health checks",
                        "Use Auto Scaling for resilience"
                    ]
                }
            },
            "performance_efficiency": {
                "general": [
                    "Use data-driven approach for architecture decisions",
                    "Review and test regularly",
                    "Monitor performance continuously",
                    "Use managed services when possible"
                ],
                "services": {
                    "lambda": [
                        "Right-size memory allocation",
                        "Minimize cold starts",
                        "Use provisioned concurrency when needed",
                        "Optimize function code"
                    ]
                }
            },
            "cost_optimization": {
                "general": [
                    "Implement cost awareness",
                    "Use appropriate pricing models",
                    "Right-size resources",
                    "Monitor and analyze costs regularly"
                ],
                "services": {
                    "ec2": [
                        "Use Reserved Instances for predictable workloads",
                        "Consider Spot Instances for fault-tolerant workloads",
                        "Right-size instances based on utilization",
                        "Use Auto Scaling to match capacity with demand"
                    ]
                }
            },
            "sustainability": {
                "general": [
                    "Optimize resource utilization",
                    "Use managed services to reduce overhead",
                    "Choose efficient architectures",
                    "Monitor and optimize regularly"
                ]
            }
        }
    
    def _load_compliance_mappings(self) -> Dict[str, Any]:
        """Load compliance framework mappings."""
        
        return {
            "SOC2": {
                "overview": "SOC 2 Type II compliance for security, availability, processing integrity, confidentiality, and privacy",
                "controls": [
                    "Access controls and user management",
                    "System monitoring and logging",
                    "Data encryption and protection",
                    "Incident response procedures",
                    "Change management processes"
                ],
                "aws_resources": [
                    "https://aws.amazon.com/compliance/soc/",
                    "https://docs.aws.amazon.com/audit-manager/latest/userguide/SOC2.html"
                ]
            },
            "HIPAA": {
                "overview": "Health Insurance Portability and Accountability Act compliance for healthcare data",
                "controls": [
                    "Administrative safeguards",
                    "Physical safeguards", 
                    "Technical safeguards",
                    "Access controls",
                    "Audit controls"
                ],
                "aws_resources": [
                    "https://aws.amazon.com/compliance/hipaa-compliance/",
                    "https://docs.aws.amazon.com/whitepapers/latest/architecting-hipaa-security-and-compliance-on-aws/architecting-hipaa-security-and-compliance-on-aws.html"
                ]
            },
            "PCI-DSS": {
                "overview": "Payment Card Industry Data Security Standard for payment card data protection",
                "controls": [
                    "Build and maintain secure networks",
                    "Protect cardholder data",
                    "Maintain vulnerability management program",
                    "Implement strong access control measures",
                    "Regularly monitor and test networks"
                ],
                "aws_resources": [
                    "https://aws.amazon.com/compliance/pci-dss-level-1-faqs/",
                    "https://docs.aws.amazon.com/whitepapers/latest/pci-dss-scoping-aws/pci-dss-scoping-aws.html"
                ]
            },
            "GDPR": {
                "overview": "General Data Protection Regulation for EU data protection and privacy",
                "controls": [
                    "Data protection by design and by default",
                    "Consent management",
                    "Data subject rights",
                    "Data breach notification",
                    "Privacy impact assessments"
                ],
                "aws_resources": [
                    "https://aws.amazon.com/compliance/gdpr-center/",
                    "https://docs.aws.amazon.com/whitepapers/latest/navigating-gdpr-compliance/navigating-gdpr-compliance.html"
                ]
            }
        }
    
    def _build_documentation_links(self, service: str, topic: str, service_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build documentation links for service and topic."""
        
        links = []
        base_url = service_info.get("base_url", "")
        topics = service_info.get("topics", {})
        
        # Add main topic link
        if topic in topics:
            links.append({
                "title": f"{service_info.get('service_name', service)} - {topic.title()}",
                "url": f"{base_url}{topics[topic]}",
                "type": "primary"
            })
        
        # Add related links
        for topic_name, topic_path in topics.items():
            if topic_name != topic:
                links.append({
                    "title": f"{service_info.get('service_name', service)} - {topic_name.title()}",
                    "url": f"{base_url}{topic_path}",
                    "type": "related"
                })
        
        return links
    
    def _get_service_best_practices(self, service: str) -> List[str]:
        """Get best practices for a specific service."""
        
        practices = []
        for pillar_practices in self.best_practices.values():
            service_practices = pillar_practices.get("services", {}).get(service.lower(), [])
            practices.extend(service_practices)
        
        return list(set(practices))  # Remove duplicates
    
    def _get_security_guidance(self, service: str) -> List[str]:
        """Get security guidance for a service."""
        
        security_practices = self.best_practices.get("security", {})
        return security_practices.get("services", {}).get(service.lower(), [])
    
    def _get_cost_optimization_guidance(self, service: str) -> List[str]:
        """Get cost optimization guidance for a service."""
        
        cost_practices = self.best_practices.get("cost_optimization", {})
        return cost_practices.get("services", {}).get(service.lower(), [])
    
    def _get_compliance_notes(self, service: str) -> List[str]:
        """Get compliance notes for a service."""
        
        # This would be expanded with service-specific compliance guidance
        return [
            f"Ensure {service} configuration meets your compliance requirements",
            f"Review {service} audit logs regularly",
            f"Implement appropriate access controls for {service}"
        ]
    
    def _get_pillar_documentation_links(self, pillar: str) -> List[Dict[str, str]]:
        """Get documentation links for a WAFR pillar."""
        
        pillar_slug = pillar.lower().replace("_", "-")
        
        return [
            {
                "title": f"AWS Well-Architected Framework - {pillar.replace('_', ' ').title()} Pillar",
                "url": f"{self.base_urls['wellarchitected']}/{pillar_slug}-pillar.html",
                "type": "primary"
            },
            {
                "title": f"{pillar.replace('_', ' ').title()} Best Practices",
                "url": f"{self.base_urls['wellarchitected']}/{pillar_slug}-pillar.html#best-practices",
                "type": "best_practices"
            }
        ]
    
    def _get_implementation_guides(self, pillar: str, services: List[str]) -> List[Dict[str, str]]:
        """Get implementation guides for pillar and services."""
        
        guides = []
        
        # Add pillar-specific guides
        guides.append({
            "title": f"Implementing {pillar.replace('_', ' ').title()} Best Practices",
            "url": f"{self.base_urls['architecture_center']}/well-architected/{pillar.lower()}",
            "type": "implementation"
        })
        
        # Add service-specific guides
        for service in services:
            guides.append({
                "title": f"{service.upper()} Best Practices Guide",
                "url": f"{self.base_urls['architecture_center']}/browse?f1=service%3A{service.lower()}",
                "type": "service_guide"
            })
        
        return guides
    
    def _get_service_compliance_mapping(self, service: str, framework: str, framework_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get compliance mapping for a specific service."""
        
        # This would be expanded with detailed service-to-compliance mappings
        return {
            "service": service,
            "applicable_controls": framework_info.get("controls", [])[:3],  # First 3 controls as example
            "implementation_notes": [
                f"Configure {service} according to {framework} requirements",
                f"Enable appropriate logging and monitoring for {service}",
                f"Implement access controls for {service} resources"
            ],
            "aws_guidance": f"https://docs.aws.amazon.com/{service.lower()}/latest/userguide/compliance.html"
        }
    
    def _get_fallback_documentation(self, service: str, topic: str) -> Dict[str, Any]:
        """Get fallback documentation when service mapping is not available."""
        
        return {
            "service": service,
            "topic": topic,
            "last_updated": datetime.utcnow().isoformat(),
            "documentation_links": [
                {
                    "title": f"AWS {service.upper()} Documentation",
                    "url": f"https://docs.aws.amazon.com/{service.lower()}/",
                    "type": "primary"
                }
            ],
            "best_practices": [
                f"Follow AWS best practices for {service}",
                f"Implement proper security controls for {service}",
                f"Monitor {service} performance and costs"
            ],
            "security_guidance": [
                f"Secure {service} according to AWS recommendations"
            ],
            "cost_optimization": [
                f"Optimize {service} costs using AWS guidance"
            ],
            "compliance_notes": [
                f"Ensure {service} meets your compliance requirements"
            ]
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached documentation is still valid."""
        
        if cache_key not in self.doc_cache:
            return False
        
        cached_time = self.doc_cache[cache_key]["timestamp"]
        return datetime.utcnow() - cached_time < self.cache_ttl
    
    def _cache_documentation(self, cache_key: str, documentation: Dict[str, Any]) -> None:
        """Cache documentation with timestamp."""
        
        self.doc_cache[cache_key] = {
            "timestamp": datetime.utcnow(),
            "data": documentation
        }
