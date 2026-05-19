#!/usr/bin/env python3
"""AWS Pricing Calculator Instructions Generator MCP Server"""

import json
import logging
import os
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from .service_lookup import ServiceDefinitionTool
from .calc_instructions import generate_calculator_instructions

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("pricing-calculator-mcp-server")


@mcp.tool()
def get_service_definition(service_name: str) -> str:
    """
    Retrieve detailed pricing definition for a single AWS service.
    
    Args:
        service_name: AWS service name (e.g., 'Amazon S3', 'AWS Lambda', 'Amazon EC2')
    
    Returns:
        JSON string containing service definition
    """
    try:
        tool = ServiceDefinitionTool()
        definitions = tool.get_service_definitions([service_name])
        if not definitions:
            return f"No definition found for: {service_name}"
        return json.dumps(definitions, indent=2)
    except Exception as e:
        logger.error(f"Error getting service definition: {str(e)}")
        return f"Error retrieving definition for {service_name}: {str(e)}"


@mcp.tool()
def generate_pricing_calculator_instructions(services: List[Dict[str, Any]]) -> str:
    """
    Generate Nova ACT instructions for AWS Pricing Calculator from service definitions.
    
    Args:
        services: Array of service configuration objects. Each service object must include:
                 - service: AWS service name (e.g., "Amazon S3", "AWS Lambda")
                 - Additional configuration fields with specific values for pricing calculation
                 
    Returns:
        JSON string containing Nova ACT instructions for the backend API
    """
    try:
        if not services:
            return json.dumps({"error": "No services provided"})
        
        # Convert services to JSON string
        content = json.dumps({"services": services})
        
        # Generate Nova Act instructions
        result = generate_calculator_instructions(content)
        instructions = result.get('nova_act_instructions', {})
        
        if isinstance(instructions, str):
            instructions = json.loads(instructions)
        
        if not instructions.get('actions'):
            return json.dumps({"error": "Failed to generate Nova Act instructions"})
        
        # Return instructions for the backend API to execute
        return json.dumps({
            "instructions": instructions,
            "services_count": len(services),
            "actions_count": len(instructions.get('actions', []))
        })
        
    except Exception as e:
        logger.error(f"Error generating pricing calculator instructions: {str(e)}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def create_pricing_calculator_link(metadata: Dict[str, Any] = None) -> str:
    """
    Generate a job ID and execution plan for creating the pricing calculator link.
    The actual Nova ACT execution happens in the backend service.
    
    Args:
        metadata: Optional metadata (e.g., chat_id)
        
    Returns:
        JSON string containing Job ID and execution plan
    """
    try:
        chat_id = metadata.get('chat_id', 'unknown') if metadata else 'unknown'
        
        # Return job info for the backend to process
        return json.dumps({
            "job_id": f"pricing_calc_{chat_id}",
            "execution_plan": "Will execute accumulated pricing calculator instructions and generate public link",
            "status": "ready_to_execute"
        })
        
    except Exception as e:
        logger.error(f"Error creating pricing calculator link: {str(e)}")
        return json.dumps({"error": str(e)})


def main():
    """Run the MCP server."""
    logger.info("Starting Pricing Calculator Instructions Generator MCP Server")
    mcp.run()


if __name__ == '__main__':
    main()
