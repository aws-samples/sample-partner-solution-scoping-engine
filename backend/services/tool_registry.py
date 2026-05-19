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

"""
Registry of MCP tools organized by intent.
"""

# Map of intents to relevant tool names
TOOL_SETS = {
    "diagram": [
        "generate_diagram",
        "get_diagram_examples",
        "list_icons"
    ],
    "documentation": [
        "read_documentation",
        "search_documentation",
        "recommend"
    ],
    "cost": [
        "get_pricing_from_web",
        "get_pricing_from_api",
        "generate_cost_report"
    ],
    "funding": [
        "get_funding_eligibility",
        "generate_funding_document",
        "read_funding_document",
        "edit_funding_document"
    ],
    "poc_funding_review": [
        "analyze_poc_funding_request_urls"
    ],
    # Add other tool sets as needed
}

def get_tools_for_intent(intent):
    """
    Get the list of tool names for a specific intent.
    
    Args:
        intent (str): The detected intent
        
    Returns:
        list: List of tool names relevant to the intent
    """
    tools = TOOL_SETS.get(intent, [])
    
    # Add logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"TOOL_REGISTRY: Intent '{intent}' mapped to tools: {tools}")
    
    if not tools:
        logger.warning(f"TOOL_REGISTRY: No tools found for intent '{intent}'. Available intents: {list(TOOL_SETS.keys())}")
    
    return tools

def validate_poc_funding_tools(available_tools):
    """
    Validate that POC funding tools are available in the MCP server.
    
    Args:
        available_tools (list): List of available tool dictionaries from MCP servers
        
    Returns:
        bool: True if POC funding tools are available
    """
    import logging
    logger = logging.getLogger(__name__)
    
    required_poc_tools = TOOL_SETS.get("poc_funding_review", [])
    available_tool_names = [tool.get('toolSpec', {}).get('name') for tool in available_tools if tool.get('toolSpec')]
    
    missing_tools = [tool for tool in required_poc_tools if tool not in available_tool_names]
    
    if missing_tools:
        logger.error(f"POC_FUNDING_VALIDATION: Missing required POC funding tools: {missing_tools}")
        logger.error(f"POC_FUNDING_VALIDATION: Available tools: {available_tool_names}")
        return False
    else:
        logger.info(f"POC_FUNDING_VALIDATION: All required POC funding tools are available: {required_poc_tools}")
        return True
