# SERA Implementation Guide

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites](#3-prerequisites)
4. [Deployment](#4-deployment)
5. [Configuration Reference](#5-configuration-reference)
6. [Security](#6-security)
7. [MCP Server Configuration](#7-mcp-server-configuration)
8. [Persona Configuration](#8-persona-configuration)
9. [Operations & Monitoring](#9-operations--monitoring)
10. [Local Development Setup](#10-local-development-setup)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Introduction

SERA (Solutions Engine for Recommending AWS) is an AI-powered chatbot application that provides AWS-based solution recommendations through deep conversations. It tracks conversation stages to determine available tools and integrates with Model Context Protocol (MCP) servers for specialized tasks including architecture diagrams, SOW generation, AWS pricing, CloudFormation template generation, and partner funding suggestions.

### Key Components

- **Frontend**: React 18 with Cloudscape Design System v3, built with Vite, served via `serve` on port 7001
- **Backend**: Flask (Python 3.12) with Gunicorn, served on port 5001
- **AI Engine**: AWS Bedrock (Claude Sonnet 4) with Bedrock Guardrails for content filtering and PII protection
- **MCP Servers**: 9 specialized tool servers launched as local stdio processes
- **Database**: DynamoDB (chat sessions + support relationships)
- **Session Store**: ElastiCache Redis 7.1 with IAM authentication
- **Authentication**: Amazon Cognito (PLUS tier) integrated with ALB
- **Document Storage**: S3 with CloudFront signed URL distribution

### Conversation Flow

1. User creates a chat session selecting an assistant persona and customer persona
2. Messages are processed through Bedrock with conversation stage tracking
3. Stages progress: `INITIAL` → `GATHERING_INFO` → `SOLUTION_PROPOSED` → `SOLUTION_FINALIZED`
4. At `SOLUTION_FINALIZED`, tools for diagrams, pricing, SOW, funding, and CloudFormation become available
5. Solutions Architects can review chats via the Human-in-the-Loop (HITL) workflow

---

## 2. Architecture Overview

```
                         ┌─────────────┐
                         │  Route 53   │
                         │   DNS       │
                         └──────┬──────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ┌─────▼─────┐          ┌──────▼──────┐
              │ CloudFront │          │     ALB     │
              │ (docs.*)   │          │  (app.*)    │
              │ Signed URLs│          │ Cognito Auth│
              └─────┬──────┘          │ WAF + TLS   │
                    │                 └──────┬──────┘
              ┌─────▼─────┐                  │
              │  S3 Chat   │          ┌──────┴──────┐
              │  Documents │          │   EC2 ASG   │
              └────────────┘          │  (Private)  │
                                      ├─────────────┤
                                      │ Frontend    │
                                      │  :7001      │
                                      │ Backend     │
                                      │  :5001      │
                                      │ MCP Servers │
                                      │  (stdio)    │
                                      └──────┬──────┘
                                             │
                    ┌────────────┬────────────┼────────────┬──────────┐
                    │            │            │            │          │
              ┌─────▼────┐ ┌────▼────┐ ┌─────▼────┐ ┌────▼───┐ ┌───▼────┐
              │ DynamoDB  │ │ Redis   │ │ Bedrock  │ │   S3   │ │  SES   │
              │ (2 tables)│ │ (IAM)   │ │ Claude 4 │ │ (logs) │ │ Email  │
              └───────────┘ └─────────┘ └──────────┘ └────────┘ └────────┘
```

### Network Architecture

- **VPC**: `10.33.0.0/16` with 3-tier subnet design across 3 Availability Zones
  - Public subnets (3x /22): ALB only
  - Private instance subnets (3x /22): EC2 application servers
  - Private session DB subnets (3x /22): ElastiCache Redis
- **VPC Endpoints**: S3 (Gateway), DynamoDB (Gateway), Bedrock Runtime (Interface), Secrets Manager (Interface)
- **No SSH/RDP access** — management via SSM Session Manager only

### CloudFormation Stack Dependency Graph

```
01-route53
  └► 02-security
       ├► 03-vpc
       ├► 04-s3
       │    ├► 05-cloudfront
       │    └► 06-bedrock
       ├► 07-dynamodb
       ├► 08-elasticache
       └► 09-cognito-waf
            └► 10-alb-cognito
                 ├► 11-load-balancer-waf
                 └► 12-ec2role
                      └► 13-compute
                           └► 14-cloudtrail
                                └► 15-cloudtrail-monitoring
```

---

## 3. Prerequisites

### AWS Account Requirements

1. **AWS Account** with permissions to create CloudFormation stacks, IAM roles, VPCs, and all services listed above
2. **Bedrock Model Access**: Grant access to Anthropic Claude Sonnet 4 in **us-east-1**, **us-east-2**, and **us-west-2** via the AWS Console (Bedrock → Model access → Request access)
3. **SES**: Verify the sender email identity if email notifications are needed

### Domain Name

A publicly reachable domain name is required. Three subdomains will be created:
- `<domain>` + `www.<domain>` — Application (ALB)
- `auth.<domain>` — Cognito authentication
- `docs.<domain>` — CloudFront document distribution

**If using Route 53**: The deployment creates a hosted zone automatically.

**If using external DNS**: Delegate a subdomain to Route 53 by creating NS records in your parent domain pointing to the Route 53 hosted zone name servers. The deploy script will pause after stack 01 and display the NS records to copy.

### Tools Required

- AWS CLI v2 configured with appropriate credentials
- `jq` (JSON processor)
- `openssl` (for CloudFront key generation — handled automatically by deploy script)
- `git` (for code packaging)
- `zip` / `unzip`

### Parameters File

Edit `cloudformation/parameters.json` before deployment:

```json
{
  "StackPrefix": "sera",
  "PublicReachableDomainName": "your-domain.com",
  "PartnerName": "Your Company Name",
  "PartnerLogoUrl": "https://your-logo-url.com/logo.png",
  "PartnerEmail": "contact@your-company.com",
  "EnableExternalIdP": "false",
  "AlertEmail": "security-alerts@your-company.com"
}
```

| Parameter | Description | Required |
|---|---|---|
| `StackPrefix` | Unique prefix for all resources (3-21 chars, lowercase, starts with letter) | Yes |
| `PublicReachableDomainName` | Your public domain name | Yes |
| `PartnerName` | Company name displayed in SOW documents | Yes |
| `PartnerLogoUrl` | Logo URL for SOW branding | Yes |
| `PartnerEmail` | Contact email for SOW documents | Yes |
| `EnableExternalIdP` | Set to `true` to federate an external IdP with Cognito | No |
| `IdPProviderName` | Name for the federated IdP | If IdP enabled |
| `IdPProviderType` | `OIDC` or `SAML` | If IdP enabled |
| `IdPClientId` | OAuth2 client ID from your IdP | If OIDC |
| `IdPClientSecret` | OAuth2 client secret from your IdP | If OIDC |
| `IdPOIDCIssuer` | OIDC issuer URL | If OIDC |
| `IdPAuthorizeScopes` | OAuth2 scopes (default: `email openid profile`) | If IdP enabled |
| `AlertEmail` | Email for CloudTrail security alerts (SNS) | No |

---

## 4. Deployment

### 4.1 Automated Deployment

The recommended deployment method uses the automated deploy script:

```bash
cd cloudformation/
chmod +x deploy-sera.sh
./deploy-sera.sh
```

The script will:
1. Validate `parameters.json` (required fields, domain format, IdP parameters if enabled)
2. Deploy all 15 CloudFormation stacks sequentially
3. Auto-generate the CloudFront RSA-2048 key pair for signed URLs
4. Package and upload the application code to S3
5. Configure Bedrock Model Invocation Logging
6. Pause for manual steps when needed (e.g., DNS delegation)

### 4.2 Stack-by-Stack Reference

If deploying manually or troubleshooting, here is what each stack does:

#### Stack 01: Route 53 — DNS Foundation
- Creates a Route 53 Hosted Zone for your domain
- **After deployment**: If using a subdomain, add the NS records displayed to your parent domain's DNS. Wait for DNS propagation before proceeding.

#### Stack 02: Security — KMS, Certificates, Secrets
- Creates a single KMS symmetric key (annual rotation) used by all SERA resources
- Issues 3 ACM certificates (ALB, Cognito auth, CloudFront) with DNS validation
- Creates Flask session secret (auto-generated 64-char) in Secrets Manager
- Creates SES email identity
- **Note**: ACM certificates require DNS validation. The deploy script handles this via Route 53, but if using external DNS you must create the CNAME validation records manually.

#### Stack 03: VPC — Network Infrastructure
- Creates the 3-tier VPC with 9 subnets across 3 AZs
- Creates VPC Endpoints for S3, DynamoDB, Bedrock Runtime, and Secrets Manager
- Creates all Security Groups (ALB, EC2, Redis, VPC Endpoints)
- Enables VPC Flow Logs to CloudWatch

#### Stack 04: S3 — Storage Buckets
- Creates 3 buckets: log files, code artifacts, token usage data
- All buckets: KMS-encrypted, versioned, SSL-only bucket policies, public access blocked
- **After deployment**: The deploy script packages the code and uploads it to the code-artifacts bucket.

#### Stack 05: CloudFront — Document Distribution
- Creates the chat documents S3 bucket (KMS, CORS, versioned)
- Creates CloudFront distribution with Origin Access Control and signed URLs
- Stores the CloudFront private key in Secrets Manager (base64-encoded)
- Creates Route 53 record for `docs.<domain>`

#### Stack 06: Bedrock — AI Guardrails & Logging
- Creates Bedrock Guardrail with:
  - Content filters: HATE, INSULTS, SEXUAL, VIOLENCE, MISCONDUCT, PROMPT_ATTACK (all HIGH)
  - Word filter: Profanity BLOCK
  - PII protection: All 31 PII types set to ANONYMIZE (addresses, SSNs, credit cards, AWS keys, etc.)
  - Contextual grounding: 0.7 threshold
- Creates S3 bucket for Bedrock model invocation logs
- **After deployment**: Configure Bedrock Model Invocation Logging in the AWS Console using the exported bucket name and IAM role ARN. Use S3-only logging (CloudWatch has a 100K token limit per invocation).

#### Stack 07: DynamoDB — Database
- Creates 2 tables:
  - `${StackPrefix}-chats-data`: PK=user_id, SK=timestamp, GSIs on chat_id and stage+updated_at
  - `${StackPrefix}-support-relationship-data`: PK=seller_id, SK=support_member_id
- Both: KMS-encrypted, Point-in-Time Recovery enabled, PAY_PER_REQUEST billing

#### Stack 08: ElastiCache — Session Store
- Creates Redis 7.1 replication group (cache.m6g.large, 2 nodes, Multi-AZ)
- IAM-based authentication (no passwords)
- TLS encryption, KMS at-rest encryption
- Non-standard port 19703, dedicated subnets with deny-all egress security group

#### Stack 09: Cognito WAF — Authentication WAF (us-east-1)
- Creates WAF Web ACL for the Cognito hosted UI
- Rules: Auth rate limiting (100 req/5min), AWS Managed Common/Known Bad Inputs/IP Reputation
- **Note**: Deployed in COUNT mode for initial tuning. Transition to BLOCK for production after reviewing WAF logs.

#### Stack 10: ALB + Cognito — Load Balancer & Authentication
- Creates the internet-facing ALB with Cognito authentication integration
- Creates Cognito User Pool (PLUS tier) with:
  - Admin-only user creation
  - Advanced security: ENFORCED mode with compromised credential detection
  - Password policy: min 8 chars, upper+lower+numbers+symbols
  - Token config: Access=10min, ID=60min, Refresh=10hr
- Creates Route 53 A records for the domain
- Optionally configures external IdP federation (OIDC or SAML)
- **After deployment**: Add users to the Cognito User Pool in the AWS Console. Assign them to groups: `sera_sales_person` or `sera_solutions_architect`.

#### Stack 11: ALB WAF — Application WAF
- Creates WAF Web ACL for the ALB in BLOCK/ENFORCE mode
- Rules: General rate limit (2000 req/5min), API rate limit (1000 req/5min), AWS Managed Common/Known Bad Inputs/SQLi/Linux/IP Reputation

#### Stack 12: EC2 Role — IAM Permissions
- Creates the EC2 instance role with least-privilege permissions scoped to specific SERA resources
- Permissions include: S3 (per-bucket read/write split), Bedrock (Claude Sonnet 4 only), KMS, Secrets Manager (5 specific secrets), Cognito (group lookup), DynamoDB (2 tables), SSM Session Manager, CloudWatch Logs, SES, ElastiCache IAM auth

#### Stack 13: Compute — EC2 Auto Scaling Group
- Creates Launch Template: Amazon Linux 2023 ARM64, m7g.medium, 20GB gp3 encrypted, IMDSv2
- Creates ASG: min 2, max 6, across 3 private subnets, ELB health check
- Auto-scaling: scale up at CPU >70%, scale down at CPU <20%
- **UserData bootstrap** (fully automated):
  1. Installs system packages (Python, Node.js, Graphviz, Chromium, xmlsec1)
  2. Downloads and extracts application code from S3
  3. Templates `config-template.json` → `config.json` with all CloudFormation values
  4. Retrieves secrets from Secrets Manager (Cognito client secret, Flask key, CloudFront private key)
  5. Builds the frontend (`npm run build`)
  6. Sets up Python backend with `uv` (virtual env, dependencies, Playwright)
  7. Sets up all 9 MCP servers (each gets its own `uv venv` + `uv sync`)
  8. Starts systemd services

#### Stack 14: CloudTrail — Audit Logging
- Creates multi-region CloudTrail with log file validation
- Dual destination: CloudWatch Logs + S3 (KMS-encrypted, 7-year lifecycle)
- Captures management events + S3 data events for all SERA buckets

#### Stack 15: CloudTrail Monitoring — Security Alerts
- Creates 7 CloudWatch metric filters + alarms:
  - **CRITICAL**: CloudTrail deletion, CloudTrail logging stopped, Root account usage
  - **HIGH**: IAM role/policy changes, IAM access key creation, VPC network changes
  - **MEDIUM**: Security group modifications (threshold: 5 events)
- SNS topic for alert delivery
- **After deployment**: Confirm the SNS email subscription if `AlertEmail` was provided.

### 4.3 Post-Deployment Verification

1. **DNS**: Verify `https://<your-domain>` loads the Cognito login page
2. **Authentication**: Log in with a Cognito user assigned to `sera_sales_person` or `sera_solutions_architect`
3. **Chat**: Create a new chat and send a message — verify Bedrock responds
4. **Documents**: After reaching `SOLUTION_FINALIZED`, verify diagram/pricing documents are accessible via CloudFront signed URLs
5. **CloudTrail**: Check the CloudTrail console to verify events are being logged
6. **WAF**: Check WAF logs in CloudWatch to verify traffic is being inspected

### 4.4 Updating Application Code

To deploy code changes without rebuilding infrastructure:

```bash
cd cloudformation/
./update-code.sh
```

This creates a fresh zip from the current git branch, uploads it to S3, and triggers a rolling ASG update. Instances are replaced one at a time with zero downtime.

### 4.5 Deleting the Stack

Delete stacks in reverse order (15 → 01). **Important**: Empty all S3 buckets before deleting their stacks, or CloudFormation deletion will fail.

---

## 5. Configuration Reference

The backend configuration lives in `backend/config/config.json`, which is generated from `backend/config/config-template.json` during deployment. In production, the compute stack's UserData script performs `sed` replacements to populate all values from CloudFormation exports and Secrets Manager.

**Important**: `config.json` is in `.gitignore` and must never be committed to version control. It contains secrets (Cognito client secret, CloudFront key pair ID). The template file `config-template.json` uses placeholders and is safe to commit.

### 5.1 Authentication & Authorization

| Key | Description | Example |
|---|---|---|
| `AUTH_PROVIDER` | Identity provider | `amazon_cognito` |
| `AUTH_TYPE` | Protocol | `oauth2`, `saml`, or `both` |
| `AUTH_MODE` | Runtime auth mode | `alb` (production) or `oauth2` (development) |
| `RUN_MODE` | Application mode | `PROD` or `DEV` |
| `ENABLE_DEV_AUTH_BYPASS` | Skip auth in dev (requires `RUN_MODE=DEV`) | `false` |
| `COGNITO_DOMAIN` | Cognito custom domain | `auth.your-domain.com` |
| `COGNITO_CLIENT_ID` | Cognito app client ID | Auto-populated |
| `COGNITO_USER_POOL_ID` | Cognito user pool ID | Auto-populated |
| `AUTH_FRONTEND_URL` | Frontend URL for auth redirects | `https://your-domain.com` |
| `ENABLE_EXTERNAL_IDP` | Enable federated IdP | `true` or `false` |

**OAUTH2_SETTINGS** (used in development mode):

| Key | Description |
|---|---|
| `provider` | `cognito` |
| `client_id` | Cognito app client ID |
| `client_secret` | Cognito app client secret |
| `user_pool_id` | Cognito user pool ID |
| `region` | AWS region |
| `domain` | Cognito domain URL |
| `redirect_uri` | OAuth2 callback URL |
| `scopes` | `["openid", "email", "profile"]` |

**SAML_SETTINGS** (for direct SAML integration, not recommended):

| Key | Description |
|---|---|
| `strict` | Enable strict SAML validation |
| `sp.entityId` | Service Provider entity ID |
| `sp.assertionConsumerService.url` | ACS callback URL |
| `idp.entityId` | Identity Provider entity ID |
| `idp.singleSignOnService.url` | IdP SSO URL |
| `idp.x509cert` | IdP X.509 certificate |

**Group Mappings** (`SAML_GROUP_MAPPINGS` / `OAUTH2_GROUP_MAPPINGS`):

Maps IdP group identifiers to application roles:

| Application Role | Description |
|---|---|
| `sera_sales_person` | Can create chats, interact with AI, submit for review |
| `sera_sales_manager` | Same as sales_person |
| `sera_solutions_architect` | Can review chats (HITL), approve documents, access supported sellers' chats |
| `sera_sa_manager` | SA permissions + management capabilities |
| `sera_cross_customer_solutions_architect` | SA permissions across all customers |
| `sera_proserve` | Professional services role |
| `sera_project_manager` | Project management role |

### 5.2 AWS & Infrastructure

| Key | Description | Example |
|---|---|---|
| `AWS_REGION` | Primary AWS region | `us-east-1` |
| `STACK_PREFIX` | CloudFormation stack prefix | `sera` |
| `BEDROCK_MODEL_ID` | Bedrock model identifier | `us.anthropic.claude-sonnet-4-6` |
| `BEDROCK_CITATIONS_ENABLED` | Enable Bedrock citations | `false` |
| `BEDROCK_RETRY_CONFIG.max_retries` | Max Bedrock API retries | `30` |
| `BEDROCK_RETRY_CONFIG.throttle_delay_seconds` | Delay between retries | `30` |
| `BEDROCK_USE_PROFILE` | Use named AWS profile for Bedrock | `false` |
| `BEDROCK_AWS_PROFILE` | Named profile (if above is true) | `""` |

### 5.3 Database & Cache

| Key | Description | Example |
|---|---|---|
| `DYNAMODB_TABLE_NAME` | Chat sessions table | `sera-chats-data` |
| `DYNAMODB_RELATIONSHIPS_TABLE_NAME` | Support relationships table | `sera-support-relationship-data` |
| `REDIS_HOST` | Redis endpoint | `localhost` or ElastiCache endpoint |
| `REDIS_PORT` | Redis port | `6379` (local) or `19703` (production) |
| `REDIS_IAM_ENABLED` | Use IAM auth for Redis | `true` |
| `REDIS_REPLICATION_GROUP_ID` | ElastiCache replication group ID | Auto-populated |
| `REDIS_IAM_USER_NAME` | ElastiCache IAM user name | Auto-populated |

### 5.4 Storage & Documents

| Key | Description | Example |
|---|---|---|
| `S3_UPLOAD_BUCKET` | Chat documents bucket | `sera-chat-docs-<account-id>` |
| `S3_LOGGING_BUCKET` | Application log files bucket | `sera-logfiles-<account-id>` |
| `S3_LOGGING_PREFIX` | Log file prefix | `logs` |
| `S3_TOKEN_USAGE_DATA_BUCKET` | Bedrock token usage audit bucket | `sera-token-usage-data-<account-id>` |
| `CLOUDFRONT_DOMAIN` | CloudFront distribution URL | `https://docs.your-domain.com` |
| `CLOUDFRONT_KEY_PAIR_ID` | CloudFront public key ID | Auto-populated |
| `CLOUDFRONT_PRIVATE_KEY_PATH` | Path to CloudFront private key on EC2 | `/home/ec2-user/sera-cloudfront-keys/sera-cloudfront-private-key.pem` |
| `SINGED_URL_TIME` | Signed URL expiry in minutes | `60` |
| `DELETE_LOCAL_FILE_AFTER_BACKUP_S3` | Delete local files after S3 upload | `False` |

### 5.5 Logging

| Key | Description | Example |
|---|---|---|
| `LOG_LEVEL` | Application log level | `INFO`, `DEBUG`, `WARNING` |
| `LOGGING_MODE` | Log destination | `cloudwatch` (production) or `local` (development) |

In production, logs go to CloudWatch Log Group `${StackPrefix}-ec2-application-logs` (KMS-encrypted, 10-year retention). In development, logs go to `backend/backend.log` (10MB rotating, 5 backups).

### 5.6 SOW Configuration

The `SOW_CONFIG` block controls Statement of Work document generation:

| Key | Description |
|---|---|
| `enabled` | Enable/disable SOW generation |
| `default_partner` | Partner branding (name, logo_url, contact_email) |
| `technical_personnel` | 11 role definitions with hourly rates ($150-$275/hr) and hours per sprint |
| `template_types` | 3 SOW templates: `aws_map` (12wk), `aws_modernization` (12wk), `standard_migration` (4wk) |
| `terms_and_conditions` | Legal text for payment/execution and liability/confidentiality |
| `pdf_settings` | Page size, margins, font family |
| `s3_settings` | Output filename and folder structure (`{chat_id}/ScopeOfWork.pdf`) |
| `review_settings` | Require review, auto-approve, reviewer roles |
| `default_assumptions` | Standard project assumptions (4 items) |
| `default_exclusions` | Standard scope exclusions (4 items) |

### 5.7 File Upload Classification

The `FILE_CLASSIFICATION_CONFIG` block controls document upload handling:

- **allowed_extensions**: 14 file types (txt, csv, json, pdf, docx, xlsx, pptx, md, jpg, jpeg, png, gif, bmp, svg)
- **rules**: 8 classification categories with keywords, extensions, and priority
- **assistant_configs**: Per-persona upload requirements (e.g., `apn_funding_assistant` requires SOW + architecture diagram)
- **MAX_FILE_SIZE**: 10MB (enforced in frontend)

---

## 6. Security

When you build systems on AWS infrastructure, security responsibilities are shared between you and AWS. This [shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/) reduces your operational burden because AWS operates, manages, and controls the components including the host operating system, the virtualization layer, and the physical security of the facilities in which the services operate. For more information about AWS security, visit [AWS Cloud Security](https://aws.amazon.com/security/).

### 6.1 Authentication and Authorization

All SERA API operations are protected through authentication requirements. In production, the Application Load Balancer enforces Amazon Cognito authentication before any request reaches the application. Unauthenticated users are redirected to the Cognito hosted UI login page. By allowing customers to configure their own identity provider (via OIDC or SAML federation with Cognito), they have full control over the configuration of their authentication system.

All JWTs used for authentication are validated through the ALB Cognito integration. The ALB injects verified user claims (`x-amzn-oidc-data` header) into every request after successful authentication. The backend extracts user identity and group membership from these claims.

The authentication flow is protected by:
- OAuth 2.0 authorization code flow (no implicit grants)
- Cognito PLUS tier with advanced security ENFORCED (compromised credential detection, account takeover protection)
- `PreventUserExistenceErrors: ENABLED` to prevent user enumeration
- Admin-only user creation (no self-registration)
- Session cookies with HttpOnly, Secure, and SameSite attributes
- Sessions stored in encrypted Redis (ElastiCache) with IAM authentication

Authorization is enforced at the application layer through role-based access control (RBAC). Users must be assigned to at least one Cognito group to access the application. The backend enforces role requirements on every route via decorators:

| Decorator | Required Roles |
|---|---|
| `@login_required` | Any valid role (401 if unauthenticated, 403 if no role) |
| `@sales_only` | `sera_sales_person` or `sera_sales_manager` |
| `@sa_only` | `sera_solutions_architect`, `sera_sa_manager`, or `sera_cross_customer_solutions_architect` |
| `@sa_manager_only` | `sera_sa_manager` |
| `@sow_reviewer` | `sera_solutions_architect` or `sera_sa_manager` |
| `@require_ownership_or_sa` | Resource owner OR any SA role |

Chat access control ensures users can only access their own chats. Solutions Architects can access chats of sellers they have a support relationship with (stored in the support-relationship DynamoDB table).

For more information, see [Managing users in Amazon Cognito user pools](https://docs.aws.amazon.com/cognito/latest/developerguide/managing-users.html).

### 6.2 Rotate Credential Keys and Secrets

This solution stores secrets in AWS Secrets Manager with the following rotation configuration:

| Secret | Rotation | Method |
|---|---|---|
| Flask session signing key | **Automatic — 90 days** | Lambda rotation function generates new key, then triggers rolling ASG instance refresh |
| Redis auth token | **Automatic — 900 seconds** | IAM-based authentication (SigV4 tokens) via `ElastiCacheIAMProvider` — no static secret |
| KMS encryption key | **Automatic — annual** | AWS KMS automatic key rotation |
| Cognito client secret | Not rotatable | Cognito client secrets are immutable; requires new client creation |

**Secrets requiring manual rotation**: Operators should establish a manual rotation schedule (recommended: annually or per your organization's security policy) for the following:

- **Nova Act API key** (`${StackPrefix}-nova-act-api-secret`): Obtain a new key from the Nova Act service, update the secret value in Secrets Manager, then trigger a code deployment (`update-code.sh`).
- **External IdP client secret** (`${StackPrefix}-v2-idp-client-secret`, if federated IdP is enabled): Rotate in your IdP first, then update in Secrets Manager and redeploy.
- **CloudFront private key** (`${StackPrefix}-cloudfront-private-key`): Generate a new RSA-2048 key pair, upload the new public key to CloudFront, update the key group, update the secret in Secrets Manager with the new private key (base64-encoded), then redeploy. Active signed URLs issued with the old key will stop working.

**Secrets that do NOT require rotation**:
- **Cognito client secret** (`${StackPrefix}-cognito-client-secret`): Immutable — tied to the Cognito app client.
- **Redis auth token** (`${StackPrefix}-redis-auth-token`): Exists as a placeholder but is not used at runtime. SERA uses IAM-based authentication for Redis.

For more information, see [Rotating AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html).

### 6.3 Elastic Load Balancing

This solution deploys an internet-facing Application Load Balancer with the following TLS configuration:

- **TLS policy**: `ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09` — TLS 1.3 with hybrid post-quantum ML-KEM key exchange (SecP256r1MLKEM768, SecP384r1MLKEM1024, X25519MLKEM768), with GCM-only TLS 1.2 fallback (no CBC ciphers, no SHA-1)
- **Deletion protection**: Enabled
- **Invalid header fields**: Dropped
- **HTTP/2**: Enabled
- **Access logs**: Enabled to S3 (AES256-encrypted, versioned, 90-day retention, SSL-only bucket policy)
- **HTTP → HTTPS**: 301 redirect on port 80

The ALB integrates with Amazon Cognito for authentication on both the frontend (default action) and backend (`/api/*` path rule) listeners.

For more information, see [Security in Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/security.html).

### 6.4 Amazon CloudFront

This solution deploys a CloudFront distribution to serve chat documents stored in an Amazon S3 bucket. To help reduce latency and improve security, the distribution uses Origin Access Control (OAC) to restrict direct access to the S3 bucket — only CloudFront can read the objects. All document URLs are signed using RSA-2048 CloudFront signed URLs with configurable expiry (default: 60 minutes).

The CloudFront distribution is configured with:
- Custom domain (`docs.<domain>`) with ACM certificate
- `TLSv1.2_2021` minimum protocol version with automatic post-quantum support
- HTTPS-only viewer protocol policy
- Custom cache policy

For more information, see [Restricting access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) and [Using alternate domain names and HTTPS](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-values-specify.html#DownloadDistValues-security-policy).

### 6.5 Amazon S3

This solution deploys 6 S3 buckets, all configured with the following security controls:

- **Encryption at rest**: KMS server-side encryption using a customer managed key with automatic annual rotation and Bucket Key enabled
- **TLS enforcement**: Bucket policy denies all `s3:*` actions when `aws:SecureTransport: false`, enforcing TLS for all connections
- **Public access blocked**: `BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, `RestrictPublicBuckets` all set to `true`
- **Versioning**: Enabled on all buckets
- **Access logging**: Enabled on all buckets (except the log bucket itself, to prevent recursive logging)
- **Lifecycle policies**: Transition to Standard-IA at 30 days, Glacier at 90 days; incomplete multipart uploads aborted after 7 days

It is recommended that you review the [S3 security best practices guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html) and further restrict access as needed after deployment.

### 6.6 AWS WAF

This solution deploys two AWS WAF Web ACLs:

**ALB WAF (ENFORCE/BLOCK mode)**:
1. General rate limit: 2000 requests per 5 minutes per IP (BLOCK)
2. API rate limit: 1000 requests per 5 minutes per IP on `/api/*` (BLOCK)
3. AWS Managed Rules: Common Rule Set, Known Bad Inputs, SQLi, Linux, IP Reputation List (all ENFORCE)

**Cognito WAF (COUNT mode)**:
1. Auth rate limit: 100 requests per 5 minutes per IP on `/oauth2/` and `/login` (COUNT)
2. AWS Managed Rules: Common Rule Set, Known Bad Inputs, IP Reputation List (all COUNT)

**Note**: The Cognito WAF is deployed in COUNT mode for initial tuning. After reviewing WAF logs and confirming no false positives, transition to BLOCK mode for production by updating `09-cognito-waf.yaml`.

Both WAF ACLs log to KMS-encrypted CloudWatch Log Groups with 10-year retention.

For more information, see [Getting started with AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/getting-started.html).

### 6.7 CloudWatch Alarms

This solution deploys 7 CloudWatch security alarms that monitor CloudTrail events for suspicious activity:

| Alarm | Severity | Threshold | Description |
|---|---|---|---|
| CloudTrail Deleted | CRITICAL | ≥1 in 60s | Attacker covering tracks |
| CloudTrail Logging Stopped | CRITICAL | ≥1 in 60s | Audit evasion |
| Root Account Used | CRITICAL | ≥1 in 60s | Root account should never be used |
| IAM Role/Policy Changed | HIGH | ≥1 in 300s | Privilege escalation |
| IAM Access Key Created | HIGH | ≥1 in 300s | Credential creation |
| VPC Network Changed | HIGH | ≥1 in 300s | Network tampering |
| Security Group Modified | MEDIUM | ≥5 in 300s | Firewall changes |

Alarms publish to an SNS topic. Provide an `AlertEmail` in `parameters.json` to receive notifications. It is recommended that you create additional CloudWatch alarms specific to your operational requirements to continuously verify your security properties and controls post-deployment.

For more information, see [Using Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html).

### 6.8 Customer Managed AWS KMS Keys

This solution uses encryption at rest for securing data and employs a customer managed KMS key for all application data. This single symmetric key (with automatic annual rotation and a 7-day pending deletion window) is used to encrypt:

- S3 buckets (all 6)
- DynamoDB tables (both)
- ElastiCache Redis
- Secrets Manager secrets
- CloudWatch Log Groups
- EBS volumes
- Bedrock invocation logs

This approach allows you to administer your own encryption key, offering a greater level of control and visibility over your data encryption. You can manage key policies, enable/disable the key, and audit key usage via CloudTrail.

For more information, see [AWS KMS concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#kms_keys) and [AWS KMS cryptographic details](https://docs.aws.amazon.com/kms/latest/cryptographic-details/basic-concepts.html).

### 6.9 Log Retention

This solution captures application and service logs by creating CloudWatch Log Groups in your account. All log groups are configured with a 10-year (3650-day) retention period:

| Log Group | Content | Retention |
|---|---|---|
| `${StackPrefix}-ec2-application-logs` | Backend application logs | 10 years |
| `${StackPrefix}-cloudtrail` | CloudTrail audit events | 10 years |
| `${StackPrefix}-vpc-flowlogs` | VPC network traffic | 10 years |
| `aws-waf-logs-${StackPrefix}-alb` | ALB WAF request logs | 10 years |
| `aws-waf-logs-${StackPrefix}-cognito` | Cognito WAF request logs | 10 years |

Additionally, CloudTrail events are stored in S3 with a 7-year lifecycle (Standard → IA → Glacier), and ALB access logs are stored in S3 with 90-day retention.

You can adjust the retention period for each log group based on your compliance requirements. Valid values range from 1 day to 10 years.

For more information, see [Amazon CloudWatch Logs features](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html#cloudwatch-logs-features).

### 6.10 Security Groups

The security groups created in this solution are designed to control and isolate network traffic between the ALB, EC2 application servers, ElastiCache Redis, and VPC Endpoints:

| Security Group | Inbound | Outbound |
|---|---|---|
| ALB SG | 80/443 from 0.0.0.0/0 | 5001/7001 → EC2 SG, 443 → Cognito |
| EC2 SG | 5001/7001 from ALB SG only | Redis 19703 → VPC, 443 → S3/DynamoDB prefix lists, HTTPS/DNS → internet |
| Redis SG | 19703 from EC2 SG only | **Deny all** (loopback only) |
| VPC Endpoint SG | 443 from VPC CIDR | DNS 53, HTTPS 443 |

Key design decisions:
- No SSH/RDP ports open — all management via SSM Session Manager
- Redis has explicit deny-all egress (cannot initiate outbound connections)
- EC2 uses AWS prefix lists for DynamoDB/S3 (not open CIDR ranges)
- VPC Endpoints keep Bedrock, Secrets Manager, DynamoDB, and S3 traffic off the public internet

It is recommended that you review the security groups and further restrict access as needed after deployment.

For more information, see [Security groups for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html).

### 6.11 Amazon Bedrock Guardrails

This solution deploys Amazon Bedrock Guardrails to provide customizable safeguards on top of the native protections of the foundation model:

- **Content Filters**: HATE, INSULTS, SEXUAL, VIOLENCE, MISCONDUCT all set to HIGH on both input and output. PROMPT_ATTACK set to HIGH on input.
- **Word Filter**: Profanity BLOCK on input and output
- **PII Protection**: All 31 PII entity types (SSN, credit cards, AWS keys, addresses, phone numbers, etc.) set to ANONYMIZE on both input and output
- **Contextual Grounding**: 0.7 threshold for grounding and relevance checks

The guardrail is applied to all Bedrock model invocations via the persona configuration. You can customize the guardrail settings in the AWS Bedrock console or by updating `06-bedrock.yaml`.

For more information, see [Amazon Bedrock Guardrails](https://aws.amazon.com/bedrock/guardrails/).

### 6.12 Amazon DynamoDB

This solution deploys two DynamoDB tables with the following security configuration:

- **Encryption at rest**: Customer managed KMS key
- **Point-in-Time Recovery (PITR)**: Enabled (35-day recovery window)
- **Billing mode**: PAY_PER_REQUEST (no capacity planning needed)
- **VPC Endpoint**: Gateway endpoint restricts DynamoDB access to within the VPC, scoped to `${StackPrefix}-*` tables

Access to DynamoDB is controlled through the EC2 instance role, which limits operations to the two specific SERA tables and their indexes.

For more information, see [Security in Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/security.html).

### 6.13 IAM Least Privilege

The EC2 instance role follows least-privilege principles:
- S3: Different permission sets per bucket (CRUD on chat-docs, write-only on logs/token-usage, read-only on code-artifacts)
- Bedrock: Scoped to `anthropic.claude-sonnet-4*` models and the specific guardrail
- Secrets Manager: Limited to 5 specific secret ARNs
- DynamoDB: Scoped to 2 specific tables and their indexes
- Cognito: Only `AdminListGroupsForUser` on the specific user pool
- No `iam:*`, `kms:*`, or `cloudformation:*` wildcards

---

## 7. MCP Server Configuration

MCP (Model Context Protocol) servers provide specialized tools to the AI assistant. They are configured in `backend/config/mcp.json` and launched as local stdio processes by the backend.

Each server runs in its own Python virtual environment under `mcp_servers/src/<server-name>/`. During deployment, the compute stack's UserData script runs `uv venv` + `uv sync` for each server.

### 7.1 Available Servers

| Server | Purpose | Key Tools |
|---|---|---|
| `aws-diagram-mcp-server` | Architecture diagram generation | Creates diagrams, uploads to S3 |
| `cost-analysis-mcp-server` | Cost estimation and analysis | Generates cost reports |
| `pricing-calculator-mcp-server` | AWS pricing calculator links | Creates pricing calculator sessions |
| `apn-funding-wizard-mcp-server` | APN funding program recommendations | Funding eligibility analysis |
| `aws-cloudformation-generation-mcp-server` | IaC template generation | Generate, validate, security scan CFN templates |
| `sow-generator-mcp-server` | Statement of Work documents | Generate SOW, calculate costs, modify documents |
| `aws-service-validation-mcp-server` | AWS service validation | Validate services, search documentation |
| `funding-reviewer-mcp-server` | POC funding compliance analysis | Analyze funding requests against compliance rules |
| `aws-well-architected-framework-mcp-server` | WAFR assessments | 6 WAFR assessment tools |

### 7.2 Server Configuration Format

Each server entry in `mcp.json`:

```json
{
  "server-name": {
    "command": "uv",
    "args": ["run", "--project", "../mcp_servers/src/<server-name>", "awslabs.<server-module>"],
    "alwaysAllow": ["tool_name_1", "tool_name_2"],
    "env": {
      "CUSTOM_VAR": "value"
    }
  }
}
```

- `command` / `args`: How to launch the server (always via `uv run`)
- `alwaysAllow`: Tools that don't require user confirmation
- `env`: Environment variables injected at startup

The backend automatically injects `FASTMCP_LOG_LEVEL`, `BACKEND_LOG_FILE`, and `BACKEND_LOG_LEVEL` into all servers.

### 7.3 Adding a New MCP Server

1. Create the server under `mcp_servers/src/<new-server-name>/`
2. Add a `pyproject.toml` with dependencies
3. Add the server entry to `backend/config/mcp.json`
4. The compute stack UserData will automatically set up the server on next deployment

---

## 8. Persona Configuration

Personas are defined in `backend/config/personas.py` and control the AI assistant's behavior, available tools, and access control.

### 8.1 Assistant Personas

| ID | Name | Status | Guardrail | Access Groups |
|---|---|---|---|---|
| `aws_solutions_assistant` | AWS Solutions Assistant | Active | None | sales_person, solutions_architect, sales_manager, sa_manager |
| `aws_well_architected_framework_assistant` | WAFR Assistant | Active | None | (same) |
| `aws_step_assistant` | AWS Training Assistant | Active | None | (same) |
| `apn_funding_assistant` | APN Funding Assistant | Active | None | (same) |
| `apn_assistant` | APN Assistant | Inactive | `sera_apn_asst_gdrl` | (same) |
| `aws_genai_pdm_assistant` | GenAI PDM Assistant | Inactive | `n5fj7rcjn66u` | (same) |

Each persona has a system prompt that defines its behavior, conversation stages, and tool usage rules. The `aws_solutions_assistant` is the primary persona with the full conversation lifecycle.

### 8.2 Customer Personas

| ID | Name |
|---|---|
| `partner_alliance_manager` | Partner Alliance Manager |
| `partner_account_manager` | Partner Account Manager |
| `partner_tech_expert` | Partner Technical Expert |
| `customer_business_exec` | Customer Business Executive |
| `customer_tech_exec` | Customer Technical Executive |
| `customer_tech_sme` | Customer Technical SME |

Customer personas provide context to the AI about who the seller is interacting with, adjusting the conversation style and depth.

### 8.3 Customizing Personas

To add or modify personas, edit `backend/config/personas.py`:

```python
"your_persona_id": AssistantPersona(
    name="Display Name",
    system_prompt="""Your system prompt here...""",
    short_description="Brief description for the UI",
    knowledgebase_id="",           # Bedrock Knowledge Base ID (optional)
    guardrail="guardrail-id",      # Bedrock Guardrail ID (optional)
    guardrail_version="1",         # Guardrail version
    active='YES',                  # YES or NO
    allowed_groups=["sera_sales_person", "sera_solutions_architect"]
)
```

---

## 9. Operations & Monitoring

### 9.1 Service Architecture

SERA runs as two systemd services managed by `sera.target`:

**sera-backend.service**:
- Gunicorn with `cpu_count * 2 + 1` workers (3 on m7g.medium), 2 threads each
- 300-second timeout (accommodates Bedrock streaming responses)
- Worker recycling: max 1000 requests with jitter
- Security: `NoNewPrivileges=true`, `PrivateTmp=true`
- File limits: NOFILE=65536, NPROC=4096

**sera-frontend.service**:
- Rebuilds frontend on every service start (`ExecStartPre: npm run build`)
- Serves static files via `serve` on port 7001
- Security headers configured in `frontend/serve.json` (HSTS, CSP, X-Frame-Options)

### 9.2 Logging

**Production (LOGGING_MODE=cloudwatch)**:
- Log Group: `${StackPrefix}-ec2-application-logs`
- Log Stream: `${StackPrefix}-backend-${instance-id}`
- Format: `%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s`
- Send interval: 5 seconds
- Retention: 10 years (3650 days)
- Noisy libraries (werkzeug, urllib3, botocore, boto3) suppressed to WARNING

**Accessing logs**:
```bash
# Via CloudWatch Logs Insights
fields @timestamp, @message
| filter @logStream like /sera-backend/
| sort @timestamp desc
| limit 100

# Via SSM Session Manager on the instance
journalctl -u sera-backend -f
journalctl -u sera-frontend -f
```

### 9.3 Health Checks

- **ALB Health Check**: `GET /api/health` on port 5001 (backend target group)
- **Frontend**: Static file serving on port 7001
- **ASG**: ELB health check with 900-second grace period (allows for bootstrap)

### 9.4 Scaling

- **Auto Scaling**: CPU-based, scale up at >70% (+1) or >90% (+2), scale down at <20% (-1), 5-minute cooldown
- **Instance type**: m7g.medium (ARM64, 1 vCPU, 4GB RAM) — suitable for moderate workloads
- **Capacity**: Min 2, Max 6 instances across 3 AZs

### 9.5 Backup & Recovery

- **DynamoDB**: Point-in-Time Recovery enabled on both tables (35-day window)
- **S3**: Versioning enabled on all buckets; lifecycle policies transition to IA (30d) → Glacier (90d)
- **CloudTrail**: S3 bucket with 7-year retention
- **Redis**: Multi-AZ with automatic failover (session data is ephemeral)

### 9.6 Instance Access

There is no SSH access. Use SSM Session Manager:

```bash
# List instances
aws ec2 describe-instances --filters "Name=tag:Application,Values=SERA-${StackPrefix}" --query 'Reservations[].Instances[].InstanceId'

# Connect
aws ssm start-session --target <instance-id>
```

---

## 10. Local Development Setup

### 10.1 Prerequisites

- Python 3.12+ with `uv` (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 20+ with npm (`brew install node`)
- Redis (`brew install redis` and `brew services start redis`)
- AWS credentials in `~/.aws/credentials` (default profile with permissions matching the EC2 role)

### 10.2 Backend Setup

```bash
# Clone and navigate
cd backend/

# Copy the dev startup script
cp ../systemd/start-dev.sh ./start-dev.sh
chmod +x start-dev.sh

# Edit start-dev.sh to set:
#   AppPath — path to your backend directory
#   CloudFrontPrivateKeyPath — path to your CloudFront private key
#   Partner info (name, logo, email)

# Run (this generates config.json from CloudFormation exports and starts Flask)
./start-dev.sh
```

The script pulls configuration from CloudFormation exports via `aws cloudformation list-exports`, retrieves secrets from Secrets Manager, and templates `config-template.json` → `config.json`.

### 10.3 Frontend Setup

```bash
cd frontend/

# Install dependencies
npm install

# Start dev server (proxies /api/* to localhost:5001)
npm run dev
```

The Vite dev server runs on port 7001 and proxies all `/api/*` requests to the backend on port 5001.

### 10.4 Key Differences from Production

| Aspect | Production | Development |
|---|---|---|
| Auth mode | `alb` (ALB Cognito headers) | `oauth2` (Flask session) |
| Server | Gunicorn (multi-worker) | Flask dev server (single process) |
| Logging | CloudWatch | Local file (`backend.log`) |
| Redis | ElastiCache with IAM auth + TLS | Local Redis (no auth, no TLS) |
| Cookies | Secure=True, SameSite=Lax | Secure=False, SameSite=None |
| Frontend | `serve` (static) | Vite dev server (HMR) |

### 10.5 Stacks Not Required for Local Development

You do not need to deploy these stacks for local development:
- `11-load-balancer-waf.yaml` (ALB WAF)
- `13-compute.yaml` (EC2 instances)

All other stacks are needed because the backend connects to DynamoDB, Redis (can be local), S3, Bedrock, and Cognito.

---

## 11. Troubleshooting

### Common Issues

**Deployment fails at stack 02 (certificates)**:
- ACM certificates require DNS validation. If using external DNS, create the CNAME records shown in the ACM console.
- The Cognito auth certificate (`auth.<domain>`) must be in us-east-1.

**Application not loading after deployment**:
- Check ASG instance health: instances may still be bootstrapping (up to 15 minutes)
- Check UserData logs: `aws ssm start-session --target <instance-id>`, then `cat /var/log/cloud-init-output.log`
- Verify target group health in the EC2 console

**Authentication redirect loop**:
- Verify Cognito callback URLs include your domain
- Check that the Cognito custom domain (`auth.<domain>`) DNS resolves correctly
- Verify the ALB listener has the Cognito authentication action configured

**Bedrock not responding**:
- Verify model access is granted in us-east-1, us-east-2, and us-west-2
- Check the Bedrock VPC Endpoint is healthy
- Review CloudWatch logs for throttling errors (the app retries up to 30 times with 30s delays)

**MCP server tools not available**:
- Check backend logs for MCP initialization errors
- Verify each MCP server's `uv.lock` is present and dependencies are installed
- On the instance: `ls /home/ec2-user/sera-*/mcp_servers/src/*/` to verify server directories exist

**Redis connection failures**:
- Production: Verify the EC2 security group allows outbound to Redis SG on port 19703
- Development: Verify local Redis is running (`redis-cli ping`)
- IAM auth issues: Check that the EC2 role has `elasticache:Connect` permission

**CloudFront signed URLs not working**:
- Verify the private key file exists at the configured path with correct permissions (600)
- Check that `CLOUDFRONT_KEY_PAIR_ID` matches the public key in CloudFront
- Verify the CloudFront distribution is deployed and the `docs.<domain>` DNS resolves

**WAF blocking legitimate requests**:
- Check WAF logs in CloudWatch (`aws-waf-logs-${StackPrefix}-alb`)
- The API rate limit is 1000 req/5min per IP — increase if needed in `11-load-balancer-waf.yaml`

### Log Locations

| Log | Location | Retention |
|---|---|---|
| Application | CloudWatch: `${StackPrefix}-ec2-application-logs` | 10 years |
| CloudTrail | CloudWatch: `${StackPrefix}-cloudtrail` + S3 | 10 years / 7 years |
| VPC Flow Logs | CloudWatch: `${StackPrefix}-vpc-flowlogs` | 10 years |
| ALB WAF | CloudWatch: `aws-waf-logs-${StackPrefix}-alb` | 10 years |
| Cognito WAF | CloudWatch: `aws-waf-logs-${StackPrefix}-cognito` | 10 years |
| ALB Access | S3: `${StackPrefix}-alb-access-logs-<account-id>` | 90 days |
| Bedrock Invocations | S3: `${StackPrefix}-bedrock-invocation-logs-<account-id>` | IA@30d, Glacier@90d |
| Instance bootstrap | `/var/log/cloud-init-output.log` on EC2 | Instance lifetime |
| systemd services | `journalctl -u sera-backend` / `journalctl -u sera-frontend` | Instance lifetime |
