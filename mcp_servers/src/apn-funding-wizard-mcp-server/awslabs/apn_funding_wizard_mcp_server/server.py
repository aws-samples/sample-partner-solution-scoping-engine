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

from typing import Dict, List, Optional, Any
from pydantic import Field
from mcp.server.fastmcp import FastMCP, Context
import sys
import os
import logging

# Set up logging using shared backend configuration
try:
    # Add backend path to sys.path to import the logger utility
    backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from utils.mcp_logger import setup_mcp_logging
    logger = setup_mcp_logging("apn-funding-wizard-mcp-server")
    logger.info("APN Funding Wizard MCP Server logger initialized using backend configuration")
except ImportError as e:
    # Fallback to basic logging if backend utils not available
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("apn-funding-wizard-mcp-server.log", maxBytes=10*1024*1024, backupCount=5)
        ]
    )
    logger = logging.getLogger("apn-funding-wizard-mcp-server")
    logger.warning(f"Could not import backend logger utility, using fallback logging: {e}")
except Exception as e:
    # Final fallback
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("apn-funding-wizard-mcp-server")
    logger.error(f"Error setting up logging: {e}")

try:
    from .consts import SELL_AND_GROW_DOCS, GETTING_STARTED_DOCS
    from .s3_manager import upload_funding_plan_to_s3, download_funding_plan_from_s3
except ImportError:
    # Fallback for direct execution
    from consts import SELL_AND_GROW_DOCS
    from s3_manager import upload_funding_plan_to_s3, download_funding_plan_from_s3
import json
import time
from datetime import datetime

def detect_isv_scenario(aws_services: str, conversation_context: str = "") -> bool:
    """Detect if this is an ISV scenario based on keywords and context.
    
    Args:
        aws_services: Comma-separated list of AWS services
        conversation_context: Additional context from conversation
    
    Returns:
        True if ISV scenario detected, False otherwise
    """
    combined_text = f"{aws_services} {conversation_context}".lower()
    
    # ISV/Software vendor indicators
    isv_keywords = ['isv', 'saas', 'software vendor', 'application migration', 'software solution', 
                   'software platform', 'multi-tenant', 'hosted solution', 'cloud software']
    
    return any(keyword in combined_text for keyword in isv_keywords)

def detect_spi_flag_from_context(aws_services: str, conversation_context: str = "") -> Optional[str]:
    """Detect SPI flag based on AWS services and conversation context.
    
    Args:
        aws_services: Comma-separated list of AWS services
        conversation_context: Additional context from conversation
    
    Returns:
        SPI flag: 'vmware', 'modernization', 'greenfield', or None
    """
    # Combine services and context for analysis
    combined_text = f"{aws_services} {conversation_context}".lower()
    
    # VMware indicators
    vmware_keywords = ['vmware', 'tanzu', 'vcenter', 'vsphere', 'vcloud']
    if any(keyword in combined_text for keyword in vmware_keywords):
        return 'vmware'
    
    # Modernization indicators  
    modernization_keywords = ['modernization', 'serverless', 'containers', 'microservices', 'kubernetes', 'fargate', 'lambda', 'ecs', 'eks']
    if any(keyword in combined_text for keyword in modernization_keywords):
        return 'modernization'
    
    # Greenfield indicators
    greenfield_keywords = ['greenfield', 'new customer', 'inactive', 'first time', 'never used aws', 'no aws experience']
    if any(keyword in combined_text for keyword in greenfield_keywords):
        return 'greenfield'
    
    return None

