# AWS Service Validation MCP Server

MCP server for validating AWS services and providing current alternatives for deprecated or invalid services.

## Features

### Validate AWS Services
- Check if AWS services are valid, deprecated, or invalid
- Use multiple validation methods (boto3, available services list, known deprecated services)
- Get suggestions for alternatives when services are deprecated or invalid

### Service Discovery
- Get comprehensive list of all available AWS services
- Validate multiple services at once for bulk operations
- Search AWS documentation for service alternatives

### Current Service Recommendations
- Identify deprecated services and their modern replacements
- Provide specific guidance for service migrations
- Keep recommendations up-to-date with latest AWS offerings

## Tools

### `validate_aws_service`
Validate a single AWS service and get detailed status information.

**Parameters:**
- `service_name` (string): Name of the AWS service to validate

**Returns:**
- Service validation result with status (valid/deprecated/invalid)
- Suggestions for alternatives if service is deprecated/invalid
- Detailed validation information

### `get_available_aws_services`
Get a complete list of all available AWS services from boto3.

**Returns:**
- Total count of available services
- Complete list of service names
- Status information

### `validate_multiple_services`
Validate multiple AWS services at once for bulk operations.

**Parameters:**
- `service_names` (array): List of AWS service names to validate

**Returns:**
- Summary statistics (valid, deprecated, invalid counts)
- Detailed results for each service
- Bulk validation status

## Installation

```bash
cd aws-service-validation-mcp-server
pip install -e .
```

## Usage

### As MCP Server
```bash
aws-service-validation-mcp-server --port 8000
```

### Example Usage in SERA
The server integrates with SERA's MCP client to provide real-time service validation:

```python
# Validate a single service
result = await mcp_client.call_tool("validate_aws_service", {"service_name": "ec2"})

# Validate multiple services
services = ["ec2", "vmware-cloud-on-aws", "evs", "fake-service"]
results = await mcp_client.call_tool("validate_multiple_services", {"service_names": services})

# Get all available services
available = await mcp_client.call_tool("get_available_aws_services", {})
```

## Service Status Types

- **valid**: Service exists and is current
- **deprecated**: Service exists but is deprecated, alternatives provided
- **invalid**: Service does not exist, search suggestions provided

## Known Deprecated Services

The server maintains a database of known deprecated services:

- `vmware-cloud-on-aws` → Use `evs` (Amazon Elastic VMware Service)
- `snowball-edge` → Use `snowball` (unified Snowball service)
- `elasticache-redis` → Use `elasticache` (ElastiCache service)

## Integration with SERA

This MCP server is designed to integrate with SERA's conversation flow to:

1. **Validate recommendations**: Check if LLM-recommended services are current
2. **Suggest alternatives**: Provide modern replacements for deprecated services
3. **Prevent outdated advice**: Ensure solution recommendations use current AWS services

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
isort .

# Type checking
mypy .
```

## License

Licensed under the Apache License, Version 2.0.
