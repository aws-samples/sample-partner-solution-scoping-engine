# SOW Generator MCP Server

An AWS Labs Model Context Protocol (MCP) server for generating professional Statement of Work (SOW) documents with automated cost calculations, professional formatting, and S3 storage with versioning.

## Overview

The SOW Generator MCP Server streamlines the creation of professional consulting engagement documents by:

- **Automated Document Generation**: Creates comprehensive SOW documents from project requirements
- **Cost Calculations**: Applies standard consulting rates with customizable pricing
- **Professional Templates**: Multiple templates for different engagement types (AWS MAP, Azure Migration, Custom)
- **S3 Integration**: Automatic upload with versioning for document management
- **PDF Generation**: High-quality PDF output suitable for client delivery

## Features

### Document Templates
- **AWS MAP Assessment SOW**: Specialized template for AWS Migration Acceleration Program assessments
- **Azure Migration SOW**: Template for Azure migration and modernization projects  
- **Custom Project SOW**: Flexible template for custom consulting engagements

### Cost Management
- Standard hourly rates for common consulting roles
- Automatic cost calculations per sprint and total project
- Support for custom rate overrides
- Detailed cost breakdowns and summaries

### Professional Output
- Executive summary and project objectives
- Detailed scope and deliverables tables
- Project timeline and milestone planning
- Personnel assignments and responsibilities
- Professional formatting with company branding
- Terms, conditions, and acceptance criteria

## Tools

### `generate_sow_document`
Generate a complete SOW document in PDF format with automatic S3 upload.

**Parameters:**
- `chat_id` (required): Unique identifier for the chat session
- `customer_name` (required): Customer company name
- `project_title` (required): Title of the project
- `project_description` (required): Detailed project scope and objectives
- `personnel_json` (required): JSON array of project personnel with roles and hours
- `deliverables_json` (required): JSON array of project deliverables
- `template_type` (optional): SOW template type (aws_map, azure_migration, custom)
- `assumptions` (optional): Comma-separated project assumptions
- `exclusions` (optional): Comma-separated scope exclusions
- `partner_name` (optional): Partner company name (default: "ExamplePartner")
- `custom_rates_json` (optional): JSON object of custom hourly rates

**Example:**
```json
{
  "chat_id": "chat_12345",
  "customer_name": "Acme Corporation",
  "project_title": "AWS MAP Assessment for Azure Migration",
  "project_description": "Comprehensive assessment of current Azure environment for migration to AWS",
  "personnel_json": "[{\"role\":\"Cloud Architect\",\"hours_per_sprint\":10,\"responsibility\":\"Lead technical assessment\"},{\"role\":\"Cloud Engineer\",\"hours_per_sprint\":20,\"responsibility\":\"Workload analysis and documentation\"}]",
  "deliverables_json": "[{\"name\":\"Business Case & TCO Analysis\",\"description\":\"Financial model comparing current and proposed architecture\"},{\"name\":\"Migration Assessment Report\",\"description\":\"Detailed analysis of migration feasibility and recommendations\"}]",
  "template_type": "aws_map"
}
```

### `calculate_sow_costs`
Calculate project costs and generate detailed cost breakdowns.

**Parameters:**
- `personnel_json` (required): JSON array of personnel with roles and hours
- `custom_rates_json` (optional): JSON object of custom hourly rates
- `sprint_count` (optional): Number of project sprints (default: 3)

### `get_sow_templates`
Get information about available SOW templates and standard rates.

## Configuration

The server uses environment variables for AWS configuration:

- `S3_UPLOAD_BUCKET`: S3 bucket for document storage (default: "sera-v3-chat-docs")
- `AWS_REGION`: AWS region (default: "us-east-1")

## File Structure

Generated SOW documents are stored in S3 with the following structure:
```
S3_UPLOAD_BUCKET/
├── {chatId}/
│   ├── ScopeOfWork.pdf          # Main SOW document (versioned)
│   └── ScopeOfWork.metadata.json   # Generation metadata
```

## Dependencies

- `mcp[cli]>=1.6.0`: Model Context Protocol framework
- `pydantic>=2.10.6`: Data validation and settings management
- `boto3>=1.36.20`: AWS SDK for Python
- `jinja2>=3.1.4`: Template engine for HTML generation
- `weasyprint>=60.0`: HTML to PDF conversion
- `python-dateutil>=2.8.0`: Date/time utilities

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sow-generator-mcp-server

# Install dependencies
uv sync --all-groups

# Run the server
uv run awslabs.sow-generator-mcp-server
```

## Usage

The server is designed to be used with MCP-compatible clients. When integrated with a conversational AI system, users can request SOW generation by providing project details, and the server will:

1. Collect required project information
2. Apply appropriate templates and calculations
3. Generate professional PDF documents
4. Upload to S3 with automatic versioning
5. Return document location and metadata

## Testing

```bash
# Run tests with coverage
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## Contributing

This server follows AWS Labs MCP development standards:

- Use conventional commits for version control
- Maintain comprehensive test coverage
- Follow Python coding standards with ruff
- Include detailed documentation for all tools

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.