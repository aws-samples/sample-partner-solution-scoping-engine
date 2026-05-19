"""AWS pricing calculator instruction generator"""

import json
import boto3
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from .models import PricingRequest, AWSService
from .config import AgentConfig
from .service_lookup import ServiceDefinitionTool

logger = logging.getLogger(__name__)


def execute_nova_act_instructions(instructions: Dict[str, Any]) -> str:
    """Execute Nova Act instructions and return the public estimate link"""
    try:
        actions = instructions.get('actions', [])
        if not actions:
            raise ValueError("No actions found in instructions")
        
        logger.info(f"🤖 Executing {len(actions)} Nova Act actions...")
        
        # Check for API key
        if not os.environ.get('NOVA_ACT_API_KEY'):
            raise ValueError("Nova Act API key required. Set NOVA_ACT_API_KEY environment variable. Get key from: https://nova.amazon.com/act")
        
        os.environ["NOVA_ACT_BROWSER_ARGS"] = "--remote-debugging-port=9222"
        
        nova = NovaAct(
            starting_page="https://calculator.aws/#/estimate",
            headless=True,
            screen_height=1296,
            screen_width=1536
        )
        
        try:
            logger.info("🚀 Starting Nova Act browser session...")
            nova.start()
            
            successful_actions = 0
            failed_actions = 0
            
            for i, action in enumerate(actions):
                act_command = action.get('act', '')
                logger.info(f"🎭 Action {i+1}/{len(actions)}: {act_command}")
                
                try:
                    nova.act(act_command)
                    successful_actions += 1
                    logger.info(f"   ✅ Success")
                except Exception as e:
                    failed_actions += 1
                    logger.info(f"   ⚠️ Failed: {str(e)}")
                    
                    if _is_critical_action(act_command):
                        logger.info(f"   ❌ Critical action failed, stopping execution")
                        raise e
                    else:
                        logger.info(f"   ➡️ Continuing with next action...")
                        continue
            
            logger.info(f"\n📊 Execution Summary: {successful_actions} successful, {failed_actions} failed")
            
            logger.info("📋 Reading clipboard for public link...")
            nova.page.context.grant_permissions(["clipboard-read"])
            
            clipboard_text = nova.page.evaluate("""
                async () => {
                    return await navigator.clipboard.readText();
                }
            """)
            
            if not clipboard_text:
                raise RuntimeError("No content found in clipboard")
            
            logger.info(f"✅ Retrieved public link: {clipboard_text}")
            return clipboard_text
            
        finally:
            logger.info("🛑 Stopping Nova Act session...")
            nova.stop()
        
    except Exception as e:
        raise RuntimeError(f"Failed to execute Nova Act instructions: {str(e)}")


def _is_critical_action(act: str) -> bool:
    """Determine if an action is critical and should stop execution if it fails"""
    act_lower = act.lower()
    
    if 'click' in act_lower:
        return True
    if 'go to' in act_lower:
        return True
    if 'scroll to' in act_lower:
        return True
    if 'set' in act_lower:
        return False
    
    return True


