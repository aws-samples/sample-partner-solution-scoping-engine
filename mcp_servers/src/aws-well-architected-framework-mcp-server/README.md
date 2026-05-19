# AWS Well-Architected Framework MCP Server

Model Context Protocol (MCP) server for AWS Well-Architected Framework assessments

This MCP server conducts comprehensive AWS Well-Architected Framework (WAFR) assessments with automated document analysis, pillar compliance evaluation, and professional report generation.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to AWS services
   - You need an AWS account with appropriate permissions
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to access S3, Bedrock, and DynamoDB

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-well-architected-framework-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-well-architected-framework-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "S3_UPLOAD_BUCKET": "your-s3-bucket"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/aws-well-architected-framework-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-well-architected-framework-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env-file",
        "/full/path/to/file/.env",
        "awslabs/aws-well-architected-framework-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "S3_UPLOAD_BUCKET": "your-s3-bucket"
}
```

Make sure the AWS profile has permissions to access S3, Bedrock, and DynamoDB. Your AWS IAM credentials remain on your local machine and are strictly used for accessing AWS services.

## Features

### Comprehensive Assessment Framework

- **Document Analysis**: Processes architecture documents (PDFs, images, text, CloudFormation, XML) using Claude multimodal capabilities
- **Capability-Based Scoring**: Intelligent scoring system that evaluates detected capabilities against pillar requirements with confidence levels (93-95%)
- **Six Pillar Evaluation**: Assesses all WAFR pillars (Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability)
- **Enterprise Validation**: Quality metrics, SLA compliance tracking, and capability detection validation
- **Bedrock Content Enhancement**: AI-generated architecture-specific narratives and implementation roadmaps

### Professional Output

- Executive summary with overall risk assessment
- Detailed pillar scores with capability breakdowns
- Specific recommendations with AWS documentation links
- Implementation roadmap with prioritized actions
- Professional DOCX formatting suitable for stakeholder review
- Automatic S3 upload with versioning

## Tools

### `analyze_architecture_documents`

Process and analyze uploaded architecture documents to extract AWS services and architectural patterns.

**Parameters:**
- `chat_id` (required): Unique identifier for the chat session
- `documents` (optional): List of document paths/URLs to analyze

**Returns:** Identified AWS services, architecture patterns, and compliance indicators

### `assess_pillar_compliance`

Evaluate a specific WAFR pillar against the analyzed architecture with capability-based scoring.

**Parameters:**
- `pillar` (required): WAFR pillar to assess (operational_excellence, security, reliability, performance_efficiency, cost_optimization, sustainability)
- `architecture_data` (required): Architecture data from document analysis

**Returns:** Pillar score (0-100), risk level, detected capabilities, and recommendations

### `generate_comprehensive_wafr_assessment`

Create a comprehensive assessment combining all pillar evaluations with enterprise-grade validation.

**Parameters:**
- `chat_id` (required): Chat session identifier
- `pillar_assessments` (required): Results from all 6 pillar assessments
- `architecture_data` (optional): Original architecture analysis data

**Returns:** Overall WAFR score, capability matrix, risk summary, validation results, and quality metrics

### `generate_professional_report`

Generate a professional DOCX report with Bedrock content enhancement and automatic S3 upload.

**Parameters:**
- `chat_id` (required): Chat session identifier
- `assessment_results` (required): Comprehensive assessment results
- `enhanced_report` (optional): Generate enhanced report with Bedrock narratives

**Returns:** S3 URL for downloadable DOCX report and report metadata

### `scan_live_aws_environment`

Scan a live AWS environment to gather architecture information.

**Parameters:**
- `aws_credentials` (optional): AWS credentials for scanning
- `regions` (required): List of AWS regions to scan

**Returns:** Live environment configuration and resource inventory

## Quick Example

```python
# Step 1: Analyze architecture documents
analyze_result = await analyze_architecture_documents(
    chat_id="assessment_001",
    documents=["s3://bucket/architecture.pdf"]
)

# Step 2: Assess each pillar
security_result = await assess_pillar_compliance(
    pillar="security",
    architecture_data=analyze_result
)

# Step 3: Generate comprehensive assessment
comprehensive_result = await generate_comprehensive_wafr_assessment(
    chat_id="assessment_001",
    pillar_assessments={"security": security_result, ...},
    architecture_data=analyze_result
)

# Step 4: Generate professional report
report_result = await generate_professional_report(
    chat_id="assessment_001",
    assessment_results=comprehensive_result,
    enhanced_report=True
)
# Returns: S3 URL for downloadable DOCX report
```

## Configuration

The server uses environment variables for AWS and S3 configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `S3_UPLOAD_BUCKET` | S3 bucket for report storage | sera-chat-docs |
| `AWS_REGION` | AWS region | us-east-1 |
| `AWS_PROFILE` | AWS profile for credentials | default |
| `FASTMCP_LOG_LEVEL` | Logging level | ERROR |
| `BACKEND_LOG_FILE` | Log file path (shared with backend) | backend.log |

## File Structure

Generated WAFR reports are stored in S3 with the following structure:

```
S3_UPLOAD_BUCKET/
├── {chatId}/
│   ├── wafr/
│   │   ├── wafr_assessment.docx           # Main WAFR report (versioned)
│   │   └── wafr_assessment.metadata.json  # Assessment metadata
│   └── uploads/                           # Analyzed architecture documents
```

## Development

To set up the development environment:

```bash
# Install dependencies
uv sync --all-groups

# Run the server locally
uv run awslabs.aws-well-architected-framework-mcp-server
```

### Testing

```bash
# Run tests with coverage
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
```

## Integration with SERA

This MCP server is designed for seamless integration with the SERA (Solution Engineering and Review Assistant) platform:

- Automatic AWS credential management through SERA backend
- S3 integration for document storage and retrieval
- Chat session management and context preservation
- Professional report generation for customer delivery
- Shared logging system with backend (`backend/utils/mcp_logger.py`)
- One-click WAFR assessment via "Start your WAFR Assessment" button

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.
