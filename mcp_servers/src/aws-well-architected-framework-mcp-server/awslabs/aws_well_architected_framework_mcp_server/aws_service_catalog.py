"""Dynamic AWS Service Catalog for comprehensive service detection."""

import json
import logging
import os
import re
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AWSServiceCatalog:
    """Dynamic AWS service catalog with automatic updates and comprehensive service detection."""
    
    def __init__(self):
        self._services_cache = None
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=24)  # Cache for 24 hours
        self._catalog_file = os.path.join(os.path.dirname(__file__), 'aws_services_catalog.json')
    
    def get_all_services(self) -> Dict[str, List[str]]:
        """Get comprehensive AWS services with all naming variations."""
        if self._is_cache_valid():
            return self._services_cache
        
        logger.info("Loading AWS service catalog...")
        
        # Try to load from local catalog file first
        if os.path.exists(self._catalog_file):
            try:
                with open(self._catalog_file, 'r') as f:
                    catalog_data = json.load(f)
                    if self._is_catalog_recent(catalog_data):
                        self._services_cache = catalog_data['services']
                        self._cache_timestamp = datetime.now()
                        logger.info(f"Loaded {len(self._services_cache)} services from local catalog")
                        return self._services_cache
            except Exception as e:
                logger.warning(f"Failed to load local catalog: {e}")
        
        # Generate comprehensive service catalog
        self._services_cache = self._generate_comprehensive_catalog()
        self._cache_timestamp = datetime.now()
        
        # Save to local file for future use
        self._save_catalog_to_file()
        
        logger.info(f"Generated comprehensive catalog with {len(self._services_cache)} services")
        return self._services_cache
    
    def _is_cache_valid(self) -> bool:
        """Check if the current cache is still valid."""
        if not self._services_cache or not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration
    
    def _is_catalog_recent(self, catalog_data: Dict) -> bool:
        """Check if the catalog file is recent enough."""
        try:
            file_timestamp = datetime.fromisoformat(catalog_data.get('timestamp', ''))
            return datetime.now() - file_timestamp < self._cache_duration
        except:
            return False
    
    def _generate_comprehensive_catalog(self) -> Dict[str, List[str]]:
        """Generate comprehensive AWS service catalog with all variations."""
        return {
            # Compute Services
            'EC2': ['EC2', 'Elastic Compute Cloud', 'virtual machine', 'instance', 'compute instance', 'VM'],
            'Lambda': ['Lambda', 'serverless function', 'function as a service', 'FaaS', 'AWS Lambda'],
            'ECS': ['ECS', 'Elastic Container Service', 'container service', 'Docker container'],
            'EKS': ['EKS', 'Elastic Kubernetes Service', 'Kubernetes', 'K8s', 'container orchestration'],
            'Fargate': ['Fargate', 'serverless container', 'serverless compute', 'AWS Fargate'],
            'Batch': ['Batch', 'batch computing', 'job scheduling', 'AWS Batch'],
            'Lightsail': ['Lightsail', 'virtual private server', 'VPS', 'simple compute'],
            'Auto Scaling': ['Auto Scaling', 'autoscaling', 'scaling group', 'horizontal scaling', 'ASG'],
            'Elastic Beanstalk': ['Elastic Beanstalk', 'platform as a service', 'PaaS', 'application platform'],
            'App Runner': ['App Runner', 'containerized web applications', 'serverless containers'],
            'Outposts': ['Outposts', 'hybrid cloud', 'on-premises AWS', 'edge computing'],
            
            # Storage Services
            'S3': ['S3', 'Simple Storage Service', 'object storage', 'bucket', 'blob storage'],
            'EBS': ['EBS', 'Elastic Block Store', 'block storage', 'disk storage'],
            'EFS': ['EFS', 'Elastic File System', 'network file system', 'NFS', 'shared storage'],
            'FSx': ['FSx', 'fully managed file system', 'Lustre', 'Windows File Server', 'NetApp ONTAP'],
            'Storage Gateway': ['Storage Gateway', 'hybrid storage', 'on-premises integration'],
            'AWS Backup': ['AWS Backup', 'backup service', 'data backup', 'backup vault'],
            'DataSync': ['DataSync', 'data transfer', 'file synchronization', 'data migration'],
            'Snow Family': ['Snow Family', 'Snowball', 'Snowmobile', 'data migration', 'edge computing'],
            'S3 Glacier': ['S3 Glacier', 'Glacier', 'archival storage', 'cold storage'],
            
            # Database Services
            'RDS': ['RDS', 'Relational Database Service', 'MySQL', 'PostgreSQL', 'MariaDB', 'Oracle', 'SQL Server'],
            'Aurora': ['Aurora', 'Amazon Aurora', 'MySQL compatible', 'PostgreSQL compatible'],
            'DynamoDB': ['DynamoDB', 'NoSQL database', 'document database', 'key-value store'],
            'ElastiCache': ['ElastiCache', 'Redis', 'Memcached', 'caching', 'in-memory cache'],
            'Neptune': ['Neptune', 'graph database', 'knowledge graph', 'RDF'],
            'DocumentDB': ['DocumentDB', 'document database', 'MongoDB compatible'],
            'Keyspaces': ['Keyspaces', 'Cassandra', 'wide column store'],
            'QLDB': ['QLDB', 'quantum ledger database', 'immutable database', 'blockchain'],
            'Timestream': ['Timestream', 'time series database', 'IoT analytics'],
            'MemoryDB': ['MemoryDB', 'Redis compatible', 'in-memory database'],
            
            # Networking & Content Delivery
            'VPC': ['VPC', 'Virtual Private Cloud', 'virtual network', 'private cloud'],
            'CloudFront': ['CloudFront', 'CDN', 'content delivery network', 'edge locations'],
            'Route 53': ['Route 53', 'DNS', 'domain name system', 'hosted zone'],
            'ELB': ['ELB', 'Elastic Load Balancer', 'load balancer', 'Classic Load Balancer'],
            'ALB': ['ALB', 'Application Load Balancer', 'layer 7 load balancer'],
            'NLB': ['NLB', 'Network Load Balancer', 'layer 4 load balancer'],
            'GWLB': ['GWLB', 'Gateway Load Balancer', 'transparent proxy'],
            'API Gateway': ['API Gateway', 'REST API', 'HTTP API', 'GraphQL API', 'WebSocket API'],
            'Direct Connect': ['Direct Connect', 'dedicated connection', 'hybrid connectivity'],
            'Transit Gateway': ['Transit Gateway', 'network hub', 'VPC connectivity'],
            'VPN': ['VPN', 'Site-to-Site VPN', 'Client VPN', 'virtual private network'],
            'Global Accelerator': ['Global Accelerator', 'network performance', 'anycast'],
            'App Mesh': ['App Mesh', 'service mesh', 'microservices communication'],
            'Cloud Map': ['Cloud Map', 'service discovery', 'DNS-based discovery'],
            'PrivateLink': ['PrivateLink', 'private connectivity', 'VPC endpoint'],
            
            # Security, Identity & Compliance
            'IAM': ['IAM', 'Identity and Access Management', 'roles', 'policies', 'users', 'permissions'],
            'Cognito': ['Cognito', 'user authentication', 'identity pool', 'user pool'],
            'KMS': ['KMS', 'Key Management Service', 'encryption key', 'customer managed key'],
            'Secrets Manager': ['Secrets Manager', 'secret management', 'password rotation'],
            'Certificate Manager': ['Certificate Manager', 'SSL certificate', 'TLS certificate', 'ACM'],
            'WAF': ['WAF', 'Web Application Firewall', 'firewall', 'web security'],
            'Shield': ['Shield', 'DDoS protection', 'Shield Advanced', 'distributed denial of service'],
            'GuardDuty': ['GuardDuty', 'threat detection', 'security monitoring'],
            'Inspector': ['Inspector', 'security assessment', 'vulnerability assessment'],
            'Macie': ['Macie', 'data security', 'sensitive data', 'data classification'],
            'Security Hub': ['Security Hub', 'security posture', 'security findings'],
            'CloudTrail': ['CloudTrail', 'audit trail', 'API logging', 'governance'],
            'Config': ['Config', 'configuration compliance', 'resource configuration'],
            'Systems Manager': ['Systems Manager', 'SSM', 'parameter store', 'patch manager'],
            'Resource Access Manager': ['Resource Access Manager', 'RAM', 'resource sharing'],
            'Single Sign-On': ['Single Sign-On', 'SSO', 'identity federation'],
            'Directory Service': ['Directory Service', 'Active Directory', 'LDAP'],
            
            # Management & Governance
            'CloudWatch': ['CloudWatch', 'monitoring', 'metrics', 'logs', 'alarms'],
            'X-Ray': ['X-Ray', 'distributed tracing', 'application monitoring'],
            'CloudFormation': ['CloudFormation', 'infrastructure as code', 'IaC', 'template'],
            'Service Catalog': ['Service Catalog', 'portfolio management', 'product catalog'],
            'Trusted Advisor': ['Trusted Advisor', 'optimization recommendations', 'best practices'],
            'Personal Health Dashboard': ['Personal Health Dashboard', 'service health', 'notifications'],
            'Control Tower': ['Control Tower', 'landing zone', 'multi-account governance'],
            'Organizations': ['Organizations', 'account management', 'consolidated billing'],
            'Config': ['Config', 'compliance monitoring', 'configuration tracking'],
            'CloudTrail': ['CloudTrail', 'API auditing', 'compliance logging'],
            'OpsWorks': ['OpsWorks', 'configuration management', 'Chef', 'Puppet'],
            'License Manager': ['License Manager', 'software licensing', 'license tracking'],
            
            # Analytics
            'Athena': ['Athena', 'serverless analytics', 'SQL queries', 'data lake analytics'],
            'EMR': ['EMR', 'Elastic MapReduce', 'big data processing', 'Hadoop', 'Spark'],
            'Redshift': ['Redshift', 'data warehouse', 'analytics database', 'OLAP'],
            'QuickSight': ['QuickSight', 'business intelligence', 'data visualization'],
            'Glue': ['Glue', 'ETL', 'data catalog', 'data preparation'],
            'Kinesis': ['Kinesis', 'streaming data', 'real-time analytics', 'data streams'],
            'Data Pipeline': ['Data Pipeline', 'data workflow', 'ETL pipeline'],
            'Lake Formation': ['Lake Formation', 'data lake', 'data governance'],
            'MSK': ['MSK', 'Managed Streaming for Kafka', 'Apache Kafka'],
            'OpenSearch': ['OpenSearch', 'search engine', 'Elasticsearch', 'log analytics'],
            'CloudSearch': ['CloudSearch', 'managed search', 'full-text search'],
            'Elasticsearch Service': ['Elasticsearch Service', 'search analytics', 'log analysis'],
            
            # Machine Learning
            'SageMaker': ['SageMaker', 'machine learning', 'ML', 'model training'],
            'Bedrock': ['Bedrock', 'generative AI', 'foundation models', 'LLM'],
            'Rekognition': ['Rekognition', 'image recognition', 'computer vision'],
            'Comprehend': ['Comprehend', 'natural language processing', 'NLP', 'text analysis'],
            'Textract': ['Textract', 'document analysis', 'OCR', 'text extraction'],
            'Polly': ['Polly', 'text to speech', 'TTS', 'voice synthesis'],
            'Transcribe': ['Transcribe', 'speech to text', 'STT', 'audio transcription'],
            'Translate': ['Translate', 'language translation', 'multilingual'],
            'Lex': ['Lex', 'chatbot', 'conversational AI', 'voice interface'],
            'Personalize': ['Personalize', 'recommendation engine', 'ML recommendations'],
            'Forecast': ['Forecast', 'time series forecasting', 'demand planning'],
            'Fraud Detector': ['Fraud Detector', 'fraud detection', 'ML fraud prevention'],
            'CodeGuru': ['CodeGuru', 'code review', 'performance optimization'],
            'DevOps Guru': ['DevOps Guru', 'operational insights', 'anomaly detection'],
            'Lookout': ['Lookout', 'anomaly detection', 'industrial AI'],
            'Monitron': ['Monitron', 'equipment monitoring', 'predictive maintenance'],
            'HealthLake': ['HealthLake', 'healthcare data', 'FHIR'],
            'Kendra': ['Kendra', 'enterprise search', 'intelligent search'],
            'Augmented AI': ['Augmented AI', 'A2I', 'human review'],
            
            # Application Integration
            'SQS': ['SQS', 'Simple Queue Service', 'message queue', 'queue'],
            'SNS': ['SNS', 'Simple Notification Service', 'notification', 'pub/sub'],
            'EventBridge': ['EventBridge', 'event bus', 'event routing', 'CloudWatch Events'],
            'Step Functions': ['Step Functions', 'state machine', 'workflow', 'orchestration'],
            'SWF': ['SWF', 'Simple Workflow Service', 'workflow coordination'],
            'MQ': ['MQ', 'message broker', 'Apache ActiveMQ', 'RabbitMQ'],
            'AppSync': ['AppSync', 'GraphQL', 'real-time data', 'offline sync'],
            
            # Developer Tools
            'CodeCommit': ['CodeCommit', 'source control', 'Git repository'],
            'CodeBuild': ['CodeBuild', 'build service', 'continuous integration'],
            'CodeDeploy': ['CodeDeploy', 'deployment service', 'blue/green deployment'],
            'CodePipeline': ['CodePipeline', 'CI/CD pipeline', 'continuous delivery'],
            'CodeStar': ['CodeStar', 'development workflow', 'project templates'],
            'CodeArtifact': ['CodeArtifact', 'artifact repository', 'package management'],
            'CodeGuru': ['CodeGuru', 'code analysis', 'performance profiling'],
            'Cloud9': ['Cloud9', 'cloud IDE', 'development environment'],
            'CloudShell': ['CloudShell', 'browser-based shell', 'command line'],
            
            # Customer Engagement
            'Connect': ['Connect', 'contact center', 'call center', 'customer service'],
            'Pinpoint': ['Pinpoint', 'customer engagement', 'marketing campaigns'],
            'Simple Email Service': ['Simple Email Service', 'SES', 'email service', 'transactional email'],
            'WorkMail': ['WorkMail', 'managed email', 'business email'],
            'Chime': ['Chime', 'video conferencing', 'business communications'],
            
            # End User Computing
            'WorkSpaces': ['WorkSpaces', 'virtual desktop', 'VDI', 'desktop as a service'],
            'AppStream': ['AppStream', 'application streaming', 'virtual applications'],
            'WorkLink': ['WorkLink', 'secure mobile access', 'internal websites'],
            'WorkDocs': ['WorkDocs', 'document collaboration', 'file sharing'],
            
            # IoT
            'IoT Core': ['IoT Core', 'Internet of Things', 'device connectivity', 'MQTT'],
            'IoT Device Management': ['IoT Device Management', 'device fleet management'],
            'IoT Analytics': ['IoT Analytics', 'IoT data analysis', 'time series analytics'],
            'IoT Events': ['IoT Events', 'event detection', 'IoT monitoring'],
            'IoT Greengrass': ['IoT Greengrass', 'edge computing', 'local processing'],
            'IoT SiteWise': ['IoT SiteWise', 'industrial data', 'asset modeling'],
            'IoT Things Graph': ['IoT Things Graph', 'visual workflow', 'device coordination'],
            'IoT Device Defender': ['IoT Device Defender', 'IoT security', 'device monitoring'],
            'IoT 1-Click': ['IoT 1-Click', 'simple IoT devices', 'one-click triggers'],
            
            # Media Services
            'Elemental MediaLive': ['Elemental MediaLive', 'live video processing', 'broadcast'],
            'Elemental MediaPackage': ['Elemental MediaPackage', 'video origination', 'packaging'],
            'Elemental MediaStore': ['Elemental MediaStore', 'media storage', 'video storage'],
            'Elemental MediaConvert': ['Elemental MediaConvert', 'video processing', 'transcoding'],
            'Kinesis Video Streams': ['Kinesis Video Streams', 'video streaming', 'real-time video'],
            'Interactive Video Service': ['Interactive Video Service', 'IVS', 'live streaming'],
            
            # Mobile
            'Amplify': ['Amplify', 'full-stack development', 'web application', 'mobile backend'],
            'Device Farm': ['Device Farm', 'mobile testing', 'device testing'],
            'Location Service': ['Location Service', 'maps', 'geocoding', 'routing'],
            
            # Game Development
            'GameLift': ['GameLift', 'game server hosting', 'multiplayer games'],
            'Lumberyard': ['Lumberyard', 'game engine', '3D game development'],
            
            # Blockchain
            'Managed Blockchain': ['Managed Blockchain', 'blockchain network', 'distributed ledger'],
            
            # Quantum Computing
            'Braket': ['Braket', 'quantum computing', 'quantum circuits'],
            
            # Satellite
            'Ground Station': ['Ground Station', 'satellite communication', 'satellite data'],
            
            # Robotics
            'RoboMaker': ['RoboMaker', 'robotics development', 'robot simulation'],
            
            # AR/VR
            'Sumerian': ['Sumerian', 'AR/VR applications', '3D scenes'],
            
            # Cost Management
            'Cost Explorer': ['Cost Explorer', 'cost analysis', 'usage reports'],
            'Budgets': ['Budgets', 'cost budgets', 'usage budgets'],
            'Cost and Usage Report': ['Cost and Usage Report', 'CUR', 'detailed billing'],
            'Savings Plans': ['Savings Plans', 'compute savings', 'cost optimization'],
            'Reserved Instances': ['Reserved Instances', 'RI', 'capacity reservation'],
            
            # Migration & Transfer
            'Migration Hub': ['Migration Hub', 'migration tracking', 'application discovery'],
            'Application Discovery Service': ['Application Discovery Service', 'ADS', 'migration planning'],
            'Database Migration Service': ['Database Migration Service', 'DMS', 'database migration'],
            'Server Migration Service': ['Server Migration Service', 'SMS', 'VM migration'],
            'Transfer Family': ['Transfer Family', 'SFTP', 'FTPS', 'file transfer'],
            'DataSync': ['DataSync', 'data transfer', 'file synchronization'],
            
            # Business Applications
            'Alexa for Business': ['Alexa for Business', 'voice assistant', 'workplace productivity'],
            'Amazon Honeycode': ['Amazon Honeycode', 'no-code application', 'spreadsheet app'],
            'Simple Email Service': ['Simple Email Service', 'SES', 'transactional email'],
            'WorkMail': ['WorkMail', 'business email', 'calendar'],
            'Chime': ['Chime', 'video meetings', 'chat'],
            'Connect': ['Connect', 'contact center', 'customer service'],
        }
    
    def _save_catalog_to_file(self):
        """Save the current catalog to a local file for caching."""
        try:
            catalog_data = {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'services': self._services_cache
            }
            with open(self._catalog_file, 'w') as f:
                json.dump(catalog_data, f, indent=2)
            logger.info(f"Saved service catalog to {self._catalog_file}")
        except Exception as e:
            logger.warning(f"Failed to save catalog to file: {e}")
    
    def find_services_in_text(self, text: str) -> List[str]:
        """Find all AWS services mentioned in the given text."""
        services = self.get_all_services()
        found_services = []
        text_upper = text.upper()
        
        for service_name, patterns in services.items():
            for pattern in patterns:
                if pattern.upper() in text_upper:
                    found_services.append(service_name)
                    break  # Found one pattern for this service, move to next
        
        return list(set(found_services))
    
    def get_service_patterns(self, service_name: str) -> List[str]:
        """Get all naming patterns for a specific service."""
        services = self.get_all_services()
        return services.get(service_name, [])
    
    def search_services(self, query: str) -> List[str]:
        """Search for services matching a query."""
        services = self.get_all_services()
        matching_services = []
        query_upper = query.upper()
        
        for service_name, patterns in services.items():
            if query_upper in service_name.upper():
                matching_services.append(service_name)
            else:
                for pattern in patterns:
                    if query_upper in pattern.upper():
                        matching_services.append(service_name)
                        break
        
        return list(set(matching_services))

# Global instance
_catalog_instance = None

def get_aws_service_catalog() -> AWSServiceCatalog:
    """Get the global AWS service catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = AWSServiceCatalog()
    return _catalog_instance
