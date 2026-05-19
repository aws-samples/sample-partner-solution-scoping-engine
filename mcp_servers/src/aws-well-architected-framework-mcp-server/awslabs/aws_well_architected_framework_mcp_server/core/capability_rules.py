"""
Capability Inference Rules for all WAFR Pillars.

This module defines the inference rules that map service categories to capabilities.
Rules are organized by pillar for clarity and maintainability.

Design Principles:
- Category-based: Rules use service categories, not specific names
- Progressive coverage: Multiple rules with increasing coverage levels
- Composite rules: Support service combinations for higher coverage
- Pattern-aware: Some rules consider architectural patterns
"""

from typing import List

from .capability_inference_engine import InferenceRule, RuleConditionType


def get_security_rules() -> List[InferenceRule]:
    """
    Get inference rules for Security pillar capabilities.
    
    Security Capabilities:
    - encryption: Data protection through encryption
    - identity_access: Identity and access management
    - network_security: Network protection and isolation
    - monitoring_detection: Security monitoring and threat detection
    - data_protection: Data classification and protection
    """
    return [
        # ENCRYPTION CAPABILITY
        InferenceRule(
            capability_name='encryption',
            pillar='security',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'security'},
            coverage=0.3,
            confidence=0.7,
            weight=0.25,
            description='Any security service detected'
        ),
        InferenceRule(
            capability_name='encryption',
            pillar='security',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['security', 'database']]},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='Security service + database service'
        ),
        InferenceRule(
            capability_name='encryption',
            pillar='security',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['security', 'storage']]},
            coverage=0.7,
            confidence=0.8,
            weight=0.25,
            description='Security service + storage service'
        ),
        InferenceRule(
            capability_name='encryption',
            pillar='security',
            condition_type=RuleConditionType.ALL_CATEGORIES,
            condition_params={'categories': ['security', 'database', 'storage']},
            coverage=0.9,
            confidence=0.9,
            weight=0.25,
            description='Security + database + storage services'
        ),
        
        # IDENTITY_ACCESS CAPABILITY
        InferenceRule(
            capability_name='identity_access',
            pillar='security',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'security'},
            coverage=0.5,
            confidence=0.8,
            weight=0.20,
            description='Security service detected (IAM, Cognito, etc.)'
        ),
        InferenceRule(
            capability_name='identity_access',
            pillar='security',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['security', 'networking']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.20,
            description='Security + API Gateway/networking'
        ),
        
        # NETWORK_SECURITY CAPABILITY
        InferenceRule(
            capability_name='network_security',
            pillar='security',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'networking'},
            coverage=0.5,
            confidence=0.7,
            weight=0.20,
            description='VPC or networking service detected'
        ),
        InferenceRule(
            capability_name='network_security',
            pillar='security',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['networking', 'security']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.20,
            description='VPC + WAF/security service'
        ),
        
        # MONITORING_DETECTION CAPABILITY
        InferenceRule(
            capability_name='monitoring_detection',
            pillar='security',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'monitoring'},
            coverage=0.5,
            confidence=0.8,
            weight=0.20,
            description='Monitoring service detected'
        ),
        InferenceRule(
            capability_name='monitoring_detection',
            pillar='security',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'monitoring', 'min_count': 2},
            coverage=0.7,
            confidence=0.9,
            weight=0.20,
            description='Multiple monitoring services (CloudWatch + X-Ray)'
        ),
        
        # DATA_PROTECTION CAPABILITY
        InferenceRule(
            capability_name='data_protection',
            pillar='security',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['security', 'storage'], ['security', 'database']]},
            coverage=0.6,
            confidence=0.8,
            weight=0.15,
            description='Security + data storage services'
        ),
    ]


