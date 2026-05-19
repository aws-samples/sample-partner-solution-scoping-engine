"""
Optimized Scoring Algorithms for WAFR Enterprise Scoring.

Implements optimized versions of scoring algorithms to minimize redundant calculations
and improve performance:
- Optimized capability coverage calculations
- Streamlined score aggregation
- Batch processing for multiple capabilities
- Vectorized operations where possible

Target: <100ms per pillar score calculation
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from datetime import datetime

from ..core.logger import WAFRLogger
from ..models.capability import DetectedCapability, CapabilityMatrix
from ..models.scoring import PillarScore, ScoreBreakdown, ScoreComponent


class OptimizedCapabilityCoverageCalculator:
    """
    Optimized calculator for capability coverage.
    
    Minimizes redundant service checks and configuration lookups.
    """
    
    def __init__(self):
        """Initialize OptimizedCapabilityCoverageCalculator."""
        self.logger = WAFRLogger(__name__)
        
        # Cache for service configuration checks
        self._config_check_cache: Dict[str, bool] = {}
    
    def calculate_coverage_batch(
        self,
        capabilities: List[str],
        capability_definitions: Dict[str, Dict[str, Any]],
        detected_services: List[str],
        service_configurations: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate coverage for multiple capabilities in batch.
        
        More efficient than calculating each capability individually.
        
        Args:
            capabilities: List of capability names to calculate
            capability_definitions: Capability definitions
            detected_services: List of detected services
            service_configurations: Service configuration data
            
        Returns:
            Dictionary mapping capability names to coverage values (0.0-1.0)
        """
        coverage_results = {}
        
        # Pre-process detected services into a set for O(1) lookup
        service_set = set(detected_services)
        
        for capability_name in capabilities:
            capability_def = capability_definitions.get(capability_name, {})
            
            coverage = self._calculate_single_coverage_optimized(
                capability_def,
                service_set,
                service_configurations
            )
            
            coverage_results[capability_name] = coverage
        
        return coverage_results
    
    def _calculate_single_coverage_optimized(
        self,
        capability_def: Dict[str, Any],
        service_set: set,
        service_configurations: Dict[str, Any]
    ) -> float:
        """
        Calculate coverage for a single capability (optimized).
        
        Args:
            capability_def: Capability definition
            service_set: Set of detected services (for O(1) lookup)
            service_configurations: Service configuration data
            
        Returns:
            Coverage value (0.0-1.0)
        """
        services_def = capability_def.get('services', {})
        
        if not services_def:
            return 0.0
        
        # Count services that provide this capability
        total_relevant = 0
        implemented_count = 0
        
        for service_name, service_def in services_def.items():
            # Check if service is detected (O(1) with set)
            detection_patterns = service_def.get('detection_patterns', [])
            
            is_detected = False
            for pattern in detection_patterns:
                # Simple pattern matching (can be optimized further with regex compilation)
                if any(pattern.lower() in s.lower() for s in service_set):
                    is_detected = True
                    break
            
            if is_detected:
                total_relevant += 1
                
                # Check configuration requirements
                config_checks = service_def.get('configuration_checks', [])
                
                if not config_checks:
                    # No config checks, service presence is enough
                    implemented_count += 1
                else:
                    # Check if configuration requirements are met
                    if self._check_configuration_optimized(
                        service_name,
                        config_checks,
                        service_configurations
                    ):
                        implemented_count += 1
        
        if total_relevant == 0:
            return 0.0
        
        return implemented_count / total_relevant
    
    def _check_configuration_optimized(
        self,
        service_name: str,
        config_checks: List[Dict[str, Any]],
        service_configurations: Dict[str, Any]
    ) -> bool:
        """
        Check if service configuration meets requirements (optimized).
        
        Uses caching to avoid redundant checks.
        
        Args:
            service_name: Service name
            config_checks: List of configuration checks
            service_configurations: Service configuration data
            
        Returns:
            True if all checks pass
        """
        # Generate cache key
        cache_key = f"{service_name}:{str(config_checks)}"
        
        # Check cache
        if cache_key in self._config_check_cache:
            return self._config_check_cache[cache_key]
        
        # Perform checks
        service_config = service_configurations.get(service_name, {})
        
        result = True
        for check in config_checks:
            field = check.get('field')
            required_values = check.get('required_values', [])
            
            if field not in service_config:
                result = False
                break
            
            if service_config[field] not in required_values:
                result = False
                break
        
        # Cache result
        self._config_check_cache[cache_key] = result
        
        return result
    
    def clear_cache(self):
        """Clear configuration check cache."""
        self._config_check_cache.clear()


