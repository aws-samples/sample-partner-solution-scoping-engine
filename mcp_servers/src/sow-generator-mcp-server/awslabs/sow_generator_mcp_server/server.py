# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""AWS Labs MCP SOW Generator server implementation.

This server provides tools for generating Statement of Work (SOW) documents with
professional formatting, cost calculations, and S3 storage with versioning.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .models import (
    SOWGenerationResult,
    SOWTemplateType,
)
from .config_utils import get_sera_config
from .docx_generator import generate_sow_docx
from .s3_manager import upload_sow_to_s3, upload_html_to_s3, download_html_from_s3, download_text_from_s3, download_binary_from_s3
from .template_engine import render_sow_template, render_sow_template_simple

# Set up logging using shared backend configuration
try:
    # Add backend path to sys.path to import the logger utility
    backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from utils.mcp_logger import setup_mcp_logging
    logger = setup_mcp_logging("sow-generator-mcp-server")
    logger.info("SOW Generator MCP Server logger initialized using backend configuration")
except ImportError as e:
    # Fallback to basic logging if backend utils not available
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("sow-generator-mcp-server.log", maxBytes=10*1024*1024, backupCount=5)
        ]
    )
    logger = logging.getLogger("sow-generator-mcp-server")
    logger.warning(f"Could not import backend logger utility, using fallback logging: {e}")
except Exception as e:
    # Final fallback
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("sow-generator-mcp-server")
    logger.error(f"Error setting up logging: {e}")

# Debug startup
logger.info("=" * 50)
logger.info("SOW GENERATOR MCP SERVER STARTING UP")
logger.info("=" * 50)


async def collect_chat_appendices(chat_id: str) -> Dict[str, Any]:
    """Scan S3 for existing documents that can be appendices.
    
    Args:
        chat_id: Chat session ID
        
    Returns:
        Dictionary containing appendices data with content loaded
    """
    print(f"COLLECT_APPENDICES CALLED: chat_id={chat_id}", file=sys.stdout)
    appendices = {
        "diagram": {
            "title": "Architecture Diagram",
            "s3_url": None,
            "s3_key": None,
            "content": None,
            "description": "AWS architecture diagram for the proposed solution"
        },
        "pricing_report": {
            "title": "Cost Analysis Report",
            "s3_url": None,
            "s3_key": None,
            "content": None,
            "description": "Detailed AWS cost analysis and pricing breakdown"
        },
        "funding_document": {
            "title": "AWS Partner Funding Analysis",
            "s3_url": None,
            "s3_key": None,
            "content": None,
            "description": "Available AWS partner funding programs and recommendations"
        }
    }
    
    # Get S3 bucket from SERA config
    try:
        sera_config = get_sera_config()
        if not sera_config:
            logger.warning("SERA config not available for appendices collection")
            return appendices
            
        # Try to get S3 bucket name from CustomerConfig
        try:
            # Calculate the correct path to backend from MCP server location
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_path = os.path.join(current_dir, '..', '..', '..', '..', '..', 'backend')
            sys.path.append(backend_path)
            # Import after path modification
            from config.app_config import CustomerConfig
            
            # Load configuration if not already loaded
            if not CustomerConfig._config:
                CustomerConfig.load_config()
                
            bucket_name = CustomerConfig.get_sow_s3_bucket()
            
        except Exception as e:
            logger.warning(f"Could not get S3 bucket from CustomerConfig: {e}")
            bucket_name = os.getenv("S3_UPLOAD_BUCKET")
            
        if not bucket_name:
            logger.warning("No S3 bucket configured for appendices")
            return appendices
            
        # Check for specific file paths according to user requirements
        
        # 1. Architecture diagram: {bucket}/{chat_id}/diagram/diagram.png
        diagram_key = f"{chat_id}/diagram/diagram.png"
        try:
            diagram_content = await download_binary_from_s3(diagram_key)
            if diagram_content:
                appendices["diagram"]["s3_url"] = f"s3://{bucket_name}/{diagram_key}"
                appendices["diagram"]["s3_key"] = diagram_key
                appendices["diagram"]["content"] = diagram_content
                logger.info(f"Found architecture diagram: {diagram_key}")
        except Exception as e:
            logger.debug(f"No diagram found at {diagram_key}: {e}")
        
        # 2. Pricing report: {bucket}/{chat_id}/pricing/pricing.md
        pricing_key = f"{chat_id}/pricing/pricing.md"
        try:
            pricing_content = await download_text_from_s3(pricing_key)
            if pricing_content:
                appendices["pricing_report"]["s3_url"] = f"s3://{bucket_name}/{pricing_key}"
                appendices["pricing_report"]["s3_key"] = pricing_key
                appendices["pricing_report"]["content"] = pricing_content
                logger.info(f"Found pricing report: {pricing_key}")
        except Exception as e:
            logger.debug(f"No pricing report found at {pricing_key}: {e}")
        
        # 3. Funding document: {bucket}/{chat_id}/funding/funding_plan.md
        funding_key = f"{chat_id}/funding/funding_plan.md"
        try:
            funding_content = await download_text_from_s3(funding_key)
            if funding_content:
                appendices["funding_document"]["s3_url"] = f"s3://{bucket_name}/{funding_key}"
                appendices["funding_document"]["s3_key"] = funding_key
                appendices["funding_document"]["content"] = funding_content
                logger.info(f"Found funding document: {funding_key}")
        except Exception as e:
            logger.debug(f"No funding document found at {funding_key}: {e}")
            
    except Exception as e:
        logger.error(f"Error collecting appendices: {e}", exc_info=True)
    
    # Log summary
    found_appendices = [key for key, data in appendices.items() if data["content"] is not None]
    logger.info(f"Collected {len(found_appendices)} appendices for chat {chat_id}: {found_appendices}")
    
    return appendices

print("IMPORTING COMPLETE - CREATING FASTMCP INSTANCE...", file=sys.stdout)

