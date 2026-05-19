"""
WAFR Data Processor - Single Source of Truth Implementation

This module provides unified data processing for both chat output and report generation,
following the same pattern as the cost analysis server to ensure data consistency.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WAFRDataProcessor:
    """
    Single source of truth for WAFR data processing.
    Ensures both chat output and reports use identical processed data.
    """
    
    @staticmethod
    def process_assessment_data(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw assessment data into standardized format for both chat and reports.
        This ensures both chat output and reports use identical data.
        
        Args:
            assessment_results: Raw assessment data from generate_comprehensive_wafr_assessment
            
        Returns:
            Standardized data structure for both chat and report generation
        """
        try:
            logger.info("🔄 Processing assessment data for unified chat/report consistency")
            
            # Create standardized data structure
            processed_data = {
                'assessment_metadata': WAFRDataProcessor._extract_metadata(assessment_results),
                'architecture_analysis': WAFRDataProcessor._extract_architecture_data(assessment_results),
                'pillar_assessments': WAFRDataProcessor._normalize_pillar_data(assessment_results),
                'risk_analysis': WAFRDataProcessor._extract_risk_data(assessment_results),
                'recommendations': WAFRDataProcessor._extract_recommendations(assessment_results),
                'business_impact': WAFRDataProcessor._calculate_business_impact(assessment_results),
                'success_metrics': WAFRDataProcessor._generate_success_metrics(assessment_results),
                'implementation_roadmap': WAFRDataProcessor._create_implementation_roadmap(assessment_results)
            }
            
            logger.info("✅ Assessment data processed successfully for unified usage")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error processing assessment data: {e}")
            raise
    
    @staticmethod
    def _extract_metadata(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize assessment metadata"""
        return {
            'chat_id': assessment_results.get('chat_id', 'unknown'),
            'assessment_timestamp': assessment_results.get('assessment_timestamp', datetime.now().isoformat()),
            'overall_score': assessment_results.get('overall_score', 0),
            'enhanced_scoring_enabled': assessment_results.get('enhanced_scoring_enabled', True),
            'total_pillars_assessed': len(assessment_results.get('pillar_assessments', {})),
            'assessment_type': 'comprehensive'
        }
    
    @staticmethod
    def _extract_architecture_data(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize architecture information"""
        document_analysis = assessment_results.get('document_analysis', {})
        
        # Handle both old and new data formats (identified_services vs aws_services)
        services = []
        if 'identified_services' in document_analysis:
            services = document_analysis['identified_services']
        elif 'aws_services' in document_analysis:
            # Extract service names from old format
            aws_services = document_analysis['aws_services']
            if isinstance(aws_services, list):
                for service in aws_services:
                    if isinstance(service, dict) and 'item' in service:
                        # Extract service name from markdown format
                        item = service['item']
                        if '**' in item:
                            service_name = item.split('**')[1] if '**' in item else item
                            services.append(service_name)
                    elif isinstance(service, str):
                        services.append(service)
        
        return {
            'services_identified': services,
            'total_services_count': len(services),
            'architecture_patterns': document_analysis.get('architectural_patterns', []),
            'combined_insights': document_analysis.get('combined_insights', {}),
            'architecture_type': WAFRDataProcessor._determine_architecture_type(document_analysis, services)
        }
    
    @staticmethod
    def _determine_architecture_type(document_analysis: Dict[str, Any], services: List[str]) -> str:
        """Determine architecture type based on services and patterns"""
        patterns = document_analysis.get('architectural_patterns', [])
        
        # Check for serverless patterns
        serverless_services = ['Lambda', 'DynamoDB', 'API Gateway', 'S3', 'CloudFront']
        serverless_count = sum(1 for service in services if any(s in service for s in serverless_services))
        
        # Check for microservices patterns
        microservices_indicators = ['API Gateway', 'ECS', 'EKS', 'Lambda', 'SQS', 'SNS']
        microservices_count = sum(1 for service in services if any(s in service for s in microservices_indicators))
        
        # Determine architecture type
        if serverless_count >= 3 and microservices_count >= 3:
            return 'Serverless Microservices Architecture'
        elif serverless_count >= 3:
            return 'Serverless Architecture'
        elif microservices_count >= 3:
            return 'Microservices Architecture'
        elif 'EC2' in services or 'RDS' in services:
            return 'Traditional Cloud Architecture'
        else:
            return 'Hybrid Cloud Architecture'
    
    @staticmethod
    def _normalize_pillar_data(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize pillar assessment data"""
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        normalized_pillars = {}
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                normalized_pillars[pillar_name] = {
                    'score': pillar_data.get('score', 0),
                    'risk_level': WAFRDataProcessor._calculate_risk_level(pillar_data.get('score', 0)),
                    'capabilities_assessed': pillar_data.get('capabilities_assessed', []),
                    'recommendations': pillar_data.get('recommendations', []),
                    'enhanced_scoring_used': pillar_data.get('enhanced_scoring_used', True),
                    'capability_based_scoring': pillar_data.get('capability_based_scoring', True),
                    'key_findings': WAFRDataProcessor._extract_key_findings(pillar_data)
                }
        
        return normalized_pillars
    
    @staticmethod
    def _calculate_risk_level(score: float) -> str:
        """Calculate risk level based on score"""
        if score >= 80:
            return 'Low'
        elif score >= 60:
            return 'Medium'
        elif score >= 40:
            return 'High'
        else:
            return 'Critical'
    
    @staticmethod
    def _extract_key_findings(pillar_data: Dict[str, Any]) -> List[str]:
        """Extract key findings from pillar data"""
        findings = []
        
        # Extract from recommendations
        recommendations = pillar_data.get('recommendations', [])
        for rec in recommendations[:3]:  # Top 3 recommendations as key findings
            if isinstance(rec, dict) and 'title' in rec:
                findings.append(rec['title'])
        
        # Add capability-based findings if available
        capabilities = pillar_data.get('capabilities_assessed', [])
        if len(capabilities) > 0:
            findings.append(f"Assessed {len(capabilities)} key capabilities")
        
        return findings
    
    @staticmethod
    def _extract_risk_data(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and categorize risk information"""
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        
        critical_risks = []
        medium_risks = []
        low_risks = []
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                score = pillar_data.get('score', 0)
                risk_level = WAFRDataProcessor._calculate_risk_level(score)
                
                risk_item = {
                    'pillar': pillar_name,
                    'score': score,
                    'risk_level': risk_level,
                    'description': f"{pillar_name.replace('_', ' ').title()} pillar assessment"
                }
                
                if risk_level == 'Critical':
                    critical_risks.append(risk_item)
                elif risk_level == 'High':
                    critical_risks.append(risk_item)
                elif risk_level == 'Medium':
                    medium_risks.append(risk_item)
                else:
                    low_risks.append(risk_item)
        
        return {
            'critical_priority_issues': critical_risks,
            'medium_priority_issues': medium_risks,
            'low_priority_issues': low_risks,
            'total_risks': len(critical_risks) + len(medium_risks) + len(low_risks),
            'risk_distribution': {
                'critical': len(critical_risks),
                'medium': len(medium_risks),
                'low': len(low_risks)
            }
        }
    
    @staticmethod
    def _extract_recommendations(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and categorize recommendations"""
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        
        immediate_actions = []
        short_term_actions = []
        long_term_actions = []
        
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                recommendations = pillar_data.get('recommendations', [])
                
                for rec in recommendations:
                    if isinstance(rec, dict):
                        priority = rec.get('priority', 'medium').lower()
                        action_item = {
                            'title': rec.get('title', 'Improvement recommendation'),
                            'description': rec.get('description', ''),
                            'pillar': pillar_name,
                            'priority': priority,
                            'effort': rec.get('effort', 'medium')
                        }
                        
                        if priority in ['critical', 'high']:
                            immediate_actions.append(action_item)
                        elif priority == 'medium':
                            short_term_actions.append(action_item)
                        else:
                            long_term_actions.append(action_item)
        
        return {
            'immediate_actions': immediate_actions[:5],  # Top 5 immediate actions
            'short_term_actions': short_term_actions[:5],  # Top 5 short-term actions
            'long_term_actions': long_term_actions[:5],  # Top 5 long-term actions
            'total_recommendations': len(immediate_actions) + len(short_term_actions) + len(long_term_actions)
        }
    
    @staticmethod
    def _calculate_business_impact(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate business impact metrics"""
        overall_score = assessment_results.get('overall_score', 0)
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        
        # Calculate potential improvements
        cost_pillar_score = pillar_assessments.get('cost_optimization', {}).get('score', 0)
        security_pillar_score = pillar_assessments.get('security', {}).get('score', 0)
        performance_pillar_score = pillar_assessments.get('performance_efficiency', {}).get('score', 0)
        operational_pillar_score = pillar_assessments.get('operational_excellence', {}).get('score', 0)
        
        return {
            'cost_optimization_potential': max(0, 90 - cost_pillar_score),
            'security_improvement_potential': max(0, 95 - security_pillar_score),
            'performance_improvement_potential': max(0, 85 - performance_pillar_score),
            'operational_improvement_potential': max(0, 80 - operational_pillar_score),
            'overall_maturity_level': WAFRDataProcessor._calculate_maturity_level(overall_score),
            'business_risk_level': WAFRDataProcessor._calculate_business_risk(overall_score)
        }
    
    @staticmethod
    def _calculate_maturity_level(overall_score: float) -> str:
        """Calculate architecture maturity level"""
        if overall_score >= 85:
            return 'Optimized'
        elif overall_score >= 70:
            return 'Managed'
        elif overall_score >= 55:
            return 'Defined'
        elif overall_score >= 40:
            return 'Repeatable'
        else:
            return 'Initial'
    
    @staticmethod
    def _calculate_business_risk(overall_score: float) -> str:
        """Calculate business risk level"""
        if overall_score >= 80:
            return 'Low'
        elif overall_score >= 60:
            return 'Medium'
        elif overall_score >= 40:
            return 'High'
        else:
            return 'Critical'
    
    @staticmethod
    def _generate_success_metrics(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate success metrics and KPIs"""
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        
        technical_metrics = []
        business_metrics = []
        
        # Generate pillar-specific metrics
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                score = pillar_data.get('score', 0)
                target_score = min(100, score + 20)  # Target 20% improvement
                
                technical_metrics.append({
                    'metric': f"{pillar_name.replace('_', ' ').title()} Score",
                    'current': f"{score:.1f}%",
                    'target': f"{target_score:.1f}%",
                    'improvement': f"+{target_score - score:.1f}%"
                })
        
        # Generate business metrics
        overall_score = assessment_results.get('overall_score', 0)
        business_metrics = [
            {
                'metric': 'Overall Architecture Maturity',
                'current': f"{overall_score:.1f}%",
                'target': f"{min(100, overall_score + 15):.1f}%",
                'timeframe': '6 months'
            },
            {
                'metric': 'Risk Reduction',
                'current': 'Baseline',
                'target': '25% reduction',
                'timeframe': '3 months'
            },
            {
                'metric': 'Operational Efficiency',
                'current': 'Baseline',
                'target': '30% improvement',
                'timeframe': '6 months'
            }
        ]
        
        return {
            'technical_metrics': technical_metrics,
            'business_metrics': business_metrics,
            'monitoring_framework': WAFRDataProcessor._create_monitoring_framework(pillar_assessments)
        }
    
    @staticmethod
    def _create_monitoring_framework(pillar_assessments: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create monitoring framework recommendations"""
        framework = [
            {
                'area': 'Performance Monitoring',
                'tool': 'CloudWatch',
                'frequency': 'Real-time',
                'key_metrics': 'Response time, throughput, error rates'
            },
            {
                'area': 'Cost Monitoring',
                'tool': 'AWS Cost Explorer',
                'frequency': 'Daily',
                'key_metrics': 'Daily spend, budget variance, cost per service'
            },
            {
                'area': 'Security Monitoring',
                'tool': 'AWS Security Hub',
                'frequency': 'Continuous',
                'key_metrics': 'Security findings, compliance status, threat detection'
            },
            {
                'area': 'Operational Monitoring',
                'tool': 'AWS Systems Manager',
                'frequency': 'Continuous',
                'key_metrics': 'System health, patch compliance, automation success'
            }
        ]
        
        return framework
    
    @staticmethod
    def _create_implementation_roadmap(assessment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation roadmap based on assessment results"""
        overall_score = assessment_results.get('overall_score', 0)
        pillar_assessments = assessment_results.get('pillar_assessments', {})
        
        # Determine priority pillars (lowest scores first)
        pillar_scores = []
        for pillar_name, pillar_data in pillar_assessments.items():
            if isinstance(pillar_data, dict):
                pillar_scores.append((pillar_name, pillar_data.get('score', 0)))
        
        pillar_scores.sort(key=lambda x: x[1])  # Sort by score (lowest first)
        
        return {
            'phase_1_foundation': {
                'priority': 'Critical Priority',
                'focus': 'Critical security and operational issues',
                'priority_pillars': [pillar_scores[0][0], pillar_scores[1][0]] if len(pillar_scores) >= 2 else [pillar_scores[0][0]] if pillar_scores else [],
                'key_activities': [
                    'Address critical security vulnerabilities',
                    'Implement basic monitoring and alerting',
                    'Establish operational procedures'
                ]
            },
            'phase_2_optimization': {
                'priority': 'High Priority',
                'focus': 'Performance and cost optimization',
                'priority_pillars': [pillar_scores[2][0], pillar_scores[3][0]] if len(pillar_scores) >= 4 else [],
                'key_activities': [
                    'Optimize performance bottlenecks',
                    'Implement cost optimization strategies',
                    'Enhance reliability measures'
                ]
            },
            'phase_3_excellence': {
                'priority': 'Medium Priority',
                'focus': 'Achieving architectural excellence',
                'priority_pillars': [pillar_scores[-1][0]] if pillar_scores else [],
                'key_activities': [
                    'Implement advanced automation',
                    'Achieve sustainability goals',
                    'Continuous improvement processes'
                ]
            }
        }