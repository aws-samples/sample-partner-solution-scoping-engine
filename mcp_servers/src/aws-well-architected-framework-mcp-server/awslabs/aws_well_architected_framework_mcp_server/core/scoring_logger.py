"""
Enhanced Scoring Logger for WAFR Enterprise Scoring System

Provides comprehensive logging for capability detection, scoring calculations,
pattern adjustments, and recommendation generation with full transparency.

Requirements: 9.5
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ScoringEventType(Enum):
    """Event types for scoring operations"""
    CAPABILITY_DETECTION_START = "capability_detection_start"
    CAPABILITY_DETECTION_COMPLETE = "capability_detection_complete"
    CAPABILITY_DETECTED = "capability_detected"
    CAPABILITY_COVERAGE_CALCULATED = "capability_coverage_calculated"
    
    SCORE_CALCULATION_START = "score_calculation_start"
    SCORE_CALCULATION_COMPLETE = "score_calculation_complete"
    PILLAR_SCORE_CALCULATED = "pillar_score_calculated"
    BASELINE_SCORE_APPLIED = "baseline_score_applied"
    CAPABILITY_CONTRIBUTION_ADDED = "capability_contribution_added"
    COMPLEXITY_ADJUSTMENT_APPLIED = "complexity_adjustment_applied"
    
    PATTERN_ADJUSTMENT_START = "pattern_adjustment_start"
    PATTERN_ADJUSTMENT_COMPLETE = "pattern_adjustment_complete"
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_ADJUSTMENT_APPLIED = "pattern_adjustment_applied"
    
    RECOMMENDATION_GENERATION_START = "recommendation_generation_start"
    RECOMMENDATION_GENERATION_COMPLETE = "recommendation_generation_complete"
    CAPABILITY_GAP_IDENTIFIED = "capability_gap_identified"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    RECOMMENDATION_PRIORITIZED = "recommendation_prioritized"


@dataclass
class ScoringLogEntry:
    """Structured log entry for scoring operations"""
    timestamp: str
    event_type: str
    correlation_id: str
    pillar: Optional[str]
    operation: str
    level: str
    message: str
    details: Dict[str, Any]
    duration_ms: Optional[float] = None


class ScoringLogger:
    """
    Enhanced logger for scoring operations with detailed transparency.
    
    Logs all scoring decisions with evidence, breakdowns, and justifications.
    """
    
    def __init__(self, name: str = "wafr-scoring", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Configure handler if not already configured - use stderr to avoid interfering with MCP JSON-RPC on stdout
        if not self.logger.handlers:
            import sys
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.current_correlation_id: Optional[str] = None
        self.operation_start_times: Dict[str, float] = {}
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for tracking related operations"""
        self.current_correlation_id = correlation_id
    
    def clear_correlation_id(self):
        """Clear correlation ID"""
        self.current_correlation_id = None
    
    def _create_log_entry(self, 
                         event_type: ScoringEventType,
                         pillar: Optional[str],
                         operation: str,
                         level: str,
                         message: str,
                         **details) -> ScoringLogEntry:
        """Create structured log entry"""
        return ScoringLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            correlation_id=self.current_correlation_id or "unknown",
            pillar=pillar,
            operation=operation,
            level=level,
            message=message,
            details=details
        )
    
    def _log_entry(self, entry: ScoringLogEntry):
        """Log structured entry"""
        log_data = asdict(entry)
        log_message = json.dumps(log_data, default=str)
        
        log_level = getattr(self.logger, entry.level.lower())
        log_level(log_message)
    
    # Capability Detection Logging
    
    def log_capability_detection_start(self, 
                                      pillar: str,
                                      services: List[str],
                                      correlation_id: str):
        """Log start of capability detection"""
        self.set_correlation_id(correlation_id)
        self.operation_start_times[f"capability_detection_{pillar}"] = time.time()
        
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_DETECTION_START,
            pillar=pillar,
            operation="capability_detection",
            level="INFO",
            message=f"Starting capability detection for {pillar} pillar",
            service_count=len(services),
            services=services
        )
        self._log_entry(entry)
    
    def log_capability_detected(self,
                               pillar: str,
                               capability_name: str,
                               coverage: float,
                               evidence: List[str],
                               confidence: float):
        """Log detected capability with evidence"""
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_DETECTED,
            pillar=pillar,
            operation="capability_detection",
            level="INFO",
            message=f"Detected {capability_name} capability in {pillar} pillar",
            capability_name=capability_name,
            coverage=coverage,
            coverage_percent=f"{coverage * 100:.1f}%",
            evidence=evidence,
            evidence_count=len(evidence),
            confidence=confidence,
            confidence_percent=f"{confidence * 100:.1f}%"
        )
        self._log_entry(entry)
    
    def log_capability_coverage_calculation(self,
                                           pillar: str,
                                           capability_name: str,
                                           total_services: int,
                                           implementing_services: int,
                                           coverage: float,
                                           calculation_method: str):
        """Log capability coverage calculation details"""
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_COVERAGE_CALCULATED,
            pillar=pillar,
            operation="capability_detection",
            level="DEBUG",
            message=f"Calculated coverage for {capability_name}",
            capability_name=capability_name,
            total_services=total_services,
            implementing_services=implementing_services,
            coverage=coverage,
            coverage_percent=f"{coverage * 100:.1f}%",
            calculation_method=calculation_method,
            formula=f"{implementing_services}/{total_services} = {coverage:.3f}"
        )
        self._log_entry(entry)
    
    def log_capability_detection_complete(self,
                                         pillar: str,
                                         capabilities_detected: int,
                                         total_coverage: float):
        """Log completion of capability detection"""
        operation_key = f"capability_detection_{pillar}"
        duration_ms = None
        if operation_key in self.operation_start_times:
            duration_ms = (time.time() - self.operation_start_times[operation_key]) * 1000
            del self.operation_start_times[operation_key]
        
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_DETECTION_COMPLETE,
            pillar=pillar,
            operation="capability_detection",
            level="INFO",
            message=f"Completed capability detection for {pillar} pillar",
            capabilities_detected=capabilities_detected,
            total_coverage=total_coverage,
            total_coverage_percent=f"{total_coverage * 100:.1f}%",
            duration_ms=duration_ms
        )
        entry.duration_ms = duration_ms
        self._log_entry(entry)
    
    # Score Calculation Logging
    
    def log_score_calculation_start(self,
                                   pillar: str,
                                   capabilities_count: int,
                                   architecture_complexity: float):
        """Log start of score calculation"""
        self.operation_start_times[f"score_calculation_{pillar}"] = time.time()
        
        entry = self._create_log_entry(
            ScoringEventType.SCORE_CALCULATION_START,
            pillar=pillar,
            operation="score_calculation",
            level="INFO",
            message=f"Starting score calculation for {pillar} pillar",
            capabilities_count=capabilities_count,
            architecture_complexity=architecture_complexity
        )
        self._log_entry(entry)
    
    def log_baseline_score_applied(self,
                                  pillar: str,
                                  baseline_score: float,
                                  reason: str):
        """Log baseline score application"""
        entry = self._create_log_entry(
            ScoringEventType.BASELINE_SCORE_APPLIED,
            pillar=pillar,
            operation="score_calculation",
            level="INFO",
            message=f"Applied baseline score for {pillar} pillar",
            baseline_score=baseline_score,
            reason=reason
        )
        self._log_entry(entry)
    
    def log_capability_contribution(self,
                                   pillar: str,
                                   capability_name: str,
                                   weight: float,
                                   coverage: float,
                                   confidence: float,
                                   contribution: float,
                                   calculation_breakdown: str):
        """Log capability contribution to score"""
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_CONTRIBUTION_ADDED,
            pillar=pillar,
            operation="score_calculation",
            level="DEBUG",
            message=f"Added {capability_name} contribution to {pillar} score",
            capability_name=capability_name,
            weight=weight,
            coverage=coverage,
            confidence=confidence,
            contribution=contribution,
            contribution_points=f"+{contribution:.2f}",
            calculation_breakdown=calculation_breakdown
        )
        self._log_entry(entry)
    
    def log_complexity_adjustment(self,
                                 pillar: str,
                                 service_count: int,
                                 adjustment: float,
                                 reason: str):
        """Log complexity adjustment to score"""
        entry = self._create_log_entry(
            ScoringEventType.COMPLEXITY_ADJUSTMENT_APPLIED,
            pillar=pillar,
            operation="score_calculation",
            level="INFO",
            message=f"Applied complexity adjustment to {pillar} score",
            service_count=service_count,
            adjustment=adjustment,
            adjustment_points=f"{adjustment:+.2f}",
            reason=reason
        )
        self._log_entry(entry)
    
    def log_pillar_score_calculated(self,
                                   pillar: str,
                                   final_score: float,
                                   baseline_score: float,
                                   capability_contributions: Dict[str, float],
                                   complexity_adjustment: float,
                                   confidence_level: float,
                                   evidence: List[str],
                                   missing_capabilities: List[str]):
        """Log final pillar score with complete breakdown"""
        total_capability_points = sum(capability_contributions.values())
        
        entry = self._create_log_entry(
            ScoringEventType.PILLAR_SCORE_CALCULATED,
            pillar=pillar,
            operation="score_calculation",
            level="INFO",
            message=f"Calculated final score for {pillar} pillar: {final_score:.1f}%",
            final_score=final_score,
            baseline_score=baseline_score,
            capability_contributions=capability_contributions,
            total_capability_points=total_capability_points,
            complexity_adjustment=complexity_adjustment,
            confidence_level=confidence_level,
            confidence_percent=f"{confidence_level * 100:.1f}%",
            evidence_count=len(evidence),
            evidence=evidence,
            missing_capabilities_count=len(missing_capabilities),
            missing_capabilities=missing_capabilities,
            score_formula=f"{baseline_score} + {total_capability_points:.2f} + {complexity_adjustment:.2f} = {final_score:.2f}"
        )
        self._log_entry(entry)
    
    def log_score_calculation_complete(self,
                                      pillar: str,
                                      final_score: float):
        """Log completion of score calculation"""
        operation_key = f"score_calculation_{pillar}"
        duration_ms = None
        if operation_key in self.operation_start_times:
            duration_ms = (time.time() - self.operation_start_times[operation_key]) * 1000
            del self.operation_start_times[operation_key]
        
        entry = self._create_log_entry(
            ScoringEventType.SCORE_CALCULATION_COMPLETE,
            pillar=pillar,
            operation="score_calculation",
            level="INFO",
            message=f"Completed score calculation for {pillar} pillar: {final_score:.1f}%",
            final_score=final_score,
            duration_ms=duration_ms
        )
        entry.duration_ms = duration_ms
        self._log_entry(entry)
    
    # Pattern Adjustment Logging
    
    def log_pattern_adjustment_start(self,
                                    patterns: List[str],
                                    correlation_id: str):
        """Log start of pattern adjustment"""
        self.set_correlation_id(correlation_id)
        self.operation_start_times["pattern_adjustment"] = time.time()
        
        entry = self._create_log_entry(
            ScoringEventType.PATTERN_ADJUSTMENT_START,
            pillar=None,
            operation="pattern_adjustment",
            level="INFO",
            message=f"Starting pattern adjustments for {len(patterns)} detected patterns",
            pattern_count=len(patterns),
            patterns=patterns
        )
        self._log_entry(entry)
    
    def log_pattern_detected(self,
                           pattern_type: str,
                           confidence: float,
                           key_services: List[str],
                           expected_capabilities: Dict[str, List[str]]):
        """Log detected architecture pattern"""
        entry = self._create_log_entry(
            ScoringEventType.PATTERN_DETECTED,
            pillar=None,
            operation="pattern_adjustment",
            level="INFO",
            message=f"Detected {pattern_type} architecture pattern",
            pattern_type=pattern_type,
            confidence=confidence,
            confidence_percent=f"{confidence * 100:.1f}%",
            key_services=key_services,
            key_services_count=len(key_services),
            expected_capabilities=expected_capabilities
        )
        self._log_entry(entry)
    
    def log_pattern_adjustment_applied(self,
                                      pillar: str,
                                      pattern_type: str,
                                      original_score: float,
                                      adjusted_score: float,
                                      adjustment_reason: str,
                                      capabilities_emphasized: List[str],
                                      capabilities_deemphasized: List[str]):
        """Log pattern-specific score adjustment"""
        adjustment_delta = adjusted_score - original_score
        
        entry = self._create_log_entry(
            ScoringEventType.PATTERN_ADJUSTMENT_APPLIED,
            pillar=pillar,
            operation="pattern_adjustment",
            level="INFO",
            message=f"Applied {pattern_type} pattern adjustment to {pillar} pillar",
            pattern_type=pattern_type,
            original_score=original_score,
            adjusted_score=adjusted_score,
            adjustment_delta=adjustment_delta,
            adjustment_points=f"{adjustment_delta:+.2f}",
            adjustment_reason=adjustment_reason,
            capabilities_emphasized=capabilities_emphasized,
            capabilities_deemphasized=capabilities_deemphasized
        )
        self._log_entry(entry)
    
    def log_pattern_adjustment_complete(self,
                                       adjusted_pillars: List[str],
                                       total_adjustments: int):
        """Log completion of pattern adjustments"""
        duration_ms = None
        if "pattern_adjustment" in self.operation_start_times:
            duration_ms = (time.time() - self.operation_start_times["pattern_adjustment"]) * 1000
            del self.operation_start_times["pattern_adjustment"]
        
        entry = self._create_log_entry(
            ScoringEventType.PATTERN_ADJUSTMENT_COMPLETE,
            pillar=None,
            operation="pattern_adjustment",
            level="INFO",
            message=f"Completed pattern adjustments for {len(adjusted_pillars)} pillars",
            adjusted_pillars=adjusted_pillars,
            total_adjustments=total_adjustments,
            duration_ms=duration_ms
        )
        entry.duration_ms = duration_ms
        self._log_entry(entry)
    
    # Recommendation Generation Logging
    
    def log_recommendation_generation_start(self,
                                           pillar_scores: Dict[str, float],
                                           correlation_id: str):
        """Log start of recommendation generation"""
        self.set_correlation_id(correlation_id)
        self.operation_start_times["recommendation_generation"] = time.time()
        
        entry = self._create_log_entry(
            ScoringEventType.RECOMMENDATION_GENERATION_START,
            pillar=None,
            operation="recommendation_generation",
            level="INFO",
            message=f"Starting recommendation generation for {len(pillar_scores)} pillars",
            pillar_count=len(pillar_scores),
            pillar_scores=pillar_scores
        )
        self._log_entry(entry)
    
    def log_capability_gap_identified(self,
                                     pillar: str,
                                     capability_name: str,
                                     current_coverage: float,
                                     target_coverage: float,
                                     impact: str,
                                     affected_services: List[str]):
        """Log identified capability gap"""
        gap_size = target_coverage - current_coverage
        
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_GAP_IDENTIFIED,
            pillar=pillar,
            operation="recommendation_generation",
            level="INFO",
            message=f"Identified {capability_name} gap in {pillar} pillar",
            capability_name=capability_name,
            current_coverage=current_coverage,
            current_coverage_percent=f"{current_coverage * 100:.1f}%",
            target_coverage=target_coverage,
            target_coverage_percent=f"{target_coverage * 100:.1f}%",
            gap_size=gap_size,
            gap_percent=f"{gap_size * 100:.1f}%",
            impact=impact,
            affected_services=affected_services,
            affected_services_count=len(affected_services)
        )
        self._log_entry(entry)
    
    def log_recommendation_generated(self,
                                    recommendation_id: str,
                                    pillar: str,
                                    title: str,
                                    priority: str,
                                    capability_addressed: str,
                                    affected_services: List[str],
                                    implementation_effort: str,
                                    estimated_score_improvement: float):
        """Log generated recommendation"""
        entry = self._create_log_entry(
            ScoringEventType.RECOMMENDATION_GENERATED,
            pillar=pillar,
            operation="recommendation_generation",
            level="INFO",
            message=f"Generated {priority} priority recommendation for {pillar} pillar",
            recommendation_id=recommendation_id,
            title=title,
            priority=priority,
            capability_addressed=capability_addressed,
            affected_services=affected_services,
            affected_services_count=len(affected_services),
            implementation_effort=implementation_effort,
            estimated_score_improvement=estimated_score_improvement,
            estimated_improvement_points=f"+{estimated_score_improvement:.1f}"
        )
        self._log_entry(entry)
    
    def log_recommendation_prioritized(self,
                                      recommendation_id: str,
                                      priority: str,
                                      priority_score: float,
                                      priority_factors: Dict[str, Any]):
        """Log recommendation prioritization"""
        entry = self._create_log_entry(
            ScoringEventType.RECOMMENDATION_PRIORITIZED,
            pillar=None,
            operation="recommendation_generation",
            level="DEBUG",
            message=f"Prioritized recommendation as {priority}",
            recommendation_id=recommendation_id,
            priority=priority,
            priority_score=priority_score,
            priority_factors=priority_factors
        )
        self._log_entry(entry)
    
    def log_recommendation_generation_complete(self,
                                              recommendations_generated: int,
                                              by_priority: Dict[str, int],
                                              by_pillar: Dict[str, int]):
        """Log completion of recommendation generation"""
        duration_ms = None
        if "recommendation_generation" in self.operation_start_times:
            duration_ms = (time.time() - self.operation_start_times["recommendation_generation"]) * 1000
            del self.operation_start_times["recommendation_generation"]
        
        entry = self._create_log_entry(
            ScoringEventType.RECOMMENDATION_GENERATION_COMPLETE,
            pillar=None,
            operation="recommendation_generation",
            level="INFO",
            message=f"Completed recommendation generation: {recommendations_generated} recommendations",
            recommendations_generated=recommendations_generated,
            by_priority=by_priority,
            by_pillar=by_pillar,
            duration_ms=duration_ms
        )
        entry.duration_ms = duration_ms
        self._log_entry(entry)
    
    # General Logging Methods
    
    def log_error(self,
                 operation: str,
                 error_message: str,
                 error_type: str,
                 pillar: Optional[str] = None,
                 **context):
        """Log error with context"""
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_DETECTION_START,  # Reuse enum for error
            pillar=pillar,
            operation=operation,
            level="ERROR",
            message=f"Error in {operation}: {error_message}",
            error_type=error_type,
            error_message=error_message,
            **context
        )
        self._log_entry(entry)
    
    def log_warning(self,
                   operation: str,
                   warning_message: str,
                   pillar: Optional[str] = None,
                   **context):
        """Log warning with context"""
        entry = self._create_log_entry(
            ScoringEventType.CAPABILITY_DETECTION_START,  # Reuse enum for warning
            pillar=pillar,
            operation=operation,
            level="WARNING",
            message=warning_message,
            **context
        )
        self._log_entry(entry)


# Global scoring logger instance
scoring_logger = ScoringLogger()
