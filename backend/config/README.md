# SERA Backend Configuration

This directory contains the configuration management system for the SERA backend application. The configuration is centralized through the `CustomerConfig` class and stored in JSON format.

## Files

- **`config.json`** - Main configuration file containing all application settings
- **`mcp.json`** - MCP (Model Context Protocol) server configurations
- **`personas.py`** - Chat persona configurations
- **`app_config.py`** - Configuration management class that loads and provides access to settings

## Configuration Structure - config.json

### Core Settings

| Setting | Description | Default | Required |
|---------|-------------|---------|----------|
| `RUN_MODE` | Application environment (DEV/PROD) | PROD | ✓ |
| `AWS_REGION` | AWS region for all services | us-east-1 | ✓ |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/ERROR) | DEBUG | ✓ |

### Authentication Configuration

#### Basic Auth Settings
Your Authentication provider details. Can be a blank value, OAUTH2 or SAML. If OAUTH2:
```json
{
  "AUTH_PROVIDER": "amazon_cognito",
  "AUTH_TYPE": "oauth2"
}
```
If SAML: 
```json
{
  "AUTH_PROVIDER": "aws_iam_identity_center",
  "AUTH_TYPE": "saml"
}

#### OAuth2 Settings
```json
{
  "OAUTH2_SETTINGS": {
    "provider": "cognito",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "user_pool_id": "us-east-1_XXXXXX",
    "region": "us-east-1",
    "domain": "your-domain.auth.region.amazoncognito.com",
    "redirect_uri": "http://localhost:5001/api/callback",
    "scopes": ["openid", "email", "profile"]
  }
}
```

#### SAML Settings
```json
{
    "SAML_SETTINGS": {
        "strict": true,
        "debug": true,
        "sp": {
            "entityId": "urn:aws:sera_application",
            "assertionConsumerService": {
                "url": "<APP_URL",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "singleLogoutService": {
                "url": "APP_LOGOUT_UTL",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "acs_url": "APP_CALLBACK_URL",
            "x509cert": "",
            "privateKey": ""
        },
        "idp": {
            "entityId": "SAML_PROVIDER_ENTITY_URL",
            "singleSignOnService": {
                "url": "SAML_PROVIDER_ENTITY_URL",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "singleLogoutService": {
                "url": "SAML_PROVIDER_ENTITY_URL",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": "SAML_PROVIDER_PROVIDED_X509_CERTIFICATE"
        }
    }
}
```

### AWS Service Configuration

#### Bedrock AI Model Settings

```json
{
  "BEDROCK_MODEL_ID": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", #Claude Sonnet-3.7 or Sonnet 4 ONLY
  "BEDROCK_AWS_PROFILE": "", # In case you need to use a different AWS account (i.e. an account with a higher tokens per minute quota), create an additional profile for that account.
  "BEDROCK_USE_PROFILE": false, # Set to true if using a seperate AWS account for ONLY the Bedrock API calls
  "BEDROCK_RETRY_CONFIG": {
    "max_retries": 30,
    "throttle_delay_seconds": 30
  } # We set a standard "wait 30 seeonds and retry" for those who may be quota-hindered. 
}
```

#### Database Configuration
```json
{
  "DB_SECRET_NAME": "operations-dev", # This secret in secrets manager contains the RDS database credentials and db host infoz for the RDS database which contains the token useage audit tables
  "DYNAMODB_TABLE_NAME": "sera-v3-user-chats-dev" # This is the DynamoDB table name
}
```

#### Storage Configuration
```json
{
  "S3_LOGGING_BUCKET": "sera-v2-15910002-logfiles", 
  "S3_LOGGING_PREFIX": "logs",
  "S3_UPLOAD_BUCKET": "sera-v3-chat-docs",
  "CLOUDFRONT_DOMAIN": "https://d14wjavg9r72u5.cloudfront.net", # Cloudfront domain 
  "CLOUDFRONT_KEY_PAIR_ID": "K2OJXY3GZ4H99R", # Cloudfront KeyPair ID
  "CLOUDFRONT_PRIVATE_KEY_PATH": "/path/to/private-key.pem" # Local path to the private key
}
```

### Statement of Work (SOW) Configuration

The SOW configuration enables automated generation of project scope documents.

```json
{
  "SOW_CONFIG": {
    "enabled": true,
    "default_partner": {
      "name": "Any Company, Inc",
      "logo_url": "",
      "contact_email": "info@anycompany.link"
    },
    "labor_rates": {
      "Cloud Architect": 265.00,
      "Cloud Engineer": 190.00,
      "Solutions Architect": 250.00,
      "DevOps Engineer": 180.00
    },
    "templates": {
      "aws_map": {
        "name": "AWS MAP Assessment SOW",
        "description": "Template for AWS Migration Acceleration Program assessments",
        "default_duration_weeks": 6,
        "default_sprints": 3
      }
    },
    "review_settings": {
      "require_review": true,
      "auto_approve": false,
      "review_roles": ["sera_solutions_architect", "sera_sa_manager"]
    }
  }
}
```

### Development Configuration

#### Dev Mode Settings
```json
{
  "RUN_MODE": "DEV", # If run mode is DEV, it will bypass authentication. PROD requires authentication.
  "DEV_TEST_USER": {
    "user_id": "test_user",
    "email": "test@localhost",
    "first_name": "Test",
    "last_name": "User",
    "groups": ["sera_sales_person"]
  } # This is the session data for the test user account for a DEV deployment
}
```

#### Cache Configuration
You can host redis either on the local machine (not recommeneded for prod) or use Elasticache/REDIS/Valkey. 
```json
{
  "REDIS_HOST": "localhost",
  "REDIS_PORT": "6379"
}
```
## Configuration Structure - mcp.json
mcp.json uses standard MCP server configuration parameters. You can enable a new MCP server or remove MCP servers here, it will
not affect the application. MCP sservers load at application startup.

## Configuration Structure - personas.py
*** It is NOT recommended that any of the system prompts be changed. Each assistant has a configuration. ***
knowledgebase_id="", # if you want to add a Bedrock Knowldgebase. This adds cost to the service. 
allowed_groups=["sera_sales_person", "sera_solutions_architect", "sera_sales_manager", "sera_sa_manager"], # These are the groups allowed to access the persona.
guardrail = '', # If you want to add a guardrail for increased security.
guardrail_version = '', 
active ='YES' # can simply deactivate the assistant or activate it.

## Using Configuration in Code

### Import the Configuration Class
```python
from backend.config.app_config import CustomerConfig
```

### Load Configuration (Done at Application Startup)
```python
CustomerConfig.load_config()
```

### Access Configuration Values

#### Generic Value Access
```python
# Get any configuration value with optional default
value = CustomerConfig.get_value('AWS_REGION', 'us-east-1')
```

#### Typed Access Methods
```python
# AWS configuration
region = CustomerConfig.get_aws_region()
model_id = CustomerConfig.get_bedrock_model_id()

# Authentication
auth_type = CustomerConfig.get_auth_type()
is_dev = CustomerConfig.is_development_mode()

# SOW configuration
sow_enabled = CustomerConfig.is_sow_enabled()
labor_rates = CustomerConfig.get_sow_labor_rates()
partner_info = CustomerConfig.get_sow_default_partner()
```

### Environment-Specific Behavior
```python
# Check environment mode
if CustomerConfig.is_development_mode():
    # Development-specific logic
    test_user = CustomerConfig.get_dev_test_user_config()
else:
    # Production logic
    pass
```

## Required Configuration Keys

The following keys must be present in `config.json` or the application will fail to start:

- `AWS_REGION`
- `LOG_LEVEL`
- `S3_LOGGING_BUCKET`
- `S3_LOGGING_PREFIX`
- `S3_UPLOAD_BUCKET`
- `FILE_CLASSIFICATION_CONFIG.allowed_extensions` (moved from ALLOWED_EXTENSIONS)
- `SAML_SETTINGS`
- `AUTH_PROVIDER`
- `AUTH_TYPE`
- `REDIS_HOST`
- `REDIS_PORT`
- `BEDROCK_AWS_PROFILE`
- `BEDROCK_USE_PROFILE`
- `DYNAMODB_TABLE_NAME`
- `CLOUDFRONT_DOMAIN`
- `CLOUDFRONT_KEY_PAIR_ID`
- `CLOUDFRONT_PRIVATE_KEY_PATH`
- `SINGED_URL_TIME`
- `DELETE_LOCAL_FILE_AFTER_BACKUP_S3`

## Security Considerations

1. **Sensitive Values**: Store sensitive information like client secrets and private keys outside of the config file when possible
2. **File Permissions**: Ensure `config.json` has appropriate file permissions (600 or 644)
3. **Version Control**: Consider using environment-specific config files and not committing sensitive values
4. **Validation**: The `CustomerConfig` class validates required keys on startup

## Environment Variables

While the application primarily uses `config.json`, some values can be overridden with environment variables. Check the `CustomerConfig` class implementation for specific environment variable support.

## Troubleshooting

### Configuration Load Errors
- **File Not Found**: Ensure `config.json` exists in the `backend/config/` directory
- **JSON Parse Error**: Validate JSON syntax using a JSON validator
- **Missing Required Keys**: Check the error message for specific missing configuration keys

### Authentication Issues
- Verify `AUTH_TYPE` and `AUTH_PROVIDER` match your identity provider setup
- For OAuth2, ensure redirect URIs match between config and identity provider
- For SAML, verify entity IDs and certificate configurations

### AWS Service Errors
- Confirm `AWS_REGION` matches your AWS resources
- Verify AWS credentials are properly configured
- Check S3 bucket names and DynamoDB table names exist in the specified region