def get_reliability_rules() -> List[InferenceRule]:
    """
    Get inference rules for Reliability pillar capabilities.
    
    Reliability Capabilities:
    - redundancy: High availability and fault tolerance
    - monitoring_alerting: System monitoring and alerting
    - backup_recovery: Backup and disaster recovery
    - scaling: Auto-scaling and elasticity
    """
    return [
        # REDUNDANCY CAPABILITY
        InferenceRule(
            capability_name='redundancy',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.6,
            confidence=0.8,
            weight=0.30,
            description='Managed database (DynamoDB, RDS, Aurora)'
        ),
        InferenceRule(
            capability_name='redundancy',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.5,
            confidence=0.7,
            weight=0.30,
            description='Serverless compute (Lambda) or managed compute'
        ),
        InferenceRule(
            capability_name='redundancy',
            pillar='reliability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['networking', 'compute']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.30,
            description='Load balancer + compute (auto-scaling)'
        ),
        
        # MONITORING_ALERTING CAPABILITY - ENHANCED DETECTION
        InferenceRule(
            capability_name='monitoring_alerting',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'monitoring'},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='Monitoring service detected (CloudWatch)'
        ),
        InferenceRule(
            capability_name='monitoring_alerting',
            pillar='reliability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['monitoring', 'integration']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='CloudWatch + SNS (alerting pipeline)'
        ),
        InferenceRule(
            capability_name='monitoring_alerting',
            pillar='reliability',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'monitoring', 'min_count': 2},
            coverage=0.85,
            confidence=0.9,
            weight=0.25,
            description='Multiple monitoring services (CloudWatch + X-Ray/CloudTrail)'
        ),
        InferenceRule(
            capability_name='monitoring_alerting',
            pillar='reliability',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'alarm', 'alert', 'notification', 'threshold', 'metric',
                    'cloudwatch alarm', 'sns notification', 'pagerduty', 'opsgenie',
                    'dashboard', 'monitoring', 'health check', 'healthcheck',
                    'cpu utilization', 'memory utilization', '5xx', '4xx', 'error rate',
                    'latency', 'response time', 'availability', 'uptime'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.25,
            description='Alerting/monitoring keywords detected in architecture'
        ),
        
        # BACKUP_RECOVERY CAPABILITY - ENHANCED DETECTION
        InferenceRule(
            capability_name='backup_recovery',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'storage'},
            coverage=0.5,
            confidence=0.7,
            weight=0.20,
            description='Storage service with backup capability (S3 versioning)'
        ),
        InferenceRule(
            capability_name='backup_recovery',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.6,
            confidence=0.8,
            weight=0.20,
            description='Managed database with automated backups (RDS, DynamoDB PITR)'
        ),
        InferenceRule(
            capability_name='backup_recovery',
            pillar='reliability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['database', 'storage']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.20,
            description='Database + storage services (comprehensive backup strategy)'
        ),
        InferenceRule(
            capability_name='backup_recovery',
            pillar='reliability',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'backup', 'recovery', 'restore', 'snapshot', 'pitr',
                    'point-in-time', 'retention', 'aws backup', 'backup plan',
                    'disaster recovery', 'dr', 'rpo', 'rto', 'failover',
                    'replication', 'cross-region', 'versioning', 'lifecycle'
                ],
                'min_matches': 1
            },
            coverage=0.85,
            confidence=0.9,
            weight=0.20,
            description='Backup/recovery keywords detected in architecture'
        ),
        
        # SCALING CAPABILITY
        InferenceRule(
            capability_name='scaling',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='Serverless compute (auto-scaling)'
        ),
        InferenceRule(
            capability_name='scaling',
            pillar='reliability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['compute', 'database']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='Auto-scaling compute + database'
        ),
    ]


