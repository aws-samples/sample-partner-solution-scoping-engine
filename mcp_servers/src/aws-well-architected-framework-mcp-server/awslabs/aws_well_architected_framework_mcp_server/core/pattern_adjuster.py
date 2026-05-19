"""
Pattern-based scoring adjustments for WAFR assessments.

Applies architecture pattern-specific adjustments to pillar scores to ensure
scoring reflects pattern-appropriate expectations. For example, serverless
architectures shouldn't be penalized for not having EC2 auto-scaling.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..core.logger import WAFRLogger
from ..models.scoring import PillarScore, ScoreComponent, ScoreBreakdown


@dataclass
class ArchitecturePattern:
    """
    Architecture pattern detected in the system.
    
    Represents a specific architectural approach (serverless, microservices, etc.)
    with associated expectations and scoring adjustments.
    """
    
    pattern_type: str  # Pattern name (serverless, microservices, etc.)
    confidence: float  # 0.0-1.0 detection confidence
    key_services: List[str]  # Services that indicate this pattern
    expected_capabilities: Dict[str, List[str]]  # Pillar → expected capabilities
    scoring_adjustments: Dict[str, Any]  # Pattern-specific adjustments
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_type": self.pattern_type,
            "confidence": round(self.confidence, 2),
            "key_services": self.key_services,
            "expected_capabilities": self.expected_capabilities,
            "scoring_adjustments": self.scoring_adjustments
        }


class PatternAdjuster:
    """
    Applies pattern-specific scoring adjustments.
    
    Different patterns have different expectations:
    - Serverless: Emphasize event-driven, stateless, managed services
    - Microservices: Emphasize service isolation, API management, observability
    - Traditional: Emphasize infrastructure resilience, scaling, redundancy
    
    Adjustments:
    1. Ignore irrelevant capabilities (e.g., EC2 auto-scaling for serverless)
    2. Emphasize pattern-specific capabilities (e.g., Lambda scaling for serverless)
    3. Apply pattern-specific score multipliers
    
    Follows MCP server patterns:
    - Configuration-driven
    - Comprehensive logging
    - Graceful degradation
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize PatternAdjuster.
        
        Args:
            config_dir: Path to configuration directory (defaults to ../config)
        """
        self.logger = WAFRLogger(__name__)
        
        # Set config directory
        if config_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_dir = os.path.join(current_dir, '..', 'config')
        else:
            self.config_dir = config_dir
        
        # Load pattern definitions from configuration
        self.pattern_definitions = self._load_pattern_definitions()
        
        self.logger.info(f"PatternAdjuster initialized with {len(self.pattern_definitions)} pattern definitions")
    
    def _load_pattern_definitions(self) -> Dict[str, Any]:
        """
        Load pattern definitions from JSON configuration.
        
        Loads from config/patterns/architecture_patterns.json
        
        Returns:
            Dictionary with pattern definitions
        """
        pattern_file = os.path.join(self.config_dir, 'patterns', 'architecture_patterns.json')
        
        if not os.path.exists(pattern_file):
            self.logger.warning(f"Pattern definitions file not found: {pattern_file}, using empty patterns")
            return {}
        
        try:
            with open(pattern_file, 'r') as f:
                patterns = json.load(f)
                self.logger.debug(f"Loaded {len(patterns)} pattern definitions from {pattern_file}")
                return patterns
        except Exception as e:
            self.logger.error(f"Error loading pattern definitions: {e}")
            return {}
    
    def apply_pattern_adjustments(
        self,
        base_scores: Dict[str, PillarScore],
        detected_patterns: List[ArchitecturePattern]
    ) -> Dict[str, PillarScore]:
        """
        Apply pattern-specific adjustments to base scores.
        
        Process:
        1. For each detected pattern (weighted by confidence)
        2. Identify capabilities to ignore (not relevant for this pattern)
        3. Identify capabilities to emphasize (critical for this pattern)
        4. Apply pattern-specific score multipliers
        5. Recalculate final scores with adjustments
        
        Args:
            base_scores: Dictionary of pillar scores before pattern adjustments
            detected_patterns: List of detected architecture patterns (or pattern name strings)
            
        Returns:
            Dictionary of adjusted pillar scores
        """
        if not detected_patterns:
            self.logger.info("No patterns detected, returning base scores unchanged")
            return base_scores
        
        # Convert string pattern names to ArchitecturePattern objects if needed
        pattern_objects = []
        for pattern in detected_patterns:
            if isinstance(pattern, str):
                # Convert string to ArchitecturePattern object
                pattern_obj = self._create_pattern_from_name(pattern)
                if pattern_obj:
                    pattern_objects.append(pattern_obj)
            else:
                pattern_objects.append(pattern)
        
        if not pattern_objects:
            self.logger.warning("No valid patterns after conversion, returning base scores unchanged")
            return base_scores
        
        self.logger.info(f"🎨 Applying pattern adjustments for {len(pattern_objects)} detected patterns")
        
        # Log detected patterns
        for pattern in pattern_objects:
            # Handle both dict and object formats
            if isinstance(pattern, dict):
                pattern_item = pattern.get('item', '')
                import re
                match = re.search(r'\*\*([^*]+)\*\*', pattern_item)
                pattern_name = match.group(1).strip() if match else pattern_item.split('-')[0].strip()
                pattern_confidence = pattern.get('confidence', 0.8)
            else:
                pattern_name = pattern.pattern_type
                pattern_confidence = pattern.confidence
            
            self.logger.info(
                f"  📐 Pattern: {pattern_name} "
                f"(confidence={pattern_confidence:.2f})"
            )
        
        # Apply adjustments for each pillar
        adjusted_scores = {}
        
        for pillar_name, base_score in base_scores.items():
            adjusted_score = self._apply_pattern_adjustments_to_pillar(
                pillar_name,
                base_score,
                pattern_objects
            )
            adjusted_scores[pillar_name] = adjusted_score
        
        # Log summary
        self._log_adjustment_summary(base_scores, adjusted_scores)
        
        return adjusted_scores
    
    def _apply_pattern_adjustments_to_pillar(
        self,
        pillar_name: str,
        base_score: PillarScore,
        detected_patterns: List[ArchitecturePattern]
    ) -> PillarScore:
        """
        Apply pattern adjustments to a single pillar score.
        
        Args:
            pillar_name: Name of the pillar
            base_score: Base score before adjustments
            detected_patterns: List of detected patterns
            
        Returns:
            Adjusted pillar score
        """
        # Start with base score values
        adjusted_capability_contributions = base_score.capability_contributions.copy()
        adjustment_log = []
        
        # Apply adjustments from each pattern (weighted by confidence)
        for pattern in detected_patterns:
            # Handle both dict and object formats for patterns
            if isinstance(pattern, dict):
                # Extract pattern name from 'item' field (format: "**Pattern Name** - description")
                pattern_item = pattern.get('item', '')
                # Extract pattern name (text between ** markers)
                import re
                match = re.search(r'\*\*([^*]+)\*\*', pattern_item)
                pattern_name = match.group(1).strip() if match else pattern_item.split('-')[0].strip()
                pattern_confidence = pattern.get('confidence', 0.8)
            else:
                # Object format with pattern_type attribute
                pattern_name = pattern.pattern_type
                pattern_confidence = pattern.confidence
            
            # Normalize pattern name: lowercase, replace spaces/hyphens with underscores, remove common suffixes
            normalized_pattern_name = pattern_name.lower().replace(' ', '_').replace('-', '_')
            # Remove common suffixes like "_architecture", "_pattern"
            normalized_pattern_name = normalized_pattern_name.replace('_architecture', '').replace('_pattern', '')
            
            pattern_config = self.pattern_definitions.get(normalized_pattern_name, {})
            if not pattern_config:
                self.logger.warning(f"No configuration found for pattern: {pattern_name} (normalized: {normalized_pattern_name})")
                continue
            
            scoring_adjustments = pattern_config.get('scoring_adjustments', {})
            
            # Get capabilities to ignore and emphasize
            ignore_capabilities = scoring_adjustments.get('ignore_capabilities', [])
            emphasize_capabilities_config = scoring_adjustments.get('emphasize_capabilities', [])
            adjustment_factor = scoring_adjustments.get('adjustment_factor', 1.0)
            
            # Apply ignore adjustments (reduce contribution to near zero)
            for ignore_cap in ignore_capabilities:
                if ignore_cap in adjusted_capability_contributions:
                    original_value = adjusted_capability_contributions[ignore_cap]
                    # Reduce to 10% of original (not completely zero to maintain transparency)
                    adjusted_capability_contributions[ignore_cap] = original_value * 0.1
                    adjustment_log.append(
                        f"  ↓ Reduced {ignore_cap} contribution by 90% "
                        f"(not relevant for {pattern_name})"
                    )
            
            # Apply emphasize adjustments (increase contribution)
            # Handle both list and dict formats for emphasize_capabilities
            if isinstance(emphasize_capabilities_config, dict):
                # Dictionary format: capability -> multiplier
                for emphasize_cap, multiplier in emphasize_capabilities_config.items():
                    if emphasize_cap in adjusted_capability_contributions:
                        original_value = adjusted_capability_contributions[emphasize_cap]
                        # Apply multiplier weighted by pattern confidence
                        weighted_multiplier = 1.0 + (multiplier - 1.0) * pattern_confidence
                        adjusted_capability_contributions[emphasize_cap] = original_value * weighted_multiplier
                        adjustment_log.append(
                            f"  ↑ Increased {emphasize_cap} contribution by {(weighted_multiplier-1)*100:.0f}% "
                            f"(important for {pattern_name})"
                        )
            elif isinstance(emphasize_capabilities_config, list):
                # List format: just capability names, use default 1.2x multiplier
                default_multiplier = 1.2
                for emphasize_cap in emphasize_capabilities_config:
                    if emphasize_cap in adjusted_capability_contributions:
                        original_value = adjusted_capability_contributions[emphasize_cap]
                        # Apply default multiplier weighted by pattern confidence
                        weighted_multiplier = 1.0 + (default_multiplier - 1.0) * pattern_confidence
                        adjusted_capability_contributions[emphasize_cap] = original_value * weighted_multiplier
                        adjustment_log.append(
                            f"  ↑ Increased {emphasize_cap} contribution by {(weighted_multiplier-1)*100:.0f}% "
                            f"(important for {pattern_name})"
                        )
            
            # Apply overall adjustment factor
            if adjustment_factor != 1.0:
                weighted_factor = 1.0 + (adjustment_factor - 1.0) * pattern_confidence
                for cap_name in adjusted_capability_contributions:
                    adjusted_capability_contributions[cap_name] *= weighted_factor
                adjustment_log.append(
                    f"  ⚖️  Applied {pattern_name} adjustment factor: {weighted_factor:.2f}"
                )
        
        # Recalculate final score with adjusted contributions
        total_capability_points = sum(adjusted_capability_contributions.values())
        raw_score = (
            base_score.baseline_score +
            total_capability_points +
            base_score.complexity_adjustment
        )
        
        # Apply score caps (from configuration, typically 95 max)
        final_score = max(0, min(95, raw_score))
        
        # Create adjusted score object
        adjusted_score = PillarScore(
            pillar_name=pillar_name,
            final_score=final_score,
            baseline_score=base_score.baseline_score,
            capability_contributions=adjusted_capability_contributions,
            complexity_adjustment=base_score.complexity_adjustment,
            confidence_level=base_score.confidence_level,
            evidence=base_score.evidence + [f"Pattern-adjusted for: {', '.join(p.pattern_type for p in detected_patterns)}"],
            missing_capabilities=base_score.missing_capabilities,
            breakdown=base_score.breakdown,
            calculation_timestamp=datetime.utcnow().isoformat(),
            raw_score=raw_score
        )
        
        # Log adjustments if any were made
        if adjustment_log:
            self.logger.debug(f"Pattern adjustments for {pillar_name}:")
            for log_entry in adjustment_log:
                self.logger.debug(log_entry)
            self.logger.debug(
                f"  Final: {base_score.final_score:.1f}% → {final_score:.1f}% "
                f"(Δ {final_score - base_score.final_score:+.1f})"
            )
        
        return adjusted_score
    
    def _log_adjustment_summary(
        self,
        base_scores: Dict[str, PillarScore],
        adjusted_scores: Dict[str, PillarScore]
    ) -> None:
        """
        Log summary of pattern adjustments.
        
        Args:
            base_scores: Scores before adjustments
            adjusted_scores: Scores after adjustments
        """
        self.logger.info("📊 Pattern Adjustment Summary:")
        
        for pillar_name in base_scores:
            base = base_scores[pillar_name].final_score
            adjusted = adjusted_scores[pillar_name].final_score
            diff = adjusted - base
            
            if abs(diff) > 0.1:  # Only log if there's a meaningful change
                direction = "↑" if diff > 0 else "↓"
                self.logger.info(
                    f"  {direction} {pillar_name}: {base:.1f}% → {adjusted:.1f}% "
                    f"({diff:+.1f})"
                )
    
    def get_pattern_expectations(
        self,
        pattern: ArchitecturePattern
    ) -> Dict[str, List[str]]:
        """
        Get expected capabilities for a pattern.
        
        Args:
            pattern: Architecture pattern
            
        Returns:
            Dict mapping pillars to expected capabilities
            
        Example for serverless:
        {
            'reliability': ['event-driven scaling', 'managed service redundancy'],
            'performance': ['caching', 'async processing'],
            'cost': ['pay-per-use', 'auto-scaling']
        }
        """
        # Handle both dict and object formats
        if isinstance(pattern, dict):
            pattern_item = pattern.get('item', '')
            import re
            match = re.search(r'\*\*([^*]+)\*\*', pattern_item)
            pattern_name = match.group(1).strip() if match else pattern_item.split('-')[0].strip()
        else:
            pattern_name = pattern.pattern_type
        
        # Normalize pattern name: lowercase, replace spaces/hyphens with underscores, remove common suffixes
        normalized_pattern_name = pattern_name.lower().replace(' ', '_').replace('-', '_')
        # Remove common suffixes like "_architecture", "_pattern"
        normalized_pattern_name = normalized_pattern_name.replace('_architecture', '').replace('_pattern', '')
        
        pattern_config = self.pattern_definitions.get(normalized_pattern_name, {})
        return pattern_config.get('expected_capabilities', {})
    
    def detect_pattern_from_services(
        self,
        detected_services: List[str]
    ) -> List[ArchitecturePattern]:
        """
        Detect architecture patterns from detected services.
        
        This is a helper method that can be used if patterns aren't already detected.
        
        Args:
            detected_services: List of detected AWS service names
            
        Returns:
            List of detected patterns with confidence scores
        """
        detected_patterns = []
        
        # Normalize service names for matching
        normalized_services = [s.lower() for s in detected_services]
        
        for pattern_name, pattern_config in self.pattern_definitions.items():
            indicator_services = pattern_config.get('indicator_services', [])
            confidence_threshold = pattern_config.get('confidence_threshold', 0.7)
            
            # Calculate pattern confidence based on indicator service matches
            matches = 0
            for indicator in indicator_services:
                # Support regex-like patterns (e.g., "ECS|EKS|Fargate")
                if '|' in indicator:
                    # OR pattern
                    options = [opt.strip().lower() for opt in indicator.split('|')]
                    if any(opt in ' '.join(normalized_services) for opt in options):
                        matches += 1
                else:
                    # Simple match
                    if indicator.lower() in ' '.join(normalized_services):
                        matches += 1
            
            # Calculate confidence
            if indicator_services:
                confidence = matches / len(indicator_services)
            else:
                confidence = 0.0
            
            # Add pattern if confidence exceeds threshold
            if confidence >= confidence_threshold:
                pattern = ArchitecturePattern(
                    pattern_type=pattern_name,
                    confidence=confidence,
                    key_services=[s for s in detected_services if any(
                        ind.lower() in s.lower() for ind in indicator_services
                    )],
                    expected_capabilities=pattern_config.get('expected_capabilities', {}),
                    scoring_adjustments=pattern_config.get('scoring_adjustments', {})
                )
                detected_patterns.append(pattern)
                
                self.logger.info(
                    f"✓ Detected pattern: {pattern_name} "
                    f"(confidence={confidence:.2f}, matches={matches}/{len(indicator_services)})"
                )
        
        return detected_patterns
    
    def validate_pattern_adjustments(
        self,
        base_scores: Dict[str, PillarScore],
        adjusted_scores: Dict[str, PillarScore]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that pattern adjustments are reasonable.
        
        Checks:
        1. Adjusted scores still in valid range (0-100)
        2. Adjustments are not too extreme (>30 point changes)
        3. Score variance maintained (not all scores the same)
        
        Args:
            base_scores: Scores before adjustments
            adjusted_scores: Scores after adjustments
            
        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []
        
        # Check 1: Scores in valid range
        for pillar, score in adjusted_scores.items():
            if not (0 <= score.final_score <= 100):
                warnings.append(
                    f"{pillar} adjusted score out of range: {score.final_score}"
                )
        
        # Check 2: Adjustments not too extreme
        for pillar in base_scores:
            base = base_scores[pillar].final_score
            adjusted = adjusted_scores[pillar].final_score
            diff = abs(adjusted - base)
            
            if diff > 30:
                warnings.append(
                    f"{pillar} adjustment too extreme: {diff:.1f} points "
                    f"({base:.1f}% → {adjusted:.1f}%)"
                )
        
        # Check 3: Score variance maintained
        adjusted_values = [s.final_score for s in adjusted_scores.values()]
        if adjusted_values:
            score_range = max(adjusted_values) - min(adjusted_values)
            if score_range < 5:
                warnings.append(
                    f"Low score variance after adjustments ({score_range:.1f}%), "
                    "scores may be too similar"
                )
        
        is_valid = len(warnings) == 0
        
        if warnings:
            self.logger.warning(f"Pattern adjustment validation warnings: {warnings}")
        
        return is_valid, warnings
    
    def reload_configuration(self):
        """
        Reload pattern definitions from configuration files.
        
        Supports hot-reload for production tuning without restart.
        """
        self.logger.info("Reloading pattern definitions")
        self.pattern_definitions = self._load_pattern_definitions()
        self.logger.info(f"Pattern definitions reloaded: {len(self.pattern_definitions)} patterns")
    
    def _create_pattern_from_name(self, pattern_name: str) -> Optional[ArchitecturePattern]:
        """
        Create an ArchitecturePattern object from a pattern name string.
        
        Args:
            pattern_name: Name of the pattern (e.g., "serverless", "microservices")
            
        Returns:
            ArchitecturePattern object or None if pattern not found
        """
        # Normalize pattern name (lowercase, remove spaces/underscores)
        normalized_name = pattern_name.lower().replace('_', '').replace('-', '').replace(' ', '')
        
        # Try to find matching pattern definition
        for pattern_key, pattern_def in self.pattern_definitions.items():
            normalized_key = pattern_key.lower().replace('_', '').replace('-', '').replace(' ', '')
            if normalized_key == normalized_name or pattern_key.lower() == pattern_name.lower():
                # Create ArchitecturePattern object with default confidence
                return ArchitecturePattern(
                    pattern_type=pattern_key,
                    confidence=0.8,  # Default confidence for string-based patterns
                    key_services=[],
                    expected_capabilities=pattern_def.get('expected_capabilities', {}),
                    scoring_adjustments=pattern_def.get('scoring_adjustments', {})
                )
        
        self.logger.warning(f"Pattern '{pattern_name}' not found in definitions")
        return None
    
    def get_pattern_info(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific pattern.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Pattern configuration dictionary or None if not found
        """
        return self.pattern_definitions.get(pattern_name)
    
    def list_available_patterns(self) -> List[str]:
        """
        Get list of all available pattern names.
        
        Returns:
            List of pattern names
        """
        return list(self.pattern_definitions.keys())


# Global pattern adjuster instance
pattern_adjuster = PatternAdjuster()