# Initialize FastMCP server
mcp = FastMCP(
    "awslabs-apn-funding-wizard-mcp-server",
    instructions="""🎯 AWS PARTNER FUNDING WIZARD - Analyze funding programs and generate professional documents.

    COMPLETE WORKFLOW (ALWAYS follow these steps):
    
    IF YOU ARE UPDATING AN EXISTING FUNDING DOCUMENT:
      - STEP 1: Call read_funding_document with chat_id to get current document content
      - STEP 2: Review the current content and make your required edits
      - STEP 3: Call edit_funding_document with chat_id and your updated document_content
    
    IF CREATING A NEW FUNDING PLAN: 
    1. REQUIRED INFORMATION:
      - Customer Name
      - Partner Name
      - If the customer is a new AWS customer (greenfield)
      - If the end customer is an ISV
      - Will the partner or end customer be listing a solution or SaaS product on AWS Marketplace?
       
       CRITICAL: Never guess, assume, or make up these values. Always ask the user directly if you do not yet have the required information.
       CRITICAL: You are STRICTLY FORBIDDEN from providing ANY funding information, program names, percentages, dollar amounts, or funding references until AFTER you have called get_funding_eligibility with complete required information. ANY mention of funding details before this point is PROHIBITED.
    
    2. For ISV scenarios (keywords: "ISV", "SaaS", "software vendor"), also ask:
       - Is the SaaS solution fully deployed on AWS?
       - Has the ISV completed Foundational Technical Review (FTR)?
       - Is this a persistent workload that runs continuously?
       
       IMPORTANT: ISV Workload Migration Program may provide significant funding based on ARR.
    
    3. Call get_funding_eligibility after gathering all required information. 
    
    4. If the tool returns an error about missing fields, ask the user for the specific missing information.
    
    5. Analyze the funding program data from get_funding_eligibility and create a detailed funding analysis document:
       - Create executive summary with partner/customer details
       - Analyze each eligible program with funding amounts and requirements
       - Provide prioritized recommendations and next steps
       - Include timeline and action items
    
    6. 🚨 MANDATORY: ALWAYS call generate_funding_document with your complete analysis:
       - Pass the full markdown document content you created
       - Include document title, partner names, and chat ID.
       - NEVER put a document date in the document. 
       - This step is REQUIRED for every funding analysis
    
    7. Return to the user:
       - Summary of your funding analysis
       - Display the exact message returned by generate_funding_document (it contains the document link)

    🚨 CRITICAL: Steps 5 and 6 are MANDATORY. Always create and save the funding document.
    """,
    dependencies=[
        'mcp[cli]',
        'loguru',
        'pydantic',
    ],
)

def read_markdown_files(file_paths: List[str]) -> str:
    """Read and concatenate content from markdown files."""
    content = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                doc_name = file_path.split('/')[-1].replace('.md', '')
                content.append(f"\n{'='*60}\n{doc_name}\n{'='*60}\n")
                content.append(file.read())
                content.append("\n\n")
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            content.append(f"\nError: Document '{file_path}' could not be found.\n")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            content.append(f"\nError reading '{file_path}': {str(e)}\n")
    return "".join(content)