class OptimizedScoreAggregator:
    """
    Optimized score aggregation for multiple pillars.
    
    Minimizes redundant calculations and streamlines aggregation logic.
    """
    
    def __init__(self):
        """Initialize OptimizedScoreAggregator."""
        self.logger = WAFRLogger(__name__)
    
    def aggregate_pillar_scores(
        self,
        pillar_scores: Dict[str, PillarScore]
    ) -> Dict[str, Any]:
        """
        Aggregate pillar scores into overall assessment score.
        
        Optimized to calculate all metrics in a single pass.
        
        Args:
            pillar_scores: Dictionary of pillar scores
            
        Returns:
            Dictionary with aggregated scores and metrics
        """
        if not pillar_scores:
            return {
                'overall_score': 0.0,
                'pillar_scores': {},
                'score_distribution': {},
                'confidence_level': 0.0
            }
        
        # Single-pass calculation of all metrics
        total_score = 0.0
        total_confidence = 0.0
        score_distribution = defaultdict(int)
        pillar_count = len(pillar_scores)
        
        pillar_score_dict = {}
        
        for pillar, score in pillar_scores.items():
            # Accumulate totals
            total_score += score.final_score
            total_confidence += score.confidence_level
            
            # Categorize score
            if score.final_score >= 80:
                score_distribution['excellent'] += 1
            elif score.final_score >= 65:
                score_distribution['good'] += 1
            elif score.final_score >= 50:
                score_distribution['fair'] += 1
            else:
                score_distribution['needs_improvement'] += 1
            
            # Store pillar score
            pillar_score_dict[pillar] = {
                'score': score.final_score,
                'confidence': score.confidence_level,
                'baseline': score.baseline_score,
                'capability_points': sum(score.capability_contributions.values())
            }
        
        # Calculate averages
        overall_score = total_score / pillar_count
        overall_confidence = total_confidence / pillar_count
        
        return {
            'overall_score': overall_score,
            'pillar_scores': pillar_score_dict,
            'score_distribution': dict(score_distribution),
            'confidence_level': overall_confidence,
            'pillar_count': pillar_count
        }
    
    def calculate_score_variance(
        self,
        pillar_scores: Dict[str, PillarScore]
    ) -> Dict[str, float]:
        """
        Calculate score variance metrics.
        
        Args:
            pillar_scores: Dictionary of pillar scores
            
        Returns:
            Dictionary with variance metrics
        """
        if not pillar_scores:
            return {
                'min_score': 0.0,
                'max_score': 0.0,
                'range': 0.0,
                'std_dev': 0.0
            }
        
        scores = [s.final_score for s in pillar_scores.values()]
        
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        
        # Calculate standard deviation
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        return {
            'min_score': min_score,
            'max_score': max_score,
            'range': score_range,
            'std_dev': std_dev,
            'mean': mean
        }


class OptimizedCapabilityContributionCalculator:
    """
    Optimized calculator for capability contributions to scores.
    
    Pre-computes common calculations and uses vectorized operations.
    """
    
    def __init__(self, max_capability_points: float = 60.0):
        """
        Initialize OptimizedCapabilityContributionCalculator.
        
        Args:
            max_capability_points: Maximum points from capabilities
        """
        self.logger = WAFRLogger(__name__)
        self.max_capability_points = max_capability_points
    
    def calculate_contributions_batch(
        self,
        capabilities: List[DetectedCapability]
    ) -> Tuple[Dict[str, float], float]:
        """
        Calculate contributions for multiple capabilities in batch.
        
        More efficient than calculating each contribution individually.
        
        Args:
            capabilities: List of DetectedCapability objects
            
        Returns:
            Tuple of (contributions_dict, total_points)
        """
        contributions = {}
        total_points = 0.0
        
        # Pre-compute max_points to avoid repeated multiplication
        max_points = self.max_capability_points
        
        for capability in capabilities:
            # Optimized formula: single multiplication chain
            contribution = (
                max_points *
                capability.weight *
                capability.coverage *
                capability.confidence
            )
            
            contributions[capability.name] = contribution
            total_points += contribution
        
        return contributions, total_points
    
    def calculate_single_contribution(
        self,
        capability: DetectedCapability
    ) -> float:
        """
        Calculate contribution for a single capability.
        
        Args:
            capability: DetectedCapability object
            
        Returns:
            Contribution in points
        """
        return (
            self.max_capability_points *
            capability.weight *
            capability.coverage *
            capability.confidence
        )


