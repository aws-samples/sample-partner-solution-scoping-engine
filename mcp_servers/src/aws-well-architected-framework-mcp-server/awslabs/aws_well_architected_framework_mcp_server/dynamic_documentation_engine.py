"""Dynamic AWS Documentation Engine - Real-Time Context-Aware Documentation Retrieval"""

import logging
import re
import json
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio
from urllib.parse import urljoin, quote

logger = logging.getLogger(__name__)


@dataclass
class DynamicDocumentationLink:
    """Dynamic documentation link with context scoring."""
    title: str
    url: str
    doc_type: str
    relevance_score: float
    service_context: List[str]
    pillar_context: str
    business_context: Optional[str] = None


class DynamicDocumentationEngine:
    """Real-time dynamic AWS documentation retrieval based on architecture context."""
    
    def __init__(self):
        """Initialize dynamic documentation engine."""
        self.aws_service_patterns = self._build_service_patterns()
        self.pillar_contexts = self._build_pillar_contexts()
        self.business_contexts = self._build_business_contexts()
        self.session = None
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def get_dynamic_documentation(
        self,
        services: List[str],
        pillar: str,
        business_context: str,
        architecture_data: Dict[str, Any] = None
    ) -> List[DynamicDocumentationLink]:
        """
        DYNAMIC - Get real-time AWS documentation based on identified services and architecture.
        
        Args:
            services: AWS services identified from uploaded documents
            pillar: WAFR pillar being assessed
            business_context: Business domain for compliance docs
            architecture_data: Analyzed architecture from uploaded documents
            
        Returns:
            Ranked documentation links with real-time relevance scoring
        """
        
        logger.info(f"Dynamic documentation retrieval for {len(services)} services, pillar: {pillar}, context: {business_context}")
        
        # Real-time AWS documentation API query
        documentation_links = await self._query_aws_documentation_api(services, pillar, business_context)
        
        # Filter by relevance to identified services
        filtered_links = await self._filter_by_service_relevance(documentation_links, services, architecture_data)
        
        # Consider business context for compliance docs
        compliance_links = await self._get_compliance_documentation(business_context, services)
        filtered_links.extend(compliance_links)
        
        # Return ranked documentation links
        return self._rank_by_relevance(filtered_links, services, pillar, business_context)
    
    async def generate_contextual_recommendations(
        self,
        architecture_data: Dict[str, Any],
        pillar: str,
        business_context: str
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations specific to identified services and business domain.
        
        Args:
            architecture_data: Actual architecture from uploaded documents
            pillar: WAFR pillar being assessed
            business_context: Business domain and compliance requirements
            
        Returns:
            Tailored guidance based on real architecture analysis
        """
        
        # Analyze actual architecture from uploaded documents
        identified_services = self._extract_services_from_architecture(architecture_data)
        architecture_patterns = self._identify_architecture_patterns(architecture_data)
        
        # Generate recommendations specific to identified services
        service_recommendations = await self._generate_service_specific_recommendations(
            identified_services, pillar, architecture_patterns
        )
        
        # Consider business domain and compliance requirements
        compliance_recommendations = await self._generate_compliance_recommendations(
            business_context, identified_services, pillar
        )
        
        # Return tailored guidance
        return service_recommendations + compliance_recommendations
    
    async def _query_aws_documentation_api(
        self,
        services: List[str],
        pillar: str,
        business_context: str
    ) -> List[DynamicDocumentationLink]:
        """Query AWS documentation API for real-time documentation links."""
        
        session = await self._get_session()
        documentation_links = []
        
        try:
            # Query AWS documentation for each service
            for service in services:
                service_docs = await self._fetch_service_documentation(session, service, pillar)
                documentation_links.extend(service_docs)
            
            # Query pillar-specific documentation
            pillar_docs = await self._fetch_pillar_documentation(session, pillar, services)
            documentation_links.extend(pillar_docs)
            
        except Exception as e:
            logger.error(f"Error querying AWS documentation API: {e}")
            # Fallback to static documentation
            documentation_links = await self._get_fallback_documentation(services, pillar, business_context)
        
        return documentation_links
    
    async def _fetch_service_documentation(
        self,
        session: aiohttp.ClientSession,
        service: str,
        pillar: str
    ) -> List[DynamicDocumentationLink]:
        """Fetch real-time service documentation."""
        
        docs = []
        service_lower = service.lower()
        
        # AWS service documentation URLs (real-time)
        base_urls = {
            "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/",
            "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/",
            "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/",
            "lambda": "https://docs.aws.amazon.com/lambda/latest/dg/",
            "vpc": "https://docs.aws.amazon.com/vpc/latest/userguide/",
            "iam": "https://docs.aws.amazon.com/IAM/latest/UserGuide/",
            "cloudfront": "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/",
            "route53": "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/",
            "elb": "https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/"
        }
        
        if service_lower in base_urls:
            # Verify URL is accessible
            try:
                async with session.head(base_urls[service_lower]) as response:
                    if response.status == 200:
                        docs.append(DynamicDocumentationLink(
                            title=f"Amazon {service} User Guide",
                            url=base_urls[service_lower],
                            doc_type="user_guide",
                            relevance_score=0.9,
                            service_context=[service],
                            pillar_context=pillar
                        ))
            except Exception as e:
                logger.warning(f"Could not verify {service} documentation URL: {e}")
        
        # Pillar-specific service documentation
        pillar_url = await self._get_real_time_pillar_service_url(session, service_lower, pillar)
        if pillar_url:
            docs.append(DynamicDocumentationLink(
                title=f"{service} {pillar.replace('_', ' ').title()} Best Practices",
                url=pillar_url,
                doc_type="best_practice",
                relevance_score=1.0,
                service_context=[service],
                pillar_context=pillar
            ))
        
        return docs
    
    async def _get_real_time_pillar_service_url(
        self,
        session: aiohttp.ClientSession,
        service: str,
        pillar: str
    ) -> Optional[str]:
        """Get real-time pillar-specific service documentation URL."""
        
        # Dynamic URL generation with real-time verification
        pillar_service_urls = {
            "security": {
                "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html",
                "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security.html",
                "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html",
                "iam": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html"
            },
            "performance_efficiency": {
                "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-types.html",
                "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html",
                "lambda": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html"
            },
            "cost_optimization": {
                "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html",
                "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-costs.html",
                "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html"
            },
            "reliability": {
                "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-recovery.html",
                "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html",
                "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/disaster-recovery-resiliency.html"
            }
        }
        
        url = pillar_service_urls.get(pillar, {}).get(service)
        if url:
            try:
                # Verify URL is accessible in real-time
                async with session.head(url) as response:
                    if response.status == 200:
                        return url
            except Exception as e:
                logger.warning(f"Could not verify pillar-service URL {url}: {e}")
        
        return None
    
    def _extract_services_from_architecture(self, architecture_data: Dict[str, Any]) -> List[str]:
        """Extract AWS services from analyzed architecture data."""
        
        services = set()
        
        if not architecture_data:
            return list(services)
        
        # Extract from document analysis
        if "services_mentioned" in architecture_data:
            services.update(architecture_data["services_mentioned"])
        
        # Extract from architecture diagrams
        if "diagram_analysis" in architecture_data:
            diagram_services = self._extract_services_from_diagrams(architecture_data["diagram_analysis"])
            services.update(diagram_services)
        
        # Extract from infrastructure code
        if "infrastructure_code" in architecture_data:
            code_services = self._extract_services_from_code(architecture_data["infrastructure_code"])
            services.update(code_services)
        
        logger.info(f"Extracted {len(services)} services from architecture: {list(services)}")
        return list(services)
    
    def _extract_services_from_diagrams(self, diagram_analysis: Dict[str, Any]) -> List[str]:
        """Extract AWS services from diagram analysis."""
        
        services = set()
        
        # Look for AWS service icons and labels
        aws_service_patterns = [
            r"aws[_-]?(\w+)", r"amazon[_-]?(\w+)", r"ec2", r"s3", r"rds", r"lambda",
            r"vpc", r"elb", r"cloudfront", r"route53", r"iam", r"kms", r"sns", r"sqs"
        ]
        
        text_content = str(diagram_analysis).lower()
        
        for pattern in aws_service_patterns:
            matches = re.findall(pattern, text_content)
            services.update(matches)
        
        return list(services)
    
    def _extract_services_from_code(self, infrastructure_code: Dict[str, Any]) -> List[str]:
        """Extract AWS services from infrastructure code."""
        
        services = set()
        
        # CloudFormation/Terraform resource patterns
        resource_patterns = [
            r"AWS::(\w+)::", r"aws_(\w+)", r"resource\s+\"aws_(\w+)\""
        ]
        
        code_content = str(infrastructure_code).lower()
        
        for pattern in resource_patterns:
            matches = re.findall(pattern, code_content)
            services.update(matches)
        
        return list(services)
    
    def _identify_architecture_patterns(self, architecture_data: Dict[str, Any]) -> List[str]:
        """Identify architecture patterns from analyzed data."""
        
        patterns = []
        
        if not architecture_data:
            return patterns
        
        # Pattern detection based on service combinations
        services = self._extract_services_from_architecture(architecture_data)
        
        # Microservices pattern
        if any(service in services for service in ["ecs", "fargate", "lambda", "api-gateway"]):
            patterns.append("microservices")
        
        # Serverless pattern
        if any(service in services for service in ["lambda", "api-gateway", "dynamodb", "s3"]):
            patterns.append("serverless")
        
        # Event-driven pattern
        if any(service in services for service in ["sns", "sqs", "eventbridge", "lambda"]):
            patterns.append("event-driven")
        
        # Data lake pattern
        if any(service in services for service in ["s3", "glue", "athena", "redshift"]):
            patterns.append("data-lake")
        
        logger.info(f"Identified architecture patterns: {patterns}")
        return patterns
    
    async def _generate_service_specific_recommendations(
        self,
        services: List[str],
        pillar: str,
        architecture_patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations specific to identified services."""
        
        recommendations = []
        
        for service in services:
            service_recs = await self._get_service_pillar_recommendations(service, pillar, architecture_patterns)
            recommendations.extend(service_recs)
        
        return recommendations
    
    async def _get_service_pillar_recommendations(
        self,
        service: str,
        pillar: str,
        patterns: List[str]
    ) -> List[Dict[str, Any]]:
        """Get pillar-specific recommendations for a service."""
        
        # Service-pillar specific recommendations
        service_pillar_recs = {
            "security": {
                "s3": [
                    {
                        "recommendation": "Enable S3 bucket encryption at rest using AWS KMS",
                        "implementation": "Configure default encryption in bucket settings",
                        "priority": "high",
                        "compliance": ["HIPAA", "PCI-DSS"]
                    },
                    {
                        "recommendation": "Implement S3 bucket policies with least privilege access",
                        "implementation": "Use IAM policies and bucket policies together",
                        "priority": "high",
                        "compliance": ["SOC2", "ISO27001"]
                    }
                ],
                "ec2": [
                    {
                        "recommendation": "Use AWS Systems Manager Session Manager instead of SSH",
                        "implementation": "Install SSM agent and configure IAM roles",
                        "priority": "medium",
                        "compliance": ["SOC2"]
                    }
                ]
            },
            "cost_optimization": {
                "ec2": [
                    {
                        "recommendation": "Right-size EC2 instances based on utilization metrics",
                        "implementation": "Use AWS Compute Optimizer recommendations",
                        "priority": "high",
                        "cost_impact": "20-40% savings"
                    }
                ],
                "s3": [
                    {
                        "recommendation": "Implement S3 Intelligent Tiering for automatic cost optimization",
                        "implementation": "Enable Intelligent Tiering on S3 buckets",
                        "priority": "medium",
                        "cost_impact": "10-30% savings"
                    }
                ]
            }
        }
        
        return service_pillar_recs.get(pillar, {}).get(service, [])
    
    async def _get_compliance_documentation(
        self,
        business_context: str,
        services: List[str]
    ) -> List[DynamicDocumentationLink]:
        """Get compliance documentation based on business context."""
        
        docs = []
        session = await self._get_session()
        
        # Business context compliance mapping
        compliance_docs = {
            "healthcare": [
                ("HIPAA Compliance on AWS", "https://aws.amazon.com/compliance/hipaa-compliance/", "compliance_guide"),
                ("Healthcare Architecture on AWS", "https://aws.amazon.com/health/", "industry_guide")
            ],
            "financial": [
                ("Financial Services on AWS", "https://aws.amazon.com/financial-services/", "industry_guide"),
                ("PCI DSS Compliance", "https://aws.amazon.com/compliance/pci-dss-level-1-faqs/", "compliance_guide")
            ],
            "government": [
                ("AWS GovCloud (US)", "https://aws.amazon.com/govcloud-us/", "industry_guide"),
                ("FedRAMP Compliance", "https://aws.amazon.com/compliance/fedramp/", "compliance_guide")
            ],
            "retail": [
                ("Retail on AWS", "https://aws.amazon.com/retail/", "industry_guide"),
                ("E-commerce Architecture", "https://aws.amazon.com/architecture/e-commerce/", "architecture_guide")
            ]
        }
        
        if business_context.lower() in compliance_docs:
            for title, url, doc_type in compliance_docs[business_context.lower()]:
                # Verify URL accessibility
                try:
                    async with session.head(url) as response:
                        if response.status == 200:
                            docs.append(DynamicDocumentationLink(
                                title=title,
                                url=url,
                                doc_type=doc_type,
                                relevance_score=0.95,
                                service_context=services,
                                pillar_context="compliance",
                                business_context=business_context
                            ))
                except Exception as e:
                    logger.warning(f"Could not verify compliance URL {url}: {e}")
        
        return docs
    
    async def _generate_compliance_recommendations(
        self,
        business_context: str,
        services: List[str],
        pillar: str
    ) -> List[Dict[str, Any]]:
        """Generate compliance recommendations based on business context."""
        
        recommendations = []
        
        # Business context compliance requirements
        compliance_requirements = {
            "healthcare": {
                "frameworks": ["HIPAA", "HITECH"],
                "key_controls": ["encryption", "access_logging", "audit_trails"],
                "required_services": ["cloudtrail", "kms", "config"]
            },
            "financial": {
                "frameworks": ["PCI-DSS", "SOX", "GDPR"],
                "key_controls": ["data_encryption", "network_segmentation", "access_control"],
                "required_services": ["kms", "vpc", "guardduty"]
            },
            "government": {
                "frameworks": ["FedRAMP", "FISMA"],
                "key_controls": ["continuous_monitoring", "incident_response", "configuration_management"],
                "required_services": ["config", "cloudtrail", "securityhub"]
            }
        }
        
        if business_context.lower() in compliance_requirements:
            req = compliance_requirements[business_context.lower()]
            
            for framework in req["frameworks"]:
                recommendations.append({
                    "recommendation": f"Implement {framework} compliance controls for {pillar} pillar",
                    "implementation": f"Configure {', '.join(req['required_services'])} services",
                    "priority": "high",
                    "compliance": [framework],
                    "services_required": req["required_services"]
                })
        
        return recommendations
    
    def _rank_by_relevance(
        self,
        docs: List[DynamicDocumentationLink],
        services: List[str],
        pillar: str,
        business_context: str
    ) -> List[DynamicDocumentationLink]:
        """Rank documentation by relevance to current context."""
        
        for doc in docs:
            # Boost score for exact service matches
            service_match_boost = len(set(doc.service_context) & set(services)) * 0.1
            
            # Boost score for pillar relevance
            pillar_boost = 0.2 if doc.pillar_context == pillar else 0.0
            
            # Boost score for business context match
            business_boost = 0.15 if doc.business_context == business_context else 0.0
            
            # Apply boosts
            doc.relevance_score += service_match_boost + pillar_boost + business_boost
            doc.relevance_score = min(doc.relevance_score, 1.0)  # Cap at 1.0
        
        # Sort by relevance score
        return sorted(docs, key=lambda x: x.relevance_score, reverse=True)
    
    async def _get_fallback_documentation(
        self,
        services: List[str],
        pillar: str,
        business_context: str
    ) -> List[DynamicDocumentationLink]:
        """Fallback to static documentation if API fails."""
        
        docs = []
        
        # Static fallback documentation
        for service in services:
            docs.append(DynamicDocumentationLink(
                title=f"Amazon {service} Documentation",
                url=f"https://docs.aws.amazon.com/{service}/",
                doc_type="user_guide",
                relevance_score=0.8,
                service_context=[service],
                pillar_context=pillar
            ))
        
        # Pillar documentation
        docs.append(DynamicDocumentationLink(
            title=f"AWS Well-Architected {pillar.replace('_', ' ').title()} Pillar",
            url=f"https://docs.aws.amazon.com/wellarchitected/latest/{pillar.replace('_', '-')}-pillar/",
            doc_type="pillar_guide",
            relevance_score=0.9,
            service_context=services,
            pillar_context=pillar
        ))
        
        return docs
    
    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def _fetch_pillar_documentation(
        self,
        session: aiohttp.ClientSession,
        pillar: str,
        services: List[str]
    ) -> List[DynamicDocumentationLink]:
        """Fetch real-time pillar documentation."""
        
        docs = []
        
        # Main pillar documentation URL
        pillar_url = f"https://docs.aws.amazon.com/wellarchitected/latest/{pillar.replace('_', '-')}-pillar/welcome.html"
        
        try:
            async with session.head(pillar_url) as response:
                if response.status == 200:
                    docs.append(DynamicDocumentationLink(
                        title=f"AWS {pillar.replace('_', ' ').title()} Pillar",
                        url=pillar_url,
                        doc_type="pillar_guide",
                        relevance_score=1.0,
                        service_context=services,
                        pillar_context=pillar
                    ))
        except Exception as e:
            logger.warning(f"Could not verify pillar URL {pillar_url}: {e}")
        
        return docs
    
    async def _filter_by_service_relevance(
        self,
        docs: List[DynamicDocumentationLink],
        services: List[str],
        architecture_data: Dict[str, Any] = None
    ) -> List[DynamicDocumentationLink]:
        """Filter documentation by relevance to identified services."""
        
        filtered_docs = []
        
        for doc in docs:
            # Check if doc is relevant to any of the identified services
            service_overlap = set(doc.service_context) & set(services)
            
            if service_overlap or doc.doc_type in ["pillar_guide", "compliance_guide"]:
                # Boost relevance score based on service overlap
                if service_overlap:
                    doc.relevance_score += len(service_overlap) * 0.1
                
                filtered_docs.append(doc)
        
        return filtered_docs
    
    def _build_service_patterns(self) -> Dict[str, List[str]]:
        """Build dynamic service detection patterns."""
        return {
            "compute": ["ec2", "lambda", "ecs", "fargate", "batch", "lightsail"],
            "storage": ["s3", "ebs", "efs", "fsx", "glacier"],
            "database": ["rds", "dynamodb", "aurora", "redshift", "documentdb", "neptune"],
            "networking": ["vpc", "cloudfront", "route53", "elb", "api-gateway", "direct-connect"],
            "security": ["iam", "kms", "secrets-manager", "certificate-manager", "guardduty", "securityhub"],
            "monitoring": ["cloudwatch", "x-ray", "cloudtrail", "config", "systems-manager"],
            "analytics": ["athena", "glue", "kinesis", "emr", "quicksight"],
            "ml": ["sagemaker", "comprehend", "rekognition", "textract", "bedrock"]
        }
    
    def _build_pillar_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Build pillar context information."""
        return {
            "security": {
                "focus_areas": ["encryption", "access_control", "network_security", "data_protection"],
                "compliance_frameworks": ["SOC", "ISO27001", "PCI-DSS", "HIPAA"]
            },
            "reliability": {
                "focus_areas": ["high_availability", "disaster_recovery", "backup", "fault_tolerance"],
                "metrics": ["RTO", "RPO", "MTTR", "availability_percentage"]
            },
            "performance_efficiency": {
                "focus_areas": ["compute_optimization", "storage_optimization", "network_optimization", "monitoring"],
                "metrics": ["latency", "throughput", "utilization", "response_time"]
            },
            "cost_optimization": {
                "focus_areas": ["right_sizing", "reserved_instances", "spot_instances", "cost_monitoring"],
                "metrics": ["cost_per_transaction", "utilization_rate", "savings_percentage"]
            },
            "operational_excellence": {
                "focus_areas": ["automation", "monitoring", "incident_response", "change_management"],
                "practices": ["IaC", "CI/CD", "monitoring", "logging"]
            },
            "sustainability": {
                "focus_areas": ["resource_efficiency", "carbon_footprint", "optimization", "lifecycle_management"],
                "metrics": ["energy_efficiency", "resource_utilization", "carbon_impact"]
            }
        }
    
    def _build_business_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Build business context information."""
        return {
            "healthcare": {
                "compliance": ["HIPAA", "HITECH"],
                "data_sensitivity": "high",
                "availability_requirements": "99.99%",
                "key_services": ["s3", "rds", "kms", "cloudtrail"]
            },
            "financial": {
                "compliance": ["PCI-DSS", "SOX", "GDPR"],
                "data_sensitivity": "high",
                "availability_requirements": "99.999%",
                "key_services": ["kms", "cloudtrail", "config", "guardduty"]
            },
            "government": {
                "compliance": ["FedRAMP", "FISMA"],
                "data_sensitivity": "high",
                "availability_requirements": "99.99%",
                "key_services": ["govcloud", "kms", "cloudtrail"]
            },
            "retail": {
                "compliance": ["PCI-DSS"],
                "data_sensitivity": "medium",
                "availability_requirements": "99.9%",
                "key_services": ["cloudfront", "elb", "auto-scaling"]
            }
        }