@mcp.tool(
    name='get_funding_eligibility',
    description="""Get eligible AWS Partner funding programs based on estimated annual solution cost and AWS services.
    COMPLETE WORKFLOW (ALWAYS follow these steps):
    1. REQUIRED INFORMATION:
      - Customer Name
      - Partner Name
      - If the customer is a new AWS customer (greenfield)
      - If the end customer is an ISV
      - Will the partner or end customer be listing a solution or SaaS product on AWS Marketplace?
       
       CRITICAL: Never guess, assume, or make up these values. Always ask the user directly if you do not yet have the required information.
       CRITICAL: You are STRICTLY FORBIDDEN from providing ANY funding information, program names, percentages, dollar amounts, or funding references until AFTER you have called get_funding_eligibility with complete required information. ANY mention of funding details before this point is PROHIBITED.
    
    2. For ISV scenarios (keywords: "ISV", "SaaS", "software vendor"), also ask:
       - Is the SaaS solution fully deployed on AWS?
       - Has the ISV completed Foundational Technical Review (FTR)?
       - Is this a persistent workload that runs continuously?
       
       IMPORTANT: ISV Workload Migration Program may provide significant funding based on ARR.
    
    3. If the tool returns an error about missing fields, ask the user for the specific missing information.
    
    4. Analyze the funding program data from get_funding_eligibility and create a detailed funding analysis document:
       - Create executive summary with partner/customer details
       - Analyze each eligible program with funding amounts and requirements
       - Provide prioritized recommendations and next steps
       - Include timeline and action items
    
    5. 🚨 MANDATORY: ALWAYS call generate_funding_document with your complete analysis:
       - Pass the full markdown document content you created
       - Include document title, partner names, and chat ID
       - NEVER put a document date in the document
       - This step is REQUIRED for every funding analysis
    
    6. Return to the user:
       - Summary of your funding analysis
       - Display the exact message returned by generate_funding_document (it contains the document link)

    🚨 CRITICAL: Steps 5 and 6 are MANDATORY. Always create and save the funding document."""
)
async def get_funding_eligibility(
    estimated_annual_solution_cost: float = Field(
        description="Annual solution cost in dollars (ARR) - e.g., 6562.0, 45000.0"
    ),
    aws_services: str = Field(
        description="Comma-separated list of AWS services - e.g., 'EC2, RDS, S3'"
    ),
    partner_name: str = Field(
        default=None,
        description="Partner name - REQUIRED: Ask user for AWS Partner name"
    ),
    end_customer_name: str = Field(
        default=None,
        description="End customer name - REQUIRED: Ask user for end customer name"
    ),
    partner_tier: str = Field(
        default=None,
        description="Partner tier level - REQUIRED: Ask user for 'registered', 'validated', 'select', 'advanced', or 'premier'"
    ),
    is_new_customer: bool = Field(
        default=None,
        description="True if new to AWS (Greenfield), False if existing - REQUIRED: Ask user to confirm customer AWS status"
    ),
    spi_flag: Optional[List[str]] = Field(
        default=None,
        description="List of Service Partner Incentive flags that apply: ['vmware'], ['modernization'], ['greenfield'], or combinations like ['greenfield', 'modernization']. Use empty list [] if none apply."
    ),
    isv_flag: Optional[bool] = Field(
        default=None,
        description="True if the end customer is an ISV"
    ),
    isv_saas_on_aws: Optional[bool] = Field(
        default=None,
        description="True if ISV's SaaS solution is fully deployed on AWS (ISV partners only)"
    ),
    isv_ftr_completed: Optional[bool] = Field(
        default=None,
        description="True if ISV has completed Foundational Technical Review (ISV partners only)"
    ),
    isv_persistent_workload: Optional[bool] = Field(
        default=None,
        description="True if ISV workload runs continuously, not bursty/transient (ISV partners only)"
    ),
    marketplace_flag: Optional[bool] = Field(
        default=None,
        description="True if the customer/ISV will list their creation on AWS Marketplace"
    ),
    ctx: Context = None
) -> Dict:
    """Get eligible funding programs based on ARR and return structured data with program documentation."""
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("=== GET_FUNDING_ELIGIBILITY TOOL CALLED ===")
        logger.info(f"Input parameters:")
        logger.info(f"  - estimated_annual_solution_cost: {estimated_annual_solution_cost} (type: {type(estimated_annual_solution_cost)})")
        logger.info(f"  - aws_services: '{aws_services}' (type: {type(aws_services)})")
        logger.info(f"  - partner_name: '{partner_name}' (type: {type(partner_name)})")
        logger.info(f"  - end_customer_name: '{end_customer_name}' (type: {type(end_customer_name)})")
        logger.info(f"  - partner_tier: '{partner_tier}' (type: {type(partner_tier)})")
        logger.info(f"  - is_new_customer: {is_new_customer} (type: {type(is_new_customer)})")
        logger.info(f"  - spi_flag: '{spi_flag}' (type: {type(spi_flag)})")
        logger.info(f"  - isv_saas_on_aws: {isv_saas_on_aws} (type: {type(isv_saas_on_aws)})")
        logger.info(f"  - isv_ftr_completed: {isv_ftr_completed} (type: {type(isv_ftr_completed)})")
        logger.info(f"  - isv_persistent_workload: {isv_persistent_workload} (type: {type(isv_persistent_workload)})")
        
        # Parameter validation and parsing
        if not isinstance(estimated_annual_solution_cost, (int, float)):
            logger.error(f"Invalid ARR type: expected float/int, got {type(estimated_annual_solution_cost)}")
            raise ValueError(f"estimated_annual_solution_cost must be a number, got {type(estimated_annual_solution_cost)}")
        
        # Validate required fields - return structured error if missing
        missing_fields = []
        if partner_name is None or not partner_name.strip():
            missing_fields.append("partner_name")
        if end_customer_name is None or not end_customer_name.strip():
            missing_fields.append("end_customer_name")
        if partner_tier is None or not partner_tier.strip():
            missing_fields.append("partner_tier")
        if is_new_customer is None:
            missing_fields.append("is_new_customer")
            
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return {
                'status': 'error',
                'error_type': 'missing_required_fields',
                'message': f'Missing required information for funding eligibility assessment',
                'missing_fields': missing_fields,
                'required_fields': {
                    'partner_name': 'Partner company name',
                    'end_customer_name': 'End customer company name', 
                    'partner_tier': 'Partner tier level (registered, validated, select, advanced, premier)',
                    'is_new_customer': 'Whether customer is new to AWS (true/false)'
                },
                'action_required': f'Please provide the following information: {", ".join(missing_fields)}'
            }
        
        arr_amount = float(estimated_annual_solution_cost)
        logger.info(f"Parsed ARR amount: ${arr_amount:,.2f}")
        
        # Parse services
        raw_services = aws_services if aws_services else ""
        services = [s.strip().upper() for s in raw_services.split(',') if s.strip()]
        logger.info(f"Parsed AWS services: {services} (count: {len(services)})")
        
        # Auto-detect SPI flags if not provided
        if spi_flag is None or len(spi_flag) == 0:
            detected_spi = detect_spi_flag_from_context(aws_services, "")
            detected_spi_list = [detected_spi] if detected_spi and detected_spi.lower() != 'none' else []
            logger.info(f"Auto-detected SPI flags: {detected_spi_list}")
        else:
            detected_spi_list = [flag for flag in spi_flag if flag and flag.lower() != 'none']
            logger.info(f"Provided SPI flags: {detected_spi_list}")
        
        # Log partner and customer details
        logger.info(f"Partner details: {partner_name} (tier: {partner_tier})")
        logger.info(f"Customer details: {end_customer_name} (new customer: {is_new_customer})")
        logger.info(f"SPI flags: {detected_spi_list}")
        
        eligible_programs = []
        logger.info(f"Starting eligibility evaluation for ${arr_amount:,.0f} ARR...")
        
        # Customer Engagement Incentive (CEI) - DISCONTINUED
        # CEI program has been discontinued and is no longer available for funding eligibility
        logger.info("CEI program discontinued - skipping eligibility check")
        
        # Migration Acceleration Program (MAP)
        # NOTE: Populate with your organization's funding program rules and thresholds
        logger.info(f"Evaluating MAP eligibility for ${arr_amount:,.0f} ARR")
        # Example: Check ARR against minimum threshold for MAP eligibility
        # if arr_amount >= MINIMUM_MAP_THRESHOLD:
        #     eligible_programs.append({"program_name": "MAP", "max_funding": "...", "program_data": "..."})
        logger.info("MAP eligibility check - configure thresholds in your deployment")
        
        # Proof of Concept (POC)
        # NOTE: Populate with your organization's POC funding rules
        logger.info("Evaluating POC eligibility")
        # Example: POC is typically available regardless of ARR
        # eligible_programs.append({"program_name": "POC Funding", "max_funding": "...", "program_data": "..."})
        logger.info("POC eligibility check - configure rules in your deployment")
        
        # ISV Workload Migration Program (WMP)
        # NOTE: Populate with your organization's ISV program rules
        logger.info("Evaluating ISV WMP eligibility")
        isv_scenario_detected = detect_isv_scenario(aws_services, "")
        isv_params_provided = all(param is not None for param in [isv_saas_on_aws, isv_ftr_completed, isv_persistent_workload])
        
        logger.info(f"ISV scenario detected: {isv_scenario_detected}")
        logger.info(f"ISV parameters provided: {isv_params_provided}")
        
        # If ISV scenario detected but parameters missing, ask for clarification first
        if isv_scenario_detected and not isv_params_provided:
            logger.error("Potential ISV scenario detected but missing ISV-specific parameters")
            return {
                'status': 'error',
                'error_type': 'isv_clarification_needed',
                'message': 'Potential ISV scenario detected - clarification needed',
                'detected_keywords': [kw for kw in ['isv', 'saas', 'software vendor', 'application migration', 'software solution', 'software platform', 'multi-tenant', 'hosted solution', 'cloud software'] if kw in f"{aws_services}".lower()],
                'clarification_required': True,
                'action_required': 'FIRST: Ask user to clarify if the partner or customer is an Independent Software Vendor (ISV) that develops and hosts SaaS solutions',
                'clarification_questions': [
                    'Is the partner an Independent Software Vendor (ISV) that develops software solutions?',
                    'Is this about migrating a SaaS application or software platform to AWS?',
                    'Does the partner host software solutions for multiple customers?'
                ],
                'if_isv_confirmed': {
                    'next_step': 'If YES to ISV questions, then ask for ISV-specific qualifications',
                    'required_isv_fields': ['isv_saas_on_aws', 'isv_ftr_completed', 'isv_persistent_workload'],
                    'isv_questions': {
                        'isv_saas_on_aws': 'Is the SaaS solution fully deployed on AWS?',
                        'isv_ftr_completed': 'Has the ISV completed Foundational Technical Review (FTR)?',
                        'isv_persistent_workload': 'Is this a persistent workload that runs continuously (not bursty/transient)?'
                    },
                    'potential_funding': 'ISV WMP funding is based on ARR - configure thresholds in your deployment',
                    'funding_note': 'ISV Workload Migration Program may offer significant funding'
                },
                'if_not_isv': {
                    'next_step': 'If NOT an ISV, proceed with standard funding program evaluation using current parameters'
                }
            }
        
        if isv_params_provided:
            logger.info("ISV parameters provided - evaluating ISV WMP qualification")
            # NOTE: Configure ISV eligibility rules for your deployment
            # Example checks: partner tier, FTR completion, SaaS deployment status, workload type
            # Example: Calculate funding based on ARR percentage tiers
            logger.info("ISV WMP eligibility check - configure rules in your deployment")
        else:
            logger.info("ISV parameters not provided - skipping ISV WMP evaluation")
        
        # Build final result
        total_content_length = sum(len(p["program_data"]) for p in eligible_programs)
        logger.info(f"Total document content: {total_content_length:,} characters across {len(eligible_programs)} programs")
        
        result = {
            'status': 'success',
            'eligible_programs': eligible_programs,
            'message': f'Found {len(eligible_programs)} eligible funding programs'
        }
        
        
        execution_time = time.time() - start_time
        result['generation_time'] = round(execution_time, 2)
        
        logger.info(f"Tool execution completed in {execution_time:.3f} seconds")
        logger.info(f"Returning result with {len(eligible_programs)} programs:")
        for i, program in enumerate(eligible_programs, 1):
            program_data_preview = program['program_data'][:250] + "..." if len(program['program_data']) > 250 else program['program_data']
            logger.info(f"  {i}. {program['program_name']} (max: {program['max_funding']})")
            logger.info(f"     Program data preview (first 250 chars): {program_data_preview}")
        
        logger.info("=== GET_FUNDING_ELIGIBILITY TOOL COMPLETED ===")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error("=" * 80)
        logger.error("=== GET_FUNDING_ELIGIBILITY TOOL ERROR ===")
        logger.error(f"Error after {execution_time:.3f} seconds: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error("=" * 80)
        
        if ctx:
            await ctx.error(f"Error determining eligible programs: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'execution_time': execution_time
        }

@mcp.tool(
    name='generate_funding_document',
    description="""Generate and save a detailed funding document to S3.
    
    This tool takes the LLM's funding analysis content and saves it as a professional document to S3.
    Use this tool after analyzing funding data from get_funding_eligibility.
    
    Returns: JSON with document summary and S3 link."""
)
async def generate_funding_document(
    chat_id: str = Field(..., description="Chat session ID"),
    document_content: str = Field(..., description="Complete funding document content in markdown format created by the LLM"),
    document_title: str = Field(..., description="Document title"),
    partner_name: str = Field(..., description="Partner company name"),
    end_customer_name: str = Field(..., description="End customer company name"),
    ctx: Optional[Context] = None,
) -> str:
    """Save the LLM's funding document content to S3 and return summary with link."""
    start_time = time.time()
    
    try:
        logger.info("=== GENERATE_FUNDING_DOCUMENT TOOL CALLED ===")
        logger.info(f"Saving document: {document_title}")
        logger.info(f"Content length: {len(document_content)} characters")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"funding_recommendations_{timestamp}"
        
        # Upload to S3
        s3_result = await upload_funding_plan_to_s3(
            chat_id=chat_id,
            plan_content=document_content,
            filename=filename,
            format='markdown'
        )
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Create response
        if s3_result and s3_result.get('s3_url'):
            # Embed document link directly in message like cost-analysis server does
            message_with_link = f"Funding document saved successfully for {partner_name} & {end_customer_name}\n\n---\n**📊 [View funding analysis document]({s3_result['s3_url']})**"
            
            response_data = {
                "status": "success",
                "chat_id": chat_id,
                "message": message_with_link,
                "document_title": document_title,
                "s3_bucket": s3_result.get("bucket"),
                "s3_url": s3_result['s3_url'],
                "s3_key": s3_result['s3_key'],
                "s3_file_version_id": s3_result.get('version_id'),
                "file_size": s3_result.get('file_size', len(document_content.encode('utf-8'))),
                "metadata_key": s3_result.get('metadata_key'),
                "filename": filename,
                "format": "markdown",
                "generation_time": round(generation_time, 2)
            }
        else:
            response_data = {
                "status": "error",
                "chat_id": chat_id,
                "message": "Failed to upload funding document to S3",
                "generation_time": round(generation_time, 2),
                "error_details": "S3 upload failed or returned no result"
            }
        
        logger.info(f"Document upload completed in {generation_time:.3f} seconds")
        logger.info(f"S3 URL: {s3_result.get('s3_url') if s3_result else 'Failed'}")
        
        return json.dumps(response_data)
        
    except Exception as e:
        logger.error(f"Error saving funding document: {e}", exc_info=True)
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "message": f"Failed to save funding document: {str(e)}",
            "error_details": str(e),
            "generation_time": round(time.time() - start_time, 2)
        }
        return json.dumps(error_response)


