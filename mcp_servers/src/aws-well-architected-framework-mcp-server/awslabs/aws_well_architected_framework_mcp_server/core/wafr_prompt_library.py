#!/usr/bin/env python3
"""
WAFR Prompt Library
Specialized prompts for Well-Architected Framework analysis using AI
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class WAFRPromptLibrary:
    """
    Comprehensive prompt library for WAFR AI analysis
    Provides structured, evidence-based prompts for different analysis types
    """
    
    def __init__(self):
        """Initialize WAFR prompt library"""
        self.pillar_focus_areas = {
            'operational_excellence': [
                'automation', 'monitoring', 'deployment practices', 'incident response',
                'change management', 'operational procedures'
            ],
            'security': [
                'identity and access management', 'data protection', 'infrastructure protection',
                'detective controls', 'incident response', 'compliance'
            ],
            'reliability': [
                'fault tolerance', 'recovery procedures', 'scaling', 'change management',
                'monitoring', 'capacity planning'
            ],
            'performance_efficiency': [
                'resource selection', 'monitoring', 'trade-offs', 'optimization',
                'scaling patterns', 'data access patterns'
            ],
            'cost_optimization': [
                'cost-effective resources', 'matching supply and demand', 'expenditure awareness',
                'optimization over time', 'resource lifecycle management'
            ],
            'sustainability': [
                'region selection', 'user behavior patterns', 'software patterns',
                'data patterns', 'hardware patterns', 'development processes'
            ]
        }
        
        logger.info("📝 WAFR Prompt Library initialized")
    
    def build_architecture_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build comprehensive architecture analysis prompt using FUNDING REVIEWER APPROACH
        
        Args:
            context: Analysis context including chat_id, workload_type, etc.
            
        Returns:
            Structured prompt for architecture analysis with ### headers
        """
        workload_type = context.get('workload_type', 'general')
        focus_areas = context.get('focus_areas', [])
        
        # FUNDING REVIEWER APPROACH: Use ### headers for consistent parsing
        prompt = f"""You are an expert AWS solutions architect analyzing architecture documents. Analyze the document thoroughly and provide a structured analysis.

Please analyze the document and extract the following information in a structured format:

## TECHNICAL ANALYSIS

### AWS Services Identified:
List all AWS services mentioned, shown, or implied in the document. Be specific and comprehensive.
Look for service icons, labels, text mentions, and architectural components.
Include services like: EC2, S3, Lambda, RDS, DynamoDB, VPC, CloudFront, ELB, Auto Scaling, CloudWatch, IAM, Route 53, API Gateway, SNS, SQS, etc.
For diagrams: Identify every service icon, box, and component you see.

### Architecture Patterns:
Identify architectural patterns, design approaches, and technical methodologies.
Examples: microservices, serverless, 3-tier, event-driven, SOA, hub-and-spoke, etc.
Describe how the architecture is organized and structured.

### Infrastructure Components:
Identify infrastructure elements, networking, security, and operational components.
Include: VPCs, subnets, security groups, load balancers, databases, caching layers, etc.
Describe the network topology and infrastructure layout.

### Security Elements:
Identify security components, access controls, and protection mechanisms.
Include: IAM roles, encryption, network ACLs, security groups, WAF, Shield, etc.
Describe security boundaries and access patterns.

### Multi-AZ Detection:
Analyze if the architecture uses multiple Availability Zones for high availability.
Look for: AZ labels (us-east-1a, us-east-1b), distributed resources, load balancers, replicas.
Provide specific evidence of multi-AZ deployment.

### Data Flow Patterns:
Describe how data moves through the system and processing workflows.
Identify data ingestion, processing, storage, and delivery patterns.

### Operational Elements:
Identify monitoring, logging, automation, and operational tools.
Include: CloudWatch, X-Ray, CloudTrail, Systems Manager, etc.

Please provide detailed, specific information for each section. If information is not available for a section, indicate "Not specified in document".

Format your response with clear section headers (###) and bullet points for easy parsing.

CRITICAL: Be explicit and thorough about AWS services. List every service you can identify."""
        
        return prompt.strip()
    
    def build_vision_analysis_prompt(self) -> str:
        """Build specialized prompt for vision/diagram analysis"""
        
        prompt = """
You are an expert at analyzing AWS architecture diagrams and visual documentation. Analyze the provided diagram with focus on Well-Architected Framework principles.

## Vision Analysis Objectives
1. **Visual Service Identification**: Identify AWS services from icons, labels, and visual elements
2. **Connection Analysis**: Analyze data flow, network connections, and service relationships
3. **Multi-AZ Visual Detection**: Identify availability zone distribution from diagram layout
4. **Security Boundaries**: Detect VPCs, subnets, security groups from visual boundaries
5. **Scaling Patterns**: Identify auto-scaling groups, load balancers, and scaling indicators

## Analysis Framework

### 1. Service Inventory from Diagram
```json
{
  "visual_services": [
    {
      "service": "service_name",
      "visual_evidence": "icon_type_or_label",
      "location_in_diagram": "description_of_position",
      "configuration_hints": "visual_configuration_clues"
    }
  ]
}
```

### 2. Architecture Flow Analysis
```json
{
  "data_flows": [
    {
      "source": "source_service",
      "destination": "destination_service",
      "connection_type": "arrow_type_or_line_style",
      "protocol_hints": "visual_protocol_indicators"
    }
  ]
}
```

### 3. Multi-AZ Visual Assessment
```json
{
  "multi_az_visual": {
    "availability_zones_shown": ["az1", "az2", "az3"],
    "services_distributed": ["service1", "service2"],
    "visual_evidence": "how_multi_az_is_depicted",
    "redundancy_patterns": "visual_redundancy_indicators"
  }
}
```

### 4. Security Architecture Visualization
```json
{
  "security_boundaries": {
    "vpc_boundaries": "visual_vpc_indicators",
    "subnet_separation": "subnet_visual_separation",
    "security_groups": "security_group_visual_indicators",
    "public_private_distinction": "how_public_private_is_shown"
  }
}
```

### 5. Well-Architected Visual Indicators
Analyze how the diagram demonstrates:
- **Operational Excellence**: Monitoring, automation visual indicators
- **Security**: Security boundaries, encryption indicators
- **Reliability**: Redundancy, backup visual patterns
- **Performance**: Caching, CDN, optimization indicators
- **Cost Optimization**: Resource sizing, reserved capacity indicators
- **Sustainability**: Efficient resource usage patterns

## Output Requirements
- Provide specific visual evidence for all findings
- Reference diagram elements by position or labels
- Quantify visual elements where possible
- Cross-reference with WAFR best practices
- Identify any visual inconsistencies or unclear elements

Analyze the architecture diagram:
"""
        
        return prompt.strip()
    
    def build_document_correlation_prompt(self) -> str:
        """Build prompt for cross-document correlation analysis"""
        
        prompt = """
You are analyzing multiple architecture documents for consistency and completeness. Perform cross-document correlation to ensure architectural coherence.

## Correlation Analysis Objectives
1. **Consistency Validation**: Ensure services and configurations match across documents
2. **Completeness Assessment**: Identify gaps or missing information
3. **Conflict Resolution**: Detect and explain any contradictions
4. **Evidence Triangulation**: Use multiple sources to validate findings
5. **Comprehensive View**: Build complete architecture picture from all sources

## Analysis Framework

### 1. Service Consistency Analysis
```json
{
  "service_correlation": [
    {
      "service": "service_name",
      "document_mentions": [
        {
          "document": "doc_name",
          "configuration": "config_details",
          "evidence": "specific_evidence"
        }
      ],
      "consistency_score": "high/medium/low",
      "conflicts": "any_contradictions_found"
    }
  ]
}
```

### 2. Architecture Completeness
```json
{
  "completeness_assessment": {
    "fully_documented_services": ["service1", "service2"],
    "partially_documented_services": ["service3"],
    "missing_documentation": ["expected_but_missing_services"],
    "documentation_gaps": ["specific_gaps_identified"]
  }
}
```

### 3. Cross-Document Validation
```json
{
  "validation_results": {
    "consistent_findings": ["finding1", "finding2"],
    "conflicting_information": [
      {
        "topic": "conflict_area",
        "document1_says": "version1",
        "document2_says": "version2",
        "resolution": "recommended_resolution"
      }
    ],
    "confidence_by_finding": {
      "finding": "confidence_level_with_justification"
    }
  }
}
```

### 4. Evidence Strength Assessment
Rate evidence strength for each finding:
- **Strong**: Multiple documents confirm with specific details
- **Medium**: Single document with clear evidence
- **Weak**: Implied or unclear evidence
- **Conflicting**: Documents contradict each other

### 5. Comprehensive Architecture View
Synthesize all documents into:
- Complete service inventory with confidence levels
- Validated architectural patterns
- Confirmed Multi-AZ setup
- Consolidated WAFR assessment
- Prioritized recommendations based on evidence strength

## Output Requirements
- Provide correlation confidence scores (0-100)
- Highlight any document conflicts with resolution suggestions
- Build evidence hierarchy (strongest to weakest findings)
- Generate consolidated architecture view
- Recommend additional documentation if needed

Perform cross-document correlation analysis:
"""
        
        return prompt.strip()
    
    def build_pillar_specific_prompt(self, pillar: str, context: Dict[str, Any]) -> str:
        """
        Build pillar-specific analysis prompt
        
        Args:
            pillar: WAFR pillar name
            context: Analysis context
            
        Returns:
            Pillar-focused analysis prompt
        """
        focus_areas = self.pillar_focus_areas.get(pillar, [])
        
        prompt = f"""
You are conducting a focused {pillar.replace('_', ' ').title()} analysis for the AWS Well-Architected Framework.

## {pillar.replace('_', ' ').title()} Analysis Focus
Analyze the architecture specifically for these areas:
{chr(10).join(f'- **{area.title()}**' for area in focus_areas)}

## Analysis Objectives
1. **Capability Assessment**: Evaluate current {pillar} capabilities
2. **Evidence-Based Scoring**: Provide specific evidence for scores
3. **Gap Identification**: Identify missing {pillar} practices
4. **Recommendation Prioritization**: Rank improvements by impact
5. **Implementation Guidance**: Provide specific next steps

## Scoring Framework
For each capability area, provide:

```json
{{
  "{pillar}_assessment": {{
    "capability_scores": [
      {{
        "capability": "capability_name",
        "score": 0-100,
        "evidence": ["specific_evidence_1", "specific_evidence_2"],
        "strengths": ["identified_strengths"],
        "gaps": ["identified_gaps"],
        "recommendations": ["specific_recommendations"]
      }}
    ],
    "overall_score": 0-100,
    "score_justification": "detailed_explanation",
    "priority_improvements": [
      {{
        "improvement": "improvement_description",
        "impact": "high/medium/low",
        "effort": "high/medium/low",
        "timeline": "suggested_timeline"
      }}
    ]
  }}
}}
```

## Evidence Requirements
- **Specific**: Reference exact configurations, services, or practices
- **Quantifiable**: Provide metrics where available
- **Actionable**: Link evidence to specific recommendations
- **Prioritized**: Rank by business impact and implementation effort

## {pillar.replace('_', ' ').title()}-Specific Considerations
{self._get_pillar_specific_guidance(pillar)}

Conduct focused {pillar} analysis:
"""
        
        return prompt.strip()
    
    def _build_pillar_analysis_section(self) -> str:
        """Build the pillar analysis section for prompts"""
        
        section = """
For each WAFR pillar, assess:

#### Operational Excellence
- Automation and orchestration evidence
- Monitoring and observability setup
- Deployment and change management practices
- Incident response capabilities

#### Security
- Identity and access management implementation
- Data protection mechanisms
- Infrastructure security controls
- Detective and protective controls

#### Reliability
- Fault tolerance and recovery mechanisms
- Multi-AZ and cross-region setup
- Backup and disaster recovery
- Capacity planning and scaling

#### Performance Efficiency
- Resource selection and optimization
- Monitoring and performance metrics
- Caching and content delivery
- Database and storage optimization

#### Cost Optimization
- Resource rightsizing evidence
- Reserved capacity utilization
- Cost monitoring and alerting
- Lifecycle management practices

#### Sustainability
- Resource efficiency patterns
- Regional optimization
- Workload optimization practices
- Development and deployment efficiency
"""
        
        return section.strip()
    
    def _get_pillar_specific_guidance(self, pillar: str) -> str:
        """Get pillar-specific analysis guidance"""
        
        guidance = {
            'operational_excellence': """
- Look for Infrastructure as Code (IaC) implementations
- Identify monitoring and alerting configurations
- Assess automation and orchestration tools
- Evaluate change management processes
- Check for operational runbooks and procedures
""",
            'security': """
- Verify IAM roles and policies implementation
- Check encryption at rest and in transit
- Assess network security controls (VPC, Security Groups, NACLs)
- Look for logging and monitoring security events
- Evaluate compliance and governance controls
""",
            'reliability': """
- Verify Multi-AZ deployment patterns
- Check backup and recovery mechanisms
- Assess auto-scaling and load balancing
- Look for circuit breaker and retry patterns
- Evaluate disaster recovery procedures
""",
            'performance_efficiency': """
- Assess resource types and sizing
- Check caching strategies (ElastiCache, CloudFront)
- Evaluate database performance optimizations
- Look for content delivery networks
- Assess monitoring and performance metrics
""",
            'cost_optimization': """
- Check for Reserved Instances and Savings Plans
- Assess resource rightsizing practices
- Look for lifecycle policies (S3, EBS)
- Evaluate cost monitoring and budgets
- Check for unused resource identification
""",
            'sustainability': """
- Assess region selection for carbon efficiency
- Look for resource optimization patterns
- Check for efficient development practices
- Evaluate workload optimization
- Assess data lifecycle management
"""
        }
        
        return guidance.get(pillar, "Focus on general Well-Architected principles.")
    
    def build_evidence_extraction_prompt(self, document_type: str) -> str:
        """Build prompt for extracting specific evidence from documents"""
        
        prompt = f"""
You are extracting specific evidence from a {document_type} document for Well-Architected Framework analysis.

## Evidence Extraction Objectives
1. **Precise Citations**: Extract exact text, configurations, or visual elements
2. **Contextual Information**: Provide surrounding context for each piece of evidence
3. **Categorization**: Organize evidence by WAFR pillar and capability
4. **Confidence Assessment**: Rate the reliability of each piece of evidence
5. **Cross-Reference Preparation**: Format evidence for correlation with other documents

## Extraction Framework

### 1. Service Evidence
```json
{{
  "service_evidence": [
    {{
      "service": "aws_service_name",
      "evidence_type": "configuration/mention/diagram",
      "exact_evidence": "precise_text_or_description",
      "context": "surrounding_information",
      "location": "document_section_or_page",
      "confidence": "high/medium/low",
      "pillar_relevance": ["relevant_pillars"]
    }}
  ]
}}
```

### 2. Configuration Evidence
```json
{{
  "configuration_evidence": [
    {{
      "component": "component_name",
      "configuration_detail": "specific_config",
      "evidence_text": "exact_text_found",
      "implications": "what_this_means_for_wafr",
      "confidence": "evidence_reliability"
    }}
  ]
}}
```

### 3. Pattern Evidence
```json
{{
  "pattern_evidence": [
    {{
      "pattern": "architectural_pattern",
      "evidence_description": "how_pattern_is_evidenced",
      "supporting_details": ["detail1", "detail2"],
      "wafr_benefits": "how_pattern_supports_wafr"
    }}
  ]
}}
```

## Evidence Quality Criteria
- **Specificity**: Exact quotes, precise configurations, clear visual elements
- **Verifiability**: Can be independently verified from the document
- **Relevance**: Directly relates to WAFR principles and practices
- **Completeness**: Sufficient detail for assessment and recommendations

Extract all relevant evidence from the {document_type} document:
"""
        
        return prompt.strip()
    
    def get_prompt_templates(self) -> Dict[str, str]:
        """Get all available prompt templates"""
        
        return {
            'architecture_analysis': 'Comprehensive architecture analysis with evidence-based findings',
            'vision_analysis': 'Specialized analysis for architecture diagrams and visual documentation',
            'document_correlation': 'Cross-document consistency and completeness analysis',
            'pillar_specific': 'Focused analysis for individual WAFR pillars',
            'evidence_extraction': 'Precise evidence extraction from documents'
        }