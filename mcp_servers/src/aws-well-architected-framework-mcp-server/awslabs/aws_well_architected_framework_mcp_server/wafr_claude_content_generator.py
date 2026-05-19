"""
WAFR Content Generator - Bedrock-Integrated Architecture

This module generates comprehensive WAFR content using Claude via AWS Bedrock
for AI-powered pillar analysis and architecture-specific insights.
"""

import logging
import json
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime

from .consts import get_aws_region

logger = logging.getLogger(__name__)


class WAFRClaudeContentGenerator:
    """
    Generate architecture-specific WAFR content using Claude via Bedrock.
    
    This class calls AWS Bedrock to generate rich, AI-powered pillar analysis
    with architecture-specific insights, detailed capability analysis, and
    actionable recommendations.
    """
    
    def __init__(self):
        """Initialize content generator with Bedrock client"""
        logger.info("Initializing WAFR content generator with Bedrock integration")
        try:
            # Get region from environment configuration
            # Configure with extended timeout for large content generation
            from botocore.config import Config
            bedrock_config = Config(
                read_timeout=120,  # 2 minutes for large responses
                connect_timeout=10,
                retries={'max_attempts': 2}
            )
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=get_aws_region(), config=bedrock_config)
            self.model_id = "us.anthropic.claude-sonnet-4-6"
            self.bedrock_available = True
            logger.info("Bedrock client initialized successfully")
        except Exception as e:
            logger.warning(f"Bedrock client initialization failed: {e}")
            self.bedrock_available = False
            self.bedrock_client = None

    def generate_architecture_specific_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive architecture-specific content for WAFR reports.
        
        This method calls Bedrock/Claude to generate rich, AI-powered pillar analysis
        with architecture-specific insights.
        
        Args:
            data: Assessment data including pillar scores, architecture analysis, etc.
            
        Returns:
            Enhanced data with comprehensive AI-generated content sections
        """
        logger.info("Generating comprehensive WAFR content with Bedrock AI integration")
        
        try:
            # Process and enhance the assessment data
            processed_data = self._process_assessment_data(data)
            
            # Try to generate AI-powered content via Bedrock
            if self.bedrock_available:
                logger.info("Calling Bedrock for AI-generated pillar analysis...")
                ai_content = self._generate_ai_pillar_content(processed_data)
                if ai_content:
                    # Merge AI content with processed data
                    enhanced_content = processed_data.copy()
                    enhanced_content.update(ai_content)
                    logger.info("AI-generated pillar content created successfully")
                    return enhanced_content
                else:
                    logger.warning("AI content generation returned empty, using fallback")
            
            # Fallback to template-based content if Bedrock unavailable
            logger.info("Using enhanced fallback content generation")
            enhanced_content = self._generate_enhanced_fallback_content(processed_data)
            
            logger.info("Architecture-specific content generated successfully")
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            # Return basic fallback content
            return self._generate_basic_fallback_content(data)
    
    def _generate_ai_pillar_content(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate AI-powered pillar analysis using Bedrock Claude."""
        try:
            pillar_assessments = data.get('pillar_assessments', {})
            architecture_data = data.get('architecture_data', {})
            document_analysis = data.get('document_analysis', architecture_data)
            
            # Extract architecture context
            services = document_analysis.get('identified_services', []) or document_analysis.get('aws_services', [])
            patterns = document_analysis.get('architectural_patterns', [])
            total_docs = document_analysis.get('total_documents', document_analysis.get('processed_documents', 0))
            insights = document_analysis.get('combined_insights', {})
            overall_score = data.get('overall_score', 0)
            
            # Build the comprehensive prompt
            prompt = self._build_pillar_analysis_prompt(
                pillar_assessments=pillar_assessments,
                services=services,
                patterns=patterns,
                total_docs=total_docs,
                insights=insights,
                overall_score=overall_score
            )
            
            # Call Bedrock
            response = self._call_bedrock(prompt)
            
            if response:
                # Parse the AI response into structured content
                return self._parse_ai_response(response, pillar_assessments, services)
            
            return None
            
        except Exception as e:
            logger.error(f"AI pillar content generation failed: {e}")
            return None
    
    def _build_pillar_analysis_prompt(
        self,
        pillar_assessments: Dict[str, Any],
        services: List[str],
        patterns: List[str],
        total_docs: int,
        insights: Dict[str, Any],
        overall_score: float
    ) -> str:
        """Build comprehensive prompt for pillar analysis."""
        
        services_str = ', '.join(services[:15]) if services else 'various AWS services'
        patterns_str = ', '.join(patterns[:5]) if patterns else 'standard cloud patterns'
        
        # Build pillar summary for context
        pillar_summary = []
        for pillar_name, assessment in pillar_assessments.items():
            score = assessment.get('score', 0)
            risk = assessment.get('risk_level', 'Unknown')
            caps = assessment.get('detected_capabilities', [])
            pillar_summary.append(f"- {pillar_name.replace('_', ' ').title()}: {score:.1f}% ({risk}), Capabilities: {', '.join(caps[:3])}")
        
        pillar_context = '\n'.join(pillar_summary)
        
        prompt = f"""You are an AWS Well-Architected Framework expert analyzing a cloud architecture assessment. Generate comprehensive, architecture-specific analysis for each pillar.

## Architecture Context
- Total Infrastructure Documents Analyzed: {total_docs}
- AWS Services Identified: {services_str}
- Architectural Patterns: {patterns_str}
- Overall WAFR Score: {overall_score:.1f}%
- Security Posture: {insights.get('security_posture', 'standard')}
- Operational Readiness: {insights.get('operational_readiness', 'standard')}
- Architecture Complexity: {insights.get('architecture_complexity', 'moderate')}

## Pillar Assessment Summary
{pillar_context}

## Your Task
For EACH of the 6 pillars (Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability), generate a detailed analysis in the following JSON format:

```json
{{
  "pillar_enhanced_content": {{
    "operational_excellence": {{
      "assessment_overview": "2-3 paragraph comprehensive assessment overview specific to this architecture, referencing actual services like {services[:3] if services else ['Lambda', 'DynamoDB', 'S3']}...",
      "capability_analysis": {{
        "excellent_capabilities": [
          {{
            "name": "Infrastructure as Code",
            "score": "92%",
            "details": [
              "Specific finding about CloudFormation usage in this architecture",
              "Specific finding about template organization",
              "Specific finding about parameter management"
            ]
          }}
        ],
        "needs_improvement": [
          {{
            "name": "Observability",
            "score": "68%",
            "gaps": [
              "Specific gap identified in monitoring",
              "Specific gap in alerting configuration"
            ]
          }}
        ]
      }},
      "detailed_findings": {{
        "compute": {{
          "strengths": ["Specific strength 1", "Specific strength 2"],
          "recommendations": ["Specific recommendation"]
        }},
        "storage": {{
          "strengths": ["Specific strength"],
          "recommendations": ["Specific recommendation"]
        }},
        "network": {{
          "strengths": ["Specific strength"],
          "recommendations": ["Specific recommendation"]
        }}
      }},
      "maturity_model": [
        {{"capability": "IaC", "current_level": "Advanced", "target_level": "Advanced", "gap": "On Target"}},
        {{"capability": "Observability", "current_level": "Intermediate", "target_level": "Advanced", "gap": "In Progress"}}
      ],
      "implementation_roadmap": {{
        "phase_1": {{"duration": "0-30 days", "focus": "Specific focus area", "activities": ["Activity 1", "Activity 2"]}},
        "phase_2": {{"duration": "30-90 days", "focus": "Specific focus area", "activities": ["Activity 1", "Activity 2"]}},
        "phase_3": {{"duration": "90+ days", "focus": "Specific focus area", "activities": ["Activity 1", "Activity 2"]}}
      }},
      "success_metrics": {{
        "current_score": "{pillar_assessments.get('operational_excellence', {}).get('score', 80):.1f}%",
        "target_score": "90%",
        "target_timeframe": "90 days",
        "key_metrics": ["Metric 1", "Metric 2", "Metric 3"]
      }}
    }},
    "security": {{ ... same structure ... }},
    "reliability": {{ ... same structure ... }},
    "performance_efficiency": {{ ... same structure ... }},
    "cost_optimization": {{ ... same structure ... }},
    "sustainability": {{ ... same structure ... }}
  }},
  "enhanced_executive_summary": {{
    "assessment_overview": "Comprehensive 2-3 paragraph executive overview of the entire architecture assessment...",
    "architecture_overview": "Detailed description of the architecture patterns and services...",
    "key_findings_summary": ["Key finding 1", "Key finding 2", "Key finding 3", "Key finding 4"],
    "business_impact": "Analysis of business impact and value of implementing recommendations..."
  }}
}}
```

IMPORTANT GUIDELINES:
1. Reference ACTUAL services from the architecture: {services_str}
2. Be SPECIFIC - avoid generic statements like "implement best practices"
3. Include QUANTITATIVE details where possible (percentages, counts, timeframes)
4. Tailor recommendations to the SPECIFIC architecture patterns: {patterns_str}
5. Ensure findings are ACTIONABLE with clear implementation steps
6. Consider service INTERDEPENDENCIES in your analysis
7. Provide REALISTIC timelines and effort estimates

Generate the complete JSON response with all 6 pillars fully populated."""

        return prompt
    
    def _call_bedrock(self, prompt: str) -> Optional[str]:
        """Call Bedrock Claude API."""
        import time
        start_time = time.time()
        try:
            logger.info(f"Calling Bedrock API (prompt: {len(prompt)} chars, max_tokens: 8000)...")
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "temperature": 0.3,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            elapsed = time.time() - start_time
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            
            if content and len(content) > 0:
                text = content[0].get('text', '')
                logger.info(f"Bedrock response received in {elapsed:.1f}s ({len(text)} chars)")
                return text
            
            logger.warning(f"Bedrock returned empty content after {elapsed:.1f}s")
            return None
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Bedrock API call failed after {elapsed:.1f}s: {e}")
            return None
    
    def _parse_ai_response(
        self, 
        response: str, 
        pillar_assessments: Dict[str, Any],
        services: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Parse AI response into structured content."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                parts = response.split('```')
                if len(parts) >= 2:
                    json_str = parts[1]
            
            # Clean up common JSON issues
            json_str = self._fix_json_string(json_str.strip())
            
            parsed = json.loads(json_str)
            
            # Validate structure
            if 'pillar_enhanced_content' in parsed:
                logger.info("Successfully parsed AI-generated pillar content")
                return parsed
            
            logger.warning("AI response missing expected structure")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Try to extract partial content
            return self._extract_partial_content(response, pillar_assessments, services)
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None
    
    def _fix_json_string(self, json_str: str) -> str:
        """Fix common JSON formatting issues from AI responses."""
        import re
        
        # Remove trailing commas before closing brackets/braces
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix unescaped quotes in strings (basic attempt)
        # This is tricky - only do simple fixes
        
        # Remove any text before the first { or after the last }
        first_brace = json_str.find('{')
        last_brace = json_str.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = json_str[first_brace:last_brace + 1]
        
        return json_str
    
    def _extract_partial_content(
        self, 
        response: str, 
        pillar_assessments: Dict[str, Any],
        services: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract partial content from malformed AI response."""
        logger.info("Attempting to extract partial content from AI response")
        
        try:
            import re
            
            # Try to extract individual pillar sections
            pillar_content = {}
            pillar_names = ['operational_excellence', 'security', 'reliability', 
                          'performance_efficiency', 'cost_optimization', 'sustainability']
            
            for pillar in pillar_names:
                # Look for assessment_overview text for each pillar
                pattern = rf'"{pillar}"[^{{]*\{{[^}}]*"assessment_overview":\s*"([^"]+)"'
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    overview = match.group(1)
                    # Clean up escaped characters
                    overview = overview.replace('\\n', ' ').replace('\\"', '"')
                    pillar_content[pillar] = {
                        'assessment_overview': overview,
                        'capability_analysis': {},
                        'detailed_findings': {},
                        'maturity_model': [],
                        'implementation_roadmap': {},
                        'success_metrics': {}
                    }
                    logger.info(f"Extracted partial content for {pillar}")
            
            if pillar_content:
                logger.info(f"Successfully extracted partial content for {len(pillar_content)} pillars")
                return {'pillar_enhanced_content': pillar_content}
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract partial content: {e}")
            return None

    def _process_assessment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure assessment data for content generation"""
        processed_data = data.copy()
        
        # Extract key metrics
        overall_score = data.get('overall_score', 0)
        pillar_assessments = data.get('pillar_assessments', {})
        # Handle both 'architecture_data' and 'document_analysis' keys
        architecture_data = data.get('architecture_data', {}) or data.get('document_analysis', {})
        
        # Add processed architecture analysis
        processed_data['architecture_analysis'] = self._analyze_architecture(architecture_data)
        
        # Add risk analysis
        processed_data['risk_analysis'] = self._analyze_risks(pillar_assessments)
        
        # Add assessment metadata
        processed_data['assessment_metadata'] = {
            'overall_score': overall_score,
            'assessment_date': datetime.now().isoformat(),
            'total_pillars': len(pillar_assessments),
            'high_risk_pillars': len([p for p in pillar_assessments.values() if p.get('risk_level') == 'High Risk'])
        }
        
        return processed_data

    def _analyze_architecture(self, architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architecture patterns and services"""
        patterns = architecture_data.get('architectural_patterns', [])
        # Handle both 'aws_services' and 'identified_services' keys
        services = architecture_data.get('aws_services', []) or architecture_data.get('identified_services', [])
        
        # Determine primary architecture type
        architecture_type = "Cloud Architecture"
        if any('serverless' in str(p).lower() for p in patterns):
            architecture_type = "Serverless Architecture"
        elif any('microservices' in str(p).lower() for p in patterns):
            architecture_type = "Microservices Architecture"
        elif any('container' in str(p).lower() for p in patterns):
            architecture_type = "Container-based Architecture"
        
        # Extract service names
        service_names = []
        for service in services:
            if isinstance(service, dict):
                item = service.get('item', '')
                if '**' in item:
                    # Extract service name from markdown format
                    service_name = item.split('**')[1] if '**' in item else item
                    service_names.append(service_name)
                else:
                    service_names.append(item)
            else:
                service_names.append(str(service))
        
        return {
            'architecture_type': architecture_type,
            'services_identified': service_names,
            'total_services_count': len(service_names),
            'patterns_detected': [str(p) for p in patterns]
        }

    def _analyze_risks(self, pillar_assessments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risks across pillars"""
        critical_issues = []
        medium_issues = []
        
        for pillar, assessment in pillar_assessments.items():
            risk_level = assessment.get('risk_level', 'Unknown')
            score = assessment.get('score', 0)
            
            risk_item = {
                'pillar': pillar,
                'score': score,
                'risk_level': risk_level
            }
            
            if risk_level == 'High Risk':
                critical_issues.append(risk_item)
            elif risk_level == 'Medium Risk':
                medium_issues.append(risk_item)
        
        return {
            'critical_priority_issues': critical_issues,
            'medium_priority_issues': medium_issues,
            'total_critical': len(critical_issues),
            'total_medium': len(medium_issues)
        }

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from text content"""
        try:
            lines = text.split('\n')
            section_content = []
            in_section = False
            
            for line in lines:
                if section_name.lower() in line.lower() and any(marker in line for marker in ['#', '##', '###', '1.', '2.', '3.']):
                    in_section = True
                    continue
                elif in_section and any(marker in line for marker in ['#', '##', '###', '1.', '2.', '3.']) and section_name.lower() not in line.lower():
                    break
                elif in_section:
                    section_content.append(line.strip())
            
            return '\n'.join(section_content).strip() or f"Analysis for {section_name} based on the architecture assessment."
            
        except Exception:
            return f"Analysis for {section_name} based on the architecture assessment."
    
    def _extract_bullet_points(self, text: str, section_name: str) -> List[str]:
        """Extract bullet points from a section"""
        try:
            section_text = self._extract_section(text, section_name)
            bullet_points = []
            
            for line in section_text.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    bullet_points.append(line[1:].strip())
            
            return bullet_points[:4] if bullet_points else [
                "Comprehensive assessment completed",
                "Architecture patterns identified",
                "Improvement opportunities discovered",
                "Action plan developed"
            ]
            
        except Exception:
            return [
                "Comprehensive assessment completed",
                "Architecture patterns identified", 
                "Improvement opportunities discovered",
                "Action plan developed"
            ]

    def _generate_basic_fallback_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic fallback content when processing fails"""
        overall_score = data.get('overall_score', 0)
        
        return {
            'executive_summary': {
                'overview': f"AWS Well-Architected Framework assessment completed with overall score of {overall_score:.1f}%.",
                'key_insights': "Assessment identifies areas for improvement across the six pillars.",
                'recommendations': "Implementation of recommended improvements will enhance architecture quality."
            },
            'conclusion': {
                'summary': "This assessment provides a roadmap for architectural improvements.",
                'next_steps': "Focus on high-priority recommendations for maximum impact."
            }
        }

    def _fallback_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback executive summary with architecture-specific insights"""
        architecture_type = data['architecture_analysis']['architecture_type']
        overall_score = data['assessment_metadata']['overall_score']
        services_count = data['architecture_analysis']['total_services_count']
        services = data['architecture_analysis']['services_identified']
        
        # Generate architecture-specific insights
        key_services = services[:5] if services else []
        service_list = ', '.join(key_services)
        
        # Architecture-specific assessment overview
        if 'serverless' in architecture_type.lower():
            assessment_overview = f"This comprehensive Well-Architected Framework assessment evaluates your {architecture_type} implementation across all six pillars. The assessment analyzed {services_count} AWS services including {service_list}, focusing on serverless best practices, event-driven patterns, and managed service optimization."
        elif 'microservices' in architecture_type.lower():
            assessment_overview = f"This Well-Architected assessment examines your {architecture_type} implementation using {services_count} AWS services. The evaluation covers service decomposition, inter-service communication, data consistency, and operational complexity across {service_list}."
        else:
            assessment_overview = f"Comprehensive Well-Architected Framework assessment completed for your {architecture_type} using {services_count} AWS services including {service_list}. Assessment evaluated all six pillars using enhanced capability-based scoring methodology."
        
        # Architecture-specific overview
        if 'serverless' in architecture_type.lower():
            architecture_overview = f"Your {architecture_type} leverages AWS managed services to minimize operational overhead while maximizing scalability. The implementation utilizes {services_count} services with emphasis on event-driven processing, automatic scaling, and pay-per-use pricing models."
        elif 'microservices' in architecture_type.lower():
            architecture_overview = f"The {architecture_type} architecture decomposes functionality into independently deployable services using {services_count} AWS components. This approach enables team autonomy, technology diversity, and independent scaling while requiring careful attention to service boundaries and data consistency."
        else:
            architecture_overview = f"The architecture implements a {architecture_type} pattern with {services_count} integrated AWS services. Current implementation demonstrates established cloud practices with opportunities for optimization across operational excellence, security, and cost efficiency."
        
        # Generate specific findings based on architecture type and score
        key_findings = []
        if overall_score >= 75:
            key_findings.append(f"Strong {architecture_type} implementation with {overall_score:.1f}% overall score")
            key_findings.append(f"Well-integrated service architecture using {services_count} AWS services")
            key_findings.append("Solid foundation with targeted optimization opportunities identified")
        elif overall_score >= 60:
            key_findings.append(f"Developing {architecture_type} with {overall_score:.1f}% score showing room for improvement")
            key_findings.append(f"Good service selection across {services_count} AWS components")
            key_findings.append("Key enhancement areas identified for operational excellence")
        else:
            key_findings.append(f"Early-stage {architecture_type} implementation requiring significant improvements")
            key_findings.append(f"Basic service integration across {services_count} AWS services")
            key_findings.append("Critical gaps identified requiring immediate attention")
        
        key_findings.append("Enhanced capability-based assessment methodology applied")
        
        # Architecture-specific business impact
        if 'serverless' in architecture_type.lower():
            business_impact = f"The assessment reveals opportunities to optimize your {architecture_type} for improved cost efficiency, enhanced security, and better operational excellence. Serverless-specific recommendations focus on function optimization, event processing efficiency, and managed service integration to reduce operational overhead while improving scalability."
        elif 'microservices' in architecture_type.lower():
            business_impact = f"Your {architecture_type} assessment identifies opportunities to improve service boundaries, enhance inter-service communication, and optimize operational complexity. Recommendations target service autonomy, data consistency, monitoring, and deployment automation to realize the full benefits of microservices architecture."
        else:
            business_impact = f"The assessment reveals significant opportunities to enhance your {architecture_type} implementation. Recommended improvements will increase operational efficiency, reduce costs, strengthen security posture, and improve overall system reliability and performance."
        
        return {
            'assessment_overview': assessment_overview,
            'architecture_overview': architecture_overview,
            'key_findings_summary': key_findings,
            'business_impact': business_impact
        }
    
    def _fallback_architecture_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback architecture analysis with detailed service insights"""
        architecture_type = data['architecture_analysis']['architecture_type']
        services = data['architecture_analysis']['services_identified']
        patterns = data['architecture_analysis'].get('patterns_detected', [])
        
        # Analyze service categories
        compute_services = [s for s in services if any(compute in s for compute in ['Lambda', 'EC2', 'ECS', 'Fargate', 'Batch'])]
        storage_services = [s for s in services if any(storage in s for storage in ['S3', 'DynamoDB', 'RDS', 'ElastiCache', 'EFS'])]
        networking_services = [s for s in services if any(network in s for network in ['CloudFront', 'API Gateway', 'VPC', 'Route53', 'ALB', 'NLB'])]
        monitoring_services = [s for s in services if any(monitor in s for monitor in ['CloudWatch', 'X-Ray', 'CloudTrail'])]
        
        # Generate detailed services analysis
        services_analysis_parts = []
        services_analysis_parts.append(f"Your {architecture_type} implementation leverages {len(services)} AWS services strategically distributed across multiple categories:")
        
        if compute_services:
            services_analysis_parts.append(f"**Compute Layer**: {', '.join(compute_services)} providing scalable processing capabilities")
        if storage_services:
            services_analysis_parts.append(f"**Data Layer**: {', '.join(storage_services)} handling data persistence and caching")
        if networking_services:
            services_analysis_parts.append(f"**Network Layer**: {', '.join(networking_services)} managing traffic routing and content delivery")
        if monitoring_services:
            services_analysis_parts.append(f"**Observability**: {', '.join(monitoring_services)} enabling monitoring and troubleshooting")
        
        services_analysis_parts.append(f"This service composition aligns well with {architecture_type} principles, providing the foundation for scalable, resilient cloud operations.")
        
        # Generate patterns analysis based on architecture type
        if 'serverless' in architecture_type.lower():
            patterns_analysis = f"The architecture demonstrates strong serverless patterns with event-driven processing, managed services, and automatic scaling. Key patterns include: {', '.join(patterns) if patterns else 'Function-as-a-Service, Event-driven Architecture, Managed Services Integration'}. This approach minimizes operational overhead while maximizing elasticity and cost efficiency."
        elif 'microservices' in architecture_type.lower():
            patterns_analysis = f"The microservices implementation shows service decomposition with independent deployment capabilities. Identified patterns: {', '.join(patterns) if patterns else 'Service Decomposition, API Gateway Pattern, Database per Service'}. The architecture enables team autonomy and technology diversity while requiring careful attention to service boundaries and data consistency."
        else:
            patterns_analysis = f"The architecture follows established cloud patterns: {', '.join(patterns) if patterns else 'Multi-tier Architecture, Load Balancing, Auto Scaling'}. The implementation demonstrates good separation of concerns with appropriate service selection for {architecture_type} requirements."
        
        # Generate current state assessment
        if len(services) >= 10:
            complexity_note = "The architecture shows significant complexity with multiple integrated services, requiring robust operational procedures and monitoring."
        elif len(services) >= 5:
            complexity_note = "The architecture demonstrates moderate complexity with well-balanced service integration."
        else:
            complexity_note = "The architecture maintains simplicity with focused service selection."
        
        current_state_assessment = f"Current {architecture_type} implementation demonstrates {complexity_note} The assessment identifies optimization opportunities across all six Well-Architected pillars, with particular focus on operational excellence automation, security hardening, reliability improvements, performance optimization, cost management, and sustainability practices. The foundation is solid with clear paths for enhancement."
        
        return {
            'services_analysis': ' '.join(services_analysis_parts),
            'patterns_analysis': patterns_analysis,
            'current_state_assessment': current_state_assessment
        }
    
    def _fallback_risk_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback risk analysis with architecture-specific insights"""
        critical_risks = data['risk_analysis']['critical_priority_issues']
        medium_risks = data['risk_analysis']['medium_priority_issues']
        architecture_type = data['architecture_analysis']['architecture_type']
        
        # Analyze risk distribution by pillar
        critical_pillars = [risk['pillar'] for risk in critical_risks]
        medium_pillars = [risk['pillar'] for risk in medium_risks]
        
        # Generate critical issues analysis
        if critical_risks:
            critical_pillar_summary = ', '.join(set(critical_pillars))
            critical_issues_analysis = f"Assessment identified {len(critical_risks)} critical priority issues requiring immediate attention. These issues span {critical_pillar_summary} pillars and pose significant risks to your {architecture_type} implementation. "
            
            if 'security' in critical_pillars:
                critical_issues_analysis += "Security gaps require urgent remediation to prevent potential breaches and ensure compliance. "
            if 'cost_optimization' in critical_pillars:
                critical_issues_analysis += "Cost optimization issues are leading to unnecessary expenses and resource waste. "
            if 'reliability' in critical_pillars:
                critical_issues_analysis += "Reliability concerns could impact system availability and user experience. "
                
            critical_issues_analysis += f"These critical findings are particularly important for {architecture_type} implementations where rapid scaling and distributed components amplify risk impact."
        else:
            critical_issues_analysis = f"No critical priority issues identified in your {architecture_type} implementation, indicating a strong foundational security and operational posture."
        
        # Generate medium issues analysis
        if medium_risks:
            medium_pillar_summary = ', '.join(set(medium_pillars))
            medium_issues_analysis = f"{len(medium_risks)} medium priority issues were identified across {medium_pillar_summary} pillars that should be addressed within 3-6 months. "
            
            if 'performance_efficiency' in medium_pillars:
                medium_issues_analysis += f"Performance optimization opportunities exist to enhance {architecture_type} responsiveness and throughput. "
            if 'operational_excellence' in medium_pillars:
                medium_issues_analysis += "Operational procedures can be improved through better automation and monitoring. "
            if 'sustainability' in medium_pillars:
                medium_issues_analysis += "Sustainability improvements will reduce environmental impact and operational costs. "
                
            medium_issues_analysis += f"These improvements will enhance the maturity and efficiency of your {architecture_type} implementation."
        else:
            medium_issues_analysis = f"No medium priority issues identified, indicating well-optimized {architecture_type} implementation across most areas."
        
        # Generate mitigation summary
        total_issues = len(critical_risks) + len(medium_risks)
        if total_issues > 0:
            mitigation_summary = f"Risk mitigation for your {architecture_type} should follow a priority-based approach: Critical Priority addresses {len(critical_risks)} critical issues, Medium Priority tackles {len(medium_risks)} medium priority improvements. "
            
            if 'serverless' in architecture_type.lower():
                mitigation_summary += "Focus on function-level security, event processing optimization, and managed service configuration. "
            elif 'microservices' in architecture_type.lower():
                mitigation_summary += "Prioritize service-to-service security, distributed monitoring, and data consistency patterns. "
            
            mitigation_summary += "This systematic approach ensures sustainable improvement without disrupting current operations."
        else:
            mitigation_summary = f"Your {architecture_type} demonstrates excellent risk management with no critical issues identified. Continue monitoring and periodic reassessment to maintain this strong posture."
        
        # Generate business impact assessment
        if total_issues > 3:
            impact_level = "significant"
        elif total_issues > 0:
            impact_level = "moderate"
        else:
            impact_level = "minimal"
            
        business_impact_assessment = f"The identified risks present {impact_level} business impact on your {architecture_type} operations. "
        
        if critical_risks:
            business_impact_assessment += f"Critical issues could affect system availability, security compliance, and operational costs. "
        if medium_risks:
            business_impact_assessment += f"Medium priority issues impact operational efficiency and long-term sustainability. "
            
        business_impact_assessment += f"Addressing these risks will improve business resilience, reduce operational overhead, and enhance the competitive advantages of your {architecture_type} implementation."
        
        return {
            'critical_issues_analysis': critical_issues_analysis,
            'medium_issues_analysis': medium_issues_analysis,
            'mitigation_summary': mitigation_summary,
            'business_impact_assessment': business_impact_assessment
        }
    
    def _fallback_action_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback action plan"""
        return {
            'immediate_actions_detailed': "Focus on critical security configurations, implement basic monitoring and alerting, establish incident response procedures, and address any high-risk operational gaps identified in the assessment.",
            'short_term_actions_detailed': "Implement performance optimization measures, enhance cost monitoring and optimization, improve reliability through redundancy and backup strategies, and establish comprehensive operational procedures.",
            'long_term_actions_detailed': "Achieve architectural excellence through advanced automation, implement comprehensive sustainability measures, establish continuous improvement processes, and optimize for long-term operational efficiency."
        }
    
    def _fallback_expected_benefits(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback expected benefits"""
        return {
            'cost_optimization_benefits': "Implementation of recommended cost optimization measures will reduce operational expenses through right-sizing, automation, and efficient resource utilization. Expected cost savings of 15-30% achievable.",
            'operational_benefits': "Enhanced operational procedures will improve system reliability, reduce manual intervention, and increase automation. This leads to improved uptime, faster incident resolution, and reduced operational overhead.",
            'security_benefits': "Security improvements will strengthen overall security posture, reduce risk exposure, and improve compliance with security best practices. Enhanced monitoring and incident response capabilities.",
            'performance_benefits': "Performance optimizations will improve system responsiveness, reduce latency, and enhance user experience. Better resource utilization and improved scalability characteristics."
        }
    
    def _fallback_next_steps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback next steps"""
        return {
            'immediate_next_steps': "Begin with critical security and operational improvements identified in the assessment. Establish monitoring and alerting systems. Create implementation timeline for recommended changes.",
            'support_resources': "Utilize AWS documentation, best practice guides, and architectural patterns. Consider AWS Professional Services or certified partners for complex implementations. Leverage AWS training and certification programs.",
            'success_criteria': "Track improvement in pillar scores, monitor operational metrics, measure cost optimization achievements, and assess security posture improvements. Regular reassessment recommended every 6 months.",
            'ongoing_monitoring': "Implement continuous monitoring of key metrics, regular review of architectural decisions, and periodic Well-Architected Framework assessments to ensure continued improvement and optimization."
        }

    def _fallback_pillar_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback pillar analysis"""
        pillar_assessments = data.get('pillar_assessments', {})
        analysis = {}
        
        for pillar, assessment in pillar_assessments.items():
            pillar_name = pillar.replace('_', ' ').title()
            score = assessment.get('score', 0)
            risk_level = assessment.get('risk_level', 'Unknown')
            capabilities = assessment.get('detected_capabilities', [])
            
            analysis[pillar] = {
                'name': pillar_name,
                'score': score,
                'risk_level': risk_level,
                'capabilities_count': len(capabilities),
                'analysis': f"{pillar_name} pillar shows {score:.1f}% compliance with {risk_level.lower()} risk level. {len(capabilities)} capabilities detected including {', '.join(capabilities[:3])}{'...' if len(capabilities) > 3 else ''}."
            }
        
        return analysis

    def _fallback_critical_findings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback critical findings"""
        high_priority_actions = data.get('high_priority_actions', [])
        critical_actions = [action for action in high_priority_actions if action.get('priority') == 'critical']
        
        findings = []
        for action in critical_actions[:5]:  # Top 5 critical findings
            findings.append({
                'title': action.get('title', 'Critical Finding'),
                'description': action.get('description', 'Critical issue requiring immediate attention'),
                'impact': 'High business risk if not addressed within 30 days',
                'category': 'Critical Priority'
            })
        
        return {
            'critical_findings': findings,
            'summary': f"Identified {len(findings)} critical findings requiring immediate remediation to ensure system security and operational excellence."
        }

    def _fallback_implementation_roadmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate architecture-specific fallback implementation roadmap matching template structure.
        
        This function creates roadmap content that references the actual detected
        services and architecture type rather than using generic boilerplate.
        """
        high_priority_actions = data.get('high_priority_actions', [])
        pillar_assessments = data.get('pillar_assessments', {})
        document_analysis = data.get('document_analysis', {})
        architecture_type = data.get('architecture_analysis', {}).get('architecture_type', 'cloud architecture')
        
        # Get detected services for architecture-specific recommendations
        services = document_analysis.get('aws_services', []) or document_analysis.get('identified_services', [])
        service_names = []
        for svc in services[:5]:
            if isinstance(svc, dict):
                name = svc.get('name', svc.get('item', ''))
            else:
                name = str(svc)
            # Clean up the name
            if '**' in name:
                import re
                match = re.search(r'\*\*([^*]+)\*\*', name)
                name = match.group(1) if match else name
            name = name.split(' - ')[0].strip()
            if name:
                service_names.append(name)
        
        services_text = ', '.join(service_names[:3]) if service_names else 'AWS services'
        
        # Get critical and medium priority actions
        critical_actions = [action for action in high_priority_actions if action.get('priority') == 'critical']
        medium_actions = [action for action in high_priority_actions if action.get('priority') == 'medium']
        
        # Identify priority pillars based on risk levels
        high_risk_pillars = [pillar for pillar, assessment in pillar_assessments.items() 
                           if assessment.get('risk_level') == 'High Risk']
        medium_risk_pillars = [pillar for pillar, assessment in pillar_assessments.items() 
                             if assessment.get('risk_level') == 'Medium Risk']
        
        # Generate architecture-specific activities
        phase_1_activities = [
            action.get('description', action.get('title', 'Critical improvement'))
            for action in critical_actions[:4]
        ]
        if not phase_1_activities:
            phase_1_activities = [
                f'Review {services_text} security configurations',
                f'Implement monitoring and alerting for {architecture_type}',
                f'Configure backup and recovery for critical {services_text} resources',
                f'Establish incident response procedures for {architecture_type}'
            ]
        
        phase_2_activities = [
            action.get('description', action.get('title', 'Performance improvement'))
            for action in medium_actions[:4]
        ]
        if not phase_2_activities:
            phase_2_activities = [
                f'Optimize {services_text} resource utilization',
                f'Implement caching strategies for {architecture_type}',
                f'Enhance {services_text} performance metrics',
                f'Establish cost optimization for {services_text}'
            ]
        
        return {
            'phase_1_foundation': {
                'duration': '0-30 days',
                'focus': f'Address critical gaps in {architecture_type} using {services_text}',
                'priority_pillars': high_risk_pillars[:3] if high_risk_pillars else ['security', 'operational_excellence'],
                'key_activities': phase_1_activities
            },
            'phase_2_optimization': {
                'duration': '1-3 months',
                'focus': f'Optimize {architecture_type} performance and cost efficiency',
                'priority_pillars': medium_risk_pillars[:3] if medium_risk_pillars else ['performance_efficiency', 'cost_optimization'],
                'key_activities': phase_2_activities
            },
            'phase_3_excellence': {
                'duration': '3-12 months',
                'focus': f'Achieve architectural excellence for {architecture_type}',
                'priority_pillars': ['sustainability', 'operational_excellence', 'reliability'],
                'key_activities': [
                    f'Establish continuous improvement processes for {services_text}',
                    f'Implement advanced automation for {architecture_type}',
                    f'Explore emerging AWS capabilities for {architecture_type}',
                    'Achieve full Well-Architected compliance and optimization'
                ]
            }
        }

    def _fallback_conclusion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback conclusion"""
        overall_score = data.get('overall_score', 0)
        high_priority_actions = data.get('high_priority_actions', [])
        architecture_type = data.get('architecture_analysis', {}).get('architecture_type', 'cloud architecture')
        
        if overall_score >= 80:
            assessment_summary = f"Your {architecture_type} demonstrates excellent Well-Architected compliance with a {overall_score:.1f}% overall score."
        elif overall_score >= 60:
            assessment_summary = f"Your {architecture_type} shows good foundation with {overall_score:.1f}% compliance and clear optimization opportunities."
        else:
            assessment_summary = f"Your {architecture_type} requires significant improvements to achieve Well-Architected best practices, currently at {overall_score:.1f}%."
        
        return {
            'assessment_summary': assessment_summary,
            'key_takeaways': [
                f"Comprehensive assessment completed across all six Well-Architected pillars",
                f"{len(high_priority_actions)} priority actions identified for implementation",
                f"Clear roadmap provided for achieving architectural excellence",
                f"Expected benefits include improved security, performance, and cost optimization"
            ],
            'success_factors': "Success depends on systematic implementation of recommendations, regular monitoring of progress, and continuous improvement practices."
        }

    def _fallback_success_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback success metrics."""
        return {
            'technical_metrics': [
                "System uptime and availability improvements",
                "Response time and performance optimizations", 
                "Security incident reduction",
                "Cost optimization achievements"
            ],
            'business_metrics': [
                "Operational efficiency gains",
                "Risk reduction measurements",
                "Compliance improvement tracking",
                "Customer satisfaction metrics"
            ],
            'monitoring_approach': "Establish baseline metrics, implement continuous monitoring, and conduct regular assessments to track progress against Well-Architected Framework principles."
        }

    def _generate_enhanced_fallback_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive enhanced fallback content with architecture-specific pillar narratives"""
        logger.info("Generating enhanced fallback content with comprehensive sections")
        
        # Ensure data is processed first (adds architecture_analysis, assessment_metadata, etc.)
        if 'architecture_analysis' not in data:
            data = self._process_assessment_data(data)
        
        enhanced_content = data.copy()
        
        # Generate all required sections with rich content
        enhanced_content.update({
            'executive_summary': self._fallback_executive_summary(data),
            'architecture_analysis_detailed': self._fallback_architecture_analysis(data),
            'risk_analysis_detailed': self._fallback_risk_analysis(data),
            'action_plan_detailed': self._fallback_action_plan(data),
            'expected_benefits_detailed': self._fallback_expected_benefits(data),
            'next_steps_detailed': self._fallback_next_steps(data),
            'success_metrics': self._fallback_success_metrics(data),
            
            # Additional enterprise-grade sections
            'critical_findings': self._fallback_critical_findings(data),
            'implementation_roadmap': self._fallback_implementation_roadmap(data),
            'cost_analysis': self._generate_cost_analysis(data),
            'business_impact': self._generate_business_impact(data)
        })
        
        # CRITICAL: Generate architecture-specific pillar content
        pillar_content = self._generate_pillar_enhanced_content(data)
        enhanced_content['pillar_enhanced_content'] = pillar_content
        logger.info(f"CONTENT_GEN: Generated pillar_enhanced_content for {len(pillar_content)} pillars: {list(pillar_content.keys())}")
        
        return enhanced_content
    
    def _generate_pillar_enhanced_content(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Generate architecture-specific enhanced content for each pillar."""
        logger.info("Generating architecture-specific pillar content")
        
        pillar_assessments = data.get('pillar_assessments', {})
        architecture_data = data.get('architecture_data', {})
        document_analysis = data.get('document_analysis', architecture_data)
        
        # Extract architecture details
        services = document_analysis.get('identified_services', []) or document_analysis.get('aws_services', [])
        patterns = document_analysis.get('architectural_patterns', [])
        total_docs = document_analysis.get('total_documents', document_analysis.get('processed_documents', 0))
        insights = document_analysis.get('combined_insights', {})
        
        pillar_content = {}
        
        for pillar_name, assessment in pillar_assessments.items():
            score = assessment.get('score', 70)
            detected_caps = assessment.get('detected_capabilities', [])
            risk_level = assessment.get('risk_level', 'Medium Risk')
            recommendations = assessment.get('recommendations', [])
            
            # Generate pillar-specific content based on architecture
            pillar_content[pillar_name] = self._generate_single_pillar_content(
                pillar_name=pillar_name,
                score=score,
                detected_caps=detected_caps,
                risk_level=risk_level,
                recommendations=recommendations,
                services=services,
                patterns=patterns,
                total_docs=total_docs,
                insights=insights
            )
        
        return pillar_content
    
    def _generate_single_pillar_content(
        self, 
        pillar_name: str, 
        score: float, 
        detected_caps: List[str],
        risk_level: str,
        recommendations: List[Dict],
        services: List[str],
        patterns: List[str],
        total_docs: int,
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive content for a single pillar."""
        
        pillar_display = pillar_name.replace('_', ' ').title()
        
        # Determine performance level
        if score >= 90:
            perf_level = "Excellent"
            perf_desc = "exceeds AWS best practices"
        elif score >= 80:
            perf_level = "Strong"
            perf_desc = "aligns well with AWS best practices"
        elif score >= 70:
            perf_level = "Good"
            perf_desc = "meets most AWS best practices with room for optimization"
        elif score >= 60:
            perf_level = "Moderate"
            perf_desc = "requires targeted improvements"
        else:
            perf_level = "Needs Improvement"
            perf_desc = "requires significant attention"
        
        # Map services to pillar relevance
        pillar_service_mapping = {
            'security': ['Cognito', 'KMS', 'WAF', 'Secrets Manager', 'IAM', 'Certificate Manager', 'VPC'],
            'reliability': ['Route 53', 'Auto Scaling', 'CloudWatch', 'DynamoDB', 'ElastiCache', 'Application Load Balancer'],
            'performance_efficiency': ['CloudFront', 'ElastiCache', 'Auto Scaling', 'EC2', 'DynamoDB', 'Application Load Balancer'],
            'cost_optimization': ['Auto Scaling', 'S3', 'DynamoDB', 'EC2', 'CloudFront', 'ElastiCache'],
            'operational_excellence': ['CloudFormation', 'CloudWatch', 'Systems Manager', 'Auto Scaling'],
            'sustainability': ['Auto Scaling', 'CloudFront', 'S3', 'DynamoDB', 'EC2']
        }
        
        relevant_services = [s for s in services if s in pillar_service_mapping.get(pillar_name, [])]
        if not relevant_services:
            relevant_services = services[:5]  # Fallback to first 5 services
        
        # Generate assessment overview
        assessment_overview = self._generate_pillar_assessment_overview(
            pillar_display, score, perf_level, perf_desc, 
            detected_caps, relevant_services, total_docs, patterns
        )
        
        # Generate capability analysis
        capability_analysis = self._generate_capability_analysis(
            pillar_name, score, detected_caps, relevant_services, insights
        )
        
        # Generate detailed findings by service
        detailed_findings = self._generate_detailed_findings(
            pillar_name, score, relevant_services, detected_caps
        )
        
        # Generate maturity model
        maturity_model = self._generate_maturity_model(
            pillar_name, score, detected_caps
        )
        
        # Generate implementation roadmap
        implementation_roadmap = self._generate_pillar_roadmap(
            pillar_name, score, recommendations, relevant_services
        )
        
        # Generate success metrics
        success_metrics = self._generate_pillar_success_metrics(
            pillar_name, score
        )
        
        result = {
            'assessment_overview': assessment_overview,
            'capability_analysis': capability_analysis,
            'detailed_findings': detailed_findings,
            'maturity_model': maturity_model,
            'implementation_roadmap': implementation_roadmap,
            'success_metrics': success_metrics,
            'relevant_services': relevant_services,
            'performance_level': perf_level
        }
        logger.info(f"PILLAR_CONTENT_GEN: {pillar_name} - maturity_model: {len(maturity_model)} items, detailed_findings: {len(detailed_findings)} keys, roadmap: {len(implementation_roadmap)} keys")
        return result
    
    def _generate_pillar_assessment_overview(
        self, pillar_display: str, score: float, perf_level: str, perf_desc: str,
        detected_caps: List[str], services: List[str], total_docs: int, patterns: List[str]
    ) -> str:
        """Generate architecture-specific assessment overview for a pillar."""
        
        services_str = ', '.join(services[:5])
        caps_str = ', '.join([c.replace('_', ' ').title() for c in detected_caps[:4]])
        patterns_str = ', '.join(patterns[:3]) if patterns else 'standard cloud patterns'
        
        overview = (
            f"The {pillar_display} assessment analyzed {total_docs} infrastructure documents "
            f"and identified {len(services)} relevant AWS services including {services_str}. "
            f"With a score of {score:.1f}%, this pillar demonstrates {perf_level.lower()} performance that {perf_desc}. "
            f"Key capabilities detected include {caps_str}. "
            f"The architecture implements {patterns_str}, providing a solid foundation for {pillar_display.lower()} practices."
        )
        
        return overview
    
    def _generate_capability_analysis(
        self, pillar_name: str, score: float, detected_caps: List[str], 
        services: List[str], insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed capability analysis with architecture-specific details."""
        
        # Define capability details based on pillar and detected services
        capability_details = {
            'security': {
                'encryption': {
                    'services': ['KMS', 'S3', 'DynamoDB'],
                    'details': [
                        'KMS Customer Managed Keys (CMK) configured for data encryption',
                        'S3 bucket encryption enabled with server-side encryption',
                        'DynamoDB encryption at rest using AWS managed keys',
                        'TLS 1.2+ enforced for data in transit'
                    ]
                },
                'identity_access': {
                    'services': ['Cognito', 'IAM'],
                    'details': [
                        'Cognito User Pools configured for authentication',
                        'IAM roles with least-privilege access policies',
                        'Multi-factor authentication available for user accounts',
                        'Service-linked roles for AWS service integration'
                    ]
                },
                'network_security': {
                    'services': ['VPC', 'WAF', 'Security Groups'],
                    'details': [
                        'VPC with private and public subnet segregation',
                        'WAF rules protecting against common web exploits',
                        'Security groups with restrictive inbound rules',
                        'VPC endpoints for private AWS service access'
                    ]
                },
                'monitoring_detection': {
                    'services': ['CloudWatch', 'CloudTrail'],
                    'details': [
                        'CloudWatch alarms for security metrics',
                        'CloudTrail logging for API activity audit',
                        'Log retention configured for compliance requirements'
                    ]
                },
                'data_protection': {
                    'services': ['Secrets Manager', 'S3'],
                    'details': [
                        'Secrets Manager for secure credential storage',
                        'S3 bucket policies restricting public access',
                        'Data classification and handling procedures'
                    ]
                }
            },
            'reliability': {
                'redundancy': {
                    'services': ['Route 53', 'Application Load Balancer'],
                    'details': [
                        'Multi-AZ deployment across availability zones',
                        'Route 53 health checks with automatic failover',
                        'Application Load Balancer distributing traffic across targets'
                    ]
                },
                'backup_recovery': {
                    'services': ['DynamoDB', 'S3'],
                    'details': [
                        'DynamoDB point-in-time recovery enabled',
                        'S3 versioning for object recovery',
                        'Automated backup schedules configured'
                    ]
                },
                'monitoring_alerting': {
                    'services': ['CloudWatch'],
                    'details': [
                        'CloudWatch dashboards for system health visibility',
                        'Automated alerting for critical metrics',
                        'Log aggregation and analysis capabilities'
                    ]
                },
                'scaling': {
                    'services': ['Auto Scaling', 'EC2'],
                    'details': [
                        'Auto Scaling groups with dynamic scaling policies',
                        'Target tracking scaling for optimal capacity',
                        'Scheduled scaling for predictable workloads'
                    ]
                },
                'fault_tolerance': {
                    'services': ['ElastiCache', 'DynamoDB'],
                    'details': [
                        'ElastiCache Redis cluster with replication',
                        'DynamoDB global tables for multi-region resilience',
                        'Circuit breaker patterns for service isolation'
                    ]
                }
            },
            'performance_efficiency': {
                'caching': {
                    'services': ['ElastiCache', 'CloudFront'],
                    'details': [
                        'ElastiCache Redis for application-level caching',
                        'CloudFront edge caching for static content',
                        'Cache invalidation strategies implemented'
                    ]
                },
                'compute_optimization': {
                    'services': ['EC2', 'Auto Scaling'],
                    'details': [
                        'Right-sized EC2 instances for workload requirements',
                        'Graviton-based instances for cost-performance optimization',
                        'Auto Scaling for demand-based capacity'
                    ]
                },
                'content_delivery': {
                    'services': ['CloudFront', 'S3'],
                    'details': [
                        'CloudFront CDN for global content distribution',
                        'S3 static website hosting for frontend assets',
                        'Edge locations optimized for user proximity'
                    ]
                },
                'database_optimization': {
                    'services': ['DynamoDB', 'ElastiCache'],
                    'details': [
                        'DynamoDB on-demand capacity for variable workloads',
                        'Read replicas for query distribution',
                        'Index optimization for query performance'
                    ]
                },
                'resource_selection': {
                    'services': ['EC2', 'DynamoDB'],
                    'details': [
                        'Instance types selected for workload characteristics',
                        'Managed services reducing operational overhead',
                        'Serverless options evaluated for appropriate use cases'
                    ]
                }
            },
            'cost_optimization': {
                'resource_optimization': {
                    'services': ['Auto Scaling', 'EC2'],
                    'details': [
                        'Auto Scaling preventing over-provisioning',
                        'Right-sizing recommendations implemented',
                        'Unused resource identification and cleanup'
                    ]
                },
                'pricing_models': {
                    'services': ['EC2', 'DynamoDB'],
                    'details': [
                        'Reserved capacity evaluation for steady-state workloads',
                        'Savings Plans assessment for compute usage',
                        'Spot instances for fault-tolerant workloads'
                    ]
                },
                'storage_optimization': {
                    'services': ['S3', 'DynamoDB'],
                    'details': [
                        'S3 lifecycle policies for data tiering',
                        'Intelligent-Tiering for unpredictable access patterns',
                        'DynamoDB capacity mode optimization'
                    ]
                },
                'managed_services': {
                    'services': ['DynamoDB', 'ElastiCache', 'Cognito'],
                    'details': [
                        'Managed services reducing operational costs',
                        'Serverless options eliminating idle capacity costs',
                        'Pay-per-use pricing for variable workloads'
                    ]
                },
                'cost_monitoring': {
                    'services': ['CloudWatch'],
                    'details': [
                        'Cost allocation tags for resource tracking',
                        'Budget alerts for spending thresholds',
                        'Cost anomaly detection enabled'
                    ]
                }
            },
            'operational_excellence': {
                'observability': {
                    'services': ['CloudWatch', 'CloudTrail'],
                    'details': [
                        'Centralized logging with CloudWatch Logs',
                        'Custom metrics for application monitoring',
                        'Distributed tracing capabilities'
                    ]
                },
                'infrastructure_as_code': {
                    'services': ['CloudFormation'],
                    'details': [
                        f'CloudFormation templates for infrastructure provisioning',
                        'Version-controlled infrastructure definitions',
                        'Parameterized templates for environment consistency'
                    ]
                },
                'deployment_automation': {
                    'services': ['CloudFormation', 'Systems Manager'],
                    'details': [
                        'Automated deployment pipelines',
                        'Blue-green deployment capabilities',
                        'Rollback procedures documented'
                    ]
                },
                'incident_response': {
                    'services': ['CloudWatch', 'Systems Manager'],
                    'details': [
                        'Automated alerting for incident detection',
                        'Runbook documentation for common issues',
                        'Escalation procedures defined'
                    ]
                },
                'runbook_automation': {
                    'services': ['Systems Manager'],
                    'details': [
                        'Systems Manager Automation documents',
                        'Self-healing capabilities for common failures',
                        'Operational procedures documented'
                    ]
                }
            },
            'sustainability': {
                'managed_services': {
                    'services': ['DynamoDB', 'S3', 'Cognito'],
                    'details': [
                        'Managed services with optimized resource utilization',
                        'Shared infrastructure reducing per-customer footprint',
                        'AWS-managed efficiency improvements'
                    ]
                },
                'efficient_compute': {
                    'services': ['EC2', 'Auto Scaling'],
                    'details': [
                        'Graviton processors for improved efficiency',
                        'Auto Scaling minimizing idle resources',
                        'Right-sized instances reducing waste'
                    ]
                },
                'resource_utilization': {
                    'services': ['Auto Scaling', 'CloudWatch'],
                    'details': [
                        'Utilization monitoring and optimization',
                        'Demand-based scaling reducing over-provisioning',
                        'Resource scheduling for non-production environments'
                    ]
                },
                'data_optimization': {
                    'services': ['S3', 'DynamoDB'],
                    'details': [
                        'Data lifecycle management reducing storage',
                        'Compression and deduplication where applicable',
                        'Archive policies for infrequently accessed data'
                    ]
                },
                'region_selection': {
                    'services': ['CloudFront'],
                    'details': [
                        'Region selection considering carbon intensity',
                        'Edge caching reducing origin requests',
                        'Data locality optimization'
                    ]
                }
            }
        }
        
        pillar_caps = capability_details.get(pillar_name, {})
        
        excellent_capabilities = []
        needs_improvement = []
        
        for cap in detected_caps:
            cap_normalized = cap.lower().replace(' ', '_')
            cap_info = pillar_caps.get(cap_normalized, {})
            
            # Filter details to only include services that are in the architecture
            relevant_details = []
            for detail in cap_info.get('details', []):
                # Check if any of the cap's services are in the architecture
                for svc in cap_info.get('services', []):
                    if svc in services:
                        relevant_details.append(detail)
                        break
                else:
                    # Include generic details if no specific service match
                    if len(relevant_details) < 2:
                        relevant_details.append(detail)
            
            if not relevant_details:
                relevant_details = [
                    f'{cap.replace("_", " ").title()} capability detected in architecture',
                    'Implementation aligns with AWS best practices'
                ]
            
            # Determine score based on overall pillar score
            cap_score = min(98, score + 5) if score >= 80 else score
            
            if cap_score >= 85:
                excellent_capabilities.append({
                    'name': cap.replace('_', ' ').title(),
                    'score': f'{cap_score:.0f}%',
                    'details': relevant_details[:4]
                })
            else:
                needs_improvement.append({
                    'name': cap.replace('_', ' ').title(),
                    'score': f'{cap_score:.0f}%',
                    'gaps': [
                        f'Current implementation at {cap_score:.0f}%, target 85%+',
                        'Review AWS best practices for optimization opportunities'
                    ]
                })
        
        return {
            'excellent_capabilities': excellent_capabilities,
            'needs_improvement': needs_improvement
        }
    
    def _generate_detailed_findings(
        self, pillar_name: str, score: float, services: List[str], detected_caps: List[str]
    ) -> Dict[str, Any]:
        """Generate service-specific detailed findings."""
        
        findings = {
            'compute': {
                'strengths': [],
                'recommendations': []
            },
            'storage': {
                'strengths': [],
                'recommendations': []
            },
            'network': {
                'strengths': [],
                'recommendations': []
            }
        }
        
        # Compute layer findings
        compute_services = [s for s in services if s in ['EC2', 'Auto Scaling', 'Lambda', 'ECS', 'Fargate']]
        if compute_services:
            findings['compute']['strengths'] = [
                f'{", ".join(compute_services)} configured for {pillar_name.replace("_", " ")}',
                'Auto Scaling policies enable dynamic capacity management' if 'Auto Scaling' in services else 'Compute resources provisioned for workload'
            ]
        else:
            findings['compute']['strengths'] = ['Basic compute configuration in place']
        
        if score < 85:
            findings['compute']['recommendations'] = ['Review compute optimization opportunities']
        else:
            findings['compute']['recommendations'] = ['Continue monitoring compute efficiency']
        
        # Storage layer findings
        storage_services = [s for s in services if s in ['S3', 'DynamoDB', 'EFS', 'ElastiCache']]
        if storage_services:
            findings['storage']['strengths'] = [
                f'{", ".join(storage_services)} providing data persistence',
                'Encryption enabled for data at rest' if score >= 75 else 'Basic storage configuration'
            ]
        else:
            findings['storage']['strengths'] = ['Storage foundation established']
        
        if score < 80:
            findings['storage']['recommendations'] = ['Implement storage lifecycle policies']
        else:
            findings['storage']['recommendations'] = ['Maintain storage best practices']
        
        # Network layer findings
        network_services = [s for s in services if s in ['VPC', 'CloudFront', 'Route 53', 'Application Load Balancer', 'WAF']]
        if network_services:
            findings['network']['strengths'] = [
                f'{", ".join(network_services)} providing network infrastructure',
                'Multi-tier network architecture implemented' if len(network_services) >= 3 else 'Network segmentation in place'
            ]
        else:
            findings['network']['strengths'] = ['Basic network setup']
        
        if score < 85:
            findings['network']['recommendations'] = ['Review network security controls']
        else:
            findings['network']['recommendations'] = ['Maintain network architecture best practices']
        
        return findings
    
    def _generate_maturity_model(
        self, pillar_name: str, score: float, detected_caps: List[str]
    ) -> List[Dict[str, str]]:
        """Generate maturity model assessment for capabilities."""
        
        maturity_items = []
        
        for cap in detected_caps[:5]:
            if score >= 85:
                current_level = 'Advanced'
                target_level = 'Advanced'
                gap = 'On Target'
            elif score >= 70:
                current_level = 'Intermediate'
                target_level = 'Advanced'
                gap = 'In Progress'
            else:
                current_level = 'Basic'
                target_level = 'Intermediate'
                gap = 'Attention Needed'
            
            maturity_items.append({
                'capability': cap.replace('_', ' ').title(),
                'current_level': current_level,
                'target_level': target_level,
                'gap': gap
            })
        
        return maturity_items
    
    def _generate_pillar_roadmap(
        self, pillar_name: str, score: float, recommendations: List[Dict], services: List[str]
    ) -> Dict[str, Any]:
        """Generate architecture-specific implementation roadmap for pillar improvements.
        
        This function creates roadmap activities that reference the actual detected
        services rather than using generic boilerplate text.
        """
        
        pillar_display = pillar_name.replace('_', ' ').title()
        
        # Get pillar-relevant services for specific recommendations
        pillar_services = self._get_pillar_relevant_services(pillar_name, services)
        services_text = ', '.join(pillar_services[:3]) if pillar_services else 'AWS services'
        
        # Generate architecture-specific phase focuses based on score and pillar
        if score >= 85:
            phase_1_focus = f'Maintain {pillar_display} excellence with {services_text}'
            phase_2_focus = f'Optimize {services_text} configurations for peak performance'
            phase_3_focus = f'Explore advanced {pillar_display} capabilities and automation'
        elif score >= 70:
            phase_1_focus = f'Address {pillar_display} gaps in {services_text} configuration'
            phase_2_focus = f'Implement {pillar_display} best practices across {services_text}'
            phase_3_focus = f'Achieve advanced {pillar_display} maturity'
        else:
            phase_1_focus = f'Critical {pillar_display} improvements for {services_text}'
            phase_2_focus = f'Establish {pillar_display} foundations with {services_text}'
            phase_3_focus = f'Scale and optimize {pillar_display} implementation'
        
        # Generate architecture-specific activities from recommendations
        phase_1_activities = []
        phase_2_activities = []
        phase_3_activities = []
        
        for i, rec in enumerate(recommendations):
            title = rec.get('title', '')
            if title:
                if i < 2:
                    phase_1_activities.append(title)
                elif i < 4:
                    phase_2_activities.append(title)
                else:
                    phase_3_activities.append(title)
        
        # Add service-specific fallback activities if needed
        if not phase_1_activities:
            phase_1_activities = [f'Review {services_text} {pillar_display.lower()} configuration']
        if not phase_2_activities:
            phase_2_activities = [f'Implement {pillar_display.lower()} monitoring for {services_text}']
        if not phase_3_activities:
            phase_3_activities = [f'Continuous {pillar_display.lower()} optimization', f'Regular {services_text} assessment']
        
        return {
            'phase_1': {
                'duration': '0-30 days',
                'focus': phase_1_focus,
                'activities': phase_1_activities
            },
            'phase_2': {
                'duration': '30-90 days',
                'focus': phase_2_focus,
                'activities': phase_2_activities
            },
            'phase_3': {
                'duration': '90+ days',
                'focus': phase_3_focus,
                'activities': phase_3_activities
            }
        }
    
    def _get_pillar_relevant_services(self, pillar_name: str, all_services: List[str]) -> List[str]:
        """Select services most relevant to a specific pillar from the detected services."""
        
        # Service categories for filtering
        pillar_keywords = {
            'security': ['cognito', 'iam', 'waf', 'kms', 'secrets', 'certificate', 'guard', 'shield', 'firewall'],
            'reliability': ['route 53', 'elb', 'alb', 'auto scaling', 'rds', 'dynamodb', 'elasticache', 'sqs', 'sns'],
            'performance_efficiency': ['cloudfront', 'elasticache', 'lambda', 'api gateway', 'appsync', 'dynamodb', 'aurora'],
            'cost_optimization': ['lambda', 's3', 'dynamodb', 'spot', 'reserved', 'savings', 'cost'],
            'operational_excellence': ['cloudwatch', 'x-ray', 'cloudformation', 'cdk', 'codepipeline', 'codebuild', 'systems manager'],
            'sustainability': ['lambda', 'fargate', 'graviton', 's3', 'aurora']
        }
        
        keywords = pillar_keywords.get(pillar_name, [])
        relevant = []
        
        for service in all_services:
            service_lower = service.lower() if isinstance(service, str) else ''
            if any(kw in service_lower for kw in keywords):
                relevant.append(service)
        
        # If no pillar-specific services found, use first 3 detected services
        if not relevant:
            relevant = all_services[:3] if all_services else []
        
        return relevant[:3]
    
    def _generate_pillar_success_metrics(self, pillar_name: str, score: float) -> Dict[str, Any]:
        """Generate success metrics for pillar improvement tracking."""
        
        target_score = min(95, score + 15)
        
        return {
            'current_score': f'{score:.1f}%',
            'target_score': f'{target_score:.0f}%',
            'target_timeframe': '90 days',
            'key_metrics': [
                f'{pillar_name.replace("_", " ").title()} compliance score',
                'Capability coverage percentage',
                'Recommendation implementation rate',
                'Risk reduction metrics'
            ]
        }
    
    def _generate_critical_findings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate critical findings section"""
        pillar_assessments = data.get('pillar_assessments', {})
        critical_findings = []
        
        for pillar, assessment in pillar_assessments.items():
            if assessment.get('risk_level') == 'High Risk':
                critical_findings.append({
                    'pillar': pillar.replace('_', ' ').title(),
                    'score': assessment.get('score', 0),
                    'finding': f"Critical gaps identified in {pillar.replace('_', ' ')} requiring immediate attention",
                    'impact': "High business risk if not addressed within 30 days"
                })
        
        return {
            'findings': critical_findings,
            'summary': f"Identified {len(critical_findings)} critical findings requiring immediate remediation"
        }
    
    def _generate_implementation_roadmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation roadmap matching template structure"""
        high_priority_actions = data.get('high_priority_actions', [])
        pillar_assessments = data.get('pillar_assessments', {})
        
        # Get critical and medium priority actions
        critical_actions = [action for action in high_priority_actions if action.get('priority') == 'critical']
        medium_actions = [action for action in high_priority_actions if action.get('priority') == 'medium']
        
        # Identify priority pillars based on risk levels
        high_risk_pillars = [pillar for pillar, assessment in pillar_assessments.items() 
                           if assessment.get('risk_level') == 'High Risk']
        medium_risk_pillars = [pillar for pillar, assessment in pillar_assessments.items() 
                             if assessment.get('risk_level') == 'Medium Risk']
        
        return {
            'phase_1_foundation': {
                'duration': '0-30 days',
                'focus': 'Address critical security and operational gaps',
                'priority_pillars': high_risk_pillars[:3] if high_risk_pillars else ['security', 'operational_excellence'],
                'key_activities': [
                    action.get('description', action.get('title', 'Critical improvement'))
                    for action in critical_actions[:4]
                ] or [
                    'Implement basic security controls and monitoring',
                    'Establish incident response procedures',
                    'Configure essential backup and recovery',
                    'Set up operational dashboards and alerting'
                ]
            },
            'phase_2_optimization': {
                'duration': '1-3 months',
                'focus': 'Implement performance and cost optimizations',
                'priority_pillars': medium_risk_pillars[:3] if medium_risk_pillars else ['performance_efficiency', 'cost_optimization'],
                'key_activities': [
                    action.get('description', action.get('title', 'Performance improvement'))
                    for action in medium_actions[:4]
                ] or [
                    'Optimize resource utilization and right-sizing',
                    'Implement caching and content delivery optimization',
                    'Enhance monitoring and performance metrics',
                    'Establish cost optimization practices'
                ]
            },
            'phase_3_excellence': {
                'duration': '3-12 months',
                'focus': 'Achieve architectural excellence and innovation',
                'priority_pillars': ['sustainability', 'operational_excellence', 'reliability'],
                'key_activities': [
                    'Establish continuous improvement processes',
                    'Implement advanced automation and orchestration',
                    'Adopt emerging AWS services and capabilities',
                    'Achieve full Well-Architected compliance and optimization'
                ]
            }
        }
    
    def _generate_cost_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost analysis section"""
        return {
            'optimization_potential': "15-30% cost reduction through right-sizing and reserved capacity",
            'key_areas': [
                "Compute optimization through right-sizing",
                "Storage optimization and lifecycle policies", 
                "Network optimization and data transfer reduction",
                "Reserved capacity and savings plans adoption"
            ],
            'estimated_savings': "$10,000-50,000 annually based on current architecture scale"
        }
    
    def _generate_business_impact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business impact analysis"""
        overall_score = data.get('overall_score', 70)
        
        if overall_score >= 80:
            impact_level = "Strong"
            description = "Architecture demonstrates excellent alignment with business objectives"
        elif overall_score >= 60:
            impact_level = "Moderate"
            description = "Architecture supports business goals with optimization opportunities"
        else:
            impact_level = "Significant"
            description = "Architecture requires improvements to fully support business objectives"
        
        return {
            'impact_level': impact_level,
            'description': description,
            'key_benefits': [
                "Improved operational efficiency and reduced manual overhead",
                "Enhanced security posture and compliance readiness",
                "Better cost predictability and optimization opportunities",
                "Increased system reliability and customer satisfaction"
            ]
        }