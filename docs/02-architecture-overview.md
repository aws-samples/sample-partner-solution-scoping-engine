# SERA Architecture Overview

## System Architecture

SERA implements a cloud-native, multi-tier architecture on AWS with modular components for scalability, security, and maintainability.

### Architecture Principles

- **Modularity**: MCP servers provide specialized functionality
- **Scalability**: Auto Scaling Groups with load balancing
- **Security**: Defense in depth with multiple security layers
- **Performance**: CDN, caching, and optimized data access patterns
- **Reliability**: Multi-AZ deployment with health monitoring

## Detailed Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                            Edge & Security Layer                           │ │
│  │                                                                             │ │
│  │  Route 53 → CloudFront → WAF → Certificate Manager                         │ │
│  │     (DNS)      (CDN)    (Security)    (SSL/TLS)                           │ │
│  └─────────────────────────────┬───────────────────────────────────────────────┘ │
│                                │                                                 │
│  ┌─────────────────────────────▼───────────────────────────────────────────────┐ │
│  │                            Network Layer                                   │ │
│  │                                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                          VPC                                        │   │ │
│  │  │                                                                     │   │ │
│  │  │  ┌─────────────────┐                    ┌─────────────────────────┐ │   │ │
│  │  │  │  Public Subnets │                    │    Private Subnets      │ │   │ │
│  │  │  │                 │                    │                         │ │   │ │
│  │  │  │  ┌─────────────┐│                    │ ┌─────────────────────┐ │ │   │ │
│  │  │  │  │     ALB     ││                    │ │    EC2 Instances    │ │ │   │ │
│  │  │  │  │             ││                    │ │   (Auto Scaling)    │ │ │   │ │
│  │  │  │  └─────────────┘│                    │ │                     │ │ │   │ │
│  │  │  │  ┌─────────────┐│                    │ │ ┌─────────────────┐ │ │ │   │ │
│  │  │  │  │ NAT Gateway ││                    │ │ │   Frontend      │ │ │ │   │ │
│  │  │  │  └─────────────┘│                    │ │ │   (React SPA)   │ │ │ │   │ │
│  │  │  └─────────────────┘                    │ │ └─────────────────┘ │ │ │   │ │
│  │  │                                         │ │ ┌─────────────────┐ │ │ │   │ │
│  │  │                                         │ │ │    Backend      │ │ │ │   │ │
│  │  │                                         │ │ │  (Flask API)    │ │ │ │   │ │
│  │  │                                         │ │ └─────────────────┘ │ │ │   │ │
│  │  │                                         │ │ ┌─────────────────┐ │ │ │   │ │
│  │  │                                         │ │ │   MCP Servers   │ │ │ │   │ │
│  │  │                                         │ │ │   (6 servers)   │ │ │ │   │ │
│  │  │                                         │ │ └─────────────────┘ │ │ │   │ │
│  │  │                                         │ └─────────────────────┘ │ │   │ │
│  │  │                                         └─────────────────────────┘ │   │ │
│  │  └─────────────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                            Data & Services Layer                           │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │     S3      │  │  DynamoDB   │  │ ElastiCache │  │     Bedrock     │   │ │
│  │  │             │  │             │  │             │  │                 │   │ │
│  │  │ • Documents │  │ • Chat Data │  │ • Sessions  │  │ • Claude 4.0    │   │ │
│  │  │ • Logs      │  │ • Metadata  │  │ • Cache     │  │ • Cross-region  │   │ │
│  │  │ • Artifacts │  │ • User Data │  │             │  │                 │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐                                         │ │
│  │  │   Cognito   │  │ VPC Endpoints│                                        │ │
│  │  │             │  │             │                                         │ │
│  │  │ • User Pool │  │ • S3        │                                         │ │
│  │  │ • Groups    │  │ • DynamoDB  │                                         │ │
│  │  │ • SAML/OAuth│  │ • Bedrock   │                                         │ │
│  │  └─────────────┘  └─────────────┘                                         │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Frontend Components (React SPA)
```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
├─────────────────────────────────────────────────────────────┤
│ • Authentication Components (Cognito integration)           │
│ • Chat Interface (Real-time messaging)                     │
│ • Document Management (Upload/download)                    │
│ • User Dashboard (Session history)                         │
│ • Settings & Configuration                                 │
└─────────────────────────────────────────────────────────────┘
```