@mcp.tool(
    name='read_funding_document',
    description="""Read the funding document from S3.
    
    This tool retrieves the funding document content from s3bucket/<chat_id>/funding/funding_plan.md.
    Only requires the chat_id parameter - the filename and location are predefined.
    
    Returns: Current document content and metadata."""
)
async def read_funding_document(
    chat_id: str = Field(..., description="Chat session ID"),
    ctx: Optional[Context] = None,
) -> str:
    """Read a funding document from S3."""
    start_time = time.time()
    
    try:
        logger.info(f"READ-DOCUMENT: Reading funding document for chat {chat_id[:50]}")
        
        # Read the existing document from S3 (always use markdown format and funding_plan filename)
        existing_content = await download_funding_plan_from_s3(
            chat_id=chat_id,
            filename="funding_plan",
            format="markdown",
            version_id=None
        )
        
        execution_time = time.time() - start_time
        logger.info(f"READ-DOCUMENT: Successfully read document ({len(existing_content)} characters)")
        
        response_data = {
            "status": "success",
            "chat_id": chat_id,
            "filename": "funding_plan",
            "format": "markdown",
            "document_content": existing_content,
            "content_length": len(existing_content),
            "execution_time": round(execution_time, 2),
            "message": "Funding document retrieved successfully. You can now review and edit the content."
        }
        
        return json.dumps(response_data)
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"READ-DOCUMENT: Failed to read document: {str(e)[:100]}")
        
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "message": f"Could not read funding document: {str(e)}",
            "error_details": str(e),
            "execution_time": round(execution_time, 2),
            "suggestion": "Document may not exist yet. Create a new funding document first using generate_funding_document tool."
        }
        return json.dumps(error_response)

