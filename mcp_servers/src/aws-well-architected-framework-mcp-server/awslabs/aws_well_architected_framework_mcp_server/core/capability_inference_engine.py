"""
Capability Inference Engine for WAFR Intelligent Scoring.

This module provides rule-based capability inference from service categories
instead of hard-coded service name lookups. This makes the system:
- Flexible: Works with any AWS service
- Accurate: Infers capabilities from service functions
- Maintainable: Rules are clear and testable
- Production-grade: Handles complex service combinations

Example:
    engine = CapabilityInferenceEngine()
    
    # Infer encryption capability
    capability = engine.infer_capability(
        'encryption',
        categorized_services=[...],
        detected_patterns=['serverless']
    )
    # Returns: DetectedCapability with coverage=0.7, confidence=0.8
"""

from typing import List, Dict, Set, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..core.logger import WAFRLogger
from ..core.service_categorizer import ServiceCategory, CategorizedService
from ..models.capability import DetectedCapability


class RuleConditionType(str, Enum):
    """Types of rule conditions."""
    ANY_CATEGORY = "any_category"  # Any service in category
    ALL_CATEGORIES = "all_categories"  # Services in all categories
    CATEGORY_COUNT = "category_count"  # Minimum number of services in category
    SERVICE_COMBINATION = "service_combination"  # Specific combination of categories
    PATTERN_MATCH = "pattern_match"  # Architectural pattern detected
    TEXT_KEYWORD_MATCH = "text_keyword_match"  # Keywords found in document text (for IaC, CI/CD detection)


@dataclass
class InferenceRule:
    """
    A rule for inferring a capability from service categories.
    
    Rules are evaluated to determine if a capability exists and its coverage level.
    """
    capability_name: str
    pillar: str
    condition_type: RuleConditionType
    condition_params: Dict
    coverage: float  # 0.0 to 1.0 - how well this rule indicates capability
    confidence: float  # 0.0 to 1.0 - confidence in this inference
    weight: float  # Importance of this capability in the pillar
    description: str
    
    def evaluate(
        self,
        categorized_services: List[CategorizedService],
        detected_patterns: List[str],
        document_text: str = ""
    ) -> bool:
        """
        Evaluate if this rule's conditions are met.
        
        Args:
            categorized_services: List of categorized services
            detected_patterns: List of detected architectural patterns
            document_text: Raw document text for keyword matching (optional)
            
        Returns:
            True if rule conditions are met
        """
        if self.condition_type == RuleConditionType.ANY_CATEGORY:
            # Check if any service belongs to the specified category
            required_category = ServiceCategory(self.condition_params['category'])
            return any(
                required_category in cs.categories
                for cs in categorized_services
            )
        
        elif self.condition_type == RuleConditionType.ALL_CATEGORIES:
            # Check if services exist in all specified categories
            required_categories = [
                ServiceCategory(cat) for cat in self.condition_params['categories']
            ]
            found_categories = set()
            for cs in categorized_services:
                found_categories.update(cs.categories)
            return all(cat in found_categories for cat in required_categories)
        
        elif self.condition_type == RuleConditionType.CATEGORY_COUNT:
            # Check if minimum number of services in category
            required_category = ServiceCategory(self.condition_params['category'])
            min_count = self.condition_params['min_count']
            count = sum(
                1 for cs in categorized_services
                if required_category in cs.categories
            )
            return count >= min_count
        
        elif self.condition_type == RuleConditionType.SERVICE_COMBINATION:
            # Check if specific combination of categories exists
            required_combinations = self.condition_params['combinations']
            found_categories = set()
            for cs in categorized_services:
                found_categories.update(cs.categories)
            
            # Check if any combination is satisfied
            for combo in required_combinations:
                combo_categories = [ServiceCategory(cat) for cat in combo]
                if all(cat in found_categories for cat in combo_categories):
                    return True
            return False
        
        elif self.condition_type == RuleConditionType.PATTERN_MATCH:
            # Check if architectural pattern is detected
            required_patterns = self.condition_params['patterns']
            return any(
                pattern.lower() in [p.lower() for p in detected_patterns]
                for pattern in required_patterns
            )
        
        elif self.condition_type == RuleConditionType.TEXT_KEYWORD_MATCH:
            # Check if any keywords are found in document text or service names
            # This is useful for detecting IaC, CI/CD, and other text-based capabilities
            required_keywords = self.condition_params.get('keywords', [])
            min_matches = self.condition_params.get('min_matches', 1)
            
            # Combine document text with service names and patterns for comprehensive search
            search_text = document_text.lower()
            
            # Also search in service names (in case CloudFormation is in identified_services)
            for cs in categorized_services:
                search_text += " " + cs.service_name.lower()
            
            # Also search in detected patterns
            for pattern in detected_patterns:
                # Handle both string patterns and ArchitecturePattern objects
                if hasattr(pattern, 'pattern_type'):
                    # ArchitecturePattern object
                    search_text += " " + pattern.pattern_type.lower()
                elif isinstance(pattern, dict):
                    # Dict with 'item' or 'pattern_type' key
                    pattern_str = pattern.get('item', '') or pattern.get('pattern_type', '') or str(pattern)
                    search_text += " " + pattern_str.lower()
                elif isinstance(pattern, str):
                    search_text += " " + pattern.lower()
                else:
                    # Fallback: convert to string
                    search_text += " " + str(pattern).lower()
            
            # Count keyword matches
            matches = sum(1 for kw in required_keywords if kw.lower() in search_text)
            return matches >= min_matches
        
        return False


