"""Draw.io/diagrams.net XML decoder for WAFR document analysis.

Draw.io files store diagram content as base64-encoded, deflate-compressed XML.
This module decodes that content to extract the actual diagram structure,
including AWS service icons, connections, and labels.
"""

import base64
import zlib
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import unquote
import logging

logger = logging.getLogger(__name__)


class DrawioDecoder:
    """Decoder for draw.io/diagrams.net XML files."""
    
    # Common AWS service patterns found in draw.io diagrams
    AWS_SERVICE_PATTERNS = {
        # Compute
        'ec2': ['EC2', 'Amazon EC2', 'Elastic Compute', 'Instance', 'mxgraph.aws4.ec2'],
        'lambda': ['Lambda', 'AWS Lambda', 'Serverless', 'mxgraph.aws4.lambda'],
        'ecs': ['ECS', 'Elastic Container Service', 'Container', 'mxgraph.aws4.ecs'],
        'eks': ['EKS', 'Elastic Kubernetes', 'Kubernetes', 'mxgraph.aws4.eks'],
        'fargate': ['Fargate', 'AWS Fargate', 'mxgraph.aws4.fargate'],
        
        # Storage
        's3': ['S3', 'Simple Storage', 'Bucket', 'mxgraph.aws4.s3'],
        'ebs': ['EBS', 'Elastic Block Store', 'mxgraph.aws4.ebs'],
        'efs': ['EFS', 'Elastic File System', 'mxgraph.aws4.efs'],
        'glacier': ['Glacier', 'S3 Glacier', 'mxgraph.aws4.glacier'],
        
        # Database
        'rds': ['RDS', 'Relational Database', 'Aurora', 'MySQL', 'PostgreSQL', 'mxgraph.aws4.rds'],
        'dynamodb': ['DynamoDB', 'Dynamo', 'NoSQL', 'mxgraph.aws4.dynamodb'],
        'elasticache': ['ElastiCache', 'Redis', 'Memcached', 'mxgraph.aws4.elasticache'],
        'redshift': ['Redshift', 'Data Warehouse', 'mxgraph.aws4.redshift'],
        
        # Networking
        'vpc': ['VPC', 'Virtual Private Cloud', 'mxgraph.aws4.vpc'],
        'cloudfront': ['CloudFront', 'CDN', 'Content Delivery', 'mxgraph.aws4.cloudfront'],
        'route53': ['Route 53', 'Route53', 'DNS', 'mxgraph.aws4.route_53'],
        'elb': ['ELB', 'ALB', 'NLB', 'Load Balancer', 'Elastic Load', 'mxgraph.aws4.elb'],
        'api_gateway': ['API Gateway', 'APIGateway', 'mxgraph.aws4.api_gateway'],
        'direct_connect': ['Direct Connect', 'DirectConnect', 'mxgraph.aws4.direct_connect'],
        
        # Security
        'iam': ['IAM', 'Identity', 'Access Management', 'mxgraph.aws4.iam'],
        'cognito': ['Cognito', 'User Pool', 'Identity Pool', 'mxgraph.aws4.cognito'],
        'waf': ['WAF', 'Web Application Firewall', 'mxgraph.aws4.waf'],
        'shield': ['Shield', 'DDoS', 'mxgraph.aws4.shield'],
        'kms': ['KMS', 'Key Management', 'mxgraph.aws4.kms'],
        'secrets_manager': ['Secrets Manager', 'SecretsManager', 'mxgraph.aws4.secrets_manager'],
        
        # Monitoring
        'cloudwatch': ['CloudWatch', 'Monitoring', 'Logs', 'Metrics', 'mxgraph.aws4.cloudwatch'],
        'cloudtrail': ['CloudTrail', 'Audit', 'mxgraph.aws4.cloudtrail'],
        'xray': ['X-Ray', 'XRay', 'Tracing', 'mxgraph.aws4.xray'],
        
        # Integration
        'sns': ['SNS', 'Simple Notification', 'mxgraph.aws4.sns'],
        'sqs': ['SQS', 'Simple Queue', 'Queue', 'mxgraph.aws4.sqs'],
        'eventbridge': ['EventBridge', 'Events', 'mxgraph.aws4.eventbridge'],
        'step_functions': ['Step Functions', 'StepFunctions', 'State Machine', 'mxgraph.aws4.step_functions'],
        
        # Analytics
        'kinesis': ['Kinesis', 'Streaming', 'mxgraph.aws4.kinesis'],
        'athena': ['Athena', 'Query', 'mxgraph.aws4.athena'],
        'glue': ['Glue', 'ETL', 'mxgraph.aws4.glue'],
        'emr': ['EMR', 'Elastic MapReduce', 'mxgraph.aws4.emr'],
        
        # AI/ML
        'sagemaker': ['SageMaker', 'Machine Learning', 'ML', 'mxgraph.aws4.sagemaker'],
        'bedrock': ['Bedrock', 'Foundation Model', 'mxgraph.aws4.bedrock'],
        'rekognition': ['Rekognition', 'Image Analysis', 'mxgraph.aws4.rekognition'],
    }
    
    # Architectural pattern indicators
    ARCHITECTURE_PATTERNS = {
        'multi_az': ['Multi-AZ', 'Availability Zone', 'AZ-a', 'AZ-b', 'AZ-c', 'us-east-1a', 'us-west-2b'],
        'microservices': ['Microservice', 'Service Mesh', 'API Gateway', 'Container'],
        'serverless': ['Lambda', 'Serverless', 'API Gateway', 'DynamoDB', 'S3'],
        'three_tier': ['Web Tier', 'App Tier', 'Data Tier', 'Presentation', 'Business Logic', 'Database'],
        'event_driven': ['Event', 'SNS', 'SQS', 'EventBridge', 'Kinesis', 'Queue'],
        'data_lake': ['Data Lake', 'S3', 'Glue', 'Athena', 'Lake Formation'],
        'hybrid': ['Direct Connect', 'VPN', 'On-Premises', 'On-Prem', 'Datacenter'],
    }
    
    @classmethod
    def is_drawio_file(cls, content: bytes) -> bool:
        """Check if content is a draw.io XML file."""
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='ignore')
            else:
                content_str = content
            
            # Check for draw.io/mxfile markers
            return '<mxfile' in content_str or '<mxGraphModel' in content_str
        except Exception:
            return False
    
    @classmethod
    def decode_drawio(cls, content: bytes) -> Tuple[str, Dict[str, Any]]:
        """
        Decode draw.io XML content and extract diagram information.
        
        Args:
            content: Raw XML content from draw.io file
            
        Returns:
            Tuple of (decoded_text_content, extracted_metadata)
        """
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='ignore')
            else:
                content_str = content
            
            logger.info("🔍 Decoding draw.io diagram file...")
            
            # Parse the XML
            root = ET.fromstring(content_str)
            
            # Extract all text content and metadata
            extracted_data = {
                'services': set(),
                'patterns': set(),
                'labels': [],
                'connections': [],
                'shapes': [],
                'raw_values': []
            }
            
            # Try to decode compressed diagram data
            decoded_content = cls._decode_compressed_content(root, extracted_data)
            
            # Also extract from uncompressed elements
            cls._extract_from_elements(root, extracted_data)
            
            # Build readable text representation
            text_content = cls._build_text_representation(extracted_data, decoded_content)
            
            # Convert sets to lists for JSON serialization
            metadata = {
                'identified_services': list(extracted_data['services']),
                'architectural_patterns': list(extracted_data['patterns']),
                'labels': extracted_data['labels'][:50],  # Limit labels
                'connection_count': len(extracted_data['connections']),
                'shape_count': len(extracted_data['shapes']),
                'is_drawio': True,
                'decode_success': bool(decoded_content or extracted_data['services'])
            }
            
            logger.info(f"✅ Draw.io decode complete: {len(metadata['identified_services'])} services, "
                       f"{len(metadata['architectural_patterns'])} patterns found")
            
            return text_content, metadata
            
        except ET.ParseError as e:
            logger.warning(f"⚠️ XML parse error in draw.io file: {e}")
            return cls._fallback_extraction(content), {'is_drawio': True, 'decode_success': False}
        except Exception as e:
            logger.error(f"❌ Error decoding draw.io file: {e}")
            return cls._fallback_extraction(content), {'is_drawio': True, 'decode_success': False}
    
    @classmethod
    def _decode_compressed_content(cls, root: ET.Element, extracted_data: Dict) -> str:
        """Decode base64+deflate compressed diagram content."""
        decoded_parts = []
        
        # Find all diagram elements with compressed content
        for diagram in root.iter('diagram'):
            # Get the compressed content (either as text or in a child element)
            compressed_data = diagram.text
            if not compressed_data:
                # Try to find mxGraphModel directly
                for child in diagram:
                    if child.tag == 'mxGraphModel':
                        cls._extract_from_graph_model(child, extracted_data)
                continue
            
            compressed_data = compressed_data.strip()
            if not compressed_data:
                continue
            
            try:
                # Decode base64
                decoded_bytes = base64.b64decode(compressed_data)
                
                # Try to decompress (draw.io uses deflate with -15 window bits)
                try:
                    decompressed = zlib.decompress(decoded_bytes, -15)
                    decoded_str = decompressed.decode('utf-8', errors='ignore')
                except zlib.error:
                    # Try without raw deflate
                    try:
                        decompressed = zlib.decompress(decoded_bytes)
                        decoded_str = decompressed.decode('utf-8', errors='ignore')
                    except zlib.error:
                        # Content might not be compressed, try direct decode
                        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
                
                # URL decode the content
                decoded_str = unquote(decoded_str)
                
                # Parse the decoded XML
                if '<mxGraphModel' in decoded_str:
                    try:
                        graph_root = ET.fromstring(decoded_str)
                        cls._extract_from_graph_model(graph_root, extracted_data)
                        decoded_parts.append(decoded_str)
                    except ET.ParseError:
                        # Extract text patterns directly
                        cls._extract_patterns_from_text(decoded_str, extracted_data)
                        decoded_parts.append(decoded_str)
                else:
                    cls._extract_patterns_from_text(decoded_str, extracted_data)
                    decoded_parts.append(decoded_str)
                    
            except Exception as e:
                logger.debug(f"Could not decode compressed content: {e}")
                continue
        
        return '\n'.join(decoded_parts)
    
    @classmethod
    def _extract_from_graph_model(cls, graph_model: ET.Element, extracted_data: Dict):
        """Extract information from mxGraphModel element."""
        
        # Find all cells (shapes and connections)
        for cell in graph_model.iter('mxCell'):
            cell_id = cell.get('id', '')
            value = cell.get('value', '')
            style = cell.get('style', '')
            source = cell.get('source')
            target = cell.get('target')
            
            # Store raw values for analysis
            if value:
                extracted_data['raw_values'].append(value)
                extracted_data['labels'].append(value)
            
            # Check if it's a connection (edge)
            if source and target:
                extracted_data['connections'].append({
                    'source': source,
                    'target': target,
                    'label': value
                })
            else:
                extracted_data['shapes'].append({
                    'id': cell_id,
                    'value': value,
                    'style': style
                })
            
            # Extract AWS services from value and style
            cls._identify_services(value, extracted_data)
            cls._identify_services(style, extracted_data)
            
            # Check for architectural patterns
            cls._identify_patterns(value, extracted_data)
            cls._identify_patterns(style, extracted_data)
        
        # Also check mxGeometry for any embedded data
        for obj in graph_model.iter('object'):
            label = obj.get('label', '')
            if label:
                extracted_data['labels'].append(label)
                cls._identify_services(label, extracted_data)
                cls._identify_patterns(label, extracted_data)
    
    @classmethod
    def _extract_from_elements(cls, root: ET.Element, extracted_data: Dict):
        """Extract information from uncompressed XML elements."""
        
        # Check all elements for AWS service references
        for elem in root.iter():
            # Check element text
            if elem.text:
                cls._identify_services(elem.text, extracted_data)
                cls._identify_patterns(elem.text, extracted_data)
            
            # Check all attributes
            for attr_name, attr_value in elem.attrib.items():
                cls._identify_services(attr_value, extracted_data)
                cls._identify_patterns(attr_value, extracted_data)
                
                # Capture labels and values
                if attr_name in ['value', 'label', 'name']:
                    if attr_value and len(attr_value) < 200:  # Skip very long values
                        extracted_data['labels'].append(attr_value)
    
    @classmethod
    def _extract_patterns_from_text(cls, text: str, extracted_data: Dict):
        """Extract patterns from raw text content."""
        cls._identify_services(text, extracted_data)
        cls._identify_patterns(text, extracted_data)
        
        # Extract any visible labels (text between tags or in value attributes)
        value_pattern = r'value="([^"]*)"'
        for match in re.finditer(value_pattern, text):
            value = match.group(1)
            if value and len(value) < 200:
                extracted_data['labels'].append(value)
    
    @classmethod
    def _identify_services(cls, text: str, extracted_data: Dict):
        """Identify AWS services in text."""
        if not text:
            return
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        for service_key, patterns in cls.AWS_SERVICE_PATTERNS.items():
            for pattern in patterns:
                if pattern.upper() in text_upper or pattern.lower() in text_lower:
                    extracted_data['services'].add(service_key.upper().replace('_', ' '))
                    break
    
    @classmethod
    def _identify_patterns(cls, text: str, extracted_data: Dict):
        """Identify architectural patterns in text."""
        if not text:
            return
        
        text_lower = text.lower()
        
        for pattern_key, indicators in cls.ARCHITECTURE_PATTERNS.items():
            for indicator in indicators:
                if indicator.lower() in text_lower:
                    extracted_data['patterns'].add(pattern_key.replace('_', ' ').title())
                    break
    
    @classmethod
    def _build_text_representation(cls, extracted_data: Dict, decoded_content: str) -> str:
        """Build a readable text representation for Claude analysis."""
        
        parts = []
        
        parts.append("=== DRAW.IO ARCHITECTURE DIAGRAM ANALYSIS ===\n")
        
        # AWS Services found
        if extracted_data['services']:
            parts.append("## AWS Services Identified:")
            for service in sorted(extracted_data['services']):
                parts.append(f"  - {service}")
            parts.append("")
        
        # Architectural patterns
        if extracted_data['patterns']:
            parts.append("## Architectural Patterns Detected:")
            for pattern in sorted(extracted_data['patterns']):
                parts.append(f"  - {pattern}")
            parts.append("")
        
        # Labels and text content
        unique_labels = list(set(extracted_data['labels']))
        meaningful_labels = [l for l in unique_labels if l and len(l) > 2 and not l.startswith('mx')]
        
        if meaningful_labels:
            parts.append("## Diagram Labels and Text:")
            for label in meaningful_labels[:30]:  # Limit to 30 labels
                # Clean up HTML entities
                clean_label = label.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                clean_label = re.sub(r'<[^>]+>', '', clean_label)  # Remove HTML tags
                if clean_label.strip():
                    parts.append(f"  - {clean_label.strip()}")
            parts.append("")
        
        # Connection summary
        if extracted_data['connections']:
            parts.append(f"## Connections: {len(extracted_data['connections'])} connections between components")
            parts.append("")
        
        # Shape summary
        if extracted_data['shapes']:
            parts.append(f"## Components: {len(extracted_data['shapes'])} shapes/components in diagram")
            parts.append("")
        
        # Add note about diagram type
        parts.append("## Analysis Notes:")
        parts.append("  - This is a draw.io/diagrams.net architecture diagram")
        parts.append("  - The diagram has been decoded and analyzed for AWS services and patterns")
        if not extracted_data['services']:
            parts.append("  - No specific AWS services were identified in the diagram labels")
            parts.append("  - The diagram may use generic shapes or custom icons")
        
        return '\n'.join(parts)
    
    @classmethod
    def _fallback_extraction(cls, content: bytes) -> str:
        """Fallback extraction when full decode fails."""
        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8', errors='ignore')
            else:
                content_str = content
            
            # Try to extract any readable text
            extracted_data = {
                'services': set(),
                'patterns': set(),
                'labels': [],
                'connections': [],
                'shapes': []
            }
            
            cls._extract_patterns_from_text(content_str, extracted_data)
            
            return cls._build_text_representation(extracted_data, "")
            
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return "Draw.io diagram file detected but could not be fully decoded. Please export as PNG or PDF for better analysis."
