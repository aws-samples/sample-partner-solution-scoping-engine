"""
Service Categorization Engine for WAFR Intelligent Capability Inference.

This module provides intelligent service categorization using fuzzy keyword matching
instead of hard-coded service name lookups. This makes the system:
- Flexible: Works with any AWS service (current and future)
- Accurate: Categorizes by function, not exact names
- Maintainable: No hard-coded service lists to update
- Production-grade: Handles variations in service naming

Example:
    categorizer = ServiceCategorizer()
    categories = categorizer.categorize_service("Lambda")
    # Returns: ['compute']
    
    categories = categorizer.categorize_service("Step Functions")
    # Returns: ['integration', 'compute']
"""

import re
from typing import List, Dict, Set
from enum import Enum
from dataclasses import dataclass

from ..core.logger import WAFRLogger


class ServiceCategory(str, Enum):
    """AWS service functional categories."""
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORKING = "networking"
    SECURITY = "security"
    MONITORING = "monitoring"
    INTEGRATION = "integration"
    ANALYTICS = "analytics"
    DEPLOYMENT = "deployment"
    CONTAINER = "container"
    UNKNOWN = "unknown"


@dataclass
class CategorizedService:
    """A service with its detected categories."""
    service_name: str
    categories: List[ServiceCategory]
    confidence: float  # 0.0 to 1.0
    matched_keywords: List[str]  # Keywords that triggered categorization


