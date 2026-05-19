"""WAFR Question Framework Integration

This module integrates with official AWS Well-Architected Framework questions,
scoring algorithms, and assessment criteria for accurate pillar evaluations.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

from .core.logger import WAFRLogger
from .core.error_handler import AssessmentEngineError
from .models.assessment import PillarName, RiskLevel, Finding, Recommendation
from .aws_wellarchitected_client import WellArchitectedToolClient

logger = WAFRLogger(__name__)


class QuestionRisk(str, Enum):
    """WAFR question risk levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
    UNANSWERED = "UNANSWERED"


@dataclass
class WAFRQuestion:
    """WAFR question definition."""
    
    question_id: str
    question_title: str
    question_description: str
    pillar_id: str
    
    choices: List[Dict[str, Any]] = field(default_factory=list)
    helpful_resources: List[Dict[str, Any]] = field(default_factory=list)
    improvement_plan: List[Dict[str, Any]] = field(default_factory=list)
    
    # Assessment data
    selected_choices: List[str] = field(default_factory=list)
    risk_level: QuestionRisk = QuestionRisk.UNANSWERED
    notes: str = ""
    is_applicable: bool = True
    
    def get_risk_score(self) -> float:
        """Calculate risk score for this question (0-100, lower is better)."""
        risk_mapping = {
            QuestionRisk.NONE: 0.0,
            QuestionRisk.LOW: 25.0,
            QuestionRisk.MEDIUM: 50.0,
            QuestionRisk.HIGH: 100.0,
            QuestionRisk.UNANSWERED: 75.0  # Treat unanswered as medium-high risk
        }
        return risk_mapping.get(self.risk_level, 75.0)


@dataclass
class PillarQuestionFramework:
    """Question framework for a specific pillar."""
    
    pillar_id: str
    pillar_name: str
    questions: List[WAFRQuestion] = field(default_factory=list)
    
    def get_pillar_score(self) -> float:
        """Calculate overall pillar score (0-100, higher is better)."""
        if not self.questions:
            return 0.0
        
        # Calculate average risk score and invert (100 - risk = score)
        total_risk = sum(q.get_risk_score() for q in self.questions if q.is_applicable)
        applicable_questions = sum(1 for q in self.questions if q.is_applicable)
        
        if applicable_questions == 0:
            return 100.0  # No applicable questions = perfect score
        
        average_risk = total_risk / applicable_questions
        return max(0.0, 100.0 - average_risk)
    
    def get_risk_counts(self) -> Dict[str, int]:
        """Get count of questions by risk level."""
        counts = {risk.value: 0 for risk in QuestionRisk}
        
        for question in self.questions:
            if question.is_applicable:
                counts[question.risk_level.value] += 1
        
        return counts
    
    def get_high_risk_questions(self) -> List[WAFRQuestion]:
        """Get all high-risk questions."""
        return [q for q in self.questions if q.risk_level == QuestionRisk.HIGH and q.is_applicable]
    
    def get_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """Get improvement opportunities from questions."""
        improvements = []
        
        for question in self.questions:
            if question.risk_level in [QuestionRisk.HIGH, QuestionRisk.MEDIUM] and question.is_applicable:
                improvements.extend(question.improvement_plan)
        
        return improvements