class StreamlinedScoreCalculator:
    """
    Streamlined score calculator that combines all optimizations.
    
    Provides a single, optimized interface for score calculation.
    """
    
    def __init__(
        self,
        baseline_scores: Dict[str, float],
        complexity_adjustments: Dict[str, Dict[str, Any]],
        score_caps: Dict[str, float],
        max_capability_points: float = 60.0
    ):
        """
        Initialize StreamlinedScoreCalculator.
        
        Args:
            baseline_scores: Baseline scores for each pillar
            complexity_adjustments: Complexity adjustment configuration
            score_caps: Score cap configuration
            max_capability_points: Maximum points from capabilities
        """
        self.logger = WAFRLogger(__name__)
        
        self.baseline_scores = baseline_scores
        self.complexity_adjustments = complexity_adjustments
        self.score_caps = score_caps
        
        # Initialize optimized components
        self.contribution_calculator = OptimizedCapabilityContributionCalculator(
            max_capability_points
        )
        
        self.logger.info("StreamlinedScoreCalculator initialized")
    
    def calculate_pillar_score_optimized(
        self,
        pillar: str,
        capabilities: List[DetectedCapability],
        architecture_complexity: int
    ) -> PillarScore:
        """
        Calculate pillar score with all optimizations applied.
        
        Target: <100ms per pillar
        
        Args:
            pillar: Pillar name
            capabilities: List of detected capabilities
            architecture_complexity: Number of services
            
        Returns:
            PillarScore with detailed breakdown
        """
        start_time = time.time()
        
        # Get baseline score (O(1) dict lookup)
        baseline = self.baseline_scores.get(pillar, 40)
        
        # Calculate all capability contributions in batch
        capability_contributions, total_capability_points = \
            self.contribution_calculator.calculate_contributions_batch(capabilities)
        
        # Calculate complexity adjustment (optimized with early returns)
        complexity_adjustment = self._calculate_complexity_adjustment_fast(
            architecture_complexity
        )
        
        # Calculate final score
        raw_score = baseline + total_capability_points + complexity_adjustment
        final_score = max(
            self.score_caps['minimum'],
            min(self.score_caps['maximum'], raw_score)
        )
        
        # Calculate overall confidence (single pass)
        overall_confidence = (
            sum(c.confidence for c in capabilities) / len(capabilities)
            if capabilities else 0.3
        )
        
        # Create score components (optimized)
        score_components = [
            ScoreComponent(
                name=cap.name,
                points=capability_contributions[cap.name],
                weight=cap.weight,
                coverage=cap.coverage,
                confidence=cap.confidence,
                evidence=cap.evidence
            )
            for cap in capabilities
        ]
        
        # Create score breakdown
        breakdown = ScoreBreakdown(
            baseline_score=baseline,
            capability_points=total_capability_points,
            complexity_adjustment=complexity_adjustment,
            raw_score=raw_score,
            final_score=final_score,
            components=score_components
        )
        
        # Calculate missing capabilities based on expected capabilities per pillar
        # PHASE 6 FIX: Populate missing_capabilities for recommendation generation
        expected_capabilities_by_pillar = {
            "security": [
                "encryption", "identity_access", "data_protection", 
                "network_security", "monitoring_detection"
            ],
            "reliability": [
                "redundancy", "backup_recovery", "monitoring_alerting", 
                "scaling", "fault_tolerance"
            ],
            "performance_efficiency": [
                "caching", "compute_optimization", "database_optimization", 
                "content_delivery", "resource_selection"
            ],
            "cost_optimization": [
                "resource_optimization", "pricing_models", "storage_optimization", 
                "managed_services", "cost_monitoring"
            ],
            "operational_excellence": [
                "observability", "infrastructure_as_code", "deployment_automation", 
                "incident_response", "runbook_automation"
            ],
            "sustainability": [
                "managed_services", "efficient_compute", "resource_utilization", 
                "data_optimization", "region_selection"
            ]
        }
        
        # Get detected capability names (normalized)
        detected_cap_names = set(c.name.lower().replace(' ', '_') for c in capabilities)
        
        # Get expected capabilities for this pillar
        expected_caps = expected_capabilities_by_pillar.get(pillar, [])
        
        # Calculate missing capabilities
        missing_caps = [
            cap for cap in expected_caps 
            if cap.lower().replace(' ', '_') not in detected_cap_names
        ]
        
        self.logger.info(f"📊 {pillar}: Detected {len(capabilities)} capabilities, missing {len(missing_caps)}: {missing_caps}")
        
        # Create pillar score
        pillar_score = PillarScore(
            pillar_name=pillar,
            final_score=final_score,
            baseline_score=baseline,
            capability_contributions=capability_contributions,
            complexity_adjustment=complexity_adjustment,
            confidence_level=overall_confidence,
            evidence=[c.name for c in capabilities],
            missing_capabilities=missing_caps,  # PHASE 6 FIX: Now populated with actual missing capabilities
            breakdown=breakdown,
            calculation_timestamp=datetime.utcnow().isoformat(),
            raw_score=raw_score
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if elapsed_ms > 100:
            self.logger.warning(
                f"Score calculation for {pillar} took {elapsed_ms:.1f}ms (target: <100ms)"
            )
        
        return pillar_score
    
    def _calculate_complexity_adjustment_fast(
        self,
        service_count: int
    ) -> float:
        """
        Calculate complexity adjustment (optimized with early returns).
        
        Args:
            service_count: Number of services
            
        Returns:
            Adjustment in points
        """
        # Early returns for most common cases
        high_config = self.complexity_adjustments.get('high_complexity', {})
        if service_count >= high_config.get('threshold', 20):
            return high_config.get('adjustment', -5)
        
        medium_config = self.complexity_adjustments.get('medium_complexity', {})
        if service_count >= medium_config.get('threshold', 10):
            return medium_config.get('adjustment', -2)
        
        low_config = self.complexity_adjustments.get('low_complexity', {})
        if service_count < low_config.get('threshold', 5):
            return low_config.get('adjustment', 3)
        
        return 0.0
    
    def calculate_all_pillars_optimized(
        self,
        capability_matrix: CapabilityMatrix,
        architecture_complexity: int
    ) -> Dict[str, PillarScore]:
        """
        Calculate scores for all pillars with optimizations.
        
        Args:
            capability_matrix: CapabilityMatrix with all capabilities
            architecture_complexity: Number of services
            
        Returns:
            Dictionary mapping pillar names to PillarScore objects
        """
        start_time = time.time()
        
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
            score = self.calculate_pillar_score_optimized(
                pillar,
                capabilities,
                architecture_complexity
            )
            scores[pillar] = score
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        self.logger.info(
            f"All pillar scores calculated in {elapsed_ms:.0f}ms "
            f"(avg: {elapsed_ms/6:.0f}ms per pillar)"
        )
        
        return scores


class PerformanceMonitor:
    """
    Monitor performance of scoring operations.
    
    Tracks timing and identifies bottlenecks.
    """
    
    def __init__(self):
        """Initialize PerformanceMonitor."""
        self.logger = WAFRLogger(__name__)
        
        self._timings: Dict[str, List[float]] = defaultdict(list)
    
    def record_timing(self, operation: str, duration_ms: float):
        """
        Record timing for an operation.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
        """
        self._timings[operation].append(duration_ms)
    
    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get timing statistics for all operations.
        
        Returns:
            Dictionary with statistics for each operation
        """
        stats = {}
        
        for operation, timings in self._timings.items():
            if timings:
                stats[operation] = {
                    'count': len(timings),
                    'avg_ms': sum(timings) / len(timings),
                    'min_ms': min(timings),
                    'max_ms': max(timings),
                    'total_ms': sum(timings)
                }
        
        return stats
    
    def get_bottlenecks(self, threshold_ms: float = 100.0) -> List[Tuple[str, float]]:
        """
        Identify operations that exceed threshold.
        
        Args:
            threshold_ms: Threshold in milliseconds
            
        Returns:
            List of (operation, avg_duration) tuples for slow operations
        """
        bottlenecks = []
        
        for operation, timings in self._timings.items():
            if timings:
                avg_duration = sum(timings) / len(timings)
                if avg_duration > threshold_ms:
                    bottlenecks.append((operation, avg_duration))
        
        # Sort by duration (slowest first)
        bottlenecks.sort(key=lambda x: x[1], reverse=True)
        
        return bottlenecks
    
    def reset(self):
        """Reset all timing data."""
        self._timings.clear()
