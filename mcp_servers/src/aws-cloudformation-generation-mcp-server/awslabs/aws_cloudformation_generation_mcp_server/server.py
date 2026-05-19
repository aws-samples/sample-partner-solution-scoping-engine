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

"""AWS CloudFormation Generation MCP Server implementation."""

import json
import os
import sys
import logging
from typing import Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .aws_validator import CloudFormationValidator
from .models import (
    CloudFormationTemplate, TemplateDownloadResult, TemplateListResult, 
    ValidationRequest, ValidationResult
)
from .s3_manager import CloudFormationS3Manager

# Set up logging using shared backend configuration
try:
    # Add backend path to sys.path to import the logger utility
    backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from utils.mcp_logger import setup_mcp_logging
    logger = setup_mcp_logging("aws-cloudformation-generation-mcp-server")
    logger.info("AWS CloudFormation Generation MCP Server logger initialized using backend configuration")
except ImportError as e:
    # Fallback to basic logging if backend utils not available
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("aws-cloudformation-generation-mcp-server.log", maxBytes=10*1024*1024, backupCount=5)
        ]
    )
    logger = logging.getLogger("aws-cloudformation-generation-mcp-server")
    logger.warning(f"Could not import backend logger utility, using fallback logging: {e}")
except Exception as e:
    # Final fallback
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("aws-cloudformation-generation-mcp-server")
    logger.error(f"Error setting up logging: {e}")

mcp = FastMCP(
    "awslabs.aws-cloudformation-generation-mcp-server",
    instructions="""
    AWS CloudFormation Validation MCP Server

    This server validates CloudFormation templates created by the LLM and provides secure storage with download links.

    Available Tools:
    1. validate_and_store_cloudformation_templates - Validate LLM-generated templates and store in S3
    2. generate_cloudformation_from_solution - Generate templates iteratively from recommended_solution variable
    3. list_cloudformation_templates - List all templates for a chat session
    4. download_cloudformation_template - Download specific template content

    Core Features:
    - YAML syntax validation with detailed error reporting
    - AWS CloudFormation API validation using boto3 validate_template()
    - S3 storage with versioning and clickable download links
    - Comprehensive error handling with actionable suggestions

    Usage Patterns:
    - Manual validation: Use validate_and_store_cloudformation_templates to validate LLM-created templates
    - Automated generation: Use generate_cloudformation_from_solution to auto-generate from recommended_solution
    - Template management: Use list and download tools for template retrieval

    The server automatically organizes templates in S3 using the pattern: {chat_id}/cloudformation/{template_name}
    All templates include metadata for tracking validation status, project information, and generation timestamps.
    """,
    dependencies=[
        'pydantic',
        'loguru',
        'boto3',
        'pyyaml',
    ],
)

# Initialize service components
validator = CloudFormationValidator()
s3_manager = CloudFormationS3Manager()