def get_performance_rules() -> List[InferenceRule]:
    """
    Get inference rules for Performance pillar capabilities.
    
    Performance Capabilities:
    - caching: Content and data caching
    - compute_optimization: Compute resource optimization
    - content_delivery: Content delivery and CDN
    - database_optimization: Database performance optimization
    """
    return [
        # CACHING CAPABILITY
        InferenceRule(
            capability_name='caching',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'networking'},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='CDN service (CloudFront)'
        ),
        InferenceRule(
            capability_name='caching',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.7,
            confidence=0.9,
            weight=0.25,
            description='Cache service (ElastiCache, MemoryDB)'
        ),
        InferenceRule(
            capability_name='caching',
            pillar='performance',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['networking', 'storage']]},
            coverage=0.9,
            confidence=0.9,
            weight=0.25,
            description='CDN + storage (CloudFront + S3)'
        ),
        
        # COMPUTE_OPTIMIZATION CAPABILITY
        InferenceRule(
            capability_name='compute_optimization',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.6,
            confidence=0.7,
            weight=0.25,
            description='Serverless or managed compute'
        ),
        InferenceRule(
            capability_name='compute_optimization',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.5,
            confidence=0.7,
            weight=0.25,
            description='Container service (ECS, EKS, Fargate)'
        ),
        
        # CONTENT_DELIVERY CAPABILITY
        InferenceRule(
            capability_name='content_delivery',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'networking'},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='CDN service detected'
        ),
        InferenceRule(
            capability_name='content_delivery',
            pillar='performance',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['networking', 'storage']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='CDN + storage service'
        ),
        
        # DATABASE_OPTIMIZATION CAPABILITY
        InferenceRule(
            capability_name='database_optimization',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.6,
            confidence=0.7,
            weight=0.25,
            description='Managed database service'
        ),
        InferenceRule(
            capability_name='database_optimization',
            pillar='performance',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'performance insights', 'enhanced monitoring', 'read replica',
                    'aurora', 'dynamodb', 'elasticache', 'memorydb', 'redis',
                    'query optimization', 'index', 'partition key', 'sort key',
                    'provisioned iops', 'gp3', 'io1', 'io2'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.25,
            description='Database optimization keywords detected'
        ),
        
        # RESOURCE_SELECTION CAPABILITY - NEW
        InferenceRule(
            capability_name='resource_selection',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.6,
            confidence=0.7,
            weight=0.20,
            description='Compute service with right-sizing capability'
        ),
        InferenceRule(
            capability_name='resource_selection',
            pillar='performance',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.7,
            confidence=0.8,
            weight=0.20,
            description='Container service with resource allocation (ECS/EKS)'
        ),
        InferenceRule(
            capability_name='resource_selection',
            pillar='performance',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'instance type', 'instance class', 'cpu', 'memory', 'vcpu',
                    'graviton', 'arm64', 'x86', 'r6g', 'm6g', 'c6g', 't3', 'm5',
                    'right-sizing', 'rightsizing', 'compute optimizer',
                    'auto scaling', 'autoscaling', 'target tracking'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.20,
            description='Resource selection keywords detected in architecture'
        ),
    ]


