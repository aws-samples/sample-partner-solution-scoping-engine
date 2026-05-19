"""
Infrastructure as Code Evidence Extractor - Phase 3 Implementation.

This module provides direct parsing of CloudFormation and Terraform templates
to extract AWS services and their configurations with high confidence.

Implements:
- UNIV-001: Evidence-Based Identification
- UNIV-002: Configuration Depth Analysis
- UNIV-004: Multi-Source Reconciliation

Supports:
- CloudFormation (YAML and JSON)
- Terraform (HCL)
"""

import json
import re
import yaml
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.logger import WAFRLogger


class IaCType(str, Enum):
    """Types of Infrastructure as Code."""
    CLOUDFORMATION = "cloudformation"
    TERRAFORM = "terraform"
    CDK_SYNTH = "cdk_synthesized"
    SAM = "sam"
    UNKNOWN = "unknown"


@dataclass
class ExtractedResource:
    """A resource extracted from IaC template."""
    resource_type: str
    resource_name: str
    service_name: str
    properties: Dict[str, Any]
    security_configs: Dict[str, Any] = field(default_factory=dict)
    reliability_configs: Dict[str, Any] = field(default_factory=dict)
    sustainability_configs: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.95  # High confidence for IaC extraction


@dataclass
class IaCExtractionResult:
    """Result of IaC template extraction."""
    iac_type: IaCType
    resources: List[ExtractedResource]
    services: Set[str]
    security_features: Dict[str, Any]
    reliability_features: Dict[str, Any]
    sustainability_features: Dict[str, Any]
    architecture_patterns: List[str]
    extraction_metadata: Dict[str, Any]