@mcp.tool(name='validate_and_store_cloudformation_templates')
async def validate_and_store_cloudformation_templates(
    chat_id: str,
    project_name: str,
    infrastructure_description: str,
    templates: List[Dict[str, str]]
) -> Dict:
    """Validate CloudFormation templates using AWS API and store validated templates in S3.
    
    This tool validates CloudFormation templates created by the LLM and provides:
    - YAML syntax validation with detailed error reporting
    - AWS CloudFormation API validation using boto3 validate_template()
    - S3 storage with versioning and clickable download links
    - Fast validation cycle (target: <5 seconds)
    
    Args:
        chat_id: Unique chat session identifier for organizing templates
        project_name: Name of the infrastructure project for metadata
        infrastructure_description: Description of the infrastructure to be deployed
        templates: List of LLM-generated templates, each with 'name' and 'content' keys
        
    Returns:
        Success: {"status": "success", "chat_id": str, "message": str, "templates_validated": int, "files": [TemplateFile]}
        Error: {"status": "error", "template_name": str, "error_type": str, "error_message": str, "suggestions": [str]}
    """
    try:
        # logger.info(f"Starting CloudFormation validation for {len(templates)} templates (chat: {chat_id})")
        
        # Validate input
        if not templates:
            return {
                "status": "error",
                "error_message": "No templates provided for validation",
                "suggestions": ["Provide at least one CloudFormation template"]
            }
        
        # Convert input format to internal models
        cf_templates = []
        templates_dict = {}
        
        for template_data in templates:
            if not isinstance(template_data, dict) or 'name' not in template_data or 'content' not in template_data:
                return {
                    "status": "error", 
                    "error_message": "Invalid template format. Each template must have 'name' and 'content' fields",
                    "suggestions": ["Ensure each template is a dictionary with 'name' and 'content' keys"]
                }
            
            cf_template = CloudFormationTemplate(
                name=template_data['name'],
                content=template_data['content']
            )
            cf_templates.append(cf_template)
            templates_dict[cf_template.name] = cf_template.content
        
        # Validate all templates
        logger.info(f"[CFN_VALIDATE] 🔍 Starting validation of {len(templates_dict)} templates for chat {chat_id}")
        for name in templates_dict.keys():
            logger.debug(f"[CFN_VALIDATE] Template to validate: {name}")
        
        validation_errors = validator.validate_multiple_templates(templates_dict)
        
        logger.info(f"[CFN_VALIDATE] Validation completed. Found {len(validation_errors)} errors")
        
        if validation_errors:
            # Return first error for immediate feedback
            error = validation_errors[0]
            logger.error(f"[CFN_VALIDATE] ❌ Validation failed for template {error.template_name}: {error.error_message}")
            return {
                "status": "error",
                "template_name": error.template_name,
                "error_type": error.error_type,
                "error_message": error.error_message,
                "aws_error_code": error.aws_error_code,
                "line_number": error.line_number,
                "suggestions": error.suggestions
            }
        
        # Upload validated templates to S3
        logger.info(f"[CFN_VALIDATE] ✅ All templates passed validation. Uploading to S3...")
        uploaded_files = await s3_manager.upload_multiple_templates(
            chat_id=chat_id,
            templates=templates_dict,
            project_name=project_name,
            validation_status="aws_validated"
        )
        
        logger.info(f"[CFN_VALIDATE] ✅ Successfully validated and uploaded {len(uploaded_files)} templates to S3")
        
        return ValidationResult(
            status="success",
            chat_id=chat_id,
            message=f"Validated and stored {len(uploaded_files)} CloudFormation templates",
            templates_validated=len(uploaded_files),
            files=uploaded_files
        ).model_dump()
        
    except Exception as e:
        # logger.error(f"Error in generate_and_validate_cloudformation_templates: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": f"Internal server error: {str(e)}",
            "suggestions": ["Check server logs for detailed error information", "Retry the operation"]
        }


