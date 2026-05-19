"""Hybrid Question Strategy for AWS Well-Architected Framework Assessments

This module implements a hybrid approach combining AWS API questions with document-based
assessment, providing fallback to local question library when API is unavailable.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

from ..core.logger import WAFRLogger
from ..aws_wellarchitected_client import WellArchitectedToolClient
from ..models.assessment import PillarName

logger = WAFRLogger(__name__)


@dataclass
class AdaptedQuestion:
    """A question adapted for document-based assessment"""
    question_id: str
    original_text: str
    adapted_text: str
    pillar: str
    relevance_score: float  # 0.0-1.0
    detected_services: List[str]
    capability_requirements: List[str]
    evaluation_criteria: Dict[str, Any]
    is_from_aws_api: bool = False
    adaptation_notes: str = ""


@dataclass
class QuestionEvaluation:
    """Result of evaluating a question based on capabilities"""
    question_id: str
    score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    evidence: List[str]
    gaps: List[str]
    recommendation: str


class QuestionAdapter:
    """
    Adapts AWS Well-Architected Tool questions for document-based assessment.
    
    Transforms questions from "How do you..." to "How does the architecture..."
    and adds context about detected services.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Question transformation patterns
        self.transformation_patterns = {
            r"How do you (.+)\?": r"How does the architecture \1?",
            r"How are you (.+)\?": r"How is the architecture \1?",
            r"How have you (.+)\?": r"How has the architecture \1?",
            r"What do you (.+)\?": r"What does the architecture \1?",
            r"Do you (.+)\?": r"Does the architecture \1?",
            r"Have you (.+)\?": r"Has the architecture \1?",
            r"Are you (.+)\?": r"Is the architecture \1?",
        }
    
    def adapt_for_document_assessment(
        self,
        aws_questions: List[Dict[str, Any]],
        detected_services: List[str],
        architecture_context: Dict[str, Any]
    ) -> List[AdaptedQuestion]:
        """
        Adapt AWS API questions for document-based assessment.
        
        Args:
            aws_questions: Questions from AWS Well-Architected Tool API
            detected_services: Services detected in architecture documents
            architecture_context: Additional context about the architecture
            
        Returns:
            List of adapted questions relevant to the detected architecture
        """
        adapted_questions = []
        
        for aws_q in aws_questions:
            # Check if question is relevant to detected services
            if self._is_question_relevant(aws_q, detected_services):
                adapted_q = self._adapt_single_question(
                    aws_q,
                    detected_services,
                    architecture_context
                )
                adapted_questions.append(adapted_q)
                
        self.logger.info(
            f"Adapted {len(adapted_questions)} of {len(aws_questions)} AWS questions "
            f"for document-based assessment"
        )
        
        return adapted_questions
    
    def _adapt_single_question(
        self,
        aws_question: Dict[str, Any],
        detected_services: List[str],
        architecture_context: Dict[str, Any]
    ) -> AdaptedQuestion:
        """Adapt a single AWS question for document-based assessment"""
        
        original_text = aws_question.get('QuestionTitle', '')
        question_id = aws_question.get('QuestionId', '')
        pillar = aws_question.get('PillarId', '')
        
        # Transform question text
        adapted_text = self._transform_question_text(original_text)
        
        # Add service context
        relevant_services = self._get_relevant_services(
            aws_question,
            detected_services
        )
        
        if relevant_services:
            service_context = f" (Detected services: {', '.join(relevant_services)})"
            adapted_text += service_context
        
        # Extract capability requirements
        capability_requirements = self._extract_capability_requirements(aws_question)
        
        # Calculate relevance score
        relevance_score = self._calculate_relevance_score(
            aws_question,
            detected_services,
            architecture_context
        )
        
        # Build evaluation criteria
        evaluation_criteria = self._build_evaluation_criteria(
            aws_question,
            capability_requirements
        )
        
        return AdaptedQuestion(
            question_id=question_id,
            original_text=original_text,
            adapted_text=adapted_text,
            pillar=pillar,
            relevance_score=relevance_score,
            detected_services=relevant_services,
            capability_requirements=capability_requirements,
            evaluation_criteria=evaluation_criteria,
            is_from_aws_api=True,
            adaptation_notes=f"Adapted from AWS API question {question_id}"
        )
    
    def _transform_question_text(self, original_text: str) -> str:
        """Transform question from 'How do you...' to 'How does the architecture...'"""
        
        transformed = original_text
        
        for pattern, replacement in self.transformation_patterns.items():
            transformed = re.sub(pattern, replacement, transformed, flags=re.IGNORECASE)
        
        return transformed
    
    def _is_question_relevant(
        self,
        question: Dict[str, Any],
        detected_services: List[str]
    ) -> bool:
        """Check if question is relevant to detected services"""
        
        # Get question description and choices
        question_text = question.get('QuestionTitle', '').lower()
        description = question.get('QuestionDescription', '').lower()
        
        # Check for service mentions
        for service in detected_services:
            service_lower = service.lower()
            if service_lower in question_text or service_lower in description:
                return True
        
        # Check choices for service mentions
        choices = question.get('Choices', [])
        for choice in choices:
            choice_text = choice.get('Title', '').lower()
            choice_desc = choice.get('Description', '').lower()
            
            for service in detected_services:
                service_lower = service.lower()
                if service_lower in choice_text or service_lower in choice_desc:
                    return True
        
        # Default to relevant if no specific service filtering
        return True
    
    def _get_relevant_services(
        self,
        question: Dict[str, Any],
        detected_services: List[str]
    ) -> List[str]:
        """Get services relevant to this question"""
        
        relevant = []
        question_text = question.get('QuestionTitle', '').lower()
        description = question.get('QuestionDescription', '').lower()
        
        for service in detected_services:
            service_lower = service.lower()
            if service_lower in question_text or service_lower in description:
                relevant.append(service)
        
        return relevant
    
    def _extract_capability_requirements(
        self,
        question: Dict[str, Any]
    ) -> List[str]:
        """Extract capability requirements from question"""
        
        capabilities = []
        
        # Map question keywords to capabilities
        question_text = question.get('QuestionTitle', '').lower()
        description = question.get('QuestionDescription', '').lower()
        combined_text = f"{question_text} {description}"
        
        capability_keywords = {
            'encryption': ['encrypt', 'kms', 'key management'],
            'monitoring': ['monitor', 'cloudwatch', 'observability', 'logging'],
            'redundancy': ['multi-az', 'redundant', 'failover', 'backup'],
            'scaling': ['scale', 'auto scaling', 'elasticity'],
            'access_control': ['iam', 'access', 'authentication', 'authorization'],
            'network_security': ['vpc', 'security group', 'network', 'firewall'],
            'backup_recovery': ['backup', 'recovery', 'disaster recovery', 'snapshot'],
            'caching': ['cache', 'cloudfront', 'elasticache'],
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                capabilities.append(capability)
        
        return capabilities
    
    def _calculate_relevance_score(
        self,
        question: Dict[str, Any],
        detected_services: List[str],
        architecture_context: Dict[str, Any]
    ) -> float:
        """Calculate how relevant this question is to the architecture"""
        
        score = 0.5  # Base relevance
        
        # Increase score if services are mentioned
        relevant_services = self._get_relevant_services(question, detected_services)
        if relevant_services:
            score += 0.3 * min(len(relevant_services) / 3, 1.0)
        
        # Increase score if question matches architecture pattern
        patterns = architecture_context.get('architectural_patterns', [])
        question_text = question.get('QuestionTitle', '').lower()
        
        for pattern in patterns:
            pattern_name = pattern.get('pattern_type', '').lower()
            if pattern_name in question_text:
                score += 0.2
        
        return min(score, 1.0)
    
    def _build_evaluation_criteria(
        self,
        question: Dict[str, Any],
        capability_requirements: List[str]
    ) -> Dict[str, Any]:
        """Build criteria for evaluating this question"""
        
        return {
            'required_capabilities': capability_requirements,
            'best_practices': question.get('BestPractices', []),
            'risk_level': question.get('Risk', 'MEDIUM'),
            'improvement_plan': question.get('ImprovementPlan', {}),
        }


class CapabilityBasedQuestionEvaluator:
    """
    Evaluates questions automatically based on detected capabilities.
    
    Maps questions to capability requirements and calculates scores
    from capability coverage.
    """
    
    def __init__(self, capability_mapper):
        """
        Initialize evaluator with capability mapper.
        
        Args:
            capability_mapper: CapabilityMapper instance for capability detection
        """
        self.capability_mapper = capability_mapper
        self.logger = logger
    
    def evaluate_question(
        self,
        question: AdaptedQuestion,
        capability_matrix: Any,
        detected_services: List[str]
    ) -> QuestionEvaluation:
        """
        Evaluate a question based on detected capabilities.
        
        Args:
            question: Adapted question to evaluate
            capability_matrix: Matrix of detected capabilities
            detected_services: List of detected AWS services
            
        Returns:
            QuestionEvaluation with score, evidence, and gaps
        """
        
        # Get capabilities for question's pillar
        pillar_capabilities = capability_matrix.get_capabilities_for_pillar(question.pillar)
        
        # Check which required capabilities are present
        present_capabilities = []
        missing_capabilities = []
        evidence = []
        
        for required_cap in question.capability_requirements:
            capability = self._find_capability(required_cap, pillar_capabilities)
            
            if capability and capability.coverage > 0.5:
                present_capabilities.append(required_cap)
                evidence.extend(capability.evidence)
            else:
                missing_capabilities.append(required_cap)
        
        # Calculate score based on capability coverage
        if question.capability_requirements:
            score = len(present_capabilities) / len(question.capability_requirements)
        else:
            score = 0.5  # Default score if no specific requirements
        
        # Calculate confidence based on detection quality
        confidence = self._calculate_confidence(
            present_capabilities,
            pillar_capabilities,
            detected_services
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            question,
            missing_capabilities,
            detected_services
        )
        
        return QuestionEvaluation(
            question_id=question.question_id,
            score=score,
            confidence=confidence,
            evidence=evidence,
            gaps=missing_capabilities,
            recommendation=recommendation
        )
    
    def _find_capability(
        self,
        capability_name: str,
        capabilities: List[Any]
    ) -> Optional[Any]:
        """Find a capability by name in the list"""
        
        for cap in capabilities:
            if cap.name.lower() == capability_name.lower():
                return cap
        return None
    
    def _calculate_confidence(
        self,
        present_capabilities: List[str],
        all_capabilities: List[Any],
        detected_services: List[str]
    ) -> float:
        """Calculate confidence in the evaluation"""
        
        # Base confidence on number of services detected
        service_confidence = min(len(detected_services) / 10, 1.0) * 0.4
        
        # Add confidence based on capability detection
        if all_capabilities:
            avg_capability_confidence = sum(
                cap.confidence for cap in all_capabilities
            ) / len(all_capabilities)
            capability_confidence = avg_capability_confidence * 0.6
        else:
            capability_confidence = 0.3
        
        return service_confidence + capability_confidence
    
    def _generate_recommendation(
        self,
        question: AdaptedQuestion,
        missing_capabilities: List[str],
        detected_services: List[str]
    ) -> str:
        """Generate recommendation based on gaps"""
        
        if not missing_capabilities:
            return "All required capabilities are present. Continue monitoring and maintaining current implementation."
        
        recommendations = []
        
        for cap in missing_capabilities:
            if cap == 'encryption':
                recommendations.append(
                    "Implement encryption at rest and in transit using AWS KMS for key management."
                )
            elif cap == 'monitoring':
                recommendations.append(
                    "Set up comprehensive monitoring using CloudWatch with custom metrics and alarms."
                )
            elif cap == 'redundancy':
                recommendations.append(
                    "Implement Multi-AZ deployment and Auto Scaling for fault tolerance."
                )
            elif cap == 'backup_recovery':
                recommendations.append(
                    "Configure automated backups using AWS Backup with appropriate retention policies."
                )
            else:
                recommendations.append(
                    f"Implement {cap.replace('_', ' ')} capability to improve architecture quality."
                )
        
        return " ".join(recommendations)


class LocalQuestionLibrary:
    """
    Curated local question library for fallback when AWS API is unavailable.
    
    Maintains comprehensive questions optimized for document-based assessment.
    """
    
    def __init__(self, config_dir: str = "config/questions"):
        """
        Initialize local question library.
        
        Args:
            config_dir: Directory containing question configuration files
        """
        self.config_dir = config_dir
        self.logger = logger
        self.questions = self._load_questions()
    
    def _load_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load questions from configuration files"""
        
        # For now, return hardcoded questions
        # In production, these would be loaded from JSON config files
        return {
            'security': self._get_security_questions(),
            'reliability': self._get_reliability_questions(),
            'performance': self._get_performance_questions(),
            'cost_optimization': self._get_cost_optimization_questions(),
            'operational_excellence': self._get_operational_excellence_questions(),
            'sustainability': self._get_sustainability_questions(),
        }
    
    def get_questions_for_pillar(
        self,
        pillar: str,
        detected_services: List[str]
    ) -> List[AdaptedQuestion]:
        """
        Get curated questions for a pillar.
        
        Args:
            pillar: WAFR pillar name
            detected_services: Services detected in architecture
            
        Returns:
            List of adapted questions for the pillar
        """
        
        pillar_questions = self.questions.get(pillar, [])
        
        adapted_questions = []
        for idx, q in enumerate(pillar_questions):
            adapted_q = AdaptedQuestion(
                question_id=f"local_{pillar}_{idx}",
                original_text=q['text'],
                adapted_text=q['text'],
                pillar=pillar,
                relevance_score=self._calculate_local_relevance(q, detected_services),
                detected_services=self._get_question_services(q, detected_services),
                capability_requirements=q.get('capabilities', []),
                evaluation_criteria=q.get('criteria', {}),
                is_from_aws_api=False,
                adaptation_notes="From curated local library"
            )
            adapted_questions.append(adapted_q)
        
        self.logger.info(
            f"Retrieved {len(adapted_questions)} local questions for {pillar} pillar"
        )
        
        return adapted_questions
    
    def _calculate_local_relevance(
        self,
        question: Dict[str, Any],
        detected_services: List[str]
    ) -> float:
        """Calculate relevance of local question to architecture"""
        
        question_services = question.get('services', [])
        if not question_services:
            return 0.7  # Default relevance
        
        # Calculate overlap with detected services
        overlap = len(set(question_services) & set(detected_services))
        if overlap > 0:
            return min(0.7 + (overlap * 0.1), 1.0)
        
        return 0.5
    
    def _get_question_services(
        self,
        question: Dict[str, Any],
        detected_services: List[str]
    ) -> List[str]:
        """Get services relevant to this question"""
        
        question_services = question.get('services', [])
        return list(set(question_services) & set(detected_services))
    
    def _get_security_questions(self) -> List[Dict[str, Any]]:
        """Get security pillar questions"""
        return [
            {
                'text': 'How does the architecture implement data encryption at rest and in transit?',
                'capabilities': ['encryption'],
                'services': ['KMS', 'S3', 'RDS', 'DynamoDB'],
                'criteria': {'required_capabilities': ['encryption']}
            },
            {
                'text': 'How does the architecture manage identity and access control?',
                'capabilities': ['access_control'],
                'services': ['IAM', 'Cognito', 'Secrets Manager'],
                'criteria': {'required_capabilities': ['access_control']}
            },
            {
                'text': 'How does the architecture implement network security and isolation?',
                'capabilities': ['network_security'],
                'services': ['VPC', 'Security Groups', 'WAF', 'Shield'],
                'criteria': {'required_capabilities': ['network_security']}
            },
            {
                'text': 'How does the architecture detect and respond to security threats?',
                'capabilities': ['monitoring_detection'],
                'services': ['CloudTrail', 'GuardDuty', 'Security Hub', 'CloudWatch'],
                'criteria': {'required_capabilities': ['monitoring_detection']}
            },
            {
                'text': 'How does the architecture protect data with backup and versioning?',
                'capabilities': ['data_protection'],
                'services': ['Backup', 'S3 Versioning', 'RDS Snapshots'],
                'criteria': {'required_capabilities': ['data_protection']}
            },
        ]
    
    def _get_reliability_questions(self) -> List[Dict[str, Any]]:
        """Get reliability pillar questions"""
        return [
            {
                'text': 'How does the architecture implement fault tolerance and redundancy?',
                'capabilities': ['redundancy'],
                'services': ['Multi-AZ', 'Auto Scaling', 'ELB', 'Route 53'],
                'criteria': {'required_capabilities': ['redundancy']}
            },
            {
                'text': 'How does the architecture monitor system health and performance?',
                'capabilities': ['monitoring_alerting'],
                'services': ['CloudWatch', 'CloudWatch Alarms', 'SNS'],
                'criteria': {'required_capabilities': ['monitoring_alerting']}
            },
            {
                'text': 'How does the architecture handle backup and disaster recovery?',
                'capabilities': ['backup_recovery'],
                'services': ['Backup', 'S3 Replication', 'RDS Snapshots'],
                'criteria': {'required_capabilities': ['backup_recovery']}
            },
            {
                'text': 'How does the architecture scale to handle varying loads?',
                'capabilities': ['scaling'],
                'services': ['Auto Scaling', 'Lambda', 'DynamoDB Auto Scaling'],
                'criteria': {'required_capabilities': ['scaling']}
            },
        ]
    
    def _get_performance_questions(self) -> List[Dict[str, Any]]:
        """Get performance pillar questions"""
        return [
            {
                'text': 'How does the architecture implement caching for performance optimization?',
                'capabilities': ['caching'],
                'services': ['CloudFront', 'ElastiCache', 'API Gateway Caching'],
                'criteria': {'required_capabilities': ['caching']}
            },
            {
                'text': 'How does the architecture optimize compute resources?',
                'capabilities': ['compute_optimization'],
                'services': ['Lambda', 'Fargate', 'EC2'],
                'criteria': {'required_capabilities': ['compute_optimization']}
            },
            {
                'text': 'How does the architecture optimize database performance?',
                'capabilities': ['database_optimization'],
                'services': ['RDS Read Replicas', 'DynamoDB DAX', 'Aurora'],
                'criteria': {'required_capabilities': ['database_optimization']}
            },
        ]
    
    def _get_cost_optimization_questions(self) -> List[Dict[str, Any]]:
        """Get cost optimization pillar questions"""
        return [
            {
                'text': 'How does the architecture implement cost-effective resource sizing?',
                'capabilities': ['resource_optimization'],
                'services': ['Auto Scaling', 'Lambda', 'Savings Plans'],
                'criteria': {'required_capabilities': ['resource_optimization']}
            },
            {
                'text': 'How does the architecture manage data lifecycle and storage costs?',
                'capabilities': ['storage_optimization'],
                'services': ['S3 Lifecycle', 'S3 Intelligent-Tiering', 'Glacier'],
                'criteria': {'required_capabilities': ['storage_optimization']}
            },
        ]
    
    def _get_operational_excellence_questions(self) -> List[Dict[str, Any]]:
        """Get operational excellence pillar questions"""
        return [
            {
                'text': 'How does the architecture implement infrastructure as code?',
                'capabilities': ['infrastructure_as_code'],
                'services': ['CloudFormation', 'CDK', 'Terraform'],
                'criteria': {'required_capabilities': ['infrastructure_as_code']}
            },
            {
                'text': 'How does the architecture implement observability and monitoring?',
                'capabilities': ['observability'],
                'services': ['CloudWatch', 'X-Ray', 'CloudTrail'],
                'criteria': {'required_capabilities': ['observability']}
            },
        ]
    
    def _get_sustainability_questions(self) -> List[Dict[str, Any]]:
        """Get sustainability pillar questions"""
        return [
            {
                'text': 'How does the architecture optimize resource utilization for sustainability?',
                'capabilities': ['resource_efficiency'],
                'services': ['Lambda', 'Fargate', 'Graviton'],
                'criteria': {'required_capabilities': ['resource_efficiency']}
            },
        ]


class HybridQuestionStrategy:
    """
    Hybrid approach combining AWS API questions with document-based assessment.
    
    Strategy:
    1. Use AWS API questions as the gold standard question library
    2. Adapt questions for document-based assessment
    3. Fall back to curated questions when API unavailable
    """
    
    def __init__(self, aws_client: Optional[WellArchitectedToolClient] = None):
        """
        Initialize hybrid question strategy.
        
        Args:
            aws_client: Optional AWS Well-Architected Tool client
        """
        self.aws_client = aws_client or WellArchitectedToolClient()
        self.local_library = LocalQuestionLibrary()
        self.question_adapter = QuestionAdapter()
        self.logger = logger
    
    async def get_questions_for_pillar(
        self,
        pillar: str,
        detected_services: List[str],
        architecture_context: Dict[str, Any]
    ) -> List[AdaptedQuestion]:
        """
        Get questions using hybrid strategy.
        
        Process:
        1. Try to fetch from AWS API (if available)
        2. Adapt API questions for document-based assessment
        3. Filter questions based on detected services
        4. Fall back to local library if API fails
        
        Args:
            pillar: WAFR pillar name
            detected_services: Services detected in architecture
            architecture_context: Additional architecture context
            
        Returns:
            List of adapted questions for the pillar
        """
        
        try:
            # Attempt to get official AWS questions
            self.logger.info(f"Attempting to fetch AWS API questions for {pillar} pillar")
            
            aws_questions = await self._fetch_aws_questions(pillar)
            
            if aws_questions:
                self.logger.info(
                    f"✅ Retrieved {len(aws_questions)} official AWS questions for {pillar}"
                )
                
                # Adapt questions for document-based assessment
                adapted_questions = self.question_adapter.adapt_for_document_assessment(
                    aws_questions,
                    detected_services,
                    architecture_context
                )
                
                # Filter by relevance
                relevant_questions = [
                    q for q in adapted_questions
                    if q.relevance_score >= 0.5
                ]
                
                self.logger.info(
                    f"Filtered to {len(relevant_questions)} relevant questions "
                    f"(relevance threshold: 0.5)"
                )
                
                return relevant_questions
                
        except Exception as e:
            self.logger.warning(
                f"⚠️ AWS API unavailable: {e}, falling back to local library"
            )
        
        # Fallback to curated local questions
        local_questions = self.local_library.get_questions_for_pillar(
            pillar,
            detected_services
        )
        
        self.logger.info(
            f"📚 Using {len(local_questions)} curated local questions for {pillar}"
        )
        
        return local_questions
    
    async def _fetch_aws_questions(self, pillar: str) -> List[Dict[str, Any]]:
        """Fetch questions from AWS Well-Architected Tool API"""
        
        try:
            # Use the AWS client to get lens questions
            # This would call the actual AWS API
            # For now, return empty list to trigger fallback
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to fetch AWS questions: {e}")
            return []
    
    def get_all_questions(
        self,
        detected_services: List[str],
        architecture_context: Dict[str, Any]
    ) -> Dict[str, List[AdaptedQuestion]]:
        """
        Get questions for all pillars.
        
        Args:
            detected_services: Services detected in architecture
            architecture_context: Additional architecture context
            
        Returns:
            Dictionary mapping pillar names to lists of adapted questions
        """
        
        pillars = [
            'security',
            'reliability',
            'performance',
            'cost_optimization',
            'operational_excellence',
            'sustainability'
        ]
        
        all_questions = {}
        
        for pillar in pillars:
            questions = asyncio.run(
                self.get_questions_for_pillar(
                    pillar,
                    detected_services,
                    architecture_context
                )
            )
            all_questions[pillar] = questions
        
        total_questions = sum(len(qs) for qs in all_questions.values())
        self.logger.info(
            f"Retrieved total of {total_questions} questions across all pillars"
        )
        
        return all_questions