def get_cost_optimization_rules() -> List[InferenceRule]:
    """
    Get inference rules for Cost Optimization pillar capabilities.
    
    Cost Optimization Capabilities:
    - resource_optimization: Resource rightsizing and optimization
    - managed_services: Use of managed services
    - pricing_models: Cost-effective pricing models
    - storage_optimization: Storage cost optimization
    
    FIXED: Enhanced managed_services detection to match Sustainability pillar rules.
    Previously required ALL categories (compute + database + storage), now accepts
    ANY managed service category for proper detection of Lambda, Fargate, DynamoDB, etc.
    """
    return [
        # RESOURCE_OPTIMIZATION CAPABILITY
        InferenceRule(
            capability_name='resource_optimization',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.7,
            confidence=0.8,
            weight=0.30,
            description='Serverless compute (pay-per-use)'
        ),
        InferenceRule(
            capability_name='resource_optimization',
            pillar='cost_optimization',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['compute', 'database']]},
            coverage=0.8,
            confidence=0.9,
            weight=0.30,
            description='Serverless compute + managed database'
        ),
        
        # MANAGED_SERVICES CAPABILITY - ENHANCED DETECTION (aligned with Sustainability pillar)
        # Serverless compute services (Lambda, Fargate) - reduces operational costs
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='Serverless compute (Lambda, Fargate) - pay-per-use pricing model'
        ),
        # Managed database services (DynamoDB, RDS, Aurora)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='Managed database service (DynamoDB, RDS, Aurora) - no infrastructure management overhead'
        ),
        # Managed storage services (S3)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'storage'},
            coverage=0.7,
            confidence=0.8,
            weight=0.25,
            description='Managed storage service (S3) - pay for what you use'
        ),
        # Container services (ECS, EKS with Fargate)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.7,
            confidence=0.8,
            weight=0.25,
            description='Managed container service (ECS, EKS, Fargate) - efficient resource utilization'
        ),
        # Integration services (SNS, SQS, EventBridge)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'integration'},
            coverage=0.6,
            confidence=0.8,
            weight=0.25,
            description='Managed integration services (SNS, SQS, EventBridge) - serverless event processing'
        ),
        # Multiple managed services combination (higher coverage)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['compute', 'database'], ['compute', 'storage'], ['database', 'storage']]},
            coverage=0.9,
            confidence=0.95,
            weight=0.25,
            description='Multiple managed services - comprehensive cost-optimized architecture'
        ),
        # All three core managed services (compute, database, storage)
        InferenceRule(
            capability_name='managed_services',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ALL_CATEGORIES,
            condition_params={'categories': ['compute', 'database', 'storage']},
            coverage=1.0,
            confidence=0.95,
            weight=0.25,
            description='Fully managed architecture (Lambda + DynamoDB/RDS + S3) - maximum cost optimization'
        ),
        
        # PRICING_MODELS CAPABILITY
        InferenceRule(
            capability_name='pricing_models',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.5,
            confidence=0.6,
            weight=0.20,
            description='Flexible compute pricing (serverless)'
        ),
        
        # STORAGE_OPTIMIZATION CAPABILITY
        InferenceRule(
            capability_name='storage_optimization',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'storage'},
            coverage=0.6,
            confidence=0.7,
            weight=0.25,
            description='Storage service with lifecycle policies'
        ),
    ]


