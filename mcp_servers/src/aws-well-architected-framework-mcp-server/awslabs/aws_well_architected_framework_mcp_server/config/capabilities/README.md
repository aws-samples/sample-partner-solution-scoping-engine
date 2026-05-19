# Security Capabilities Configuration

## Overview

This directory contains capability definitions for the WAFR Enterprise Scoring system. Each capability configuration file defines how AWS services map to specific capabilities that contribute to pillar scores.

## Security Capabilities

The `security_capabilities.json` file defines five core security capabilities:

### 1. Encryption (25% weight)
**Purpose**: Data encryption at rest and in transit

**Services**:
- **KMS** (30% coverage): Key management and encryption key lifecycle
  - Detection: "AWS KMS", "Key Management Service", "KMS key", "customer managed key", "CMK"
  - Checks: Key rotation enabled, key policy defined
  
- **S3_encryption** (20% coverage): Storage encryption for S3 buckets
  - Detection: "S3 encryption", "bucket encryption", "SSE-S3", "SSE-KMS", "server-side encryption"
  - Checks: Default encryption enabled, HTTPS/TLS required
  
- **RDS_encryption** (20% coverage): Database encryption for RDS instances
  - Detection: "RDS encryption", "encrypted RDS", "database encryption", "Aurora encryption"
  - Checks: Encryption at rest, SSL/TLS connections
  
- **DynamoDB_encryption** (15% coverage): NoSQL database encryption
  - Detection: "DynamoDB encryption", "encrypted DynamoDB", "DynamoDB KMS"
  - Checks: Encryption at rest enabled
  
- **EBS_encryption** (15% coverage): Volume encryption for EC2 instances
  - Detection: "EBS encryption", "encrypted EBS", "encrypted volume"
  - Checks: Encryption enabled on volumes

### 2. Identity & Access (25% weight)
**Purpose**: Identity and access management

**Services**:
- **IAM** (40% coverage): Access control and permissions
  - Detection: "IAM", "Identity and Access Management", "IAM role", "IAM policy", "least privilege"
  - Checks: MFA enabled, least privilege policies, password policy
  
- **Cognito** (30% coverage): User authentication and authorization
  - Detection: "Cognito", "user pool", "identity pool", "user authentication"
  - Checks: MFA configuration, password requirements
  
- **Secrets_Manager** (30% coverage): Credential management
  - Detection: "Secrets Manager", "AWS Secrets Manager", "secret rotation", "credential management"
  - Checks: Automatic rotation, encryption enabled

### 3. Network Security (20% weight)
**Purpose**: Network isolation and protection

**Services**:
- **VPC** (40% coverage): Network isolation
  - Detection: "VPC", "Virtual Private Cloud", "private subnet", "public subnet", "network isolation"
  - Checks: Private subnets for sensitive resources, VPC Flow Logs enabled
  
- **Security_Groups** (30% coverage): Firewall rules
  - Detection: "security group", "firewall rules", "ingress rules", "egress rules"
  - Checks: Least privilege rules, default deny approach
  
- **WAF** (30% coverage): Application firewall
  - Detection: "WAF", "Web Application Firewall", "AWS WAF", "WAF rules"
  - Checks: Managed rules configured, rate limiting
  
- **Network_ACL** (20% coverage): Subnet-level firewall
  - Detection: "Network ACL", "NACL", "network access control list"
  - Checks: Stateless filtering configured

### 4. Monitoring & Detection (15% weight)
**Purpose**: Security monitoring and threat detection

**Services**:
- **CloudTrail** (40% coverage): Audit logging
  - Detection: "CloudTrail", "AWS CloudTrail", "audit log", "API logging"
  - Checks: Enabled in all regions, log file validation, S3 encryption
  
- **GuardDuty** (30% coverage): Threat detection
  - Detection: "GuardDuty", "AWS GuardDuty", "threat detection", "intelligent threat detection"
  - Checks: Enabled, findings notifications configured
  
- **Security_Hub** (30% coverage): Security posture management
  - Detection: "Security Hub", "AWS Security Hub", "security posture", "compliance checks"
  - Checks: Enabled, security standards enabled
  
