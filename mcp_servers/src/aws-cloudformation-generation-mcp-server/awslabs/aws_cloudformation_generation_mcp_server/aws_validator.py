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

"""AWS CloudFormation validation engine with comprehensive error handling."""

import re
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from loguru import logger

from .models import ValidationError


class CloudFormationValidator:
    """AWS CloudFormation template validator with error handling and suggestions."""
    
    def __init__(self, region: str = "us-east-1"):
        """Initialize the CloudFormation validator.
        
        Args:
            region: AWS region for CloudFormation client
        """
        self.region = region
        self.config = Config(
            region_name=region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=10
        )
        self.cfn_client = boto3.client('cloudformation', config=self.config)
        
    
    def validate_with_aws_api(self, template_name: str, content: str) -> Optional[ValidationError]:
        """Validate CloudFormation template using AWS API.
        
        Args:
            template_name: Name of the template file
            content: Template content to validate
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        logger.debug(f"[CFN_VALIDATE] Starting AWS API validation for template: {template_name}")
        logger.debug(f"[CFN_VALIDATE] Template content length: {len(content)} characters")
        
        try:
            logger.debug(f"[CFN_VALIDATE] Calling AWS CloudFormation validate_template API for {template_name}")
            response = self.cfn_client.validate_template(TemplateBody=content)
            logger.debug(f"[CFN_VALIDATE] AWS validation response for {template_name}: {response}")
            logger.info(f"[CFN_VALIDATE] ✅ AWS validation PASSED for {template_name}")
            return None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'ValidationError')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error(f"[CFN_VALIDATE] ❌ AWS validation FAILED for {template_name}")
            logger.error(f"[CFN_VALIDATE] Error code: {error_code}")
            logger.error(f"[CFN_VALIDATE] Error message: {error_message}")
            
            suggestions = self._generate_error_suggestions(error_code, error_message)
            
            return ValidationError(
                template_name=template_name,
                error_type="aws_validation",
                error_message=f"Template format error: {error_message}",
                aws_error_code=error_code,
                suggestions=suggestions
            )
            
        except BotoCoreError as e:
            logger.error(f"[CFN_VALIDATE] ❌ AWS API error validating {template_name}: {e}")
            return ValidationError(
                template_name=template_name,
                error_type="aws_api_error",
                error_message=f"AWS API error: {str(e)}",
                suggestions=["Check AWS credentials and network connectivity", "Retry the validation"]
            )
    
    def _generate_error_suggestions(self, error_code: str, error_message: str) -> List[str]:
        """Generate helpful suggestions based on AWS validation errors.
        
        Args:
            error_code: AWS error code
            error_message: AWS error message
            
        Returns:
            List of suggestions for fixing the error
        """
        suggestions = []
        
        # Common error patterns and suggestions
        error_patterns = {
            r"Unresolved resource dependencies \[(.+?)\]": [
                "Check that referenced resources are defined in the template",
                "Verify resource dependencies are correct",
                "Ensure all Ref and GetAtt references are valid"
            ],
            r"Template format error: (.+?) is not supported": [
                "Check AWS documentation for supported resource types",
                "Verify the resource type name spelling",
                "Ensure you're using the correct AWS region for this resource"
            ],
            r"Invalid template property or properties \[(.+?)\]": [
                "Check AWS documentation for valid resource properties",
                "Verify property names are spelled correctly",
                "Remove any unsupported properties"
            ],
            r"Template parameter (.+?) must have a value": [
                "Provide a default value for the parameter",
                "Ensure parameter values are supplied when using the template",
                "Check parameter definitions in the template"
            ],
            r"Circular dependency between resources": [
                "Review resource dependencies to identify circular references",
                "Consider using Conditions or DependsOn attributes",
                "Restructure resources to eliminate the cycle"
            ]
        }
        
        # Match error patterns and add specific suggestions
        for pattern, pattern_suggestions in error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                suggestions.extend(pattern_suggestions)
                break
        
        # Error code specific suggestions
        code_suggestions = {
            "ValidationError": [
                "Review the CloudFormation template syntax",
                "Check AWS documentation for the specific error"
            ],
            "AccessDenied": [
                "Check AWS IAM permissions for CloudFormation",
                "Ensure proper credentials are configured"
            ],
            "InvalidParameterValue": [
                "Verify parameter values match expected formats",
                "Check parameter constraints and allowed values"
            ],
            "LimitExceeded": [
                "Check AWS service limits for resources in the template",
                "Consider splitting large templates into nested stacks"
            ]
        }
        
        if error_code in code_suggestions:
            suggestions.extend(code_suggestions[error_code])
        
        # General suggestions if no specific patterns matched
        if not suggestions:
            suggestions = [
                "Review the CloudFormation template syntax",
                "Check AWS documentation for the resource types used",
                "Validate template parameters and their values",
                "Ensure proper IAM permissions for CloudFormation"
            ]
        
        return suggestions
    
    def validate_template(self, template_name: str, content: str) -> Optional[ValidationError]:
        """Validate a CloudFormation template using AWS API.
        
        Args:
            template_name: Name of the template file
            content: Template content to validate
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        logger.info(f"[CFN_VALIDATE] 🔍 Starting validation for template: {template_name}")
        logger.debug(f"[CFN_VALIDATE] Validation method: AWS CloudFormation API validate_template()")
        
        # Validate directly with AWS API (handles CloudFormation YAML syntax)
        aws_error = self.validate_with_aws_api(template_name, content)
        if aws_error:
            logger.error(f"[CFN_VALIDATE] ❌ Template validation failed: {template_name}")
            return aws_error
        
        logger.info(f"[CFN_VALIDATE] ✅ Template {template_name} passed ALL validations")
        return None
    
    def validate_multiple_templates(self, templates: Dict[str, str]) -> List[ValidationError]:
        """Validate multiple CloudFormation templates.
        
        Args:
            templates: Dictionary mapping template names to content
            
        Returns:
            List of validation errors (empty if all templates are valid)
        """
        errors = []
        
        for template_name, content in templates.items():
            error = self.validate_template(template_name, content)
            if error:
                errors.append(error)
        
        return errors
    
    def get_template_summary(self, content: str) -> Dict:
        """Get CloudFormation template summary from AWS API.
        
        Args:
            content: Template content
            
        Returns:
            Template summary dictionary
        """
        try:
            response = self.cfn_client.get_template_summary(TemplateBody=content)
            return {
                "description": response.get("Description", ""),
                "parameters": response.get("Parameters", []),
                "resources": response.get("ResourceTypes", []),
                "capabilities": response.get("Capabilities", []),
                "resource_count": len(response.get("ResourceTypes", []))
            }
        except ClientError as e:
            logger.warning(f"Failed to get template summary: {e}")
            return {}
    
    def estimate_template_cost(self, content: str, parameters: Optional[Dict] = None) -> Optional[str]:
        """Estimate template deployment cost using AWS API.
        
        Args:
            content: Template content
            parameters: Template parameters
            
        Returns:
            Cost estimate URL or None if estimation fails
        """
        try:
            params = {
                "TemplateBody": content,
            }
            
            if parameters:
                params["Parameters"] = [
                    {"ParameterKey": k, "ParameterValue": str(v)}
                    for k, v in parameters.items()
                ]
            
            response = self.cfn_client.estimate_template_cost(**params)
            return response.get("Url")
            
        except ClientError as e:
            logger.warning(f"Failed to estimate template cost: {e}")
            return None