# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS documentation and reference architecture integration."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class DocumentationType(Enum):
    """Types of AWS documentation."""
    BEST_PRACTICES = "best_practices"
    REFERENCE_ARCHITECTURE = "reference_architecture"
    IMPLEMENTATION_GUIDE = "implementation_guide"
    SERVICE_DOCUMENTATION = "service_documentation"
    SECURITY_GUIDANCE = "security_guidance"
    COST_OPTIMIZATION = "cost_optimization"
    WELL_ARCHITECTED = "well_architected"
    SOLUTIONS_LIBRARY = "solutions_library"
    WHITEPAPERS = "whitepapers"


@dataclass
class AWSDocumentationLink:
    """Represents an AWS documentation link."""
    title: str
    url: str
    doc_type: DocumentationType
    description: str
    services: List[str]
    pillars: List[str]
    use_cases: List[str]


class AWSDocumentationDatabase:
    """Database of AWS documentation links organized by service, pattern, and pillar."""

    def __init__(self):
        self.documentation = self._load_documentation_database()

    def _load_documentation_database(self) -> Dict[str, List[AWSDocumentationLink]]:
        """Load comprehensive AWS documentation database."""
        docs = {}

        # Well-Architected Framework Documentation
        docs["well_architected"] = [
            AWSDocumentationLink(
                title="AWS Well-Architected Framework",
                url="https://aws.amazon.com/architecture/well-architected/",
                doc_type=DocumentationType.WELL_ARCHITECTED,
                description="Complete Well-Architected Framework overview and principles",
                services=["all"],
                pillars=["operational_excellence", "security", "reliability", "performance_efficiency", "cost_optimization", "sustainability"],
                use_cases=["architecture_review", "design_validation", "continuous_improvement"]
            ),
            AWSDocumentationLink(
                title="Well-Architected Tool",
                url="https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html",
                doc_type=DocumentationType.IMPLEMENTATION_GUIDE,
                description="How to use AWS Well-Architected Tool for assessments",
                services=["well-architected-tool"],
                pillars=["all"],
                use_cases=["assessment", "tracking", "improvement"]
            )
        ]

        # Security Documentation
        docs["security"] = [
            AWSDocumentationLink(
                title="AWS Security Best Practices",
                url="https://docs.aws.amazon.com/security/",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="Comprehensive AWS security best practices and guidance",
                services=["iam", "kms", "vpc", "cloudtrail"],
                pillars=["security"],
                use_cases=["security_design", "compliance", "threat_protection"]
            ),
            AWSDocumentationLink(
                title="AWS Security Reference Architecture",
                url="https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/",
                doc_type=DocumentationType.REFERENCE_ARCHITECTURE,
                description="Comprehensive security reference architecture for AWS",
                services=["iam", "organizations", "control-tower", "security-hub"],
                pillars=["security"],
                use_cases=["enterprise_security", "multi_account", "compliance"]
            ),
            AWSDocumentationLink(
                title="IAM Best Practices",
                url="https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="Identity and Access Management best practices",
                services=["iam", "sts", "organizations"],
                pillars=["security"],
                use_cases=["access_control", "privilege_management", "federation"]
            )
        ]

        # Cost Optimization Documentation
        docs["cost_optimization"] = [
            AWSDocumentationLink(
                title="AWS Cost Optimization Best Practices",
                url="https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="Complete cost optimization strategies and best practices",
                services=["cost-explorer", "budgets", "trusted-advisor"],
                pillars=["cost_optimization"],
                use_cases=["cost_management", "rightsizing", "optimization"]
            ),
            AWSDocumentationLink(
                title="Reserved Instances Guide",
                url="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html",
                doc_type=DocumentationType.IMPLEMENTATION_GUIDE,
                description="How to purchase and manage Reserved Instances for cost savings",
                services=["ec2", "rds", "elasticache"],
                pillars=["cost_optimization"],
                use_cases=["cost_savings", "capacity_planning"]
            )
        ]

        # Architecture Patterns Documentation
        docs["microservices"] = [
            AWSDocumentationLink(
                title="Microservices on AWS",
                url="https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html",
                doc_type=DocumentationType.REFERENCE_ARCHITECTURE,
                description="Complete guide to implementing microservices on AWS",
                services=["ecs", "eks", "api-gateway", "lambda"],
                pillars=["operational_excellence", "reliability", "performance_efficiency"],
                use_cases=["microservices", "containerization", "api_design"]
            ),
            AWSDocumentationLink(
                title="Amazon ECS Reference Architecture",
                url="https://github.com/aws-samples/ecs-refarch-continuous-deployment",
                doc_type=DocumentationType.REFERENCE_ARCHITECTURE,
                description="Reference architecture for microservices with ECS",
                services=["ecs", "alb", "cloudformation"],
                pillars=["operational_excellence", "reliability"],
                use_cases=["containerization", "cicd", "microservices"]
            )
        ]

        # Serverless Documentation
        docs["serverless"] = [
            AWSDocumentationLink(
                title="AWS Serverless Application Lens",
                url="https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html",
                doc_type=DocumentationType.WELL_ARCHITECTED,
                description="Well-Architected guidance specifically for serverless applications",
                services=["lambda", "api-gateway", "dynamodb", "s3"],
                pillars=["all"],
                use_cases=["serverless", "event_driven", "cost_optimization"]
            ),
            AWSDocumentationLink(
                title="Serverless Reference Architectures",
                url="https://github.com/aws-samples/lambda-refarch-webapp",
                doc_type=DocumentationType.REFERENCE_ARCHITECTURE,
                description="Reference architectures for serverless web applications",
                services=["lambda", "api-gateway", "dynamodb", "cognito"],
                pillars=["cost_optimization", "performance_efficiency"],
                use_cases=["web_applications", "mobile_backend", "apis"]
            )
        ]

        # Reliability Documentation
        docs["reliability"] = [
            AWSDocumentationLink(
                title="AWS Reliability Pillar",
                url="https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
                doc_type=DocumentationType.WELL_ARCHITECTED,
                description="Complete reliability pillar guidance and best practices",
                services=["auto-scaling", "elb", "rds", "backup"],
                pillars=["reliability"],
                use_cases=["fault_tolerance", "disaster_recovery", "scaling"]
            ),
            AWSDocumentationLink(
                title="Disaster Recovery Strategies",
                url="https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="Comprehensive disaster recovery strategies and implementation",
                services=["backup", "cloudformation", "route53"],
                pillars=["reliability"],
                use_cases=["disaster_recovery", "business_continuity"]
            )
        ]

        # Performance Documentation
        docs["performance"] = [
            AWSDocumentationLink(
                title="Performance Efficiency Pillar",
                url="https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html",
                doc_type=DocumentationType.WELL_ARCHITECTED,
                description="Performance efficiency best practices and guidance",
                services=["cloudfront", "elasticache", "rds"],
                pillars=["performance_efficiency"],
                use_cases=["performance_optimization", "caching", "latency_reduction"]
            ),
            AWSDocumentationLink(
                title="Amazon CloudFront Best Practices",
                url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/best-practices.html",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="CloudFront configuration and optimization best practices",
                services=["cloudfront", "s3"],
                pillars=["performance_efficiency", "cost_optimization"],
                use_cases=["content_delivery", "global_performance"]
            )
        ]

        # Solutions Library
        docs["solutions"] = [
            AWSDocumentationLink(
                title="AWS Solutions Library",
                url="https://aws.amazon.com/solutions/",
                doc_type=DocumentationType.SOLUTIONS_LIBRARY,
                description="Pre-built solutions for common use cases",
                services=["various"],
                pillars=["all"],
                use_cases=["quick_start", "proven_patterns"]
            ),
            AWSDocumentationLink(
                title="AWS Architecture Center",
                url="https://aws.amazon.com/architecture/",
                doc_type=DocumentationType.REFERENCE_ARCHITECTURE,
                description="Reference architectures, diagrams, and best practices",
                services=["various"],
                pillars=["all"],
                use_cases=["architecture_design", "reference_patterns"]
            )
        ]

        # Service-Specific Documentation
        docs["ec2"] = [
            AWSDocumentationLink(
                title="Amazon EC2 Best Practices",
                url="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-best-practices.html",
                doc_type=DocumentationType.BEST_PRACTICES,
                description="EC2 instance configuration and optimization best practices",
                services=["ec2"],
                pillars=["security", "performance_efficiency", "cost_optimization"],
                use_cases=["instance_configuration", "security", "cost_optimization"]
            )
        ]

        docs["s3"] = [
            AWSDocumentationLink(
                title="Amazon S3 Security Best Practices",
                url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html",
                doc_type=DocumentationType.SECURITY_GUIDANCE,
                description="S3 security configuration and access control best practices",
                services=["s3"],
                pillars=["security"],
                use_cases=["data_protection", "access_control", "compliance"]
            )
        ]

        return docs

    def get_documentation_by_service(self, service: str) -> List[AWSDocumentationLink]:
        """Get documentation links for a specific AWS service."""
        docs = []
        for category_docs in self.documentation.values():
            for doc in category_docs:
                if service in doc.services or "all" in doc.services or "various" in doc.services:
                    docs.append(doc)
        return docs

    def get_documentation_by_pillar(self, pillar: str) -> List[AWSDocumentationLink]:
        """Get documentation links for a specific WAFR pillar."""
        docs = []
        for category_docs in self.documentation.values():
            for doc in category_docs:
                if pillar in doc.pillars or "all" in doc.pillars:
                    docs.append(doc)
        return docs

    def get_documentation_by_pattern(self, pattern: str) -> List[AWSDocumentationLink]:
        """Get documentation links for an architecture pattern."""
        return self.documentation.get(pattern, [])

    def get_documentation_by_use_case(self, use_case: str) -> List[AWSDocumentationLink]:
        """Get documentation links for a specific use case."""
        docs = []
        for category_docs in self.documentation.values():
            for doc in category_docs:
                if use_case in doc.use_cases:
                    docs.append(doc)
        return docs

    def enhance_recommendation_with_docs(
        self,
        recommendation: str,
        services: List[str],
        pillars: List[str],
        use_cases: List[str] = None
    ) -> Dict[str, any]:
        """Enhance a recommendation with relevant documentation links."""
        relevant_docs = []

        # Get docs by services
        for service in services:
            relevant_docs.extend(self.get_documentation_by_service(service))

        # Get docs by pillars
        for pillar in pillars:
            relevant_docs.extend(self.get_documentation_by_pillar(pillar))

        # Get docs by use cases if provided
        if use_cases:
            for use_case in use_cases:
                relevant_docs.extend(self.get_documentation_by_use_case(use_case))

        # Remove duplicates and limit to most relevant
        unique_docs = []
        seen_urls = set()
        for doc in relevant_docs:
            if doc.url not in seen_urls:
                unique_docs.append(doc)
                seen_urls.add(doc.url)

        # Sort by relevance (prioritize implementation guides and best practices)
        priority_order = [
            DocumentationType.IMPLEMENTATION_GUIDE,
            DocumentationType.BEST_PRACTICES,
            DocumentationType.REFERENCE_ARCHITECTURE,
            DocumentationType.WELL_ARCHITECTED,
            DocumentationType.SECURITY_GUIDANCE,
            DocumentationType.SOLUTIONS_LIBRARY
        ]

        unique_docs.sort(key=lambda doc: (
            priority_order.index(doc.doc_type) if doc.doc_type in priority_order else 999,
            doc.title
        ))

        return {
            "recommendation": recommendation,
            "documentation": [
                {
                    "title": doc.title,
                    "url": doc.url,
                    "type": doc.doc_type.value,
                    "description": doc.description
                }
                for doc in unique_docs[:5]  # Limit to top 5 most relevant
            ],
            "implementation_guides": [
                doc for doc in unique_docs
                if doc.doc_type == DocumentationType.IMPLEMENTATION_GUIDE
            ][:2],
            "reference_architectures": [
                doc for doc in unique_docs
                if doc.doc_type == DocumentationType.REFERENCE_ARCHITECTURE
            ][:2]
        }


# Global documentation database instance
aws_docs_db = AWSDocumentationDatabase()


# Utility functions
def get_enhanced_recommendation(
    recommendation: str,
    services: List[str],
    pillars: List[str],
    use_cases: List[str] = None
) -> Dict[str, any]:
    """Get a recommendation enhanced with AWS documentation links."""
    return aws_docs_db.enhance_recommendation_with_docs(
        recommendation, services, pillars, use_cases
    )


def get_service_documentation(service: str) -> List[AWSDocumentationLink]:
    """Get documentation for a specific AWS service."""
    return aws_docs_db.get_documentation_by_service(service)


def get_pillar_documentation(pillar: str) -> List[AWSDocumentationLink]:
    """Get documentation for a specific WAFR pillar."""
    return aws_docs_db.get_documentation_by_pillar(pillar)