# SERA API Specifications

## Overview

This document provides comprehensive API specifications for the SERA (Solutions Engine for Recommending AWS) backend service. The API follows RESTful design principles and provides endpoints for chat management, authentication, document handling, and administrative functions.

## API Architecture

### Base Configuration
- **Base URL**: `https://{domain}/api`
- **Protocol**: HTTPS only
- **Authentication**: Session-based with OAuth2/SAML
- **Content Type**: `application/json`
- **CORS**: Configured for cross-origin requests

### Authentication Model
- **Primary**: AWS Cognito with OAuth2
- **Secondary**: SAML integration for enterprise IdP
- **Session Management**: Redis-backed sessions
- **Authorization**: Role-based access control (RBAC)

## User Roles and Permissions

### Role Definitions
| Role | Description | Permissions |
|------|-------------|-------------|
| `sera_sales_person` | Inside sales personnel | Own chats, create/manage conversations |
| `sera_solutions_architect` | Technical architects | All chats, SA reviews, document approval |

### Permission Matrix
| Operation | Sales Person | Solutions Architect | SA Manager |
|-----------|--------------|-------------------|------------|
| Create Chat | ✓ | ✓ | ✓ |
| View Own Chats | ✓ | ✓ | ✓ |
| View All Chats | ✗ | ✓ | ✓ |
| SA Review | ✗ | ✓ | ✓ |
| SOW Review | ✗ | ✓ | ✓ |
| Document Approval | ✗ | ✓ | ✓ |

## API Endpoints

### Authentication Endpoints

#### `GET /api/auth`
**Purpose**: Initiate authentication flow
**Authentication**: None required
**Parameters**:
- `provider` (query, optional): Authentication provider (`saml` | `oauth2`)
- `return_to` (query, optional): Return URL after authentication

**Response**: `302 Redirect` to IdP

#### `GET /api/callback`
**Purpose**: Handle authentication callback from IdP
**Authentication**: None required
**Parameters**:
- `provider` (query): Authentication provider
- Provider-specific callback parameters

**Response**: `302 Redirect` to frontend or error page

#### `GET /api/logout`
**Purpose**: Terminate user session
**Authentication**: Optional
**Parameters**:
- `provider` (query, optional): Logout provider

**Response**: 
```json
{
  "message": "Logged out successfully"
}
```

#### `GET /api/status`
**Purpose**: Check authentication status
**Authentication**: None required

**Response**:
```json
{
  "authenticated": true,
  "user": {
    "id": "user@example.com",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "groups": ["sera_sales_person"],
    "is_sales_person": true,
    "is_solutions_architect": false,
    "can_review_sow": false,
    "can_access_all_chats": false
  }
}
```

### Chat Management Endpoints

#### `GET /api/chats`
**Purpose**: List chats with role-based filtering
**Authentication**: Required
**Parameters**:
- `stage` (query, optional): Filter by stage (`SOLUTION_REVIEW` | `SOLUTION_PROPOSED` | `SOLUTION_FINALIZED` | `NOT_FINALIZED`)
- `limit` (query, optional): Maximum results (default: 20, max: 100)
- `offset` (query, optional): Pagination offset (default: 0)
- `include_completed_sa_reviews` (query, optional): Include completed SA reviews (default: false)

**Response**:
```json
{
  "chats": [
    {
      "chatId": "uuid",
      "chatName": "Customer Discussion",
      "stage": "SOLUTION_PROPOSED",
      "userId": "user@example.com",
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T14:20:00Z"
    }
  ],
  "total": 25
}
```

#### `POST /api/chats`
**Purpose**: Create new chat session
**Authentication**: Required
**Request Body**:
```json
{
  "assistant_persona": "aws_solutions_architect",
  "customer_persona": "startup_cto",
  "interaction_method": "technical_consultation",
  "chat_name": "AWS Migration Discussion"
}
```

**Response**:
```json
{
  "chatId": "uuid",
  "userId": "user@example.com",
  "assistantPersona": "aws_solutions_architect",
  "customerPersona": "startup_cto",
  "interactionMethod": "technical_consultation",
  "timestamp": "2024-01-15T10:30:00Z",
  "stage": "INITIAL",
  "chatName": "AWS Migration Discussion"
}
```

#### `GET /api/chats/{chat_id}`
**Purpose**: Get complete chat session
**Authentication**: Required
**Path Parameters**:
- `chat_id`: Chat identifier

