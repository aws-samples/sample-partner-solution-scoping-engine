"""
Enhanced Scoring Error Handler

Provides comprehensive error handling and graceful degradation for the enhanced
capability-based scoring system.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .logger import WAFRLogger


class EnhancedScoringErrorHandler:
    """
    Error handler for enhanced scoring system with graceful degradation.
    
    Ensures that scoring failures don't break the assessment workflow by
    providing fallback mechanisms and comprehensive error logging.
    """
    
    def __init__(self):
        self.logger = WAFRLogger(__name__)
        self.error_counts = {}
        self.fallback_scores = {
            'security': 35,
            'reliability': 40,
            'performance': 40,
            'cost_optimization': 35,
            'operational_excellence': 40,
            'sustainability': 30
        }
    
    def handle_capability_detection_failure(
        self,
        pillar: str,
        error: Exception,
        architecture_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle capability detection failures with graceful degradation.
        
        Args:
            pillar: The pillar being assessed
            error: The exception that occurred
            architecture_data: Architecture data for context
            
        Returns:
            Fallback assessment result with baseline score
        """
        self.logger.error(
            f"❌ Capability detection failed for {pillar}: {error}",
            extra={
                'pillar': pillar,
                'error_type': type(error).__name__,
                'services_count': len(architecture_data.get('identified_services', [])),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Track error for monitoring
        error_key = f"{pillar}_capability_detection"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Return fallback result with baseline score
        return {
            'success': True,
            'pillar': pillar,
            'score': self.fallback_scores.get(pillar, 40),
            'risk_level': 'medium',
            'fallback_used': True,
            'fallback_reason': 'capability_detection_failure',
            'error_message': str(error),
            'confidence_level': 0.3,  # Low confidence
            'recommendations': [
                {
                    'title': 'Limited Analysis Available',
                    'description': f'Capability detection encountered issues for {pillar}. Recommendations are based on general best practices.',
                    'priority': 'medium',
                    'implementation_effort': 'varies'
                }
            ],
            'data_sources': {
                'enhanced_scoring_enabled': False,
                'fallback_mode': True,
                'error_type': type(error).__name__
            }
        }
    
    def handle_scoring_calculation_failure(
        self,
        pillar: str,
        error: Exception,
        capabilities: list
    ) -> Dict[str, Any]:
        """
        Handle scoring calculation failures.
        
        Args:
            pillar: The pillar being assessed
            error: The exception that occurred
            capabilities: Detected capabilities (if any)
            
        Returns:
            Fallback assessment result
        """
        self.logger.error(
            f"❌ Scoring calculation failed for {pillar}: {error}",
            extra={
                'pillar': pillar,
                'error_type': type(error).__name__,
                'capabilities_count': len(capabilities) if capabilities else 0,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Track error
        error_key = f"{pillar}_scoring_calculation"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Return fallback with slightly higher score if capabilities were detected
        base_score = self.fallback_scores.get(pillar, 40)
        adjusted_score = base_score + (len(capabilities) * 2) if capabilities else base_score
        adjusted_score = min(adjusted_score, 60)  # Cap at 60 for fallback
        
        return {
            'success': True,
            'pillar': pillar,
            'score': adjusted_score,
            'risk_level': 'medium',
            'fallback_used': True,
            'fallback_reason': 'scoring_calculation_failure',
            'error_message': str(error),
            'confidence_level': 0.4,  # Low-medium confidence
            'detected_capabilities': [c.name if hasattr(c, 'name') else str(c) for c in capabilities] if capabilities else [],
            'recommendations': [
                {
                    'title': 'Scoring Calculation Issue',
                    'description': f'Score calculation encountered issues for {pillar}. Using baseline assessment with detected capabilities.',
                    'priority': 'medium',
                    'implementation_effort': 'varies'
                }
            ],
            'data_sources': {
                'enhanced_scoring_enabled': False,
                'fallback_mode': True,
                'partial_capability_detection': bool(capabilities),
                'error_type': type(error).__name__
            }
        }
    
    def handle_pattern_adjustment_failure(
        self,
        pillar: str,
        error: Exception,
        base_score: float
    ) -> float:
        """
        Handle pattern adjustment failures.
        
        Args:
            pillar: The pillar being assessed
            error: The exception that occurred
            base_score: The base score before pattern adjustments
            
        Returns:
            Base score without pattern adjustments
        """
        self.logger.warning(
            f"⚠️ Pattern adjustment failed for {pillar}: {error}",
            extra={
                'pillar': pillar,
                'error_type': type(error).__name__,
                'base_score': base_score,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Track error
        error_key = f"{pillar}_pattern_adjustment"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Return base score without adjustments
        return base_score
    
    def handle_recommendation_generation_failure(
        self,
        pillar: str,
        error: Exception
    ) -> list:
        """
        Handle recommendation generation failures.
        
        Args:
            pillar: The pillar being assessed
            error: The exception that occurred
            
        Returns:
            Generic fallback recommendations
        """
        self.logger.warning(
            f"⚠️ Recommendation generation failed for {pillar}: {error}",
            extra={
                'pillar': pillar,
                'error_type': type(error).__name__,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Track error
        error_key = f"{pillar}_recommendation_generation"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Return generic recommendations
        return [
            {
                'title': f'Review {pillar.replace("_", " ").title()} Best Practices',
                'description': f'Consult AWS Well-Architected Framework documentation for {pillar} best practices.',
                'priority': 'medium',
                'implementation_effort': 'varies',
                'fallback': True
            }
        ]
    
    def add_low_confidence_warning(
        self,
        assessment_result: Dict[str, Any],
        confidence_level: float
    ) -> Dict[str, Any]:
        """
        Add low-confidence warnings to assessment results.
        
        Args:
            assessment_result: The assessment result to enhance
            confidence_level: The confidence level (0.0-1.0)
            
        Returns:
            Enhanced assessment result with warnings
        """
        if confidence_level < 0.5:
            warning_level = 'high'
            warning_message = (
                'This assessment has low confidence due to limited data or processing issues. '
                'Results should be validated and may not fully reflect your architecture quality.'
            )
        elif confidence_level < 0.7:
            warning_level = 'medium'
            warning_message = (
                'This assessment has medium confidence. Some aspects may require additional validation.'
            )
        else:
            # No warning needed for high confidence
            return assessment_result
        
        # Add warning to result
        assessment_result['confidence_warning'] = {
            'level': warning_level,
            'message': warning_message,
            'confidence_score': confidence_level,
            'recommendation': 'Consider providing additional architecture documentation or performing a live AWS environment scan for more accurate results.'
        }
        
        return assessment_result
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics for monitoring.
        
        Returns:
            Dictionary with error counts and statistics
        """
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_counts_by_type': self.error_counts.copy(),
            'most_common_error': max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def log_scoring_decision(
        self,
        pillar: str,
        score: float,
        capabilities_detected: int,
        confidence: float,
        fallback_used: bool
    ):
        """
        Log scoring decisions for audit and debugging.
        
        Args:
            pillar: The pillar assessed
            score: The final score
            capabilities_detected: Number of capabilities detected
            confidence: Confidence level
            fallback_used: Whether fallback was used
        """
        self.logger.info(
            f"📊 Scoring decision for {pillar}",
            extra={
                'pillar': pillar,
                'score': score,
                'capabilities_detected': capabilities_detected,
                'confidence': confidence,
                'fallback_used': fallback_used,
                'timestamp': datetime.now().isoformat()
            }
        )