@mcp.tool(
    name='edit_funding_document',
    description="""Save updated funding document content to S3.
    
    Use this tool to save your edited version of a funding document after you have reviewed the current content
    using read_funding_document. This will overwrite the existing document (S3 versioning preserves history).
    
    Returns: S3 location and update confirmation."""
)
async def edit_funding_document(
    chat_id: str = Field(..., description="Chat session ID"),
    document_content: str = Field(..., description="Updated document content to save"),
    ctx: Optional[Context] = None,
) -> str:
    """Save updated funding document to S3."""
    start_time = time.time()
    
    try:
        logger.info(f"EDIT-DOCUMENT: Saving updated funding document for chat {chat_id[:50]}")
        logger.info(f"EDIT-DOCUMENT: Content length: {len(document_content)} characters")
        
        # Upload the updated document to S3 (overwrite existing, S3 versioning handles history)
        s3_result = await upload_funding_plan_to_s3(
            chat_id=chat_id,
            plan_content=document_content,
            filename="funding_plan",
            format="markdown"
        )
        
        execution_time = time.time() - start_time
        logger.info(f"EDIT-DOCUMENT: S3 upload completed in {execution_time:.3f}s")
        
        # Create response
        if s3_result and s3_result.get('s3_url'):
            # Embed document link directly in message
            message_with_link = f"Funding document updated successfully\n\n---\n**📊 [View updated funding document]({s3_result['s3_url']})**"
            
            response_data = {
                "status": "success",
                "chat_id": chat_id,
                "message": message_with_link,
                "filename": "funding_plan",
                "format": "markdown",
                "s3_bucket": s3_result.get("bucket"),
                "s3_url": s3_result['s3_url'],
                "s3_key": s3_result['s3_key'],
                "s3_file_version_id": s3_result.get('version_id'),
                "file_size": s3_result.get('file_size', len(document_content.encode('utf-8'))),
                "metadata_key": s3_result.get('metadata_key'),
                "execution_time": round(execution_time, 2)
            }
            logger.info(f"EDIT-DOCUMENT: Update successful, version: {s3_result.get('version_id')}")
        else:
            response_data = {
                "status": "error",
                "chat_id": chat_id,
                "message": "Failed to update funding document in S3",
                "execution_time": round(execution_time, 2),
                "error_details": "S3 upload failed or returned no result"
            }
            logger.error(f"EDIT-DOCUMENT: S3 upload failed")
        
        return json.dumps(response_data)
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"EDIT-DOCUMENT: Failed to save document: {str(e)[:100]}")
        
        error_response = {
            "status": "error",
            "chat_id": chat_id,
            "message": f"Failed to update funding document: {str(e)}",
            "error_details": str(e),
            "execution_time": round(execution_time, 2)
        }
        return json.dumps(error_response)

def main():
    """Run the MCP server."""
    logger.info("Starting APN Funding Wizard MCP Server")
    logger.debug("Server starting with stdio transport")
    mcp.run()

if __name__ == "__main__":
    main()