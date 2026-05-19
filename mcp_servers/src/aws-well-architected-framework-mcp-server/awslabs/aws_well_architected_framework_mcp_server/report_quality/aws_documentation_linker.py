"""
AWS Documentation Linker for WAFR Report Quality Enhancement.

This module provides AWS documentation references for recommendations and pillar sections.
Links are organized by pillar, service, capability, and architectural pattern.
"""

import logging
from typing import List, Dict, Optional
from .models import DocumentationLink

logger = logging.getLogger(__name__)


class AWSDocumentationLinker:
    """
    Provides relevant AWS documentation links for WAFR assessments.
    
    Features:
    - Pillar-specific WAFR documentation
    - Service-specific documentation
    - Capability-specific implementation guides
    - Pattern-specific architecture guides
    - Link relevance scoring and filtering
    """
    
    def __init__(self):
        """Initialize the documentation linker with static link database."""
        self._load_pillar_documentation()
        self._load_service_documentation()
        self._load_capability_documentation()
        self._load_pattern_documentation()
    
    def _load_pillar_documentation(self):
        """Load official WAFR pillar documentation links."""
        self.pillar_docs = {
            "security": [
                DocumentationLink(
                    title="Security Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
                    description="Official AWS Well-Architected Framework Security Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS Security Best Practices",
                    url="https://aws.amazon.com/architecture/security-identity-compliance/",
                    description="AWS security best practices and reference architectures",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="AWS Security Documentation",
                    url="https://docs.aws.amazon.com/security/",
                    description="Comprehensive AWS security documentation hub",
                    relevance="medium",
                    link_type="documentation"
                )
            ],
            "reliability": [
                DocumentationLink(
                    title="Reliability Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
                    description="Official AWS Well-Architected Framework Reliability Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS Reliability Best Practices",
                    url="https://aws.amazon.com/architecture/reliability/",
                    description="AWS reliability best practices and patterns",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="Disaster Recovery on AWS",
                    url="https://aws.amazon.com/disaster-recovery/",
                    description="AWS disaster recovery strategies and solutions",
                    relevance="medium",
                    link_type="guide"
                )
            ],
            "performance_efficiency": [
                DocumentationLink(
                    title="Performance Efficiency Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html",
                    description="Official AWS Well-Architected Framework Performance Efficiency Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS Performance Best Practices",
                    url="https://aws.amazon.com/architecture/performance-efficiency/",
                    description="AWS performance optimization best practices",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="AWS Compute Optimizer",
                    url="https://aws.amazon.com/compute-optimizer/",
                    description="Right-sizing recommendations for AWS resources",
                    relevance="medium",
                    link_type="documentation"
                )
            ],
            "cost_optimization": [
                DocumentationLink(
                    title="Cost Optimization Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
                    description="Official AWS Well-Architected Framework Cost Optimization Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS Cost Management",
                    url="https://aws.amazon.com/aws-cost-management/",
                    description="AWS cost management tools and best practices",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="AWS Cost Optimization Best Practices",
                    url="https://aws.amazon.com/architecture/cost-optimization/",
                    description="Cost optimization strategies and patterns",
                    relevance="medium",
                    link_type="guide"
                )
            ],
            "operational_excellence": [
                DocumentationLink(
                    title="Operational Excellence Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html",
                    description="Official AWS Well-Architected Framework Operational Excellence Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS DevOps Best Practices",
                    url="https://aws.amazon.com/devops/",
                    description="AWS DevOps practices and automation tools",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="AWS Systems Manager",
                    url="https://docs.aws.amazon.com/systems-manager/",
                    description="Operational management and automation",
                    relevance="medium",
                    link_type="documentation"
                )
            ],
            "sustainability": [
                DocumentationLink(
                    title="Sustainability Pillar - AWS Well-Architected Framework",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html",
                    description="Official AWS Well-Architected Framework Sustainability Pillar documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="AWS Sustainability",
                    url="https://aws.amazon.com/sustainability/",
                    description="AWS sustainability initiatives and best practices",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="AWS Customer Carbon Footprint Tool",
                    url="https://aws.amazon.com/aws-cost-management/aws-customer-carbon-footprint-tool/",
                    description="Track and reduce your carbon footprint on AWS",
                    relevance="medium",
                    link_type="documentation"
                )
            ]
        }
    
    def _load_service_documentation(self):
        """Load service-specific documentation links."""
        self.service_docs = {
            # Compute services
            "Lambda": DocumentationLink(
                title="AWS Lambda Documentation",
                url="https://docs.aws.amazon.com/lambda/",
                description="Serverless compute service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "EC2": DocumentationLink(
                title="Amazon EC2 Documentation",
                url="https://docs.aws.amazon.com/ec2/",
                description="Virtual server documentation",
                relevance="high",
                link_type="documentation"
            ),
            "ECS": DocumentationLink(
                title="Amazon ECS Documentation",
                url="https://docs.aws.amazon.com/ecs/",
                description="Container orchestration service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "Fargate": DocumentationLink(
                title="AWS Fargate Documentation",
                url="https://docs.aws.amazon.com/fargate/",
                description="Serverless container compute documentation",
                relevance="high",
                link_type="documentation"
            ),
            
            # Database services
            "RDS": DocumentationLink(
                title="Amazon RDS Documentation",
                url="https://docs.aws.amazon.com/rds/",
                description="Managed relational database service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "DynamoDB": DocumentationLink(
                title="Amazon DynamoDB Documentation",
                url="https://docs.aws.amazon.com/dynamodb/",
                description="NoSQL database service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "Aurora": DocumentationLink(
                title="Amazon Aurora Documentation",
                url="https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/",
                description="MySQL and PostgreSQL-compatible relational database",
                relevance="high",
                link_type="documentation"
            ),
            
            # Storage services
            "S3": DocumentationLink(
                title="Amazon S3 Documentation",
                url="https://docs.aws.amazon.com/s3/",
                description="Object storage service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "EBS": DocumentationLink(
                title="Amazon EBS Documentation",
                url="https://docs.aws.amazon.com/ebs/",
                description="Block storage for EC2 documentation",
                relevance="high",
                link_type="documentation"
            ),
            "EFS": DocumentationLink(
                title="Amazon EFS Documentation",
                url="https://docs.aws.amazon.com/efs/",
                description="Elastic file system documentation",
                relevance="high",
                link_type="documentation"
            ),
            
            # Networking services
            "VPC": DocumentationLink(
                title="Amazon VPC Documentation",
                url="https://docs.aws.amazon.com/vpc/",
                description="Virtual private cloud documentation",
                relevance="high",
                link_type="documentation"
            ),
            "CloudFront": DocumentationLink(
                title="Amazon CloudFront Documentation",
                url="https://docs.aws.amazon.com/cloudfront/",
                description="Content delivery network documentation",
                relevance="high",
                link_type="documentation"
            ),
            "API Gateway": DocumentationLink(
                title="Amazon API Gateway Documentation",
                url="https://docs.aws.amazon.com/apigateway/",
                description="API management service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "Route 53": DocumentationLink(
                title="Amazon Route 53 Documentation",
                url="https://docs.aws.amazon.com/route53/",
                description="DNS and domain registration service documentation",
                relevance="high",
                link_type="documentation"
            ),
            
            # Security services
            "IAM": DocumentationLink(
                title="AWS IAM Documentation",
                url="https://docs.aws.amazon.com/iam/",
                description="Identity and access management documentation",
                relevance="high",
                link_type="documentation"
            ),
            "KMS": DocumentationLink(
                title="AWS KMS Documentation",
                url="https://docs.aws.amazon.com/kms/",
                description="Key management service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "WAF": DocumentationLink(
                title="AWS WAF Documentation",
                url="https://docs.aws.amazon.com/waf/",
                description="Web application firewall documentation",
                relevance="high",
                link_type="documentation"
            ),
            "Cognito": DocumentationLink(
                title="Amazon Cognito Documentation",
                url="https://docs.aws.amazon.com/cognito/",
                description="User authentication and authorization documentation",
                relevance="high",
                link_type="documentation"
            ),
            "Secrets Manager": DocumentationLink(
                title="AWS Secrets Manager Documentation",
                url="https://docs.aws.amazon.com/secretsmanager/",
                description="Secrets management service documentation",
                relevance="high",
                link_type="documentation"
            ),
            
            # Monitoring services
            "CloudWatch": DocumentationLink(
                title="Amazon CloudWatch Documentation",
                url="https://docs.aws.amazon.com/cloudwatch/",
                description="Monitoring and observability service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "X-Ray": DocumentationLink(
                title="AWS X-Ray Documentation",
                url="https://docs.aws.amazon.com/xray/",
                description="Distributed tracing service documentation",
                relevance="high",
                link_type="documentation"
            ),
            "CloudTrail": DocumentationLink(
                title="AWS CloudTrail Documentation",
                url="https://docs.aws.amazon.com/cloudtrail/",
                description="AWS API activity logging documentation",
                relevance="high",
                link_type="documentation"
            )
        }
    
    def _load_capability_documentation(self):
        """Load capability-specific implementation guides."""
        self.capability_docs = {
            "encryption": [
                DocumentationLink(
                    title="Encryption at Rest",
                    url="https://docs.aws.amazon.com/whitepapers/latest/logical-separation/encrypting-data-at-rest-and--in-transit.html",
                    description="AWS encryption at rest best practices",
                    relevance="high",
                    link_type="whitepaper"
                ),
                DocumentationLink(
                    title="AWS KMS Best Practices",
                    url="https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html",
                    description="Key management best practices",
                    relevance="high",
                    link_type="guide"
                )
            ],
            "backup_recovery": [
                DocumentationLink(
                    title="AWS Backup Documentation",
                    url="https://docs.aws.amazon.com/aws-backup/",
                    description="Centralized backup service documentation",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="Disaster Recovery Strategies",
                    url="https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html",
                    description="DR strategies and implementation patterns",
                    relevance="high",
                    link_type="whitepaper"
                )
            ],
            "monitoring_alerting": [
                DocumentationLink(
                    title="CloudWatch Alarms",
                    url="https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html",
                    description="Creating CloudWatch alarms for monitoring",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="Monitoring Best Practices",
                    url="https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html",
                    description="Recommended alarms for AWS services",
                    relevance="high",
                    link_type="guide"
                )
            ],
            "scaling": [
                DocumentationLink(
                    title="Auto Scaling Documentation",
                    url="https://docs.aws.amazon.com/autoscaling/",
                    description="Auto scaling for EC2 and other services",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="Scaling Best Practices",
                    url="https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-simple-step.html",
                    description="Auto scaling policies and best practices",
                    relevance="high",
                    link_type="guide"
                )
            ],
            "managed_services": [
                DocumentationLink(
                    title="AWS Managed Services",
                    url="https://aws.amazon.com/managed-services/",
                    description="Overview of AWS managed services",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="Serverless on AWS",
                    url="https://aws.amazon.com/serverless/",
                    description="Serverless architecture and services",
                    relevance="high",
                    link_type="guide"
                )
            ]
        }
    
    def _load_pattern_documentation(self):
        """Load pattern-specific architecture guides."""
        self.pattern_docs = {
            "serverless": [
                DocumentationLink(
                    title="Serverless Application Lens",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html",
                    description="Well-Architected Framework for serverless applications",
                    relevance="high",
                    link_type="documentation"
                ),
                DocumentationLink(
                    title="Serverless Patterns Collection",
                    url="https://serverlessland.com/patterns",
                    description="Serverless architecture patterns and examples",
                    relevance="high",
                    link_type="guide"
                )
            ],
            "microservices": [
                DocumentationLink(
                    title="Microservices on AWS",
                    url="https://aws.amazon.com/microservices/",
                    description="Microservices architecture on AWS",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="Implementing Microservices on AWS",
                    url="https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html",
                    description="Microservices implementation whitepaper",
                    relevance="high",
                    link_type="whitepaper"
                )
            ],
            "container_based": [
                DocumentationLink(
                    title="Containers on AWS",
                    url="https://aws.amazon.com/containers/",
                    description="Container services and best practices",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="ECS Best Practices",
                    url="https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html",
                    description="Amazon ECS best practices guide",
                    relevance="high",
                    link_type="guide"
                )
            ],
            "data_analytics": [
                DocumentationLink(
                    title="Analytics on AWS",
                    url="https://aws.amazon.com/big-data/datalakes-and-analytics/",
                    description="Data lakes and analytics on AWS",
                    relevance="high",
                    link_type="guide"
                ),
                DocumentationLink(
                    title="Data Analytics Lens",
                    url="https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html",
                    description="Well-Architected Framework for analytics workloads",
                    relevance="high",
                    link_type="documentation"
                )
            ]
        }
    
    def get_pillar_documentation(self, pillar: str) -> List[DocumentationLink]:
        """
        Get official WAFR documentation for a pillar.
        
        Args:
            pillar: WAFR pillar name
            
        Returns:
            List of documentation links for the pillar
        """
        return self.pillar_docs.get(pillar, [])
    
    def get_service_documentation(self, service: str) -> Optional[DocumentationLink]:
        """
        Get AWS service documentation link.
        
        Args:
            service: AWS service name
            
        Returns:
            Documentation link for the service, or None if not found
        """
        return self.service_docs.get(service)
    
    def get_capability_documentation(
        self,
        capability: str,
        services: Optional[List[str]] = None
    ) -> List[DocumentationLink]:
        """
        Get documentation for implementing a capability.
        
        Args:
            capability: Capability name
            services: Optional list of services to get specific guidance for
            
        Returns:
            List of relevant documentation links
        """
        links = []
        
        # Add capability-specific documentation
        if capability in self.capability_docs:
            links.extend(self.capability_docs[capability])
        
        # Add service-specific documentation if services provided
        if services:
            for service in services[:3]:  # Limit to top 3 services
                service_doc = self.get_service_documentation(service)
                if service_doc:
                    links.append(service_doc)
        
        return self._filter_top_links(links, max_links=5)
    
    def get_pattern_documentation(self, pattern: str) -> List[DocumentationLink]:
        """
        Get architecture pattern documentation and best practices.
        
        Args:
            pattern: Architecture pattern name
            
        Returns:
            List of pattern-specific documentation links
        """
        return self.pattern_docs.get(pattern, [])
    
    def get_comprehensive_links(
        self,
        pillar: str,
        capability: Optional[str] = None,
        services: Optional[List[str]] = None,
        pattern: Optional[str] = None
    ) -> List[DocumentationLink]:
        """
        Get comprehensive documentation links for a recommendation.
        
        Combines pillar, capability, service, and pattern documentation
        with relevance scoring and filtering.
        
        Args:
            pillar: WAFR pillar name
            capability: Optional capability name
            services: Optional list of services
            pattern: Optional architecture pattern
            
        Returns:
            Filtered list of top 3-5 most relevant documentation links
        """
        all_links = []
        
        # Add pillar documentation (always include top 1)
        pillar_links = self.get_pillar_documentation(pillar)
        if pillar_links:
            all_links.append(pillar_links[0])  # Top pillar doc
        
        # Add capability documentation
        if capability:
            capability_links = self.get_capability_documentation(capability, services)
            all_links.extend(capability_links[:2])  # Top 2 capability docs
        
        # Add pattern documentation
        if pattern:
            pattern_links = self.get_pattern_documentation(pattern)
            all_links.extend(pattern_links[:1])  # Top 1 pattern doc
        
        # Add service documentation
        if services:
            for service in services[:2]:  # Top 2 services
                service_doc = self.get_service_documentation(service)
                if service_doc:
                    all_links.append(service_doc)
        
        return self._filter_top_links(all_links, max_links=5)
    
    def _filter_top_links(
        self,
        links: List[DocumentationLink],
        max_links: int = 5
    ) -> List[DocumentationLink]:
        """
        Filter and prioritize documentation links.
        
        Args:
            links: List of documentation links
            max_links: Maximum number of links to return
            
        Returns:
            Filtered list of top links by relevance
        """
        # Remove duplicates by URL
        seen_urls = set()
        unique_links = []
        for link in links:
            if link.url not in seen_urls:
                seen_urls.add(link.url)
                unique_links.append(link)
        
        # Sort by relevance (high > medium > low)
        relevance_order = {"high": 3, "medium": 2, "low": 1}
        sorted_links = sorted(
            unique_links,
            key=lambda x: relevance_order.get(x.relevance, 0),
            reverse=True
        )
        
        return sorted_links[:max_links]
