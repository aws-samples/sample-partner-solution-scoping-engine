# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Constants for the AWS Security Pillar MCP Server."""

import os

# Default AWS region fallback (only used if no environment variable is set)
DEFAULT_AWS_REGION = "us-east-1"

# Default AWS regions to use if none are specified
DEFAULT_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]


def get_aws_region() -> str:
    """
    Get AWS region from environment variables.
    
    Priority order:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. DEFAULT_AWS_REGION constant (fallback)
    
    Returns:
        AWS region string
    """
    return os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or DEFAULT_AWS_REGION

# Instructions for the MCP server
INSTRUCTIONS = """AWS Well-Architected Framework MCP Server for comprehensive solution assessment across all 6 pillars.

This server provides complete Well-Architected Framework reviews by analyzing solution text, architecture diagrams, and integrating with cost analysis to identify High Risk Issues (HRIs), Medium Risk Issues (MRIs), and generate actionable recommendations.

## Key Capabilities
- Complete WAFR assessment across all 6 pillars (83 questions)
- Solution text analysis and AWS service identification
- Architecture diagram processing (via integration)
- Cost analysis integration for optimization recommendations
- High/Medium/Low risk issue classification
- Security services integration (Security Hub, GuardDuty, etc.)
- Dynamic resource discovery and security scanning
- Detailed remediation planning with AWS best practices links

## Available Tools

### WAFR Assessment Tools

### AnalyzeSolutionText
Analyzes solution text to extract AWS services, architecture patterns, and WAFR-relevant information.
This tool parses solution descriptions to identify services, patterns, requirements, and business context
needed for comprehensive Well-Architected Framework assessment.

### AssessWellArchitectedFramework
Runs comprehensive Well-Architected Framework assessment across all 6 pillars using the official 83 questions.
Identifies High Risk Issues (HRIs), Medium Risk Issues (MRIs), and provides detailed recommendations with
AWS best practices links. Integrates with cost analysis for enhanced optimization recommendations.

### SetupMCPIntegrations
Sets up integrations with external MCP servers (cost-analysis-mcp-server, aws-diagram-mcp-server) for
enhanced WAFR assessment capabilities including real-time cost analysis and architecture diagram processing.

### AnalyzeArchitectureDiagram
Processes PNG architecture diagrams to extract additional insights that complement text-based solution analysis.
Identifies services, relationships, data flows, security boundaries, and architecture patterns.

### Security Assessment Tools

### CheckSecurityServices
Verifies if selected AWS security services are enabled in the specified region and account.
This consolidated tool checks the status of multiple AWS security services in a single call,
providing a comprehensive overview of your security posture.

### GetSecurityFindings
Retrieves security findings from various AWS security services including GuardDuty, Security Hub,
Inspector, IAM Access Analyzer, Trusted Advisor, and Macie with filtering options by severity.

### CheckStorageEncryption
Identifies storage resources using Resource Explorer and checks if they are properly configured
for data protection at rest according to AWS Well-Architected Framework Security Pillar best practices.

### CheckNetworkSecurity
Identifies network resources using Resource Explorer and checks if they are properly configured
for data protection in transit according to AWS Well-Architected Framework Security Pillar best practices.
This tool helps ensure your network configurations follow security best practices for protecting data in transit.

### GetStoredSecurityContext
Retrieves security services data that was stored in context from a previous CheckSecurityServices call
without making additional AWS API calls.

### GetResourceComplianceStatus
Checks the compliance status of specific AWS resources against AWS Config rules, providing
detailed compliance information and configuration history.

### ExploreAwsResources
Provides a comprehensive inventory of AWS resources within a specified region across multiple services.
This tool is useful for understanding what resources are deployed in your environment before conducting
a security assessment.

## Usage Guidelines
1. Start by exploring your AWS resources to understand your environment:
   - Use ExploreAwsResources to get a comprehensive inventory of resources
   - Review what services and resources are deployed in your target region

2. Check if key security services are enabled:
   - Use CheckSecurityServices to verify which security services are enabled
   - Review the summary to identify which services need to be enabled

3. Assess your data protection posture:
   - Use CheckStorageEncryption to verify encryption at rest
   - Use CheckNetworkSecurity to verify encryption in transit
   - Review the recommendations for improving your data protection

4. Analyze security findings:
   - Use GetSecurityFindings to retrieve findings from enabled security services
   - Focus on high-severity findings first

5. Apply recommended remediation steps to improve your security posture

## AWS Security Pillar
This server aligns with the Security Pillar of the AWS Well-Architected Framework, which focuses on:
- Identity and Access Management
- Detection Controls
- Infrastructure Protection
- Data Protection
- Incident Response

For more information, see: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html
"""


# Security domains from Well-Architected Framework
SECURITY_DOMAINS = [
    "identity_and_access_management",
    "detection",
    "infrastructure_protection",
    "data_protection",
    "incident_response",
    "application_security",
]

# Severity levels for security findings
SEVERITY_LEVELS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFORMATIONAL": 0,
}