### Backend Components (Flask API)
```
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend                            │
├─────────────────────────────────────────────────────────────┤
│ • Authentication Middleware                                 │
│ • REST API Endpoints                                       │
│ • Session Management                                       │
│ • MCP Server Orchestration                                │
│ • Business Logic Layer                                     │
│ • Error Handling & Logging                                │
└─────────────────────────────────────────────────────────────┘
```

### MCP Server Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   MCP Servers (stdio)                      │
├─────────────────────────────────────────────────────────────┤
│ aws-service-validation-mcp-server                          │
│ ├─ Validate AWS service configurations                     │
│ ├─ Check service compatibility                             │
│ └─ Verify resource limits                                  │
│                                                            │
│ aws-cloudformation-generation-mcp-server                   │
│ ├─ Generate CloudFormation templates                       │
│ ├─ Create infrastructure diagrams                          │
│ └─ Validate template syntax and save to S3                             │
│                                                            │
│ aws-diagram-mcp-server                                     │
│ ├─ Create architecture diagrams                            │
│ ├─ Generate visual representations                         │
│ └─ Export multiple formats and save to s3                               │
│                                                            │
│ cost-analysis-mcp-server                                   │
│ ├─ Calculate AWS pricing                                   │
│ ├─ Optimize cost recommendations                           │
│ └─ Generate cost reports and save to s3                                 │
│                                                            │
│ sow-generator-mcp-server                                   │
│ ├─ Generate Statements of Work                             │
│ ├─ Create project proposals                                │                             │
│                                                            │
│ apn-funding-wizard-mcp-server                              │
│ ├─ APN partner funding guidance                            │
│ ├─ Funding program recommendations                         │
│ └─ Application assistance                                  │
└─────────────────────────────────────────────────────────────┘
```

## Infrastructure Architecture

### Compute Infrastructure
```
┌─────────────────────────────────────────────────────────────┐
│                  Auto Scaling Group                         │
├─────────────────────────────────────────────────────────────┤
│ Launch Template                                            │
│ ├─ AMI: Amazon Linux 2023                                 │
│ ├─ Instance Type: t3.medium (configurable)                │
│ ├─ Security Groups: Web tier access                       │
│ ├─ IAM Instance Profile: SERA-EC2-Role                    │
│ └─ User Data: Application bootstrap script                 │
│                                                            │
│ Scaling Configuration                                      │
│ ├─ Min Size: 2 instances                                  │
│ ├─ Max Size: 6 instances                                 │
│ ├─ Target Tracking: CPU 70%                               │
│ └─ Health Check: ALB + EC2                                │
│                                                            │
│ Target Groups                                              │
│ ├─ Frontend: Port 7001 (Vite Production Server)                 │
│ ├─ Backend: Port 5001 (Flask API)                         │
│ └─ Health Check: /health endpoint                         │
└─────────────────────────────────────────────────────────────┘
```

### Network Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        VPC                                  │
├─────────────────────────────────────────────────────────────┤
│ CIDR: 10.0.0.0/16                                         │
│                                                            │
│ Public Subnets (10.0.1.0/24, 10.0.2.0/24)                │
│ ├─ Application Load Balancer                               │
│ ├─ NAT Gateways (Single-AZ)                              │
│ └─ Internet Gateway attachment                             │
│                                                            │
│ Private Subnets (10.0.10.0/24, 10.0.20.0/24)             │
│ ├─ EC2 Instances (Auto Scaling Group)                     │
│ ├─ ElastiCache Redis Cluster                              │
│ └─ Route to NAT Gateway                                    │
│                                                            │
│ VPC Endpoints                                              │
│ ├─ S3 Gateway Endpoint                                     │
│ ├─ DynamoDB Gateway Endpoint                              │
│ └─ Bedrock Interface Endpoint                              │
└─────────────────────────────────────────────────────────────┘
```

### Security Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Security Layers                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Edge Security                                     │
│ ├─ AWS WAF: Rate limiting, IP filtering                    │
│ ├─ CloudFront: DDoS protection, geo-blocking               │
│ └─ Certificate Manager: TLS 1.2+ enforcement              │
│                                                            │
│ Layer 2: Network Security                                  │
│ ├─ Security Groups: Port-based access control             │
│ ├─ NACLs: Subnet-level filtering                          │
│ └─ Private Subnets: No direct internet access             │
│                                                            │
│ Layer 3: Application Security                              │
│ ├─ Cognito: Authentication & authorization                 │
│ ├─ IAM Roles: Service-to-service access                   │
│ └─ Session Management: Redis-based sessions               │
│                                                            │
│ Layer 4: Data Security                                     │
│ ├─ KMS: Encryption key management                          │
│ ├─ S3: Server-side encryption                             │
│ └─ DynamoDB: Encryption at rest                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Architecture

