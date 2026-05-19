"""
Remediation Guidance for WAFR Capabilities.

This module provides detailed, actionable remediation steps for each capability gap.
Each capability has specific AWS services, implementation steps, and best practices.
"""

from typing import Dict, List, Any

# Detailed remediation guidance for each capability
CAPABILITY_REMEDIATION_GUIDANCE: Dict[str, Dict[str, Any]] = {
    # SECURITY PILLAR
    "encryption": {
        "display_name": "Encryption",
        "pillar": "security",
        "description": "Implement comprehensive encryption for data at rest and in transit",
        "aws_services": ["AWS KMS", "AWS Certificate Manager", "S3 Server-Side Encryption"],
        "implementation_steps": [
            "Enable AWS KMS customer-managed keys (CMKs) for all data stores",
            "Configure S3 bucket default encryption with SSE-KMS",
            "Enable RDS/Aurora encryption at rest using KMS",
            "Implement TLS 1.2+ for all API endpoints using ACM certificates",
            "Enable DynamoDB encryption at rest with KMS",
            "Configure EBS volume encryption by default in account settings"
        ],
        "best_practices": [
            "Use separate KMS keys per environment (dev/staging/prod)",
            "Enable automatic key rotation for KMS keys",
            "Use AWS Secrets Manager for credential encryption",
            "Implement envelope encryption for large data sets"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 9,
        "compliance_impact": "SOC2, HIPAA, PCI-DSS, GDPR"
    },
    "identity_access": {
        "display_name": "Identity & Access Management",
        "pillar": "security",
        "description": "Strengthen identity controls and implement least-privilege access",
        "aws_services": ["AWS IAM", "Amazon Cognito", "AWS IAM Identity Center", "AWS STS"],
        "implementation_steps": [
            "Implement IAM roles with least-privilege policies for all services",
            "Enable MFA for all IAM users and root account",
            "Configure Amazon Cognito user pools with strong password policies",
            "Implement IAM Identity Center for centralized access management",
            "Use IAM Access Analyzer to identify overly permissive policies",
            "Enable AWS CloudTrail for IAM activity logging"
        ],
        "best_practices": [
            "Use IAM roles instead of long-term access keys",
            "Implement service control policies (SCPs) in AWS Organizations",
            "Regular access reviews using IAM Access Analyzer",
            "Implement just-in-time access for privileged operations"
        ],
        "estimated_effort": "2-3 weeks",
        "priority_score": 10,
        "compliance_impact": "SOC2, HIPAA, PCI-DSS, ISO 27001"
    },
    "network_security": {
        "display_name": "Network Security",
        "pillar": "security",
        "description": "Implement defense-in-depth network security controls",
        "aws_services": ["Amazon VPC", "AWS WAF", "AWS Shield", "Security Groups", "NACLs"],
        "implementation_steps": [
            "Configure VPC with public/private subnet architecture",
            "Implement security groups with least-privilege ingress/egress rules",
            "Deploy AWS WAF with managed rule sets on CloudFront/ALB",
            "Enable VPC Flow Logs for network traffic analysis",
            "Configure Network ACLs as additional defense layer",
            "Use AWS PrivateLink for private service connectivity"
        ],
        "best_practices": [
            "Use separate VPCs for different environments",
            "Implement AWS Network Firewall for advanced inspection",
            "Enable AWS Shield Advanced for DDoS protection",
            "Use VPC endpoints to avoid public internet exposure"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 9,
        "compliance_impact": "SOC2, PCI-DSS, NIST"
    },
    "monitoring_detection": {
        "display_name": "Security Monitoring & Detection",
        "pillar": "security",
        "description": "Implement comprehensive security monitoring and threat detection",
        "aws_services": ["Amazon GuardDuty", "AWS Security Hub", "Amazon Detective", "CloudWatch"],
        "implementation_steps": [
            "Enable Amazon GuardDuty in all regions for threat detection",
            "Configure AWS Security Hub with CIS/PCI-DSS standards",
            "Set up CloudWatch alarms for security-related metrics",
            "Enable AWS Config rules for compliance monitoring",
            "Implement Amazon Detective for security investigation",
            "Configure SNS notifications for security findings"
        ],
        "best_practices": [
            "Aggregate findings in Security Hub across accounts",
            "Implement automated remediation with EventBridge + Lambda",
            "Regular review of GuardDuty findings",
            "Enable AWS CloudTrail Insights for anomaly detection"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 8,
        "compliance_impact": "SOC2, HIPAA, PCI-DSS"
    },
    "data_protection": {
        "display_name": "Data Protection",
        "pillar": "security",
        "description": "Implement data classification, protection, and lifecycle management",
        "aws_services": ["Amazon Macie", "AWS Backup", "S3 Object Lock", "DynamoDB PITR"],
        "implementation_steps": [
            "Enable Amazon Macie for sensitive data discovery",
            "Implement S3 bucket policies to prevent public access",
            "Configure S3 Object Lock for compliance data retention",
            "Enable versioning on all S3 buckets",
            "Implement DynamoDB Point-in-Time Recovery (PITR)",
            "Configure AWS Backup for centralized backup management"
        ],
        "best_practices": [
            "Classify data and apply appropriate protection controls",
            "Implement data retention policies aligned with compliance",
            "Use S3 Glacier for long-term archival",
            "Regular backup testing and recovery drills"
        ],
        "estimated_effort": "2-3 weeks",
        "priority_score": 8,
        "compliance_impact": "GDPR, HIPAA, SOC2"
    },

    # RELIABILITY PILLAR
    "redundancy": {
        "display_name": "Redundancy & High Availability",
        "pillar": "reliability",
        "description": "Implement multi-AZ and multi-region redundancy",
        "aws_services": ["Multi-AZ RDS", "S3 Cross-Region Replication", "Route 53", "Global Accelerator"],
        "implementation_steps": [
            "Deploy resources across multiple Availability Zones",
            "Enable Multi-AZ for RDS/Aurora databases",
            "Configure S3 Cross-Region Replication for critical data",
            "Implement Route 53 health checks with failover routing",
            "Use Application Load Balancer across multiple AZs",
            "Consider AWS Global Accelerator for global redundancy"
        ],
        "best_practices": [
            "Design for N+1 redundancy at minimum",
            "Implement active-passive or active-active failover",
            "Regular failover testing",
            "Document and test disaster recovery procedures"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 9,
        "compliance_impact": "Business Continuity, SLA Requirements"
    },
    "monitoring_alerting": {
        "display_name": "Monitoring & Alerting",
        "pillar": "reliability",
        "description": "Implement comprehensive monitoring and proactive alerting",
        "aws_services": ["Amazon CloudWatch", "AWS X-Ray", "CloudWatch Synthetics", "SNS"],
        "implementation_steps": [
            "Configure CloudWatch alarms for key metrics (CPU, memory, errors)",
            "Implement CloudWatch dashboards for operational visibility",
            "Enable AWS X-Ray for distributed tracing",
            "Set up CloudWatch Synthetics for endpoint monitoring",
            "Configure SNS topics for alert notifications",
            "Implement CloudWatch Logs Insights for log analysis"
        ],
        "best_practices": [
            "Define SLIs/SLOs and create corresponding alarms",
            "Implement anomaly detection alarms",
            "Use composite alarms to reduce alert fatigue",
            "Integrate with PagerDuty/OpsGenie for on-call"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 8,
        "compliance_impact": "Operational Excellence, SLA Monitoring"
    },
    "backup_recovery": {
        "display_name": "Backup & Recovery",
        "pillar": "reliability",
        "description": "Implement automated backup and tested recovery procedures",
        "aws_services": ["AWS Backup", "RDS Snapshots", "DynamoDB PITR", "S3 Versioning"],
        "implementation_steps": [
            "Configure AWS Backup with backup plans for all resources",
            "Enable automated RDS/Aurora snapshots with retention policies",
            "Enable DynamoDB Point-in-Time Recovery",
            "Configure S3 versioning and lifecycle policies",
            "Implement cross-region backup replication",
            "Document and test recovery procedures (RTO/RPO)"
        ],
        "best_practices": [
            "Define RTO/RPO requirements per workload",
            "Regular backup restoration testing",
            "Implement immutable backups for ransomware protection",
            "Automate recovery procedures with runbooks"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 9,
        "compliance_impact": "Business Continuity, Data Protection"
    },
    "scaling": {
        "display_name": "Auto Scaling",
        "pillar": "reliability",
        "description": "Implement automatic scaling to handle demand changes",
        "aws_services": ["Auto Scaling Groups", "Application Auto Scaling", "ECS Service Auto Scaling"],
        "implementation_steps": [
            "Configure EC2 Auto Scaling groups with target tracking",
            "Implement Application Auto Scaling for ECS/Lambda/DynamoDB",
            "Set up predictive scaling for known traffic patterns",
            "Configure scaling policies based on custom metrics",
            "Implement connection draining for graceful scale-in",
            "Test scaling behavior under load"
        ],
        "best_practices": [
            "Use target tracking scaling policies",
            "Implement warm pools for faster scale-out",
            "Set appropriate cooldown periods",
            "Monitor scaling activities and adjust thresholds"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 7,
        "compliance_impact": "Performance, Cost Optimization"
    },
    "fault_tolerance": {
        "display_name": "Fault Tolerance",
        "pillar": "reliability",
        "description": "Design systems to continue operating despite component failures",
        "aws_services": ["ELB Health Checks", "Route 53 Health Checks", "SQS Dead Letter Queues"],
        "implementation_steps": [
            "Implement health checks at load balancer level",
            "Configure circuit breakers for external dependencies",
            "Use SQS dead letter queues for failed message handling",
            "Implement retry logic with exponential backoff",
            "Design for graceful degradation",
            "Implement bulkhead patterns to isolate failures"
        ],
        "best_practices": [
            "Implement chaos engineering practices",
            "Use AWS Fault Injection Simulator for testing",
            "Design stateless applications where possible",
            "Implement idempotent operations"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 8,
        "compliance_impact": "System Reliability, SLA"
    },

    # OPERATIONAL EXCELLENCE PILLAR
    "observability": {
        "display_name": "Observability",
        "pillar": "operational_excellence",
        "description": "Implement comprehensive observability across metrics, logs, and traces",
        "aws_services": ["CloudWatch", "X-Ray", "CloudWatch Logs", "CloudWatch Container Insights"],
        "implementation_steps": [
            "Enable CloudWatch Container Insights for ECS/EKS",
            "Implement structured logging with CloudWatch Logs",
            "Configure AWS X-Ray for distributed tracing",
            "Create CloudWatch dashboards for key metrics",
            "Implement custom metrics for business KPIs",
            "Set up CloudWatch Logs Insights queries for analysis"
        ],
        "best_practices": [
            "Implement the three pillars: metrics, logs, traces",
            "Use correlation IDs across services",
            "Define and track SLIs/SLOs",
            "Implement log aggregation and analysis"
        ],
        "estimated_effort": "2-3 weeks",
        "priority_score": 8,
        "compliance_impact": "Operational Visibility, Incident Response"
    },
    "infrastructure_as_code": {
        "display_name": "Infrastructure as Code",
        "pillar": "operational_excellence",
        "description": "Manage all infrastructure through version-controlled code",
        "aws_services": ["AWS CloudFormation", "AWS CDK", "AWS SAM", "Terraform"],
        "implementation_steps": [
            "Convert existing resources to CloudFormation/CDK templates",
            "Implement nested stacks for modular infrastructure",
            "Set up CI/CD pipeline for infrastructure deployment",
            "Implement drift detection with AWS Config",
            "Use parameter stores for environment-specific values",
            "Implement stack policies to prevent accidental changes"
        ],
        "best_practices": [
            "Store templates in version control (Git)",
            "Implement code review for infrastructure changes",
            "Use change sets to preview changes",
            "Implement automated testing for templates"
        ],
        "estimated_effort": "3-6 weeks",
        "priority_score": 7,
        "compliance_impact": "Change Management, Audit Trail"
    },
    "deployment_automation": {
        "display_name": "Deployment Automation",
        "pillar": "operational_excellence",
        "description": "Implement automated, safe deployment pipelines",
        "aws_services": ["AWS CodePipeline", "AWS CodeBuild", "AWS CodeDeploy", "ECR"],
        "implementation_steps": [
            "Set up CodePipeline for CI/CD automation",
            "Configure CodeBuild for automated testing",
            "Implement blue/green or canary deployments with CodeDeploy",
            "Set up ECR for container image management",
            "Implement automated rollback on deployment failures",
            "Configure deployment approvals for production"
        ],
        "best_practices": [
            "Implement progressive deployment strategies",
            "Automate security scanning in pipeline",
            "Use feature flags for safe releases",
            "Implement deployment metrics and monitoring"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 7,
        "compliance_impact": "Change Management, Release Quality"
    },
    "incident_response": {
        "display_name": "Incident Response",
        "pillar": "operational_excellence",
        "description": "Implement structured incident detection and response procedures",
        "aws_services": ["CloudWatch Alarms", "SNS", "Systems Manager Incident Manager", "EventBridge"],
        "implementation_steps": [
            "Configure CloudWatch alarms for incident detection",
            "Set up SNS topics for incident notifications",
            "Implement AWS Systems Manager Incident Manager",
            "Create EventBridge rules for automated response",
            "Document incident response runbooks",
            "Implement post-incident review process"
        ],
        "best_practices": [
            "Define incident severity levels and escalation paths",
            "Implement on-call rotations",
            "Conduct regular incident response drills",
            "Maintain blameless post-mortems"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 8,
        "compliance_impact": "Incident Management, MTTR Reduction"
    },
    "runbook_automation": {
        "display_name": "Runbook Automation",
        "pillar": "operational_excellence",
        "description": "Automate operational procedures and remediation",
        "aws_services": ["Systems Manager Automation", "Lambda", "Step Functions", "EventBridge"],
        "implementation_steps": [
            "Create SSM Automation documents for common tasks",
            "Implement Lambda functions for automated remediation",
            "Use Step Functions for complex workflows",
            "Configure EventBridge for event-driven automation",
            "Document manual procedures as runbooks",
            "Implement approval workflows for sensitive operations"
        ],
        "best_practices": [
            "Start with most frequent manual tasks",
            "Implement idempotent automation",
            "Include rollback procedures",
            "Test automation in non-production first"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 6,
        "compliance_impact": "Operational Efficiency, Error Reduction"
    },

    # PERFORMANCE EFFICIENCY PILLAR
    "caching": {
        "display_name": "Caching Strategy",
        "pillar": "performance_efficiency",
        "description": "Implement caching at multiple layers to reduce latency",
        "aws_services": ["Amazon ElastiCache", "CloudFront", "DAX", "API Gateway Caching"],
        "implementation_steps": [
            "Deploy ElastiCache Redis/Memcached for application caching",
            "Configure CloudFront caching for static content",
            "Implement DAX for DynamoDB read acceleration",
            "Enable API Gateway response caching",
            "Implement cache invalidation strategies",
            "Monitor cache hit rates and optimize TTLs"
        ],
        "best_practices": [
            "Cache at the edge with CloudFront",
            "Use read replicas for database caching",
            "Implement cache-aside pattern",
            "Monitor and optimize cache hit ratios"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 7,
        "compliance_impact": "Performance, User Experience"
    },
    "compute_optimization": {
        "display_name": "Compute Optimization",
        "pillar": "performance_efficiency",
        "description": "Right-size and optimize compute resources",
        "aws_services": ["AWS Compute Optimizer", "EC2 Right Sizing", "Lambda Power Tuning"],
        "implementation_steps": [
            "Enable AWS Compute Optimizer for recommendations",
            "Analyze and implement EC2 right-sizing recommendations",
            "Use Lambda Power Tuning for optimal memory configuration",
            "Consider Graviton instances for cost-performance",
            "Implement spot instances for fault-tolerant workloads",
            "Monitor and adjust based on utilization patterns"
        ],
        "best_practices": [
            "Regular review of Compute Optimizer recommendations",
            "Use latest generation instance types",
            "Implement auto-scaling based on demand",
            "Consider serverless for variable workloads"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 6,
        "compliance_impact": "Cost Efficiency, Performance"
    },
    "content_delivery": {
        "display_name": "Content Delivery",
        "pillar": "performance_efficiency",
        "description": "Optimize content delivery for global users",
        "aws_services": ["Amazon CloudFront", "S3 Transfer Acceleration", "Global Accelerator"],
        "implementation_steps": [
            "Configure CloudFront distribution for static/dynamic content",
            "Enable S3 Transfer Acceleration for uploads",
            "Implement CloudFront Functions for edge processing",
            "Configure origin shield for origin protection",
            "Use Global Accelerator for TCP/UDP optimization",
            "Implement geographic routing with Route 53"
        ],
        "best_practices": [
            "Use appropriate cache behaviors",
            "Implement compression (gzip/brotli)",
            "Optimize origin response times",
            "Monitor CloudFront metrics and adjust"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 7,
        "compliance_impact": "User Experience, Global Performance"
    },
    "database_optimization": {
        "display_name": "Database Optimization",
        "pillar": "performance_efficiency",
        "description": "Optimize database performance and query efficiency",
        "aws_services": ["RDS Performance Insights", "Aurora", "DynamoDB", "ElastiCache"],
        "implementation_steps": [
            "Enable RDS Performance Insights for query analysis",
            "Implement read replicas for read scaling",
            "Optimize indexes based on query patterns",
            "Consider Aurora for improved performance",
            "Use DynamoDB for high-throughput workloads",
            "Implement connection pooling"
        ],
        "best_practices": [
            "Regular query performance analysis",
            "Implement database caching layer",
            "Use appropriate instance sizes",
            "Consider Aurora Serverless for variable workloads"
        ],
        "estimated_effort": "2-3 weeks",
        "priority_score": 7,
        "compliance_impact": "Application Performance, Scalability"
    },
    "resource_selection": {
        "display_name": "Resource Selection",
        "pillar": "performance_efficiency",
        "description": "Select optimal AWS resources for workload requirements",
        "aws_services": ["AWS Compute Optimizer", "Trusted Advisor", "Cost Explorer"],
        "implementation_steps": [
            "Review Compute Optimizer recommendations",
            "Analyze Trusted Advisor performance checks",
            "Evaluate serverless vs. container vs. EC2",
            "Consider managed services vs. self-managed",
            "Benchmark different instance types",
            "Document resource selection decisions"
        ],
        "best_practices": [
            "Match resource type to workload characteristics",
            "Use purpose-built databases",
            "Consider total cost of ownership",
            "Regular architecture reviews"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 6,
        "compliance_impact": "Cost Efficiency, Performance"
    },

    # COST OPTIMIZATION PILLAR
    "resource_optimization": {
        "display_name": "Resource Optimization",
        "pillar": "cost_optimization",
        "description": "Optimize resource utilization and eliminate waste",
        "aws_services": ["AWS Cost Explorer", "Trusted Advisor", "Compute Optimizer"],
        "implementation_steps": [
            "Enable Cost Explorer and analyze spending patterns",
            "Review Trusted Advisor cost optimization checks",
            "Identify and terminate unused resources",
            "Right-size over-provisioned instances",
            "Implement auto-scaling to match demand",
            "Set up cost allocation tags for visibility"
        ],
        "best_practices": [
            "Regular cost reviews (weekly/monthly)",
            "Implement resource tagging strategy",
            "Use AWS Organizations for consolidated billing",
            "Set up AWS Budgets with alerts"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 7,
        "compliance_impact": "Cost Reduction, Budget Management"
    },
    "managed_services": {
        "display_name": "Managed Services Adoption",
        "pillar": "cost_optimization",
        "description": "Leverage managed services to reduce operational overhead",
        "aws_services": ["RDS", "Aurora Serverless", "Lambda", "Fargate", "DynamoDB"],
        "implementation_steps": [
            "Evaluate self-managed vs. managed service options",
            "Migrate databases to RDS/Aurora",
            "Consider Lambda for event-driven workloads",
            "Use Fargate instead of EC2 for containers",
            "Implement DynamoDB for NoSQL workloads",
            "Calculate TCO including operational costs"
        ],
        "best_practices": [
            "Consider operational overhead in cost analysis",
            "Use serverless for variable workloads",
            "Leverage managed service features",
            "Regular review of new managed service offerings"
        ],
        "estimated_effort": "4-8 weeks",
        "priority_score": 6,
        "compliance_impact": "Operational Efficiency, TCO Reduction"
    },
    "pricing_models": {
        "display_name": "Pricing Model Optimization",
        "pillar": "cost_optimization",
        "description": "Optimize costs through appropriate pricing models",
        "aws_services": ["Savings Plans", "Reserved Instances", "Spot Instances"],
        "implementation_steps": [
            "Analyze usage patterns for commitment opportunities",
            "Purchase Compute Savings Plans for predictable workloads",
            "Implement Reserved Instances for steady-state databases",
            "Use Spot Instances for fault-tolerant workloads",
            "Consider Reserved Capacity for ElastiCache/OpenSearch",
            "Review and adjust commitments quarterly"
        ],
        "best_practices": [
            "Start with Savings Plans for flexibility",
            "Use Spot for batch processing and CI/CD",
            "Monitor commitment utilization",
            "Consider 1-year vs 3-year commitments"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 8,
        "compliance_impact": "20-40% Cost Savings"
    },
    "storage_optimization": {
        "display_name": "Storage Optimization",
        "pillar": "cost_optimization",
        "description": "Optimize storage costs through tiering and lifecycle policies",
        "aws_services": ["S3 Intelligent-Tiering", "S3 Lifecycle Policies", "EBS Optimization"],
        "implementation_steps": [
            "Enable S3 Intelligent-Tiering for unknown access patterns",
            "Implement S3 Lifecycle policies for archival",
            "Delete unused EBS snapshots and volumes",
            "Use gp3 volumes instead of gp2",
            "Implement data compression where applicable",
            "Review and optimize backup retention policies"
        ],
        "best_practices": [
            "Use appropriate storage classes",
            "Implement data lifecycle management",
            "Regular cleanup of unused storage",
            "Monitor storage growth trends"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 7,
        "compliance_impact": "Storage Cost Reduction"
    },
    "cost_monitoring": {
        "display_name": "Cost Monitoring & Governance",
        "pillar": "cost_optimization",
        "description": "Implement cost visibility and governance controls",
        "aws_services": ["AWS Budgets", "Cost Explorer", "Cost Anomaly Detection"],
        "implementation_steps": [
            "Set up AWS Budgets with threshold alerts",
            "Enable Cost Anomaly Detection",
            "Implement cost allocation tags",
            "Create Cost Explorer reports and dashboards",
            "Set up monthly cost review meetings",
            "Implement Service Control Policies for cost governance"
        ],
        "best_practices": [
            "Implement showback/chargeback",
            "Set budget alerts at 50%, 80%, 100%",
            "Regular cost optimization reviews",
            "Track cost per unit metrics"
        ],
        "estimated_effort": "1 week",
        "priority_score": 7,
        "compliance_impact": "Budget Control, Cost Visibility"
    },

    # SUSTAINABILITY PILLAR
    "efficient_compute": {
        "display_name": "Efficient Compute",
        "pillar": "sustainability",
        "description": "Maximize compute efficiency to reduce environmental impact",
        "aws_services": ["Graviton Instances", "Lambda", "Fargate", "Spot Instances"],
        "implementation_steps": [
            "Migrate to Graviton-based instances (up to 60% more efficient)",
            "Use Lambda for event-driven workloads",
            "Implement Fargate for containerized workloads",
            "Right-size instances to avoid over-provisioning",
            "Use Spot Instances for interruptible workloads",
            "Implement auto-scaling to match demand"
        ],
        "best_practices": [
            "Prefer serverless and managed services",
            "Use latest generation instances",
            "Implement efficient code practices",
            "Monitor and optimize utilization"
        ],
        "estimated_effort": "2-4 weeks",
        "priority_score": 6,
        "compliance_impact": "Carbon Footprint Reduction"
    },
    "resource_utilization": {
        "display_name": "Resource Utilization",
        "pillar": "sustainability",
        "description": "Maximize resource utilization to reduce waste",
        "aws_services": ["Compute Optimizer", "Auto Scaling", "CloudWatch"],
        "implementation_steps": [
            "Monitor resource utilization with CloudWatch",
            "Implement auto-scaling for all scalable resources",
            "Right-size based on Compute Optimizer recommendations",
            "Consolidate underutilized workloads",
            "Implement scheduling for non-production environments",
            "Use containerization for better resource sharing"
        ],
        "best_practices": [
            "Target 60-80% average utilization",
            "Implement dev/test environment scheduling",
            "Regular utilization reviews",
            "Use shared services where appropriate"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 6,
        "compliance_impact": "Resource Efficiency, Cost Savings"
    },
    "data_optimization": {
        "display_name": "Data Optimization",
        "pillar": "sustainability",
        "description": "Optimize data storage and transfer to reduce environmental impact",
        "aws_services": ["S3 Intelligent-Tiering", "Data Lifecycle Manager", "CloudFront"],
        "implementation_steps": [
            "Implement data lifecycle policies",
            "Use S3 Intelligent-Tiering for automatic optimization",
            "Delete unnecessary data and backups",
            "Implement data compression",
            "Use CloudFront to reduce data transfer",
            "Optimize data formats (Parquet, ORC for analytics)"
        ],
        "best_practices": [
            "Implement data retention policies",
            "Use efficient data formats",
            "Minimize data duplication",
            "Regular data cleanup"
        ],
        "estimated_effort": "1-2 weeks",
        "priority_score": 5,
        "compliance_impact": "Storage Efficiency, Data Governance"
    },
    "region_selection": {
        "display_name": "Region Selection",
        "pillar": "sustainability",
        "description": "Select regions with lower carbon intensity",
        "aws_services": ["AWS Regions", "Customer Carbon Footprint Tool"],
        "implementation_steps": [
            "Review AWS Customer Carbon Footprint Tool",
            "Consider regions powered by renewable energy",
            "Evaluate latency vs. sustainability trade-offs",
            "Use edge locations for content delivery",
            "Document region selection decisions",
            "Monitor carbon footprint metrics"
        ],
        "best_practices": [
            "Prefer regions with renewable energy",
            "Balance latency and sustainability",
            "Use multi-region only when necessary",
            "Track carbon footprint over time"
        ],
        "estimated_effort": "1 week",
        "priority_score": 4,
        "compliance_impact": "Carbon Footprint, ESG Reporting"
    }
}


def get_remediation_guidance(capability_name: str) -> Dict[str, Any]:
    """Get detailed remediation guidance for a specific capability."""
    return CAPABILITY_REMEDIATION_GUIDANCE.get(capability_name, {
        "display_name": capability_name.replace('_', ' ').title(),
        "description": f"Implement {capability_name.replace('_', ' ')} best practices",
        "aws_services": [],
        "implementation_steps": [f"Review AWS documentation for {capability_name.replace('_', ' ')}"],
        "best_practices": ["Follow AWS Well-Architected Framework guidelines"],
        "estimated_effort": "2-4 weeks",
        "priority_score": 5
    })


def enrich_recommendation_with_guidance(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a recommendation with detailed remediation guidance."""
    title = recommendation.get('title', '')
    
    # Extract capability name from title (e.g., "Implement monitoring_detection" -> "monitoring_detection")
    capability_name = title.lower().replace('implement ', '').replace('enhance ', '').replace(' ', '_')
    
    guidance = get_remediation_guidance(capability_name)
    
    if guidance:
        recommendation['remediation_guidance'] = {
            'display_name': guidance.get('display_name', capability_name),
            'aws_services': guidance.get('aws_services', []),
            'implementation_steps': guidance.get('implementation_steps', []),
            'best_practices': guidance.get('best_practices', []),
            'estimated_effort': guidance.get('estimated_effort', '2-4 weeks'),
            'compliance_impact': guidance.get('compliance_impact', '')
        }
    
    return recommendation