@mcp.tool(name='generate_cloudformation_templates')
async def generate_cloudformation_templates(
    chat_id: str,
    project_name: str = "CloudFormation Infrastructure"
) -> str:
    """Guide the LLM through CloudFormation template generation workflow.
    
    This tool provides step-by-step instructions for the LLM to follow:
    1. Extract services from recommended_solution variable
    2. Generate templates for each service individually  
    3. Validate and store each template
    4. Provide final summary with links
    
    Args:
        chat_id: Unique chat session identifier
        project_name: Name of the infrastructure project
        
    Returns:
        Detailed workflow instructions for the LLM
    """
    # logger.info(f"CloudFormation template generation workflow started for chat: {chat_id}")
    
    instructions = f"""
# CloudFormation Template Generation Workflow

**Project:** {project_name}  
**Chat ID:** {chat_id}  
**Storage:** Templates will be saved to S3 at `{chat_id}/cloudformation/`

## Step-by-Step Process:

### 1. EXTRACT SERVICES FROM RECOMMENDED_SOLUTION
First, analyze your `recommended_solution` variable and provide a list of all AWS services in this format:
```
Services in recommended_solution:
- Service 1: [Service Name] - [Purpose]
- Service 2: [Service Name] - [Purpose]
- etc.
```

### 2. GENERATE TEMPLATES IN PROPER ORDER (ONE AT A TIME)

**CRITICAL**: Generate templates in this exact order to avoid dependencies:

- If a VPC is required, create the VPC Foundation Template
- Template name: `vpc-network.yaml`
- Include: VPC, Subnets, Internet Gateway, Route Tables, NAT Gateway (if needed)
- Include: Base Security Groups (NO circular references)
- Export all resource IDs for other templates to import

**STEP 2: Service Templates (IN DEPENDENCY ORDER)**
For each service identified above, process them individually:

1. Generate a CloudFormation template using this exact prompt:
   **"Generate the CloudFormation template for [SERVICE_NAME] in recommended_solution"**

2. Template requirements:
   - YAML format only
   - Include only resources for that specific service
   - Use proper CloudFormation syntax with AWSTemplateFormatVersion
   - Include relevant Parameters, Resources, and Outputs sections
   
3. **CRITICAL DESIGN PATTERNS** (to avoid validation errors):
   - **EVALUATE FOR VPC REQUIREMENT**: VPC required when using RDS, Elasticache, or any other VPC-only services; when Lambda needs private network access or access to the internet; and when EC2, EKS or ECS compute resources are used in the solution. VPCs are not required for pure severless architectures such as Lambda + DynamoDB + S3. VPCs are not required when ONLY managed service singleton solutions are designed such as CloudFront or API Gateway, etc.)
   - **NO VPC RESOURCES IN SERVICE TEMPLATES**: Never create VPC, Subnets, IGW, NAT Gateway, Transit Gateway, interface endpoints or gateway endpoints in service templates
   - **USE IMPORTS**: Reference VPC resources using `!ImportValue` from the VPC template exports
   - **NO CIRCULAR DEPENDENCIES**: Don't have resources reference each other within same template
   - **SECURITY GROUP PATTERN**: Create base security groups in VPC template, specific ones in service templates
   - **PARAMETER PATTERN**: Use Parameters for cross-template values, not direct Refs
   - **EXPORT PATTERN**: Every template should export key resource IDs for others to import

4. **TEMPLATE STRUCTURE REQUIREMENTS**:
   - **VPC Template**: Exports VPC ID, Subnet IDs, Security Group IDs, NACL IDs, NAT Gateway ID, Gateway Endpoint IDs, Interface Endpoint IDs, Transit Gateway IDs, Client VPN Connections or Site to Site VPN
   - **Service Templates**: Import VPC resources, create only service-specific resources
   - **Naming Convention**: Use consistent export names like `{project_name}-VPC-ID`, `{project_name}-PrivateSubnet1-ID`

5. Immediately call `validate_and_store_cloudformation_templates` with:
   ```json
   {{
     "chat_id": "{chat_id}",
     "project_name": "{project_name}",
     "infrastructure_description": "CloudFormation template for [SERVICE_NAME]",
     "templates": [
       {{
         "name": "[service-name].yaml",
         "content": "[YAML_CONTENT]"
       }}
     ]
   }}
   ```

6. If validation fails, fix the template and retry immediately (max 15 attempts per template)

7. Only move to the next service when current template is validated and stored

### 3. TEMPLATE GENERATION ORDER EXAMPLE
For a Typical 3 tier web application:
1. `01-vpc-network.yaml` - VPC foundation if required (ALWAYS FIRST)
2. `02-route53.yaml` - Route 53 and DNS foundations
3. `03-s3-buckets.yaml` - S3 buckets (no VPC dependency)  
4. `04-rds-database.yaml` - Database (imports VPC subnets)
5. `05-compute.yaml` - EC2-AutoScalingGroup-Application-Load-Balancer or ECS/EKS/Fargate Container infrastructure (Places compute and ALB in the correct public and private subnets)
6. `06-certificate-manager.yaml` - Certificate Manager (issues certificate for the Application Load Balancer)

For a typical serverless web application:
1. `01-vpc-network.yaml` - VPC foundation if required (ALWAYS FIRST)
2. `02-route53.yaml` - Route 53 and DNS foundations
3. `03-s3-buckets.yaml` - S3 buckets (no VPC dependency)
4. `04-api-gateway.yaml` - API Gateway foundations
5. `05-lambda-functions.yaml` - Lambda functions
6. `06-dynamodb.yaml` - DynamoDB tables
7. `07-cloudfront.yaml` - CloudFront distribution
8. `08-certificate-manager.yaml` - Certificate Manager (issues certificate for the CloudFront distribution)

### 4. FINAL SUMMARY
When all services are processed, provide:
- Total number of templates created
- List of successful templates with clickable S3 links
- Any failed templates and failure reasons
- Overall project status

**Start now by extracting the services from your recommended_solution variable.**
"""
    
    return instructions