### Data Storage Design
```
┌─────────────────────────────────────────────────────────────┐
│                    S3 Buckets                               │
├─────────────────────────────────────────────────────────────┤
│ sera-documents-<account-id>                                │
│ ├─ User uploaded documents                                 │
│ ├─ Generated SOWs and reports                              │
│ ├─ Architecture diagrams                                   │
│ └─ Versioning enabled, lifecycle policies                 │
│                                                            │
│ sera-logs-<account-id>                                     │
│ ├─ Application logs (CloudWatch export)                   │
│ ├─ Access logs (ALB, CloudFront)                          │
│ ├─ Audit trails                                           │
│ └─ Bedrock invocation logs (optional)                     │
│                                                            │
│ sera-code-artifacts-<account-id>                           │
│ ├─ Application deployment packages                         │
│ ├─ CloudFormation templates                               │
│ └─ Configuration files                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  DynamoDB Tables                            │
├─────────────────────────────────────────────────────────────┤
│ sera-chat-sessions                                         │
│ ├─ PK: user_id, SK: session_id                            │
│ ├─ Chat conversation history                               │
│ ├─ Message timestamps and metadata                        │
│ └─ TTL for automatic cleanup                               │
│                                                            │
│ sera-user-metadata                                         │
│ ├─ PK: user_id                                            │
│ ├─ User preferences and settings                          │
│ ├─ Last login, session counts                             │
│ └─ User-scoped configuration                               │
│                                                            │
│ sera-application-config                                    │
│ ├─ PK: config_key                                         │
│ ├─ Application settings                                    │
│ ├─ Feature flags                                           │
│ └─ System configuration                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                ElastiCache Redis                            │
├─────────────────────────────────────────────────────────────┤
│ Cluster Configuration                                      │
│ ├─ Node Type: cache.t3.micro                              │
│ ├─ Multi-AZ: Enabled                                      │
│ ├─ Encryption: In transit and at rest                     │
│ └─ Backup: Daily snapshots                                │
│                                                            │
│ Data Patterns                                              │
│ ├─ Session tokens (TTL: 24 hours)                         │
│ ├─ Rate limiting counters (TTL: 1 hour)                   │
│ ├─ Temporary chat context (TTL: 30 minutes)               │
│ └─ MCP server response cache (TTL: 5 minutes)             │
└─────────────────────────────────────────────────────────────┘
```