def get_operational_excellence_rules() -> List[InferenceRule]:
    """
    Get inference rules for Operational Excellence pillar capabilities.
    
    Operational Excellence Capabilities:
    - observability: System observability and monitoring
    - infrastructure_as_code: IaC and automation
    - deployment_automation: CI/CD and deployment automation
    - incident_response: Incident management and response
    
    FIXED: Added TEXT_KEYWORD_MATCH rules to detect IaC and CI/CD mentions in document
    text, not just in the identified_services list. This fixes false negatives where
    CloudFormation/CDK/Terraform are mentioned in architecture documents but not
    extracted as discrete services.
    """
    return [
        # OBSERVABILITY CAPABILITY
        InferenceRule(
            capability_name='observability',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'monitoring'},
            coverage=0.4,
            confidence=0.7,
            weight=0.30,
            description='Monitoring service detected'
        ),
        InferenceRule(
            capability_name='observability',
            pillar='operational_excellence',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'monitoring', 'min_count': 2},
            coverage=0.7,
            confidence=0.9,
            weight=0.30,
            description='Multiple monitoring services (CloudWatch + X-Ray)'
        ),
        InferenceRule(
            capability_name='observability',
            pillar='operational_excellence',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'monitoring', 'min_count': 3},
            coverage=0.9,
            confidence=0.9,
            weight=0.30,
            description='Comprehensive monitoring (CloudWatch + X-Ray + CloudTrail)'
        ),
        
        # INFRASTRUCTURE_AS_CODE CAPABILITY - ENHANCED WITH COMPREHENSIVE DETECTION
        # Category-based detection (when CloudFormation/CDK is in identified_services)
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'deployment'},
            coverage=0.8,
            confidence=0.9,
            weight=0.25,
            description='IaC service (CloudFormation, CDK) in identified services'
        ),
        # Text-based detection - explicit IaC tool mentions (works for all file formats)
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    # IaC tools - commonly mentioned in architecture docs
                    'cloudformation', 'aws cloudformation', 'cfn',
                    'cdk', 'cloud development kit', 'aws cdk',
                    'terraform', 'hashicorp terraform', 'tf',
                    'pulumi', 'serverless framework', 'sam', 'aws sam',
                    'ansible', 'chef', 'puppet',
                    # IaC concepts
                    'infrastructure as code', 'infrastructure-as-code', 'iac',
                    'template.yaml', 'template.json', 'stack',
                    'nested stack', 'cross-stack', 'cloudformation stack',
                    'declarative', 'idempotent', 'version controlled infrastructure'
                ],
                'min_matches': 1
            },
            coverage=0.85,
            confidence=0.9,
            weight=0.25,
            description='IaC tool/concept explicitly mentioned (CloudFormation, CDK, Terraform, SAM, Ansible)'
        ),
        # Architecture diagram patterns - common in PNG/JPEG/PDF diagrams (OCR text)
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    # Common diagram labels that imply defined infrastructure
                    'architecture diagram', 'system architecture', 'aws architecture',
                    'infrastructure diagram', 'network diagram', 'deployment diagram',
                    'high availability', 'multi-az', 'multi-region',
                    # Configuration indicators from diagrams/docs
                    'vpc', 'subnet', 'security group', 'nacl',
                    'auto scaling group', 'asg', 'launch template',
                    'target group', 'load balancer', 'alb', 'nlb',
                    'nat gateway', 'internet gateway', 'igw',
                    # Resource specifications (common in architecture docs)
                    'instance type', 't3.', 'm5.', 'r5.', 'c5.',
                    'db.r5', 'db.r6g', 'db.m5', 'cache.r5', 'cache.r6g'
                ],
                'min_matches': 3
            },
            coverage=0.7,
            confidence=0.75,
            weight=0.25,
            description='Architecture diagram/document patterns indicate defined infrastructure'
        ),
        # XML/JSON/YAML structure detection (for structured file formats)
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    # XML structure indicators
                    'awsarchitecture', '<vpc', '<ecs', '<rds', '<lambda',
                    '<s3', '<dynamodb', '<cloudfront', '<route53',
                    'taskdefinition', 'securitygroup',
                    # JSON/YAML structure indicators  
                    'resources:', 'type: aws::', 'aws::',
                    'properties:', 'dependson', 'ref:', '!ref',
                    # CloudFormation/CDK patterns
                    'cidrblock', 'availabilityzone', 'instancetype',
                    'desiredcount', 'targetgroup', 'listener'
                ],
                'min_matches': 3
            },
            coverage=0.75,
            confidence=0.8,
            weight=0.25,
            description='Structured definition (XML/JSON/YAML) indicates IaC approach'
        ),
        # Comprehensive architecture implies IaC (4+ service categories = complex infra)
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ALL_CATEGORIES,
            condition_params={'categories': ['compute', 'database', 'networking', 'storage']},
            coverage=0.65,
            confidence=0.7,
            weight=0.25,
            description='Comprehensive multi-service architecture typically requires IaC for management'
        ),
        # Even 3 core categories suggest IaC is needed
        InferenceRule(
            capability_name='infrastructure_as_code',
            pillar='operational_excellence',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [
                ['compute', 'database', 'networking'],
                ['compute', 'storage', 'networking'],
                ['compute', 'database', 'storage']
            ]},
            coverage=0.6,
            confidence=0.65,
            weight=0.25,
            description='Multi-tier architecture (3+ categories) benefits from IaC'
        ),
        
        # DEPLOYMENT_AUTOMATION CAPABILITY - ENHANCED WITH TEXT DETECTION
        # Category-based detection
        InferenceRule(
            capability_name='deployment_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'deployment'},
            coverage=0.7,
            confidence=0.8,
            weight=0.25,
            description='Deployment service detected'
        ),
        InferenceRule(
            capability_name='deployment_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'deployment', 'min_count': 2},
            coverage=0.9,
            confidence=0.9,
            weight=0.25,
            description='Multiple deployment services (CI/CD pipeline)'
        ),
        # Container services imply deployment automation (ECS/EKS have built-in deployment)
        InferenceRule(
            capability_name='deployment_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.6,
            confidence=0.7,
            weight=0.25,
            description='Container service (ECS/EKS) with built-in deployment capabilities'
        ),
        # Lambda implies deployment automation (serverless deployment)
        InferenceRule(
            capability_name='deployment_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.5,
            confidence=0.6,
            weight=0.25,
            description='Serverless compute (Lambda) with automated deployment model'
        ),
        # Text-based detection for CI/CD mentions
        InferenceRule(
            capability_name='deployment_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'codepipeline', 'aws codepipeline', 'code pipeline',
                    'codebuild', 'aws codebuild', 'code build',
                    'codedeploy', 'aws codedeploy', 'code deploy',
                    'ci/cd', 'cicd', 'ci cd', 'continuous integration', 'continuous deployment',
                    'continuous delivery', 'pipeline', 'deployment pipeline',
                    'jenkins', 'github actions', 'gitlab ci', 'circleci',
                    'blue/green', 'blue-green', 'canary deployment', 'rolling deployment',
                    'automated deployment', 'auto deploy', 'deployment automation',
                    'fargate', 'ecs service', 'task definition', 'ecr',
                    'auto scaling', 'autoscaling', 'desired count', 'rolling update'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.25,
            description='CI/CD or container deployment keywords detected in document text'
        ),
        
        # INCIDENT_RESPONSE CAPABILITY
        InferenceRule(
            capability_name='incident_response',
            pillar='operational_excellence',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['monitoring', 'integration']]},
            coverage=0.7,
            confidence=0.8,
            weight=0.20,
            description='Monitoring + alerting (CloudWatch + SNS)'
        ),
        # Monitoring service alone indicates some incident response capability
        InferenceRule(
            capability_name='incident_response',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'monitoring'},
            coverage=0.5,
            confidence=0.6,
            weight=0.20,
            description='Monitoring service (CloudWatch) provides alerting for incident detection'
        ),
        # Multiple monitoring services indicate better incident response
        InferenceRule(
            capability_name='incident_response',
            pillar='operational_excellence',
            condition_type=RuleConditionType.CATEGORY_COUNT,
            condition_params={'category': 'monitoring', 'min_count': 2},
            coverage=0.7,
            confidence=0.8,
            weight=0.20,
            description='Multiple monitoring services for comprehensive incident detection'
        ),
        # Text-based detection for incident response
        InferenceRule(
            capability_name='incident_response',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'incident response', 'incident management', 'runbook',
                    'playbook', 'on-call', 'oncall', 'pagerduty', 'opsgenie',
                    'systems manager', 'ssm', 'automation document',
                    'cloudwatch alarm', 'alarm action', 'sns notification',
                    'auto-remediation', 'self-healing', 'automated recovery',
                    'alarm', 'alert', 'notification', 'threshold', 'metric',
                    'health check', 'healthcheck', 'monitoring', 'dashboard'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.20,
            description='Incident response/alerting keywords detected in document text'
        ),
    ]


