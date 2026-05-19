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

"""AWS Service Validation MCP Server implementation.

This server provides tools for validating AWS services and finding current alternatives
for deprecated or invalid services.
"""

import argparse
import boto3
import logging
import os
import sys
import re
import uuid
from bs4 import BeautifulSoup
from botocore.exceptions import UnknownServiceError, NoCredentialsError
from httpx import AsyncClient
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

# Set up logging to write to backend.log
import logging
from logging.handlers import RotatingFileHandler

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Configure logging to write to backend.log - CRITICAL: Use stderr for MCP compatibility
log_file = os.path.join(backend_path, "backend.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Use stderr instead of stdout for MCP compatibility
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)
logger.info("***SERVICE-VALIDATION-SERVER-USE*** AWS Service Validation MCP Server logger initialized")

# Initialize FastMCP server
mcp = FastMCP("AWS Service Validation", dependencies=["boto3", "botocore", "httpx", "beautifulsoup4"])

instructions = """AWS Service Validation tool - use this workflow to validate aws services that you are considering recommending or discussing with a user BEFORE including them in your recommendation.

WORKFLOW: 
CRITICAL: BEFORE RECOMMENDING A SOLUTION TO A USER, OR DISCUSSING ANY SINGLE SERVICE WITH A USER:
    - Use validate_aws_services tool and specify the service name in list format 
    - If status = "deprecated": DO NOT USE THIS SERVICE IN THE IDEA OR SOLUTION. Use search_aws_documentation tool for replacement service, then use the read_aws_documentation tool to get the data you need about the service to make an accurate recommendation.
    - If status = "invalid": DO NOT USE THIS SERVICE IN THE IDEA OR SOLUTION. Use search_aws_documentation tool for correct service name, then use the read_aws_documentation tool to get the data you need about the service to make an accurate recommendation.
    - If status = "valid" you may use the service in your recommendation; be aware of new features that should be researched if the feature is used in your recommendation.
"""

def load_service_validations():
    """Load service validation rules from backend configuration."""
    try:
        logger.info("***SERVICE-VALIDATION-SERVER-USE*** Loading service validations from backend config")
        from config.app_config import CustomerConfig
        CustomerConfig.load_config()
        validations = CustomerConfig.get_aws_service_validations()
        logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Loaded validations: {validations}")
        return validations
    except Exception as e:
        logger.error(f"***SERVICE-VALIDATION-SERVER-USE*** Could not load service validations from config: {e}")
        return {}

