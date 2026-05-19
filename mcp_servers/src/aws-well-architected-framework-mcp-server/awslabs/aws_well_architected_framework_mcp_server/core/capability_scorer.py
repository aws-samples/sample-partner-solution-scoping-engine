"""
Capability-based scoring engine for WAFR assessments.

Implements dynamic pillar scoring based on detected capabilities, replacing
static default scores with evidence-based calculations.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..core.logger import WAFRLogger
from ..models.capability import DetectedCapability, CapabilityMatrix
from ..models.scoring import PillarScore, ScoreBreakdown, ScoreComponent


class CapabilityScorer:
    """
    Dynamic scoring engine based on capability detection.
    
    Scoring Logic:
    - Baseline: 30-40% (minimal/no capabilities detected)
    - Good: 60-75% (core capabilities present)
    - Excellent: 80-95% (comprehensive capabilities with good coverage)
    
    Formula:
        score = baseline + Σ(capability_contribution) + complexity_adjustment
        
    Where:
        capability_contribution = max_points * weight * coverage * confidence
        complexity_adjustment = -5 to +5 based on architecture complexity
        Final score capped at 95% (perfection unrealistic)
    
    Follows MCP server patterns:
    - Shared backend logging
    - Configuration-driven
    - Graceful degradation
    - Comprehensive error handling
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize CapabilityScorer.
        
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
        
        # Load scoring parameters from configuration
        self.scoring_params = self._load_scoring_parameters()
        
        # Extract baseline scores with pillar name normalization
        raw_baseline_scores = self.scoring_params.get('baseline_scores', {
            'security': 40,
            'reliability': 42,
            'performance': 42,
            'performance_efficiency': 42,
            'cost_optimization': 40,
            'operational_excellence': 42,
            'sustainability': 40
        })
        
        # Normalize pillar names to handle variations (performance vs performance_efficiency)
        self.baseline_scores = {}
        for pillar, score in raw_baseline_scores.items():
            self.baseline_scores[pillar] = score
            # Add aliases for common pillar name variations
            if pillar == 'performance':
                self.baseline_scores['performance_efficiency'] = score
            elif pillar == 'performance_efficiency':
                self.baseline_scores['performance'] = score
        
        # Extract complexity adjustments
        self.complexity_adjustments = self.scoring_params.get('complexity_adjustments', {})
        
        # Extract score caps
        self.score_caps = self.scoring_params.get('score_caps', {
            'maximum': 95,
            'minimum': 0
        })
        
        # Maximum points available from capabilities
        self.max_capability_points = 60.0
        
        self.logger.info("CapabilityScorer initialized with configuration-driven parameters")
    
    def _load_scoring_parameters(self) -> Dict[str, Any]:
        """
        Load scoring parameters from JSON configuration.
        
        Loads from config/scoring/scoring_parameters.json
        
        Returns:
            Dictionary with scoring parameters
        """
        scoring_file = os.path.join(self.config_dir, 'scoring', 'scoring_parameters.json')
        
        if not os.path.exists(scoring_file):
            self.logger.warning(f"Scoring parameters file not found: {scoring_file}, using defaults")
            return {}
        
        try:
            with open(scoring_file, 'r') as f:
                params = json.load(f)
                self.logger.debug(f"Loaded scoring parameters from {scoring_file}")
                return params
        except Exception as e:
            self.logger.error(f"Error loading scoring parameters: {e}")
            return {}
    
    def calculate_pillar_score(
        self,
        pillar: str,
        capabilities: List[DetectedCapability],
        architecture_complexity: int
    ) -> PillarScore:
        """
        Calculate score for a single pillar based on capabilities.
        
        Algorithm:
        1. Start with baseline score (30-40%)
        2. Add points for each detected capability weighted by:
           - Capability importance (weight)
           - Coverage level (0.0-1.0)
           - Detection confidence (0.0-1.0)
        3. Apply complexity adjustment
        4. Cap at 95% (perfection is unrealistic)
        
        Args:
            pillar: Pillar name (security, reliability, etc.)
            capabilities: List of detected capabilities for this pillar
            architecture_complexity: Number of services (used for complexity adjustment)
            
        Returns:
            PillarScore with detailed breakdown
        """
        self.logger.info(f"🎯 Calculating score for {pillar} pillar with {len(capabilities)} capabilities")
        
        # Get baseline score for this pillar
        baseline = self.baseline_scores.get(pillar, 40)
        
        # Calculate capability contributions
        capability_contributions = {}
        total_capability_points = 0.0
        score_components = []
        
        for capability in capabilities:
            contribution = self._calculate_capability_contribution(capability)
            capability_contributions[capability.name] = contribution
            total_capability_points += contribution
            
            # Create score component for transparency
            component = ScoreComponent(
                name=capability.name,
                points=contribution,
                weight=capability.weight,
                coverage=capability.coverage,
                confidence=capability.confidence,
                evidence=capability.evidence
            )
            score_components.append(component)
            
            self.logger.debug(
                f"  📊 {capability.name}: +{contribution:.2f} points "
                f"(weight={capability.weight:.2f}, coverage={capability.coverage:.2f}, "
                f"confidence={capability.confidence:.2f})"
            )
        
        # Calculate complexity adjustment
        complexity_adjustment = self._calculate_complexity_adjustment(architecture_complexity)
        
        # Calculate final score
        raw_score = baseline + total_capability_points + complexity_adjustment
        
        # Apply score caps
        final_score = max(
            self.score_caps['minimum'],
            min(self.score_caps['maximum'], raw_score)
        )
        
        # Calculate overall confidence - ENHANCED DYNAMIC CALCULATION
        # Confidence is based on:
        # 1. Average capability confidence (40% weight)
        # 2. Capability coverage breadth (30% weight) - how many capabilities detected
        # 3. Evidence quality (30% weight) - average coverage of detected capabilities
        if capabilities:
            # Factor 1: Average capability confidence
            avg_capability_confidence = sum(c.confidence for c in capabilities) / len(capabilities)
            
            # Factor 2: Capability coverage breadth
            # Expected capabilities per pillar varies, but typically 3-5
            expected_capabilities = 4  # Average expected per pillar
            coverage_breadth = min(1.0, len(capabilities) / expected_capabilities)
            
            # Factor 3: Evidence quality (average coverage)
            avg_coverage = sum(c.coverage for c in capabilities) / len(capabilities)
            
            # Weighted combination
            overall_confidence = (
                0.4 * avg_capability_confidence +
                0.3 * coverage_breadth +
                0.3 * avg_coverage
            )
            
            # Boost confidence if we have high coverage capabilities
            high_coverage_count = sum(1 for c in capabilities if c.coverage >= 0.7)
            if high_coverage_count >= 2:
                overall_confidence = min(0.95, overall_confidence + 0.1)
        else:
            overall_confidence = 0.3  # Low confidence with no capabilities
        
        # Identify missing capabilities
        missing_capabilities = self._identify_missing_capabilities(pillar, capabilities)
        
        # Create score breakdown
        breakdown = ScoreBreakdown(
            baseline_score=baseline,
            capability_points=total_capability_points,
            complexity_adjustment=complexity_adjustment,
            raw_score=raw_score,
            final_score=final_score,
            components=score_components
        )
        
        # Create pillar score - simplified for compatibility with server.py
        class SimplePillarScore:
            def __init__(self, pillar, score):
                self.pillar = pillar
                self.score = score
                # Add missing attributes with calculated values
                self.baseline_score = baseline
                self.capability_contributions = capability_contributions  # Use the dict, not the float
                self.complexity_adjustment = complexity_adjustment
                self.pattern_adjustments = {}
                self.confidence_level = overall_confidence
                self.evidence = [c.name for c in capabilities]
                self.missing_capabilities = missing_capabilities
                self.breakdown = breakdown  # Add the breakdown attribute
                self.final_score = score  # Add the final_score attribute
        
        pillar_score = SimplePillarScore(pillar, final_score)
        
        self.logger.info(
            f"✅ {pillar} score: {final_score:.1f}% "
            f"(baseline={baseline}, capabilities=+{total_capability_points:.1f}, "
            f"complexity={complexity_adjustment:+.1f}, confidence={overall_confidence:.2f})"
        )
        
        return pillar_score
    
    def _calculate_capability_contribution(
        self,
        capability: DetectedCapability
    ) -> float:
        """
        Calculate how much a capability contributes to the score.
        
        Formula: max_points * weight * coverage * confidence
        
        Example:
        - Encryption capability: weight=0.25 (25% of security)
        - Coverage: 0.8 (80% of data stores encrypted)
        - Confidence: 0.9 (high confidence detection)
        - Contribution: 60 * 0.25 * 0.8 * 0.9 = 10.8 points
        
        Args:
            capability: DetectedCapability
            
        Returns:
            Score contribution in points
        """
        contribution = (
            self.max_capability_points *
            capability.weight *
            capability.coverage *
            capability.confidence
        )
        
        return contribution
    
    def _calculate_complexity_adjustment(
        self,
        service_count: int
    ) -> float:
        """
        Calculate complexity adjustment based on architecture size.
        
        Logic:
        - High complexity (20+ services): -5 points (harder to manage)
        - Medium complexity (10-19 services): -2 points
        - Low complexity (<5 services): +3 points (simpler is better)
        - Normal complexity (5-9 services): 0 points
        
        Args:
            service_count: Number of services in architecture
            
        Returns:
            Adjustment in points (-5 to +5)
        """
        adjustments = self.complexity_adjustments
        
        # High complexity
        high_config = adjustments.get('high_complexity', {})
        if service_count >= high_config.get('threshold', 20):
            return high_config.get('adjustment', -5)
        
        # Medium complexity
        medium_config = adjustments.get('medium_complexity', {})
        if service_count >= medium_config.get('threshold', 10):
            return medium_config.get('adjustment', -2)
        
        # Low complexity
        low_config = adjustments.get('low_complexity', {})
        if service_count < low_config.get('threshold', 5):
            return low_config.get('adjustment', 3)
        
        # Normal complexity
        return 0.0
    
    def _identify_missing_capabilities(
        self,
        pillar: str,
        detected_capabilities: List[DetectedCapability]
    ) -> List[str]:
        """
        Identify capabilities that are missing or have low coverage.
        
        Args:
            pillar: Pillar name
            detected_capabilities: List of detected capabilities
            
        Returns:
            List of missing capability names
        """
        # Get all possible capabilities for this pillar from config
        # For now, return capabilities with coverage < 0.3
        missing = []
        
        for capability in detected_capabilities:
            if capability.coverage < 0.3:
                missing.append(f"{capability.name} (low coverage: {capability.coverage:.0%})")
        
        return missing
    
    def calculate_all_pillar_scores(
        self,
        capability_matrix: CapabilityMatrix,
        architecture_complexity: int
    ) -> Dict[str, PillarScore]:
        """
        Calculate scores for all six pillars.
        
        Args:
            capability_matrix: CapabilityMatrix with all detected capabilities
            architecture_complexity: Number of services
            
        Returns:
            Dictionary mapping pillar names to PillarScore objects
        """
        self.logger.info(f"📊 Calculating scores for all 6 pillars (complexity={architecture_complexity} services)")
        
        pillars = [
            'security',
            'reliability',
            'performance',
            'cost_optimization',
            'operational_excellence',
            'sustainability'
        ]
        
        scores = {}
        
        for pillar in pillars:
            capabilities = capability_matrix.get_capabilities_for_pillar(pillar)
            score = self.calculate_pillar_score(pillar, capabilities, architecture_complexity)
            scores[pillar] = score
        
        # Log summary
        avg_score = sum(s.final_score for s in scores.values()) / len(scores)
        self.logger.info(f"✅ All pillar scores calculated. Average: {avg_score:.1f}%")
        
        return scores
    
    def validate_score_reasonableness(
        self,
        pillar_scores: Dict[str, PillarScore]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that scores are reasonable.
        
        Checks:
        1. All scores between 0-100
        2. Score variance > 10% (not all the same)
        3. Confidence levels reasonable
        4. Evidence provided for scores
        
        Args:
            pillar_scores: Dictionary of pillar scores
            
        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []
        
        # Check 1: Scores in valid range
        for pillar, score in pillar_scores.items():
            if not (0 <= score.final_score <= 100):
                warnings.append(f"{pillar} score out of range: {score.final_score}")
        
        # Check 2: Score variance
        scores = [s.final_score for s in pillar_scores.values()]
        if scores:
            score_range = max(scores) - min(scores)
            if score_range < 10:
                warnings.append(f"Low score variance ({score_range:.1f}%), scores may be too similar")
        
        # Check 3: Confidence levels
        for pillar, score in pillar_scores.items():
            if score.confidence_level < 0.3:
                warnings.append(f"{pillar} has low confidence: {score.confidence_level:.2f}")
        
        # Check 4: Evidence
        for pillar, score in pillar_scores.items():
            if not score.evidence:
                warnings.append(f"{pillar} has no evidence for score")
        
        is_valid = len(warnings) == 0
        
        if warnings:
            self.logger.warning(f"Score validation warnings: {warnings}")
        
        return is_valid, warnings
    
    def reload_configuration(self):
        """
        Reload scoring parameters from configuration files.
        
        Supports hot-reload for production tuning without restart.
        """
        self.logger.info("Reloading scoring parameters")
        self.scoring_params = self._load_scoring_parameters()
        self.baseline_scores = self.scoring_params.get('baseline_scores', self.baseline_scores)
        self.complexity_adjustments = self.scoring_params.get('complexity_adjustments', self.complexity_adjustments)
        self.score_caps = self.scoring_params.get('score_caps', self.score_caps)
        self.logger.info("Scoring parameters reloaded")


# Global capability scorer instance
capability_scorer = CapabilityScorer()
