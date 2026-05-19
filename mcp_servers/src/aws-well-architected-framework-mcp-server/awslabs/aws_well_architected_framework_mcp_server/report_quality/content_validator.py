"""
Content Validator for WAFR Report Generation.

This module provides comprehensive validation of assessment data before report
generation to ensure data quality and prevent raw dictionary output.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """
    Represents a single validation issue.
    
    Tracks the severity, location, and details of validation problems.
    """
    severity: ValidationSeverity
    component: str  # Which component has the issue (e.g., "pillar_assessment", "recommendation")
    field: str  # Which field has the issue
    message: str
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "severity": self.severity.value,
            "component": self.component,
            "field": self.field,
            "message": self.message
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ValidationResult:
    """
    Result of content validation.
    
    Contains all validation issues categorized by severity.
    """
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_error(self, component: str, field: str, message: str, suggestion: Optional[str] = None):
        """Add an error to the validation result."""
        self.errors.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            component=component,
            field=field,
            message=message,
            suggestion=suggestion
        ))
        self.is_valid = False
    
    def add_warning(self, component: str, field: str, message: str, suggestion: Optional[str] = None):
        """Add a warning to the validation result."""
        self.warnings.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            component=component,
            field=field,
            message=message,
            suggestion=suggestion
        ))
    
    def add_info(self, component: str, field: str, message: str, suggestion: Optional[str] = None):
        """Add an info message to the validation result."""
        self.info.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            component=component,
            field=field,
            message=message,
            suggestion=suggestion
        ))
    
    def get_error_count(self) -> int:
        """Get total number of errors."""
        return len(self.errors)
    
    def get_warning_count(self) -> int:
        """Get total number of warnings."""
        return len(self.warnings)
    
    def get_all_issues(self) -> List[ValidationIssue]:
        """Get all validation issues."""
        return self.errors + self.warnings + self.info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "error_count": self.get_error_count(),
            "warning_count": self.get_warning_count(),
            "info_count": len(self.info),
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "info": [issue.to_dict() for issue in self.info],
            "missing_fields": self.missing_fields,
            "suggestions": self.suggestions
        }


class ContentValidator:
    """
    Validates WAFR assessment data before report generation.
    
    Ensures data quality, completeness, and proper structure to prevent
    raw dictionary output and ensure professional report generation.
    """
    
    def __init__(self):
        """Initialize the content validator."""
        self.required_pillars = [
            "operational_excellence",
            "security",
            "reliability",
            "performance_efficiency",
            "cost_optimization",
            "sustainability"
        ]
    
    def validate_assessment_data(self, assessment_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete assessment data structure.
        
        Args:
            assessment_data: Complete assessment results
            
        Returns:
            ValidationResult with all issues found
        """
        logger.info("🔍 Validating complete assessment data structure")
        result = ValidationResult(is_valid=True)
        
        # Validate top-level structure
        self._validate_top_level_structure(assessment_data, result)
        
        # Validate pillar assessments
        if "pillar_assessments" in assessment_data:
            self._validate_all_pillar_assessments(
                assessment_data["pillar_assessments"],
                result
            )
        else:
            result.add_error(
                "assessment_data",
                "pillar_assessments",
                "Missing pillar_assessments field",
                "Ensure all 6 pillars have been assessed"
            )
        
        # Validate metadata
        self._validate_metadata(assessment_data, result)
        
        # Validate overall scores
        self._validate_overall_scores(assessment_data, result)
        
        logger.info(
            f"✅ Validation complete: {result.get_error_count()} errors, "
            f"{result.get_warning_count()} warnings"
        )
        
        return result
    
    def validate_pillar_data(self, pillar_data: Dict[str, Any], pillar_name: str = "unknown") -> ValidationResult:
        """
        Validate individual pillar assessment data.
        
        Args:
            pillar_data: Pillar assessment data
            pillar_name: Name of the pillar being validated
            
        Returns:
            ValidationResult with issues found
        """
        logger.info(f"🔍 Validating pillar data for: {pillar_name}")
        result = ValidationResult(is_valid=True)
        
        # Validate required fields
        required_fields = ["score", "risk_level"]
        for field_name in required_fields:
            if field_name not in pillar_data:
                result.add_error(
                    f"pillar_{pillar_name}",
                    field_name,
                    f"Missing required field: {field_name}",
                    f"Ensure pillar assessment includes {field_name}"
                )
        
        # Validate score
        if "score" in pillar_data:
            score = pillar_data["score"]
            if not isinstance(score, (int, float)):
                result.add_error(
                    f"pillar_{pillar_name}",
                    "score",
                    f"Score must be numeric, got {type(score).__name__}",
                    "Ensure score is a number between 0-100"
                )
            elif score < 0 or score > 100:
                result.add_error(
                    f"pillar_{pillar_name}",
                    "score",
                    f"Score {score} is out of valid range (0-100)",
                    "Scores should be between 0 and 100"
                )
        
        # Validate capabilities
        self._validate_capabilities(pillar_data, pillar_name, result)
        
        # Validate recommendations
        if "recommendations" in pillar_data:
            for idx, rec in enumerate(pillar_data["recommendations"]):
                self.validate_recommendation(rec, f"{pillar_name}_rec_{idx}", result)
        
        # Validate questions assessed
        if "questions_assessed" in pillar_data:
            if not isinstance(pillar_data["questions_assessed"], int):
                result.add_warning(
                    f"pillar_{pillar_name}",
                    "questions_assessed",
                    "questions_assessed should be an integer",
                    "Convert to integer count"
                )
        else:
            result.add_warning(
                f"pillar_{pillar_name}",
                "questions_assessed",
                "Missing questions_assessed count",
                "Add questions_assessed field to track assessment thoroughness"
            )
        
        return result
    
    def validate_recommendation(
        self,
        recommendation: Dict[str, Any],
        rec_id: str = "unknown",
        result: Optional[ValidationResult] = None
    ) -> ValidationResult:
        """
        Validate recommendation structure and content.
        
        Args:
            recommendation: Recommendation data
            rec_id: Identifier for the recommendation
            result: Optional existing ValidationResult to append to
            
        Returns:
            ValidationResult with issues found
        """
        if result is None:
            result = ValidationResult(is_valid=True)
        
        # Validate required fields
        required_fields = ["title", "priority", "description"]
        for field_name in required_fields:
            if field_name not in recommendation:
                result.add_error(
                    f"recommendation_{rec_id}",
                    field_name,
                    f"Missing required field: {field_name}",
                    f"All recommendations must have {field_name}"
                )
        
        # Validate title is not a dictionary
        if "title" in recommendation:
            if isinstance(recommendation["title"], dict):
                result.add_error(
                    f"recommendation_{rec_id}",
                    "title",
                    "Title is a dictionary instead of string",
                    "Convert dictionary to formatted string"
                )
        
        # Validate description is not a dictionary
        if "description" in recommendation:
            if isinstance(recommendation["description"], dict):
                result.add_error(
                    f"recommendation_{rec_id}",
                    "description",
                    "Description is a dictionary instead of string",
                    "Convert dictionary to formatted text"
                )
        
        # Validate priority
        if "priority" in recommendation:
            valid_priorities = ["critical", "high", "medium", "low"]
            priority = recommendation["priority"]
            if isinstance(priority, str):
                if priority.lower() not in valid_priorities:
                    result.add_warning(
                        f"recommendation_{rec_id}",
                        "priority",
                        f"Invalid priority value: {priority}",
                        f"Use one of: {', '.join(valid_priorities)}"
                    )
            else:
                result.add_error(
                    f"recommendation_{rec_id}",
                    "priority",
                    "Priority must be a string",
                    "Convert to string priority level"
                )
        
        # Validate affected services
        if "affected_services" in recommendation:
            services = recommendation["affected_services"]
            if not isinstance(services, list):
                result.add_error(
                    f"recommendation_{rec_id}",
                    "affected_services",
                    "affected_services must be a list",
                    "Convert to list of service names"
                )
            elif len(services) == 0:
                result.add_warning(
                    f"recommendation_{rec_id}",
                    "affected_services",
                    "affected_services list is empty",
                    "Specify which services need this improvement"
                )
        else:
            result.add_warning(
                f"recommendation_{rec_id}",
                "affected_services",
                "Missing affected_services field",
                "Add list of services that need this improvement"
            )
        
        # Validate implementation guidance
        if "implementation_guidance" not in recommendation:
            result.add_warning(
                f"recommendation_{rec_id}",
                "implementation_guidance",
                "Missing implementation_guidance",
                "Add step-by-step implementation instructions"
            )
        
        # Validate AWS documentation links
        if "aws_documentation_links" not in recommendation:
            result.add_warning(
                f"recommendation_{rec_id}",
                "aws_documentation_links",
                "Missing AWS documentation links",
                "Add relevant AWS documentation references"
            )
        elif len(recommendation["aws_documentation_links"]) == 0:
            result.add_warning(
                f"recommendation_{rec_id}",
                "aws_documentation_links",
                "No AWS documentation links provided",
                "Add at least one relevant documentation link"
            )
        
        return result
    
    def validate_metadata(self, assessment_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate assessment metadata completeness.
        
        Args:
            assessment_data: Complete assessment data
            
        Returns:
            ValidationResult with issues found
        """
        result = ValidationResult(is_valid=True)
        self._validate_metadata(assessment_data, result)
        return result
    
    def _validate_top_level_structure(self, data: Dict[str, Any], result: ValidationResult):
        """Validate top-level assessment data structure."""
        required_top_level = [
            "assessment_id",
            "chat_id",
            "timestamp",
            "pillar_assessments",
            "overall_score",
            "overall_risk_level"
        ]
        
        for field_name in required_top_level:
            if field_name not in data:
                result.add_error(
                    "assessment_data",
                    field_name,
                    f"Missing required top-level field: {field_name}",
                    f"Ensure assessment includes {field_name}"
                )
    
    def _validate_all_pillar_assessments(
        self,
        pillar_assessments: Dict[str, Any],
        result: ValidationResult
    ):
        """Validate all pillar assessments."""
        # Check all required pillars are present
        for pillar in self.required_pillars:
            if pillar not in pillar_assessments:
                result.add_error(
                    "pillar_assessments",
                    pillar,
                    f"Missing pillar assessment: {pillar}",
                    f"Ensure {pillar} has been assessed"
                )
        
        # Validate each pillar
        for pillar_name, pillar_data in pillar_assessments.items():
            pillar_result = self.validate_pillar_data(pillar_data, pillar_name)
            
            # Merge results
            result.errors.extend(pillar_result.errors)
            result.warnings.extend(pillar_result.warnings)
            result.info.extend(pillar_result.info)
            
            if not pillar_result.is_valid:
                result.is_valid = False
    
    def _validate_capabilities(
        self,
        pillar_data: Dict[str, Any],
        pillar_name: str,
        result: ValidationResult
    ):
        """Validate capability data in pillar assessment."""
        # Check for detected capabilities
        if "detected_capabilities" not in pillar_data:
            result.add_warning(
                f"pillar_{pillar_name}",
                "detected_capabilities",
                "Missing detected_capabilities field",
                "Add list of detected capabilities with evidence"
            )
        elif not isinstance(pillar_data["detected_capabilities"], list):
            result.add_error(
                f"pillar_{pillar_name}",
                "detected_capabilities",
                "detected_capabilities must be a list",
                "Convert to list of capability objects"
            )
        
        # Check for missing capabilities
        if "missing_capabilities" not in pillar_data:
            result.add_info(
                f"pillar_{pillar_name}",
                "missing_capabilities",
                "Missing missing_capabilities field",
                "Add list of expected but missing capabilities"
            )
        elif not isinstance(pillar_data["missing_capabilities"], list):
            result.add_error(
                f"pillar_{pillar_name}",
                "missing_capabilities",
                "missing_capabilities must be a list",
                "Convert to list of missing capability objects"
            )
    
    def _validate_metadata(self, data: Dict[str, Any], result: ValidationResult):
        """Validate assessment metadata."""
        # Check for assessment date
        if "timestamp" not in data and "assessment_date" not in data:
            result.add_warning(
                "metadata",
                "timestamp",
                "Missing timestamp or assessment_date",
                "Add assessment date for tracking"
            )
        
        # Check for services analyzed
        if "document_analysis" in data:
            doc_analysis = data["document_analysis"]
            if "identified_services" not in doc_analysis:
                result.add_info(
                    "metadata",
                    "identified_services",
                    "Missing identified_services in document_analysis",
                    "Add list of AWS services detected"
                )
        
        # Check for patterns detected
        if "document_analysis" in data:
            doc_analysis = data["document_analysis"]
            if "architectural_patterns" not in doc_analysis:
                result.add_info(
                    "metadata",
                    "architectural_patterns",
                    "Missing architectural_patterns in document_analysis",
                    "Add list of detected architecture patterns"
                )
    
    def _validate_overall_scores(self, data: Dict[str, Any], result: ValidationResult):
        """Validate overall score calculations."""
        if "overall_score" in data:
            score = data["overall_score"]
            if not isinstance(score, (int, float)):
                result.add_error(
                    "overall_scores",
                    "overall_score",
                    f"Overall score must be numeric, got {type(score).__name__}",
                    "Calculate numeric overall score"
                )
            elif score < 0 or score > 100:
                result.add_error(
                    "overall_scores",
                    "overall_score",
                    f"Overall score {score} is out of valid range (0-100)",
                    "Ensure score is between 0 and 100"
                )
        
        # Validate risk level
        if "overall_risk_level" in data:
            risk_level = data["overall_risk_level"]
            valid_risk_levels = ["critical", "high", "medium", "low"]
            if isinstance(risk_level, str):
                if risk_level.lower() not in valid_risk_levels:
                    result.add_warning(
                        "overall_scores",
                        "overall_risk_level",
                        f"Invalid risk level: {risk_level}",
                        f"Use one of: {', '.join(valid_risk_levels)}"
                    )
            else:
                result.add_error(
                    "overall_scores",
                    "overall_risk_level",
                    "Risk level must be a string",
                    "Convert to string risk level"
                )
    
    def log_validation_results(self, result: ValidationResult, component: str = "assessment"):
        """
        Log validation results with appropriate severity levels.
        
        Args:
            result: ValidationResult to log
            component: Component being validated
        """
        if result.is_valid:
            logger.info(f"✅ {component} validation passed with {result.get_warning_count()} warnings")
        else:
            logger.error(f"❌ {component} validation failed with {result.get_error_count()} errors")
        
        # Log errors
        for error in result.errors:
            logger.error(
                f"  ERROR [{error.component}.{error.field}]: {error.message}"
            )
            if error.suggestion:
                logger.error(f"    Suggestion: {error.suggestion}")
        
        # Log warnings
        for warning in result.warnings:
            logger.warning(
                f"  WARNING [{warning.component}.{warning.field}]: {warning.message}"
            )
            if warning.suggestion:
                logger.warning(f"    Suggestion: {warning.suggestion}")
        
        # Log info messages
        for info in result.info:
            logger.info(
                f"  INFO [{info.component}.{info.field}]: {info.message}"
            )