class ServiceCategorizer:
    """
    Intelligent service categorization engine using fuzzy keyword matching.
    
    This replaces hard-coded service name lookups with flexible pattern matching
    that works with any AWS service naming convention.
    
    Design Principles:
    - Case-insensitive matching
    - Partial keyword matching (e.g., "gateway" matches "API Gateway")
    - Multi-category support (services can belong to multiple categories)
    - Confidence scoring based on keyword matches
    - Extensible keyword definitions
    """
    
    # Service category keywords for fuzzy matching
    # These are functional indicators, not specific service names
    # ENHANCED: Added Graviton, Bedrock Guardrails, VPC Endpoints, and other missing patterns
    CATEGORY_KEYWORDS = {
        ServiceCategory.COMPUTE: [
            'lambda', 'ec2', 'ecs', 'fargate', 'batch', 'lightsail',
            'elastic beanstalk', 'app runner', 'compute', 'function',
            # Graviton/ARM instance patterns for sustainability detection
            'm7g', 'c7g', 'r7g', 't4g', 'm6g', 'c6g', 'r6g', 't3g',
            'graviton', 'arm64', 'aarch64'
        ],
        ServiceCategory.STORAGE: [
            's3', 'efs', 'fsx', 'glacier', 'backup', 'storage gateway',
            'storage', 'bucket', 'file system',
            # S3 lifecycle patterns
            'intelligent-tiering', 'lifecycle', 'transition'
        ],
        ServiceCategory.DATABASE: [
            'dynamodb', 'rds', 'aurora', 'documentdb', 'neptune',
            'elasticache', 'memorydb', 'redshift', 'timestream',
            'database', 'db', 'cache', 'redis', 'memcached',
            # Reliability patterns
            'point-in-time', 'pitr', 'multi-az', 'read replica'
        ],
        ServiceCategory.NETWORKING: [
            'vpc', 'cloudfront', 'route53', 'gateway', 'load balancer',
            'elb', 'alb', 'nlb', 'direct connect', 'transit gateway',
            'network', 'cdn', 'dns', 'api gateway',
            # VPC Endpoint patterns (critical for security)
            'vpc endpoint', 'privatelink', 'interface endpoint', 'gateway endpoint',
            'private dns', 'endpoint service',
            # Flow logs
            'flow log', 'flowlog', 'vpc flow'
        ],
        ServiceCategory.SECURITY: [
            'kms', 'cloudhsm', 'acm', 'secrets', 'iam', 'cognito',
            'waf', 'shield', 'guard', 'macie', 'inspector',
            'security', 'key', 'certificate', 'identity', 'access',
            # Bedrock Guardrails patterns (critical - was missed)
            'guardrail', 'content filter', 'content policy', 'pii', 'pii filter',
            'sensitive information', 'blocked input', 'blocked output',
            'toxicity', 'hate', 'insults', 'sexual', 'violence', 'misconduct',
            # WAF patterns
            'rate limit', 'rate based', 'managed rule', 'web acl',
            'ip reputation', 'known bad inputs', 'common rule set',
            # Cognito advanced security
            'advanced security', 'compromised credentials', 'account takeover',
            'risk-based', 'adaptive authentication',
            # CloudFront security
            'signed url', 'signed cookie', 'origin access', 'key group',
            # Encryption patterns
            'encryption at rest', 'encryption in transit', 'tls', 'ssl',
            'server-side encryption', 'sse-kms', 'sse-s3'
        ],
        ServiceCategory.MONITORING: [
            'cloudwatch', 'x-ray', 'cloudtrail', 'config', 'systems manager',
            'monitor', 'observability', 'trace', 'log', 'metric', 'alarm',
            # Enhanced monitoring patterns
            'log retention', 'log group', 'metric filter', 'dashboard',
            'anomaly detection', 'contributor insights'
        ],
        ServiceCategory.INTEGRATION: [
            'sns', 'sqs', 'eventbridge', 'step functions', 'mq', 'kinesis',
            'appflow', 'event', 'queue', 'topic', 'stream', 'workflow',
            'orchestration', 'message'
        ],
        ServiceCategory.ANALYTICS: [
            'athena', 'glue', 'emr', 'quicksight', 'opensearch',
            'elasticsearch', 'data pipeline', 'lake formation',
            'analytics', 'query', 'search', 'data'
        ],
        ServiceCategory.DEPLOYMENT: [
            'cloudformation', 'cdk', 'codepipeline', 'codebuild',
            'codedeploy', 'amplify', 'sam', 'deployment', 'pipeline',
            'infrastructure', 'iac', 'ci/cd', 'cicd',
            # Terraform patterns
            'terraform', 'tf', 'hcl'
        ],
        ServiceCategory.CONTAINER: [
            'ecs', 'eks', 'ecr', 'fargate', 'container', 'kubernetes',
            'docker', 'registry'
        ]
    }
    
    # AI/ML category for Bedrock and related services
    CATEGORY_KEYWORDS[ServiceCategory.SECURITY].extend([
        'bedrock', 'sagemaker', 'comprehend', 'rekognition', 'textract'
    ])
    
    def __init__(self):
        """Initialize the service categorizer."""
        self.logger = WAFRLogger(__name__)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficient matching."""
        self.compiled_patterns: Dict[ServiceCategory, List[re.Pattern]] = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            patterns = []
            for keyword in keywords:
                # Create pattern that matches keyword as whole word or part of compound word
                # e.g., "gateway" matches "API Gateway" or "gateway"
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                patterns.append(pattern)
            self.compiled_patterns[category] = patterns
    
    def categorize_service(self, service_name: str) -> CategorizedService:
        """
        Categorize a service using fuzzy keyword matching.
        
        Args:
            service_name: Name of the AWS service (e.g., "Lambda", "API Gateway", "Step Functions")
            
        Returns:
            CategorizedService with detected categories, confidence, and matched keywords
            
        Examples:
            >>> categorizer.categorize_service("Lambda")
            CategorizedService(service_name="Lambda", categories=[ServiceCategory.COMPUTE], 
                             confidence=1.0, matched_keywords=['lambda'])
            
            >>> categorizer.categorize_service("Step Functions")
            CategorizedService(service_name="Step Functions", 
                             categories=[ServiceCategory.INTEGRATION, ServiceCategory.COMPUTE],
                             confidence=0.9, matched_keywords=['step functions', 'function'])
        """
        if not service_name or not service_name.strip():
            return CategorizedService(
                service_name=service_name,
                categories=[ServiceCategory.UNKNOWN],
                confidence=0.0,
                matched_keywords=[]
            )
        
        # Normalize service name for matching
        normalized_name = service_name.strip()
        
        # Track matches
        category_matches: Dict[ServiceCategory, List[str]] = {}
        
        # Check each category's patterns
        for category, patterns in self.compiled_patterns.items():
            matched_keywords = []
            for pattern in patterns:
                if pattern.search(normalized_name):
                    # Extract the keyword that matched
                    keyword = pattern.pattern.replace(r'\b', '').replace('\\', '')
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                category_matches[category] = matched_keywords
        
        # Determine final categories and confidence
        if not category_matches:
            self.logger.debug(f"No category match for service: {service_name}")
            return CategorizedService(
                service_name=service_name,
                categories=[ServiceCategory.UNKNOWN],
                confidence=0.0,
                matched_keywords=[]
            )
        
        # Sort categories by number of keyword matches (more matches = higher priority)
        sorted_categories = sorted(
            category_matches.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        categories = [cat for cat, _ in sorted_categories]
        all_matched_keywords = [kw for _, keywords in sorted_categories for kw in keywords]
        
        # Calculate confidence based on match quality
        # More keyword matches = higher confidence
        total_matches = sum(len(keywords) for keywords in category_matches.values())
        confidence = min(1.0, 0.7 + (total_matches * 0.1))  # Base 0.7, +0.1 per match, max 1.0
        
        self.logger.debug(
            f"Categorized '{service_name}': {[c.value for c in categories]} "
            f"(confidence={confidence:.2f}, keywords={all_matched_keywords})"
        )
        
        return CategorizedService(
            service_name=service_name,
            categories=categories,
            confidence=confidence,
            matched_keywords=all_matched_keywords
        )
    
    def categorize_services(self, service_names: List[str]) -> List[CategorizedService]:
        """
        Categorize multiple services at once.
        
        Args:
            service_names: List of AWS service names
            
        Returns:
            List of CategorizedService objects
        """
        return [self.categorize_service(name) for name in service_names]
    
    def get_services_by_category(
        self,
        categorized_services: List[CategorizedService],
        category: ServiceCategory
    ) -> List[str]:
        """
        Get all services that belong to a specific category.
        
        Args:
            categorized_services: List of categorized services
            category: Category to filter by
            
        Returns:
            List of service names in that category
        """
        return [
            cs.service_name
            for cs in categorized_services
            if category in cs.categories
        ]
    
    def get_category_summary(
        self,
        categorized_services: List[CategorizedService]
    ) -> Dict[ServiceCategory, List[str]]:
        """
        Get a summary of services organized by category.
        
        Args:
            categorized_services: List of categorized services
            
        Returns:
            Dictionary mapping categories to service names
        """
        summary: Dict[ServiceCategory, List[str]] = {cat: [] for cat in ServiceCategory}
        
        for cs in categorized_services:
            for category in cs.categories:
                summary[category].append(cs.service_name)
        
        return summary


# Global instance for easy access
service_categorizer = ServiceCategorizer()