**Response**:
```json
{
  "chatId": "uuid",
  "userId": "user@example.com",
  "assistantPersona": "aws_solutions_architect",
  "customerPersona": "startup_cto",
  "interactionMethod": "technical_consultation",
  "stage": "SOLUTION_PROPOSED",
  "chatName": "AWS Migration Discussion",
  "messages": [
    {
      "message_id": "uuid",
      "role": "user",
      "content": "I need help with AWS migration",
      "message_timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T14:20:00Z"
}
```

#### `POST /api/chats/{chat_id}/messages`
**Purpose**: Send message to chat (streaming response)
**Authentication**: Required
**Content Types**: 
- `application/json` (text only)
- `multipart/form-data` (with file uploads)

**Request Body (JSON)**:
```json
{
  "message": "Can you help me design a serverless architecture?",
  "intent": "architecture_design"
}
```

**Request Body (Multipart)**:
- `message` (form field): Message text
- `intent` (form field, optional): Message intent
- `files` (file field, multiple): Uploaded files

**Response**: `text/plain` streaming response with AI-generated content

#### `PUT /api/chats/{chat_id}/stage`
**Purpose**: Update chat conversation stage
**Authentication**: Required
**Request Body**:
```json
{
  "stage": "SOLUTION_FINALIZED"
}
```

**Response**:
```json
{
  "chatId": "uuid",
  "stage": "SOLUTION_FINALIZED"
}
```

#### `PUT /api/chats/{chat_id}/name`
**Purpose**: Update chat name
**Authentication**: Required
**Request Body**:
```json
{
  "name": "Updated Chat Name"
}
```

**Response**:
```json
{
  "chatId": "uuid",
  "chatName": "Updated Chat Name"
}
```

#### `DELETE /api/chats/{chat_id}`
**Purpose**: Delete chat and associated resources
**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "message": "Chat deleted successfully"
}
```

### Document Management Endpoints

#### `GET /api/chats/{chat_id}/documents`
**Purpose**: Get all documents for a chat
**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "documents": {
    "doc_id_1": {
      "document_type": "diagram",
      "s3_key": "chat_id/diagram.png",
      "version_id": "version_uuid",
      "file_size": 1024000,
      "original_filename": "architecture_diagram.png",
      "created_timestamp": "2024-01-15T10:30:00Z",
      "approved": false
    }
  }
}
```