def get_sustainability_rules() -> List[InferenceRule]:
    """
    Get inference rules for Sustainability pillar capabilities.
    
    Sustainability Capabilities:
    - managed_services: Use of managed services (reduced carbon footprint)
    - efficient_compute: Efficient compute resources
    - resource_utilization: Optimal resource utilization
    - data_optimization: Data storage and transfer optimization
    
    FIXED: Enhanced managed_services detection to properly recognize Lambda, DynamoDB,
    S3, Fargate, and other serverless/managed services. This addresses the issue where
    managed services were not being credited in sustainability scoring.
    """
    return [
        # MANAGED_SERVICES CAPABILITY - ENHANCED DETECTION
        # Serverless compute services (Lambda, Fargate)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.8,
            confidence=0.9,
            weight=0.35,
            description='Serverless compute (Lambda, Fargate) - reduces operational overhead and environmental impact'
        ),
        # Managed database services (DynamoDB, RDS, Aurora)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.8,
            confidence=0.9,
            weight=0.35,
            description='Managed database service (DynamoDB, RDS, Aurora) - AWS-managed infrastructure optimization'
        ),
        # Managed storage services (S3)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'storage'},
            coverage=0.7,
            confidence=0.8,
            weight=0.35,
            description='Managed storage service (S3) - automatic optimization and lifecycle management'
        ),
        # Container services (ECS, EKS with Fargate)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.7,
            confidence=0.8,
            weight=0.35,
            description='Managed container service (ECS, EKS, Fargate) - efficient resource utilization'
        ),
        # Integration services (SNS, SQS, EventBridge, Step Functions)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'integration'},
            coverage=0.6,
            confidence=0.8,
            weight=0.35,
            description='Managed integration services (SNS, SQS, EventBridge) - serverless event processing'
        ),
        # API Gateway and networking services
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'networking'},
            coverage=0.6,
            confidence=0.7,
            weight=0.35,
            description='Managed networking services (API Gateway, CloudFront) - AWS-optimized infrastructure'
        ),
        # Multiple managed services combination (higher coverage)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['compute', 'database'], ['compute', 'storage'], ['database', 'storage']]},
            coverage=0.9,
            confidence=0.95,
            weight=0.35,
            description='Multiple managed services - comprehensive serverless/managed architecture'
        ),
        # All three core managed services (compute, database, storage)
        InferenceRule(
            capability_name='managed_services',
            pillar='sustainability',
            condition_type=RuleConditionType.ALL_CATEGORIES,
            condition_params={'categories': ['compute', 'database', 'storage']},
            coverage=1.0,
            confidence=0.95,
            weight=0.35,
            description='Fully managed architecture (Lambda + DynamoDB/RDS + S3) - maximum sustainability benefit'
        ),
        
        # EFFICIENT_COMPUTE CAPABILITY
        InferenceRule(
            capability_name='efficient_compute',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.8,
            confidence=0.8,
            weight=0.30,
            description='Serverless compute (efficient scaling and resource utilization)'
        ),
        InferenceRule(
            capability_name='efficient_compute',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'container'},
            coverage=0.7,
            confidence=0.8,
            weight=0.30,
            description='Container services (efficient resource packing)'
        ),
        
        # RESOURCE_UTILIZATION CAPABILITY
        InferenceRule(
            capability_name='resource_utilization',
            pillar='sustainability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['compute', 'monitoring']]},
            coverage=0.6,
            confidence=0.7,
            weight=0.20,
            description='Compute + monitoring (utilization tracking and optimization)'
        ),
        InferenceRule(
            capability_name='resource_utilization',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.5,
            confidence=0.6,
            weight=0.20,
            description='Serverless compute (automatic resource optimization)'
        ),
        
        # DATA_OPTIMIZATION CAPABILITY
        InferenceRule(
            capability_name='data_optimization',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'storage'},
            coverage=0.6,
            confidence=0.7,
            weight=0.15,
            description='Storage service with optimization features (S3 Intelligent-Tiering, lifecycle policies)'
        ),
        InferenceRule(
            capability_name='data_optimization',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.5,
            confidence=0.6,
            weight=0.15,
            description='Managed database with automatic optimization'
        ),
        
        # REGION_SELECTION CAPABILITY - NEW
        # Multi-region or region-aware architecture
        InferenceRule(
            capability_name='region_selection',
            pillar='sustainability',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'multi-region', 'multiregion', 'cross-region', 'global',
                    'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast',
                    'region', 'availability zone', 'az', 'multi-az',
                    'disaster recovery', 'dr', 'failover', 'replication'
                ],
                'min_matches': 1
            },
            coverage=0.7,
            confidence=0.8,
            weight=0.10,
            description='Region-aware architecture with multi-region or multi-AZ deployment'
        ),
        # CloudFront or Route53 indicates global/regional awareness
        InferenceRule(
            capability_name='region_selection',
            pillar='sustainability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'networking'},
            coverage=0.6,
            confidence=0.7,
            weight=0.10,
            description='CDN or DNS service indicates region-aware content delivery'
        ),
    ]


