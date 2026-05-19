"""
Missing Capability Analyzer for WAFR Report Quality Enhancement.

This module identifies capabilities that are expected for each pillar but were not
detected in the architecture. It provides detailed analysis of gaps with importance
explanations and score impact calculations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.logger import WAFRLogger
from .models import MissingCapability


class MissingCapabilityAnalyzer:
    """
    Analyzes pillar assessments to identify missing capabilities.
    
    This component compares detected capabilities against expected capabilities
    for each pillar, considering architectural patterns to avoid false positives.
    
    Example:
        analyzer = MissingCapabilityAnalyzer()
        
        missing = analyzer.analyze_pillar_gaps(
            pillar="security",
            detected_capabilities=["encryption", "identity_access"],
            architecture_services=["Lambda", "DynamoDB", "S3"]
        )
        # Returns: List of MissingCapability objects
    """
    
    # Expected capabilities for each pillar with importance levels
    EXPECTED_CAPABILITIES = {
        "security": {
            "encryption": {
                "importance": "critical",
                "description": "Data encryption at rest and in transit",
                "why_important": "Protects sensitive data from unauthorized access and meets compliance requirements",
                "example_services": ["AWS KMS", "ACM", "CloudHSM"],
                "weight": 0.25
            },
            "identity_access": {
                "importance": "critical",
                "description": "Identity and access management controls",
                "why_important": "Ensures only authorized users and services can access resources",
                "example_services": ["IAM", "Cognito", "AWS SSO"],
                "weight": 0.20
            },
            "network_security": {
                "importance": "high",
                "description": "Network isolation and protection",
                "why_important": "Prevents unauthorized network access and protects against network-based attacks",
                "example_services": ["VPC", "Security Groups", "WAF", "Shield"],
                "weight": 0.20
            },
            "monitoring_detection": {
                "importance": "high",
                "description": "Security monitoring and threat detection",
                "why_important": "Enables early detection of security incidents and compliance violations",
                "example_services": ["CloudWatch", "GuardDuty", "Security Hub", "CloudTrail"],
                "weight": 0.20
            },
            "data_protection": {
                "importance": "high",
                "description": "Data classification and protection mechanisms",
                "why_important": "Ensures sensitive data is properly classified and protected throughout its lifecycle",
                "example_services": ["Macie", "KMS", "S3 encryption"],
                "weight": 0.15
            }
        },
        "reliability": {
            "redundancy": {
                "importance": "critical",
                "description": "High availability and fault tolerance",
                "why_important": "Ensures system continues operating even when components fail",
                "example_services": ["Multi-AZ RDS", "DynamoDB", "S3", "Auto Scaling"],
                "weight": 0.30
            },
            "monitoring_alerting": {
                "importance": "high",
                "description": "System monitoring and alerting",
                "why_important": "Enables proactive detection and response to system issues",
                "example_services": ["CloudWatch", "SNS", "EventBridge"],
                "weight": 0.25
            },
            "backup_recovery": {
                "importance": "critical",
                "description": "Backup and disaster recovery capabilities",
                "why_important": "Protects against data loss and enables recovery from failures",
                "example_services": ["AWS Backup", "RDS snapshots", "S3 versioning"],
                "weight": 0.20
            },
            "scaling": {
                "importance": "high",
                "description": "Auto-scaling and elasticity",
                "why_important": "Maintains performance during demand changes and optimizes resource usage",
                "example_services": ["Auto Scaling", "Lambda", "DynamoDB auto-scaling"],
                "weight": 0.25
            }
        },
        "performance_efficiency": {
            "caching": {
                "importance": "high",
                "description": "Content and data caching",
                "why_important": "Reduces latency and improves response times for frequently accessed data",
                "example_services": ["CloudFront", "ElastiCache", "DAX"],
                "weight": 0.25
            },
            "compute_optimization": {
                "importance": "high",
                "description": "Optimized compute resources",
                "why_important": "Ensures efficient use of compute resources for workload requirements",
                "example_services": ["Lambda", "Fargate", "EC2 instance types"],
                "weight": 0.25
            },
            "content_delivery": {
                "importance": "medium",
                "description": "Content delivery network",
                "why_important": "Delivers content to users with low latency from edge locations",
                "example_services": ["CloudFront", "Global Accelerator"],
                "weight": 0.25
            },
            "database_optimization": {
                "importance": "high",
                "description": "Database performance optimization",
                "why_important": "Ensures efficient data access and query performance",
                "example_services": ["DynamoDB", "Aurora", "RDS Performance Insights"],
                "weight": 0.25
            }
        },
        "cost_optimization": {
            "resource_optimization": {
                "importance": "high",
                "description": "Resource rightsizing and optimization",
                "why_important": "Eliminates waste and ensures resources match actual needs",
                "example_services": ["Compute Optimizer", "Lambda", "Auto Scaling"],
                "weight": 0.30
            },
            "managed_services": {
                "importance": "high",
                "description": "Use of managed services",
                "why_important": "Reduces operational overhead and total cost of ownership",
                "example_services": ["Lambda", "DynamoDB", "S3", "RDS"],
                "weight": 0.25
            },
            "pricing_models": {
                "importance": "medium",
                "description": "Cost-effective pricing models",
                "why_important": "Optimizes costs through appropriate pricing strategies",
                "example_services": ["Savings Plans", "Reserved Instances", "Spot Instances"],
                "weight": 0.20
            },
            "storage_optimization": {
                "importance": "medium",
                "description": "Storage cost optimization",
                "why_important": "Reduces storage costs through lifecycle policies and tiering",
                "example_services": ["S3 Intelligent-Tiering", "EFS lifecycle", "Glacier"],
                "weight": 0.25
            }
        },
        "operational_excellence": {
            "observability": {
                "importance": "critical",
                "description": "System observability and monitoring",
                "why_important": "Provides visibility into system behavior and enables data-driven decisions",
                "example_services": ["CloudWatch", "X-Ray", "CloudTrail"],
                "weight": 0.30
            },
            "infrastructure_as_code": {
                "importance": "high",
                "description": "Infrastructure as Code practices",
                "why_important": "Enables consistent, repeatable infrastructure deployments",
                "example_services": ["CloudFormation", "CDK", "Terraform"],
                "weight": 0.25
            },
            "deployment_automation": {
                "importance": "high",
                "description": "CI/CD and deployment automation",
                "why_important": "Reduces deployment errors and accelerates delivery",
                "example_services": ["CodePipeline", "CodeBuild", "CodeDeploy"],
                "weight": 0.25
            },
            "incident_response": {
                "importance": "high",
                "description": "Incident management and response",
                "why_important": "Enables rapid response to and recovery from incidents",
                "example_services": ["CloudWatch Alarms", "SNS", "Systems Manager"],
                "weight": 0.20
            }
        },
        "sustainability": {
            "managed_services": {
                "importance": "high",
                "description": "Use of managed and serverless services",
                "why_important": "Reduces carbon footprint through efficient resource utilization",
                "example_services": ["Lambda", "DynamoDB", "S3", "Fargate"],
                "weight": 0.35
            },
            "efficient_compute": {
                "importance": "high",
                "description": "Efficient compute resources",
                "why_important": "Minimizes energy consumption through optimized compute",
                "example_services": ["Lambda", "Graviton processors", "Fargate"],
                "weight": 0.30
            },
            "resource_utilization": {
                "importance": "medium",
                "description": "Optimal resource utilization",
                "why_important": "Reduces waste and environmental impact",
                "example_services": ["Auto Scaling", "Lambda", "monitoring tools"],
                "weight": 0.20
            },
            "data_optimization": {
                "importance": "medium",
                "description": "Data storage and transfer optimization",
                "why_important": "Reduces storage footprint and data transfer energy costs",
                "example_services": ["S3 Intelligent-Tiering", "compression", "deduplication"],
                "weight": 0.15
            }
        }
    }
    
    # Pattern-specific capability adjustments
    # Some capabilities may not be relevant for certain architectural patterns
    PATTERN_ADJUSTMENTS = {
        "serverless": {
            "excluded_capabilities": [
                # Serverless architectures don't need traditional scaling
                # because Lambda and managed services handle it automatically
            ],
            "reduced_importance": {
                # These are less critical in serverless
                "infrastructure_as_code": "medium",  # Still important but less complex
            }
        },
        "microservices": {
            "increased_importance": {
                "observability": "critical",  # More critical in distributed systems
                "monitoring_alerting": "critical"
            }
        },
        "event_driven": {
            "increased_importance": {
                "monitoring_alerting": "critical",
                "incident_response": "critical"
            }
        }
    }
    
    def __init__(self):
        """Initialize the missing capability analyzer."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("MissingCapabilityAnalyzer initialized")
    
    def analyze_pillar_gaps(
        self,
        pillar: str,
        detected_capabilities: List[str],
        architecture_services: List[str],
        detected_patterns: Optional[List[str]] = None
    ) -> List[MissingCapability]:
        """
        Analyze a pillar to identify missing capabilities.
        
        Args:
            pillar: WAFR pillar name (e.g., "security", "reliability")
            detected_capabilities: List of capability names that were detected
            architecture_services: List of AWS services in the architecture
            detected_patterns: Optional list of architectural patterns
            
        Returns:
            List of MissingCapability objects with importance and impact
        """
        if detected_patterns is None:
            detected_patterns = []
        
        self.logger.info(
            f"Analyzing capability gaps for {pillar} pillar: "
            f"{len(detected_capabilities)} detected, {len(architecture_services)} services"
        )
        
        # Get expected capabilities for this pillar
        expected_caps = self.EXPECTED_CAPABILITIES.get(pillar, {})
        if not expected_caps:
            self.logger.warning(f"No expected capabilities defined for pillar: {pillar}")
            return []
        
        # Convert detected capabilities to set for efficient lookup
        detected_set = set(cap.lower() for cap in detected_capabilities)
        
        # Identify missing capabilities
        missing_capabilities = []
        
        for cap_name, cap_info in expected_caps.items():
            if cap_name.lower() not in detected_set:
                # Check if this capability should be excluded based on patterns
                if self._should_exclude_capability(cap_name, detected_patterns):
                    self.logger.debug(
                        f"Excluding {cap_name} for {pillar} due to pattern: {detected_patterns}"
                    )
                    continue
                
                # Adjust importance based on patterns
                importance = self._adjust_importance(
                    cap_name,
                    cap_info["importance"],
                    detected_patterns
                )
                
                # Calculate score impact
                score_impact = self._calculate_score_impact(
                    cap_info["weight"],
                    importance
                )
                
                # Create missing capability object
                missing_cap = MissingCapability(
                    name=cap_name,
                    pillar=pillar,
                    importance=importance,
                    description=cap_info["description"],
                    example_services=cap_info["example_services"],
                    score_impact=score_impact,
                    why_important=cap_info["why_important"]
                )
                
                missing_capabilities.append(missing_cap)
                
                self.logger.debug(
                    f"Missing capability: {cap_name} (importance={importance}, "
                    f"impact={score_impact:.2f})"
                )
        
        # Sort by importance and score impact
        missing_capabilities.sort(
            key=lambda x: (
                self._importance_to_numeric(x.importance),
                x.score_impact
            ),
            reverse=True
        )
        
        self.logger.info(
            f"Found {len(missing_capabilities)} missing capabilities for {pillar}"
        )
        
        return missing_capabilities
    
    def _should_exclude_capability(
        self,
        capability: str,
        patterns: List[str]
    ) -> bool:
        """
        Check if a capability should be excluded based on architectural patterns.
        
        Args:
            capability: Capability name
            patterns: List of detected patterns
            
        Returns:
            True if capability should be excluded
        """
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in self.PATTERN_ADJUSTMENTS:
                excluded = self.PATTERN_ADJUSTMENTS[pattern_lower].get(
                    "excluded_capabilities", []
                )
                if capability in excluded:
                    return True
        
        return False
    
    def _adjust_importance(
        self,
        capability: str,
        base_importance: str,
        patterns: List[str]
    ) -> str:
        """
        Adjust capability importance based on architectural patterns.
        
        Args:
            capability: Capability name
            base_importance: Base importance level
            patterns: List of detected patterns
            
        Returns:
            Adjusted importance level
        """
        adjusted_importance = base_importance
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in self.PATTERN_ADJUSTMENTS:
                adjustments = self.PATTERN_ADJUSTMENTS[pattern_lower]
                
                # Check for increased importance
                if capability in adjustments.get("increased_importance", {}):
                    adjusted_importance = adjustments["increased_importance"][capability]
                
                # Check for reduced importance
                if capability in adjustments.get("reduced_importance", {}):
                    adjusted_importance = adjustments["reduced_importance"][capability]
        
        return adjusted_importance
    
    def _calculate_score_impact(
        self,
        capability_weight: float,
        importance: str
    ) -> float:
        """
        Calculate potential score improvement from adding this capability.
        
        Args:
            capability_weight: Weight of the capability in pillar scoring
            importance: Importance level of the capability
            
        Returns:
            Estimated score impact (0-100 scale)
        """
        # Base impact from capability weight (convert to 0-100 scale)
        base_impact = capability_weight * 100
        
        # Adjust based on importance
        importance_multipliers = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4
        }
        
        multiplier = importance_multipliers.get(importance, 0.6)
        
        return base_impact * multiplier
    
    def _importance_to_numeric(self, importance: str) -> int:
        """Convert importance level to numeric value for sorting."""
        importance_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return importance_map.get(importance, 2)
    
    def get_capability_gap_summary(
        self,
        missing_capabilities: List[MissingCapability]
    ) -> Dict[str, Any]:
        """
        Generate a summary of capability gaps.
        
        Args:
            missing_capabilities: List of missing capabilities
            
        Returns:
            Summary dictionary with statistics
        """
        if not missing_capabilities:
            return {
                "total_gaps": 0,
                "critical_gaps": 0,
                "high_priority_gaps": 0,
                "total_potential_improvement": 0.0
            }
        
        critical_count = sum(
            1 for cap in missing_capabilities
            if cap.importance == "critical"
        )
        
        high_count = sum(
            1 for cap in missing_capabilities
            if cap.importance == "high"
        )
        
        total_impact = sum(cap.score_impact for cap in missing_capabilities)
        
        return {
            "total_gaps": len(missing_capabilities),
            "critical_gaps": critical_count,
            "high_priority_gaps": high_count,
            "total_potential_improvement": round(total_impact, 2),
            "gaps_by_importance": {
                "critical": critical_count,
                "high": high_count,
                "medium": sum(1 for cap in missing_capabilities if cap.importance == "medium"),
                "low": sum(1 for cap in missing_capabilities if cap.importance == "low")
            }
        }
