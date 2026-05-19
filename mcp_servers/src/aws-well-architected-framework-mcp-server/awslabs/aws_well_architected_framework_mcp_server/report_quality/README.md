# WAFR Report Quality Enhancement - Error Handling and Validation

This module provides comprehensive error handling, validation, and logging capabilities for WAFR report generation, ensuring that partial reports can be generated even when data is incomplete or errors occur.

## Overview

The report quality enhancement module consists of three main components:

1. **Graceful Degradation Handler** - Handles missing or invalid data with intelligent fallbacks
2. **Report Generation Logger** - Provides comprehensive logging with integration into existing infrastructure
3. **DOCX Validator** - Ensures DOCX files are valid and openable with recovery mechanisms

## Components

### 1. Graceful Degradation Handler (`error_handler.py`)

Handles various error scenarios with appropriate fallback mechanisms:

#### Features

- **Missing Assessment Data**: Provides complete fallback assessment data when data is missing
- **Invalid Data Structures**: Converts invalid data types to expected formats
- **Missing Metadata**: Fills in missing metadata fields with sensible defaults
- **Documentation Link Failures**: Uses static fallback links when dynamic generation fails
- **Partial Report Generation**: Ensures reports can be generated even with errors
- **Error Explanations**: Adds clear error messages to reports for users

#### Usage

```python
from report_quality import GracefulDegradationHandler

handler = GracefulDegradationHandler()

# Handle missing assessment data
result = handler.handle_missing_assessment_data(assessment_data)
if result.fallback_used:
    print(f"Warnings: {result.warnings}")
validated_data = result.data

# Handle invalid data structures
result = handler.handle_invalid_data_structures(
    data=some_data,
    expected_type="dict",
    component="pillar_assessment"
)

# Handle missing metadata
result = handler.handle_missing_metadata(metadata)
complete_metadata = result.data

# Handle documentation link failures
result = handler.handle_documentation_link_failure(
    pillar="security",
    service="IAM"
)
fallback_links = result.data

# Ensure partial report generation on error
partial_data = handler.ensure_partial_report_generation(
    assessment_data=incomplete_data,
    error=exception
)

# Add error explanations to report
enhanced_data = handler.add_error_explanation_to_report(
    report_data=data,
    errors=handler.errors,
    warnings=handler.warnings
)
```

#### Fallback Strategies

1. **Complete Data Fallback**: When assessment data is completely missing, provides a full fallback structure with all 6 pillars
2. **Field-Level Fallback**: When specific fields are missing, fills them with appropriate defaults
3. **Type Conversion**: Converts invalid types to expected types (e.g., string to dict, dict to readable string)
4. **Static Documentation**: Uses pre-defined AWS documentation links when dynamic generation fails

### 2. Report Generation Logger (`report_logger.py`)

Provides comprehensive logging with detailed tracking of validation errors, formatting issues, and content warnings.

#### Features

- **Validation Error Logging**: Tracks data validation errors with severity levels
- **Formatting Error Logging**: Logs formatting issues with section context
- **Content Warning Logging**: Records content quality warnings
- **Generation Statistics**: Tracks comprehensive metrics about report generation
- **Integration with Existing Logging**: Uses standard Python logging infrastructure
- **Factory Pattern**: Manages logger instances per chat session

#### Usage

```python
from report_quality import ReportLoggerFactory

# Get logger for a chat session
logger = ReportLoggerFactory.get_logger(chat_id="test-123")

# Log validation errors
logger.log_validation_error(
    component="pillar_security",
    validation_type="data_structure",
    message="Invalid pillar data structure",
    severity="error",
    data_context={"pillar": "security"}
)

# Log formatting errors
logger.log_formatting_error(
    section="executive_summary",
    error_type="missing_data",
    message="Executive summary data incomplete",
    pillar="security",
    fallback_used=True
)

# Log content warnings
logger.log_content_warning(
    warning_type="low_confidence",
    message="Assessment confidence is below threshold",
    affected_component="overall_score",
    recommendation="Review assessment data and re-run"
)

# Update statistics
logger.update_pillar_stats(total=6, successful=5, failed=1)
logger.update_recommendation_count(count=15)

# Log generation summary
logger.log_generation_summary(
    success=True,
    report_size_bytes=1024000
)

# Get error summary for report
error_summary = logger.get_error_summary_for_report()

# Export complete log
log_json = logger.export_to_json()
```

#### Log Entry Types

1. **ValidationLogEntry**: Validation errors with component context
2. **FormattingLogEntry**: Formatting errors with section and pillar context
3. **ContentWarningEntry**: Content quality warnings with recommendations
4. **GenerationStats**: Comprehensive statistics about report generation

#### Statistics Tracked

- Duration (seconds)
- Total/successful/failed pillars
- Total recommendations
- Validation/formatting errors
- Content warnings
- Fallbacks used
- Report size (bytes)

### 3. DOCX Validator (`docx_validator.py`)

Ensures DOCX files are valid and openable with recovery mechanisms for generation failures.

#### Features

- **File Validation**: Validates DOCX structure and integrity
- **Openability Check**: Verifies files can be opened with python-docx
- **Error Recovery**: Creates minimal valid DOCX files when generation fails
- **File Repair**: Attempts to repair corrupted DOCX files
- **Integrity Checks**: Comprehensive checks for file validity

#### Usage

