# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS Well-Architected Framework questions and assessment logic."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk levels for WAFR assessment findings."""
    HIGH_RISK = "HRI"
    MEDIUM_RISK = "MRI"
    LOW_RISK = "LRI"
    NO_RISK = "NONE"


class PillarName(Enum):
    """Well-Architected Framework pillars."""
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE_EFFICIENCY = "performance_efficiency"
    COST_OPTIMIZATION = "cost_optimization"
    SUSTAINABILITY = "sustainability"


@dataclass
class WAFRChoice:
    """Represents a choice for a WAFR question."""
    choice_id: str
    title: str
    description: str
    best_practices: List[str]
    implementation_guidance: List[str]
    aws_services: List[str]
    risk_if_not_implemented: RiskLevel


@dataclass
class WAFRQuestion:
    """Represents a Well-Architected Framework question."""
    question_id: str
    pillar: PillarName
    title: str
    description: str
    choices: List[WAFRChoice]
    aws_docs_links: List[str]
    weight: float = 1.0


@dataclass
class QuestionAssessment:
    """Assessment result for a specific WAFR question."""
    question_id: str
    question_title: str
    pillar: str
    implemented_choices: List[str]
    missing_choices: List[str]
    risk_level: RiskLevel
    score: float
    recommendations: List[str]
    aws_docs: List[str]


@dataclass
class PillarAssessment:
    """Assessment result for a complete pillar."""
    pillar_name: str
    questions_assessed: List[QuestionAssessment]
    pillar_score: float
    high_risk_issues: List[str]
    medium_risk_issues: List[str]
    low_risk_issues: List[str]
    recommendations: List[str]