def find_replacement_service(service_name, validations):
    """Find if a service is deprecated by checking if it's in any 'replaces' list."""
    logger.debug(f"***SERVICE-VALIDATION-SERVER-USE*** Checking if '{service_name}' is in any 'replaces' list")
    for replacement_service, config in validations.items():
        replaces_list = config.get('replaces', [])
        logger.debug(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{replacement_service}' replaces: {replaces_list}")
        if service_name in replaces_list:
            logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Found '{service_name}' is replaced by '{replacement_service}'")
            return replacement_service, config
    logger.debug(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{service_name}' not found in any 'replaces' list")
    return None, None

def has_new_features(service_name, validations):
    """Check if a service has new features that require documentation search."""
    config = validations.get(service_name, {})
    features = config.get('has_new_features', [])
    has_features = bool(features)
    logger.debug(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{service_name}' has new features: {has_features}, features: {features}")
    return has_features

# Load service validations from backend config
SERVICE_VALIDATIONS = load_service_validations()

class ServiceValidationResult(BaseModel):
    """Result of AWS service validation."""
    service: str = Field(description="The service name that was validated")
    status: str = Field(description="Status: valid, deprecated, or invalid")
    exists_in_boto3: bool = Field(description="Whether service exists in boto3")
    exists_in_available_list: bool = Field(description="Whether service is in available services list")
    action_required: Optional[str] = Field(description="Required action for deprecated/invalid services")
    alternatives: Optional[List[str]] = Field(description="Alternative services if deprecated")

def validate_service_boto3(service_name: str) -> bool:
    """Check if service exists in boto3."""
    try:
        # Import here to avoid circular imports
        from config.app_config import CustomerConfig
        CustomerConfig.load_config()
        region = CustomerConfig.get_aws_region()
        boto3.client(service_name, region_name=region)
        return True
    except UnknownServiceError:
        return False

def is_service_available(service_name: str) -> bool:
    """Check if service is in boto3 available services."""
    try:
        session = boto3.session.Session()
        return service_name in session.get_available_services()
    except:
        return False

async def search_aws_for_alternatives(service_name: str) -> Optional[str]:
    """Search AWS documentation for service alternatives."""
    try:
        # Search AWS documentation for the service
        search_terms = [
            f"{service_name} AWS service",
            f"{service_name} alternative AWS",
            f"AWS {service_name} replacement"
        ]
        
        for search_term in search_terms:
            # Try AWS documentation search
            search_url = f"https://docs.aws.amazon.com/search/doc-search.html?searchPath=documentation&searchQuery={search_term.replace(' ', '+')}"
            
            async with AsyncClient() as client:
                try:
                    response = await client.get(search_url, follow_redirects=True, timeout=10.0)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for service links in search results
                        service_links = []
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            if '/aws-services/' in href or '/products/' in href:
                                text = link.get_text(strip=True)
                                if text and len(text) > 5:
                                    service_links.append(text)
                        
                        if service_links:
                            return f"Found potential alternatives: {', '.join(service_links[:3])}"
                            
                except Exception as e:
                    logger.debug(f"Search attempt failed for {search_term}: {e}")
                    continue
        
        return f"Use search_aws_documentation tool to search for '{service_name}'"
        
    except Exception as e:
        logger.error(f"Error searching for alternatives: {e}")
        return f"Unable to search for alternatives: {str(e)}"

@mcp.tool(
    name='get_available_aws_services',
    description="""Get list of all available AWS services from boto3.
    
    Returns a comprehensive list of all AWS services that are currently available
    through the boto3 SDK. Useful for checking what services are supported.
    """
)
async def get_available_aws_services(ctx: Context) -> Dict[str, Any]:
    """Get list of all available AWS services."""
    
    logger.info("Getting available AWS services")
    
    try:
        session = boto3.session.Session()
        services = sorted(session.get_available_services())
        
        result = {
            "total_services": len(services),
            "services": services,
            "status": "success"
        }
        
        logger.info(f"Retrieved {len(services)} available services")
        return result
        
    except Exception as e:
        logger.error(f"Error getting available services: {e}")
        return {
            "total_services": 0,
            "services": [],
            "status": "error",
            "error": str(e)
        }

@mcp.tool(
    name='validate_aws_services',
    description="""Validate AWS services and get current status with alternatives if deprecated.
    
    Validates one or more AWS service names against boto3 and provides status information.
    For deprecated services, provides replacement alternatives and migration guidance.
    For invalid services, provides suggestions to search documentation.
    
    Args:
        service_names: List of AWS service names to validate (e.g., ["lambda"] or ["s3", "ec2", "lambda"])
    
    Returns:
        Dictionary with validation results for each service including status, suggestions, and alternatives.
    """
)
async def validate_aws_services(service_names: List[str], ctx: Context) -> Dict[str, Any]:
    """Validate multiple AWS services at once."""
    
    logger.info(f"Validating {len(service_names)} services")
    
    results = {}
    
    for service_name in service_names:
        try:
            logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Starting validation for service: '{service_name}'")
            
            # Clean up service name
            clean_service_name = service_name.strip().lower()
            logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Cleaned service name: '{clean_service_name}'")
            
            # Check if service exists using multiple methods
            boto3_exists = validate_service_boto3(clean_service_name)
            available_exists = is_service_available(clean_service_name)
            logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' - boto3_exists: {boto3_exists}, available_exists: {available_exists}")
            
            # Determine status and suggestions
            if boto3_exists and available_exists:
                logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' exists in both boto3 and available list")
                # Valid service - check if it has new features requiring doc search
                if has_new_features(clean_service_name, SERVICE_VALIDATIONS):
                    config = SERVICE_VALIDATIONS[clean_service_name]
                    features = ', '.join(config['has_new_features'])
                    status = "valid"
                    action_required = f"{clean_service_name} has new features: {features}. Use search_aws_documentation tool to search for \"{clean_service_name}\" for latest information."
                    alternatives = None
                    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' has new features, suggesting doc search")
                else:
                    status = "valid"
                    action_required = None
                    alternatives = None
                    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' is valid with no special requirements")
            elif boto3_exists or available_exists:
                status = "valid"
                action_required = None
                alternatives = None
                logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' exists in one validation method, marking as valid")
            else:
                logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' does not exist in boto3 or available list")
                # Service doesn't exist - check if it's deprecated
                replacement_service, replacement_config = find_replacement_service(clean_service_name, SERVICE_VALIDATIONS)
                if replacement_service:
                    status = "deprecated"
                    action_required = f"{clean_service_name} is deprecated. Use {replacement_service} instead. Use search_aws_documentation tool to search for \"{replacement_service}\" for service information, then use read_aws_documentation for description of the service"
                    alternatives = [replacement_service]
                    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' is deprecated, replacement: '{replacement_service}'")
                else:
                    status = "invalid"
                    action_required = await search_aws_for_alternatives(clean_service_name)
                    alternatives = None
                    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Service '{clean_service_name}' is invalid, searching for alternatives")
            
            results[service_name] = {
                'service': clean_service_name,
                'status': status,
                'exists_in_boto3': boto3_exists,
                'exists_in_available_list': available_exists,
                'action_required': action_required,
                'alternatives': alternatives
            }
            
            logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Final result for '{clean_service_name}': status={status}, action_required='{action_required}', alternatives={alternatives}")
            
        except Exception as e:
            logger.error(f"***SERVICE-VALIDATION-SERVER-USE*** Error validating {service_name}: {e}")
            results[service_name] = {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    summary = {
        "total_validated": len(service_names),
        "valid_services": len([r for r in results.values() if r.get('status') == 'valid']),
        "deprecated_services": len([r for r in results.values() if r.get('status') == 'deprecated']),
        "invalid_services": len([r for r in results.values() if r.get('status') == 'invalid']),
        "results": results
    }
    
    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Validation complete: {summary['valid_services']} valid, {summary['deprecated_services']} deprecated, {summary['invalid_services']} invalid")
    logger.info(f"***SERVICE-VALIDATION-SERVER-USE*** Full summary: {summary}")
    return summary

# AWS Documentation Tools (copied from awslabs.aws-documentation-mcp-server)
SEARCH_API_URL = 'https://proxy.search.docs.aws.com/search'
RECOMMENDATIONS_API_URL = 'https://contentrecs-api.docs.aws.amazon.com/v1/recommendations'
DOC_SESSION_UUID = str(uuid.uuid4())

@mcp.tool(
    name='search_aws_documentation',
    description="""***READING-DOC*** Search AWS documentation using the official AWS Documentation Search API.
    
    This tool searches across all AWS documentation for pages matching your search phrase.
    Use it to find relevant documentation when you don't have a specific URL.
    """
)
async def search_aws_documentation(
    search_phrase: str,
    limit: int = 10,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """Search AWS documentation using the official AWS Documentation Search API."""
    
    logger.info(f'***READING-DOC*** Starting AWS documentation search for: "{search_phrase}", limit: {limit}')

    request_body = {
        'textQuery': {
            'input': search_phrase,
        },
        'contextAttributes': [{'key': 'domain', 'value': 'docs.aws.amazon.com'}],
        'acceptSuggestionBody': 'RawText',
        'locales': ['en_us'],
    }
    
    logger.info(f'***READING-DOC*** Search request body: {request_body}')

    search_url_with_session = f'{SEARCH_API_URL}?session={DOC_SESSION_UUID}'
    logger.info(f'***READING-DOC*** Making request to: {search_url_with_session}')

    async with AsyncClient() as client:
        try:
            response = await client.post(
                search_url_with_session,
                json=request_body,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'AWS-Service-Validation-MCP-Server/1.0',
                    'X-MCP-Session-Id': DOC_SESSION_UUID,
                },
                timeout=30,
            )
            logger.info(f'***READING-DOC*** Search response status: {response.status_code}')
        except Exception as e:
            error_msg = f'Error searching AWS docs: {str(e)}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return [{'rank_order': 1, 'url': '', 'title': error_msg, 'context': None}]

        if response.status_code >= 400:
            error_msg = f'Error searching AWS docs - status code {response.status_code}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return [{'rank_order': 1, 'url': '', 'title': error_msg, 'context': None}]

        try:
            data = response.json()
            logger.info(f'***READING-DOC*** Search response data keys: {list(data.keys()) if data else "None"}')
        except json.JSONDecodeError as e:
            error_msg = f'Error parsing search results: {str(e)}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return [{'rank_order': 1, 'url': '', 'title': error_msg, 'context': None}]

    results = []
    if 'suggestions' in data:
        logger.info(f'***READING-DOC*** Found {len(data["suggestions"])} suggestions, processing up to {limit}')
        for i, suggestion in enumerate(data['suggestions'][:limit]):
            if 'textExcerptSuggestion' in suggestion:
                text_suggestion = suggestion['textExcerptSuggestion']
                context = None

                metadata = text_suggestion.get('metadata', {})
                if 'seo_abstract' in metadata:
                    context = metadata['seo_abstract']
                elif 'abstract' in metadata:
                    context = metadata['abstract']
                elif 'summary' in text_suggestion:
                    context = text_suggestion['summary']
                elif 'suggestionBody' in text_suggestion:
                    context = text_suggestion['suggestionBody']

                results.append({
                    'rank_order': i + 1,
                    'url': text_suggestion.get('link', ''),
                    'title': text_suggestion.get('title', ''),
                    'context': context,
                })

    logger.info(f'***READING-DOC*** Found {len(results)} search results for: "{search_phrase}"')
    logger.info(f'***READING-DOC*** Search results: {results}')
    return results

@mcp.tool(
    name='read_aws_documentation',
    description="""***READING-DOC*** Fetch and convert an AWS documentation page to markdown format.
    
    This tool retrieves the content of an AWS documentation page and converts it to markdown format.
    """
)
async def read_aws_documentation(
    url: str,
    max_length: int = 5000,
    start_index: int = 0,
    ctx: Context = None
) -> str:
    """Fetch and convert an AWS documentation page to markdown format."""
    
    logger.info(f'***READING-DOC*** Starting to read AWS documentation from: "{url}", max_length: {max_length}, start_index: {start_index}')
    
    # Validate that URL is from docs.aws.amazon.com and ends with .html
    if not re.match(r'^https?://docs\.aws\.amazon\.com/', url):
        error_msg = 'URL must be from the docs.aws.amazon.com domain'
        logger.error(f'***READING-DOC*** {error_msg}')
        raise ValueError(error_msg)
    if not url.endswith('.html'):
        error_msg = 'URL must end with .html'
        logger.error(f'***READING-DOC*** {error_msg}')
        raise ValueError(error_msg)

    logger.info(f'***READING-DOC*** URL validation passed, fetching content from: {url}')

    async with AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={
                    'User-Agent': 'AWS-Service-Validation-MCP-Server/1.0',
                    'X-MCP-Session-Id': DOC_SESSION_UUID,
                },
                timeout=30,
            )
            logger.info(f'***READING-DOC*** HTTP response status: {response.status_code}')
        except Exception as e:
            error_msg = f'Error reading AWS docs: {str(e)}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return error_msg

        if response.status_code >= 400:
            error_msg = f'Error reading AWS docs - status code {response.status_code}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return error_msg

        try:
            logger.info(f'***READING-DOC*** Converting HTML to markdown, content length: {len(response.text)} chars')
            # Convert HTML to markdown (simplified)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            logger.info(f'***READING-DOC*** Extracted text length: {len(text)} chars')
            
            # Apply length and start index limits
            if start_index > 0:
                text = text[start_index:]
                logger.info(f'***READING-DOC*** Applied start_index {start_index}, new length: {len(text)} chars')
            if len(text) > max_length:
                text = text[:max_length] + "... [truncated]"
                logger.info(f'***READING-DOC*** Truncated to max_length {max_length}, final length: {len(text)} chars')
            
            logger.info(f'***READING-DOC*** Successfully processed documentation, returning {len(text)} chars')
            return text
            
        except Exception as e:
            error_msg = f'Error parsing documentation: {str(e)}'
            logger.error(f'***READING-DOC*** {error_msg}')
            return error_msg

def main():
    """Run the MCP server with stdio transport only."""
    logger.info("Starting AWS Service Validation MCP Server with stdio transport")
    mcp.run()

if __name__ == "__main__":
    main()