mcp = FastMCP(
    name='awslabs.sow-generator-mcp-server',
    instructions="""🎯 STATEMENT OF WORK DOCX DOCUMENT GENERATOR 🎯

    This server EXCLUSIVELY creates formal business SOW documents in DOCX format.

    WORKFLOW:
    1. MUST use generate_sow_document tool ONLY - this tool automatically loads personnel data and template types internally for your reference in your analysis
    2. After tool execution, provide brief summary of the document.""",
    dependencies=['pydantic', 'boto3', 'jinja2', 'markdown2', 'python-docx'],
)

print("FASTMCP INSTANCE CREATED SUCCESSFULLY", file=sys.stdout)

@mcp.tool(
    name='generate_sow_document',
    description="""STATEMENT OF WORK DOCX GENERATOR - Creates formal business SOW documents in DOCX format.

    🎯 USE THIS TOOL WHEN: User requests SOW, Statement of Work, project proposal, or consulting agreement document.

    ⚠️ CRITICAL: This tool generates ACTUAL DOCX DOCUMENTS, not text content. After calling this tool, 
    provide ONLY a brief summary confirming the SOW DOCX was generated and where it was saved. 
    Do NOT write additional SOW content in the chat.

    ✅ INTEGRATED FEATURES:
    - Provides available technical personnel data (roles, rates, hours per sprint)
    - Provides available template types (aws_map, aws_modernization, standard_migration)
    - Returns this reference data in the response for your use

    WORKFLOW: 
    REQUIRED INFORMATION:
      - Customer Name
      - Partner Name      
    CRITICAL: Never guess, assume, or make up these values. Always ask the user directly if you do not yet have the required information.
    CRITICAL: You are STRICTLY FORBIDDEN from using the generate_sow_document unless you can provide the end cusomter name and partner name.
    MUST:
      - Perform an analysis of the conversation to extract a project executive summary.
      - Perform an analysis of recommended_solution to extract a summary of the AWS infrastructure to be deployed.
      - Peform an analysis of the conversation and recommended_solution to extract the objective of the project.
      - ALWAYS Perform a security-focused analysis of the conversation to extract:
        - Current Security Pain Points: What security issues is the customer experiencing?
        - Compliance Requirements: What regulatory or data residency requirements exist?
        - Threat Mitigation: What potential vulnerabilities should be considered in recommended_solution?
        - Security Architecture: What security controls must be implemented in recommended_solution?
        - Security Validation: How will security improvements be tested and verified?
        - The number of security sprint required for a Security Architect in the project.
      - Peform an analysis of the conversation and recommended_solution to extract the project management requirements of the project as a whole.
      - Peform an analysis of the conversation and recommended_solution to extract the individual deliverables that are required to complete the project as a whole.
      - Peform an analysis of the conversation and recommended_solution to extract the specific software development needs of the project.
      - Peform an analysis of the conversation and recommended_solution to extract the realistic timeline with milestones to complete all deliverables and complete the project.
      - Peform an analysis of the conversation and recommended_solution to extract any exclusions from the project scope that may be required.
      - Peform an analysis of the conversation and recommended_solution to extract the realistic acceptance critera that should be used by the customer to verify project completion.
      - Peform an analysis of the conversation and recommended_solution to extract the assumptions that are to be used in evaluating the scope of work.
      - Determine the template type to use for the SOW document based on the funding summary (if available) and the available Statement Of Work templates. If there is no funding summary, use the "standard migration" template. IMPORTANT: IF THERE IS NO FUNDING SUMMARY, DO NOT MAKE ONE UP OR CREATE A DEFAULT FUNDING SUMMARY. ASSUME THERE IS NO AWS FUNDING FOR THE PROJECT TO BE TAKEN INTO CONSIDERATION.
      - Based on the recommended_solution, and your analysis of the complexity iof the migration or workload creation:
          - Peform an analysis of the conversation and recommended_solution to extract the technical personnel that are required to complete the project.
          - Always include Security Architect tasks in the project scope.
          - Determine a REALISTIC amount of sprints for each required personnel. 
          - CRITICAL: THIS SHOULD BE REALISTIC BASED ON THE AWS SERVICES IN THE SOLUTION. For example:
            - Do not select a data scientist or data analyst if there is no data complexity (multiple data sources) or if there is no machine learning in the project. 
            - Do not select a software development engineer if there is no actual software development work required. If unclear, as the user clarifying questions. DO NOT CONTINUE UNTIL THIS IS CLEAR.
            - Do not select DevOps engineer if there is no actual DevOps work required. If unsure, ask the user clarifying questions. DO NOT CONTINUE UNTIL THIS IS CLEAR.

    Returns: JSON with S3 location, file size, and generation details.""",
)
async def generate_sow_document(
    chat_id: str = Field(..., description="REQUIRED: Use the current chat session ID exactly as provided - do not create a custom ID"),
    partner_name: str = Field(
        default=None,
        description="Partner name - REQUIRED: Ask user for partner name"
    ),
    customer_name: str = Field(
        default=None,
        description="End customer name - REQUIRED: Ask user for end customer name"
    ),
    project_title: Optional[str] = Field(
        default=None, 
        description="Title of the project - REQUIRED"
    ),
    solution_description: Optional[str] = Field(
        default=None, 
        description="A description of the AWS Solution - REQUIRED"
    ),
    executive_summary: Optional[str] = Field(
        default=None, 
        description="Project executive summary - REQUIRED"
    ),
    project_objective: Optional[str] = Field(
        default=None, 
        description="Project objective - REQUIRED"
    ),
    project_timeline: Optional[Union[str, List[Dict]]] = Field(
        default=None, 
        description="JSON string or list containing timeline phases with names, durations, and descriptions - REQUIRED"
    ),
    project_personnel: Optional[Union[str, List[Dict]]] = Field(
        default=None, 
        description="JSON string or list containing personnel with roles, personnel names, hours_per_sprint, and responsibilities - REQUIRED"
    ),
    project_deliverables: Optional[Union[str, List[Dict]]] = Field(
        default=None, 
        description="JSON string or list containing deliverables with names and descriptions - REQUIRED"
    ),
    template_type: Optional[str] = Field(
        default=None,
        description="Type of SOW template to use (aws_map, aws_modernization, standard_migration) - REQUIRED"
    ),
    project_assumptions: Optional[Union[str, List[str]]] = Field(
        default=None, 
        description="JSON string or list containing project assumptions"
    ),
    project_exclusions: Optional[Union[str, List[str]]] = Field(
        default=None, 
        description="JSON string or list containing project exclusions"
    ),
    ctx: Optional[Context] = None,
) -> str:
    """Generate a complete SOW document and upload to S3."""
    start_time = time.time()
    
    # Debug tool call
    print("=" * 80, file=sys.stdout)
    print("=== GENERATE_SOW_DOCUMENT TOOL CALLED ===", file=sys.stdout)
    print(f"CHAT_ID: {chat_id}", file=sys.stdout)
    print(f"PARTNER_NAME: {partner_name}", file=sys.stdout) 
    print(f"CUSTOMER_NAME: {customer_name}", file=sys.stdout)
    print("=" * 80, file=sys.stdout)
    
    try:
        logger.info("=" * 80)
        logger.info("=== GENERATE_SOW_DOCUMENT TOOL CALLED ===")
        
        # STEP 1: Get available personnel data
        logger.info("STEP 1: Loading available personnel data...")
        try:
            sera_config = get_sera_config()
            available_personnel = sera_config.get('SOW_CONFIG', {}).get('technical_personnel', {})
            logger.info(f"Loaded {len(available_personnel)} personnel roles from configuration")
        except Exception as e:
            logger.error(f"Failed to load personnel data: {e}")
            if ctx:
                await ctx.error(f"Failed to load personnel data: {str(e)}")
            return json.dumps({
                'status': 'error',
                'message': f'Failed to load personnel data: {str(e)}',
                'generation_time': round(time.time() - start_time, 2)
            })
        
        # STEP 2: Get available template types
        logger.info("STEP 2: Loading available template types...")
        try:
            template_types = sera_config.get('SOW_CONFIG', {}).get('template_types', {})
            logger.info(f"Loaded {len(template_types)} template types")
        except Exception as e:
            logger.error(f"Failed to load template types: {e}")
            template_types = {
                "aws_map": {"name": "AWS MAP Assessment SOW", "description": "For AWS Migration Acceleration Program assessments"},
                "aws_modernization": {"name": "AWS Modernization SOW", "description": "For application modernization projects"},
                "standard_migration": {"name": "Standard Migration SOW", "description": "For standard migration projects"}
            }
            logger.warning("Using fallback template types")
        
        # STEP 3: Get terms and conditions
        logger.info("STEP 3: Loading terms and conditions...")
        try:
            terms_and_conditions = sera_config.get('SOW_CONFIG', {}).get('terms_and_conditions', {})
            logger.info(f"Loaded {len(terms_and_conditions)} terms and conditions sections")
        except Exception as e:
            logger.error(f"Failed to load terms and conditions: {e}")
            terms_and_conditions = {
                "payment_and_execution": "Payment terms and execution conditions to be defined.",
                "liability_and_confidentiality": "Liability and confidentiality terms to be defined."
            }
            logger.warning("Using fallback terms and conditions")
        
        logger.info(f"Input parameters:")
        logger.info(f"  - chat_id: '{chat_id}'")
        logger.info(f"  - partner_name: '{partner_name}'")
        logger.info(f"  - customer_name: '{customer_name}'")
        logger.info(f"  - project_title: '{project_title}'")
        logger.info(f"  - template_type: '{template_type}'")
        logger.info(f"  - solution_description: '{solution_description}'")
        logger.info(f"  - executive_summary: '{executive_summary}'")
        logger.info(f"  - project_objective: '{project_objective}'")
        logger.info(f"  - project_timeline: {project_timeline}")
        logger.info(f"  - project_personnel: {project_personnel}")
        logger.info(f"  - project_deliverables: {project_deliverables}")
        logger.info(f"  - project_assumptions: {project_assumptions}")
        logger.info(f"  - project_exclusions: {project_exclusions}")
        logger.info(f"SOW_DEBUG: Raw personnel type: {type(project_personnel)}")
        logger.info(f"TIMELINE-CHANGE: Raw timeline type: {type(project_timeline)}")
        logger.info(f"TIMELINE-CHANGE: Raw timeline content: {project_timeline}")
        logger.info(f"SOW_DEBUG: Raw deliverables type: {type(project_deliverables)}")
        
        # Validate required fields - return structured error if missing
        missing_fields = []
        if not partner_name or not partner_name.strip():
            missing_fields.append("partner_name")
        if not customer_name or not customer_name.strip():
            missing_fields.append("customer_name")
        if not project_title or not project_title.strip():
            missing_fields.append("project_title")
        if not executive_summary or not executive_summary.strip():
            missing_fields.append("executive_summary")
        if not project_objective or not project_objective.strip():
            missing_fields.append("project_objective")
        if not project_timeline:
            missing_fields.append("project_timeline")
        if not project_personnel:
            missing_fields.append("project_personnel")
        if not project_deliverables:
            missing_fields.append("project_deliverables")
        if not template_type or not template_type.strip():
            missing_fields.append("template_type")
            
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            
            # Log the personnel data we're about to return
            logger.info(f"SOW_DEBUG: available_personnel keys being returned: {list(available_personnel.keys())}")
            logger.info(f"SOW_DEBUG: template_types keys being returned: {list(template_types.keys())}")
            
            # Log each role with its rate to see what we're actually returning
            for role, data in available_personnel.items():
                logger.info(f"SOW_DEBUG: Returning role '{role}' with rate ${data.get('hourly_rate', 0)}/hour")
            
            # Log the complete error response
            error_response = {
                'status': 'error',
                'error_type': 'missing_required_fields',
                'message': 'Missing required information for SOW generation',
                'missing_fields': missing_fields,
                'required_fields': {
                    'partner_name': 'Partner company name',
                    'customer_name': 'End customer company name',
                    'project_title': 'Project title',
                    'executive_summary': 'Project executive summary',
                    'project_objective': 'Project objective',
                    'project_timeline': 'Project timeline and milestones',
                    'project_personnel': 'Project personnel data',
                    'project_deliverables': 'Project deliverables',
                    'template_type': 'Template type (aws_map, aws_modernization, standard_migration)'
                },
                'action_required': f'Please provide the following information: {", ".join(missing_fields)}',
                
                # Include reference data for LLM to make informed selections
                'available_personnel_data': available_personnel,
                'available_template_types': template_types,
                'terms_and_conditions': terms_and_conditions
            }
            
            logger.info(f"SOW_DEBUG: Complete error response JSON length: {len(json.dumps(error_response))} characters")
            
            return json.dumps(error_response)
        
        # Get SERA configuration first
        sera_config = get_sera_config()
        if not sera_config:
            logger.error("SERA configuration not available")
            return json.dumps({
                'status': 'error',
                'error_type': 'configuration_error',
                'message': 'SERA configuration not available',
                'action_required': 'Please check SERA configuration system'
            })
        
        # Validate template type against config (no fallbacks - use actual config data)
        valid_templates = list(template_types.keys())
        logger.info(f"SOW_DEBUG: Valid templates from config: {valid_templates}")
        
        if template_type not in valid_templates:
            logger.error(f"Invalid template type: {template_type}")
            return json.dumps({
                'status': 'error',
                'error_type': 'invalid_template_type',
                'message': f'Invalid template type: {template_type}',
                'invalid_template': template_type,
                'valid_templates': valid_templates,
                'available_personnel_data': available_personnel,
                'available_template_types': template_types,
                'terms_and_conditions': terms_and_conditions,
                'action_required': f'Please use only valid template types from available_template_types. Invalid template: {template_type}'
            })
        
        # Parse and validate personnel data
        try:
            if isinstance(project_personnel, str):
                personnel_data = json.loads(project_personnel)
            else:
                personnel_data = project_personnel
            
            logger.info(f"SOW_DEBUG: Parsed personnel data: {personnel_data}")
            logger.info(f"SOW_DEBUG: Personnel data type: {type(personnel_data)}")
            
            if not isinstance(personnel_data, list) or len(personnel_data) == 0:
                raise ValueError("Personnel data must be a non-empty list")
            
            # Validate personnel structure and roles against available config
            valid_roles = list(available_personnel.keys())
            logger.info(f"SOW_DEBUG: Valid roles from config: {valid_roles}")
            
            invalid_roles = []
            for i, person in enumerate(personnel_data):
                required_keys = ['role', 'hours_per_sprint']
                missing_keys = [key for key in required_keys if key not in person]
                if missing_keys:
                    raise ValueError(f"Personnel item {i} missing required keys: {missing_keys}")
                
                # Check if role exists in available personnel
                if person['role'] not in valid_roles:
                    invalid_roles.append(person['role'])
            
            # If invalid roles found, return error with valid options
            if invalid_roles:
                logger.error(f"Invalid personnel roles provided: {invalid_roles}")
                return json.dumps({
                    'status': 'error',
                    'error_type': 'invalid_personnel_roles',
                    'message': f'Invalid personnel roles provided: {invalid_roles}',
                    'invalid_roles': invalid_roles,
                    'valid_roles': valid_roles,
                    'available_personnel_data': available_personnel,
                    'available_template_types': template_types,
                    'terms_and_conditions': terms_and_conditions,
                    'action_required': f'Please use only valid roles from available_personnel_data. Invalid roles: {invalid_roles}'
                })
                    
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Invalid personnel data: {e}")
            return json.dumps({
                'status': 'error',
                'error_type': 'invalid_personnel_data',
                'message': f'Invalid personnel data format: {str(e)}',
                'available_personnel_data': available_personnel,
                'available_template_types': template_types,
                'terms_and_conditions': terms_and_conditions,
                'expected_format': 'List of objects with role, hours_per_sprint, and optional name/responsibilities',
                'action_required': 'Please provide valid personnel data using roles from available_personnel_data'
            })
        
        # Parse and validate deliverables data
        try:
            if isinstance(project_deliverables, str):
                deliverables_data = json.loads(project_deliverables)
            else:
                deliverables_data = project_deliverables
            
            if not isinstance(deliverables_data, list) or len(deliverables_data) == 0:
                raise ValueError("Deliverables data must be a non-empty list")
            
            # Validate deliverables structure
            for i, deliverable in enumerate(deliverables_data):
                required_keys = ['name', 'description']
                missing_keys = [key for key in required_keys if key not in deliverable]
                if missing_keys:
                    raise ValueError(f"Deliverable item {i} missing required keys: {missing_keys}")
                    
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Invalid deliverables data: {e}")
            return json.dumps({
                'status': 'error',
                'error_type': 'invalid_deliverables_data',
                'message': f'Invalid deliverables data format: {str(e)}',
                'expected_format': 'List of objects with name and description',
                'action_required': 'Please provide valid deliverables data in the correct format'
            })
        
        # sera_config already loaded above
        
        # Create personnel dictionaries by merging LLM selections with config data
        personnel_dicts = []
        for p in personnel_data:
            # Get the full personnel data from config
            config_personnel = available_personnel[p['role']]
            
            # Handle different field names from LLM - use LLM provided or fall back to config
            name = p.get('name') or p.get('personnel_name') or config_personnel.get('name', 'TBD')
            
            # For responsibilities, prefer LLM custom responsibilities, otherwise use config
            llm_responsibility = p.get('responsibility') or p.get('responsibilities', '')
            if llm_responsibility:
                # If LLM provided custom responsibilities, use them
                if isinstance(llm_responsibility, list):
                    responsibility = '; '.join(llm_responsibility)
                else:
                    responsibility = llm_responsibility
            else:
                # Fall back to config responsibilities
                config_responsibilities = config_personnel.get('responsibilities', [])
                if isinstance(config_responsibilities, list):
                    responsibility = '; '.join(config_responsibilities)
                else:
                    responsibility = config_responsibilities
            
            # Calculate totals
            hours_per_sprint = p['hours_per_sprint']
            total_sprints = 3
            total_hours = hours_per_sprint * total_sprints
            hourly_rate = config_personnel.get('hourly_rate', 0.0)
            cost_per_sprint = hourly_rate * hours_per_sprint
            total_cost = hourly_rate * total_hours
            
            logger.info(f"SOW_DEBUG: Merging personnel {p['role']}: LLM hours={hours_per_sprint}, config_rate=${hourly_rate}")
                
            personnel_dicts.append({
                'role': p['role'],
                'name': name,
                'responsibility': responsibility,
                'hours_per_sprint': hours_per_sprint,
                'total_sprints': total_sprints,
                'total_hours': total_hours,
                'hourly_rate': hourly_rate,
                'cost_per_sprint': cost_per_sprint,
                'total_cost': total_cost
            })
        
        # Convert deliverables to simple dictionaries
        deliverables = [{
            'name': d['name'],
            'description': d['description']
        } for d in deliverables_data]
        
        # Parse and validate timeline data
        try:
            logger.info(f"TIMELINE-CHANGE: Starting timeline parsing...")
            if isinstance(project_timeline, str):
                logger.info(f"TIMELINE-CHANGE: Parsing timeline from string")
                timeline_data = json.loads(project_timeline)
            else:
                logger.info(f"TIMELINE-CHANGE: Using timeline as-is (not string)")
                timeline_data = project_timeline
            
            logger.info(f"TIMELINE-CHANGE: Parsed timeline data: {timeline_data}")
            logger.info(f"TIMELINE-CHANGE: Timeline data type: {type(timeline_data)}")
            
            if not isinstance(timeline_data, list) or len(timeline_data) == 0:
                raise ValueError("Timeline data must be a non-empty list")
            
            # Validate timeline structure
            for i, timeline_item in enumerate(timeline_data):
                logger.info(f"TIMELINE-CHANGE: Validating timeline item {i}: {timeline_item}")
                required_keys = ['name', 'duration', 'description']
                missing_keys = [key for key in required_keys if key not in timeline_item]
                if missing_keys:
                    raise ValueError(f"Timeline item {i} missing required keys: {missing_keys}")
            
            logger.info(f"TIMELINE-CHANGE: Timeline validation successful - {len(timeline_data)} items")
                    
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"TIMELINE-CHANGE: Invalid timeline data: {e}")
            return json.dumps({
                'status': 'error',
                'error_type': 'invalid_timeline_data',
                'message': f'Invalid timeline data format: {str(e)}',
                'expected_format': 'List of objects with name, duration, and description',
                'example': [
                    {
                        "name": "Assessment and Architecture Design", 
                        "duration": "weeks 1-2",
                        "description": "Current state analysis and AWS architecture design"
                    },
                    {
                        "name": "Infrastructure Setup",
                        "duration": "weeks 3-4", 
                        "description": "AWS environment deployment and configuration"
                    }
                ],
                'action_required': 'Please provide timeline data in the correct structured format'
            })

        # STEP 4: Collect appendices from S3
        logger.info("STEP 4: Collecting appendices from S3...")
        try:
            appendices = await collect_chat_appendices(chat_id)
            logger.info(f"Collected appendices: {[key for key, data in appendices.items() if data['content'] is not None]}")
        except Exception as e:
            logger.warning(f"Failed to collect appendices: {e}")
            # Don't fail SOW generation if appendices collection fails
            appendices = {
                "diagram": {"title": "Architecture Diagram", "s3_url": None, "content": None},
                "pricing_report": {"title": "Cost Analysis Report", "s3_url": None, "content": None},
                "funding_document": {"title": "AWS Partner Funding Analysis", "s3_url": None, "content": None}
            }

        # Create SOW metadata as dictionary
        metadata = {
            'chat_id': chat_id,
            'customer_name': customer_name,
            'project_title': project_title,
            'project_description': executive_summary,
            'project_objective': project_objective,
            'project_timeline': timeline_data,
            'template_type': template_type,
            'partner_name': partner_name,
            'effective_date': datetime.now()
        }
        
        # Parse assumptions and exclusions - handle both JSON strings and native lists
        assumptions_list = []
        if project_assumptions:
            try:
                if isinstance(project_assumptions, str):
                    assumptions_data = json.loads(project_assumptions)
                else:
                    assumptions_data = project_assumptions
                
                if isinstance(assumptions_data, list):
                    assumptions_list = [str(a).strip() for a in assumptions_data if str(a).strip()]
                else:
                    # Fallback to CSV parsing for backward compatibility
                    assumptions_list = [a.strip() for a in str(assumptions_data).split(',') if a.strip()]
                    
            except (json.JSONDecodeError, TypeError):
                # Fallback to CSV parsing for backward compatibility
                assumptions_list = [a.strip() for a in str(project_assumptions).split(',') if a.strip()]
        
        exclusions_list = []
        if project_exclusions:
            try:
                if isinstance(project_exclusions, str):
                    exclusions_data = json.loads(project_exclusions)
                else:
                    exclusions_data = project_exclusions
                
                if isinstance(exclusions_data, list):
                    exclusions_list = [str(e).strip() for e in exclusions_data if str(e).strip()]
                else:
                    # Fallback to CSV parsing for backward compatibility
                    exclusions_list = [e.strip() for e in str(exclusions_data).split(',') if e.strip()]
                    
            except (json.JSONDecodeError, TypeError):
                # Fallback to CSV parsing for backward compatibility
                exclusions_list = [e.strip() for e in str(project_exclusions).split(',') if e.strip()]
        
        logger.info(f"SOW_DEBUG: Parsed assumptions count: {len(assumptions_list)}")
        logger.info(f"SOW_DEBUG: Parsed assumptions: {assumptions_list}")
        logger.info(f"SOW_DEBUG: Parsed exclusions count: {len(exclusions_list)}")
        logger.info(f"SOW_DEBUG: Parsed exclusions: {exclusions_list}")
        
        # Calculate total project costs from personnel dicts
        total_per_sprint = sum(person['cost_per_sprint'] for person in personnel_dicts)
        total_project_team_costs = sum(person['total_cost'] for person in personnel_dicts)
        
        logger.info(f"SOW_DEBUG: Total per sprint: ${total_per_sprint}, Total project costs: ${total_project_team_costs}")
        
        # Create simplified data structure for template
        logger.info(f"TIMELINE-CHANGE: Adding timeline_data to sow_data: {timeline_data}")
        sow_data = {
            # Metadata
            "chat_id": chat_id,
            "customer_name": customer_name,
            "partner_name": partner_name,
            "project_title": project_title,
            "project_description": solution_description,
            "executive_summary": executive_summary,
            "project_objective": project_objective,
            "template_type": template_type,
            "effective_date": metadata['effective_date'],
            
            # Personnel and costs (no model objects - raw dicts)
            "personnel": personnel_dicts,
            "deliverables": deliverables,
            "assumptions": assumptions_list,
            "exclusions": exclusions_list,
            "project_timeline": timeline_data,
            
            # Terms and conditions from config
            "terms_and_conditions": terms_and_conditions,
            
            # Cost calculations
            "total_per_sprint": total_per_sprint,
            "total_project_team_costs": total_project_team_costs,
            "total_sprints": 3,
            "project_duration_weeks": 6,
            "sprint_duration_weeks": 2,
            
            # Appendices with content
            "appendices": appendices,
        }
        
        # Generate HTML content from template using simplified approach
        html_content = await render_sow_template_simple(sow_data)
        
        # Generate DOCX from HTML
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
            docx_path = temp_docx.name
        
        await generate_sow_docx(html_content, docx_path, None)
        
        # Upload both HTML and DOCX to S3
        html_result = await upload_html_to_s3(chat_id, html_content)
        s3_result = await upload_sow_to_s3(chat_id, docx_path)
        
        # Store SOW metadata in DynamoDB chat item
        await store_sow_metadata_in_dynamodb(chat_id, {
            'customer_name': customer_name,
            'project_title': project_title,
            'template_type': metadata['template_type'],
            's3_url': s3_result['s3_url'],
            's3_key': s3_result['s3_key'],
            'html_s3_url': html_result['s3_url'],
            'html_s3_key': html_result['s3_key'],
            'version_id': s3_result.get('version_id'),
            'html_version_id': html_result.get('version_id'),
            'file_size': s3_result.get('file_size', 0),
            'html_file_size': html_result.get('file_size', 0),
            'generation_time': round(time.time() - start_time, 2),
            'generated_date': datetime.now().isoformat(),
            'status': 'generated'
        })
        
        # Clean up temporary file
        os.unlink(docx_path)
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Get file size
        file_size = s3_result.get('file_size', 0)
        
        # Always return structured JSON response
        if s3_result and s3_result.get('s3_url'):
            response_data = {
                "status": "success",
                "chat_id": chat_id,
                "message": f"SOW document generated successfully for {customer_name}",
                "s3_bucket": s3_result.get("bucket"),
                "s3_url": s3_result['s3_url'],
                "s3_key": s3_result['s3_key'],
                "s3_file_version_id": s3_result.get('version_id'),
                "file_size": file_size,
                "metadata_key": f"{s3_result['s3_key']}.metadata.json",
                "generation_time": round(generation_time, 2),
                
                # Include reference data for LLM context
                "available_personnel_data": available_personnel,
                "available_template_types": template_types,
                "terms_and_conditions": terms_and_conditions,
                "used_template_type": template_type,
                "project_details": {
                    "customer_name": customer_name,
                    "partner_name": partner_name,
                    "project_title": project_title,
                    "executive_summary": executive_summary,
                    "project_objective": project_objective,
                    "selected_personnel": personnel_dicts,
                    "deliverables": deliverables,
                    "timeline": timeline_data,
                    "assumptions": assumptions_list,
                    "exclusions": exclusions_list,
                    "total_project_team_costs": total_project_team_costs,
                    "total_per_sprint": total_per_sprint
                }
            }
        else:
            # Fallback when S3 upload fails
            response_data = {
                "status": "error",
                "chat_id": chat_id,
                "message": "SOW document generated but S3 upload failed",
                "generation_time": round(generation_time, 2),
                "error_details": "S3 upload failed or returned no result"
            }
        
        return json.dumps(response_data)
        
    except Exception as e:
        logger.error(f"Error generating SOW document: {e}", exc_info=True)
        # Return JSON error response
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "message": f"Failed to generate SOW document: {str(e)}",
            "error_details": str(e),
            "generation_time": round(time.time() - start_time, 2)
        }
        return json.dumps(error_response)