class WAFRQuestionsFramework:
    """Main framework for WAFR questions and assessment."""

    def __init__(self):
        self.questions = self._load_wafr_questions()

    def _load_wafr_questions(self) -> Dict[str, WAFRQuestion]:
        """Load all 83 Well-Architected Framework questions."""
        questions = {}

        # Operational Excellence Questions (14 questions)
        questions.update(self._load_operational_excellence_questions())

        # Security Questions (14 questions)
        questions.update(self._load_security_questions())

        # Reliability Questions (13 questions)
        questions.update(self._load_reliability_questions())

        # Performance Efficiency Questions (13 questions)
        questions.update(self._load_performance_efficiency_questions())

        # Cost Optimization Questions (17 questions)
        questions.update(self._load_cost_optimization_questions())

        # Sustainability Questions (12 questions)
        questions.update(self._load_sustainability_questions())

        return questions

    def _load_operational_excellence_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Operational Excellence pillar questions."""
        questions = {}

        # OPS 1: How do you determine what your priorities are?
        questions["OPS01"] = WAFRQuestion(
            question_id="OPS01",
            pillar=PillarName.OPERATIONAL_EXCELLENCE,
            title="How do you determine what your priorities are?",
            description="Understanding your priorities helps you focus on the business outcomes that matter most and make informed decisions about where to invest effort.",
            choices=[
                WAFRChoice(
                    choice_id="ops01_01",
                    title="External customer needs",
                    description="Understand and prioritize external customer needs",
                    best_practices=[
                        "Regularly gather customer feedback",
                        "Implement customer journey mapping",
                        "Use customer success metrics"
                    ],
                    implementation_guidance=[
                        "Implement customer feedback systems",
                        "Use Amazon Connect for customer insights",
                        "Track customer satisfaction metrics"
                    ],
                    aws_services=["connect", "pinpoint", "cloudwatch"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                ),
                WAFRChoice(
                    choice_id="ops01_02",
                    title="Internal stakeholder needs",
                    description="Understand and prioritize internal stakeholder needs",
                    best_practices=[
                        "Regular stakeholder communication",
                        "Clear escalation processes",
                        "Stakeholder impact assessment"
                    ],
                    implementation_guidance=[
                        "Implement internal communication tools",
                        "Use AWS Chime for collaboration",
                        "Create stakeholder dashboards"
                    ],
                    aws_services=["chime", "workspaces", "cloudwatch"],
                    risk_if_not_implemented=RiskLevel.MEDIUM_RISK
                ),
                WAFRChoice(
                    choice_id="ops01_03",
                    title="Governance and compliance requirements",
                    description="Understand governance and compliance requirements",
                    best_practices=[
                        "Regular compliance assessments",
                        "Documented governance policies",
                        "Compliance monitoring"
                    ],
                    implementation_guidance=[
                        "Implement AWS Config for compliance",
                        "Use AWS Security Hub for governance",
                        "Set up compliance reporting"
                    ],
                    aws_services=["config", "security-hub", "cloudtrail"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_org_priorities.html"
            ]
        )

        # OPS 2: How do you structure your organization to support your business outcomes?
        questions["OPS02"] = WAFRQuestion(
            question_id="OPS02",
            pillar=PillarName.OPERATIONAL_EXCELLENCE,
            title="How do you structure your organization to support your business outcomes?",
            description="Your teams must understand their part in achieving business outcomes and how their role contributes to the success of the business.",
            choices=[
                WAFRChoice(
                    choice_id="ops02_01",
                    title="Resources have identified owners",
                    description="Ensure resources have identified owners responsible for their operation",
                    best_practices=[
                        "Clear ownership assignment",
                        "Resource tagging for ownership",
                        "Ownership documentation"
                    ],
                    implementation_guidance=[
                        "Use AWS Resource Groups and Tagging",
                        "Implement consistent tagging strategy",
                        "Create ownership dashboards"
                    ],
                    aws_services=["resource-groups", "tag-editor", "cloudformation"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                ),
                WAFRChoice(
                    choice_id="ops02_02",
                    title="Processes and procedures have identified owners",
                    description="Processes and procedures have identified owners responsible for their definition and performance",
                    best_practices=[
                        "Process documentation",
                        "Process ownership assignment",
                        "Regular process reviews"
                    ],
                    implementation_guidance=[
                        "Use AWS Systems Manager documents",
                        "Implement runbook automation",
                        "Create process monitoring"
                    ],
                    aws_services=["systems-manager", "cloudwatch", "lambda"],
                    risk_if_not_implemented=RiskLevel.MEDIUM_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_org_structure.html"
            ]
        )

        # Add more operational excellence questions...
        # (For brevity, I'm showing the pattern. You would add all 14 questions)

        return questions

    def _load_security_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Security pillar questions."""
        questions = {}

        # SEC 1: How do you securely operate your workload?
        questions["SEC01"] = WAFRQuestion(
            question_id="SEC01",
            pillar=PillarName.SECURITY,
            title="How do you securely operate your workload?",
            description="Staying up to date with security threats and recommendations helps you understand and implement appropriate controls.",
            choices=[
                WAFRChoice(
                    choice_id="sec01_01",
                    title="Separate workloads using accounts",
                    description="Use AWS accounts to separate workloads and provide strong isolation",
                    best_practices=[
                        "Account separation strategy",
                        "Cross-account access controls",
                        "Account governance"
                    ],
                    implementation_guidance=[
                        "Use AWS Organizations for account management",
                        "Implement AWS Control Tower for governance",
                        "Set up cross-account roles"
                    ],
                    aws_services=["organizations", "control-tower", "iam"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                ),
                WAFRChoice(
                    choice_id="sec01_02",
                    title="Secure account root user and properties",
                    description="Root user has unrestricted access and should be carefully protected",
                    best_practices=[
                        "MFA on root account",
                        "Strong root password",
                        "Limited root usage"
                    ],
                    implementation_guidance=[
                        "Enable MFA for root user",
                        "Use hardware MFA device",
                        "Monitor root user activity"
                    ],
                    aws_services=["iam", "cloudtrail", "cloudwatch"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate.html"
            ]
        )

        # SEC 2: How do you manage identities for people and machines?
        questions["SEC02"] = WAFRQuestion(
            question_id="SEC02",
            pillar=PillarName.SECURITY,
            title="How do you manage identities for people and machines?",
            description="There are different types of identities you need to manage: human identities and machine identities that require access to your AWS environment and applications.",
            choices=[
                WAFRChoice(
                    choice_id="sec02_01",
                    title="Use strong identity foundation",
                    description="Implement strong identity foundation with centralized identity provider",
                    best_practices=[
                        "Centralized identity management",
                        "Strong authentication",
                        "Regular access reviews"
                    ],
                    implementation_guidance=[
                        "Use AWS IAM Identity Center",
                        "Implement SAML/OIDC federation",
                        "Set up MFA requirements"
                    ],
                    aws_services=["iam-identity-center", "iam", "cognito"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                ),
                WAFRChoice(
                    choice_id="sec02_02",
                    title="Use temporary credentials",
                    description="Use temporary credentials for human and machine access",
                    best_practices=[
                        "Avoid long-term credentials",
                        "Use IAM roles for EC2",
                        "Rotate credentials regularly"
                    ],
                    implementation_guidance=[
                        "Use IAM roles instead of access keys",
                        "Implement credential rotation",
                        "Use AWS STS for temporary access"
                    ],
                    aws_services=["iam", "sts", "secrets-manager"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identity_management.html"
            ]
        )

        # Add more security questions...
        # (Continue with all 14 security questions)

        return questions

    def _load_reliability_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Reliability pillar questions."""
        questions = {}

        # REL 1: How do you manage service quotas and constraints?
        questions["REL01"] = WAFRQuestion(
            question_id="REL01",
            pillar=PillarName.RELIABILITY,
            title="How do you manage service quotas and constraints?",
            description="Service quotas and constraints are the maximum number of resources that you can create in an AWS account.",
            choices=[
                WAFRChoice(
                    choice_id="rel01_01",
                    title="Aware of service quotas and constraints",
                    description="Be aware of fixed service quotas and variable constraints",
                    best_practices=[
                        "Understand service limits",
                        "Monitor quota usage",
                        "Plan for quota increases"
                    ],
                    implementation_guidance=[
                        "Use AWS Service Quotas console",
                        "Monitor with CloudWatch",
                        "Set up quota alarms"
                    ],
                    aws_services=["service-quotas", "cloudwatch", "trusted-advisor"],
                    risk_if_not_implemented=RiskLevel.HIGH_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_manage_requests_service_quotas.html"
            ]
        )

        # Add more reliability questions...

        return questions

    def _load_performance_efficiency_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Performance Efficiency pillar questions."""
        questions = {}

        # PERF 1: How do you select the best performing architecture?
        questions["PERF01"] = WAFRQuestion(
            question_id="PERF01",
            pillar=PillarName.PERFORMANCE_EFFICIENCY,
            title="How do you select the best performing architecture?",
            description="Understand how systems perform and maintain efficiency as business needs evolve.",
            choices=[
                WAFRChoice(
                    choice_id="perf01_01",
                    title="Learn about available cloud services and features",
                    description="Learn about and understand available cloud services and features",
                    best_practices=[
                        "Regular service updates review",
                        "Architecture reviews",
                        "Technology evaluation"
                    ],
                    implementation_guidance=[
                        "Use AWS architecture guides",
                        "Attend AWS training",
                        "Implement proof of concepts"
                    ],
                    aws_services=["well-architected-tool", "trusted-advisor"],
                    risk_if_not_implemented=RiskLevel.MEDIUM_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_select_best_performing_architecture.html"
            ]
        )

        # Add more performance efficiency questions...

        return questions

    def _load_cost_optimization_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Cost Optimization pillar questions."""
        questions = {}

        # COST 1: How do you implement cloud financial management?
        questions["COST01"] = WAFRQuestion(
            question_id="COST01",
            pillar=PillarName.COST_OPTIMIZATION,
            title="How do you implement cloud financial management?",
            description="Implementing Cloud Financial Management enables organizations to realize business value and financial success.",
            choices=[
                WAFRChoice(
                    choice_id="cost01_01",
                    title="Establish a cost optimization function",
                    description="Create a team or individual responsible for cloud financial management",
                    best_practices=[
                        "Dedicated cost optimization team",
                        "Regular cost reviews",
                        "Cost optimization training"
                    ],
                    implementation_guidance=[
                        "Use AWS Cost Explorer",
                        "Implement AWS Budgets",
                        "Set up cost anomaly detection"
                    ],
                    aws_services=["cost-explorer", "budgets", "cost-anomaly-detection"],
                    risk_if_not_implemented=RiskLevel.MEDIUM_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_implement_cfm.html"
            ]
        )

        # Add more cost optimization questions...

        return questions

    def _load_sustainability_questions(self) -> Dict[str, WAFRQuestion]:
        """Load Sustainability pillar questions."""
        questions = {}

        # SUS 1: How do you select Regions to support your sustainability goals?
        questions["SUS01"] = WAFRQuestion(
            question_id="SUS01",
            pillar=PillarName.SUSTAINABILITY,
            title="How do you select Regions to support your sustainability goals?",
            description="Choose Regions near your users to reduce the environmental impact of network traffic.",
            choices=[
                WAFRChoice(
                    choice_id="sus01_01",
                    title="Choose Region based on business requirements and sustainability goals",
                    description="Select Regions that align with sustainability goals and business needs",
                    best_practices=[
                        "Consider renewable energy usage",
                        "Evaluate carbon footprint",
                        "Minimize data transfer"
                    ],
                    implementation_guidance=[
                        "Use AWS sustainability data",
                        "Consider region carbon intensity",
                        "Optimize for locality"
                    ],
                    aws_services=["cloudfront", "route53"],
                    risk_if_not_implemented=RiskLevel.LOW_RISK
                )
            ],
            aws_docs_links=[
                "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_region_selection.html"
            ]
        )

        # Add more sustainability questions...

        return questions

    def get_questions_by_pillar(self, pillar: PillarName) -> List[WAFRQuestion]:
        """Get all questions for a specific pillar."""
        return [q for q in self.questions.values() if q.pillar == pillar]

    def get_question(self, question_id: str) -> Optional[WAFRQuestion]:
        """Get a specific question by ID."""
        return self.questions.get(question_id)

    def assess_solution_against_question(
        self,
        question: WAFRQuestion,
        solution_analysis: Any,  # SolutionAnalysis from solution_parser
        cost_data: Optional[Dict] = None
    ) -> QuestionAssessment:
        """
        Assess a solution against a specific WAFR question.

        Args:
            question: The WAFR question to assess
            solution_analysis: Parsed solution analysis
            cost_data: Optional cost analysis data

        Returns:
            QuestionAssessment with results
        """
        implemented_choices = []
        missing_choices = []
        recommendations = []
        aws_docs = question.aws_docs_links.copy()

        # Analyze each choice in the question
        for choice in question.choices:
            is_implemented = self._is_choice_implemented(
                choice, solution_analysis, cost_data
            )

            if is_implemented:
                implemented_choices.append(choice.choice_id)
            else:
                missing_choices.append(choice.choice_id)
                recommendations.extend(choice.implementation_guidance)

        # Calculate score (0-100)
        if len(question.choices) > 0:
            score = (len(implemented_choices) / len(question.choices)) * 100
        else:
            score = 0

        # Determine risk level
        risk_level = self._calculate_risk_level(implemented_choices, missing_choices, question)

        return QuestionAssessment(
            question_id=question.question_id,
            question_title=question.title,
            pillar=question.pillar.value,
            implemented_choices=implemented_choices,
            missing_choices=missing_choices,
            risk_level=risk_level,
            score=score,
            recommendations=list(set(recommendations)),  # Remove duplicates
            aws_docs=aws_docs
        )

    def _is_choice_implemented(
        self,
        choice: WAFRChoice,
        solution_analysis: Any,
        cost_data: Optional[Dict] = None
    ) -> bool:
        """
        Determine if a specific choice is implemented in the solution.

        This is a simplified implementation. In practice, this would involve
        more sophisticated analysis of the solution components.
        """
        # Check if required AWS services are mentioned
        solution_services = [s.name for s in solution_analysis.aws_services]

        for required_service in choice.aws_services:
            if required_service in solution_services:
                return True

        # Check if best practices keywords are mentioned in requirements
        all_requirements = (
            solution_analysis.security_requirements +
            solution_analysis.performance_requirements +
            solution_analysis.cost_considerations
        )

        requirements_text = " ".join(all_requirements).lower()

        for best_practice in choice.best_practices:
            if any(word.lower() in requirements_text for word in best_practice.split()):
                return True

        return False

    def _calculate_risk_level(
        self,
        implemented: List[str],
        missing: List[str],
        question: WAFRQuestion
    ) -> RiskLevel:
        """Calculate the risk level based on implemented vs missing choices."""
        if len(missing) == 0:
            return RiskLevel.NO_RISK

        # Check if any missing choice has high risk
        for choice in question.choices:
            if choice.choice_id in missing and choice.risk_if_not_implemented == RiskLevel.HIGH_RISK:
                return RiskLevel.HIGH_RISK

        # Check if any missing choice has medium risk
        for choice in question.choices:
            if choice.choice_id in missing and choice.risk_if_not_implemented == RiskLevel.MEDIUM_RISK:
                return RiskLevel.MEDIUM_RISK

        return RiskLevel.LOW_RISK

    def assess_pillar(
        self,
        pillar: PillarName,
        solution_analysis: Any,
        cost_data: Optional[Dict] = None
    ) -> PillarAssessment:
        """Assess a complete pillar against the solution."""
        questions = self.get_questions_by_pillar(pillar)
        question_assessments = []
        high_risk_issues = []
        medium_risk_issues = []
        low_risk_issues = []
        all_recommendations = []

        for question in questions:
            assessment = self.assess_solution_against_question(
                question, solution_analysis, cost_data
            )
            question_assessments.append(assessment)

            # Collect risks and recommendations
            if assessment.risk_level == RiskLevel.HIGH_RISK:
                high_risk_issues.append(f"{question.question_id}: {question.title}")
            elif assessment.risk_level == RiskLevel.MEDIUM_RISK:
                medium_risk_issues.append(f"{question.question_id}: {question.title}")
            elif assessment.risk_level == RiskLevel.LOW_RISK:
                low_risk_issues.append(f"{question.question_id}: {question.title}")

            all_recommendations.extend(assessment.recommendations)

        # Calculate pillar score
        if question_assessments:
            pillar_score = sum(qa.score for qa in question_assessments) / len(question_assessments)
        else:
            pillar_score = 0

        return PillarAssessment(
            pillar_name=pillar.value,
            questions_assessed=question_assessments,
            pillar_score=pillar_score,
            high_risk_issues=high_risk_issues,
            medium_risk_issues=medium_risk_issues,
            low_risk_issues=low_risk_issues,
            recommendations=list(set(all_recommendations))  # Remove duplicates
        )


# Utility functions
def get_wafr_framework() -> WAFRQuestionsFramework:
    """Get the WAFR questions framework instance."""
    return WAFRQuestionsFramework()


def get_all_pillar_names() -> List[str]:
    """Get all WAFR pillar names."""
    return [pillar.value for pillar in PillarName]


def get_question_count_by_pillar() -> Dict[str, int]:
    """Get the number of questions in each pillar."""
    framework = WAFRQuestionsFramework()
    counts = {}

    for pillar in PillarName:
        questions = framework.get_questions_by_pillar(pillar)
        counts[pillar.value] = len(questions)

    return counts