class CapabilityInferenceEngine:
    """
    Rule-based capability inference engine.
    
    Infers capabilities from service categories using configurable rules
    instead of hard-coded service name lookups.
    
    Design Principles:
    - Rule-based: Clear, testable inference logic
    - Category-driven: Uses service categories, not names
    - Composite rules: Supports complex service combinations
    - Pattern-aware: Adjusts for architectural patterns
    - Confidence scoring: Provides transparency in inferences
    
    FIXED: Rules are now stored by pillar:capability_name composite key to support
    the same capability name across different pillars (e.g., managed_services in
    both cost_optimization and sustainability pillars).
    """
    
    def __init__(self):
        """Initialize the capability inference engine."""
        self.logger = WAFRLogger(__name__)
        # FIXED: Use pillar:capability_name as key to support same capability across pillars
        self.rules: Dict[str, List[InferenceRule]] = {}
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize inference rules for all capabilities."""
        # Rules will be added by pillar-specific methods
        # This keeps the code organized and maintainable
        pass
    
    def _get_rule_key(self, pillar: str, capability_name: str) -> str:
        """
        Generate composite key for rule storage.
        
        Args:
            pillar: Pillar name (e.g., 'security', 'sustainability')
            capability_name: Capability name (e.g., 'managed_services')
            
        Returns:
            Composite key in format 'pillar:capability_name'
        """
        return f"{pillar}:{capability_name}"
    
    def add_rule(self, rule: InferenceRule):
        """
        Add an inference rule.
        
        FIXED: Now uses pillar:capability_name composite key to support
        the same capability name across different pillars.
        
        Args:
            rule: InferenceRule to add
        """
        # Use composite key to support same capability across pillars
        rule_key = self._get_rule_key(rule.pillar, rule.capability_name)
        
        if rule_key not in self.rules:
            self.rules[rule_key] = []
        self.rules[rule_key].append(rule)
        
        self.logger.debug(
            f"Added rule for {rule_key}: {rule.description}"
        )
    
    def add_rules(self, rules: List[InferenceRule]):
        """
        Add multiple inference rules.
        
        Args:
            rules: List of InferenceRule objects
        """
        for rule in rules:
            self.add_rule(rule)
    
    def infer_capability(
        self,
        capability_name: str,
        categorized_services: List[CategorizedService],
        detected_patterns: List[str] = None,
        document_text: str = "",
        pillar: str = None
    ) -> Optional[DetectedCapability]:
        """
        Infer a capability from categorized services.
        
        FIXED: Now supports pillar parameter to correctly handle same capability
        name across different pillars (e.g., managed_services in cost_optimization
        and sustainability).
        
        Args:
            capability_name: Name of capability to infer
            categorized_services: List of categorized services
            detected_patterns: List of detected architectural patterns
            document_text: Raw document text for keyword matching (optional)
            pillar: Pillar name for pillar-specific capability lookup (optional)
            
        Returns:
            DetectedCapability if capability is detected, None otherwise
        """
        if detected_patterns is None:
            detected_patterns = []
        
        # FIXED: Use composite key if pillar is provided
        if pillar:
            rule_key = self._get_rule_key(pillar, capability_name)
        else:
            # Fallback to capability_name only for backward compatibility
            rule_key = capability_name
        
        if rule_key not in self.rules:
            self.logger.debug(f"No rules defined for capability: {rule_key}")
            return None
        
        # Evaluate all rules for this capability
        matching_rules = []
        for rule in self.rules[rule_key]:
            if rule.evaluate(categorized_services, detected_patterns, document_text):
                matching_rules.append(rule)
        
        if not matching_rules:
            self.logger.debug(f"No rules matched for capability: {rule_key}")
            return None
        
        # Use the rule with highest coverage (best match)
        best_rule = max(matching_rules, key=lambda r: r.coverage)
        
        # Collect evidence (services that contributed to this capability)
        evidence = []
        for cs in categorized_services:
            # Add service if it's relevant to the capability
            # (This is a simplified approach - could be more sophisticated)
            evidence.append(cs.service_name)
        
        # Create detected capability
        capability = DetectedCapability(
            name=best_rule.capability_name,
            pillar=best_rule.pillar,
            coverage=best_rule.coverage,
            evidence=evidence[:5],  # Limit to top 5 for readability
            confidence=best_rule.confidence,
            weight=best_rule.weight
        )
        
        self.logger.info(
            f"Inferred {rule_key}: coverage={capability.coverage:.2f}, "
            f"confidence={capability.confidence:.2f}, rule='{best_rule.description}'"
        )
        
        return capability
    
    def infer_all_capabilities(
        self,
        categorized_services: List[CategorizedService],
        detected_patterns: List[str] = None,
        document_text: str = ""
    ) -> List[DetectedCapability]:
        """
        Infer all possible capabilities from categorized services.
        
        FIXED: Now properly handles same capability name across different pillars
        by using pillar:capability_name composite keys. This ensures that
        managed_services is detected for both cost_optimization AND sustainability.
        
        Args:
            categorized_services: List of categorized services
            detected_patterns: List of detected architectural patterns
            document_text: Raw document text for keyword matching (optional)
            
        Returns:
            List of detected capabilities
        """
        if detected_patterns is None:
            detected_patterns = []
        
        capabilities = []
        
        # FIXED: Iterate over composite keys (pillar:capability_name)
        # This ensures same capability name is evaluated for each pillar separately
        for rule_key in self.rules.keys():
            # Parse the composite key to get pillar and capability_name
            if ':' in rule_key:
                pillar, capability_name = rule_key.split(':', 1)
            else:
                # Backward compatibility for old-style keys
                pillar = None
                capability_name = rule_key
            
            capability = self.infer_capability(
                capability_name,
                categorized_services,
                detected_patterns,
                document_text,
                pillar=pillar
            )
            if capability:
                capabilities.append(capability)
        
        self.logger.info(
            f"Inferred {len(capabilities)} capabilities from "
            f"{len(categorized_services)} services"
        )
        
        return capabilities
    
    def get_capabilities_by_pillar(
        self,
        capabilities: List[DetectedCapability],
        pillar: str
    ) -> List[DetectedCapability]:
        """
        Filter capabilities by pillar.
        
        Args:
            capabilities: List of detected capabilities
            pillar: Pillar name to filter by
            
        Returns:
            List of capabilities for the specified pillar
        """
        return [cap for cap in capabilities if cap.pillar == pillar]
    
    def get_capability_summary(
        self,
        capabilities: List[DetectedCapability]
    ) -> Dict[str, List[str]]:
        """
        Get a summary of capabilities organized by pillar.
        
        Args:
            capabilities: List of detected capabilities
            
        Returns:
            Dictionary mapping pillars to capability names
        """
        summary: Dict[str, List[str]] = {}
        
        for cap in capabilities:
            if cap.pillar not in summary:
                summary[cap.pillar] = []
            summary[cap.pillar].append(cap.name)
        
        return summary


# Global instance for easy access
capability_inference_engine = CapabilityInferenceEngine()