async def calculate_sow_costs(
    personnel_json: Union[str, List[Dict]] = Field(..., description="JSON string or list containing personnel with roles and hours_per_sprint"),
    custom_rates_json: Optional[str] = Field(None, description="Optional JSON string of custom hourly rates by role"),
    sprint_count: int = Field(3, description="Number of sprints in the project", ge=1),
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """Calculate SOW project costs."""
    try:
        # Parse personnel JSON - handle both string and object formats
        try:
            if isinstance(personnel_json, str):
                personnel_data = json.loads(personnel_json)
            else:
                personnel_data = personnel_json
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return {
                "status": "error",
                "message": f"Invalid personnel format: {str(e)}",
                "error_details": "Personnel must be valid JSON array or list with role and hours_per_sprint fields"
            }
        
        # Parse custom rates if provided, otherwise use SERA config defaults
        if custom_rates_json:
            try:
                rates_data = json.loads(custom_rates_json)
                labor_rates = rates_data
            except (json.JSONDecodeError, ValueError) as e:
                return {
                    "status": "error",
                    "message": f"Invalid custom rates JSON format: {str(e)}",
                    "error_details": "Custom rates must be valid JSON object"
                }
        else:
            # Use SERA configuration for default rates
            sera_config = get_sera_config()
            if sera_config and sera_config.get('SOW_CONFIG', {}).get('technical_personnel'):
                # Extract rates from personnel config
                personnel_config = sera_config['SOW_CONFIG']['technical_personnel']
                labor_rates = {role: data.get('hourly_rate', 0.0) for role, data in personnel_config.items()}
            else:
                labor_rates = {}  # Empty rates dict if no config
        
        # Calculate costs
        cost_breakdown = []
        total_cost = 0.0
        total_hours = 0
        
        for person_data in personnel_data:
            # Validate person data structure
            if not isinstance(person_data, dict) or 'role' not in person_data or 'hours_per_sprint' not in person_data:
                return {
                    "status": "error",
                    "message": "Invalid personnel data structure",
                    "error_details": "Each person must have 'role' and 'hours_per_sprint' fields"
                }
            
            role = person_data['role']
            hours_per_sprint = person_data['hours_per_sprint']
            name = person_data.get('name', 'TBD')
            
            # Calculate totals
            total_hours_person = hours_per_sprint * sprint_count
            rate = labor_rates.get(role, 0.0)
            person_cost = rate * total_hours_person
            cost_per_sprint = rate * hours_per_sprint
            
            cost_breakdown.append({
                "role": role,
                "name": name,
                "hourly_rate": rate,
                "hours_per_sprint": hours_per_sprint,
                "total_hours": total_hours_person,
                "total_cost": person_cost,
                "cost_per_sprint": cost_per_sprint
            })
            
            total_cost += person_cost
            total_hours += total_hours_person
        
        return {
            "status": "success",
            "cost_breakdown": cost_breakdown,
            "summary": {
                "total_labor_cost": total_cost,
                "total_hours": total_hours,
                "average_hourly_rate": total_cost / total_hours if total_hours > 0 else 0,
                "cost_per_sprint": total_cost / sprint_count if sprint_count > 0 else 0,
                "sprint_count": sprint_count
            },
            "standard_rates": labor_rates
        }
        
    except Exception as e:
        logger.error(f"Error calculating SOW costs: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to calculate costs: {str(e)}",
            "error_details": str(e)
        }


@mcp.tool(
    name='get_sow_templates',
    description="Get information about available SOW templates and their use cases.",
)
async def get_sow_templates(ctx: Optional[Context] = None) -> Dict[str, Any]:
    """Get available SOW templates from SERA configuration."""
    sera_config = get_sera_config()
    
    # Use SERA templates if available, otherwise use defaults
    if sera_config and sera_config.get('templates'):
        templates = sera_config['templates']
        # Add additional metadata for templates
        for template_key, template_config in templates.items():
            if template_key == 'aws_map':
                template_config.update({
                    "use_case": "Azure to AWS migration projects, cloud assessments",
                    "key_deliverables": [
                        "Business Case & TCO Analysis",
                        "Cloud Maturity Assessment Report",
                        "Migration & Modernization Pattern Analysis",
                        "Workload Migration Assessment",
                        "Executive Readout"
                    ]
                })
            elif template_key == 'aws_modernization':
                template_config.update({
                    "use_case": "AWS application modernization and cloud-native transformation",
                    "key_deliverables": [
                        "Current State Assessment",
                        "AWS Cloud-Native Architecture Design",
                        "Modernization Plan",
                        "Security and Compliance Review"
                    ]
                })
            elif template_key == 'custom':
                template_config.update({
                    "use_case": "Custom projects, multi-cloud, specialty consulting",
                    "key_deliverables": [
                        "Project-specific deliverables",
                        "Custom analysis and recommendations"
                    ]
                })
    else:
        # Fallback to default templates
        templates = {
            "aws_map": {
                "name": "AWS MAP Assessment SOW",
                "description": "Template for AWS Migration Acceleration Program assessments",
                "use_case": "Azure to AWS migration projects, cloud assessments",
                "default_duration_weeks": 6,
                "default_sprints": 3,
                "key_deliverables": [
                    "Business Case & TCO Analysis",
                    "Cloud Maturity Assessment Report",
                    "Migration & Modernization Pattern Analysis",
                    "Workload Migration Assessment",
                    "Executive Readout"
                ]
            },
            "aws_modernization": {
                "name": "AWS Modernization SOW",
                "description": "Template for AWS application modernization and cloud-native transformation projects",
                "use_case": "AWS application modernization and cloud-native transformation",
                "default_duration_weeks": 8,
                "default_sprints": 4,
                "key_deliverables": [
                    "Current State Assessment",
                    "AWS Cloud-Native Architecture Design",
                    "Modernization Plan",
                    "Security and Compliance Review"
                ]
            },
            "custom": {
                "name": "Custom Project SOW",
                "description": "Flexible template for custom consulting engagements",
                "use_case": "Custom projects, multi-cloud, specialty consulting",
                "default_duration_weeks": 4,
                "default_sprints": 2,
                "key_deliverables": [
                    "Project-specific deliverables",
                    "Custom analysis and recommendations"
                ]
            }
        }
    
    # Get labor rates from SERA config
    if sera_config and sera_config.get('SOW_CONFIG', {}).get('technical_personnel'):
        # Extract rates from personnel config
        personnel_config = sera_config['SOW_CONFIG']['technical_personnel']
        default_rates = {role: data.get('hourly_rate', 0.0) for role, data in personnel_config.items()}
        standard_roles = list(personnel_config.keys())
    else:
        default_rates = {}
        standard_roles = []
    
    return {
        "templates": templates,
        "standard_roles": standard_roles,
        "default_rates": default_rates,
        "sera_config_loaded": sera_config is not None
    }


async def store_sow_metadata_in_dynamodb(chat_id: str, sow_metadata: Dict[str, Any]):
    """Store SOW metadata in the DynamoDB chat item.
    
    Args:
        chat_id: Chat session ID
        sow_metadata: SOW metadata to store
    """
    try:
        # Get SERA configuration
        config = get_sera_config()
        if not config:
            logger.warning("SERA config not available, skipping DynamoDB metadata storage")
            return
            
        table_name = config.get('DYNAMODB_TABLE_NAME')
        aws_region = config.get('AWS_REGION', 'us-east-1')
        
        if not table_name:
            logger.warning("DynamoDB table name not configured, skipping metadata storage")
            return
            
        # Create DynamoDB client
        dynamodb = boto3.client('dynamodb', region_name=aws_region)
        
        # Prepare the metadata as DynamoDB attributes
        metadata_attr = {
            'M': {
                'status': {'S': sow_metadata['status']},
                'generated_date': {'S': sow_metadata['generated_date']},
                'customer_name': {'S': sow_metadata['customer_name']},
                'project_title': {'S': sow_metadata['project_title']},
                'template_type': {'S': sow_metadata['template_type']},
                's3_url': {'S': sow_metadata['s3_url']},
                's3_key': {'S': sow_metadata['s3_key']},
                'file_size': {'N': str(sow_metadata['file_size'])},
                'generation_time': {'N': str(sow_metadata['generation_time'])}
            }
        }
        
        # Add version_id if present
        if sow_metadata.get('version_id'):
            metadata_attr['M']['version_id'] = {'S': sow_metadata['version_id']}
        
        # Update the chat item with SOW metadata
        # We need to find the chat item by chat_id first
        # Scan for the item with the matching chat_id
        scan_response = dynamodb.scan(
            TableName=table_name,
            FilterExpression='chat_id = :chat_id',
            ExpressionAttributeValues={
                ':chat_id': {'S': chat_id}
            },
            Limit=1
        )
        
        items = scan_response.get('Items', [])
        if not items:
            logger.warning(f"No chat found with chat_id: {chat_id}")
            return
            
        chat_item = items[0]
        user_id = chat_item['user_id']['S']
        timestamp = chat_item['timestamp']['S']
        
        # Update the item with SOW metadata
        dynamodb.update_item(
            TableName=table_name,
            Key={
                'user_id': {'S': user_id},
                'timestamp': {'S': timestamp}
            },
            UpdateExpression='SET sow_metadata = :metadata',
            ExpressionAttributeValues={
                ':metadata': metadata_attr
            }
        )
        
        logger.info(f"Successfully stored SOW metadata in DynamoDB for chat_id: {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to store SOW metadata in DynamoDB: {e}", exc_info=True)
        # Don't fail the SOW generation if metadata storage fails
        

@mcp.tool(
    name='read_sow_document',
    description="""Read the existing SOW content from S3.
    
    This tool retrieves the source used to generate the SOW document from S3.
    Use this before making SOW document modifications to get the current content.
    
    Returns: Current SOW content and metadata."""
)
async def read_sow_document(
    chat_id: str = Field(..., description="Chat session ID"),
    ctx: Optional[Context] = None,
) -> str:
    """Read SOW Document content from S3."""
    start_time = time.time()
    
    try:
        logger.info(f"Reading SOW document for chat {chat_id}")
        
        html_content = await download_html_from_s3(chat_id)
        
        execution_time = time.time() - start_time
        
        response_data = {
            "status": "success",
            "chat_id": chat_id,
            "html_content": html_content,
            "content_length": len(html_content),
            "execution_time": round(execution_time, 2),
            "message": "SOW content retrieved successfully. You can now review and modify the content."
        }
        
        return json.dumps(response_data)
        
    except Exception as e:
        logger.error(f"Failed to read SOW for chat {chat_id}: {e}")
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "error": str(e),
            "message": "Failed to retrieve SOW content. The document may not exist yet."
        }
        return json.dumps(error_response)


