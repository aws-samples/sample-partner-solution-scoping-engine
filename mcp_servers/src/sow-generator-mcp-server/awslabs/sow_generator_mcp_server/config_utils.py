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

"""Configuration utilities for integrating with SERA CustomerConfig."""

import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


def get_sera_config() -> Optional[Dict[str, Any]]:
    """Get SERA configuration if available.
    
    Returns:
        Dict with SERA configuration or None if not available.
    """
    try:
        # Try to import SERA CustomerConfig
        import sys
        sys.path.append('../backend')
        from config.app_config import CustomerConfig
        
        # Load configuration if not already loaded
        if not CustomerConfig._config:
            CustomerConfig.load_config()
        
        # Return complete configuration including SOW_CONFIG
        config_dict = CustomerConfig._config
        
        # Extract SOW configuration
        sow_config = config_dict.get('SOW_CONFIG', {})
        
        return {
            'enabled': sow_config.get('enabled', True),
            'SOW_CONFIG': sow_config,
            'AWS_REGION': config_dict.get('AWS_REGION', 'us-east-1'),
            'S3_UPLOAD_BUCKET': config_dict.get('S3_UPLOAD_BUCKET', ''),
            'DYNAMODB_TABLE_NAME': config_dict.get('DYNAMODB_TABLE_NAME', '')
        }
    except Exception as e:
        logger.warning(f"Could not load SERA configuration: {e}")
        return None


def get_labor_rates() -> Dict[str, float]:
    """Get labor rates from SERA config or defaults.
    
    Returns:
        Dictionary of role names to hourly rates.
    """
    sera_config = get_sera_config()
    if sera_config and sera_config.get('labor_rates'):
        return sera_config['labor_rates']
    
    # Fallback to default rates
    return {
        "Cloud Architect": 265.00,
        "Cloud Engineer": 190.00,
        "Solutions Architect": 250.00,
        "DevOps Engineer": 180.00,
        "Scrum Master": 210.00,
        "Data Engineer": 200.00,
        "Security Engineer": 220.00,
        "Business Analyst": 175.00,
        "Project Manager": 195.00
    }


def get_default_partner() -> Dict[str, str]:
    """Get default partner information from SERA config or defaults.
    
    Returns:
        Dictionary with partner name, logo_url, and contact_email.
    """
    sera_config = get_sera_config()
    if sera_config and sera_config.get('default_partner'):
        return sera_config['default_partner']
    
    # Fallback to default partner
    return {
        'name': 'ExamplePartner',
        'logo_url': '',
        'contact_email': 'info@example.com'
    }


def get_template_config(template_type: str) -> Dict[str, Any]:
    """Get configuration for a specific template type.
    
    Args:
        template_type: The template type (e.g., 'aws_map', 'aws_modernization').
        
    Returns:
        Template configuration dictionary.
    """
    sera_config = get_sera_config()
    if sera_config and sera_config.get('templates'):
        return sera_config['templates'].get(template_type, {})
    
    # Fallback defaults
    default_templates = {
        'aws_map': {
            'name': 'AWS MAP Assessment SOW',
            'description': 'Template for AWS Migration Acceleration Program assessments',
            'default_duration_weeks': 6,
            'default_sprints': 3
        },
        'aws_modernization': {
            'name': 'AWS Modernization SOW',
            'description': 'Template for AWS application modernization and cloud-native transformation projects',
            'default_duration_weeks': 8,
            'default_sprints': 4
        },
        'custom': {
            'name': 'Custom Project SOW',
            'description': 'Flexible template for custom consulting engagements',
            'default_duration_weeks': 4,
            'default_sprints': 2
        }
    }
    return default_templates.get(template_type, {})


def get_default_assumptions() -> list:
    """Get default assumptions from SERA config or defaults.
    
    Returns:
        List of default assumption strings.
    """
    sera_config = get_sera_config()
    if sera_config and sera_config.get('default_assumptions'):
        return sera_config['default_assumptions']
    
    # Fallback defaults
    return [
        "Customer will provide timely access to environment resources and documentation",
        "Key subject matter experts will participate in scheduled workshops and review sessions",
        "Appropriate access will be provided to complete the assessment",
        "Migration execution and application modernization are out of scope"
    ]


def get_default_exclusions() -> list:
    """Get default exclusions from SERA config or defaults.
    
    Returns:
        List of default exclusion strings.
    """
    sera_config = get_sera_config()
    if sera_config and sera_config.get('default_exclusions'):
        return sera_config['default_exclusions']
    
    # Fallback defaults
    return [
        "Migration execution of workloads, data, or environments",
        "Application-level refactoring and code changes",
        "Ongoing operations and post-assessment support",
        "Procurement of licenses, AWS services, or third-party tools"
    ]


def is_sow_enabled() -> bool:
    """Check if SOW generation is enabled in SERA config.
    
    Returns:
        True if SOW generation is enabled, False otherwise.
    """
    sera_config = get_sera_config()
    if sera_config:
        return sera_config.get('enabled', False)
    
    # Default to enabled if no config available
    return True