@mcp.tool(name='list_cloudformation_templates')
async def list_cloudformation_templates(
    chat_id: str
) -> Dict:
    """List all CloudFormation templates for a specific chat session.
    
    This utility tool provides an overview of all templates associated with a chat session,
    including metadata such as file sizes, validation status, and modification timestamps.
    
    Args:
        chat_id: Chat session identifier
        
    Returns:
        {"status": "success", "chat_id": str, "template_count": int, "templates": [TemplateListItem]}
    """
    try:
        # logger.info(f"Listing CloudFormation templates for chat: {chat_id}")
        
        template_list = await s3_manager.list_templates(chat_id)
        
        result = TemplateListResult(
            status="success",
            chat_id=chat_id,
            template_count=len(template_list),
            templates=template_list
        )
        
        # logger.info(f"Found {len(template_list)} templates for chat {chat_id}")
        
        return result.model_dump()
        
    except Exception as e:
        # logger.error(f"Error in list_cloudformation_templates: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": f"Failed to list templates: {str(e)}",
            "suggestions": ["Check S3 permissions and connectivity"]
        }


@mcp.tool(name='download_cloudformation_template')
async def download_cloudformation_template(
    chat_id: str,
    template_name: str,
    version_id: Optional[str] = None
) -> Dict:
    """Download the content of a specific CloudFormation template.
    
    This utility tool retrieves template content from S3 storage, optionally 
    specifying a particular version if S3 versioning is enabled.
    
    Args:
        chat_id: Chat session identifier
        template_name: Name of the template file to download
        version_id: Optional S3 version ID for retrieving specific version
        
    Returns:
        {"status": "success", "template_name": str, "content": str, "s3_key": str, "size": int}
    """
    try:
        # logger.info(f"Downloading template {template_name} for chat {chat_id}")
        
        content = await s3_manager.download_template(chat_id, template_name, version_id)
        
        # Get template metadata
        s3_key = s3_manager._get_template_s3_key(chat_id, template_name)
        
        result = TemplateDownloadResult(
            status="success",
            template_name=template_name,
            content=content,
            s3_key=s3_key,
            version_id=version_id,
            size=len(content.encode('utf-8'))
        )
        
        # logger.info(f"Successfully downloaded template {template_name} ({result.size} bytes)")
        
        return result.model_dump()
        
    except Exception as e:
        # logger.error(f"Error in download_cloudformation_template: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": f"Failed to download template: {str(e)}",
            "suggestions": [
                "Verify the template name is correct",
                "Check that the template exists for this chat session",
                "Ensure S3 permissions are properly configured"
            ]
        }


def main():
    """Run the CloudFormation Generation MCP server."""
    logger.info("Starting AWS CloudFormation Generation MCP Server")
    
    # Validate S3 access on startup
    if not s3_manager.validate_s3_access():
        logger.warning("S3 access validation failed - some features may not work properly")
    else:
        logger.debug("S3 access validation successful")
    
    logger.info("AWS CloudFormation Generation MCP Server is ready")
    logger.debug("Server starting with stdio transport")
    mcp.run()


if __name__ == '__main__':
    main()