#### `GET /api/chats/{chat_id}/documents/{document_id}/download`
**Purpose**: Get download URL for approved documents
**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "download_url": "https://cloudfront.domain.com/signed-url",
  "document_type": "diagram",
  "file_size": 1024000
}
```

#### `POST /api/chats/{chat_id}/documents/{document_id}/approve`
**Purpose**: Approve document for download (SA only)
**Authentication**: Required (SA role)

**Response**:
```json
{
  "success": true,
  "message": "Document approved"
}
```

### File Upload Endpoints

#### `POST /api/chats/{chat_id}/upload`
**Purpose**: Upload files to chat session
**Authentication**: Required
**Content Type**: `multipart/form-data`

**Request Body**:
- `file` (file field): File to upload
- `option` (form field): Upload option (`read` | `save`)
- `timestamp` (form field, optional): Upload timestamp

**Response**:
```json
{
  "success": true,
  "message": "File uploaded and saved to library",
  "document": {
    "name": "document.pdf",
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": "user@example.com",
    "location": "s3://bucket/chat_id/uuid_document.pdf"
  }
}
```

#### `GET /api/chats/{chat_id}/documents/cf_signedurl/{path:file_path}`
**Purpose**: Get CloudFront signed URL for any file
**Authentication**: Required
**Query Parameters**:
- `version_id` (optional): S3 version ID for specific version

**Response**:
```json
{
  "url": "https://cloudfront.domain.com/signed-url",
  "uri": "chat_id/file_path"
}
```

### Persona Management Endpoints

#### `GET /api/personas`
**Purpose**: Get available assistant and customer personas
**Authentication**: Optional (returns filtered results based on user groups)

**Response**:
```json
{
  "assistants": [
    {
      "label": "AWS Solutions Architect",
      "value": "aws_solutions_architect",
      "description": "Expert in AWS architecture and best practices",
      "enabled": true
    }
  ],
  "customers": [
    {
      "label": "Startup CTO",
      "value": "startup_cto",
      "description": "Technical leader at a growing startup",
      "enabled": true
    }
  ]
}
```

### SA Review Endpoints

#### `POST /api/sa-review/request`
**Purpose**: Request SA review for a chat
**Authentication**: Required
**Request Body**:
```json
{
  "chat_id": "uuid",
  "comment": "Please review the proposed architecture"
}
```

**Response**:
```json
{
  "success": true,
  "system_message": "Review requested from Solutions Architect - Comment: Please review the proposed architecture",
  "chat_id": "uuid",
  "status": "requested"
}
```

#### `POST /api/sa-review/start/{original_chat_id}`
**Purpose**: Start SA review by creating copy (SA only)
**Authentication**: Required (SA role)

**Response**:
```json
{
  "success": true,
  "sa_copy_chat_id": "uuid",
  "original_chat_id": "uuid",
  "action": "new_copy"
}
```

#### `POST /api/sa-review/actions`
**Purpose**: Execute SA review actions
**Authentication**: Required (SA role)
**Request Body**:
```json
{
  "action": "mark_ready",
  "sa_copy_chat_id": "uuid",
  "comment": "Architecture looks good with minor suggestions",
  "documentIds": ["doc_id_1", "doc_id_2"]
}
```

**Actions**: `mark_ready` | `complete_no_changes` | `reject` | `reassign`

**Response**:
```json
{
  "success": true,
  "action": "mark_ready",
  "result": {
    "original_chat_id": "uuid",
    "notification_sent": true
  }
}
```

#### `POST /api/sa-review/merge`
**Purpose**: Merge SA changes to original chat
**Authentication**: Required
**Request Body**:
```json
{
  "chat_id": "uuid"
}
```

**Response**:
```json
{
  "success": true,
  "merge_result": {
    "documents_merged": 3,
    "messages_added": 2
  }
}
```

### SOW Review Endpoints

#### `GET /api/sow-reviews`
**Purpose**: Get SOWs for review (authorized users only)
**Authentication**: Required (SOW reviewer role)
**Query Parameters**:
- `limit` (optional): Maximum results (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
  "sows": [
    {
      "chat_id": "uuid",
      "chat_name": "Customer Project",
      "customer_name": "Acme Corp",
      "project_title": "AWS Migration Project",
      "stage": "SOW_GENERATED",
      "created_by": "user@example.com",
      "sow_generated_date": "2024-01-15T10:30:00Z",
      "estimated_project_cost": 150000.00,
      "template_type": "aws_map",
      "partner_name": "ExamplePartner",
      "s3_url": "s3://bucket/chat_id/sow/ScopeOfWork.pdf",
      "review_required": true
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0,
  "has_more": false
}
```

#### `POST /api/sow-reviews/{chat_id}/feedback`
**Purpose**: Submit SOW review feedback
**Authentication**: Required (SOW reviewer role)
**Request Body**:
```json
{
  "feedback_type": "approved",
  "comments": "SOW looks comprehensive and accurate"
}
```

**Response**:
```json
{
  "message": "SOW feedback submitted successfully",
  "new_sow_status": "approved",
  "review_data": {
    "chat_id": "uuid",
    "reviewer_id": "sa@example.com",
    "feedback_type": "approved",
    "comments": "SOW looks comprehensive and accurate",
    "review_timestamp": "2024-01-15T14:30:00Z"
  }
}
```

#### `GET /api/sow-reviews/{chat_id}/download`
**Purpose**: Download SOW PDF document
**Authentication**: Required (SOW reviewer role)
**Query Parameters**:
- `version_id` (optional): Specific version to download

**Response**: Binary PDF file with appropriate headers

### Support Team Management

#### `GET /api/support/team`
**Purpose**: Get current user's support team
**Authentication**: Required

