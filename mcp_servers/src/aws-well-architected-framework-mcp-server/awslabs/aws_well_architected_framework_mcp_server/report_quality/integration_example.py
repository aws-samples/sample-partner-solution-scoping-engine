"""Integration Example for Report Quality Enhancement Components.

This module demonstrates how to use the error handling, logging, and validation
components together in the report generation workflow.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .error_handler import GracefulDegradationHandler
from .report_logger import ReportLoggerFactory
from .docx_validator import get_docx_validator

logger = logging.getLogger(__name__)


def generate_report_with_error_handling(
    chat_id: str,
    assessment_data: Optional[Dict[str, Any]],
    output_path: str
) -> Dict[str, Any]:
    """
    Example of generating a report with comprehensive error handling.
    
    This demonstrates the integration of all error handling components:
    1. Graceful degradation for missing/invalid data
    2. Comprehensive logging of all issues
    3. DOCX file validation and recovery
    
    Args:
        chat_id: Unique chat session identifier
        assessment_data: Assessment data (may be incomplete)
        output_path: Path where the report should be saved
        
    Returns:
        Dictionary with generation results and status
    """
    # Initialize components
    degradation_handler = GracefulDegradationHandler()
    report_logger = ReportLoggerFactory.get_logger(chat_id)
    docx_validator = get_docx_validator()
    
    try:
        logger.info(f"🚀 Starting report generation with error handling for chat_id: {chat_id}")
        
        # Step 1: Handle missing assessment data
        assessment_result = degradation_handler.handle_missing_assessment_data(assessment_data)
        
        if assessment_result.fallback_used:
            report_logger.log_content_warning(
                warning_type="missing_data",
                message="Assessment data was incomplete, using fallback values",
                affected_component="assessment_data",
                recommendation="Re-run assessment with complete data"
            )
        
        validated_data = assessment_result.data
        
        # Step 2: Validate pillar assessments
        pillar_assessments = validated_data.get("pillar_assessments", {})
        total_pillars = len(pillar_assessments)
        successful_pillars = 0
        failed_pillars = 0
        
        for pillar_name, pillar_data in pillar_assessments.items():
            # Validate pillar data structure
            pillar_result = degradation_handler.handle_invalid_data_structures(
                pillar_data,
                "dict",
                f"pillar_{pillar_name}"
            )
            
            if pillar_result.fallback_used:
                report_logger.log_validation_error(
                    component=f"pillar_{pillar_name}",
                    validation_type="data_structure",
                    message=f"Invalid pillar data structure for {pillar_name}",
                    severity="warning"
                )
                failed_pillars += 1
            else:
                successful_pillars += 1
        
        report_logger.update_pillar_stats(total_pillars, successful_pillars, failed_pillars)
        
        # Step 3: Handle missing metadata
        metadata = validated_data.get("metadata", {})
        metadata_result = degradation_handler.handle_missing_metadata(metadata)
        
        if metadata_result.fallback_used:
            report_logger.log_content_warning(
                warning_type="missing_metadata",
                message="Metadata was incomplete, using default values",
                affected_component="metadata"
            )
        
        validated_data["metadata"] = metadata_result.data
        
        # Step 4: Generate the report (simulated)
        # In real implementation, this would call the actual report generator
        try:
            # Simulate report generation
            logger.info("📝 Generating report content...")
            
            # For this example, we'll create a minimal DOCX
            success = docx_validator.create_minimal_valid_docx(
                output_path,
                title="WAFR Assessment Report"
            )
            
            if not success:
                raise Exception("Failed to create DOCX file")
            
            # Step 5: Validate the generated DOCX
            validation_result = docx_validator.validate_docx_file(output_path)
            
            if not validation_result.is_valid:
                report_logger.log_formatting_error(
                    section="docx_generation",
                    error_type="validation_failed",
                    message=f"DOCX validation failed: {', '.join(validation_result.errors)}",
                    fallback_used=False
                )
                
                # Attempt recovery
                recovery_success, recovery_path, recovery_message = docx_validator.recover_from_generation_failure(
                    error=Exception("DOCX validation failed"),
                    output_path=output_path
                )
                
                if recovery_success:
                    report_logger.log_content_warning(
                        warning_type="recovery_used",
                        message="DOCX was recovered after validation failure",
                        affected_component="docx_file",
                        recommendation="Review the recovered file"
                    )
                    output_path = recovery_path
            
            # Step 6: Ensure file integrity
            integrity_success, integrity_message = docx_validator.ensure_file_integrity(output_path)
            
            if not integrity_success:
                report_logger.log_formatting_error(
                    section="docx_integrity",
                    error_type="integrity_check_failed",
                    message=integrity_message,
                    fallback_used=False
                )
            
            # Step 7: Log generation summary
            import os
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            report_logger.log_generation_summary(
                success=True,
                report_size_bytes=file_size
            )
            
            # Step 8: Add error explanations to report data
            validated_data = degradation_handler.add_error_explanation_to_report(
                validated_data,
                degradation_handler.errors,
                degradation_handler.warnings
            )
            
            # Return results
            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "validation_result": validation_result.to_dict(),
                "error_summary": degradation_handler.get_error_summary(),
                "log_summary": report_logger.get_error_summary_for_report(),
                "generation_stats": report_logger.stats.to_dict()
            }
            
        except Exception as generation_error:
            logger.error(f"❌ Report generation failed: {generation_error}")
            
            # Ensure partial report generation
            partial_data = degradation_handler.ensure_partial_report_generation(
                validated_data,
                generation_error
            )
            
            # Attempt recovery
            recovery_success, recovery_path, recovery_message = docx_validator.recover_from_generation_failure(
                error=generation_error,
                partial_content=str(partial_data),
                output_path=output_path
            )
            
            report_logger.log_formatting_error(
                section="report_generation",
                error_type="generation_failed",
                message=str(generation_error),
                fallback_used=recovery_success
            )
            
            report_logger.log_generation_summary(
                success=recovery_success,
                report_size_bytes=0
            )
            
            return {
                "success": recovery_success,
                "output_path": recovery_path if recovery_success else "",
                "error": str(generation_error),
                "recovery_message": recovery_message,
                "error_summary": degradation_handler.get_error_summary(),
                "log_summary": report_logger.get_error_summary_for_report()
            }
    
    except Exception as e:
        logger.error(f"❌ Critical error in report generation: {e}")
        
        report_logger.log_validation_error(
            component="report_generation",
            validation_type="critical_error",
            message=str(e),
            severity="critical"
        )
        
        report_logger.log_generation_summary(success=False)
        
        return {
            "success": False,
            "error": str(e),
            "error_summary": degradation_handler.get_error_summary(),
            "log_summary": report_logger.get_error_summary_for_report()
        }


def example_usage():
    """Example usage of the integrated error handling system."""
    
    # Example 1: Complete data
    print("Example 1: Complete assessment data")
    print("=" * 50)
    
    complete_data = {
        "chat_id": "test-123",
        "overall_score": 85.0,
        "pillar_assessments": {
            "security": {"score": 90.0, "risk_level": "Low"},
            "reliability": {"score": 80.0, "risk_level": "Medium"}
        },
        "metadata": {
            "assessment_date": datetime.now().isoformat(),
            "services_analyzed": 10
        }
    }
    
    result1 = generate_report_with_error_handling(
        chat_id="test-123",
        assessment_data=complete_data,
        output_path="/tmp/wafr_report_complete.docx"
    )
    
    print(f"Success: {result1['success']}")
    print(f"Errors: {result1['error_summary']['total_errors']}")
    print(f"Warnings: {result1['error_summary']['total_warnings']}")
    print()
    
    # Example 2: Missing data
    print("Example 2: Missing assessment data")
    print("=" * 50)
    
    result2 = generate_report_with_error_handling(
        chat_id="test-456",
        assessment_data=None,
        output_path="/tmp/wafr_report_missing.docx"
    )
    
    print(f"Success: {result2['success']}")
    print(f"Errors: {result2['error_summary']['total_errors']}")
    print(f"Warnings: {result2['error_summary']['total_warnings']}")
    print()
    
    # Example 3: Invalid data structure
    print("Example 3: Invalid data structure")
    print("=" * 50)
    
    invalid_data = {
        "chat_id": "test-789",
        "overall_score": "not a number",  # Invalid
        "pillar_assessments": "not a dict"  # Invalid
    }
    
    result3 = generate_report_with_error_handling(
        chat_id="test-789",
        assessment_data=invalid_data,
        output_path="/tmp/wafr_report_invalid.docx"
    )
    
    print(f"Success: {result3['success']}")
    print(f"Errors: {result3['error_summary']['total_errors']}")
    print(f"Warnings: {result3['error_summary']['total_warnings']}")


if __name__ == "__main__":
    # Run examples
    example_usage()
