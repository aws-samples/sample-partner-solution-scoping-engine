"""Capability detection data models for WAFR enterprise scoring."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class CapabilityName(str, Enum):
    """Capability names across all pillars."""
    
    # Security capabilities
    ENCRYPTION = "encryption"
    IDENTITY_ACCESS = "identity_access"
    NETWORK_SECURITY = "network_security"
    MONITORING_DETECTION = "monitoring_detection"
    DATA_PROTECTION = "data_protection"
    
    # Reliability capabilities
    REDUNDANCY = "redundancy"
    MONITORING_ALERTING = "monitoring_alerting"
    BACKUP_RECOVERY = "backup_recovery"
    SCALING = "scaling"
    
    # Performance capabilities
    CACHING = "caching"
    COMPUTE_OPTIMIZATION = "compute_optimization"
    DATABASE_OPTIMIZATION = "database_optimization"
    PERFORMANCE_MONITORING = "performance_monitoring"
    
    # Cost optimization capabilities
    COST_MONITORING = "cost_monitoring"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    LIFECYCLE_MANAGEMENT = "lifecycle_management"
    RIGHTSIZING = "rightsizing"
    
    # Operational excellence capabilities
    IAC_AUTOMATION = "iac_automation"
    CICD_PIPELINE = "cicd_pipeline"
    OPERATIONAL_MONITORING = "operational_monitoring"
    INCIDENT_RESPONSE = "incident_response"
    
    # Sustainability capabilities
    EFFICIENT_COMPUTE = "efficient_compute"
    MANAGED_SERVICES = "managed_services"
    RESOURCE_EFFICIENCY = "resource_efficiency"


@dataclass
class DetectedCapability:
    """
    A capability detected in the architecture.
    
    Represents a functional capability (e.g., encryption, redundancy)
    provided by one or more AWS services.
    """
    
    name: str  # Capability name (e.g., "encryption", "redundancy")
    pillar: str  # WAFR pillar (e.g., "security", "reliability")
    coverage: float  # 0.0 to 1.0 - how well implemented
    evidence: List[str]  # Services/configs that provide this capability
    confidence: float  # 0.0 to 1.0 - detection confidence
    weight: float  # Importance weight for scoring (0.0 to 1.0)
    
    # Additional metadata
    service_count: int = 0  # Number of services providing this capability
    configuration_quality: float = 0.0  # 0.0 to 1.0 - quality of configurations
    missing_services: List[str] = field(default_factory=list)  # Services that should have this
    
    def get_score_contribution(self, max_points: float = 60.0) -> float:
        """
        Calculate how much this capability contributes to the pillar score.
        
        Formula: max_points * weight * coverage * confidence
        
        Args:
            max_points: Maximum points available from capabilities (default 60)
            
        Returns:
            Score contribution in points
        """
        return max_points * self.weight * self.coverage * self.confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "pillar": self.pillar,
            "coverage": round(self.coverage, 2),
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "weight": self.weight,
            "service_count": self.service_count,
            "configuration_quality": round(self.configuration_quality, 2),
            "missing_services": self.missing_services,
            "score_contribution": round(self.get_score_contribution(), 2)
        }


@dataclass
class CapabilityMatrix:
    """
    Matrix of detected capabilities organized by pillar.
    
    Provides a structured view of all capabilities across the six WAFR pillars.
    """
    
    security_capabilities: List[DetectedCapability] = field(default_factory=list)
    reliability_capabilities: List[DetectedCapability] = field(default_factory=list)
    performance_capabilities: List[DetectedCapability] = field(default_factory=list)
    cost_capabilities: List[DetectedCapability] = field(default_factory=list)
    operational_capabilities: List[DetectedCapability] = field(default_factory=list)
    sustainability_capabilities: List[DetectedCapability] = field(default_factory=list)
    
    # Metadata
    total_services_analyzed: int = 0
    detection_timestamp: Optional[str] = None
    overall_confidence: float = 0.0
    
    def get_capabilities_for_pillar(self, pillar: str) -> List[DetectedCapability]:
        """
        Get all capabilities for a specific pillar.
        
        Args:
            pillar: Pillar name (security, reliability, etc.)
            
        Returns:
            List of capabilities for that pillar
        """
        pillar_mapping = {
            "security": self.security_capabilities,
            "reliability": self.reliability_capabilities,
            "performance": self.performance_capabilities,
            "performance_efficiency": self.performance_capabilities,  # Alias
            "cost_optimization": self.cost_capabilities,
            "operational_excellence": self.operational_capabilities,
            "sustainability": self.sustainability_capabilities
        }
        return pillar_mapping.get(pillar.lower(), [])
    
    def get_all_capabilities(self) -> List[DetectedCapability]:
        """Get all capabilities across all pillars."""
        return (
            self.security_capabilities +
            self.reliability_capabilities +
            self.performance_capabilities +
            self.cost_capabilities +
            self.operational_capabilities +
            self.sustainability_capabilities
        )
    
    def get_capability_count(self) -> int:
        """Get total number of detected capabilities."""
        return len(self.get_all_capabilities())
    
    def get_average_coverage(self) -> float:
        """Get average coverage across all capabilities."""
        capabilities = self.get_all_capabilities()
        if not capabilities:
            return 0.0
        return sum(c.coverage for c in capabilities) / len(capabilities)
    
    def get_average_confidence(self) -> float:
        """Get average confidence across all capabilities."""
        capabilities = self.get_all_capabilities()
        if not capabilities:
            return 0.0
        return sum(c.confidence for c in capabilities) / len(capabilities)
    
    def get_pillar_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get summary of capabilities by pillar.
        
        Returns:
            Dictionary with pillar summaries
        """
        pillars = {
            "security": self.security_capabilities,
            "reliability": self.reliability_capabilities,
            "performance": self.performance_capabilities,
            "cost_optimization": self.cost_capabilities,
            "operational_excellence": self.operational_capabilities,
            "sustainability": self.sustainability_capabilities
        }
        
        summary = {}
        for pillar_name, capabilities in pillars.items():
            if capabilities:
                summary[pillar_name] = {
                    "capability_count": len(capabilities),
                    "average_coverage": round(
                        sum(c.coverage for c in capabilities) / len(capabilities), 2
                    ),
                    "average_confidence": round(
                        sum(c.confidence for c in capabilities) / len(capabilities), 2
                    ),
                    "capabilities": [c.name for c in capabilities]
                }
            else:
                summary[pillar_name] = {
                    "capability_count": 0,
                    "average_coverage": 0.0,
                    "average_confidence": 0.0,
                    "capabilities": []
                }
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "security_capabilities": [c.to_dict() for c in self.security_capabilities],
            "reliability_capabilities": [c.to_dict() for c in self.reliability_capabilities],
            "performance_capabilities": [c.to_dict() for c in self.performance_capabilities],
            "cost_capabilities": [c.to_dict() for c in self.cost_capabilities],
            "operational_capabilities": [c.to_dict() for c in self.operational_capabilities],
            "sustainability_capabilities": [c.to_dict() for c in self.sustainability_capabilities],
            "total_services_analyzed": self.total_services_analyzed,
            "detection_timestamp": self.detection_timestamp,
            "overall_confidence": round(self.overall_confidence, 2),
            "summary": self.get_pillar_summary()
        }