class WAFRQuestionFramework:
    """
    Official AWS Well-Architected Framework question framework integration.
    
    Provides access to current WAFR questions, scoring algorithms, and
    assessment criteria for accurate pillar evaluations.
    """
    
    def __init__(self, wellarchitected_client: Optional[WellArchitectedToolClient] = None):
        """
        Initialize WAFR question framework.
        
        Args:
            wellarchitected_client: Optional Well-Architected Tool client (uses SERA credentials by default)
        """
        # Use provided client or create new one with SERA credentials
        self.wellarchitected_client = wellarchitected_client or WellArchitectedToolClient()
        self.pillar_frameworks: Dict[str, PillarQuestionFramework] = {}
        self.lens_alias = "wellarchitected"  # AWS Well-Architected Framework lens
        
        # Initialize with default pillar mappings
        self.pillar_mapping = {
            PillarName.OPERATIONAL_EXCELLENCE: "operational",
            PillarName.SECURITY: "security",
            PillarName.RELIABILITY: "reliability",
            PillarName.PERFORMANCE_EFFICIENCY: "performance",
            PillarName.COST_OPTIMIZATION: "cost",
            PillarName.SUSTAINABILITY: "sustainability"
        }
        
        logger.info("Initialized WAFR Question Framework")
    
    async def load_pillar_questions(self, pillar_name: PillarName) -> PillarQuestionFramework:
        """
        Load questions for a specific pillar.
        
        Args:
            pillar_name: WAFR pillar to load questions for
            
        Returns:
            Pillar question framework with all questions
            
        Raises:
            AssessmentEngineError: If question loading fails
        """
        try:
            pillar_id = self.pillar_mapping[pillar_name]
            
            logger.info(f"Loading questions for {pillar_name.value} pillar")
            
            # Try to load from Well-Architected Tool API if available
            if self.wellarchitected_client:
                try:
                    questions = await self._load_questions_from_api(pillar_id)
                    logger.info(f"Loaded {len(questions)} questions from Well-Architected Tool API")
                    
                    # CRITICAL FIX: If API succeeds but returns no questions, use fallback
                    if not questions or len(questions) == 0:
                        logger.warning(f"API returned 0 questions for {pillar_id}, using fallback questions")
                        questions = self._load_questions_fallback(pillar_id)
                        logger.info(f"Using {len(questions)} fallback questions for {pillar_id}")
                        
                except Exception as api_error:
                    logger.warning(f"Failed to load from API, using fallback: {api_error}")
                    questions = self._load_questions_fallback(pillar_id)
            else:
                questions = self._load_questions_fallback(pillar_id)
            
            # Create pillar framework
            framework = PillarQuestionFramework(
                pillar_id=pillar_id,
                pillar_name=pillar_name.value,
                questions=questions
            )
            
            # Cache the framework
            self.pillar_frameworks[pillar_id] = framework
            
            logger.info(f"Successfully loaded {len(questions)} questions for {pillar_name.value}")
            return framework
            
        except Exception as e:
            logger.error(f"Failed to load questions for {pillar_name.value}: {e}")
            raise AssessmentEngineError(f"Failed to load WAFR questions for {pillar_name.value}: {str(e)}")
    
    async def _load_questions_from_api(self, pillar_id: str) -> List[WAFRQuestion]:
        """Load questions from Well-Architected Tool API."""
        try:
            # Get lens questions
            lens_data = await self.wellarchitected_client.get_lens_questions(self.lens_alias)
            
            pillar_data = lens_data.get('pillar_questions', {}).get(pillar_id, {})
            questions_data = pillar_data.get('questions', [])
            
            questions = []
            for q_data in questions_data:
                question = WAFRQuestion(
                    question_id=q_data.get('QuestionId', ''),
                    question_title=q_data.get('QuestionTitle', ''),
                    question_description=q_data.get('QuestionDescription', ''),
                    pillar_id=pillar_id,
                    choices=q_data.get('Choices', []),
                    helpful_resources=q_data.get('HelpfulResources', []),
                    improvement_plan=q_data.get('ImprovementPlan', [])
                )
                questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to load questions from API for {pillar_id}: {e}")
            raise
    
    def _load_questions_fallback(self, pillar_id: str) -> List[WAFRQuestion]:
        """Load questions from fallback data when API is not available."""
        # This provides a fallback set of key WAFR questions for each pillar
        # In a production system, this would be loaded from a comprehensive JSON file
        
        fallback_questions = {
            "operational": [
                {
                    "question_id": "ops_1",
                    "question_title": "How do you determine what your priorities are?",
                    "question_description": "Everyone needs to understand their part in enabling business success.",
                    "choices": [
                        {"choice_id": "ops_1_a", "title": "Evaluate business needs", "description": "Business needs are evaluated and priorities are set."},
                        {"choice_id": "ops_1_b", "title": "Evaluate compliance requirements", "description": "Compliance requirements are evaluated."},
                        {"choice_id": "ops_1_c", "title": "Evaluate threat landscape", "description": "Threat landscape is evaluated."}
                    ]
                },
                {
                    "question_id": "ops_2",
                    "question_title": "How do you structure your organization to support your business outcomes?",
                    "question_description": "Your teams must understand their part in achieving business outcomes.",
                    "choices": [
                        {"choice_id": "ops_2_a", "title": "Resources have identified owners", "description": "Resources have identified owners responsible for their definition, deployment, and performance."},
                        {"choice_id": "ops_2_b", "title": "Processes and procedures have identified owners", "description": "Processes and procedures have identified owners responsible for their definition and performance."}
                    ]
                }
            ],
            "security": [
                {
                    "question_id": "sec_1",
                    "question_title": "How do you securely operate your workload?",
                    "question_description": "To operate your workload securely, you must apply overarching best practices to every area of security.",
                    "choices": [
                        {"choice_id": "sec_1_a", "title": "Separate workloads using accounts", "description": "Organize workloads in separate accounts and group accounts based on function or a common set of controls."},
                        {"choice_id": "sec_1_b", "title": "Secure account root user and properties", "description": "The root user has the highest level of access to your account."}
                    ]
                },
                {
                    "question_id": "sec_2",
                    "question_title": "How do you manage identities for people and machines?",
                    "question_description": "There are two types of identities you need to manage when approaching operating secure AWS workloads.",
                    "choices": [
                        {"choice_id": "sec_2_a", "title": "Use strong identity foundation", "description": "Enforce minimum password length and complexity requirements."},
                        {"choice_id": "sec_2_b", "title": "Enforce use of multi-factor authentication", "description": "Enforce MFA for all users and privileged operations."}
                    ]
                }
            ],
            "reliability": [
                {
                    "question_id": "rel_1",
                    "question_title": "How do you manage service quotas and constraints?",
                    "question_description": "For cloud-based workload architectures, there are service quotas (which are also referred to as service limits).",
                    "choices": [
                        {"choice_id": "rel_1_a", "title": "Aware of service quotas and constraints", "description": "You are aware of default quotas and request increases proactively."},
                        {"choice_id": "rel_1_b", "title": "Manage service quotas across accounts and regions", "description": "If you are using multiple AWS accounts or AWS Regions, ensure that you request the appropriate quotas in all environments."}
                    ]
                },
                {
                    "question_id": "rel_2",
                    "question_title": "How do you plan your network topology?",
                    "question_description": "Workloads often exist in multiple environments.",
                    "choices": [
                        {"choice_id": "rel_2_a", "title": "Use highly available network connectivity", "description": "Building highly available network connectivity between AWS and your on-premises environment is critical."},
                        {"choice_id": "rel_2_b", "title": "Ensure IP subnet allocation accounts for expansion", "description": "Amazon VPC IP address ranges must be large enough to accommodate workload requirements."}
                    ]
                }
            ],
            "performance": [
                {
                    "question_id": "perf_1",
                    "question_title": "How do you select the best performing architecture?",
                    "question_description": "Often, multiple approaches are required for optimal performance across a workload.",
                    "choices": [
                        {"choice_id": "perf_1_a", "title": "Understand the available services and resources", "description": "Learn about and understand the wide range of services available that could improve workload performance."},
                        {"choice_id": "perf_1_b", "title": "Define a process for architectural choices", "description": "Use internal experience and knowledge of the cloud or external resources to guide your architectural choices."}
                    ]
                },
                {
                    "question_id": "perf_2",
                    "question_title": "How do you select your compute solution?",
                    "question_description": "The optimal compute solution for a workload varies based on application design, usage patterns, and configuration settings.",
                    "choices": [
                        {"choice_id": "perf_2_a", "title": "Evaluate the available compute options", "description": "Understand the performance characteristics of the compute-related options available to you."},
                        {"choice_id": "perf_2_b", "title": "Understand the available compute configuration options", "description": "Understand how various options complement your workload and which configuration options are best for your system."}
                    ]
                }
            ],
            "cost": [
                {
                    "question_id": "cost_1",
                    "question_title": "How do you implement cloud financial management?",
                    "question_description": "Implementing Cloud Financial Management enables organizations to realize business value and financial success.",
                    "choices": [
                        {"choice_id": "cost_1_a", "title": "Establish a cost optimization function", "description": "Create a team that is responsible for establishing and maintaining cost awareness across your organization."},
                        {"choice_id": "cost_1_b", "title": "Establish partnership between finance and technology", "description": "Involve finance and technology teams in cost and usage discussions at all stages of your cloud journey."}
                    ]
                },
                {
                    "question_id": "cost_2",
                    "question_title": "How do you govern usage?",
                    "question_description": "Establish policies and mechanisms to ensure that appropriate costs are incurred while objectives are achieved.",
                    "choices": [
                        {"choice_id": "cost_2_a", "title": "Develop policies based on your organization requirements", "description": "Develop policies that define how resources are managed by your organization."},
                        {"choice_id": "cost_2_b", "title": "Implement goals and targets", "description": "Implement both cost and usage goals for your workload."}
                    ]
                }
            ],
            "sustainability": [
                {
                    "question_id": "sus_1",
                    "question_title": "How do you select Regions for your workload?",
                    "question_description": "Selecting Regions for your workload impacts its sustainability characteristics.",
                    "choices": [
                        {"choice_id": "sus_1_a", "title": "Choose Regions based on business requirements and sustainability goals", "description": "Choose Regions for your workload based on both business requirements and sustainability goals."},
                        {"choice_id": "sus_1_b", "title": "Optimize for user location", "description": "Select Regions that are close to your users to reduce the environmental impact of network traffic."}
                    ]
                },
                {
                    "question_id": "sus_2",
                    "question_title": "How do you take advantage of user behavior patterns to support sustainability goals?",
                    "question_description": "The way users consume your services and the devices they use can help you identify opportunities to support sustainability goals.",
                    "choices": [
                        {"choice_id": "sus_2_a", "title": "Scale infrastructure with user load", "description": "Scale your infrastructure to match user load and avoid over-provisioning."},
                        {"choice_id": "sus_2_b", "title": "Align SLA with sustainability goals", "description": "Consider sustainability goals when defining SLAs for your workload."}
                    ]
                }
            ]
        }
        
        questions_data = fallback_questions.get(pillar_id, [])
        questions = []
        
        for q_data in questions_data:
            question = WAFRQuestion(
                question_id=q_data["question_id"],
                question_title=q_data["question_title"],
                question_description=q_data["question_description"],
                pillar_id=pillar_id,
                choices=q_data.get("choices", []),
                helpful_resources=[],
                improvement_plan=[]
            )
            questions.append(question)
        
        logger.info(f"Loaded {len(questions)} fallback questions for {pillar_id}")
        return questions
    
    async def assess_pillar(
        self,
        pillar: str,
        architecture_data: Dict[str, Any],
        live_aws_data: Optional[Dict[str, Any]] = None,
        official_questions: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Assess a specific WAFR pillar.
        
        Args:
            pillar: Pillar name (e.g., 'security', 'reliability')
            architecture_data: Architecture data from document analysis
            live_aws_data: Optional live AWS environment data
            official_questions: Optional official WAFR questions
            
        Returns:
            Pillar assessment results with score and recommendations
        """
        try:
            logger.info(f"Assessing {pillar} pillar")
            
            # Map pillar string to PillarName enum
            pillar_mapping = {
                "operational_excellence": PillarName.OPERATIONAL_EXCELLENCE,
                "security": PillarName.SECURITY,
                "reliability": PillarName.RELIABILITY,
                "performance_efficiency": PillarName.PERFORMANCE_EFFICIENCY,
                "cost_optimization": PillarName.COST_OPTIMIZATION,
                "sustainability": PillarName.SUSTAINABILITY
            }
            
            pillar_enum = pillar_mapping.get(pillar)
            if not pillar_enum:
                return {
                    "success": False,
                    "error": f"Unknown pillar: {pillar}",
                    "pillar": pillar,
                    "score": 0,
                    "risk_counts": {"HIGH": 0, "MEDIUM": 0, "NONE": 0, "UNANSWERED": 1, "NOT_APPLICABLE": 0}
                }
            
            # Use the existing assess_pillar_against_framework method
            framework, findings, recommendations = await self.assess_pillar_against_framework(
                pillar_name=pillar_enum,
                architecture_data=architecture_data,
                live_aws_data=live_aws_data
            )
            
            # Calculate score based on findings
            total_questions = len(framework.questions)
            high_risk_count = sum(1 for q in framework.questions if q.risk_level == QuestionRisk.HIGH)
            medium_risk_count = sum(1 for q in framework.questions if q.risk_level == QuestionRisk.MEDIUM)
            none_risk_count = sum(1 for q in framework.questions if q.risk_level == QuestionRisk.NONE)
            
            # Create risk_counts structure matching AWS WAFR API format
            risk_counts = {
                "HIGH": high_risk_count,
                "MEDIUM": medium_risk_count, 
                "NONE": none_risk_count,
                "UNANSWERED": max(0, total_questions - high_risk_count - medium_risk_count - none_risk_count),
                "NOT_APPLICABLE": 0
            }
            
            # Dynamic scoring: AWS WAFR doesn't provide scores, calculate from risk distribution
            score = self._calculate_score_from_risk_counts(risk_counts, total_questions)
            
            return {
                "success": True,
                "pillar": pillar,
                "score": score,
                "risk_level": "high" if score < 60 else "medium" if score < 80 else "low",
                "risk_counts": risk_counts,
                "total_questions": total_questions,
                "high_risk_findings": high_risk_count,
                "medium_risk_findings": medium_risk_count,
                "findings": [f.to_dict() for f in findings],
                "recommendations": [r.to_dict() for r in recommendations],
                "assessment_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error assessing {pillar} pillar: {e}")
            return {
                "success": False,
                "error": str(e),
                "pillar": pillar,
                "score": 0,  # Failed assessment = 0 score
                "risk_counts": {"HIGH": 0, "MEDIUM": 0, "NONE": 0, "UNANSWERED": 1, "NOT_APPLICABLE": 0}
            }

    def _calculate_score_from_risk_counts(self, risk_counts: Dict[str, int], total_questions: int) -> int:
        """Calculate numerical score from AWS WAFR risk counts.
        
        AWS WAFR API returns risk counts, not scores. This method converts
        risk distribution to a 0-100 score for reporting purposes.
        """
        if total_questions == 0:
            return 0
            
        # Weight factors for different risk levels
        weights = {
            "NONE": 1.0,      # Best case - no risk
            "MEDIUM": 0.6,    # Moderate risk
            "HIGH": 0.2,      # High risk - significant deduction
            "UNANSWERED": 0.3, # Unanswered questions are risky
            "NOT_APPLICABLE": 1.0  # No impact on score
        }
        
        # Calculate weighted score
        weighted_sum = sum(risk_counts.get(risk, 0) * weight for risk, weight in weights.items())
        score = int((weighted_sum / total_questions) * 100)
        
        return max(0, min(100, score))  # Ensure 0-100 range

    async def assess_pillar_against_framework(
        self, 
        pillar_name: PillarName, 
        architecture_data: Dict[str, Any],
        live_aws_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[PillarQuestionFramework, List[Finding], List[Recommendation]]:
        """
        Assess a pillar against the WAFR question framework.
        
        Args:
            pillar_name: WAFR pillar to assess
            architecture_data: Extracted architectural information
            live_aws_data: Optional live AWS environment data
            
        Returns:
            Tuple of (pillar framework, findings, recommendations)
        """
        try:
            logger.info(f"Assessing {pillar_name.value} against WAFR framework")
            
            # Load pillar questions
            framework = await self.load_pillar_questions(pillar_name)
            
            # Assess each question
            findings = []
            recommendations = []
            
            for question in framework.questions:
                # Analyze question against architecture data
                risk_assessment = await self._assess_question(
                    question, architecture_data, live_aws_data
                )
                
                # Update question with assessment results
                question.risk_level = risk_assessment["risk_level"]
                question.selected_choices = risk_assessment["selected_choices"]
                question.notes = risk_assessment["notes"]
                
                # Generate findings for high/medium risks
                if question.risk_level in [QuestionRisk.HIGH, QuestionRisk.MEDIUM]:
                    finding = self._create_finding_from_question(question, pillar_name)
                    findings.append(finding)
                    
                    # Always generate recommendations for medium/high risk questions
                    recommendation = self._create_recommendation_from_question(question, pillar_name)
                    recommendations.append(recommendation)
            
            # Update framework risk counts
            risk_counts = framework.get_risk_counts()
            logger.info(f"Assessment complete: {risk_counts['HIGH']} high, {risk_counts['MEDIUM']} medium, {risk_counts['LOW']} low risks")
            
            return framework, findings, recommendations
            
        except Exception as e:
            logger.error(f"Failed to assess {pillar_name.value} against framework: {e}")
            raise AssessmentEngineError(f"Failed to assess pillar against WAFR framework: {str(e)}")
    
    async def _assess_question(
        self, 
        question: WAFRQuestion, 
        architecture_data: Dict[str, Any],
        live_aws_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess a single question against architecture data.
        
        Args:
            question: WAFR question to assess
            architecture_data: Architecture information
            live_aws_data: Optional live AWS data
            
        Returns:
            Assessment results for the question
        """
        # This is a simplified assessment logic
        # In a full implementation, this would include sophisticated analysis
        # of architecture patterns, service configurations, and best practices
        
        services = architecture_data.get("services", [])
        configurations = architecture_data.get("configurations", {})
        
        # Default assessment based on question patterns
        risk_level = QuestionRisk.MEDIUM  # Default to medium risk
        selected_choices = []
        notes = "Automated assessment based on document analysis"
        
        # Simple pattern matching for demonstration
        question_lower = question.question_title.lower()
        
        # Security-related assessments
        if question.pillar_id == "security":
            if "identity" in question_lower or "authentication" in question_lower:
                if "IAM" in services or "Cognito" in services:
                    risk_level = QuestionRisk.LOW
                    notes = "Identity services detected in architecture"
                else:
                    risk_level = QuestionRisk.HIGH
                    notes = "No identity management services detected"
            
            elif "encrypt" in question_lower:
                if configurations.get("encryption", False):
                    risk_level = QuestionRisk.LOW
                    notes = "Encryption configuration detected"
                else:
                    risk_level = QuestionRisk.HIGH
                    notes = "No encryption configuration detected"
        
        # Reliability-related assessments
        elif question.pillar_id == "reliability":
            if "availability" in question_lower or "fault" in question_lower:
                if configurations.get("multi_az", False):
                    risk_level = QuestionRisk.LOW
                    notes = "Multi-AZ configuration detected"
                else:
                    risk_level = QuestionRisk.MEDIUM
                    notes = "Multi-AZ configuration not clearly specified"
            
            elif "backup" in question_lower:
                if configurations.get("backup_configured", False):
                    risk_level = QuestionRisk.LOW
                    notes = "Backup configuration detected"
                else:
                    risk_level = QuestionRisk.HIGH
                    notes = "No backup configuration detected"
        
        # Performance-related assessments
        elif question.pillar_id == "performance":
            if "compute" in question_lower:
                if "EC2" in services or "Lambda" in services:
                    risk_level = QuestionRisk.LOW
                    notes = "Compute services detected"
                else:
                    risk_level = QuestionRisk.MEDIUM
                    notes = "Compute architecture needs review"
        
        # Cost-related assessments
        elif question.pillar_id == "cost":
            if "optimization" in question_lower:
                risk_level = QuestionRisk.MEDIUM
                notes = "Cost optimization requires ongoing monitoring"
        
        # Sustainability-related assessments
        elif question.pillar_id == "sustainability":
            if "region" in question_lower:
                risk_level = QuestionRisk.LOW
                notes = "Regional deployment considerations noted"
        
        # Operational Excellence assessments
        elif question.pillar_id == "operational":
            if "monitoring" in question_lower:
                if "CloudWatch" in services:
                    risk_level = QuestionRisk.LOW
                    notes = "Monitoring services detected"
                else:
                    risk_level = QuestionRisk.MEDIUM
                    notes = "Monitoring strategy needs clarification"
        
        return {
            "risk_level": risk_level,
            "selected_choices": selected_choices,
            "notes": notes
        }
    
    def _create_finding_from_question(self, question: WAFRQuestion, pillar_name: PillarName) -> Finding:
        """Create a finding from a WAFR question assessment."""
        risk_mapping = {
            QuestionRisk.HIGH: RiskLevel.HIGH,
            QuestionRisk.MEDIUM: RiskLevel.MEDIUM,
            QuestionRisk.LOW: RiskLevel.LOW
        }
        
        return Finding(
            finding_id=f"wafr_{question.question_id}",
            title=f"WAFR: {question.question_title}",
            description=question.question_description,
            pillar=pillar_name,
            risk_level=risk_mapping.get(question.risk_level, RiskLevel.MEDIUM),
            confidence_score=0.8,
            evidence=[question.notes],
            business_impact=f"Impacts {pillar_name.value} pillar compliance",
            recommendations=[f"Review and address: {question.question_title}"],
            aws_documentation_links=[f"https://docs.aws.amazon.com/wellarchitected/latest/framework/{pillar_name.value.replace('_', '-')}-pillar.html"]
        )
    
    def _create_recommendation_from_question(self, question: WAFRQuestion, pillar_name: PillarName) -> Recommendation:
        """Create a recommendation from a WAFR question."""
        return Recommendation(
            recommendation_id=f"wafr_rec_{question.question_id}",
            title=f"Improve: {question.question_title}",
            description=f"Address the following WAFR question: {question.question_description}",
            pillar=pillar_name,
            priority=1 if question.risk_level == QuestionRisk.HIGH else 2,
            implementation_steps=[
                "Review current architecture against WAFR best practices",
                "Implement recommended improvements",
                "Validate changes against WAFR criteria"
            ],
            estimated_effort_hours=8 if question.risk_level == QuestionRisk.HIGH else 4,
            expected_benefits=[f"Improved {pillar_name.value} compliance"],
            aws_documentation_links=[f"https://docs.aws.amazon.com/wellarchitected/latest/framework/{pillar_name.value.replace('_', '-')}-pillar.html"]
        )
    
    def get_pillar_framework(self, pillar_id: str) -> Optional[PillarQuestionFramework]:
        """Get cached pillar framework."""
        return self.pillar_frameworks.get(pillar_id)
    
    def get_all_frameworks(self) -> Dict[str, PillarQuestionFramework]:
        """Get all loaded pillar frameworks."""
        return self.pillar_frameworks.copy()
    
    async def calculate_overall_wafr_score(self) -> Dict[str, Any]:
        """
        Calculate overall WAFR score across all pillars.
        
        Returns:
            Overall WAFR assessment score and breakdown
        """
        if not self.pillar_frameworks:
            return {
                "overall_score": 0.0,
                "grade": "F",
                "pillar_scores": {},
                "total_risks": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            }
        
        pillar_scores = {}
        total_risks = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for pillar_id, framework in self.pillar_frameworks.items():
            score = framework.get_pillar_score()
            risk_counts = framework.get_risk_counts()
            
            pillar_scores[pillar_id] = {
                "score": score,
                "grade": self._score_to_grade(score),
                "risk_counts": risk_counts
            }
            
            # Aggregate risk counts
            total_risks["HIGH"] += risk_counts.get("HIGH", 0)
            total_risks["MEDIUM"] += risk_counts.get("MEDIUM", 0)
            total_risks["LOW"] += risk_counts.get("LOW", 0)
        
        # Calculate overall score (average of pillar scores)
        overall_score = sum(p["score"] for p in pillar_scores.values()) / len(pillar_scores)
        
        return {
            "overall_score": overall_score,
            "grade": self._score_to_grade(overall_score),
            "pillar_scores": pillar_scores,
            "total_risks": total_risks,
            "assessment_timestamp": logger.get_current_timestamp()
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"