def get_additional_reliability_rules() -> List[InferenceRule]:
    """
    Get additional inference rules for Reliability pillar capabilities.
    
    Adds fault_tolerance capability that was missing from the original rules.
    """
    return [
        # FAULT_TOLERANCE CAPABILITY - NEW
        InferenceRule(
            capability_name='fault_tolerance',
            pillar='reliability',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['networking', 'compute'], ['database', 'storage']]},
            coverage=0.7,
            confidence=0.8,
            weight=0.25,
            description='Load balancer + compute or database + storage indicates fault tolerance design'
        ),
        InferenceRule(
            capability_name='fault_tolerance',
            pillar='reliability',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'multi-az', 'multiaz', 'high availability', 'ha',
                    'failover', 'automatic failover', 'fault tolerant',
                    'redundant', 'redundancy', 'replica', 'read replica',
                    'standby', 'warm standby', 'hot standby', 'pilot light'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.25,
            description='Fault tolerance keywords detected in architecture'
        ),
        InferenceRule(
            capability_name='fault_tolerance',
            pillar='reliability',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'database'},
            coverage=0.6,
            confidence=0.7,
            weight=0.25,
            description='Managed database with built-in fault tolerance (RDS Multi-AZ, DynamoDB)'
        ),
    ]


def get_additional_operational_excellence_rules() -> List[InferenceRule]:
    """
    Get additional inference rules for Operational Excellence pillar capabilities.
    
    Adds runbook_automation capability for operational maturity.
    """
    return [
        # RUNBOOK_AUTOMATION CAPABILITY - NEW
        InferenceRule(
            capability_name='runbook_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.SERVICE_COMBINATION,
            condition_params={'combinations': [['monitoring', 'compute'], ['monitoring', 'integration']]},
            coverage=0.6,
            confidence=0.7,
            weight=0.15,
            description='Monitoring + compute/integration enables automated runbooks'
        ),
        InferenceRule(
            capability_name='runbook_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'runbook', 'playbook', 'automation', 'ssm', 'systems manager',
                    'auto-remediation', 'self-healing', 'automated recovery',
                    'lambda trigger', 'eventbridge rule', 'step functions',
                    'state machine', 'workflow', 'orchestration'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.15,
            description='Runbook/automation keywords detected in architecture'
        ),
        InferenceRule(
            capability_name='runbook_automation',
            pillar='operational_excellence',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'compute'},
            coverage=0.5,
            confidence=0.6,
            weight=0.15,
            description='Serverless compute (Lambda) enables automated operational tasks'
        ),
    ]


