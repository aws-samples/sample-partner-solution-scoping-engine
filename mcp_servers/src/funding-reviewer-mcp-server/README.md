# Funding Reviewer MCP Server

An MCP (Model Context Protocol) server that provides automated compliance analysis for AWS Partner POC (Proof of Concept) funding requests using AWS Bedrock.

## Overview

This MCP server analyzes Statement of Work (SOW) PDF documents, architecture diagrams, and AWS Pricing Calculator CSV files to ensure compliance with POC funding program requirements. It leverages AWS Bedrock with configurable LLM models to perform comprehensive reviews against AWS partner program standards and guidelines.

## Features

- **Document Processing**: Supports SOW PDFs, architecture diagrams (PNG/JPG), and AWS Pricing Calculator CSV files
- **Compliance Analysis**: Automated validation against POC funding program requirements
- **AWS Bedrock Integration**: Configurable LLM models with Claude Sonnet 4 as default
- **MCP Protocol**: Standard Model Context Protocol implementation for broad compatibility
- **Comprehensive Validation**: Financial calculations, document correlation, and scope verification

## Installation

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Configuration

The server can be configured through environment variables:

```bash
# AWS Configuration
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>

# Bedrock Configuration
export BEDROCK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
export BEDROCK_TEMPERATURE=0.1
export BEDROCK_MAX_TOKENS=4000

# Server Configuration
export MCP_SERVER_NAME=funding-reviewer
export LOG_LEVEL=INFO
```

## Usage

### Running the Server

```bash
# Run directly
python -m awslabs.poc_funding_reviewer_mcp_server.server

# Or use the installed script
poc-funding-reviewer-mcp-server
```

### MCP Tools

The server exposes the following MCP tools:

#### `analyze_poc_funding_request`

Primary tool for analyzing POC funding requests.

**Parameters:**
- `sow_document` (required): Base64 encoded SOW PDF document
- `architecture_diagram` (required): Base64 encoded architecture diagram (PNG/JPG)
- `pricing_calculator_csv` (optional): Base64 encoded AWS Pricing Calculator CSV file
- `request_metadata` (optional): Additional request metadata

**Returns:**
Structured analysis results including compliance status, findings, and action items.

#### `validate_documents`

Validates document formats and basic requirements.

**Parameters:**
- `documents` (required): Array of documents to validate

**Returns:**
Validation results for each document.

#### `get_funding_requirements`

Retrieves POC funding program requirements and guidelines.

**Parameters:**
- `program_type` (optional): Type of POC funding program

**Returns:**
Funding requirements and guidelines.

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd poc-funding-reviewer-mcp-server

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test categories
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .
```

## Architecture

The server is built with a modular architecture:

- **MCP Interface Layer**: Handles MCP protocol communication
- **Document Processing Layer**: Processes PDFs, images, and CSV files
- **Analysis Engine**: Orchestrates AI-powered analysis using AWS Bedrock
- **Compliance Validator**: Implements POC funding program rules
- **Configuration Management**: Handles settings, logging, and error handling

## Requirements

- Python 3.9+
- AWS credentials with Bedrock access
- Required Python packages (see pyproject.toml)

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests for any improvements.

## Support

For issues and questions, please use the GitHub issue tracker.