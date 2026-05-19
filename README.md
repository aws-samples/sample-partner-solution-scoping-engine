# Partner Solution Scoping Engine for AWS

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

An AI-powered partner solution scoping engine that helps AWS Partners and sellers design, price, and document cloud solutions through deep conversational workflows. It leverages AWS Bedrock and Model Context Protocol (MCP) servers to provide architecture diagrams, cost estimates, funding recommendations, Statements of Work, and CloudFormation templates — all from a single chat interface.

## Key Features

- **Conversational Solution Design** — Guides sellers through discovery questions, proposes AWS architectures, and refines solutions based on feedback
- **Architecture Diagrams** — Generates professional AWS architecture diagrams via MCP tooling
- **Pricing Estimates** — Produces cost breakdowns using the AWS Pricing Calculator
- **Funding Recommendations** — Analyzes eligibility for AWS Partner funding programs (MAP, POC, ISV WMP)
- **Statement of Work Generation** — Creates professional SOW documents with configurable templates
- **CloudFormation Templates** — Generates IaC for proposed solutions
- **Well-Architected Assessment** — Evaluates architectures against the AWS Well-Architected Framework
- **Role-Based Access Control** — Supports multiple user roles (sales, SA, management) with Cognito/SAML
- **Human-in-the-Loop Review** — Solutions Architects can review and validate AI recommendations

## Architecture

```
┌─────────────┐       ┌─────────────────┐       ┌──────────────────────────┐
│  React/Vite │◄─────►│  Flask Backend  │◄─────►│  AWS Bedrock (Claude)    │
│  Frontend   │       │  (Python 3.12)  │       └──────────────────────────┘
│ Cloudscape  │       │                 │
└─────────────┘       │  MCP Client     │◄─────►┌──────────────────────────┐
                      │                 │       │  MCP Servers             │
                      └────────┬────────┘       │  ├─ Diagram Generator    │
                               │                │  ├─ Cost Analysis        │
                               ▼                │  ├─ Pricing Calculator   │
                      ┌─────────────────┐       │  ├─ Funding Wizard      │
                      │    DynamoDB     │       │  ├─ SOW Generator       │
                      │  (Chat State)   │       │  ├─ CloudFormation Gen  │
                      └─────────────────┘       │  └─ Well-Architected    │
                                                └──────────────────────────┘
```

## Prerequisites

- AWS Account with Bedrock model access (Claude Sonnet 4)
- Python 3.12+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Redis (local development)

## Quick Start (Local Development)

```bash
# 1. Clone the repo
git clone <repo-url> && cd partner-solution-scoping-engine

# 2. Set up backend
cd backend
uv python pin 3.12.10
uv venv && source .venv/bin/activate && uv sync
cp config/config-template.json config/config.json
# Edit config.json with your AWS region, Cognito settings, etc.
deactivate

# 3. Set up MCP servers (repeat for each server in mcp_servers/src/*)
cd ../mcp_servers/src/<server-name>
uv venv && source .venv/bin/activate && uv sync && deactivate

# 4. Set up frontend
cd ../../../frontend
npm install

# 5. Start services
redis-server &                          # Terminal 1
cd backend && ./start-dev.sh            # Terminal 2
cd frontend && npm run dev              # Terminal 3
```

The app will be available at `http://localhost:7001`.

## Production Deployment

This project ships with CloudFormation templates for a full production deployment on AWS (ALB, EC2, CloudFront, Cognito, DynamoDB, S3, ElastiCache).

See [docs/deployment-guide.md](docs/deployment-guide.md) for step-by-step instructions.

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](docs/deployment-guide.md) | Production IaC deployment and local dev setup |
| [Implementation Guide](docs/implementation-guide.md) | Comprehensive implementation and operations guide |
| [Architecture Overview](docs/02-architecture-overview.md) | Detailed system architecture |
| [API Specifications](docs/03-api-specifications.md) | Backend API reference |

## Configuration

All configuration is managed through `backend/config/config.json` (copy from `config-template.json`). Key settings:

- **Authentication**: Cognito OAuth2 or SAML federation
- **Bedrock**: Model ID, region, retry configuration
- **MCP Servers**: Enabled servers and their settings (`backend/config/mcp.json`)
- **Personas**: Assistant behavior and access control (`backend/config/personas.py`)

## Project Structure

```
partner-solution-scoping-engine/
├── backend/              # Flask API server
│   ├── config/           # Configuration files
│   ├── models/           # DynamoDB data models
│   ├── routes/           # API endpoints
│   ├── services/         # Business logic (Bedrock, MCP, auth)
│   └── utils/            # Shared utilities
├── frontend/             # React + Cloudscape UI
├── mcp_servers/src/      # MCP tool servers
│   ├── aws-diagram-mcp-server/
│   ├── cost-analysis-mcp-server/
│   ├── pricing-calculator-mcp-server/
│   ├── apn-funding-wizard-mcp-server/
│   ├── sow-generator-mcp-server/
│   ├── aws-cloudformation-generation-mcp-server/
│   ├── funding-reviewer-mcp-server/
│   └── aws-well-architected-framework-mcp-server/
├── cloudformation/       # IaC deployment templates
├── docs/                 # Documentation
└── systemd/              # Service scripts
```

## Contributing

Contributions are welcome! Please open an issue to discuss proposed changes before submitting a pull request.

## Security

See [CONTRIBUTING](CONTRIBUTING.md) for reporting security issues.

If you discover a potential security issue, please do **not** create a public GitHub issue. Instead, follow the responsible disclosure process described in the contributing guide.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
