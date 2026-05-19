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

"""Solution text parsing and AWS service identification for WAFR assessment."""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

import boto3
from mcp.server.fastmcp import Context


@dataclass
class AWSService:
    """Represents an identified AWS service in the solution."""
    name: str
    service_type: str
    confidence: float
    context: str
    pillar_relevance: Dict[str, float]


@dataclass
class ArchitecturePattern:
    """Represents an identified architecture pattern."""
    pattern_name: str
    description: str
    services_involved: List[str]
    wafr_implications: Dict[str, List[str]]


@dataclass
class SolutionAnalysis:
    """Complete analysis of a solution text."""
    solution_id: str
    aws_services: List[AWSService]
    architecture_patterns: List[ArchitecturePattern]
    data_flows: List[Dict[str, Any]]
    security_requirements: List[str]
    performance_requirements: List[str]
    cost_considerations: List[str]
    compliance_requirements: List[str]
    sustainability_aspects: List[str]
    business_context: Dict[str, Any]


class SolutionTextParser:
    """Main class for parsing solution text and extracting WAFR-relevant information."""

    def __init__(self):
        self.aws_services_data = self._load_aws_services_mapping()
        self.architecture_patterns = self._load_architecture_patterns()
        self.wafr_keywords = self._load_wafr_keywords()

    def _load_aws_services_mapping(self) -> Dict[str, Any]:
        """Load AWS services mapping data."""
        # AWS Services with WAFR pillar relevance
        return {
            # Compute Services
            "ec2": {
                "full_name": "Amazon Elastic Compute Cloud",
                "category": "compute",
                "pillar_relevance": {
                    "operational_excellence": 0.8,
                    "security": 0.9,
                    "reliability": 0.8,
                    "performance_efficiency": 0.9,
                    "cost_optimization": 0.8,
                    "sustainability": 0.7
                },
                "keywords": ["ec2", "elastic compute", "virtual machine", "instance", "ami"]
            },
            "lambda": {
                "full_name": "AWS Lambda",
                "category": "compute",
                "pillar_relevance": {
                    "operational_excellence": 0.9,
                    "security": 0.7,
                    "reliability": 0.8,
                    "performance_efficiency": 0.8,
                    "cost_optimization": 0.9,
                    "sustainability": 0.9
                },
                "keywords": ["lambda", "serverless", "function", "event-driven"]
            },
            "ecs": {
                "full_name": "Amazon Elastic Container Service",
                "category": "compute",
                "pillar_relevance": {
                    "operational_excellence": 0.8,
                    "security": 0.8,
                    "reliability": 0.9,
                    "performance_efficiency": 0.8,
                    "cost_optimization": 0.7,
                    "sustainability": 0.8
                },
                "keywords": ["ecs", "container", "docker", "fargate", "task"]
            },
            # Storage Services
            "s3": {
                "full_name": "Amazon Simple Storage Service",
                "category": "storage",
                "pillar_relevance": {
                    "operational_excellence": 0.7,
                    "security": 0.9,
                    "reliability": 0.9,
                    "performance_efficiency": 0.7,
                    "cost_optimization": 0.8,
                    "sustainability": 0.8
                },
                "keywords": ["s3", "bucket", "object storage", "simple storage"]
            },
            "ebs": {
                "full_name": "Amazon Elastic Block Store",
                "category": "storage",
                "pillar_relevance": {
                    "operational_excellence": 0.6,
                    "security": 0.8,
                    "reliability": 0.8,
                    "performance_efficiency": 0.9,
                    "cost_optimization": 0.7,
                    "sustainability": 0.7
                },
                "keywords": ["ebs", "elastic block store", "volume", "storage"]
            },
            # Database Services
            "rds": {
                "full_name": "Amazon Relational Database Service",
                "category": "database",
                "pillar_relevance": {
                    "operational_excellence": 0.8,
                    "security": 0.9,
                    "reliability": 0.9,
                    "performance_efficiency": 0.8,
                    "cost_optimization": 0.7,
                    "sustainability": 0.7
                },
                "keywords": ["rds", "relational database", "mysql", "postgresql", "oracle", "sql server"]
            },
            "dynamodb": {
                "full_name": "Amazon DynamoDB",
                "category": "database",
                "pillar_relevance": {
                    "operational_excellence": 0.9,
                    "security": 0.8,
                    "reliability": 0.9,
                    "performance_efficiency": 0.9,
                    "cost_optimization": 0.8,
                    "sustainability": 0.8
                },
                "keywords": ["dynamodb", "nosql", "document database", "key-value"]
            },
            # Networking Services
            "vpc": {
                "full_name": "Amazon Virtual Private Cloud",
                "category": "networking",
                "pillar_relevance": {
                    "operational_excellence": 0.7,
                    "security": 0.9,
                    "reliability": 0.8,
                    "performance_efficiency": 0.7,
                    "cost_optimization": 0.6,
                    "sustainability": 0.6
                },
                "keywords": ["vpc", "virtual private cloud", "subnet", "network"]
            },
            "cloudfront": {
                "full_name": "Amazon CloudFront",
                "category": "networking",
                "pillar_relevance": {
                    "operational_excellence": 0.7,
                    "security": 0.8,
                    "reliability": 0.8,
                    "performance_efficiency": 0.9,
                    "cost_optimization": 0.8,
                    "sustainability": 0.8
                },
                "keywords": ["cloudfront", "cdn", "content delivery", "edge"]
            },
            # Security Services
            "iam": {
                "full_name": "AWS Identity and Access Management",
                "category": "security",
                "pillar_relevance": {
                    "operational_excellence": 0.8,
                    "security": 1.0,
                    "reliability": 0.7,
                    "performance_efficiency": 0.5,
                    "cost_optimization": 0.6,
                    "sustainability": 0.5
                },
                "keywords": ["iam", "identity", "access management", "role", "policy", "user"]
            },
            "kms": {
                "full_name": "AWS Key Management Service",
                "category": "security",
                "pillar_relevance": {
                    "operational_excellence": 0.7,
                    "security": 1.0,
                    "reliability": 0.8,
                    "performance_efficiency": 0.6,
                    "cost_optimization": 0.7,
                    "sustainability": 0.6
                },
                "keywords": ["kms", "key management", "encryption", "cryptographic"]
            }
            # Add more services as needed
        }

    def _load_architecture_patterns(self) -> Dict[str, Any]:
        """Load common architecture patterns and their WAFR implications."""
        return {
            "microservices": {
                "description": "Application broken into small, independent services",
                "indicators": ["microservice", "service mesh", "api gateway", "container", "kubernetes"],
                "wafr_implications": {
                    "operational_excellence": ["Improved deployment flexibility", "Better monitoring granularity"],
                    "security": ["Reduced blast radius", "Fine-grained access control"],
                    "reliability": ["Fault isolation", "Independent scaling"],
                    "performance_efficiency": ["Optimized resource usage", "Technology diversity"],
                    "cost_optimization": ["Pay for what you use", "Independent scaling"],
                    "sustainability": ["Efficient resource utilization", "Right-sized services"]
                }
            },
            "serverless": {
                "description": "Event-driven architecture using managed services",
                "indicators": ["lambda", "serverless", "event-driven", "api gateway", "step functions"],
                "wafr_implications": {
                    "operational_excellence": ["Reduced operational overhead", "Automatic scaling"],
                    "security": ["Built-in security features", "No server management"],
                    "reliability": ["Automatic fault tolerance", "Built-in redundancy"],
                    "performance_efficiency": ["Automatic scaling", "Optimized runtime"],
                    "cost_optimization": ["Pay-per-use pricing", "No idle costs"],
                    "sustainability": ["Shared infrastructure", "Efficient resource usage"]
                }
            },
            "multi-tier": {
                "description": "Traditional three-tier architecture",
                "indicators": ["web tier", "application tier", "database tier", "load balancer"],
                "wafr_implications": {
                    "operational_excellence": ["Clear separation of concerns", "Standardized deployment"],
                    "security": ["Layer-based security", "Network segmentation"],
                    "reliability": ["Redundancy at each tier", "Load distribution"],
                    "performance_efficiency": ["Caching strategies", "Horizontal scaling"],
                    "cost_optimization": ["Right-sized tiers", "Reserved instances"],
                    "sustainability": ["Efficient resource allocation", "Shared resources"]
                }
            },
            "event_driven": {
                "description": "Loose coupling through events and messaging",
                "indicators": ["event", "message queue", "sns", "sqs", "eventbridge", "kinesis"],
                "wafr_implications": {
                    "operational_excellence": ["Loose coupling", "Asynchronous processing"],
                    "security": ["Reduced attack surface", "Message encryption"],
                    "reliability": ["Fault tolerance", "Message durability"],
                    "performance_efficiency": ["Asynchronous processing", "Load smoothing"],
                    "cost_optimization": ["Efficient resource usage", "Pay-per-message"],
                    "sustainability": ["Efficient processing", "Reduced idle time"]
                }
            }
        }

    def _load_wafr_keywords(self) -> Dict[str, List[str]]:
        """Load keywords relevant to each WAFR pillar."""
        return {
            "operational_excellence": [
                "monitoring", "logging", "automation", "ci/cd", "deployment", "pipeline",
                "observability", "metrics", "alerting", "incident response", "runbook",
                "cloudwatch", "cloudtrail", "systems manager", "config"
            ],
            "security": [
                "encryption", "authentication", "authorization", "firewall", "security group",
                "iam", "kms", "certificate", "ssl", "tls", "vpc", "private", "access control",
                "compliance", "audit", "governance", "secrets manager", "parameter store"
            ],
            "reliability": [
                "backup", "disaster recovery", "multi-az", "multi-region", "redundancy",
                "fault tolerance", "auto scaling", "load balancer", "health check",
                "circuit breaker", "retry", "timeout", "resilience", "rpo", "rto"
            ],
            "performance_efficiency": [
                "caching", "cdn", "database optimization", "indexing", "connection pooling",
                "lazy loading", "compression", "minification", "elastic", "auto scaling",
                "performance testing", "load testing", "benchmarking", "latency", "throughput"
            ],
            "cost_optimization": [
                "reserved instance", "spot instance", "right sizing", "lifecycle policy",
                "storage class", "data transfer", "cost monitoring", "budget", "billing",
                "cost explorer", "trusted advisor", "savings plan", "cost allocation"
            ],
            "sustainability": [
                "carbon footprint", "energy efficient", "renewable energy", "green",
                "environmental impact", "resource efficiency", "waste reduction",
                "sustainable", "eco-friendly", "carbon neutral", "emission"
            ]
        }

    async def parse_solution(
        self,
        solution_text: str,
        business_requirements: Optional[str] = None,
        compliance_requirements: Optional[List[str]] = None,
        ctx: Optional[Context] = None
    ) -> SolutionAnalysis:
        """
        Parse solution text and extract WAFR-relevant information.

        Args:
            solution_text: The solution description text
            business_requirements: Additional business context
            compliance_requirements: List of compliance standards
            ctx: MCP context for logging

        Returns:
            SolutionAnalysis object with extracted information
        """
        if ctx:
            await ctx.info(f"Starting solution text analysis (length: {len(solution_text)} chars)")

        # Generate unique solution ID
        import hashlib
        solution_id = hashlib.md5(solution_text.encode()).hexdigest()[:8]

        # Extract AWS services
        aws_services = await self._identify_aws_services(solution_text, ctx)

        # Identify architecture patterns
        patterns = await self._identify_architecture_patterns(solution_text, ctx)

        # Extract requirements by pillar
        security_reqs = await self._extract_security_requirements(solution_text, ctx)
        performance_reqs = await self._extract_performance_requirements(solution_text, ctx)
        cost_considerations = await self._extract_cost_considerations(solution_text, ctx)
        sustainability_aspects = await self._extract_sustainability_aspects(solution_text, ctx)

        # Analyze data flows
        data_flows = await self._analyze_data_flows(solution_text, aws_services, ctx)

        # Extract business context
        business_context = await self._extract_business_context(
            solution_text, business_requirements, ctx
        )

        # Process compliance requirements
        compliance_reqs = compliance_requirements or []
        if compliance_requirements:
            compliance_reqs.extend(await self._extract_compliance_from_text(solution_text, ctx))

        analysis = SolutionAnalysis(
            solution_id=solution_id,
            aws_services=aws_services,
            architecture_patterns=patterns,
            data_flows=data_flows,
            security_requirements=security_reqs,
            performance_requirements=performance_reqs,
            cost_considerations=cost_considerations,
            compliance_requirements=compliance_reqs,
            sustainability_aspects=sustainability_aspects,
            business_context=business_context
        )

        if ctx:
            await ctx.info(f"Solution analysis complete: {len(aws_services)} services, {len(patterns)} patterns identified")

        return analysis

    async def _identify_aws_services(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[AWSService]:
        """Identify AWS services mentioned in the text."""
        services = []
        text_lower = text.lower()

        for service_key, service_data in self.aws_services_data.items():
            confidence = 0.0
            contexts = []

            # Check for service keywords
            for keyword in service_data["keywords"]:
                if keyword in text_lower:
                    confidence += 0.2
                    # Find context around the keyword
                    pattern = re.compile(rf'.{{0,50}}{re.escape(keyword)}.{{0,50}}', re.IGNORECASE)
                    matches = pattern.findall(text)
                    contexts.extend(matches)

            # Check for full service name
            if service_data["full_name"].lower() in text_lower:
                confidence += 0.4

            # Boost confidence based on context
            if service_data["category"] in text_lower:
                confidence += 0.1

            if confidence > 0.3:  # Threshold for service identification
                service = AWSService(
                    name=service_key,
                    service_type=service_data["category"],
                    confidence=min(confidence, 1.0),
                    context="; ".join(contexts[:3]),  # First 3 contexts
                    pillar_relevance=service_data["pillar_relevance"]
                )
                services.append(service)

        return sorted(services, key=lambda x: x.confidence, reverse=True)

    async def _identify_architecture_patterns(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[ArchitecturePattern]:
        """Identify architecture patterns in the solution."""
        patterns = []
        text_lower = text.lower()

        for pattern_name, pattern_data in self.architecture_patterns.items():
            confidence = 0.0

            # Check for pattern indicators
            for indicator in pattern_data["indicators"]:
                if indicator in text_lower:
                    confidence += 0.2

            # Check for pattern description keywords
            description_words = pattern_data["description"].lower().split()
            for word in description_words:
                if len(word) > 3 and word in text_lower:
                    confidence += 0.1

            if confidence > 0.4:  # Threshold for pattern identification
                # Find services involved in this pattern
                services_involved = []
                for service_key, service_data in self.aws_services_data.items():
                    for keyword in service_data["keywords"]:
                        if keyword in text_lower:
                            services_involved.append(service_key)
                            break

                pattern = ArchitecturePattern(
                    pattern_name=pattern_name,
                    description=pattern_data["description"],
                    services_involved=list(set(services_involved)),
                    wafr_implications=pattern_data["wafr_implications"]
                )
                patterns.append(pattern)

        return patterns

    async def _extract_security_requirements(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[str]:
        """Extract security-related requirements from the text."""
        requirements = []
        text_lower = text.lower()

        security_keywords = self.wafr_keywords["security"]

        # Look for security-related sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in security_keywords:
                if keyword in sentence_lower:
                    requirements.append(sentence.strip())
                    break

        # Remove duplicates and empty strings
        return list(set([req for req in requirements if req]))

    async def _extract_performance_requirements(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[str]:
        """Extract performance-related requirements from the text."""
        requirements = []
        text_lower = text.lower()

        performance_keywords = self.wafr_keywords["performance_efficiency"]

        # Look for performance-related sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in performance_keywords:
                if keyword in sentence_lower:
                    requirements.append(sentence.strip())
                    break

        return list(set([req for req in requirements if req]))

    async def _extract_cost_considerations(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[str]:
        """Extract cost-related considerations from the text."""
        considerations = []
        text_lower = text.lower()

        cost_keywords = self.wafr_keywords["cost_optimization"]

        # Look for cost-related sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in cost_keywords:
                if keyword in sentence_lower:
                    considerations.append(sentence.strip())
                    break

        return list(set([con for con in considerations if con]))

    async def _extract_sustainability_aspects(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[str]:
        """Extract sustainability-related aspects from the text."""
        aspects = []
        text_lower = text.lower()

        sustainability_keywords = self.wafr_keywords["sustainability"]

        # Look for sustainability-related sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for keyword in sustainability_keywords:
                if keyword in sentence_lower:
                    aspects.append(sentence.strip())
                    break

        return list(set([asp for asp in aspects if asp]))

    async def _analyze_data_flows(
        self,
        text: str,
        services: List[AWSService],
        ctx: Optional[Context] = None
    ) -> List[Dict[str, Any]]:
        """Analyze data flows between services."""
        flows = []

        # Simple data flow analysis based on common patterns
        flow_patterns = [
            r'(\w+)\s+(?:sends|transmits|transfers|streams)\s+(?:data\s+)?to\s+(\w+)',
            r'(\w+)\s+(?:receives|gets|fetches)\s+(?:data\s+)?from\s+(\w+)',
            r'data\s+flows?\s+from\s+(\w+)\s+to\s+(\w+)',
            r'(\w+)\s+(?:writes|stores)\s+(?:data\s+)?(?:in|to)\s+(\w+)'
        ]

        service_names = [s.name for s in services]

        for pattern in flow_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                source, destination = match.groups()

                # Try to map to identified services
                source_service = self._map_to_service(source, service_names)
                dest_service = self._map_to_service(destination, service_names)

                if source_service or dest_service:
                    flow = {
                        "source": source_service or source,
                        "destination": dest_service or destination,
                        "context": match.group(0),
                        "confidence": 0.7 if source_service and dest_service else 0.4
                    }
                    flows.append(flow)

        return flows

    def _map_to_service(self, text: str, service_names: List[str]) -> Optional[str]:
        """Map text to an identified AWS service."""
        text_lower = text.lower()

        # Direct match
        if text_lower in service_names:
            return text_lower

        # Check against service keywords
        for service_name in service_names:
            if service_name in self.aws_services_data:
                for keyword in self.aws_services_data[service_name]["keywords"]:
                    if keyword in text_lower:
                        return service_name

        return None

    async def _extract_business_context(
        self,
        solution_text: str,
        business_requirements: Optional[str],
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Extract business context and requirements."""
        context = {
            "industry": None,
            "scale": None,
            "criticality": None,
            "geographic_scope": None,
            "business_drivers": []
        }

        text_to_analyze = solution_text
        if business_requirements:
            text_to_analyze += " " + business_requirements

        text_lower = text_to_analyze.lower()

        # Industry indicators
        industries = {
            "financial": ["bank", "financial", "fintech", "payment", "trading"],
            "healthcare": ["healthcare", "medical", "patient", "hospital", "hipaa"],
            "retail": ["retail", "ecommerce", "shopping", "customer", "order"],
            "government": ["government", "public sector", "federal", "agency"],
            "education": ["education", "school", "university", "student", "learning"]
        }

        for industry, keywords in industries.items():
            if any(keyword in text_lower for keyword in keywords):
                context["industry"] = industry
                break

        # Scale indicators
        if any(word in text_lower for word in ["enterprise", "large scale", "millions", "global"]):
            context["scale"] = "enterprise"
        elif any(word in text_lower for word in ["startup", "small", "prototype", "poc"]):
            context["scale"] = "startup"
        else:
            context["scale"] = "medium"

        # Criticality indicators
        if any(word in text_lower for word in ["mission critical", "high availability", "24/7"]):
            context["criticality"] = "high"
        elif any(word in text_lower for word in ["best effort", "development", "test"]):
            context["criticality"] = "low"
        else:
            context["criticality"] = "medium"

        return context

    async def _extract_compliance_from_text(
        self,
        text: str,
        ctx: Optional[Context] = None
    ) -> List[str]:
        """Extract compliance requirements mentioned in the text."""
        compliance_standards = []
        text_lower = text.lower()

        known_standards = {
            "sox": ["sox", "sarbanes-oxley"],
            "pci-dss": ["pci", "pci-dss", "payment card"],
            "hipaa": ["hipaa", "health insurance"],
            "gdpr": ["gdpr", "general data protection"],
            "iso27001": ["iso 27001", "iso27001"],
            "fedramp": ["fedramp", "federal risk"],
            "fisma": ["fisma", "federal information security"]
        }

        for standard, keywords in known_standards.items():
            if any(keyword in text_lower for keyword in keywords):
                compliance_standards.append(standard)

        return compliance_standards


# Utility functions for external use
async def parse_solution_text(
    solution_text: str,
    business_requirements: Optional[str] = None,
    compliance_requirements: Optional[List[str]] = None,
    ctx: Optional[Context] = None
) -> SolutionAnalysis:
    """
    Parse solution text and return analysis.

    This is the main entry point for solution text parsing.
    """
    parser = SolutionTextParser()
    return await parser.parse_solution(
        solution_text, business_requirements, compliance_requirements, ctx
    )


def get_service_pillar_relevance(service_name: str) -> Dict[str, float]:
    """Get WAFR pillar relevance for a specific AWS service."""
    parser = SolutionTextParser()
    if service_name in parser.aws_services_data:
        return parser.aws_services_data[service_name]["pillar_relevance"]
    return {}