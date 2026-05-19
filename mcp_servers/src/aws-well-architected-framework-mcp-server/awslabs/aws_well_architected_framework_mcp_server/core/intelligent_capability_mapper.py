"""
Intelligent Capability Mapper for WAFR Enterprise Scoring.

This is the NEW production-grade capability mapper that uses intelligent inference
instead of hard-coded service name lookups.

Key Improvements:
- Uses ServiceCategorizer for flexible service categorization
- Uses CapabilityInferenceEngine for rule-based capability detection
- Works with ANY AWS service (current and future)
- No hard-coded service names or JSON configuration files
- Production-grade and maintainable
- FIX Issue 2: Converts IaC-detected features to DetectedCapability objects
"""

from typing import Dict, List, Optional, Any

from ..core.logger import WAFRLogger
from ..core.service_categorizer import service_categorizer
from ..core.capability_inference_engine import capability_inference_engine
from ..core.capability_rules import initialize_all_rules
from ..models.capability import (
    DetectedCapability,
    CapabilityMatrix,
    CapabilityGap
)


class IntelligentCapabilityMapper:
    """
    Intelligent capability mapper using inference rules instead of hard-coded lookups.
    
    This replaces the old CapabilityMapper with a production-grade approach:
    - Service categorization: Fuzzy keyword matching
    - Capability inference: Rule-based detection
    - Pattern awareness: Adjusts for architectural patterns
    - No hard-coding: Works with any AWS service
    - FIX Issue 2: Converts IaC features to DetectedCapability objects
    
    Example:
        mapper = IntelligentCapabilityMapper()
        
        services = ["Lambda", "DynamoDB", "S3", "CloudWatch", "X-Ray"]
        patterns = ["serverless"]
        
        matrix = mapper.map_services_to_capabilities(services, {}, patterns)
        # Returns: CapabilityMatrix with detected capabilities
    """
    
    # FIX Issue 2: Mapping from IaC feature names to capability names and pillars
    IAC_FEATURE_TO_CAPABILITY = {
        # Security features
        'kms_encryption': ('encryption', 'security', 0.9),
        'encryption_at_rest': ('encryption', 'security', 0.85),
        'encryption_in_transit': ('encryption', 'security', 0.85),
        'vpc_endpoints': ('network_security', 'security', 0.8),
        'security_groups': ('network_security', 'security', 0.75),
        'nacls': ('network_security', 'security', 0.7),
        'waf': ('network_security', 'security', 0.85),
        'cognito_advanced_security': ('identity_access', 'security', 0.85),
        'iam_roles': ('identity_access', 'security', 0.8),
        'secrets_manager': ('data_protection', 'security', 0.85),
        'certificate_manager': ('data_protection', 'security', 0.8),
        'guardduty': ('monitoring_detection', 'security', 0.9),
        'cloudtrail': ('monitoring_detection', 'security', 0.85),
        'bedrock_guardrails': ('data_protection', 'security', 0.9),
        
        # Reliability features
        'multi_az': ('redundancy', 'reliability', 0.9),
        'cross_region_replication': ('redundancy', 'reliability', 0.85),
        'auto_scaling': ('scaling', 'reliability', 0.85),
        'pitr': ('backup_recovery', 'reliability', 0.9),
        'backup_enabled': ('backup_recovery', 'reliability', 0.85),
        'automatic_failover': ('fault_tolerance', 'reliability', 0.85),
        'health_checks': ('monitoring_alerting', 'reliability', 0.8),
        'cloudwatch_alarms': ('monitoring_alerting', 'reliability', 0.85),
        
        # Sustainability features
        'graviton': ('efficient_compute', 'sustainability', 0.9),
        'spot_instances': ('resource_utilization', 'sustainability', 0.8),
        'lambda': ('managed_services', 'sustainability', 0.85),
        'fargate': ('managed_services', 'sustainability', 0.85),
    }
    
    def __init__(self):
        """Initialize the intelligent capability mapper."""
        self.logger = WAFRLogger(__name__)
        
        # Initialize inference rules
        initialize_all_rules(capability_inference_engine)
        
        self.logger.info("IntelligentCapabilityMapper initialized with intelligent inference")
    
    def map_services_to_capabilities(
        self,
        detected_services: List[str],
        service_configurations: Dict[str, Any] = None,
        detected_patterns: List[str] = None,
        document_text: str = "",
        iac_features: Dict[str, Dict[str, Any]] = None
    ) -> CapabilityMatrix:
        """
        Map detected services to capabilities using intelligent inference.
        
        Process:
        1. Categorize services by function (compute, storage, database, etc.)
        2. Apply inference rules to detect capabilities
        3. FIX Issue 2: Convert IaC features to capabilities
        4. Calculate coverage and confidence for each capability
        5. Organize capabilities by pillar
        
        Args:
            detected_services: List of AWS service names
            service_configurations: Optional service configuration details
            detected_patterns: Optional list of architectural patterns
            document_text: Optional raw document text for keyword-based detection
            iac_features: Optional dict with 'security_features', 'reliability_features',
                         'sustainability_features' from IaC extraction
            
        Returns:
            CapabilityMatrix with capabilities organized by pillar
        """
        if service_configurations is None:
            service_configurations = {}
        if detected_patterns is None:
            detected_patterns = []
        if iac_features is None:
            iac_features = {}
        
        self.logger.info(
            f"Mapping {len(detected_services)} services to capabilities "
            f"with {len(detected_patterns)} patterns"
            f"{' and document text' if document_text else ''}"
            f"{' and IaC features' if iac_features else ''}"
        )
        
        # Step 1: Categorize services
        categorized_services = service_categorizer.categorize_services(detected_services)
        
        # Log categorization summary
        category_summary = service_categorizer.get_category_summary(categorized_services)
        self.logger.debug(f"Service categorization: {category_summary}")
        
        # Step 2: Infer capabilities from services
        capabilities = capability_inference_engine.infer_all_capabilities(
            categorized_services,
            detected_patterns,
            document_text
        )
        
        self.logger.info(f"Inferred {len(capabilities)} capabilities from services")
        
        # Step 3: FIX Issue 2 - Convert IaC features to capabilities
        iac_capabilities = self._convert_iac_features_to_capabilities(iac_features)
        if iac_capabilities:
            self.logger.info(f"FIX Issue 2: Converted {len(iac_capabilities)} IaC features to capabilities")
            # Merge IaC capabilities with inferred capabilities (IaC takes precedence)
            capabilities = self._merge_capabilities(capabilities, iac_capabilities)
        
        self.logger.info(f"Total capabilities after merge: {len(capabilities)}")
        
        # Step 4: Organize by pillar
        matrix = CapabilityMatrix(
            security_capabilities=self._get_pillar_capabilities(capabilities, 'security'),
            reliability_capabilities=self._get_pillar_capabilities(capabilities, 'reliability'),
            performance_capabilities=self._get_pillar_capabilities(capabilities, 'performance'),
            cost_capabilities=self._get_pillar_capabilities(capabilities, 'cost_optimization'),
            operational_capabilities=self._get_pillar_capabilities(capabilities, 'operational_excellence'),
            sustainability_capabilities=self._get_pillar_capabilities(capabilities, 'sustainability')
        )
        
        # Log summary
        self.logger.info(
            f"Capability matrix: "
            f"security={len(matrix.security_capabilities)}, "
            f"reliability={len(matrix.reliability_capabilities)}, "
            f"performance={len(matrix.performance_capabilities)}, "
            f"cost={len(matrix.cost_capabilities)}, "
            f"operational={len(matrix.operational_capabilities)}, "
            f"sustainability={len(matrix.sustainability_capabilities)}"
        )
        
        return matrix
    
    def _convert_iac_features_to_capabilities(
        self,
        iac_features: Dict[str, Dict[str, Any]]
    ) -> List[DetectedCapability]:
        """
        FIX Issue 2: Convert IaC-detected features to DetectedCapability objects.
        
        This ensures that features detected from CloudFormation/Terraform templates
        are properly represented in the capability matrix.
        
        Args:
            iac_features: Dict with keys like 'security_features', 'reliability_features'
                         Each value is a dict of feature_name -> bool/value
        
        Returns:
            List of DetectedCapability objects
        """
        capabilities = []
        
        # Process each feature category
        for category_key in ['security_features', 'reliability_features', 'sustainability_features']:
            features = iac_features.get(category_key, {})
            if not features:
                continue
            
            for feature_name, feature_value in features.items():
                # Skip if feature is False or empty
                if not feature_value:
                    continue
                
                # Normalize feature name
                normalized_name = feature_name.lower().replace('-', '_').replace(' ', '_')
                
                # Look up capability mapping
                if normalized_name in self.IAC_FEATURE_TO_CAPABILITY:
                    cap_name, pillar, confidence = self.IAC_FEATURE_TO_CAPABILITY[normalized_name]
                    
                    # Create capability
                    capability = DetectedCapability(
                        name=cap_name,
                        pillar=pillar,
                        coverage=0.85,  # High coverage since detected from IaC
                        evidence=[f"IaC: {feature_name}"],
                        confidence=confidence,
                        weight=0.8  # Standard weight
                    )
                    capabilities.append(capability)
                    self.logger.debug(f"FIX Issue 2: Converted IaC feature '{feature_name}' to capability '{cap_name}' ({pillar})")
                else:
                    # Try to infer capability from feature name
                    inferred = self._infer_capability_from_feature_name(normalized_name, feature_value)
                    if inferred:
                        capabilities.append(inferred)
                        self.logger.debug(f"FIX Issue 2: Inferred capability from IaC feature '{feature_name}'")
        
        return capabilities
    
    def _infer_capability_from_feature_name(
        self,
        feature_name: str,
        feature_value: Any
    ) -> Optional[DetectedCapability]:
        """
        Infer capability from feature name using pattern matching.
        
        Args:
            feature_name: Normalized feature name
            feature_value: Feature value (bool, dict, etc.)
        
        Returns:
            DetectedCapability if inference successful, None otherwise
        """
        # Pattern-based inference
        if 'encrypt' in feature_name:
            return DetectedCapability(
                name='encryption',
                pillar='security',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        elif 'backup' in feature_name or 'snapshot' in feature_name:
            return DetectedCapability(
                name='backup_recovery',
                pillar='reliability',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        elif 'scaling' in feature_name or 'autoscal' in feature_name:
            return DetectedCapability(
                name='scaling',
                pillar='reliability',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        elif 'monitor' in feature_name or 'alarm' in feature_name or 'metric' in feature_name:
            return DetectedCapability(
                name='monitoring_alerting',
                pillar='reliability',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        elif 'vpc' in feature_name or 'security_group' in feature_name or 'firewall' in feature_name:
            return DetectedCapability(
                name='network_security',
                pillar='security',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        elif 'iam' in feature_name or 'role' in feature_name or 'policy' in feature_name:
            return DetectedCapability(
                name='identity_access',
                pillar='security',
                coverage=0.7,
                evidence=[f"IaC: {feature_name}"],
                confidence=0.75,
                weight=0.8
            )
        
        return None
    
    def _merge_capabilities(
        self,
        inferred_capabilities: List[DetectedCapability],
        iac_capabilities: List[DetectedCapability]
    ) -> List[DetectedCapability]:
        """
        Merge inferred capabilities with IaC capabilities.
        
        IaC capabilities take precedence (higher confidence).
        Duplicate capabilities are merged, keeping the higher confidence.
        
        Args:
            inferred_capabilities: Capabilities from service inference
            iac_capabilities: Capabilities from IaC feature extraction
        
        Returns:
            Merged list of capabilities
        """
        # Create a dict keyed by (pillar, name) for deduplication
        capability_map: Dict[tuple, DetectedCapability] = {}
        
        # Add inferred capabilities first
        for cap in inferred_capabilities:
            key = (cap.pillar, cap.name)
            capability_map[key] = cap
        
        # Add/override with IaC capabilities (higher confidence)
        for cap in iac_capabilities:
            key = (cap.pillar, cap.name)
            if key in capability_map:
                existing = capability_map[key]
                # Keep the one with higher confidence
                if cap.confidence > existing.confidence:
                    # Merge evidence
                    merged_evidence = list(set(existing.evidence + cap.evidence))
                    cap.evidence = merged_evidence
                    capability_map[key] = cap
                else:
                    # Merge evidence into existing
                    existing.evidence = list(set(existing.evidence + cap.evidence))
            else:
                capability_map[key] = cap
        
        return list(capability_map.values())
    
    def _get_pillar_capabilities(
        self,
        capabilities: List[DetectedCapability],
        pillar: str
    ) -> List[DetectedCapability]:
        """
        Filter capabilities by pillar.
        
        Args:
            capabilities: List of all detected capabilities
            pillar: Pillar name to filter by
            
        Returns:
            List of capabilities for the specified pillar
        """
        return [cap for cap in capabilities if cap.pillar == pillar]
    
    def identify_capability_gaps(
        self,
        capability_matrix: CapabilityMatrix,
        target_coverage: float = 0.8
    ) -> List[CapabilityGap]:
        """
        Identify capability gaps (missing or poorly implemented capabilities).
        
        Args:
            capability_matrix: CapabilityMatrix with detected capabilities
            target_coverage: Target coverage threshold (default 0.8 = 80%)
            
        Returns:
            List of CapabilityGap objects
        """
        gaps: List[CapabilityGap] = []
        
        # Define expected capabilities for each pillar
        # UPDATED: Added fault_tolerance for reliability, cost_monitoring for cost_optimization,
        # and region_selection for sustainability
        expected_capabilities = {
            'security': ['encryption', 'identity_access', 'network_security', 'monitoring_detection', 'data_protection'],
            'reliability': ['redundancy', 'monitoring_alerting', 'backup_recovery', 'scaling', 'fault_tolerance'],
            'performance': ['caching', 'compute_optimization', 'content_delivery', 'database_optimization'],
            'cost_optimization': ['resource_optimization', 'managed_services', 'pricing_models', 'storage_optimization', 'cost_monitoring'],
            'operational_excellence': ['observability', 'infrastructure_as_code', 'deployment_automation', 'incident_response'],
            'sustainability': ['managed_services', 'efficient_compute', 'resource_utilization', 'data_optimization', 'region_selection']
        }
        
        # Check each pillar
        for pillar, expected_caps in expected_capabilities.items():
            # Get detected capabilities for this pillar
            pillar_capabilities = capability_matrix.get_capabilities_for_pillar(pillar)
            detected_cap_names = {cap.name for cap in pillar_capabilities}
            
            # Find missing capabilities
            for cap_name in expected_caps:
                # Check if capability is missing or has low coverage
                detected_cap = next(
                    (c for c in pillar_capabilities if c.name == cap_name),
                    None
                )
                
                if detected_cap is None:
                    # Capability is completely missing
                    gap = CapabilityGap(
                        capability_name=cap_name,
                        pillar=pillar,
                        current_coverage=0.0,
                        target_coverage=target_coverage,
                        impact='critical',
                        affected_services=[],
                        missing_services=[]
                    )
                    gaps.append(gap)
                elif detected_cap.coverage < target_coverage:
                    # Capability exists but coverage is low
                    gap = CapabilityGap(
                        capability_name=cap_name,
                        pillar=pillar,
                        current_coverage=detected_cap.coverage,
                        target_coverage=target_coverage,
                        impact='high' if detected_cap.coverage < 0.5 else 'medium',
                        affected_services=detected_cap.evidence,
                        missing_services=[]
                    )
                    gaps.append(gap)
        
        # Sort by priority
        gaps.sort(key=lambda g: g.priority_score, reverse=True)
        
        self.logger.info(f"Identified {len(gaps)} capability gaps")
        
        return gaps


# Global instance for easy access
intelligent_capability_mapper = IntelligentCapabilityMapper()