- **CloudWatch_Logs** (20% coverage): Log monitoring
  - Detection: "CloudWatch Logs", "log monitoring", "log aggregation"
  - Checks: Log retention configured, metric filters for security events

### 5. Data Protection (15% weight)
**Purpose**: Data backup and protection

**Services**:
- **Backup** (50% coverage): Automated backup
  - Detection: "AWS Backup", "backup plan", "backup vault", "automated backup"
  - Checks: Backup plan configured, vault encrypted, cross-region backup
  
- **S3_versioning** (50% coverage): Data versioning
  - Detection: "S3 versioning", "bucket versioning", "object versioning"
  - Checks: Versioning enabled, MFA Delete enabled
  
- **S3_Object_Lock** (30% coverage): Immutable storage
  - Detection: "S3 Object Lock", "object lock", "WORM", "immutable storage"
  - Checks: Object Lock enabled for compliance

## Configuration Structure

Each capability follows this structure:

```json
{
  "capability_name": {
    "weight": 0.25,                    // Contribution to pillar score (0.0-1.0)
    "description": "...",              // Human-readable description
    "pillar": "security",              // Pillar this capability belongs to
    "services": {
      "Service_Name": {
        "provides": "...",             // What this service provides
        "coverage_factor": 0.3,        // How much this service contributes (0.0-1.0)
        "detection_patterns": [...],   // Keywords to detect this service
        "configuration_checks": [      // Specific checks for this service
          {
            "check": "...",            // Check identifier
            "description": "...",      // What this check validates
            "weight": 0.3              // Importance of this check (0.0-1.0)
          }
        ]
      }
    }
  }
}
```

## Weight Distribution

Security pillar weights must sum to 1.0:
- Encryption: 0.25 (25%)
- Identity & Access: 0.25 (25%)
- Network Security: 0.20 (20%)
- Monitoring & Detection: 0.15 (15%)
- Data Protection: 0.15 (15%)
- **Total: 1.00 (100%)**

## Detection Patterns

Detection patterns are case-insensitive keywords used to identify services in architecture documents. Multiple patterns increase detection accuracy.

**Best Practices**:
- Include official AWS service names
- Include common abbreviations (e.g., "KMS" for "Key Management Service")
- Include related terms (e.g., "customer managed key", "CMK")
- Include feature-specific terms (e.g., "SSE-S3", "SSE-KMS")

## Configuration Checks

Configuration checks validate that services are properly configured for security. Each check has:
- **check**: Unique identifier for the check
- **description**: What the check validates
- **weight**: Importance of this check (0.0-1.0)

Check weights within a service should sum to approximately 1.0 for balanced scoring.

## Usage Example

```python
from config.configuration_manager import get_config_manager

# Get configuration manager
config_manager = get_config_manager()

# Get all security capabilities
security_caps = config_manager.get_all_capabilities_for_pillar('security')

# Get specific capability
encryption_cap = config_manager.get_capability_definition('security', 'encryption')

# Access service details
kms_service = encryption_cap['services']['KMS']
detection_patterns = kms_service['detection_patterns']
config_checks = kms_service['configuration_checks']
```

## Validation

The configuration is automatically validated on load:
- All required fields present
- Weights sum to 1.0 (±0.1 tolerance)
- No duplicate capability names
- All services have detection patterns
- All services have configuration checks

Run validation manually:
```bash
python3 validate_security_config.py
```

## Extending Configuration

To add a new service to a capability:

1. Add service entry under the capability's `services` object
2. Define `provides`, `coverage_factor`, `detection_patterns`, and `configuration_checks`
3. Ensure coverage factors within the capability sum to approximately 1.0
4. Run validation to ensure configuration is valid

To add a new capability:

1. Add capability entry at the root level
2. Ensure all capabilities' weights sum to 1.0
3. Follow the same structure as existing capabilities
4. Run validation to ensure configuration is valid

## References

- Requirements: `.kiro/specs/wafr-enterprise-scoring/requirements.md` (Requirement 2.1, 4.1)
- Design: `.kiro/specs/wafr-enterprise-scoring/design.md` (Security Capabilities section)
- Configuration Manager: `config/configuration_manager.py`