class IaCEvidenceExtractor:
    """
    Extracts AWS services and configurations directly from IaC templates.
    
    This provides the highest confidence service identification by parsing
    actual resource definitions rather than relying on text analysis.
    """
    
    # CloudFormation resource type to service name mapping
    CFN_SERVICE_MAP: Dict[str, str] = {
        # Compute
        'AWS::EC2::Instance': 'EC2',
        'AWS::EC2::LaunchTemplate': 'EC2',
        'AWS::AutoScaling::AutoScalingGroup': 'Auto Scaling',
        'AWS::AutoScaling::LaunchConfiguration': 'Auto Scaling',
        'AWS::Lambda::Function': 'Lambda',
        'AWS::Serverless::Function': 'Lambda',
        'AWS::ECS::Cluster': 'ECS',
        'AWS::ECS::Service': 'ECS',
        'AWS::ECS::TaskDefinition': 'ECS',
        'AWS::EKS::Cluster': 'EKS',
        'AWS::EKS::Nodegroup': 'EKS',
        'AWS::Batch::ComputeEnvironment': 'Batch',
        'AWS::AppRunner::Service': 'App Runner',
        
        # Networking
        'AWS::EC2::VPC': 'VPC',
        'AWS::EC2::Subnet': 'VPC',
        'AWS::EC2::RouteTable': 'VPC',
        'AWS::EC2::SecurityGroup': 'VPC',
        'AWS::EC2::VPCEndpoint': 'VPC Endpoint',
        'AWS::EC2::FlowLog': 'VPC Flow Logs',
        'AWS::ElasticLoadBalancingV2::LoadBalancer': 'ALB',
        'AWS::ElasticLoadBalancing::LoadBalancer': 'ELB',
        'AWS::CloudFront::Distribution': 'CloudFront',
        'AWS::CloudFront::KeyGroup': 'CloudFront',
        'AWS::CloudFront::PublicKey': 'CloudFront',
        'AWS::Route53::HostedZone': 'Route 53',
        'AWS::Route53::RecordSet': 'Route 53',
        'AWS::ApiGateway::RestApi': 'API Gateway',
        'AWS::ApiGatewayV2::Api': 'API Gateway',
        
        # Database
        'AWS::DynamoDB::Table': 'DynamoDB',
        'AWS::DynamoDB::GlobalTable': 'DynamoDB',
        'AWS::RDS::DBInstance': 'RDS',
        'AWS::RDS::DBCluster': 'RDS',
        'AWS::ElastiCache::CacheCluster': 'ElastiCache',
        'AWS::ElastiCache::ReplicationGroup': 'ElastiCache',
        'AWS::DocDB::DBCluster': 'DocumentDB',
        'AWS::Neptune::DBCluster': 'Neptune',
        'AWS::Redshift::Cluster': 'Redshift',
        
        # Storage
        'AWS::S3::Bucket': 'S3',
        'AWS::EFS::FileSystem': 'EFS',
        'AWS::FSx::FileSystem': 'FSx',
        
        # Security
        'AWS::IAM::Role': 'IAM',
        'AWS::IAM::Policy': 'IAM',
        'AWS::IAM::User': 'IAM',
        'AWS::KMS::Key': 'KMS',
        'AWS::KMS::Alias': 'KMS',
        'AWS::SecretsManager::Secret': 'Secrets Manager',
        'AWS::Cognito::UserPool': 'Cognito',
        'AWS::Cognito::IdentityPool': 'Cognito',
        'AWS::WAFv2::WebACL': 'WAF',
        'AWS::WAF::WebACL': 'WAF',
        'AWS::Shield::Protection': 'Shield',
        'AWS::CertificateManager::Certificate': 'Certificate Manager',
        'AWS::GuardDuty::Detector': 'GuardDuty',
        'AWS::Macie::Session': 'Macie',
        
        # AI/ML
        'AWS::Bedrock::Guardrail': 'Bedrock Guardrails',
        'AWS::Bedrock::Agent': 'Bedrock',
        'AWS::Bedrock::KnowledgeBase': 'Bedrock',
        'AWS::SageMaker::Model': 'SageMaker',
        'AWS::SageMaker::Endpoint': 'SageMaker',
        
        # Integration
        'AWS::SNS::Topic': 'SNS',
        'AWS::SNS::Subscription': 'SNS',
        'AWS::SQS::Queue': 'SQS',
        'AWS::Events::Rule': 'EventBridge',
        'AWS::Events::EventBus': 'EventBridge',
        'AWS::StepFunctions::StateMachine': 'Step Functions',
        'AWS::Kinesis::Stream': 'Kinesis',
        'AWS::KinesisFirehose::DeliveryStream': 'Kinesis Firehose',
        
        # Monitoring
        'AWS::CloudWatch::Alarm': 'CloudWatch',
        'AWS::CloudWatch::Dashboard': 'CloudWatch',
        'AWS::Logs::LogGroup': 'CloudWatch Logs',
        'AWS::CloudTrail::Trail': 'CloudTrail',
        'AWS::XRay::Group': 'X-Ray',
        'AWS::Config::ConfigRule': 'Config',
        
        # Deployment
        'AWS::CloudFormation::Stack': 'CloudFormation',
        'AWS::CodePipeline::Pipeline': 'CodePipeline',
        'AWS::CodeBuild::Project': 'CodeBuild',
        'AWS::CodeDeploy::Application': 'CodeDeploy',
        
        # Other
        'AWS::SSM::Parameter': 'Systems Manager',
        'AWS::SSM::Document': 'Systems Manager',
    }

    # Terraform resource type to service name mapping
    TF_SERVICE_MAP: Dict[str, str] = {
        # Compute
        'aws_instance': 'EC2',
        'aws_launch_template': 'EC2',
        'aws_autoscaling_group': 'Auto Scaling',
        'aws_lambda_function': 'Lambda',
        'aws_ecs_cluster': 'ECS',
        'aws_ecs_service': 'ECS',
        'aws_ecs_task_definition': 'ECS',
        'aws_eks_cluster': 'EKS',
        'aws_eks_node_group': 'EKS',
        'aws_batch_compute_environment': 'Batch',
        'aws_apprunner_service': 'App Runner',
        
        # Networking
        'aws_vpc': 'VPC',
        'aws_subnet': 'VPC',
        'aws_route_table': 'VPC',
        'aws_security_group': 'VPC',
        'aws_vpc_endpoint': 'VPC Endpoint',
        'aws_flow_log': 'VPC Flow Logs',
        'aws_lb': 'ALB',
        'aws_alb': 'ALB',
        'aws_elb': 'ELB',
        'aws_cloudfront_distribution': 'CloudFront',
        'aws_route53_zone': 'Route 53',
        'aws_route53_record': 'Route 53',
        'aws_api_gateway_rest_api': 'API Gateway',
        'aws_apigatewayv2_api': 'API Gateway',
        
        # Database
        'aws_dynamodb_table': 'DynamoDB',
        'aws_dynamodb_global_table': 'DynamoDB',
        'aws_db_instance': 'RDS',
        'aws_rds_cluster': 'RDS',
        'aws_elasticache_cluster': 'ElastiCache',
        'aws_elasticache_replication_group': 'ElastiCache',
        'aws_docdb_cluster': 'DocumentDB',
        'aws_neptune_cluster': 'Neptune',
        'aws_redshift_cluster': 'Redshift',
        
        # Storage
        'aws_s3_bucket': 'S3',
        'aws_efs_file_system': 'EFS',
        'aws_fsx_lustre_file_system': 'FSx',
        
        # Security
        'aws_iam_role': 'IAM',
        'aws_iam_policy': 'IAM',
        'aws_iam_user': 'IAM',
        'aws_kms_key': 'KMS',
        'aws_kms_alias': 'KMS',
        'aws_secretsmanager_secret': 'Secrets Manager',
        'aws_cognito_user_pool': 'Cognito',
        'aws_cognito_identity_pool': 'Cognito',
        'aws_wafv2_web_acl': 'WAF',
        'aws_waf_web_acl': 'WAF',
        'aws_shield_protection': 'Shield',
        'aws_acm_certificate': 'Certificate Manager',
        'aws_guardduty_detector': 'GuardDuty',
        
        # AI/ML
        'aws_bedrock_guardrail': 'Bedrock Guardrails',
        'aws_sagemaker_model': 'SageMaker',
        'aws_sagemaker_endpoint': 'SageMaker',
        
        # Integration
        'aws_sns_topic': 'SNS',
        'aws_sns_topic_subscription': 'SNS',
        'aws_sqs_queue': 'SQS',
        'aws_cloudwatch_event_rule': 'EventBridge',
        'aws_sfn_state_machine': 'Step Functions',
        'aws_kinesis_stream': 'Kinesis',
        'aws_kinesis_firehose_delivery_stream': 'Kinesis Firehose',
        
        # Monitoring
        'aws_cloudwatch_metric_alarm': 'CloudWatch',
        'aws_cloudwatch_dashboard': 'CloudWatch',
        'aws_cloudwatch_log_group': 'CloudWatch Logs',
        'aws_cloudtrail': 'CloudTrail',
        
        # Deployment
        'aws_codepipeline': 'CodePipeline',
        'aws_codebuild_project': 'CodeBuild',
        'aws_codedeploy_app': 'CodeDeploy',
        
        # Other
        'aws_ssm_parameter': 'Systems Manager',
    }
    
    def __init__(self):
        """Initialize the IaC evidence extractor."""
        self.logger = WAFRLogger(__name__)

    def extract_from_document(self, document_text: str) -> IaCExtractionResult:
        """
        Extract AWS services and configurations from IaC document.
        
        Args:
            document_text: Raw IaC template content
            
        Returns:
            IaCExtractionResult with all extracted information
        """
        iac_type = self._detect_iac_type(document_text)
        
        self.logger.info(f"Extracting from {iac_type.value} template")
        
        if iac_type == IaCType.CLOUDFORMATION:
            return self._extract_cloudformation(document_text)
        elif iac_type == IaCType.TERRAFORM:
            return self._extract_terraform(document_text)
        else:
            return self._create_empty_result(iac_type)
    
    def _detect_iac_type(self, text: str) -> IaCType:
        """Detect the type of IaC template."""
        # CloudFormation detection
        if 'AWSTemplateFormatVersion' in text:
            return IaCType.CLOUDFORMATION
        if 'Transform: AWS::Serverless' in text:
            return IaCType.SAM
        if '"Type": "AWS::' in text or 'Type: AWS::' in text:
            return IaCType.CLOUDFORMATION
        
        # Terraform detection
        if 'resource "aws_' in text:
            return IaCType.TERRAFORM
        if 'provider "aws"' in text:
            return IaCType.TERRAFORM
        if 'terraform {' in text:
            return IaCType.TERRAFORM
        
        return IaCType.UNKNOWN
    
    def _extract_cloudformation(self, text: str) -> IaCExtractionResult:
        """Extract resources from CloudFormation template."""
        resources = []
        services = set()
        security_features = {}
        reliability_features = {}
        sustainability_features = {}
        
        try:
            # Try to parse as YAML first, then JSON
            try:
                template = yaml.safe_load(text)
            except:
                template = json.loads(text)
            
            if not template or 'Resources' not in template:
                return self._create_empty_result(IaCType.CLOUDFORMATION)
            
            # Extract each resource
            for resource_name, resource_def in template.get('Resources', {}).items():
                resource_type = resource_def.get('Type', '')
                properties = resource_def.get('Properties', {})
                
                # Map to service name
                service_name = self._map_cfn_to_service(resource_type)
                if service_name:
                    services.add(service_name)
                    
                    extracted = ExtractedResource(
                        resource_type=resource_type,
                        resource_name=resource_name,
                        service_name=service_name,
                        properties=properties
                    )
                    
                    # Extract configurations
                    self._extract_cfn_security_config(extracted, properties)
                    self._extract_cfn_reliability_config(extracted, properties)
                    self._extract_cfn_sustainability_config(extracted, properties, text)
                    
                    resources.append(extracted)
            
            # Aggregate features
            security_features = self._aggregate_security_features(resources, text)
            reliability_features = self._aggregate_reliability_features(resources, text)
            sustainability_features = self._aggregate_sustainability_features(resources, text)
            
        except Exception as e:
            self.logger.error(f"Error parsing CloudFormation: {e}")
            # Fall back to regex-based extraction
            return self._extract_cfn_regex(text)
        
        return IaCExtractionResult(
            iac_type=IaCType.CLOUDFORMATION,
            resources=resources,
            services=services,
            security_features=security_features,
            reliability_features=reliability_features,
            sustainability_features=sustainability_features,
            architecture_patterns=self._detect_patterns(services, resources),
            extraction_metadata={
                'resource_count': len(resources),
                'service_count': len(services),
                'extraction_method': 'yaml_parse'
            }
        )

    def _extract_terraform(self, text: str) -> IaCExtractionResult:
        """Extract resources from Terraform template using regex."""
        resources = []
        services = set()
        
        # Regex to match Terraform resource blocks
        resource_pattern = r'resource\s+"(aws_[^"]+)"\s+"([^"]+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(resource_pattern, text, re.DOTALL):
            resource_type = match.group(1)
            resource_name = match.group(2)
            resource_body = match.group(3)
            
            service_name = self._map_tf_to_service(resource_type)
            if service_name:
                services.add(service_name)
                
                # Parse properties from resource body
                properties = self._parse_tf_properties(resource_body)
                
                extracted = ExtractedResource(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    service_name=service_name,
                    properties=properties
                )
                
                resources.append(extracted)
        
        security_features = self._aggregate_security_features(resources, text)
        reliability_features = self._aggregate_reliability_features(resources, text)
        sustainability_features = self._aggregate_sustainability_features(resources, text)

        return IaCExtractionResult(
            iac_type=IaCType.TERRAFORM,
            resources=resources,
            services=services,
            security_features=security_features,
            reliability_features=reliability_features,
            sustainability_features=sustainability_features,
            architecture_patterns=self._detect_patterns(services, resources),
            extraction_metadata={
                'resource_count': len(resources),
                'service_count': len(services),
                'extraction_method': 'regex_parse'
            }
        )
    
    def _extract_cfn_regex(self, text: str) -> IaCExtractionResult:
        """Fallback regex-based extraction for CloudFormation."""
        resources = []
        services = set()
        
        # Find all AWS:: resource types
        type_pattern = r'Type:\s*["\']?(AWS::[^"\'\s]+)["\']?'
        for match in re.finditer(type_pattern, text):
            resource_type = match.group(1)
            service_name = self._map_cfn_to_service(resource_type)
            if service_name:
                services.add(service_name)
                resources.append(ExtractedResource(
                    resource_type=resource_type,
                    resource_name='unknown',
                    service_name=service_name,
                    properties={}
                ))
        
        return IaCExtractionResult(
            iac_type=IaCType.CLOUDFORMATION,
            resources=resources,
            services=services,
            security_features=self._aggregate_security_features(resources, text),
            reliability_features=self._aggregate_reliability_features(resources),
            sustainability_features=self._aggregate_sustainability_features(resources, text),
            architecture_patterns=self._detect_patterns(services, resources),
            extraction_metadata={
                'resource_count': len(resources),
                'service_count': len(services),
                'extraction_method': 'regex_fallback'
            }
        )
    
    def _map_cfn_to_service(self, resource_type: str) -> Optional[str]:
        """Map CloudFormation resource type to service name."""
        # Direct mapping
        if resource_type in self.CFN_SERVICE_MAP:
            return self.CFN_SERVICE_MAP[resource_type]
        
        # Prefix matching for services with many resource types
        for cfn_type, service in self.CFN_SERVICE_MAP.items():
            if resource_type.startswith(cfn_type.rsplit('::', 1)[0] + '::'):
                return service
        
        return None
    
    def _map_tf_to_service(self, resource_type: str) -> Optional[str]:
        """Map Terraform resource type to service name."""
        if resource_type in self.TF_SERVICE_MAP:
            return self.TF_SERVICE_MAP[resource_type]
        
        # Prefix matching
        for tf_type, service in self.TF_SERVICE_MAP.items():
            if resource_type.startswith(tf_type.rsplit('_', 1)[0] + '_'):
                return service
        
        return None
    
    def _parse_tf_properties(self, body: str) -> Dict[str, Any]:
        """Parse Terraform resource body into properties dict."""
        properties = {}
        # Simple key = value parsing
        prop_pattern = r'(\w+)\s*=\s*"?([^"\n]+)"?'
        for match in re.finditer(prop_pattern, body):
            properties[match.group(1)] = match.group(2).strip()
        return properties

    def _extract_cfn_security_config(self, resource: ExtractedResource, props: Dict):
        """Extract security configurations from CloudFormation resource."""
        configs = {}
        
        # KMS encryption
        if 'KmsKeyId' in props or 'KMSMasterKeyId' in props:
            configs['encryption'] = 'kms'
        if 'SSESpecification' in props:
            configs['sse_enabled'] = props['SSESpecification'].get('SSEEnabled', False)
        
        # Bedrock Guardrails
        if 'ContentPolicyConfig' in props:
            configs['content_policy'] = True
            configs['content_filters'] = props.get('ContentPolicyConfig', {})
        if 'SensitiveInformationPolicyConfig' in props:
            configs['pii_protection'] = True
            configs['pii_config'] = props.get('SensitiveInformationPolicyConfig', {})
        
        # WAF configurations
        if 'Rules' in props and resource.service_name == 'WAF':
            configs['waf_rules'] = len(props.get('Rules', []))
        
        # Cognito advanced security
        if 'UserPoolAddOns' in props:
            addons = props.get('UserPoolAddOns', {})
            if addons.get('AdvancedSecurityMode') == 'ENFORCED':
                configs['advanced_security'] = True
        
        resource.security_configs = configs
    
    def _extract_cfn_reliability_config(self, resource: ExtractedResource, props: Dict):
        """Extract reliability configurations from CloudFormation resource."""
        configs = {}
        
        # Multi-AZ
        if props.get('MultiAZ') or props.get('MultiAZEnabled'):
            configs['multi_az'] = True
        if 'AvailabilityZones' in props:
            configs['availability_zones'] = len(props.get('AvailabilityZones', []))
        
        # Point-in-Time Recovery (DynamoDB)
        if 'PointInTimeRecoverySpecification' in props:
            pitr = props.get('PointInTimeRecoverySpecification', {})
            configs['pitr_enabled'] = pitr.get('PointInTimeRecoveryEnabled', False)
        
        # Automatic failover (ElastiCache)
        if props.get('AutomaticFailoverEnabled'):
            configs['automatic_failover'] = True
        
        # Backup retention
        if 'BackupRetentionPeriod' in props:
            configs['backup_retention_days'] = props.get('BackupRetentionPeriod')
        
        resource.reliability_configs = configs
    
    def _extract_cfn_sustainability_config(self, resource: ExtractedResource, props: Dict, text: str):
        """Extract sustainability configurations from CloudFormation resource."""
        configs = {}
        
        # Graviton/ARM instances
        instance_type = props.get('InstanceType', '')
        if any(g in instance_type.lower() for g in ['m7g', 'c7g', 'r7g', 't4g', 'm6g', 'c6g']):
            configs['graviton'] = True
            configs['instance_type'] = instance_type
        
        # S3 Lifecycle
        if 'LifecycleConfiguration' in props:
            configs['lifecycle_rules'] = True
            rules = props.get('LifecycleConfiguration', {}).get('Rules', [])
            configs['lifecycle_rule_count'] = len(rules)
        
        resource.sustainability_configs = configs
    
    def _aggregate_security_features(self, resources: List[ExtractedResource], text: str) -> Dict:
        """Aggregate security features from all resources and text patterns."""
        features = {
            'bedrock_guardrails': False,
            'pii_protection': False,
            'waf_enabled': False,
            'waf_rule_count': 0,
            'vpc_endpoints': False,
            'vpc_flow_logs': False,
            'kms_encryption': False,
            'cognito_advanced_security': False,
            'cloudfront_signed_urls': False,
            'secrets_manager': False,
            'certificate_manager': False,
            'guardduty': False,
            'security_groups': False
        }

        # Check resources for service-based features
        for r in resources:
            if r.service_name == 'Bedrock Guardrails':
                features['bedrock_guardrails'] = True
            if r.security_configs.get('pii_protection'):
                features['pii_protection'] = True
            if r.service_name == 'WAF':
                features['waf_enabled'] = True
                features['waf_rule_count'] += r.security_configs.get('waf_rules', 0)
            if r.service_name == 'VPC Endpoint':
                features['vpc_endpoints'] = True
            if r.service_name == 'VPC Flow Logs':
                features['vpc_flow_logs'] = True
            if r.security_configs.get('encryption') == 'kms':
                features['kms_encryption'] = True
            if r.security_configs.get('advanced_security'):
                features['cognito_advanced_security'] = True
            if r.service_name == 'Secrets Manager':
                features['secrets_manager'] = True
            if r.service_name == 'Certificate Manager':
                features['certificate_manager'] = True
            if r.service_name == 'GuardDuty':
                features['guardduty'] = True
            if r.resource_type in ['AWS::EC2::SecurityGroup', 'aws_security_group']:
                features['security_groups'] = True

        # TEXT-BASED PATTERN DETECTION (Issue 1 Fix)
        # Detect features from CloudFormation/Terraform text patterns
        text_lower = text.lower()

        # KMS encryption detection - check for KMS key references in properties
        kms_patterns = [
            'kmskeyid', 'kms_key_id', 'kmsmasterkeyid', 'kms_master_key_id',
            'ssespecification', 'sse_specification', 'serversideencryption',
            'aws::kms::key', 'aws_kms_key', 'encryptionconfiguration',
            'kmsencrypted', 'kms_encrypted', 'kmskeyarn', 'kms_key_arn'
        ]
        if any(pattern in text_lower for pattern in kms_patterns):
            features['kms_encryption'] = True

        # VPC Endpoints detection - check for endpoint configurations
        vpc_endpoint_patterns = [
            'aws::ec2::vpcendpoint', 'aws_vpc_endpoint', 'vpcendpointtype',
            'vpc_endpoint_type', 'privatelink', 'interfaceendpoint',
            'gatewayendpoint', 'servicename: com.amazonaws'
        ]
        if any(pattern in text_lower for pattern in vpc_endpoint_patterns):
            features['vpc_endpoints'] = True

        # VPC Flow Logs detection
        flow_log_patterns = [
            'aws::ec2::flowlog', 'aws_flow_log', 'flowlogid', 'flow_log_id',
            'traffictype', 'traffic_type', 'logdestination', 'log_destination'
        ]
        if any(pattern in text_lower for pattern in flow_log_patterns):
            features['vpc_flow_logs'] = True

        # Bedrock Guardrails detection - check for guardrail configurations
        guardrail_patterns = [
            'aws::bedrock::guardrail', 'aws_bedrock_guardrail',
            'contentpolicyconfig', 'content_policy_config',
            'sensitiveinformationpolicyconfig', 'sensitive_information_policy',
            'topicpolicyconfig', 'topic_policy_config', 'wordpolicyconfig',
            'guardrailidentifier', 'guardrail_identifier'
        ]
        if any(pattern in text_lower for pattern in guardrail_patterns):
            features['bedrock_guardrails'] = True

        # WAF detection from text
        waf_patterns = [
            'aws::wafv2::webacl', 'aws_wafv2_web_acl', 'aws::waf::webacl',
            'webacl', 'web_acl', 'wafregional', 'waf_regional'
        ]
        if any(pattern in text_lower for pattern in waf_patterns):
            features['waf_enabled'] = True

        # Cognito Advanced Security detection
        cognito_security_patterns = [
            'advancedsecuritymode', 'advanced_security_mode', 'enforced',
            'userpooladdons', 'user_pool_add_ons', 'mfaconfiguration'
        ]
        if any(pattern in text_lower for pattern in cognito_security_patterns):
            features['cognito_advanced_security'] = True

        # CloudFront signed URLs detection
        if 'KeyGroup' in text or 'PublicKey' in text or 'key_group' in text_lower:
            features['cloudfront_signed_urls'] = True

        # Secrets Manager detection
        secrets_patterns = [
            'aws::secretsmanager::secret', 'aws_secretsmanager_secret',
            'secretstring', 'secret_string', 'secretarn', 'secret_arn'
        ]
        if any(pattern in text_lower for pattern in secrets_patterns):
            features['secrets_manager'] = True

        # Certificate Manager detection
        cert_patterns = [
            'aws::certificatemanager::certificate', 'aws_acm_certificate',
            'certificatearn', 'certificate_arn', 'domainvalidationoptions'
        ]
        if any(pattern in text_lower for pattern in cert_patterns):
            features['certificate_manager'] = True

        # GuardDuty detection
        guardduty_patterns = [
            'aws::guardduty::detector', 'aws_guardduty_detector',
            'guardduty', 'guard_duty', 'threatintelset'
        ]
        if any(pattern in text_lower for pattern in guardduty_patterns):
            features['guardduty'] = True

        return features
    
    def _aggregate_reliability_features(self, resources: List[ExtractedResource], text: str = "") -> Dict:
        """Aggregate reliability features from all resources and text patterns."""
        features = {
            'multi_az_enabled': False,
            'pitr_enabled': False,
            'automatic_failover': False,
            'backup_configured': False,
            'auto_scaling': False,
            'health_checks': False,
            'cross_region_replication': False
        }

        # Check resources for reliability configs
        for r in resources:
            if r.reliability_configs.get('multi_az'):
                features['multi_az_enabled'] = True
            if r.reliability_configs.get('pitr_enabled'):
                features['pitr_enabled'] = True
            if r.reliability_configs.get('automatic_failover'):
                features['automatic_failover'] = True
            if r.reliability_configs.get('backup_retention_days'):
                features['backup_configured'] = True
            if r.service_name == 'Auto Scaling':
                features['auto_scaling'] = True

        # TEXT-BASED PATTERN DETECTION (Issue 1 Fix - Reliability)
        text_lower = text.lower() if text else ""

        # Multi-AZ detection from text patterns
        multi_az_patterns = [
            'multiaz', 'multi_az', 'multi-az', 'availabilityzones',
            'availability_zones', 'multiazdeployment', 'multi_az_deployment',
            'crosszone', 'cross_zone', 'azmode', 'az_mode'
        ]
        if any(pattern in text_lower for pattern in multi_az_patterns):
            features['multi_az_enabled'] = True

        # Point-in-Time Recovery detection
        pitr_patterns = [
            'pointintimerecovery', 'point_in_time_recovery', 'pitr',
            'pointintimerecoveryenabled', 'point_in_time_recovery_enabled'
        ]
        if any(pattern in text_lower for pattern in pitr_patterns):
            features['pitr_enabled'] = True

        # Automatic failover detection
        failover_patterns = [
            'automaticfailover', 'automatic_failover', 'failoverenabled',
            'failover_enabled', 'autofailover', 'auto_failover'
        ]
        if any(pattern in text_lower for pattern in failover_patterns):
            features['automatic_failover'] = True

        # Backup configuration detection
        backup_patterns = [
            'backupretentionperiod', 'backup_retention_period',
            'backupretentiondays', 'backup_retention_days',
            'backupconfiguration', 'backup_configuration',
            'automatedbackups', 'automated_backups'
        ]
        if any(pattern in text_lower for pattern in backup_patterns):
            features['backup_configured'] = True

        # Auto Scaling detection
        autoscaling_patterns = [
            'aws::autoscaling', 'aws_autoscaling', 'scalingpolicy',
            'scaling_policy', 'targettrackingscaling', 'target_tracking',
            'minsize', 'min_size', 'maxsize', 'max_size', 'desiredcapacity'
        ]
        if any(pattern in text_lower for pattern in autoscaling_patterns):
            features['auto_scaling'] = True

        # Health checks detection
        health_patterns = [
            'healthcheck', 'health_check', 'healthcheckpath',
            'health_check_path', 'healthcheckinterval', 'targethealth'
        ]
        if any(pattern in text_lower for pattern in health_patterns):
            features['health_checks'] = True

        # Cross-region replication detection
        replication_patterns = [
            'replicationconfiguration', 'replication_configuration',
            'crossregionreplication', 'cross_region_replication',
            'replicaregion', 'replica_region', 'globalcluster'
        ]
        if any(pattern in text_lower for pattern in replication_patterns):
            features['cross_region_replication'] = True

        return features
    
    def _aggregate_sustainability_features(self, resources: List[ExtractedResource], text: str) -> Dict:
        """Aggregate sustainability features from all resources."""
        features = {
            'graviton_instances': False,
            'graviton_types': [],
            's3_lifecycle': False,
            'auto_scaling': False
        }
        
        for r in resources:
            if r.sustainability_configs.get('graviton'):
                features['graviton_instances'] = True
                features['graviton_types'].append(r.sustainability_configs.get('instance_type'))
            if r.sustainability_configs.get('lifecycle_rules'):
                features['s3_lifecycle'] = True
            if r.service_name == 'Auto Scaling':
                features['auto_scaling'] = True
        
        return features

    def _detect_patterns(self, services: Set[str], resources: List[ExtractedResource]) -> List[str]:
        """Detect architecture patterns based on services present."""
        patterns = []
        
        # Multi-Tier (requires presentation + logic + data layers)
        has_presentation = any(s in services for s in ['CloudFront', 'ALB', 'ELB', 'S3'])
        has_logic = any(s in services for s in ['EC2', 'ECS', 'Lambda', 'EKS'])
        has_data = any(s in services for s in ['RDS', 'DynamoDB', 'ElastiCache', 'Aurora'])
        if has_presentation and has_logic and has_data:
            patterns.append('Multi-Tier Architecture')
        
        # Serverless (requires Lambda or Fargate)
        if 'Lambda' in services:
            patterns.append('Serverless')
        
        # Microservices (requires multiple compute services or ECS/EKS)
        if 'ECS' in services or 'EKS' in services:
            patterns.append('Microservices')
        
        # Event-Driven (requires event services)
        event_services = {'SNS', 'SQS', 'EventBridge', 'Kinesis'}
        if services & event_services:
            patterns.append('Event-Driven')
        
        # Infrastructure as Code (always true for IaC templates)
        patterns.append('Infrastructure as Code')
        
        # Multi-AZ (check reliability configs)
        if any(r.reliability_configs.get('multi_az') for r in resources):
            patterns.append('Multi-AZ Deployment')
        
        # Auto Scaling
        if 'Auto Scaling' in services:
            patterns.append('Auto Scaling')
        
        # Content Delivery
        if 'CloudFront' in services:
            patterns.append('Content Delivery Network')
        
        return patterns
    
    def _create_empty_result(self, iac_type: IaCType) -> IaCExtractionResult:
        """Create empty result for unknown or unparseable templates."""
        return IaCExtractionResult(
            iac_type=iac_type,
            resources=[],
            services=set(),
            security_features={},
            reliability_features={},
            sustainability_features={},
            architecture_patterns=[],
            extraction_metadata={
                'resource_count': 0,
                'service_count': 0,
                'extraction_method': 'none'
            }
        )
    
    def merge_with_claude_analysis(
        self,
        iac_result: IaCExtractionResult,
        claude_services: List[str]
    ) -> Dict[str, Any]:
        """
        Merge IaC extraction with Claude analysis.
        
        IaC extraction takes precedence for service identification.
        Claude analysis is used for diagram interpretation and text analysis.
        
        Implements UNIV-004: Multi-Source Reconciliation
        """
        merged = {
            'confirmed_services': list(iac_result.services),
            'claude_only_services': [],
            'rejected_services': [],
            'reconciliation_notes': []
        }
        
        # Check each Claude-identified service
        for service in claude_services:
            if service in iac_result.services:
                # Confirmed by both sources
                merged['reconciliation_notes'].append(
                    f"✅ {service}: Confirmed by IaC and Claude"
                )
            elif service in ['Lambda', 'API Gateway', 'SNS', 'SQS', 'CDK']:
                # Common false positive - reject unless in IaC
                merged['rejected_services'].append(service)
                merged['reconciliation_notes'].append(
                    f"❌ {service}: Rejected (no IaC evidence, common false positive)"
                )
            else:
                # Claude-only - might be from diagram
                merged['claude_only_services'].append(service)
                merged['reconciliation_notes'].append(
                    f"⚠️ {service}: Claude-only (verify in diagram)"
                )
        
        return merged


# Global instance for easy access
iac_evidence_extractor = IaCEvidenceExtractor()
