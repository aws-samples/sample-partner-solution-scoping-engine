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

import boto3
from botocore.exceptions import ClientError
import json
import logging
import ast

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    pass

import json
import logging
import os

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    pass

class CustomerConfig:
    _config = {}
    REQUIRED_KEYS = [
        'AWS_REGION', 
        'LOG_LEVEL', 
        'S3_LOGGING_BUCKET', 
        'S3_LOGGING_PREFIX', 
        'S3_UPLOAD_BUCKET',
        'S3_TOKEN_USAGE_DATA_BUCKET',
        'SAML_SETTINGS', 
        'AUTH_PROVIDER', 
        'AUTH_TYPE', 
        'REDIS_HOST', 
        'REDIS_PORT', 
        'BEDROCK_AWS_PROFILE', 
        'BEDROCK_USE_PROFILE',
        'DYNAMODB_TABLE_NAME',
        'CLOUDFRONT_DOMAIN',
        'CLOUDFRONT_KEY_PAIR_ID',
        'CLOUDFRONT_PRIVATE_KEY_PATH',
        "SINGED_URL_TIME",
        'DELETE_LOCAL_FILE_AFTER_BACKUP_S3',
        'DYNAMODB_RELATIONSHIPS_TABLE_NAME'
    ]

    @classmethod
    def load_config(cls, customer_id=None):
        logger.info(f"Loading app config")
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        try:
            with open(config_path, 'r') as config_file:
                cls._config = json.load(config_file)

            if customer_id:
                cls._config['CUSTOMER_ID'] = customer_id

            # Check for missing required keys
            missing_keys = [key for key in cls.REQUIRED_KEYS if key not in cls._config]
            if missing_keys:
                raise ConfigurationError(f"Missing required configuration keys: {', '.join(missing_keys)}")

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise ConfigurationError(f"Error parsing configuration file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise ConfigurationError(f"Unexpected error in configuration loading: {e}")

    @classmethod
    def get_config(cls):
        return cls._config

    @classmethod
    def get_value(cls, key, default=None):
        return cls._config.get(key, default)

    @classmethod
    def get_saml_settings(cls):
        return cls._config.get('SAML_SETTINGS', {})

    @classmethod
    def get_idp_config(cls):
        return cls._config.get('IDP_CONFIG', {})

    @classmethod
    def get_saml_group_mappings(cls):
        return cls._config.get('SAML_GROUP_MAPPINGS', {})

    @classmethod
    def get_readable_saml_group_name(cls, guid):
        mappings = cls.get_saml_group_mappings()
        return mappings.get(guid, guid)  # Return the GUID if no mapping found

    @classmethod
    def get_redis_config(cls):
        return {
            'host': cls.get_value('REDIS_HOST'),
            'port': int(cls.get_value('REDIS_PORT')),
            'db': 0,
            'ssl': True,
            'ssl_cert_reqs': None,  # Don't verify SSL cert
            'ssl_ca_certs': None,   # Don't use CA certs
            'decode_responses': True
        }

    @classmethod
    def get_aws_region(cls):
        """Get the AWS region from configuration.
        
        Returns:
            str: The AWS region configured for the customer.
        
        Raises:
            ConfigurationError: If AWS region is not configured.
        """
        region = cls.get_value('AWS_REGION')
        if not region:
            raise ConfigurationError("AWS region is not configured")
        return region

    @classmethod
    def get_bedrock_model_id(cls):
        """Get the Bedrock model ID from configuration.
        
        Returns:
            str: The Bedrock model ID configured for the customer.
        
        Raises:
            ConfigurationError: If Bedrock model ID is not configured.
        """
        model_id = cls.get_value('BEDROCK_MODEL_ID')
        if not model_id:
            raise ConfigurationError("Bedrock model ID is not configured")
        return model_id

    @classmethod
    def get_bedrock_aws_profile(cls):
        """Get the AWS profile to use for Bedrock API calls.
        
        Returns:
            str: The AWS profile name for Bedrock calls.
        
        Raises:
            ConfigurationError: If Bedrock AWS profile is not configured.
        """
        profile = cls.get_value('BEDROCK_AWS_PROFILE')
        if not profile:
            raise ConfigurationError("Bedrock AWS profile is not configured")
        return profile

    @classmethod
    def should_use_bedrock_profile(cls):
        """Check if Bedrock should use a specific AWS profile.
        
        Returns:
            bool: True if Bedrock should use the configured profile, False to use default.
        """
        use_profile = cls.get_value('BEDROCK_USE_PROFILE')
        return bool(use_profile)

    @classmethod
    def get_run_mode(cls):
        """Get the application run mode (DEV or PROD).
        
        Returns:
            str: The run mode, defaults to 'PROD' for security
        """
        return cls.get_value('RUN_MODE', 'PROD')

    @classmethod
    def get_aws_service_validations(cls):
        """Load AWS service validations from separate JSON file.
        
        Returns:
            dict: AWS service validation rules, empty dict if file doesn't exist
        """
        import json
        validations_file = os.path.join(os.path.dirname(__file__), 'aws_service_validations.json')
        if os.path.exists(validations_file):
            try:
                with open(validations_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load AWS service validations: {e}")
                return {}
        return {}

    @classmethod
    def is_development_mode(cls):
        """Check if the application is running in development mode.
        
        Returns:
            bool: True if in development mode
        """
        return cls.get_run_mode().upper() == 'DEV'

    @classmethod
    def get_dev_test_user_config(cls):
        """Get the development test user configuration.
        
        Returns:
            dict: Test user configuration for development mode
        """
        default_config = {
            "user_id": "test_user",
            "email": "test@localhost",
            "first_name": "Test", 
            "last_name": "User",
            "groups": ["sera_sales_person"]
        }
        return cls.get_value('DEV_TEST_USER', default_config)

    @classmethod
    def get_sow_config(cls):
        """Get the complete SOW configuration.
        
        Returns:
            dict: The SOW configuration settings.
        """
        return cls.get_value('SOW_CONFIG', {})

    @classmethod
    def is_sow_enabled(cls):
        """Check if SOW generation is enabled.
        
        Returns:
            bool: True if SOW generation is enabled, False otherwise.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('enabled', False)

    @classmethod
    def get_sow_labor_rates(cls):
        """Get the SOW labor rates configuration.
        
        Returns:
            dict: Dictionary of role names to hourly rates.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('labor_rates', {})

    @classmethod
    def get_sow_default_partner(cls):
        """Get the default partner information for SOWs.
        
        Returns:
            dict: Partner information including name, logo_url, and contact_email.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('default_partner', {
            'name': 'ExamplePartner',
            'logo_url': '',
            'contact_email': 'info@example.com'
        })

    @classmethod
    def get_sow_templates(cls):
        """Get the available SOW templates configuration.
        
        Returns:
            dict: Dictionary of template types and their configurations.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('templates', {})

    @classmethod
    def get_sow_template_config(cls, template_type):
        """Get configuration for a specific SOW template.
        
        Args:
            template_type (str): The template type (e.g., 'aws_map', 'azure_migration').
            
        Returns:
            dict: Template configuration or empty dict if not found.
        """
        templates = cls.get_sow_templates()
        return templates.get(template_type, {})

    @classmethod
    def get_sow_pdf_settings(cls):
        """Get the SOW PDF generation settings.
        
        Returns:
            dict: PDF settings including page_size, margin, etc.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('pdf_settings', {
            'page_size': 'Letter',
            'margin': '1in',
            'include_header_footer': True,
            'font_family': 'Arial, sans-serif'
        })

    @classmethod
    def get_sow_s3_settings(cls):
        """Get the SOW S3 storage settings.
        
        Returns:
            dict: S3 settings including file names and folder structure.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('s3_settings', {
            'file_name': 'ScopeOfWork.pdf',
            'metadata_file_name': 'ScopeOfWork.metadata.json',
            'folder_structure': '{chat_id}/sow/',
            'content_type': 'application/pdf'
        })

    @classmethod
    def get_sow_review_settings(cls):
        """Get the SOW review workflow settings.
        
        Returns:
            dict: Review settings including approval requirements and roles.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('review_settings', {
            'require_review': True,
            'auto_approve': False,
            'review_roles': ['sera_solutions_architect', 'sera_sa_manager'],
            'notification_enabled': True
        })

    @classmethod
    def get_sow_default_assumptions(cls):
        """Get the default assumptions for SOW documents.
        
        Returns:
            list: List of default assumption strings.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('default_assumptions', [])

    @classmethod
    def get_sow_default_exclusions(cls):
        """Get the default exclusions for SOW documents.
        
        Returns:
            list: List of default exclusion strings.
        """
        sow_config = cls.get_sow_config()
        return sow_config.get('default_exclusions', [])

    @classmethod
    def get_sow_s3_bucket(cls):
        """Get the S3 bucket for SOW document storage.
        
        Returns:
            str: The S3 bucket name, defaults to S3_UPLOAD_BUCKET.
        """
        return cls.get_value('S3_UPLOAD_BUCKET')

    @classmethod
    def can_user_review_sow(cls, user_role):
        """Check if a user role can review SOW documents.
        
        Args:
            user_role (str): The user's role identifier.
            
        Returns:
            bool: True if the user can review SOWs, False otherwise.
        """
        review_settings = cls.get_sow_review_settings()
        review_roles = review_settings.get('review_roles', [])
        return user_role in review_roles

    @classmethod
    def get_bedrock_retry_config(cls):
        """Get the Bedrock retry configuration.
        
        Returns:
            dict: Retry configuration with max_retries and throttle_delay_seconds.
        """
        return cls.get_value('BEDROCK_RETRY_CONFIG', {
            'max_retries': 20,
            'throttle_delay_seconds': 30
        })

    @classmethod
    def get_bedrock_max_retries(cls):
        """Get the maximum number of retries for Bedrock API calls.
        
        Returns:
            int: Maximum retry attempts (default: 20).
        """
        retry_config = cls.get_bedrock_retry_config()
        return retry_config.get('max_retries', 20)

    @classmethod
    def get_bedrock_throttle_delay(cls):
        """Get the throttle delay in seconds for Bedrock API retries.
        
        Returns:
            int: Delay in seconds between retries (default: 30).
        """
        retry_config = cls.get_bedrock_retry_config()
        return retry_config.get('throttle_delay_seconds', 30)

    # Authentication-related methods
    
    @classmethod
    def get_auth_type(cls):
        """Get the authentication type from configuration.
        
        Returns:
            str: Authentication type ('saml', 'oauth2', or 'both').
        """
        return cls.get_value('AUTH_TYPE', 'saml')
    
    @classmethod
    def get_auth_provider(cls):
        """Get the authentication provider from configuration.
        
        Returns:
            str: Authentication provider identifier.
        """
        return cls.get_value('AUTH_PROVIDER', 'aws_iam_identity_center')
    
    @classmethod
    def get_saml_settings(cls):
        """Get the SAML settings from configuration.
        
        Returns:
            dict: SAML configuration settings.
        """
        return cls.get_value('SAML_SETTINGS', {})
    
    @classmethod
    def get_saml_group_mappings(cls):
        """Get the SAML group mappings from configuration.
        
        Returns:
            dict: Mapping of SAML group IDs to application roles.
        """
        return cls.get_value('SAML_GROUP_MAPPINGS', {})
    
    @classmethod
    def get_frontend_url(cls):
        """Get the frontend URL for redirects.
        
        Returns:
            str: Frontend URL for AUTH callback
        """
        return cls.get_value('AUTH_FRONTEND_URL')
    
    @classmethod
    def get_token_usage_bucket(cls):
        """Get the S3 bucket for token usage data storage.
        
        Returns:
            str: S3 bucket name for token usage data
        """
        return cls.get_value('S3_TOKEN_USAGE_DATA_BUCKET')
    @classmethod
    def get_file_classification_config(cls):
        """Get the complete file classification configuration.
        
        Returns:
            dict: The file classification configuration settings.
        """
        return cls.get_value('FILE_CLASSIFICATION_CONFIG', {})

    @classmethod
    def get_allowed_extensions(cls):
        """Get the allowed file extensions for uploads.
        
        Returns:
            list: List of allowed file extensions.
        """
        file_config = cls.get_file_classification_config()
        return file_config.get('allowed_extensions', [])

    @classmethod
    def is_extension_allowed(cls, extension):
        """Check if a file extension is allowed.
        
        Args:
            extension (str): File extension to check (with or without dot).
            
        Returns:
            bool: True if extension is allowed, False otherwise.
        """
        # Normalize extension (ensure it has no leading dot for comparison)
        ext = extension.lower().lstrip('.')
        allowed = cls.get_allowed_extensions()
        
        # Check both with and without dots in the allowed list
        return ext in allowed or f'.{ext}' in allowed