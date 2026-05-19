"""
Evidence Validator for WAFR Assessment - Phase 2 Implementation.

This module validates Claude's service identifications against actual evidence
in CloudFormation and Terraform templates to eliminate false positives.

Implements UNIV-001: Evidence-Based Identification from the Universal Validation Framework.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.logger import WAFRLogger


class EvidenceType(str, Enum):
    """Types of evidence for service identification."""
    CFN_RESOURCE = "cfn_resource"
    TERRAFORM_RESOURCE = "terraform_resource"
    TEXT_MENTION = "text_mention"
    DIAGRAM_ICON = "diagram_icon"
    NO_EVIDENCE = "no_evidence"


class ConfidenceLevel(str, Enum):
    """Confidence levels for service identification."""
    HIGH = "high"      # Explicit resource type found
    MEDIUM = "medium"  # Clear text mention
    LOW = "low"        # Visual/inferred only
    NONE = "none"      # No evidence found


@dataclass
class ServiceEvidence:
    """Evidence for a service identification."""
    service_name: str
    evidence_type: EvidenceType
    evidence_details: str
    confidence: ConfidenceLevel
    resource_types: List[str] = field(default_factory=list)
    configurations: Dict[str, any] = field(default_factory=dict)
    is_valid: bool = True


@dataclass
class ValidationResult:
    """Result of validating identified services."""
    validated_services: List[ServiceEvidence]
    rejected_services: List[ServiceEvidence]
    potential_services: List[ServiceEvidence]
    security_features: Dict[str, any]
    sustainability_features: Dict[str, any]
    reliability_features: Dict[str, any]
    validation_summary: Dict[str, any]


class EvidenceValidator:
    """
    Validates Claude's service identifications against actual evidence.
    
    This class implements UNIV-001 (Evidence-Based Identification) by:
    1. Mapping services to their CloudFormation and Terraform resource types
    2. Scanning document text for explicit resource definitions
    3. Rejecting services without supporting evidence
    4. Extracting configuration details for validated services
    """
    
    # CloudFormation resource type patterns for each AWS service
    CFN_RESOURCE_PATTERNS: Dict[str, List[str]] = {
        # Compute
        'EC2': ['AWS::EC2::Instance', 'AWS::EC2::LaunchTemplate', 'AWS::AutoScaling::'],
        'Lambda': ['AWS::Lambda::Function', 'AWS::Serverless::Function', 'AWS::Lambda::'],
        'ECS': ['AWS::ECS::Cluster', 'AWS::ECS::Service', 'AWS::ECS::TaskDefinition'],
        'EKS': ['AWS::EKS::Cluster', 'AWS::EKS::Nodegroup'],
        'Fargate': ['AWS::ECS::Service'],  # Fargate is detected via LaunchType
        'Batch': ['AWS::Batch::'],
        'App Runner': ['AWS::AppRunner::'],
        
        # Networking
        'VPC': ['AWS::EC2::VPC', 'AWS::EC2::Subnet', 'AWS::EC2::RouteTable'],
        'ALB': ['AWS::ElasticLoadBalancingV2::LoadBalancer'],
        'ELB': ['AWS::ElasticLoadBalancing::LoadBalancer', 'AWS::ElasticLoadBalancingV2::'],
        'NLB': ['AWS::ElasticLoadBalancingV2::LoadBalancer'],
        'CloudFront': ['AWS::CloudFront::Distribution', 'AWS::CloudFront::'],
        'Route 53': ['AWS::Route53::HostedZone', 'AWS::Route53::RecordSet'],
        'API Gateway': ['AWS::ApiGateway::', 'AWS::ApiGatewayV2::'],
        'VPC Endpoint': ['AWS::EC2::VPCEndpoint'],
        
        # Database
        'DynamoDB': ['AWS::DynamoDB::Table', 'AWS::DynamoDB::GlobalTable'],
        'RDS': ['AWS::RDS::DBInstance', 'AWS::RDS::DBCluster'],
        'Aurora': ['AWS::RDS::DBCluster'],
        'ElastiCache': ['AWS::ElastiCache::CacheCluster', 'AWS::ElastiCache::ReplicationGroup'],
        'DocumentDB': ['AWS::DocDB::'],
        'Neptune': ['AWS::Neptune::'],
        'Redshift': ['AWS::Redshift::'],
        
        # Storage
        'S3': ['AWS::S3::Bucket'],
        'EFS': ['AWS::EFS::FileSystem'],
        'FSx': ['AWS::FSx::'],
        
        # Security
        'IAM': ['AWS::IAM::Role', 'AWS::IAM::Policy', 'AWS::IAM::User'],
        'KMS': ['AWS::KMS::Key', 'AWS::KMS::Alias'],
        'Secrets Manager': ['AWS::SecretsManager::Secret'],
        'Cognito': ['AWS::Cognito::UserPool', 'AWS::Cognito::IdentityPool'],
        'WAF': ['AWS::WAFv2::WebACL', 'AWS::WAF::WebACL', 'AWS::WAFv2::'],
        'Shield': ['AWS::Shield::'],
        'Certificate Manager': ['AWS::CertificateManager::Certificate'],
        'GuardDuty': ['AWS::GuardDuty::'],
        'Macie': ['AWS::Macie::'],
        'Inspector': ['AWS::Inspector::'],
        
        # AI/ML
        'Bedrock': ['AWS::Bedrock::', 'bedrock:'],
        'SageMaker': ['AWS::SageMaker::'],
        
        # Integration
        'SNS': ['AWS::SNS::Topic', 'AWS::SNS::Subscription'],
        'SQS': ['AWS::SQS::Queue'],
        'EventBridge': ['AWS::Events::Rule', 'AWS::Events::EventBus'],
        'Step Functions': ['AWS::StepFunctions::StateMachine'],
        'Kinesis': ['AWS::Kinesis::Stream', 'AWS::KinesisFirehose::'],
        
        # Monitoring
        'CloudWatch': ['AWS::CloudWatch::', 'AWS::Logs::LogGroup'],
        'CloudTrail': ['AWS::CloudTrail::Trail'],
        'X-Ray': ['AWS::XRay::'],
        'Config': ['AWS::Config::'],
        
        # Deployment
        'CloudFormation': ['AWS::CloudFormation::'],
        'CodePipeline': ['AWS::CodePipeline::'],
        'CodeBuild': ['AWS::CodeBuild::'],
        'CodeDeploy': ['AWS::CodeDeploy::'],
        
        # Other
        'Systems Manager': ['AWS::SSM::', 'AWS::SystemsManager::'],
    }

    # Terraform resource type patterns for each AWS service
    TERRAFORM_RESOURCE_PATTERNS: Dict[str, List[str]] = {
        # Compute
        'EC2': ['aws_instance', 'aws_launch_template', 'aws_autoscaling_group'],
        'Lambda': ['aws_lambda_function', 'aws_lambda_'],
        'ECS': ['aws_ecs_cluster', 'aws_ecs_service', 'aws_ecs_task_definition'],
        'EKS': ['aws_eks_cluster', 'aws_eks_node_group'],
        'Batch': ['aws_batch_'],
        'App Runner': ['aws_apprunner_'],
        
        # Networking
        'VPC': ['aws_vpc', 'aws_subnet', 'aws_route_table'],
        'ALB': ['aws_lb', 'aws_alb'],
        'ELB': ['aws_elb', 'aws_lb'],
        'NLB': ['aws_lb'],
        'CloudFront': ['aws_cloudfront_distribution', 'aws_cloudfront_'],
        'Route 53': ['aws_route53_zone', 'aws_route53_record'],
        'API Gateway': ['aws_api_gateway_', 'aws_apigatewayv2_'],
        'VPC Endpoint': ['aws_vpc_endpoint'],
        
        # Database
        'DynamoDB': ['aws_dynamodb_table', 'aws_dynamodb_global_table'],
        'RDS': ['aws_db_instance', 'aws_rds_cluster'],
        'Aurora': ['aws_rds_cluster'],
        'ElastiCache': ['aws_elasticache_cluster', 'aws_elasticache_replication_group'],
        'DocumentDB': ['aws_docdb_'],
        'Neptune': ['aws_neptune_'],
        'Redshift': ['aws_redshift_'],
        
        # Storage
        'S3': ['aws_s3_bucket'],
        'EFS': ['aws_efs_file_system'],
        'FSx': ['aws_fsx_'],
        
        # Security
        'IAM': ['aws_iam_role', 'aws_iam_policy', 'aws_iam_user'],
        'KMS': ['aws_kms_key', 'aws_kms_alias'],
        'Secrets Manager': ['aws_secretsmanager_secret'],
        'Cognito': ['aws_cognito_user_pool', 'aws_cognito_identity_pool'],
        'WAF': ['aws_wafv2_web_acl', 'aws_waf_web_acl'],
        'Shield': ['aws_shield_'],
        'Certificate Manager': ['aws_acm_certificate'],
        'GuardDuty': ['aws_guardduty_'],
        'Macie': ['aws_macie_'],
        
        # AI/ML
        'Bedrock': ['aws_bedrock_'],
        'SageMaker': ['aws_sagemaker_'],
        
        # Integration
        'SNS': ['aws_sns_topic', 'aws_sns_topic_subscription'],
        'SQS': ['aws_sqs_queue'],
        'EventBridge': ['aws_cloudwatch_event_rule', 'aws_cloudwatch_event_bus'],
        'Step Functions': ['aws_sfn_state_machine'],
        'Kinesis': ['aws_kinesis_stream', 'aws_kinesis_firehose_'],
        
        # Monitoring
        'CloudWatch': ['aws_cloudwatch_', 'aws_cloudwatch_log_group'],
        'CloudTrail': ['aws_cloudtrail'],
        'X-Ray': ['aws_xray_'],
        'Config': ['aws_config_'],
        
        # Deployment
        'CodePipeline': ['aws_codepipeline'],
        'CodeBuild': ['aws_codebuild_'],
        'CodeDeploy': ['aws_codedeploy_'],
        
        # Other
        'Systems Manager': ['aws_ssm_', 'aws_ssm_parameter'],
    }
    
    # Services that are commonly false positives (claimed without evidence)
    COMMON_FALSE_POSITIVES = ['Lambda', 'API Gateway', 'SNS', 'SQS', 'CDK']
    
    def __init__(self):
        """Initialize the evidence validator."""
        self.logger = WAFRLogger(__name__)

    def validate_services(
        self,
        claimed_services: List[str],
        document_text: str
    ) -> ValidationResult:
        """
        Validate claimed services against document evidence.
        
        Args:
            claimed_services: List of service names claimed by Claude
            document_text: Raw document text (CloudFormation, Terraform, or other)
            
        Returns:
            ValidationResult with validated, rejected, and potential services
        """
        validated = []
        rejected = []
        potential = []
        
        # Detect document type
        is_cloudformation = self._is_cloudformation(document_text)
        is_terraform = self._is_terraform(document_text)
        
        self.logger.info(f"Validating {len(claimed_services)} services. "
                        f"CFN: {is_cloudformation}, TF: {is_terraform}")
        
        for service in claimed_services:
            evidence = self._find_service_evidence(service, document_text, 
                                                   is_cloudformation, is_terraform)
            
            if evidence.is_valid and evidence.confidence != ConfidenceLevel.NONE:
                validated.append(evidence)
                self.logger.debug(f"✅ Validated: {service} ({evidence.evidence_type.value})")
            elif service in self.COMMON_FALSE_POSITIVES:
                evidence.is_valid = False
                rejected.append(evidence)
                self.logger.warning(f"❌ Rejected (common false positive): {service}")
            else:
                evidence.is_valid = False
                potential.append(evidence)
                self.logger.debug(f"⚠️ Potential (no evidence): {service}")
        
        # Extract additional features
        security_features = self._extract_security_features(document_text)
        sustainability_features = self._extract_sustainability_features(document_text)
        reliability_features = self._extract_reliability_features(document_text)
        
        return ValidationResult(
            validated_services=validated,
            rejected_services=rejected,
            potential_services=potential,
            security_features=security_features,
            sustainability_features=sustainability_features,
            reliability_features=reliability_features,
            validation_summary={
                'total_claimed': len(claimed_services),
                'validated': len(validated),
                'rejected': len(rejected),
                'potential': len(potential),
                'accuracy_improvement': f"{len(rejected)} false positives eliminated"
            }
        )
    
    def _is_cloudformation(self, text: str) -> bool:
        """Check if document is CloudFormation template."""
        cfn_indicators = [
            'AWSTemplateFormatVersion',
            'AWS::',
            'Resources:',
            'Type: AWS::',
            '"Type": "AWS::'
        ]
        return any(indicator in text for indicator in cfn_indicators)
    
    def _is_terraform(self, text: str) -> bool:
        """Check if document is Terraform template."""
        tf_indicators = [
            'resource "aws_',
            'provider "aws"',
            'data "aws_',
            'module "',
            'terraform {'
        ]
        return any(indicator in text for indicator in tf_indicators)

    def _find_service_evidence(
        self,
        service_name: str,
        document_text: str,
        is_cloudformation: bool,
        is_terraform: bool
    ) -> ServiceEvidence:
        """Find evidence for a specific service in the document."""
        
        found_resources = []
        evidence_type = EvidenceType.NO_EVIDENCE
        confidence = ConfidenceLevel.NONE
        evidence_details = ""
        
        # Check CloudFormation patterns
        if is_cloudformation and service_name in self.CFN_RESOURCE_PATTERNS:
            for pattern in self.CFN_RESOURCE_PATTERNS[service_name]:
                if pattern in document_text:
                    found_resources.append(pattern)
                    evidence_type = EvidenceType.CFN_RESOURCE
                    confidence = ConfidenceLevel.HIGH
        
        # Check Terraform patterns
        if is_terraform and service_name in self.TERRAFORM_RESOURCE_PATTERNS:
            for pattern in self.TERRAFORM_RESOURCE_PATTERNS[service_name]:
                if pattern in document_text:
                    found_resources.append(pattern)
                    evidence_type = EvidenceType.TERRAFORM_RESOURCE
                    confidence = ConfidenceLevel.HIGH
        
        # If no IaC evidence, check for text mentions (lower confidence)
        if not found_resources:
            service_lower = service_name.lower()
            if service_lower in document_text.lower():
                evidence_type = EvidenceType.TEXT_MENTION
                confidence = ConfidenceLevel.MEDIUM
                evidence_details = f"Text mention of '{service_name}'"
        
        if found_resources:
            evidence_details = f"Found resources: {', '.join(found_resources)}"
        
        return ServiceEvidence(
            service_name=service_name,
            evidence_type=evidence_type,
            evidence_details=evidence_details,
            confidence=confidence,
            resource_types=found_resources,
            is_valid=confidence != ConfidenceLevel.NONE
        )
    
    def _extract_security_features(self, document_text: str) -> Dict[str, any]:
        """Extract specific security features from document."""
        features = {
            'bedrock_guardrails': False,
            'guardrail_details': {},
            'waf_rules': False,
            'waf_details': {},
            'vpc_endpoints': False,
            'vpc_endpoint_details': [],
            'vpc_flow_logs': False,
            'cognito_advanced_security': False,
            'cloudfront_signed_urls': False,
            'pii_protection': False,
            'encryption_at_rest': False,
            'encryption_in_transit': False
        }
        
        # Bedrock Guardrails detection
        guardrail_patterns = [
            'ContentPolicyConfig', 'SensitiveInformationPolicyConfig',
            'blockedInputMessaging', 'blockedOutputsMessaging',
            'filtersConfig', 'HATE', 'INSULTS', 'SEXUAL', 'VIOLENCE',
            'piiEntitiesConfig', 'AWS::Bedrock::Guardrail'
        ]
        for pattern in guardrail_patterns:
            if pattern in document_text:
                features['bedrock_guardrails'] = True
                features['guardrail_details'][pattern] = True
        
        # PII Protection detection
        pii_patterns = [
            'piiEntitiesConfig', 'SSN', 'CREDIT_DEBIT_CARD', 'EMAIL',
            'PHONE', 'PASSWORD', 'AWS_ACCESS_KEY', 'ANONYMIZE', 'BLOCK'
        ]
        for pattern in pii_patterns:
            if pattern in document_text:
                features['pii_protection'] = True
                break
        
        # WAF Rules detection
        waf_patterns = [
            'RateBasedStatement', 'ManagedRuleGroupStatement',
            'AWSManagedRulesCommonRuleSet', 'AWSManagedRulesKnownBadInputsRuleSet',
            'AWSManagedRulesAmazonIpReputationList', 'Log4JRCE'
        ]
        for pattern in waf_patterns:
            if pattern in document_text:
                features['waf_rules'] = True
                features['waf_details'][pattern] = True
        
        # VPC Endpoints detection
        if 'AWS::EC2::VPCEndpoint' in document_text or 'aws_vpc_endpoint' in document_text:
            features['vpc_endpoints'] = True
            # Extract endpoint types
            if 'Gateway' in document_text:
                features['vpc_endpoint_details'].append('Gateway Endpoint')
            if 'Interface' in document_text:
                features['vpc_endpoint_details'].append('Interface Endpoint')
        
        # VPC Flow Logs detection
        if 'AWS::EC2::FlowLog' in document_text or 'aws_flow_log' in document_text:
            features['vpc_flow_logs'] = True
        
        # Cognito Advanced Security
        if 'AdvancedSecurityMode' in document_text or 'ENFORCED' in document_text:
            features['cognito_advanced_security'] = True
        
        # CloudFront Signed URLs
        if 'KeyGroup' in document_text or 'PublicKey' in document_text:
            features['cloudfront_signed_urls'] = True
        
        # Encryption detection
        if 'KMS' in document_text or 'kms' in document_text:
            features['encryption_at_rest'] = True
        if 'TLS' in document_text or 'SSL' in document_text:
            features['encryption_in_transit'] = True
        
        return features

    def _extract_sustainability_features(self, document_text: str) -> Dict[str, any]:
        """Extract sustainability features from document."""
        features = {
            'graviton_instances': False,
            'graviton_types': [],
            's3_lifecycle_policies': False,
            'lifecycle_transitions': [],
            'auto_scaling': False,
            'spot_instances': False
        }
        
        # Graviton/ARM instance detection (critical - was missed in original assessment)
        graviton_patterns = [
            'm7g', 'c7g', 'r7g', 't4g', 'm6g', 'c6g', 'r6g', 't3g',
            'graviton', 'arm64', 'aarch64'
        ]
        for pattern in graviton_patterns:
            if pattern.lower() in document_text.lower():
                features['graviton_instances'] = True
                features['graviton_types'].append(pattern)
        
        # S3 Lifecycle policies
        lifecycle_patterns = [
            'LifecycleConfiguration', 'Transition', 'ExpirationInDays',
            'NoncurrentVersionTransition', 'INTELLIGENT_TIERING',
            'STANDARD_IA', 'GLACIER', 'DEEP_ARCHIVE'
        ]
        for pattern in lifecycle_patterns:
            if pattern in document_text:
                features['s3_lifecycle_policies'] = True
                features['lifecycle_transitions'].append(pattern)
        
        # Auto Scaling
        if 'AutoScaling' in document_text or 'aws_autoscaling' in document_text:
            features['auto_scaling'] = True
        
        # Spot instances
        if 'spot' in document_text.lower() or 'SpotPrice' in document_text:
            features['spot_instances'] = True
        
        return features
    
    def _extract_reliability_features(self, document_text: str) -> Dict[str, any]:
        """Extract reliability features from document."""
        features = {
            'multi_az': False,
            'point_in_time_recovery': False,
            'automatic_failover': False,
            'backup_enabled': False,
            'cross_region_replication': False,
            's3_versioning': False,
            'read_replicas': False
        }
        
        # Multi-AZ detection
        if 'MultiAZ' in document_text or 'multi_az' in document_text:
            features['multi_az'] = True
        if 'AvailabilityZones' in document_text:
            features['multi_az'] = True
        
        # Point-in-Time Recovery (DynamoDB)
        if 'PointInTimeRecoveryEnabled' in document_text:
            features['point_in_time_recovery'] = True
        if 'point_in_time_recovery' in document_text:
            features['point_in_time_recovery'] = True
        
        # Automatic Failover (ElastiCache, RDS)
        if 'AutomaticFailoverEnabled' in document_text:
            features['automatic_failover'] = True
        if 'automatic_failover_enabled' in document_text:
            features['automatic_failover'] = True
        
        # Backup
        if 'BackupRetentionPeriod' in document_text or 'backup_retention' in document_text:
            features['backup_enabled'] = True
        if 'AWS::Backup::' in document_text or 'aws_backup_' in document_text:
            features['backup_enabled'] = True
        
        # Cross-region replication
        if 'ReplicationConfiguration' in document_text:
            features['cross_region_replication'] = True
        
        # S3 Versioning
        if 'VersioningConfiguration' in document_text or 'versioning' in document_text:
            features['s3_versioning'] = True
        
        # Read Replicas
        if 'ReadReplica' in document_text or 'read_replica' in document_text:
            features['read_replicas'] = True
        
        return features


# Global instance for easy access
evidence_validator = EvidenceValidator()
