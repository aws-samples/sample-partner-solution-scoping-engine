# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pydantic models for CloudFormation template generation and validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class CloudFormationTemplate(BaseModel):
    """Model representing a CloudFormation template."""
    
    name: str = Field(..., description="Template filename (e.g., 'vpc.yaml')")
    content: str = Field(..., description="YAML/JSON content of the template")


class ValidationRequest(BaseModel):
    """Model for CloudFormation validation requests."""
    
    chat_id: str = Field(..., description="Unique chat session identifier")
    project_name: str = Field(..., description="Name of the infrastructure project")
    infrastructure_description: str = Field(..., description="Description of infrastructure to generate")
    templates: List[CloudFormationTemplate] = Field(..., description="List of CloudFormation templates to validate")


class ValidationError(BaseModel):
    """Model representing a validation error."""
    
    template_name: str = Field(..., description="Name of the template with error")
    error_type: str = Field(..., description="Type of error (yaml_syntax, aws_validation)")
    error_message: str = Field(..., description="Detailed error message")
    aws_error_code: Optional[str] = Field(None, description="AWS-specific error code")
    line_number: Optional[int] = Field(None, description="Line number where error occurred")
    suggestions: List[str] = Field(default_factory=list, description="Suggested fixes for the error")


class TemplateFile(BaseModel):
    """Model representing an uploaded CloudFormation template file."""
    
    name: str = Field(..., description="Template filename")
    s3_url: str = Field(..., description="S3 URL of the template")
    s3_key: str = Field(..., description="S3 key path")
    version_id: Optional[str] = Field(None, description="S3 version ID")
    file_size: int = Field(..., description="File size in bytes")
    validation_status: str = Field(..., description="Validation status (aws_validated, syntax_error, etc.)")


class ValidationResult(BaseModel):
    """Model for CloudFormation validation results."""
    
    status: str = Field(..., description="Overall validation status (success, error)")
    chat_id: str = Field(..., description="Chat session identifier")
    message: str = Field(..., description="Human-readable result message")
    templates_validated: int = Field(0, description="Number of templates successfully validated")
    files: List[TemplateFile] = Field(default_factory=list, description="List of uploaded template files")
    error: Optional[ValidationError] = Field(None, description="Error details if validation failed")


class SecurityScanOptions(BaseModel):
    """Model for security scanning configuration."""
    
    include_cfn_nag: bool = Field(True, description="Include cfn-nag security scanning")
    include_python_analysis: bool = Field(True, description="Include Python code analysis for Custom Resources")
    fail_on_warnings: bool = Field(False, description="Treat warnings as failures")


class SecurityScanRequest(BaseModel):
    """Model for security scanning requests."""
    
    chat_id: str = Field(..., description="Chat session identifier")
    scan_options: SecurityScanOptions = Field(default_factory=SecurityScanOptions, description="Scanning options")


class SecurityIssue(BaseModel):
    """Model representing a security issue found during scanning."""
    
    rule_id: str = Field(..., description="Security rule identifier")
    type: str = Field(..., description="Issue type (WARN, FAIL, etc.)")
    severity: str = Field(..., description="Issue severity (HIGH, MEDIUM, LOW)")
    message: str = Field(..., description="Issue description")
    resource: Optional[str] = Field(None, description="AWS resource name where issue was found")
    line_number: Optional[int] = Field(None, description="Line number where issue occurred")


class CfnNagResults(BaseModel):
    """Model for cfn-nag scanning results."""
    
    issues: List[SecurityIssue] = Field(default_factory=list, description="List of security issues found")


class PythonCodeResults(BaseModel):
    """Model for Python code analysis results."""
    
    custom_resources_found: List[str] = Field(default_factory=list, description="List of Custom Resource names found")
    bandit_issues: List[SecurityIssue] = Field(default_factory=list, description="List of Python security issues")


class TemplateSecurityResults(BaseModel):
    """Model for security results for a single template."""
    
    template_name: str = Field(..., description="Name of the scanned template")
    cfn_nag_results: Optional[CfnNagResults] = Field(None, description="cfn-nag scanning results")
    python_code_results: Optional[PythonCodeResults] = Field(None, description="Python code analysis results")


class SecuritySummary(BaseModel):
    """Model for overall security scan summary."""
    
    overall_score: str = Field(..., description="Overall risk assessment (low_risk, medium_risk, high_risk)")
    total_issues: int = Field(..., description="Total number of issues found")
    critical_issues: int = Field(..., description="Number of critical issues")
    warnings: int = Field(..., description="Number of warnings")


class SecurityScanResult(BaseModel):
    """Model for complete security scanning results."""
    
    status: str = Field(..., description="Scan status (completed, error)")
    chat_id: str = Field(..., description="Chat session identifier")
    scan_duration_seconds: float = Field(..., description="Time taken for the scan")
    templates_scanned: int = Field(..., description="Number of templates scanned")
    security_summary: SecuritySummary = Field(..., description="Overall security summary")
    template_results: List[TemplateSecurityResults] = Field(default_factory=list, description="Per-template results")
    recommendations: List[str] = Field(default_factory=list, description="Security recommendations")
    error_message: Optional[str] = Field(None, description="Error message if scan failed")


class TemplateListItem(BaseModel):
    """Model representing a template in a list."""
    
    name: str = Field(..., description="Template filename")
    s3_key: str = Field(..., description="S3 key path")
    s3_url: str = Field(..., description="S3 URL")
    version_id: Optional[str] = Field(None, description="S3 version ID")
    size: int = Field(..., description="File size in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    validation_status: str = Field(..., description="Last known validation status")


class TemplateListResult(BaseModel):
    """Model for template listing results."""
    
    status: str = Field(..., description="Operation status")
    chat_id: str = Field(..., description="Chat session identifier")
    template_count: int = Field(..., description="Number of templates found")
    templates: List[TemplateListItem] = Field(default_factory=list, description="List of templates")


class TemplateDownloadResult(BaseModel):
    """Model for template download results."""
    
    status: str = Field(..., description="Download status")
    template_name: str = Field(..., description="Downloaded template name")
    content: str = Field(..., description="Template content")
    s3_key: str = Field(..., description="S3 key of the template")
    version_id: Optional[str] = Field(None, description="S3 version ID")
    size: int = Field(..., description="File size in bytes")