def get_additional_cost_rules() -> List[InferenceRule]:
    """
    Get additional inference rules for Cost Optimization pillar capabilities.
    
    Adds cost_monitoring capability that was missing from the original rules.
    """
    return [
        # COST_MONITORING CAPABILITY - NEW
        InferenceRule(
            capability_name='cost_monitoring',
            pillar='cost_optimization',
            condition_type=RuleConditionType.ANY_CATEGORY,
            condition_params={'category': 'monitoring'},
            coverage=0.6,
            confidence=0.7,
            weight=0.20,
            description='Monitoring service can be used for cost tracking'
        ),
        InferenceRule(
            capability_name='cost_monitoring',
            pillar='cost_optimization',
            condition_type=RuleConditionType.TEXT_KEYWORD_MATCH,
            condition_params={
                'keywords': [
                    'budget', 'cost', 'billing', 'cost explorer',
                    'savings plan', 'reserved', 'spot', 'on-demand',
                    'cost allocation', 'tagging', 'cost center'
                ],
                'min_matches': 1
            },
            coverage=0.8,
            confidence=0.85,
            weight=0.20,
            description='Cost monitoring keywords detected in architecture'
        ),
    ]


def initialize_all_rules(engine):
    """
    Initialize all capability inference rules in the engine.
    
    Args:
        engine: CapabilityInferenceEngine instance
    """
    # Add rules for all pillars
    engine.add_rules(get_security_rules())
    engine.add_rules(get_reliability_rules())
    engine.add_rules(get_additional_reliability_rules())  # NEW: fault_tolerance
    engine.add_rules(get_performance_rules())
    engine.add_rules(get_cost_optimization_rules())
    engine.add_rules(get_additional_cost_rules())  # NEW: cost_monitoring
    engine.add_rules(get_operational_excellence_rules())
    engine.add_rules(get_additional_operational_excellence_rules())  # NEW: runbook_automation
    engine.add_rules(get_sustainability_rules())  # Includes region_selection
