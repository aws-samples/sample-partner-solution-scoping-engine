# Funding Reviewer MCP Server - Configuration Guide

This guide provides detailed information about configuring the Funding Reviewer MCP Server for different environments and use cases.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Environment Variables](#environment-variables)
- [AWS Configuration](#aws-configuration)
- [Server Configuration](#server-configuration)
- [File Processing Configuration](#file-processing-configuration)
- [Logging Configuration](#logging-configuration)
- [Performance Configuration](#performance-configuration)
- [Security Configuration](#security-configuration)
- [Development Configuration](#development-configuration)
- [Configuration Validation](#configuration-validation)
- [Best Practices](#best-practices)

## Configuration Overview

The POC Funding Reviewer MCP Server uses environment variables for configuration. This approach provides flexibility for different deployment environments while maintaining security best practices.

### Configuration Sources (in order of precedence)

1. **Environment variables** (highest priority)
2. **`.env` file** in the project root
3. **Default values** (lowest priority)

### Configuration Files

- **`.env.template`**: Template with all available configuration options
- **`.env.example`**: Example configuration with sample values
- **`.env`**: Your actual configuration (create from template)

## Environment Variables

### AWS Configuration

#### Required AWS Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AWS_REGION` | AWS region for Bedrock and other services | `us-west-2` | `us-east-1` |

#### Optional AWS Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key (if not using IAM roles) | - | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (if not using IAM roles) | - | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_SESSION_TOKEN` | AWS session token (for temporary credentials) | - | `AQoDYXdzEJr...` |
| `AWS_PROFILE` | AWS profile name | `default` | `production` |

### Bedrock Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `BEDROCK_MODEL_ID` | Bedrock model identifier | `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | `us.anthropic.claude-3-haiku-20240307-v1:0` |
| `BEDROCK_TEMPERATURE` | Model temperature (0.0-1.0) | `0.1` | `0.3` |
| `BEDROCK_MAX_TOKENS` | Maximum tokens per request | `4000` | `8000` |
| `BEDROCK_TIMEOUT` | Request timeout in seconds | `300` | `600` |

#### Available Bedrock Models

| Model ID | Description | Use Case |
|----------|-------------|----------|
| `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | Claude 3.5 Sonnet (Latest) | Balanced performance and cost |
| `us.anthropic.claude-3-haiku-20240307-v1:0` | Claude 3 Haiku | Fast, cost-effective |
| `us.anthropic.claude-3-opus-20240229-v1:0` | Claude 3 Opus | Highest quality analysis |

### Server Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MCP_SERVER_NAME` | Server identification name | `poc-funding-reviewer` | `poc-reviewer-prod` |
| `MCP_SERVER_VERSION` | Server version | `1.0.0` | `1.2.3` |
| `MCP_SERVER_HOST` | Server bind address | `0.0.0.0` | `127.0.0.1` |
| `MCP_SERVER_PORT` | Server port | `8080` | `9000` |

### File Processing Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | `50` | `100` |
| `SUPPORTED_IMAGE_FORMATS` | Comma-separated image formats | `png,jpg,jpeg` | `png,jpg,jpeg,gif` |
| `SUPPORTED_DOCUMENT_FORMATS` | Comma-separated document formats | `pdf` | `pdf,docx` |
| `SUPPORTED_CSV_FORMATS` | Comma-separated CSV formats | `csv` | `csv,tsv` |
| `TEMP_DIR` | Temporary file storage directory | `/tmp/poc-funding-reviewer` | `/var/tmp/poc-reviewer` |

### Reference Documents Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `REFERENCE_DOCS_PATH` | Path to general guidance document | `awslabs/poc_funding_reviewer_mcp_server/docs/poc_general_guidance.md` | `/app/docs/guidance.md` |
| `PROJECT_TEMPLATE_PATH` | Path to project template document | `awslabs/poc_funding_reviewer_mcp_server/docs/PoC_Project_Plan_Template.docx` | `/app/templates/template.docx` |

### Logging Configuration

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | Log output format | `json` | `json`, `text` |
| `LOG_FILE` | Log file path (optional) | - | `/var/log/poc-funding-reviewer.log` |
| `ENABLE_CORRELATION_IDS` | Enable request correlation IDs | `true` | `true`, `false` |

### Performance Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `REQUEST_TIMEOUT` | Request timeout in seconds | `600` | `1200` |
| `MAX_CONCURRENT_REQUESTS` | Maximum concurrent requests | `10` | `20` |
| `MAX_RETRIES` | Maximum retry attempts | `3` | `5` |
| `RETRY_BACKOFF_FACTOR` | Exponential backoff factor | `2.0` | `1.5` |

### Health Check Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENABLE_HEALTH_CHECK` | Enable health check endpoints | `true` | `false` |
| `HEALTH_CHECK_INTERVAL` | Health check interval in seconds | `30` | `60` |

### Security Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENABLE_REQUEST_VALIDATION` | Enable request validation | `true` | `false` |
| `MAX_REQUEST_SIZE_MB` | Maximum request size in MB | `100` | `200` |
| `ENABLE_FILE_SCANNING` | Enable file content scanning | `true` | `false` |

### Development Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DEBUG_MODE` | Enable debug mode | `false` | `true` |
| `DEV_MODE` | Enable development features | `false` | `true` |
| `MOCK_BEDROCK` | Mock Bedrock responses for testing | `false` | `true` |

### Monitoring Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENABLE_METRICS` | Enable metrics collection | `true` | `false` |
| `METRICS_INTERVAL` | Metrics export interval in seconds | `60` | `300` |
| `ENABLE_PERFORMANCE_MONITORING` | Enable performance monitoring | `true` | `false` |

## AWS Configuration

### Credential Configuration Methods

#### 1. Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
```

#### 2. AWS Profile
```bash
export AWS_PROFILE=poc-reviewer
export AWS_REGION=us-west-2
```

#### 3. IAM Roles (Recommended for Production)
```bash
# No credentials needed - uses instance/container role
export AWS_REGION=us-west-2
```

#### 4. AWS CLI Configuration
```bash
aws configure set aws_access_key_id your_access_key
aws configure set aws_secret_access_key your_secret_key
aws configure set default.region us-west-2
```

### Regional Considerations

#### Bedrock Availability by Region

| Region | Code | Claude 3.5 Sonnet | Claude 3 Haiku | Claude 3 Opus |
|--------|------|-------------------|----------------|---------------|
| US East (N. Virginia) | `us-east-1` | ✅ | ✅ | ✅ |
| US West (Oregon) | `us-west-2` | ✅ | ✅ | ✅ |
| Europe (Frankfurt) | `eu-central-1` | ✅ | ✅ | ❌ |
| Asia Pacific (Tokyo) | `ap-northeast-1` | ✅ | ✅ | ❌ |

## Server Configuration

### Port Configuration

```bash
# Default port
MCP_SERVER_PORT=8080

# Custom port
MCP_SERVER_PORT=9000

# Bind to specific interface
MCP_SERVER_HOST=127.0.0.1  # localhost only
MCP_SERVER_HOST=0.0.0.0    # all interfaces (default)
```

### SSL/TLS Configuration

For production deployments, use a reverse proxy (nginx, Apache) or load balancer for SSL termination:

```nginx
server {
    listen 443 ssl;
    server_name poc-reviewer.example.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## File Processing Configuration

### File Size Limits

```bash
# Maximum individual file size
MAX_FILE_SIZE_MB=50

# Maximum total request size
MAX_REQUEST_SIZE_MB=100
```

### Supported Formats

```bash
# Image formats for architecture diagrams
SUPPORTED_IMAGE_FORMATS=png,jpg,jpeg

# Document formats for SOW files
SUPPORTED_DOCUMENT_FORMATS=pdf

# CSV formats for pricing calculator files
SUPPORTED_CSV_FORMATS=csv
```

### Temporary File Storage

```bash
# Temporary directory for file processing
TEMP_DIR=/tmp/poc-funding-reviewer

# Ensure the directory exists and has proper permissions
mkdir -p /tmp/poc-funding-reviewer
chmod 755 /tmp/poc-funding-reviewer
```

## Logging Configuration

### Log Levels

```bash
# Debug: Detailed debugging information
LOG_LEVEL=DEBUG

# Info: General information (default)
LOG_LEVEL=INFO

# Warning: Warning messages only
LOG_LEVEL=WARNING

# Error: Error messages only
LOG_LEVEL=ERROR

# Critical: Critical errors only
LOG_LEVEL=CRITICAL
```

### Log Formats

#### JSON Format (Default)
```bash
LOG_FORMAT=json
```

Example output:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "poc_funding_reviewer",
  "message": "Processing POC funding request",
  "correlation_id": "req_123456",
  "request_id": "abc-def-ghi"
}
```

#### Text Format
```bash
LOG_FORMAT=text
```

Example output:
```
2024-01-15 10:30:00 - poc_funding_reviewer - INFO - Processing POC funding request
```

### Log File Configuration

```bash
# Log to file
LOG_FILE=/var/log/poc-funding-reviewer/application.log

# Log to stdout (default)
# LOG_FILE=  # Leave empty or unset
```

### Correlation IDs

```bash
# Enable request correlation IDs for tracing
ENABLE_CORRELATION_IDS=true
```

## Performance Configuration

### Request Handling

```bash
# Request timeout (seconds)
REQUEST_TIMEOUT=600

# Maximum concurrent requests
MAX_CONCURRENT_REQUESTS=10

# For high-traffic environments
MAX_CONCURRENT_REQUESTS=50
REQUEST_TIMEOUT=300
```

### Retry Configuration

```bash
# Maximum retry attempts for failed requests
MAX_RETRIES=3

# Exponential backoff factor
RETRY_BACKOFF_FACTOR=2.0

# Example: 1s, 2s, 4s delays between retries
```

### Bedrock Performance Tuning

```bash
# Faster responses with lower quality
BEDROCK_MODEL_ID=us.anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_TEMPERATURE=0.0
BEDROCK_MAX_TOKENS=2000

# Higher quality with slower responses
BEDROCK_MODEL_ID=us.anthropic.claude-3-opus-20240229-v1:0
BEDROCK_TEMPERATURE=0.1
BEDROCK_MAX_TOKENS=8000
```

## Security Configuration

### Request Validation

```bash
# Enable comprehensive request validation
ENABLE_REQUEST_VALIDATION=true

# Maximum request size
MAX_REQUEST_SIZE_MB=100

# Enable file content scanning
ENABLE_FILE_SCANNING=true
```

### File Security

```bash
# Restrict file types
SUPPORTED_IMAGE_FORMATS=png,jpg  # Remove jpeg if not needed
SUPPORTED_DOCUMENT_FORMATS=pdf   # Only PDF documents

# Limit file sizes
MAX_FILE_SIZE_MB=25  # Reduce if appropriate
```

### Network Security

```bash
# Bind to localhost only for local deployments
MCP_SERVER_HOST=127.0.0.1

# Use specific port
MCP_SERVER_PORT=8080
```

## Development Configuration

### Development Mode

```bash
# Enable development features
DEV_MODE=true
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Enable auto-reload
# (when using --dev flag)
```

### Testing Configuration

```bash
# Mock Bedrock for testing
MOCK_BEDROCK=true

# Reduce timeouts for faster tests
REQUEST_TIMEOUT=30
BEDROCK_TIMEOUT=10

# Use smaller file limits
MAX_FILE_SIZE_MB=10
```

### Local Development

```bash
# Minimal configuration for local development
AWS_REGION=us-west-2
AWS_PROFILE=default
BEDROCK_MODEL_ID=us.anthropic.claude-3-haiku-20240307-v1:0
LOG_LEVEL=DEBUG
DEV_MODE=true
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8080
```

## Configuration Validation

### Validation Script

Create a configuration validation script:

```bash
#!/bin/bash
# validate-config.sh

echo "Validating POC Funding Reviewer configuration..."

# Check required variables
required_vars=("AWS_REGION")

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "ERROR: Required variable $var is not set"
        exit 1
    fi
done

# Test AWS connectivity
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured or invalid"
    exit 1
fi

# Test Bedrock access
if ! aws bedrock list-foundation-models --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "ERROR: Cannot access Bedrock in region $AWS_REGION"
    exit 1
fi

echo "Configuration validation passed!"
```

### Python Validation

```python
from awslabs.poc_funding_reviewer_mcp_server.config import get_config

try:
    config = get_config()
    print("Configuration loaded successfully:")
    print(f"  AWS Region: {config.aws_region}")
    print(f"  Bedrock Model: {config.bedrock_model_id}")
    print(f"  Server Port: {config.mcp_server_port}")
except Exception as e:
    print(f"Configuration error: {e}")
    exit(1)
```

## Best Practices

### Security Best Practices

1. **Use IAM Roles**: Prefer IAM roles over access keys in production
2. **Least Privilege**: Grant minimal required permissions
3. **Rotate Credentials**: Regularly rotate access keys if used
4. **Secure Storage**: Never commit credentials to version control
5. **Network Security**: Use VPCs and security groups appropriately

### Performance Best Practices

1. **Model Selection**: Choose appropriate Bedrock model for your use case
2. **Resource Limits**: Set appropriate file size and request limits
3. **Monitoring**: Enable metrics and monitoring
4. **Caching**: Consider caching for repeated requests
5. **Scaling**: Use load balancers and multiple instances for high traffic

### Operational Best Practices

1. **Environment Separation**: Use different configurations for dev/staging/prod
2. **Configuration Management**: Use configuration management tools
3. **Backup**: Backup configuration and reference documents
4. **Documentation**: Document any custom configuration changes
5. **Testing**: Test configuration changes in non-production environments

### Configuration Management

#### Using Environment-Specific Files

```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production
```

#### Using Configuration Management Tools

- **Ansible**: Manage configuration with playbooks
- **Terraform**: Infrastructure as code with configuration
- **Kubernetes ConfigMaps**: Container orchestration configuration
- **AWS Systems Manager**: Parameter Store for configuration

### Troubleshooting Configuration

#### Common Configuration Issues

1. **AWS Credentials**:
   ```bash
   aws sts get-caller-identity
   aws bedrock list-foundation-models --region us-west-2
   ```

2. **File Permissions**:
   ```bash
   ls -la .env
   chmod 600 .env  # Secure permissions
   ```

3. **Environment Variables**:
   ```bash
   env | grep -E "(AWS|BEDROCK|MCP)"
   ```

4. **Port Conflicts**:
   ```bash
   netstat -tlnp | grep 8080
   lsof -i :8080
   ```

#### Configuration Debugging

```bash
# Enable debug mode
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m awslabs.poc_funding_reviewer_mcp_server.server --dev
```