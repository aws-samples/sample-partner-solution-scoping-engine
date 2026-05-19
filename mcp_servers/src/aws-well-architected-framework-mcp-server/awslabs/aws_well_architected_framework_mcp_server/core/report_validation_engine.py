"""
Report Validation Engine for WAFR Assessment Reports

This module provides validation capabilities to ensure report consistency,
accuracy, and completeness. It implements critical validation checks while
maintaining a minimal, focused approach.

Validation Focus (Option 2 - Minimal):
- Score-recommendation consistency ✅
- Required sections present ✅
- Basic validation framework ✅

Skipped (nice-to-have):
- Percentile math validation ❌
- Critical issues count ❌
- Duplicate content detection ❌
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }
    
    def add_error(self, message: str):
        """Add an error and mark as invalid"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning (doesn't affect validity)"""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion for improvement"""
        self.suggestions.append(message)


class ReportValidationEngine:
    """
    Validates WAFR assessment reports for consistency and completeness.
    
    This engine implements a minimal validation approach focusing on:
    1. Score-recommendation consistency
    2. Required sections presence
    3. Basic structural validation
    
    Usage:
        validator = ReportValidationEngine()
        result = validator.validate_report(assessment_results)
        if not result.is_valid:
            logger.error(f"Validation failed: {result.errors}")
    """
    
    # Required sections that must be present in every report
    REQUIRED_SECTIONS = [
        "Executive Summary",
        "Architecture Overview",
        "Pillar Assessments",
        "Risk Analysis",
        "Recommendations",
        "Implementation Roadmap",
        "Methodology",
        "Assumptions",
        "Glossary"
    ]
    
    # Score thresholds for recommendation validation
    LOW_SCORE_THRESHOLD = 70.0  # Scores below this should have recommendations
    HIGH_SCORE_THRESHOLD = 85.0  # Scores above this may have fewer recommendations
    
    def __init__(self):
        """Initialize the validation engine"""
        logger.info("ReportValidationEngine initialized")
    
    def validate_report(self, assessment_results: Dict[str, Any]) -> ValidationResult:
        """
        Main validation method that runs all validation checks.
        
        Args:
            assessment_results: Complete assessment data including scores,
                              recommendations, and report content
        
        Returns:
            ValidationResult with overall validation status
        """
        logger.info("Starting report validation")
        result = ValidationResult(is_valid=True)
        
        try:
            # Run all validation checks
            self._validate_score_recommendation_consistency(assessment_results, result)
            self._validate_required_sections(assessment_results, result)
            
            # Log validation summary
            if result.is_valid:
                logger.info("Report validation passed")
            else:
                logger.warning(f"Report validation failed with {len(result.errors)} errors")
            
            if result.warnings:
                logger.info(f"Report validation completed with {len(result.warnings)} warnings")
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            result.add_error(f"Validation process failed: {str(e)}")
        
        return result
    
    def validate_score_recommendation_consistency(
        self,
        pillar_score: float,
        recommendations: List[Dict[str, Any]],
        pillar_name: str
    ) -> ValidationResult:
        """
        Validates that recommendations align with pillar score.
        
        Low scores (<70%) should have recommendations for that pillar.
        High scores (>85%) may have fewer or no recommendations.
        
        Args:
            pillar_score: Score for the pillar (0-100)
            recommendations: List of recommendations
            pillar_name: Name of the pillar being validated
        
        Returns:
            ValidationResult with consistency check results
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Count recommendations related to this pillar
            pillar_recommendations = [
                r for r in recommendations
                if pillar_name.lower() in r.get("title", "").lower() or
                   pillar_name.lower() in r.get("description", "").lower() or
                   pillar_name.lower() in r.get("pillar", "").lower()
            ]
            
            recommendation_count = len(pillar_recommendations)
            
            # Validate low scores have recommendations
            if pillar_score < self.LOW_SCORE_THRESHOLD:
                if recommendation_count == 0:
                    result.add_error(
                        f"{pillar_name} score is {pillar_score:.1f}% (below {self.LOW_SCORE_THRESHOLD}%) "
                        f"but has no recommendations"
                    )
                elif recommendation_count < 2:
                    result.add_warning(
                        f"{pillar_name} score is {pillar_score:.1f}% but only has {recommendation_count} "
                        f"recommendation(s). Consider adding more specific recommendations."
                    )
            
            # Validate high scores don't have excessive recommendations
            elif pillar_score > self.HIGH_SCORE_THRESHOLD:
                if recommendation_count > 5:
                    result.add_warning(
                        f"{pillar_name} score is {pillar_score:.1f}% (above {self.HIGH_SCORE_THRESHOLD}%) "
                        f"but has {recommendation_count} recommendations. Consider if all are necessary."
                    )
            
            # Medium scores should have some recommendations
            else:
                if recommendation_count == 0:
                    result.add_warning(
                        f"{pillar_name} score is {pillar_score:.1f}% but has no recommendations. "
                        f"Consider adding improvement suggestions."
                    )
            
        except Exception as e:
            logger.error(f"Error validating score-recommendation consistency: {e}")
            result.add_error(f"Failed to validate score-recommendation consistency: {str(e)}")
        
        return result
    
    def validate_required_sections(self, report_content: Dict[str, Any]) -> ValidationResult:
        """
        Validates that all required sections are present and populated.
        
        Args:
            report_content: Report content dictionary or assessment results
        
        Returns:
            ValidationResult with section validation results
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Extract report content if nested in assessment results
            if "report_content" in report_content:
                content = report_content["report_content"]
            else:
                content = report_content
            
            # Check for required sections
            missing_sections = []
            empty_sections = []
            
            for section in self.REQUIRED_SECTIONS:
                # Check if section exists
                section_key = section.lower().replace(" ", "_")
                
                # Try multiple possible keys (case-insensitive matching)
                possible_keys = [
                    section_key,  # executive_summary
                    section.replace(" ", "_"),  # Executive_Summary
                    section.replace(" ", "").lower(),  # executivesummary
                    section.replace(" ", ""),  # ExecutiveSummary (PascalCase)
                    section,  # Executive Summary (original)
                    section.lower()  # executive summary
                ]
                
                found = False
                # Check all keys in content (case-insensitive)
                for content_key in content.keys():
                    # Normalize both keys for comparison
                    normalized_content_key = content_key.lower().replace(" ", "_")
                    normalized_section_key = section.lower().replace(" ", "_")
                    
                    if normalized_content_key == normalized_section_key:
                        found = True
                        # Check if section is populated
                        section_content = content[content_key]
                        if not section_content or (
                            isinstance(section_content, str) and len(section_content.strip()) == 0
                        ):
                            empty_sections.append(section)
                        break
                
                if not found:
                    missing_sections.append(section)
            
            # Report missing sections as errors
            if missing_sections:
                result.add_error(
                    f"Missing required sections: {', '.join(missing_sections)}"
                )
            
            # Report empty sections as warnings
            if empty_sections:
                result.add_warning(
                    f"Empty required sections: {', '.join(empty_sections)}"
                )
            
            # Add suggestion if all sections present
            if not missing_sections and not empty_sections:
                result.add_suggestion(
                    "All required sections are present and populated"
                )
        
        except Exception as e:
            logger.error(f"Error validating required sections: {e}")
            result.add_error(f"Failed to validate required sections: {str(e)}")
        
        return result
    
    def _validate_score_recommendation_consistency(
        self,
        assessment_results: Dict[str, Any],
        result: ValidationResult
    ):
        """Internal method to validate score-recommendation consistency for all pillars"""
        try:
            # Extract pillar assessments
            pillar_assessments = assessment_results.get("pillar_assessments", {})
            
            # Skip if pillar_assessments is not a dict (might be string in report content)
            if not isinstance(pillar_assessments, dict):
                logger.debug("pillar_assessments is not a dict, skipping score validation")
                return
            
            recommendations = assessment_results.get("recommendations", [])
            
            # Skip if recommendations is not a list (might be string in report content)
            if not isinstance(recommendations, list):
                logger.debug("recommendations is not a list, skipping score validation")
                return
            
            # Validate each pillar
            for pillar_name, pillar_data in pillar_assessments.items():
                if isinstance(pillar_data, dict) and "score" in pillar_data:
                    pillar_score = pillar_data["score"]
                    
                    # Run consistency check
                    pillar_result = self.validate_score_recommendation_consistency(
                        pillar_score,
                        recommendations,
                        pillar_name
                    )
                    
                    # Merge results
                    result.errors.extend(pillar_result.errors)
                    result.warnings.extend(pillar_result.warnings)
                    result.suggestions.extend(pillar_result.suggestions)
                    
                    if not pillar_result.is_valid:
                        result.is_valid = False
        
        except Exception as e:
            logger.error(f"Error in score-recommendation consistency validation: {e}")
            result.add_error(f"Failed to validate score-recommendation consistency: {str(e)}")
    
    def _validate_required_sections(
        self,
        assessment_results: Dict[str, Any],
        result: ValidationResult
    ):
        """Internal method to validate required sections"""
        try:
            section_result = self.validate_required_sections(assessment_results)
            
            # Merge results
            result.errors.extend(section_result.errors)
            result.warnings.extend(section_result.warnings)
            result.suggestions.extend(section_result.suggestions)
            
            if not section_result.is_valid:
                result.is_valid = False
        
        except Exception as e:
            logger.error(f"Error in required sections validation: {e}")
            result.add_error(f"Failed to validate required sections: {str(e)}")
