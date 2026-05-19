"""Graceful Degradation and Error Handling for WAFR Report Generation.

This module provides comprehensive error handling with fallback mechanisms
to ensure partial reports are generated even when data is incomplete or invalid.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    component: str
    error_type: str
    message: str
    severity: str  # "critical", "error", "warning"
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """Result of a fallback operation."""
    success: bool
    data: Any
    fallback_used: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class GracefulDegradationHandler:
    """Handles graceful degradation for report generation with comprehensive fallbacks."""
    
    def __init__(self):
        """Initialize the graceful degradation handler."""
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        logger.info("✅ Graceful degradation handler initialized")
    
    def handle_missing_assessment_data(
        self,
        assessment_data: Optional[Dict[str, Any]]
    ) -> FallbackResult:
        """
        Handle missing or incomplete assessment data with fallback.
        
        Args:
            assessment_data: The assessment data that may be missing or incomplete
            
        Returns:
            FallbackResult with fallback data if needed
        """
        try:
            if not assessment_data:
                logger.warning("⚠️ Assessment data is completely missing, using fallback")
                self.warnings.append("Assessment data was missing - using placeholder data")
                
                return FallbackResult(
                    success=True,
                    data=self._get_fallback_assessment_data(),
                    fallback_used=True,
                    warnings=["Complete assessment data missing - report contains placeholder information"]
                )
            
            # Check for required fields
            required_fields = ["pillar_assessments", "overall_score", "chat_id"]
            missing_fields = [field for field in required_fields if field not in assessment_data]
            
            if missing_fields:
                logger.warning(f"⚠️ Missing required fields: {missing_fields}, applying fallbacks")
                
                # Apply field-level fallbacks
                fallback_data = dict(assessment_data)
                for field in missing_fields:
                    fallback_data[field] = self._get_field_fallback(field)
                    self.warnings.append(f"Field '{field}' was missing - using fallback value")
                
                return FallbackResult(
                    success=True,
                    data=fallback_data,
                    fallback_used=True,
                    warnings=[f"Missing fields: {', '.join(missing_fields)} - using fallback values"]
                )
            
            # Data is complete
            return FallbackResult(
                success=True,
                data=assessment_data,
                fallback_used=False
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling missing assessment data: {e}")
            error = ValidationError(
                component="assessment_data",
                error_type="processing_error",
                message=str(e),
                severity="error"
            )
            self.errors.append(error)
            
            return FallbackResult(
                success=True,
                data=self._get_fallback_assessment_data(),
                fallback_used=True,
                errors=[error],
                warnings=["Error processing assessment data - using complete fallback"]
            )
    
    def handle_invalid_data_structures(
        self,
        data: Any,
        expected_type: str,
        component: str
    ) -> FallbackResult:
        """
        Handle invalid data structures with type conversion and fallback.
        
        Args:
            data: The data to validate
            expected_type: Expected type ("dict", "list", "str", "float", "int")
            component: Component name for error tracking
            
        Returns:
            FallbackResult with validated or fallback data
        """
        try:
            # Type validation and conversion
            if expected_type == "dict":
                if isinstance(data, dict):
                    return FallbackResult(success=True, data=data, fallback_used=False)
                elif isinstance(data, str):
                    # Try to parse as dict representation
                    logger.warning(f"⚠️ {component}: Converting string to dict")
                    return FallbackResult(
                        success=True,
                        data={"value": data},
                        fallback_used=True,
                        warnings=[f"{component}: Converted string to dict structure"]
                    )
                else:
                    logger.warning(f"⚠️ {component}: Invalid dict, using fallback")
                    return FallbackResult(
                        success=True,
                        data={},
                        fallback_used=True,
                        warnings=[f"{component}: Invalid data type, using empty dict"]
                    )
            
            elif expected_type == "list":
                if isinstance(data, list):
                    return FallbackResult(success=True, data=data, fallback_used=False)
                elif isinstance(data, (str, dict)):
                    logger.warning(f"⚠️ {component}: Converting to list")
                    return FallbackResult(
                        success=True,
                        data=[data],
                        fallback_used=True,
                        warnings=[f"{component}: Converted single item to list"]
                    )
                else:
                    return FallbackResult(
                        success=True,
                        data=[],
                        fallback_used=True,
                        warnings=[f"{component}: Invalid data type, using empty list"]
                    )
            
            elif expected_type == "str":
                if isinstance(data, str):
                    return FallbackResult(success=True, data=data, fallback_used=False)
                elif isinstance(data, (dict, list)):
                    # Convert dict/list to readable string (not repr)
                    logger.warning(f"⚠️ {component}: Converting complex type to string")
                    readable_str = self._convert_to_readable_string(data)
                    return FallbackResult(
                        success=True,
                        data=readable_str,
                        fallback_used=True,
                        warnings=[f"{component}: Converted complex type to readable string"]
                    )
                else:
                    return FallbackResult(
                        success=True,
                        data=str(data),
                        fallback_used=True,
                        warnings=[f"{component}: Converted to string"]
                    )
            
            elif expected_type in ["float", "int"]:
                try:
                    if expected_type == "float":
                        converted = float(data)
                    else:
                        converted = int(data)
                    return FallbackResult(success=True, data=converted, fallback_used=False)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ {component}: Cannot convert to {expected_type}, using default")
                    default_value = 0.0 if expected_type == "float" else 0
                    return FallbackResult(
                        success=True,
                        data=default_value,
                        fallback_used=True,
                        warnings=[f"{component}: Invalid numeric value, using {default_value}"]
                    )
            
            # Unknown type
            return FallbackResult(
                success=True,
                data=data,
                fallback_used=False,
                warnings=[f"{component}: Unknown expected type '{expected_type}', returning as-is"]
            )
            
        except Exception as e:
            logger.error(f"❌ Error validating data structure for {component}: {e}")
            error = ValidationError(
                component=component,
                error_type="validation_error",
                message=str(e),
                severity="error"
            )
            self.errors.append(error)
            
            # Return safe fallback based on type
            fallback_data = self._get_type_fallback(expected_type)
            return FallbackResult(
                success=True,
                data=fallback_data,
                fallback_used=True,
                errors=[error],
                warnings=[f"{component}: Validation error, using fallback"]
            )
    
    def handle_missing_metadata(
        self,
        metadata: Optional[Dict[str, Any]]
    ) -> FallbackResult:
        """
        Handle missing metadata with default values.
        
        Args:
            metadata: The metadata that may be missing or incomplete
            
        Returns:
            FallbackResult with complete metadata
        """
        try:
            if not metadata:
                logger.warning("⚠️ Metadata is completely missing, using defaults")
                return FallbackResult(
                    success=True,
                    data=self._get_default_metadata(),
                    fallback_used=True,
                    warnings=["Metadata was missing - using default values"]
                )
            
            # Ensure required metadata fields
            required_metadata = {
                "assessment_date": datetime.now().isoformat(),
                "services_analyzed": 0,
                "patterns_detected": [],
                "questions_assessed": 0,
                "confidence_level": 0.5
            }
            
            complete_metadata = dict(metadata)
            missing_fields = []
            
            for field, default_value in required_metadata.items():
                if field not in complete_metadata or complete_metadata[field] is None:
                    complete_metadata[field] = default_value
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"⚠️ Missing metadata fields: {missing_fields}, using defaults")
                return FallbackResult(
                    success=True,
                    data=complete_metadata,
                    fallback_used=True,
                    warnings=[f"Missing metadata fields: {', '.join(missing_fields)} - using defaults"]
                )
            
            return FallbackResult(
                success=True,
                data=complete_metadata,
                fallback_used=False
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling missing metadata: {e}")
            return FallbackResult(
                success=True,
                data=self._get_default_metadata(),
                fallback_used=True,
                warnings=["Error processing metadata - using complete defaults"]
            )
    
    def handle_documentation_link_failure(
        self,
        pillar: str,
        service: Optional[str] = None
    ) -> FallbackResult:
        """
        Handle documentation link generation failures with static fallbacks.
        
        Args:
            pillar: The WAFR pillar name
            service: Optional AWS service name
            
        Returns:
            FallbackResult with fallback documentation links
        """
        try:
            logger.warning(f"⚠️ Documentation link generation failed for {pillar}, using static links")
            
            fallback_links = self._get_static_documentation_links(pillar, service)
            
            return FallbackResult(
                success=True,
                data=fallback_links,
                fallback_used=True,
                warnings=[f"Using static documentation links for {pillar}"]
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating fallback documentation links: {e}")
            return FallbackResult(
                success=True,
                data=[{
                    "title": "AWS Well-Architected Framework",
                    "url": "https://aws.amazon.com/architecture/well-architected/",
                    "description": "Official AWS Well-Architected Framework documentation"
                }],
                fallback_used=True,
                warnings=["Using generic AWS documentation link"]
            )
    
    def ensure_partial_report_generation(
        self,
        assessment_data: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Ensure a partial report can be generated even with errors.
        
        Args:
            assessment_data: The assessment data (may be incomplete)
            error: The error that occurred
            
        Returns:
            Modified assessment data that can generate a partial report
        """
        try:
            logger.warning(f"⚠️ Ensuring partial report generation after error: {error}")
            
            # Start with fallback data
            partial_data = self._get_fallback_assessment_data()
            
            # Merge any valid data from the original assessment
            if assessment_data:
                for key, value in assessment_data.items():
                    if value is not None and key in partial_data:
                        try:
                            # Validate the value before using it
                            validated = self.handle_invalid_data_structures(
                                value,
                                type(partial_data[key]).__name__,
                                key
                            )
                            if validated.success:
                                partial_data[key] = validated.data
                        except Exception as merge_error:
                            logger.debug(f"Could not merge field {key}: {merge_error}")
                            # Keep fallback value
            
            # Add error explanation to the report
            partial_data["error_notice"] = {
                "message": "This is a partial report generated due to an error during assessment",
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
                "recommendation": "Please review the error and re-run the assessment for complete results"
            }
            
            return partial_data
            
        except Exception as e:
            logger.error(f"❌ Error ensuring partial report generation: {e}")
            # Return absolute minimum fallback
            return self._get_fallback_assessment_data()
    
    def add_error_explanation_to_report(
        self,
        report_data: Dict[str, Any],
        errors: List[ValidationError],
        warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Add clear error explanations to the report data.
        
        Args:
            report_data: The report data to enhance
            errors: List of validation errors
            warnings: List of warnings
            
        Returns:
            Enhanced report data with error explanations
        """
        try:
            if not errors and not warnings:
                return report_data
            
            # Add error summary section
            error_summary = {
                "has_errors": len(errors) > 0,
                "has_warnings": len(warnings) > 0,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "errors": [
                    {
                        "component": err.component,
                        "type": err.error_type,
                        "message": err.message,
                        "severity": err.severity
                    }
                    for err in errors
                ],
                "warnings": warnings,
                "user_message": self._generate_user_friendly_error_message(errors, warnings)
            }
            
            report_data["generation_status"] = error_summary
            
            return report_data
            
        except Exception as e:
            logger.error(f"❌ Error adding error explanation to report: {e}")
            return report_data
    
    def _get_fallback_assessment_data(self) -> Dict[str, Any]:
        """Get complete fallback assessment data."""
        return {
            "chat_id": "fallback-assessment",
            "overall_score": 70.0,
            "overall_risk_level": "medium",
            "pillar_assessments": {
                "operational_excellence": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                },
                "security": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                },
                "reliability": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                },
                "performance_efficiency": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                },
                "cost_optimization": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                },
                "sustainability": {
                    "score": 70.0,
                    "risk_level": "Medium",
                    "detected_capabilities": [],
                    "missing_capabilities": [],
                    "recommendations": ["Complete assessment for detailed recommendations"],
                    "questions_assessed": 0
                }
            },
            "architecture_data": {
                "identified_services": [],
                "architectural_patterns": []
            },
            "assessment_date": datetime.now().isoformat(),
            "fallback_notice": "This assessment uses fallback data due to incomplete information"
        }
    
    def _get_field_fallback(self, field: str) -> Any:
        """Get fallback value for a specific field."""
        fallbacks = {
            "chat_id": f"fallback-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "overall_score": 70.0,
            "overall_risk_level": "medium",
            "pillar_assessments": {},
            "architecture_data": {},
            "assessment_date": datetime.now().isoformat(),
            "services_analyzed": 0,
            "patterns_detected": []
        }
        return fallbacks.get(field, None)
    
    def _get_type_fallback(self, expected_type: str) -> Any:
        """Get fallback value based on expected type."""
        fallbacks = {
            "dict": {},
            "list": [],
            "str": "",
            "float": 0.0,
            "int": 0
        }
        return fallbacks.get(expected_type, None)
    
    def _get_default_metadata(self) -> Dict[str, Any]:
        """Get default metadata values."""
        return {
            "assessment_date": datetime.now().isoformat(),
            "services_analyzed": 0,
            "patterns_detected": [],
            "questions_assessed": 0,
            "confidence_level": 0.5,
            "assessment_type": "automated",
            "data_sources": ["document_analysis"]
        }
    
    def _get_static_documentation_links(
        self,
        pillar: str,
        service: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get static documentation links for a pillar."""
        base_links = {
            "operational_excellence": [
                {
                    "title": "Operational Excellence Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html",
                    "description": "AWS Well-Architected Operational Excellence Pillar"
                }
            ],
            "security": [
                {
                    "title": "Security Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
                    "description": "AWS Well-Architected Security Pillar"
                },
                {
                    "title": "IAM Best Practices",
                    "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
                    "description": "AWS IAM Best Practices Guide"
                }
            ],
            "reliability": [
                {
                    "title": "Reliability Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html",
                    "description": "AWS Well-Architected Reliability Pillar"
                }
            ],
            "performance_efficiency": [
                {
                    "title": "Performance Efficiency Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html",
                    "description": "AWS Well-Architected Performance Efficiency Pillar"
                }
            ],
            "cost_optimization": [
                {
                    "title": "Cost Optimization Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html",
                    "description": "AWS Well-Architected Cost Optimization Pillar"
                }
            ],
            "sustainability": [
                {
                    "title": "Sustainability Pillar",
                    "url": "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html",
                    "description": "AWS Well-Architected Sustainability Pillar"
                }
            ]
        }
        
        links = base_links.get(pillar, [
            {
                "title": "AWS Well-Architected Framework",
                "url": "https://aws.amazon.com/architecture/well-architected/",
                "description": "Official AWS Well-Architected Framework documentation"
            }
        ])
        
        # Add service-specific link if provided
        if service:
            links.append({
                "title": f"AWS {service} Documentation",
                "url": f"https://docs.aws.amazon.com/{service.lower().replace(' ', '-')}/",
                "description": f"Official AWS {service} documentation"
            })
        
        return links
    
    def _convert_to_readable_string(self, data: Any) -> str:
        """Convert complex data types to readable strings (not repr)."""
        try:
            if isinstance(data, dict):
                # Convert dict to readable format
                items = []
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        items.append(f"{key}: [complex data]")
                    else:
                        items.append(f"{key}: {value}")
                return ", ".join(items)
            elif isinstance(data, list):
                # Convert list to readable format
                if all(isinstance(item, str) for item in data):
                    return ", ".join(data)
                else:
                    return f"{len(data)} items"
            else:
                return str(data)
        except Exception:
            return "[data conversion error]"
    
    def _generate_user_friendly_error_message(
        self,
        errors: List[ValidationError],
        warnings: List[str]
    ) -> str:
        """Generate a user-friendly error message."""
        if not errors and not warnings:
            return "Report generated successfully"
        
        message_parts = []
        
        if errors:
            critical_errors = [e for e in errors if e.severity == "critical"]
            if critical_errors:
                message_parts.append(
                    f"Critical errors occurred during report generation ({len(critical_errors)} issues). "
                    "Some sections may contain placeholder data."
                )
            else:
                message_parts.append(
                    f"Minor errors occurred during report generation ({len(errors)} issues). "
                    "Report quality may be affected."
                )
        
        if warnings:
            message_parts.append(
                f"{len(warnings)} warnings were generated. "
                "Some data was incomplete and fallback values were used."
            )
        
        message_parts.append(
            "Please review the report carefully and consider re-running the assessment "
            "with complete data for best results."
        )
        
        return " ".join(message_parts)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors and warnings."""
        return {
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "errors_by_severity": {
                "critical": len([e for e in self.errors if e.severity == "critical"]),
                "error": len([e for e in self.errors if e.severity == "error"]),
                "warning": len([e for e in self.errors if e.severity == "warning"])
            },
            "errors": [
                {
                    "component": e.component,
                    "type": e.error_type,
                    "message": e.message,
                    "severity": e.severity,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self.errors
            ],
            "warnings": self.warnings
        }
    
    def clear_errors(self):
        """Clear all accumulated errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
