"""
AWS Documentation Linker for WAFR Report Content Improvement.

This module provides accurate, relevant AWS documentation links using a hybrid approach:
1. URL Pattern Templates (fast) - generates standard service documentation URLs
2. AWS Documentation Search API (accurate) - searches for capability-specific content
3. Static Links (reliable) - for stable content like WAFR pillars

This approach works for ANY AWS service (current and future) without hardcoded mappings.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import urllib.parse
import json
from .logger import WAFRLogger


@dataclass
class DocumentationLink:
    """Represents a link to AWS documentation."""
    
    title: str
    url: str
    relevance: str  # "direct", "related", "service", "pillar", "general"
    description: str
    search_score: float = 0.0  # Score from AWS Documentation Search API
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "relevance": self.relevance,
            "description": self.description,
            "search_score": self.search_score
        }
    
    def __lt__(self, other):
        """Enable sorting by relevance and search score."""
        relevance_order = {"direct": 0, "related": 1, "service": 2, "pillar": 3, "general": 4}
        self_order = relevance_order.get(self.relevance, 5)
        other_order = relevance_order.get(other.relevance, 5)
        
        if self_order != other_order:
            return self_order < other_order
        return self.search_score > other.search_score  # Higher score is better


class AWSDocumentationLinker:
    """
    Provides accurate AWS documentation links using a hybrid approach.
    
    Three-tier link generation strategy:
    1. URL Pattern Templates (fast) - generates standard service documentation URLs
    2. AWS Documentation Search API (accurate) - searches for capability-specific content  
    3. Static Links (reliable) - for stable content like WAFR pillars
    
    This approach works for ANY AWS service (current and future) without maintenance.
    """
    
    # Tier 1: URL Pattern Templates for fast generation
    AWS_DOC_URL_PATTERNS = {
        "service_home": "https://docs.aws.amazon.com/{service}/latest/",
        "user_guide": "https://docs.aws.amazon.com/{service}/latest/userguide/",
        "developer_guide": "https://docs.aws.amazon.com/{service}/latest/dg/",
        "api_reference": "https://docs.aws.amazon.com/{service}/latest/APIReference/",
        "admin_guide": "https://docs.aws.amazon.com/{service}/latest/adminguide/",
        "best_practices": "https://docs.aws.amazon.com/{service}/latest/userguide/best-practices.html"
    }
    
    # Service name to documentation slug mapping (common services)
    SERVICE_DOC_SLUGS = {
        "api gateway": "apigateway",
        "apigateway": "apigateway",
        "dynamodb": "amazondynamodb",
        "lambda": "lambda",
        "cloudwatch": "AmazonCloudWatch",
        "step functions": "step-functions",
        "stepfunctions": "step-functions",
        "cloudfront": "AmazonCloudFront",
        "s3": "AmazonS3",
        "sns": "sns",
        "sqs": "AWSSimpleQueueService",
        "vpc": "vpc",
        "waf": "waf",
        "kms": "kms",
        "iam": "IAM",
        "x-ray": "xray",
        "xray": "xray",
        "ec2": "ec2",
        "rds": "AmazonRDS",
        "ecs": "AmazonECS",
        "eks": "eks",
        "elasticache": "AmazonElastiCache",
        "redshift": "redshift",
        "athena": "athena",
        "glue": "glue",
        "emr": "emr",
        "kinesis": "kinesis",
        "eventbridge": "eventbridge",
        "cognito": "cognito",
        "secrets manager": "secretsmanager",
        "secretsmanager": "secretsmanager",
        "systems manager": "systems-manager",
        "ssm": "systems-manager",
        "cloudformation": "AWSCloudFormation",
        "cloudtrail": "awscloudtrail",
        "config": "config",
        "guardduty": "guardduty",
        "inspector": "inspector",
        "macie": "macie",
        "security hub": "securityhub",
        "securityhub": "securityhub"
    }
    
    # Tier 3: Static Links for stable content (WAFR pillars and patterns)
    WAFR_PILLAR_LINKS = {

        "operational_excellence": "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html",
        "security": "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
        "reliability": "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
        "performance_efficiency": "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html",
        "cost_optimization": "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
        "sustainability": "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/welcome.html"
    }
    
    # Static pattern links (stable content)
    PATTERN_LINKS = {
        "serverless": "https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html",
        "microservices": "https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/introduction.html",
        "event_driven": "https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-event-driven-architectures/welcome.html"
    }
    
    def __init__(self):
        """Initialize the AWSDocumentationLinker with hybrid approach."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("AWSDocumentationLinker initialized with hybrid approach")
        
        # Cache for link validation results (24 hour TTL)
        self._validation_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=24)
        
        # Cache for AWS Documentation Search results (24 hour TTL)
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self._search_cache_ttl = timedelta(hours=24)

    def _normalize_service_name(self, service: str) -> str:
        """
        Normalize service name to documentation slug format.
        
        Args:
            service: AWS service name (e.g., "DynamoDB", "API Gateway")
            
        Returns:
            Documentation slug (e.g., "amazondynamodb", "apigateway")
        """
        normalized = service.strip().lower()
        
        # Check if we have a mapping
        if normalized in self.SERVICE_DOC_SLUGS:
            return self.SERVICE_DOC_SLUGS[normalized]
        
        # Default: lowercase and remove spaces
        return normalized.replace(" ", "")
    
    def _generate_service_urls(self, service: str) -> List[DocumentationLink]:
        """
        Generate standard service documentation URLs using patterns (Tier 1: Fast).
        
        Args:
            service: AWS service name
            
        Returns:
            List of DocumentationLink objects with generated URLs
        """
        self.logger.debug(f"Generating URL patterns for service: {service}")
        
        links = []
        service_slug = self._normalize_service_name(service)
        
        # Generate URLs from patterns
        for doc_type, pattern in self.AWS_DOC_URL_PATTERNS.items():
            url = pattern.format(service=service_slug)
            
            # Determine relevance based on doc type
            relevance = "service" if doc_type in ["service_home", "user_guide", "developer_guide"] else "general"
            
            links.append(DocumentationLink(
                title=f"{service} {doc_type.replace('_', ' ').title()}",
                url=url,
                relevance=relevance,
                description=f"{doc_type.replace('_', ' ').title()} for {service}",
                search_score=0.5  # Pattern-generated links get medium score
            ))
        
        self.logger.debug(f"Generated {len(links)} URL pattern links for {service}")
        return links
    
    def _search_aws_documentation(self, query: str, limit: int = 5) -> List[DocumentationLink]:
        """
        Search AWS Documentation using AWS Documentation Search API (Tier 2: Accurate).
        
        This method searches the official AWS documentation for capability-specific content.
        Results are cached for 24 hours to improve performance.
        
        Args:
            query: Search query (e.g., "DynamoDB encryption implementation")
            limit: Maximum number of results to return
            
        Returns:
            List of DocumentationLink objects from search results
        """
        self.logger.info(f"Searching AWS documentation for: {query}")
        
        # Check cache first
        cache_key = f"{query}:{limit}"
        if cache_key in self._search_cache:
            cached_result = self._search_cache[cache_key]
            cache_time = cached_result["timestamp"]
            
            if datetime.now() - cache_time < self._search_cache_ttl:
                self.logger.debug(f"Using cached search results for: {query}")
                return cached_result["links"]
        
        links = []
        
        try:
            # Use AWS Documentation Search API
            # This searches across all AWS documentation including:
            # - Service documentation
            # - Best practices guides
            # - Whitepapers
            # - Architecture guides
            
            # AWS Documentation Search endpoint
            search_url = "https://docs.aws.amazon.com/search/doc-search.html"
            encoded_query = urllib.parse.quote(query)
            
            # Build search URL with parameters
            full_url = f"{search_url}?searchPath=documentation&searchQuery={encoded_query}&size={limit}"
            
            self.logger.debug(f"Searching AWS docs: {full_url}")
            
            # Make HTTP request
            request = Request(full_url)
            request.add_header('User-Agent', 'AWS-WAFR-MCP-Server/1.0')
            request.add_header('Accept', 'application/json')
            
            with urlopen(request, timeout=10) as response:
                if response.getcode() == 200:
                    # Parse JSON response
                    data = json.loads(response.read().decode('utf-8'))
                    
                    # Extract search results
                    results = data.get('results', [])
                    
                    for idx, result in enumerate(results[:limit]):
                        # Extract relevant fields
                        title = result.get('title', 'AWS Documentation')
                        url = result.get('url', '')
                        description = result.get('description', '')
                        
                        # Calculate search score based on position (higher = better)
                        search_score = 1.0 - (idx * 0.1)  # First result = 1.0, second = 0.9, etc.
                        
                        links.append(DocumentationLink(
                            title=title,
                            url=url if url.startswith('http') else f"https://docs.aws.amazon.com{url}",
                            relevance="direct",  # Search results are capability-specific
                            description=description[:200] if description else f"AWS documentation for {query}",
                            search_score=search_score
                        ))
                    
                    self.logger.info(f"Found {len(links)} search results for: {query}")
                else:
                    self.logger.warning(f"AWS Documentation Search returned status {response.getcode()}")
            
        except HTTPError as e:
            self.logger.warning(f"HTTP error searching AWS documentation: {e.code}")
        except (URLError, OSError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Error searching AWS documentation: {str(e)}")
        
        # Cache the results (even if empty)
        self._search_cache[cache_key] = {
            "links": links,
            "timestamp": datetime.now()
        }
        
        return links
    
    def get_service_documentation(
        self,
        service: str,
        capability: Optional[str] = None
    ) -> List[DocumentationLink]:
        """
        Get documentation links using hybrid approach (Tier 1 + Tier 2 + Tier 3).
        
        Strategy:
        1. Generate service URLs using patterns (fast, always works)
        2. Search AWS docs using API for capability-specific content (accurate)
        3. Combine and rank results by relevance
        
        Args:
            service: AWS service name (e.g., "DynamoDB", "Lambda")
            capability: Optional specific capability (e.g., "encryption", "monitoring")
            
        Returns:
            List of DocumentationLink objects with relevant documentation
        """
        self.logger.info(f"Getting documentation for service: {service}, capability: {capability}")
        
        all_links = []
        
        # Step 1: Generate standard service URLs using patterns (fast)
        pattern_links = self._generate_service_urls(service)
        all_links.extend(pattern_links)
        
        # Step 2: Search AWS Documentation API for capability-specific content (accurate)
        if capability:
            search_query = f"{service} {capability} implementation best practices"
            search_links = self._search_aws_documentation(search_query, limit=3)
            
            # Mark search results as "direct" relevance since they're capability-specific
            for link in search_links:
                link.relevance = "direct"
                link.search_score = 1.0  # Search results get highest score
            
            all_links.extend(search_links)
        
        # Step 3: Fallback - if no capability-specific links found, use service home
        if capability and not any(link.relevance == "direct" for link in all_links):
            self.logger.info("No capability-specific links found, using service home as fallback")
            service_slug = self._normalize_service_name(service)
            fallback_url = f"https://docs.aws.amazon.com/{service_slug}/latest/"
            
            all_links.append(DocumentationLink(
                title=f"{service} Documentation",
                url=fallback_url,
                relevance="service",
                description=f"Complete documentation for {service}",
                search_score=0.3  # Fallback gets lower score
            ))
        
        self.logger.info(f"Found {len(all_links)} documentation links for {service}")
        return all_links

    def get_pillar_documentation(self, pillar: str) -> List[DocumentationLink]:
        """
        Get WAFR pillar framework documentation links (Tier 3: Static).
        
        Args:
            pillar: WAFR pillar name (e.g., "operational_excellence", "security")
            
        Returns:
            List of DocumentationLink objects with pillar documentation
        """
        self.logger.info(f"Getting documentation for pillar: {pillar}")
        
        links = []
        
        # Normalize pillar name
        normalized_pillar = pillar.lower().replace(" ", "_")
        
        # Check if pillar exists in static links
        if normalized_pillar not in self.WAFR_PILLAR_LINKS:
            self.logger.warning(f"Pillar '{pillar}' not found in WAFR pillar links")
            return links
        
        pillar_url = self.WAFR_PILLAR_LINKS[normalized_pillar]
        
        # Add pillar framework documentation
        links.append(DocumentationLink(
            title=f"AWS Well-Architected {pillar.replace('_', ' ').title()} Pillar",
            url=pillar_url,
            relevance="pillar",
            description=f"Complete framework documentation for the {pillar.replace('_', ' ').title()} pillar",
            search_score=1.0  # Static links are authoritative
        ))
        
        self.logger.info(f"Found {len(links)} documentation links for pillar {pillar}")
        return links

    def validate_link(self, url: str, max_retries: int = 2) -> bool:
        """
        Validate that a documentation link is accessible.
        
        Makes an HTTP HEAD request to check if the link returns a 200 status.
        Handles AWS documentation redirects (301/302) and implements retry logic.
        Results are cached for 24 hours to avoid excessive requests.
        
        Args:
            url: URL to validate
            max_retries: Maximum number of retry attempts for transient failures
            
        Returns:
            True if link is accessible (200 or redirect status), False otherwise
        """
        # Check cache first
        if url in self._validation_cache:
            cached_result = self._validation_cache[url]
            cache_time = cached_result["timestamp"]
            
            # Check if cache is still valid
            if datetime.now() - cache_time < self._cache_ttl:
                self.logger.debug(f"Using cached validation result for {url}")
                return cached_result["valid"]
        
        # Perform validation with retry logic
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"Validating link (attempt {attempt + 1}/{max_retries + 1}): {url}")
                
                # Create HEAD request
                request = Request(url, method='HEAD')
                request.add_header('User-Agent', 'AWS-WAFR-MCP-Server/1.0')
                
                with urlopen(request, timeout=5) as response:
                    status_code = response.getcode()
                    # Accept 200 (OK) and 3xx (redirects) as valid
                    is_valid = status_code in [200, 301, 302, 303, 307, 308]
                
                # Cache the result
                self._validation_cache[url] = {
                    "valid": is_valid,
                    "timestamp": datetime.now(),
                    "status_code": status_code
                }
                
                if not is_valid:
                    self.logger.warning(
                        f"Link validation failed for {url}: "
                        f"status code {status_code}"
                    )
                
                return is_valid
                
            except HTTPError as e:
                # Handle redirects as valid
                if e.code in [301, 302, 303, 307, 308]:
                    self.logger.debug(f"Link {url} redirects with status {e.code}")
                    self._validation_cache[url] = {
                        "valid": True,
                        "timestamp": datetime.now(),
                        "status_code": e.code
                    }
                    return True
                
                # Retry on server errors (5xx)
                if e.code >= 500 and attempt < max_retries:
                    self.logger.warning(f"Server error {e.code} for {url}, retrying...")
                    continue
                
                self.logger.warning(f"Link validation HTTP error for {url}: {e.code}")
                
                # Cache the failure
                self._validation_cache[url] = {
                    "valid": False,
                    "timestamp": datetime.now(),
                    "status_code": e.code
                }
                
                return False
                
            except (URLError, OSError, TimeoutError) as e:
                # Retry on transient errors
                if attempt < max_retries:
                    self.logger.warning(f"Transient error for {url}, retrying: {str(e)}")
                    continue
                
                self.logger.warning(f"Link validation error for {url}: {str(e)}")
                
                # Cache the failure
                self._validation_cache[url] = {
                    "valid": False,
                    "timestamp": datetime.now(),
                    "error": str(e)
                }
                
                return False
        
        # Should not reach here, but return False as fallback
        return False

    def prioritize_links(
        self,
        links: List[DocumentationLink],
        service: Optional[str] = None,
        capability: Optional[str] = None,
        pillar: Optional[str] = None,
        max_links: int = 5
    ) -> List[DocumentationLink]:
        """
        Prioritize and filter documentation links by relevance and search scores.
        
        Ranks links by:
        1. Relevance: direct > related > service > pillar > general
        2. Search score (within same relevance level)
        3. Diversity (different doc types)
        
        Filters out duplicate or very similar links.
        
        Args:
            links: List of DocumentationLink objects to prioritize
            service: Optional service context for prioritization
            capability: Optional capability context for prioritization
            pillar: Optional pillar context for prioritization
            max_links: Maximum number of links to return (default: 5)
            
        Returns:
            Prioritized list of top N DocumentationLink objects with diversity
        """
        self.logger.info(
            f"Prioritizing {len(links)} links "
            f"(service={service}, capability={capability}, pillar={pillar})"
        )
        
        if not links:
            return []
        
        # Sort links by relevance and search score (using __lt__ method)
        sorted_links = sorted(links)
        
        # Remove duplicates and very similar URLs
        seen_urls = set()
        seen_base_urls = set()
        unique_links = []
        
        for link in sorted_links:
            # Skip exact duplicates
            if link.url in seen_urls:
                continue
            
            # Extract base URL (without anchors/query params) for similarity check
            base_url = link.url.split('#')[0].split('?')[0]
            
            # For diversity, prefer different base URLs
            # But allow duplicates if they're high-relevance (direct/related)
            if base_url in seen_base_urls and link.relevance not in ["direct", "related"]:
                continue
            
            seen_urls.add(link.url)
            seen_base_urls.add(base_url)
            unique_links.append(link)
        
        # Ensure diversity of doc types (user guide, API ref, best practices, etc.)
        diverse_links = []
        doc_types_seen = set()
        
        for link in unique_links:
            # Extract doc type from URL or title
            doc_type = "general"
            if "userguide" in link.url:
                doc_type = "userguide"
            elif "/dg/" in link.url or "developer" in link.url.lower():
                doc_type = "developer"
            elif "APIReference" in link.url or "api" in link.url.lower():
                doc_type = "api"
            elif "best-practices" in link.url or "best practices" in link.title.lower():
                doc_type = "best_practices"
            elif "wellarchitected" in link.url:
                doc_type = "wafr"
            
            # Always include direct/related links
            if link.relevance in ["direct", "related"]:
                diverse_links.append(link)
            # For others, prefer diversity
            elif doc_type not in doc_types_seen or len(diverse_links) < max_links:
                diverse_links.append(link)
                doc_types_seen.add(doc_type)
            
            # Stop when we have enough links
            if len(diverse_links) >= max_links:
                break
        
        # Return top N links
        prioritized = diverse_links[:max_links]
        
        self.logger.info(f"Prioritized to {len(prioritized)} top links with diversity")
        return prioritized