@dataclass
class ServiceCapabilityMapping:
    """
    Mapping of an AWS service to the capabilities it provides.
    
    Used internally by CapabilityMapper to track service-to-capability relationships.
    """
    
    service_name: str
    capability_name: str
    pillar: str
    coverage_factor: float  # How much this service contributes to capability coverage
    confidence: float  # Confidence in this mapping
    
    # Configuration checks
    requires_configuration: bool = False
    configuration_checks: List[Dict[str, Any]] = field(default_factory=list)
    detected_configuration: Optional[Dict[str, Any]] = None
    
    def is_properly_configured(self) -> bool:
        """
        Check if service is properly configured for this capability.
        
        Returns:
            True if properly configured or no configuration required
        """
        if not self.requires_configuration:
            return True
        
        if not self.detected_configuration:
            return False
        
        # Check all configuration requirements
        for check in self.configuration_checks:
            field_name = check.get("field")
            required_values = check.get("required_values", [])
            
            if field_name not in self.detected_configuration:
                return False
            
            actual_value = self.detected_configuration[field_name]
            if required_values and actual_value not in required_values:
                return False
        
        return True
    
    def get_configuration_quality(self) -> float:
        """
        Get configuration quality score (0.0 to 1.0).
        
        Returns:
            1.0 if properly configured, 0.5 if partially configured, 0.0 if not configured
        """
        if not self.requires_configuration:
            return 1.0
        
        if not self.detected_configuration:
            return 0.0
        
        if self.is_properly_configured():
            return 1.0
        
        # Partial configuration
        return 0.5


@dataclass
class CapabilityGap:
    """
    A missing or poorly implemented capability.
    
    Used for recommendation generation.
    """
    
    capability_name: str
    pillar: str
    current_coverage: float  # 0.0 to 1.0
    target_coverage: float  # What it should be (typically 0.8-1.0)
    impact: str  # 'critical', 'high', 'medium', 'low'
    
    # Services that should provide this capability
    affected_services: List[str] = field(default_factory=list)
    missing_services: List[str] = field(default_factory=list)
    
    # Gap analysis
    gap_size: float = 0.0  # target_coverage - current_coverage
    priority_score: float = 0.0  # Calculated priority (0-100)
    estimated_score_improvement: float = 0.0  # Expected score improvement (0-10)
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.gap_size = self.target_coverage - self.current_coverage
        self.priority_score = self._calculate_priority()
        self.estimated_score_improvement = self._calculate_score_improvement()
    
    def _calculate_priority(self) -> float:
        """
        Calculate priority score based on gap size and impact.
        
        Returns:
            Priority score (0-100, higher is more urgent)
        """
        impact_weights = {
            'critical': 1.0,
            'high': 0.75,
            'medium': 0.5,
            'low': 0.25
        }
        
        impact_weight = impact_weights.get(self.impact, 0.5)
        return self.gap_size * impact_weight * 100
    
    def _calculate_score_improvement(self) -> float:
        """
        Calculate estimated score improvement based on gap size and impact.
        
        Returns:
            Estimated score improvement (0-10 scale)
        """
        impact_multipliers = {
            'critical': 10.0,
            'high': 7.5,
            'medium': 5.0,
            'low': 2.5
        }
        
        impact_multiplier = impact_multipliers.get(self.impact, 5.0)
        # Cap the improvement at 10 points maximum
        return min(self.gap_size * impact_multiplier, 10.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "capability_name": self.capability_name,
            "pillar": self.pillar,
            "current_coverage": round(self.current_coverage, 2),
            "target_coverage": round(self.target_coverage, 2),
            "gap_size": round(self.gap_size, 2),
            "impact": self.impact,
            "priority_score": round(self.priority_score, 2),
            "estimated_score_improvement": round(self.estimated_score_improvement, 2),
            "affected_services": self.affected_services,
            "missing_services": self.missing_services
        }