@mcp.tool(
    name='modify_sow_document',
    description="""Modify an existing SOW document by updating the source content.
    
    This tool takes modified HTML content, generates a new DOCX from it, and saves both to S3.
    Use read_sow_document first to get the current content, then modify it and use this tool.
    
    Returns: Updated document information and S3 URLs."""
)
async def modify_sow_document(
    chat_id: str = Field(..., description="Chat session ID"),
    modified_html: str = Field(..., description="Modified content for the SOW"),
    modification_notes: str = Field(default="", description="Optional notes about what was modified"),
    ctx: Optional[Context] = None,
) -> str:
    """Modify existing SOW document with new content."""
    start_time = time.time()
    
    try:
        logger.info(f"Modifying SOW document for chat {chat_id}")
        
        # Generate DOCX from modified HTML
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
            docx_path = temp_docx.name
        
        await generate_sow_docx(modified_html, docx_path, None)
        
        # Upload both HTML and DOCX to S3
        html_result = await upload_html_to_s3(chat_id, modified_html)
        s3_result = await upload_sow_to_s3(chat_id, docx_path)
        
        # Update SOW metadata in DynamoDB
        await store_sow_metadata_in_dynamodb(chat_id, {
            'template_type': 'modified',
            's3_url': s3_result['s3_url'],
            's3_key': s3_result['s3_key'],
            'html_s3_url': html_result['s3_url'],
            'html_s3_key': html_result['s3_key'],
            'version_id': s3_result.get('version_id'),
            'html_version_id': html_result.get('version_id'),
            'file_size': s3_result.get('file_size', 0),
            'html_file_size': html_result.get('file_size', 0),
            'modification_notes': modification_notes,
            'modified_date': datetime.now().isoformat(),
            'status': 'modified'
        })
        
        # Clean up temporary file
        os.unlink(docx_path)
        
        execution_time = time.time() - start_time
        
        response_data = {
            "status": "success",
            "chat_id": chat_id,
            "message": f"SOW document modified successfully",
            "s3_bucket": s3_result.get("bucket"),
            "s3_url": s3_result['s3_url'],
            "s3_key": s3_result['s3_key'],
            "html_s3_url": html_result['s3_url'],
            "html_s3_key": html_result['s3_key'],
            "file_size": s3_result.get('file_size', 0),
            "metadata_key": f"{s3_result['s3_key']}.metadata.json",
            "modification_notes": modification_notes,
            "execution_time": round(execution_time, 2)
        }
        
        return json.dumps(response_data)
        
    except Exception as e:
        logger.error(f"Failed to modify SOW document for chat {chat_id}: {e}")
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "error": str(e),
            "message": "Failed to modify SOW document"
        }
        return json.dumps(error_response)


def main():
    """Run the MCP server with CLI argument support."""
    logger.info("Starting SOW Generator MCP Server")
    logger.debug("Main function called")
    
    parser = argparse.ArgumentParser(description='Generate professional SOW documents')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()
    
    logger.debug(f"Server arguments - SSE: {args.sse}, Port: {args.port}")

    # Run server with appropriate transport
    if args.sse:
        logger.info(f"Starting server with SSE transport on port {args.port}")
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        logger.info("Starting server with stdio transport")
        mcp.run()


if __name__ == '__main__':
    logger.info("SOW Generator Server main starting")
    main()