```python
from report_quality import get_docx_validator

validator = get_docx_validator()

# Validate a DOCX file
validation_result = validator.validate_docx_file("/path/to/report.docx")
print(f"Valid: {validation_result.is_valid}")
print(f"Can open: {validation_result.can_open}")
print(f"Errors: {validation_result.errors}")
print(f"Warnings: {validation_result.warnings}")

# Recover from generation failure
success, file_path, message = validator.recover_from_generation_failure(
    error=exception,
    partial_content="Partial report content",
    output_path="/path/to/recovery.docx"
)

# Ensure file integrity
success, message = validator.ensure_file_integrity("/path/to/report.docx")

# Create minimal valid DOCX
success = validator.create_minimal_valid_docx(
    output_path="/path/to/minimal.docx",
    title="WAFR Report"
)

# Run comprehensive integrity checks
checks = validator.add_integrity_checks("/path/to/report.docx")
```

#### Validation Checks

1. **File Existence**: Verifies file exists
2. **File Size**: Checks file is not empty
3. **ZIP Structure**: Validates DOCX is a valid ZIP file
4. **Required Files**: Checks for required DOCX components
5. **File Integrity**: Tests ZIP integrity
6. **Openability**: Attempts to open with python-docx

#### Recovery Mechanisms

1. **Minimal DOCX Creation**: Creates a valid DOCX with error information
2. **Partial Content Inclusion**: Includes any partial content that was generated
3. **Error Documentation**: Documents the error and provides recovery instructions
4. **Text File Fallback**: Creates a text file if python-docx is not available

## Integration Example

See `integration_example.py` for a complete example of using all components together:

```python
from report_quality import (
    GracefulDegradationHandler,
    ReportLoggerFactory,
    get_docx_validator
)

def generate_report_with_error_handling(chat_id, assessment_data, output_path):
    # Initialize components
    degradation_handler = GracefulDegradationHandler()
    report_logger = ReportLoggerFactory.get_logger(chat_id)
    docx_validator = get_docx_validator()
    
    try:
        # Handle missing data
        assessment_result = degradation_handler.handle_missing_assessment_data(
            assessment_data
        )
        
        # Validate and generate report
        # ... (see integration_example.py for complete code)
        
        # Validate generated DOCX
        validation_result = docx_validator.validate_docx_file(output_path)
        
        # Log summary
        report_logger.log_generation_summary(success=True, report_size_bytes=file_size)
        
        return {"success": True, "output_path": output_path}
        
    except Exception as e:
        # Ensure partial report generation
        partial_data = degradation_handler.ensure_partial_report_generation(
            assessment_data, e
        )
        
        # Attempt recovery
        success, path, msg = docx_validator.recover_from_generation_failure(
            error=e, output_path=output_path
        )
        
        return {"success": success, "output_path": path, "error": str(e)}
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Report Generation Request                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Graceful Degradation Handler                         │
│  • Validate assessment data                                  │
│  • Handle missing/invalid data                               │
│  • Apply fallbacks as needed                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Report Generation Logger                             │
│  • Log validation errors                                     │
│  • Log formatting errors                                     │
│  • Log content warnings                                      │
│  • Track statistics                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Report Generation (with error handling)              │
│  • Generate report content                                   │
│  • Create DOCX file                                          │
│  • Handle generation errors                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         DOCX Validator                                       │
│  • Validate DOCX structure                                   │
│  • Check file integrity                                      │
│  • Recover from failures                                     │
│  • Ensure file is openable                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Final Report (with error summary)                    │
│  • Valid DOCX file                                           │
│  • Error explanations included                               │
│  • Comprehensive logs                                        │
└─────────────────────────────────────────────────────────────┘
```

## Requirements Addressed

This implementation addresses the following requirements from the spec:

### Requirement 12: Report Generation Error Handling

- ✅ **12.1**: Handles incomplete assessment data with placeholder sections
- ✅ **12.2**: Validates all data structures before formatting
- ✅ **12.3**: Includes failed pillars with error notes
- ✅ **12.4**: Logs all formatting errors with sufficient detail
- ✅ **12.5**: Ensures DOCX files are valid and openable

### Requirement 15.5: Logging Infrastructure

- ✅ Integrates with existing logging infrastructure
- ✅ Provides detailed error logging
- ✅ Tracks generation statistics
- ✅ Exports logs for analysis

## Testing

To test the error handling components:

```bash
# Run the integration example
python -m awslabs.aws_well_architected_framework_mcp_server.report_quality.integration_example

# Run with different scenarios
python -c "
from report_quality.integration_example import generate_report_with_error_handling

# Test with missing data
result = generate_report_with_error_handling(
    chat_id='test-1',
    assessment_data=None,
    output_path='/tmp/test_report.docx'
)
print(result)
"
```

## Best Practices

1. **Always use the factory pattern** for loggers to ensure proper session tracking
2. **Check fallback_used flag** to determine if data quality is affected
3. **Validate DOCX files** after generation before uploading to S3
4. **Include error summaries** in reports for user transparency
5. **Clear loggers** after report generation to prevent memory leaks
6. **Use appropriate severity levels** for errors (critical, error, warning)
7. **Provide actionable recommendations** in content warnings

## Future Enhancements

Potential improvements for future iterations:

1. **Metrics Dashboard**: Real-time monitoring of error rates and fallback usage
2. **Automated Recovery**: More sophisticated recovery strategies based on error patterns
3. **Quality Scoring**: Automated quality scoring for generated reports
4. **Error Analytics**: Analysis of common error patterns for proactive fixes
5. **User Notifications**: Automated notifications for critical errors
6. **Retry Mechanisms**: Automatic retry with different strategies on failure

## Support

For issues or questions about the error handling implementation:

1. Check the integration example for usage patterns
2. Review the inline documentation in each module
3. Check the logs for detailed error information
4. Contact the WAFR development team for assistance