### AI/ML Integration Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                  Bedrock Integration                        │
├─────────────────────────────────────────────────────────────┤
│ Model Configuration                                        │
│ ├─ Primary: Claude Sonnet 4                           │
│ ├─ Regions: us-east-1, us-east-2, us-west-2               │
│ ├─ Cross-region inference for availability                 │
│ └─ Model access permissions via IAM                       │
│                                                            │
│ Request Flow                                               │
│ ├─ Backend → Bedrock API                                  │
│ ├─ Context injection from chat history                    │
│ ├─ MCP tool results integration                            │
│ └─ Response streaming to frontend                         │
│                                                            │
│ Monitoring & Logging                                       │
│ ├─ Invocation metrics (CloudWatch)                        │
│ ├─ Token usage tracking                                    │
│ ├─ Error rate monitoring                                   │
│ └─ Cost optimization alerts                                │
└─────────────────────────────────────────────────────────────┘
```

## Communication Architecture

### Request Flow Patterns
```
┌─────────────────────────────────────────────────────────────┐
│                  User Request Flow                          │
├─────────────────────────────────────────────────────────────┤
│ 1. User Browser                                            │
│    ├─ HTTPS Request                                        │
│    └─ Authentication Token                                 │
│                                                            │
│ 2. CloudFront (CDN)                                        │
│    ├─ Static content caching                               │
│    ├─ Geographic distribution                              │
│    └─ Origin request to ALB                                │
│                                                            │
│ 3. Application Load Balancer                               │
│    ├─ SSL termination                                      │
│    ├─ Health check routing                                 │
│    └─ Target group distribution                            │
│                                                            │
│ 4. EC2 Instance                                            │
│    ├─ Frontend: React SPA serving                         │
│    ├─ Backend: Flask API processing                       │
│    └─ MCP Servers: Tool execution                         │
└─────────────────────────────────────────────────────────────┘
```

### Internal Service Communication
```
┌─────────────────────────────────────────────────────────────┐
│               Service Integration Patterns                  │
├─────────────────────────────────────────────────────────────┤
│ Frontend ↔ Backend                                         │
│ ├─ Protocol: HTTP/HTTPS REST API                           │
│ ├─ Authentication: JWT tokens                              │
│ ├─ Data Format: JSON                                       │
│ └─ WebSocket: Real-time chat updates                      │
│                                                            │
│ Backend ↔ MCP Servers                                      │
│ ├─ Protocol: stdio (JSON-RPC)                             │
│ ├─ Process Management: Subprocess spawning                 │
│ ├─ Error Handling: Timeout and retry logic                │
│ └─ Resource Limits: Memory and CPU constraints            │
│                                                            │
│ Backend ↔ AWS Services                                     │
│ ├─ Authentication: IAM roles and policies                 │
│ ├─ Network: VPC endpoints for private access              │
│ ├─ Encryption: TLS 1.2+ for all connections               │
│ └─ Retry Logic: Exponential backoff                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Data Flow Patterns                       │
├─────────────────────────────────────────────────────────────┤
│ Chat Message Flow                                          │
│ ├─ User Input → Frontend → Backend                         │
│ ├─ Backend → MCP Servers (if tools needed)                │
│ ├─ Backend → Bedrock (AI processing)                      │
│ ├─ Response → DynamoDB (persistence)                      │
│ └─ Response → Frontend (real-time display)                │
│                                                            │
│ Document Flow                                              │
│ ├─ Upload: Frontend → S3 (pre-signed URLs)                │
│ ├─ Processing: Backend → MCP Servers                      │
│ ├─ Storage: Generated content → S3                        │
│ └─ Access: CloudFront signed URLs                         │
│                                                            │
│ Session Management                                         │
│ ├─ Login: Cognito → Backend → Redis                       │
│ ├─ Validation: Backend → Redis (session lookup)          │
│ ├─ Refresh: Automatic token renewal                       │
│ └─ Logout: Session cleanup from Redis                     │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Production Environment
- **Region**: us-east-1 (primary)
- **Availability Zones**: Multi-AZ deployment
- **Scaling**: Auto Scaling Groups with target tracking
- **Load Balancing**: Application Load Balancer with health checks

### Development Environment
- **Local Components**: Redis, Frontend (npm), Backend (Flask)
- **AWS Components**: S3, DynamoDB, Bedrock, Cognito
- **Excluded**: ALB, CloudFront, Auto Scaling, ElastiCache

## Security Architecture

### Authentication Flow
```
User → Cognito OAuth2 → JWT Token → Backend Validation → Session Creation
```

### Authorization Layers
1. **Cognito Groups**: `sera_sales_person` group membership
2. **IAM Roles**: EC2 instance profile with least privilege
3. **Application Logic**: User-scoped data access

### Encryption
- **In Transit**: TLS 1.2+ for all communications
- **At Rest**: Customer-managed KMS keys
- **Document Access**: CloudFront signed URLs with RSA-2048

## Monitoring and Observability

### Logging Strategy
- **Application Logs**: CloudWatch Logs from EC2 instances
- **Access Logs**: ALB and CloudFront logs to S3
- **Audit Logs**: S3 bucket for compliance tracking
- **Debug Logs**: Structured logging with 50-character data limits

### Metrics and Monitoring
- **CloudWatch Metrics**: EC2, ALB, DynamoDB, ElastiCache
- **Custom Metrics**: Application performance and business metrics
- **Health Checks**: ALB target group health monitoring

## Scalability Considerations

### Horizontal Scaling
- **Frontend/Backend**: Auto Scaling Groups based on CPU/memory
- **Database**: DynamoDB on-demand scaling
- **Cache**: ElastiCache cluster scaling

### Performance Optimization
- **CDN**: CloudFront for static content delivery
- **Caching**: Redis for session and temporary data
- **Connection Pooling**: Database connection optimization

## Disaster Recovery

### Backup Strategy
- **S3**: Cross-region replication for critical documents
- **DynamoDB**: Point-in-time recovery enabled
- **Configuration**: Infrastructure as Code (CloudFormation)

### Recovery Procedures
- **RTO**: 4 hours for full environment restoration
- **RPO**: 1 hour for data loss tolerance
- **Failover**: Manual failover to secondary region if needed