**Response**:
```json
{
  "success": true,
  "support_team": [
    {
      "support_member_id": "sa@example.com",
      "support_member_role": "solution_architect",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### `POST /api/support/add`
**Purpose**: Add support team member
**Authentication**: Required
**Request Body**:
```json
{
  "support_member_id": "sa@example.com",
  "support_member_role": "solution_architect"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Added sa@example.com as solution_architect"
}
```

### Administrative Endpoints

#### `GET /api/health`
**Purpose**: Health check for load balancer
**Authentication**: None required

**Response**:
```json
{
  "status": "healthy"
}
```

#### `GET /api/chats/recent`
**Purpose**: Get 5 most recent chats (excluding SA copies)
**Authentication**: Required

**Response**:
```json
[
  {
    "chatId": "uuid",
    "chatName": "Recent Discussion",
    "updatedAt": "2024-01-15T14:20:00Z",
    "stage": "SOLUTION_PROPOSED"
  }
]
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": "Error message description",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional error context"
  }
}
```

### HTTP Status Codes
| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful GET requests |
| 201 | Created | Successful POST requests creating resources |
| 400 | Bad Request | Invalid request parameters or body |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server-side errors |

### Common Error Scenarios
- **Authentication Failures**: Return 401 with redirect to login
- **Authorization Failures**: Return 403 with permission details
- **Validation Errors**: Return 400 with field-specific error messages
- **Resource Not Found**: Return 404 with resource identifier
- **Rate Limiting**: Return 429 with retry-after header

## Security Considerations

### Authentication Security
- **Session Management**: Redis-backed sessions with configurable expiration
- **CSRF Protection**: SameSite cookie attributes and CSRF tokens
- **Secure Headers**: HSTS, X-Content-Type-Options, X-Frame-Options
- **Input Validation**: Comprehensive validation on all endpoints

### Authorization Model
- **Role-Based Access**: Granular permissions based on user groups
- **Resource Ownership**: Users can only access their own resources unless explicitly granted
- **SA Privileges**: Solutions Architects have elevated access for review functions

### Data Protection
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Encryption at Rest**: KMS encryption for S3 and DynamoDB
- **PII Handling**: Minimal PII collection with proper anonymization
- **Audit Logging**: Comprehensive logging of all user actions

## Rate Limiting

### Default Limits
- **Authentication**: 10 requests per minute per IP
- **Chat Messages**: 60 requests per minute per user
- **File Uploads**: 10 uploads per minute per user
- **General API**: 1000 requests per hour per user

### Rate Limit Headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642694400
```

## Monitoring and Observability

### Metrics Collection
- **Request Metrics**: Response times, error rates, throughput
- **Business Metrics**: Chat creation rates, SA review completion times
- **Infrastructure Metrics**: DynamoDB performance, S3 usage, Redis health

### Logging Standards
- **Structured Logging**: JSON format with consistent field names
- **Log Levels**: DEBUG, INFO, WARN, ERROR with appropriate usage
- **Correlation IDs**: Request tracking across service boundaries
- **PII Redaction**: Automatic removal of sensitive data from logs

### Health Checks
- **Application Health**: `/api/health` endpoint for load balancer
- **Dependency Health**: DynamoDB, Redis, S3 connectivity checks
- **Business Logic Health**: Core functionality validation

## API Versioning

### Current Version
- **Version**: v1 (implicit in current API)
- **Compatibility**: Backward compatibility maintained within major version
- **Deprecation Policy**: 6-month notice for breaking changes

### Future Versioning Strategy
- **URL Versioning**: `/api/v2/` for major version changes
- **Header Versioning**: `Accept: application/vnd.sera.v2+json` for content negotiation
- **Feature Flags**: Gradual rollout of new features

## Integration Patterns

### MCP Server Integration
- **Tool Registry**: Dynamic registration of MCP server capabilities
- **Async Processing**: Non-blocking tool execution with streaming responses
- **Error Handling**: Graceful degradation when MCP servers are unavailable

### AWS Service Integration
- **Bedrock**: AI model inference with retry logic and throttling
- **S3**: Document storage with versioning and lifecycle policies
- **DynamoDB**: Chat data persistence with GSI for efficient queries
- **CloudFront**: Secure document delivery with signed URLs

### External System Integration
- **Identity Providers**: SAML and OAuth2 integration for enterprise SSO
- **Notification Systems**: Email and Slack notifications for SA reviews
- **Monitoring Systems**: CloudWatch integration for metrics and alarms

## Performance Considerations

### Response Time Targets
- **Authentication**: < 500ms for login/logout operations
- **Chat List**: < 200ms for paginated chat retrieval
- **Message Send**: < 2s for AI response initiation (streaming)
- **File Upload**: < 5s for files up to 10MB

### Scalability Design
- **Horizontal Scaling**: Stateless application servers behind load balancer
- **Database Optimization**: Efficient DynamoDB queries with proper indexing
- **Caching Strategy**: Redis for session data and frequently accessed content
- **CDN Integration**: CloudFront for static assets and document delivery

### Resource Limits
- **File Upload**: 10MB maximum per file, 50MB total per chat
- **Message Length**: 100KB maximum per message
- **Chat History**: 1000 messages maximum per chat (with archiving)
- **Concurrent Users**: Designed for 1000+ concurrent users

This API specification provides a comprehensive foundation for SERA backend integration and serves as the authoritative reference for all API consumers.