def load_service_name_mapping(definitions_path: str = None) -> Dict[str, str]:
    """Load the service name mapping file"""
    if definitions_path is None:
        current_dir = Path(__file__).parent.parent.parent
        definitions_path = current_dir / "service_definitions"
    else:
        definitions_path = Path(definitions_path)
    
    mapping_file = definitions_path / "service_name_mapping.json"
    if not mapping_file.exists():
        return {}
    
    try:
        with open(mapping_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.info(f"⚠️ Error loading service name mapping: {e}")
        return {}


def load_service_definitions_by_filenames(definitions_path: str = None, service_filenames: List[str] = None) -> Dict[str, Any]:
    """Load AWS service definitions by filenames using the service lookup tool"""
    tool = ServiceDefinitionTool(definitions_path)
    service_definitions = {}
    
    if not service_filenames:
        raise ValueError("No service filenames provided - cannot determine which services to load")
    
    # Load specific services by filename
    for filename in service_filenames:
        json_file = tool.defs_path / f"{filename}.json"
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    service_data = json.load(f)
                    service_code = service_data.get('serviceCode', filename)
                    service_definitions[service_code] = service_data
            except Exception as e:
                logger.info(f"⚠️ Error loading {json_file}: {e}")
                continue
        else:
            logger.warning(f"⚠️ Service definition file not found: {filename}.json")
    
    return service_definitions


def identify_services_with_bedrock(content: str, service_name_mapping: Dict[str, str], bedrock_client, config: AgentConfig) -> List[str]:
    """Use Bedrock to identify which services are mentioned in the document and return matching filenames"""
    
    # Log the size of content being processed
    content_size = len(content)
    logger.info(f"🔍 Processing document: {content_size:,} characters ({content_size/1024:.1f} KB)")
    if content_size > 500000:  # 500KB
        logger.warning(f"⚠️ Large document detected: {content_size:,} chars - may cause Bedrock errors")
    
    # Step 1: Extract service names mentioned in the document
    extraction_prompt = f"""
    Analyze the following AWS pricing document and extract ALL AWS service names that are mentioned.
    
    Document content:
    {content}
    
    Return ONLY a JSON array of AWS service names found in the document:
    ["service name 1", "service name 2", "service name 3"]
    
    """
    
    try:
        # Log prompt size before sending to Bedrock
        prompt_size = len(extraction_prompt)
        logger.info(f"📤 Bedrock extraction call: {prompt_size:,} characters ({prompt_size/1024:.1f} KB)")
        
        # Step 1: Extract service names from document using Bedrock
        response = bedrock_client.invoke_model(
            modelId=config.bedrock.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        extracted_text = response_body['content'][0]['text'].strip()
        
        # Extract JSON array from the response
        import re
        json_match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(0)
            extracted_service_names = json.loads(extracted_json)
        else:
            raise ValueError("No JSON array found in extraction response")
        
        logger.info(f"🔍 Extracted service names from document: {extracted_service_names}")
        
        # Step 2: Direct matching against service name mapping
        # Handle both old format (string) and new format (dict)
        matched_filenames = []
        
        # For each extracted service name, find matches in the mapping
        for extracted_name in extracted_service_names:
            for filename, service_info in service_name_mapping.items():
                original_name = service_info.get('original_name', '')
                official_name = service_info.get('official_name', '')
                
                # Exact string matching (case-insensitive) against both original and official names
                if (extracted_name.lower() == official_name.lower() or 
                    extracted_name.lower() == original_name.lower()):
                    matched_filenames.append(filename)
                    logger.info(f"✅ Exact match: '{extracted_name}' → {filename}")
                    break
                
                # Special handling for common service name variations
                extracted_lower = extracted_name.lower()
                original_lower = original_name.lower()
                official_lower = official_name.lower()
                
                # Handle "Amazon S3" → "Amazon Simple Storage Service (S3)"
                if (extracted_lower == "amazon s3" and "simple storage service" in original_lower) or \
                   (extracted_lower == "s3" and "simple storage service" in original_lower) or \
                   ("s3" in extracted_lower and "simple storage service" in original_lower):
                    matched_filenames.append(filename)
                    logger.info(f"🔄 S3 match: '{extracted_name}' → '{original_name}' → {filename}")
                    break
                
                # Handle "Amazon Kinesis Firehose" → "Amazon Kinesis Data Firehose"
                elif ("kinesis" in extracted_lower and "firehose" in extracted_lower and 
                      "kinesis" in official_lower and "firehose" in official_lower):
                    matched_filenames.append(filename)
                    logger.info(f"🔄 Kinesis Firehose match: '{extracted_name}' → '{official_name}' → {filename}")
                    break
                
                # Handle other common abbreviations and variations
                elif (extracted_lower in original_lower or original_lower in extracted_lower or
                      extracted_lower in official_lower or official_lower in extracted_lower):
                    # Only add if it's a substantial match (avoid matching single words)
                    if len(extracted_name) > 3 and (len(original_name) > 3 or len(official_name) > 3):
                        # Additional check to avoid false positives
                        words_extracted = set(extracted_lower.split())
                        words_original = set(original_lower.split())
                        words_official = set(official_lower.split())
                        
                        # Require at least 2 word overlap or one significant word match
                        if (len(words_extracted & words_original) >= 2 or 
                            len(words_extracted & words_official) >= 2 or
                            any(word in words_original or word in words_official 
                                for word in words_extracted if len(word) > 4)):
                            matched_filenames.append(filename)
                            logger.info(f"🔄 Partial match: '{extracted_name}' → '{original_name}' | '{official_name}' → {filename}")
                            break
        
        # Remove duplicates while preserving order
        matched_filenames = list(dict.fromkeys(matched_filenames))
        
        logger.info(f"🔄 Final mapped filenames: {matched_filenames}")
        return matched_filenames
        
    except Exception as e:
        logger.info(f"⚠️ Bedrock service identification failed: {e}")
        raise e


def generate_nova_act_instructions_with_bedrock(content: str, config: AgentConfig = None, definitions_path: str = None) -> str:
    """Generate Nova Act instructions directly using AWS Bedrock"""
    
    # Log the input size
    content_size = len(content)
    logger.info(f"🚀 Generating instructions for document: {content_size:,} characters ({content_size/1024:.1f} KB)")
    
    # Initialize config and Bedrock client
    if config is None:
        config = AgentConfig.from_env()
    
    bedrock = boto3.client('bedrock-runtime', region_name=config.bedrock.region)
    
    # Load service name mapping
    service_name_mapping = load_service_name_mapping(definitions_path)
    
    # Check if content is JSON with services array
    mentioned_filenames = []
    try:
        parsed_json = json.loads(content)
        if isinstance(parsed_json, dict) and 'services' in parsed_json:
            services = parsed_json['services']
            logger.info(f"✅ Detected JSON format with {len(services)} service(s)")
            
            # Extract service codes directly from JSON
            for service in services:
                # Use 'service' field (SERA uses this format) or 'service_name' as fallback
                service_name = service.get('service', '') or service.get('service_name', '')
                if service_name:
                    # Map service name to serviceCode
                    mapped_code = None
                    
                    # Special handling for common service names
                    if service_name.lower() in ['amazon s3', 's3', 'amazons3', 's3 standard', 'amazon s3 standard']:
                        mapped_code = 'amazonS3Standard'
                    elif service_name.lower() in ['amazon ec2', 'ec2']:
                        mapped_code = 'eC2Next'
                    elif service_name.lower() in ['amazon rds', 'rds']:
                        mapped_code = 'amazonRDSMySQLDB'  # Default to MySQL
                    elif service_name.lower() in ['amazon lambda', 'lambda']:
                        mapped_code = 'aWSLambda'
                    else:
                        # Try to find by service name in mapping
                        for filename, service_info in service_name_mapping.items():
                            original_name = service_info.get('original_name', '')
                            official_name = service_info.get('official_name', '')
                            if (service_name.lower() == original_name.lower() or 
                                service_name.lower() == official_name.lower()):
                                mapped_code = filename
                                break
                    
                    if mapped_code:
                        mentioned_filenames.append(mapped_code)
                        logger.info(f"✅ Mapped '{service_name}' → '{mapped_code}'")
                    else:
                        logger.warning(f"⚠️ Could not map service name: {service_name}")
                else:
                    logger.warning(f"⚠️ No service name found in service object: {service}")
            
            logger.info(f"🔄 Extracted service codes: {mentioned_filenames}")
    except json.JSONDecodeError:
        pass  # Not JSON, continue with normal flow
    
    # If no services found in JSON, fail early
    if not mentioned_filenames:
        raise ValueError("No AWS services identified in the document. Please specify services in JSON format: {\"services\": [{\"service\": \"Amazon S3\", ...}]}")
    
    # Replace official service names with original names in the document content
    processed_content = content
    replacements_made = []
    
    for filename, service_info in service_name_mapping.items():
        original_name = service_info.get('original_name', '')
        official_name = service_info.get('official_name', '')
        
        # Replace if names are different and official name is longer/more specific
        if (official_name and original_name and 
            official_name != original_name and 
            len(official_name) > len(original_name) and
            official_name in processed_content):
            
            processed_content = processed_content.replace(official_name, original_name)
            replacements_made.append(f"'{official_name}' → '{original_name}'")
        
        # Also handle common variations that should be replaced with the full original name
        # Special case for S3 variations
        if original_name == "Amazon Simple Storage Service (S3)":
            s3_variations = ["Amazon S3", "S3", "S3 Standard", "Amazon S3 Standard"]
            for variation in s3_variations:
                if variation in processed_content and variation != original_name:
                    processed_content = processed_content.replace(variation, original_name)
                    replacements_made.append(f"'{variation}' → '{original_name}'")
    
    if replacements_made:
        logger.info(f"🔄 Made {len(replacements_made)} service name replacements in document")
        for replacement in replacements_made[:5]:  # Show first 5
            logger.info(f"   {replacement}")
        if len(replacements_made) > 5:
            logger.info(f"   ... and {len(replacements_made) - 5} more")
    
    # Load only the relevant service definitions
    service_definitions = load_service_definitions_by_filenames(definitions_path, mentioned_filenames)
    
    # Log which services are being passed to Bedrock
    logger.info(f"🔍 Service files loaded: {mentioned_filenames}")
    logger.info(f"🔍 Service definitions loaded: {list(service_definitions.keys())}")
    
    # Create context with actual service names from definitions and mapping
    service_context = "AWS Services mentioned in the document with their full definitions:\n\n"
    for service_code, definition in service_definitions.items():
        service_name = definition.get('serviceName', service_code)
        if isinstance(service_name, dict):
            service_name = service_name.get('aws', service_code)
        
        # Find the corresponding mapping info
        mapping_info = None
        for filename, mapping_data in service_name_mapping.items():
            if filename == service_code:
                mapping_info = mapping_data
                break
        
        service_context += f"=== {service_code} ===\n"
        service_context += f"Service Name: {service_name}\n"
        
        if mapping_info:
            service_context += f"Original Name (for calculator): {mapping_info.get('original_name', service_name)}\n"
            service_context += f"Official Name: {mapping_info.get('official_name', service_name)}\n"
        
        service_context += f"Full Service Definition:\n"
        service_context += f"```json\n{json.dumps(definition, indent=2)}\n```\n\n"
    
    # Prompt for generating Nova Act instructions as JSON
    prompt = f"""
Analyze the following AWS pricing document and generate Nova Act instructions for the AWS pricing calculator.

{service_context}

IMPORTANT: When specifying usage metrics, convert values to the correct units expected by the AWS pricing calculator:

Use the service definition json to find out the possible values for the metrics for that particular service

Document content:
{processed_content}

Generate Nova Act instructions as a JSON object with an array of actions. Each action should have an "act" field describing what to do.

Return ONLY a JSON object in this exact format:

{{
  "actions": [
    {{
      "act": "In 'Find service' textbox, type 'Amazon API Gateway'"
    }},
    {{
      "act": "Click the 'Configure' button under Amazon API Gateway"
    }},
    {{
      "act": "Scroll to REST APIs card, then under the REST APIs card, set Service to 'Amazon API Gateway'"
    }},
    {{
      "act": "Scroll to REST APIs card, then under the REST APIs card, set REST API request units dropdown to 'millions'"
    }},
    {{
      "act": "Scroll to REST APIs card, then under the REST APIs card, set Number of REST API requests to 0.1"
    }},
    {{
      "act": "Scroll to REST APIs card, then under the REST APIs card, set Unit dropdown to 'per month'"
    }},
    {{
      "act": "Click 'Save and Add Service'"
    }}
  ]
}}

IMPORTANT FORMATTING RULES FOR CARDS:
- MANDATORY: ALL field operations MUST include card references and scroll actions
- For fields within a card, use the format: "Scroll to [Card Title] card, then under the [Card Title] card, set [field] to [value]"
- If a service has only one card or no explicit cards, omit the card reference and use: "Set [field] to [value]"
- Use the EXACT service names as they appear in the document content above
- Use the EXACT card titles as they appear in the service definitions (e.g., "HTTP APIs", "REST APIs")
- Do not include fields that are not in the specific service definition under the specific section/card
- Each dropdown setting should be a separate action
- CRITICAL: For every numeric field that has a "variableUnitLabel" in the service definition, create TWO actions:
  1. Set the field value: "Scroll to [Card Title] card, then under the [Card Title] card, set [Field Name] to [value]"
  2. Set the unit dropdown: "Scroll to [Card Title] card, then under the [Card Title] card, set [Field Name] unit dropdown to '[unit from variableUnitLabel]'"
- CRITICAL: For searchable dropdowns like Instance type, use TWO actions:
  1. "Scroll to [Card Title] card, then under the [Card Title] card, in Instance type search, type '[value]'"
  2. "Select '[value]' from Instance type search results"
- Each field setting should be a separate action
- Use the exact dropdown options from the service definitions provided above
- Break down complex steps into individual actions
- Add scroll actions when moving between cards: "Scroll down to [Card Title] card if not visible"
- Each service should end with 'Save and Add service' button click.
- Don't make up values if not mandatory, and not mentioned in the Document content
- SKIP any fields that have a value of 0 (zero) - do not include "set [field] to 0" actions
- SKIP unit dropdown actions for fields that have zero values
- SKIP actions that set fields to their default values (check service definitions for defaults)
- Only include fields that have non-zero values or are explicitly required by the service
- Use EXACT numeric values from the document content - do not add unit suffixes like "thousands", "millions", etc.
- Respect the schema's variableUnitLabel - if it says "requests in a month", use the raw number, not "thousands"
- For fields expecting raw numbers (like request counts), use the actual numeric value without unit conversion

Return only the valid JSON object, no other text.
"""

    # Call Bedrock Claude model
    try:
        # Log prompt size before sending to Bedrock
        prompt_size = len(prompt)
        logger.info(f"📤 Sending to Bedrock: {prompt_size:,} characters ({prompt_size/1024:.1f} KB)")
        if prompt_size > 500000:  # 500KB
            logger.warning(f"⚠️ Large prompt detected: {prompt_size:,} chars - may exceed model limits")
        
        response = bedrock.invoke_model(
            modelId=config.bedrock.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": config.bedrock.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text'].strip()
        
        # Extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON found in Bedrock response: {response_text[:200]}...")
        
        json_text = json_match.group(0)
        instructions_json = json.loads(json_text)
        
        # Post-process: Replace official service names with original names for calculator
        instructions_json = _replace_service_names_in_instructions(instructions_json, service_name_mapping)
        
        # Validation step: Double-check the instructions against service definitions
        logger.info("🔍 Validating instructions against service definitions...")
        validated_instructions = _validate_instructions_with_bedrock(
            instructions_json, service_definitions, service_name_mapping, bedrock, config
        )
        
        return validated_instructions
        
    except Exception as e:
        raise ValueError(f"Failed to parse pricing document with Bedrock: {str(e)}")




def _validate_instructions_with_bedrock(
    instructions: Dict[str, Any], 
    service_definitions: Dict[str, Any], 
    service_name_mapping: Dict[str, Dict[str, str]], 
    bedrock_client, 
    config: AgentConfig
) -> Dict[str, Any]:
    """Use Bedrock to validate and correct the generated instructions"""
    
    try:
        # Create validation context with service definitions
        validation_context = "Service Definitions for Validation:\n\n"
        for service_code, definition in service_definitions.items():
            validation_context += f"=== {service_code} ===\n"
            validation_context += f"```json\n{json.dumps(definition, indent=2)}\n```\n\n"
        
        # Create validation prompt
        validation_prompt = f"""
Review and validate the following Nova Act instructions against the AWS service definitions provided.

{validation_context}

INSTRUCTIONS TO VALIDATE:
```json
{json.dumps(instructions, indent=2)}
```

VALIDATION TASKS:
1. Check that field names match exactly with the service definitions FOR THE SAME SERVICE
2. Verify that unit dropdowns are correctly associated with their fields
3. Ensure dropdown values are valid options from the service definitions
4. Fix any obvious field name mismatches WITHIN THE SAME SERVICE
5. Make sure each field has its own unit dropdown if needed

CRITICAL RULES:
- ONLY remove an action if you are 100% certain the field does not exist in ANY of the service definitions provided
- If you're unsure whether a field exists, KEEP the action
- NEVER change field names from one service to another service's fields
- Only validate fields against their own service definition
- DO NOT mix field names between different services
- Be CONSERVATIVE - when in doubt, keep the action

CRITICAL FIXES NEEDED:
- If you see "set Unit dropdown" without specifying which field, fix it to be specific like "set [Field Name] unit to [value]"
- For frequency fields, use format: "Set [Field Name] frequency dropdown to [value]"
- For unit dropdowns, use format: "Set [Field Name] unit dropdown to [value]"
- Match field labels exactly as they appear in the service definitions FOR THE SAME SERVICE

Return the corrected instructions in the same JSON format. If no corrections are needed, return the original instructions.

Return ONLY the JSON object:
"""
        
        # Call Bedrock for validation
        response = bedrock_client.invoke_model(
            modelId=config.bedrock.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": config.bedrock.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": validation_prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        validation_response = response_body['content'][0]['text'].strip()
        
        # Extract JSON from validation response
        import re
        json_match = re.search(r'\{.*\}', validation_response, re.DOTALL)
        if not json_match:
            logger.info("⚠️ Validation failed to return JSON, using original instructions")
            return instructions
        
        validated_json = json.loads(json_match.group(0))
        
        # Count changes made
        original_actions = instructions.get('actions', [])
        validated_actions = validated_json.get('actions', [])
        
        changes_made = 0
        for i, (orig, valid) in enumerate(zip(original_actions, validated_actions)):
            if orig.get('act') != valid.get('act'):
                changes_made += 1
                logger.info(f"🔧 Fixed action {i+1}:")
                logger.info(f"   Before: {orig.get('act')}")
                logger.info(f"   After:  {valid.get('act')}")
        
        if changes_made == 0:
            logger.info("✅ No corrections needed - instructions are valid")
        else:
            logger.info(f"✅ Made {changes_made} corrections to instructions")
        
        return validated_json
        
    except Exception as e:
        logger.info(f"⚠️ Validation failed: {str(e)}, using original instructions")
        return instructions


def _replace_service_names_in_instructions(instructions: Dict[str, Any], service_name_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Replace official service names with original names in the generated instructions"""
    
    if not instructions or 'actions' not in instructions:
        return instructions
    
    # Create replacement mapping from official_name to original_name
    replacements = {}
    for service_info in service_name_mapping.values():
        official_name = service_info.get('official_name', '')
        original_name = service_info.get('original_name', '')
        
        if official_name and original_name and official_name != original_name:
            replacements[official_name] = original_name
    
    # Replace service names in each action
    for action in instructions['actions']:
        if 'act' in action:
            act_text = action['act']
            
            # Replace each official name with original name
            for official_name, original_name in replacements.items():
                # Only replace service names in specific contexts, not in field names
                if ("Find service" in act_text and f"type '{official_name}'" in act_text) or \
                   ("Configure' button under" in act_text and f"under {official_name}" in act_text):
                    act_text = act_text.replace(official_name, original_name)
            
            action['act'] = act_text
    
    return instructions


def get_service_definitions_by_names(service_names: List[str], definitions_path: str = None) -> List[Dict[str, Any]]:
    """
    Agent tool function: Get service definitions by service names
    
    Args:
        service_names: List of AWS service names to look up
        definitions_path: Optional path to service definitions directory
        
    Returns:
        List of service definition dictionaries with metadata
    """
    tool = ServiceDefinitionTool(definitions_path)
    definitions = tool.get_service_definitions(service_names)
    
    logger.info(f"🔍 Service Definition Tool: Requested {len(service_names)} services, found {len(definitions)} definitions")
    
    for definition in definitions:
        requested_name = definition.get('_requested_service_name', 'Unknown')
        service_code = definition.get('serviceCode', 'Unknown')
        logger.info(f"   ✅ {requested_name} → {service_code}")
    
    missing_services = []
    found_names = {def_item.get('_requested_service_name') for def_item in definitions}
    for service_name in service_names:
        if service_name not in found_names:
            missing_services.append(service_name)
    
    if missing_services:
        logger.info(f"   ⚠️ Missing definitions for: {', '.join(missing_services)}")
    
    return definitions


def search_available_services(query: str, definitions_path: str = None) -> List[Dict[str, str]]:
    """
    Agent tool function: Search for available services by name or partial match
    
    Args:
        query: Search query string
        definitions_path: Optional path to service definitions directory
        
    Returns:
        List of matching service information dictionaries
    """
    tool = ServiceDefinitionTool(definitions_path)
    results = tool.search_services(query)
    
    logger.info(f"🔍 Service Search Tool: Found {len(results)} services matching '{query}'")
    
    for result in results[:5]:  # Show first 5 results
        logger.info(f"   📦 {result['original_name']} ({result['filename']})")
    
    if len(results) > 5:
        logger.info(f"   ... and {len(results) - 5} more results")
    
    return results


def generate_calculator_instructions(content: str, config: AgentConfig = None, definitions_path: str = None) -> dict:
    """Generate Nova Act instructions for AWS pricing calculator from JSON content"""
    
    # Generate Nova Act instructions directly using Bedrock
    instructions_json = generate_nova_act_instructions_with_bedrock(content, config, definitions_path)
    
    # Create a simple summary
    summary = "Generated Nova Act instructions for AWS pricing calculator"
    
    return {
        "nova_act_instructions": instructions_json,
        "summary": summary,
        "parsed_services": []  # No longer needed since we generate instructions directly
    }