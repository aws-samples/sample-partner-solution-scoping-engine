"""
Business Impact Quantifier for WAFR Report Content Improvement.

This module translates technical risks into business metrics, including downtime estimates,
outage costs, security risk scores (CVSS), compliance gaps, and cost optimization potential.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from .logger import WAFRLogger


@dataclass
class DowntimeRisk:
    """Represents potential downtime risk."""
    
    hours_per_month: str  # e.g., "2-4"
    probability: str  # "low", "medium", "high"
    affected_users: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hours_per_month": self.hours_per_month,
            "probability": self.probability,
            "affected_users": self.affected_users
        }


@dataclass
class OutageCost:
    """Represents financial impact of outages."""
    
    per_hour: str  # e.g., "$5,000"
    per_month_risk: str  # e.g., "$10,000-20,000"
    calculation_basis: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "per_hour": self.per_hour,
            "per_month_risk": self.per_month_risk,
            "calculation_basis": self.calculation_basis
        }


@dataclass
class SecurityRisk:
    """Represents security risk assessment."""
    
    cvss_score: float
    severity: str  # "Critical", "High", "Medium", "Low"
    attack_vector: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cvss_score": self.cvss_score,
            "severity": self.severity,
            "attack_vector": self.attack_vector,
            "description": self.description
        }


@dataclass
class ComplianceGap:
    """Represents a compliance framework gap."""
    
    framework: str  # e.g., "SOC 2", "HIPAA", "PCI-DSS", "GDPR"
    requirement: str
    gap: str
    remediation_priority: str  # "Critical", "High", "Medium", "Low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "framework": self.framework,
            "requirement": self.requirement,
            "gap": self.gap,
            "remediation_priority": self.remediation_priority
        }


@dataclass
class CostSavingsPotential:
    """Represents cost optimization opportunities."""
    
    monthly_savings: str  # e.g., "$500-800"
    actions: List[str]
    roi_months: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "monthly_savings": self.monthly_savings,
            "actions": self.actions,
            "roi_months": self.roi_months
        }


@dataclass
class BusinessImpact:
    """Comprehensive business impact assessment."""
    
    potential_downtime: Optional[DowntimeRisk] = None
    outage_cost: Optional[OutageCost] = None
    security_risk: Optional[SecurityRisk] = None
    compliance_gaps: List[ComplianceGap] = field(default_factory=list)
    cost_savings_potential: Optional[CostSavingsPotential] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "potential_downtime": self.potential_downtime.to_dict() if self.potential_downtime else None,
            "outage_cost": self.outage_cost.to_dict() if self.outage_cost else None,
            "security_risk": self.security_risk.to_dict() if self.security_risk else None,
            "compliance_gaps": [gap.to_dict() for gap in self.compliance_gaps],
            "cost_savings_potential": self.cost_savings_potential.to_dict() if self.cost_savings_potential else None
        }


class BusinessImpactQuantifier:
    """
    Quantifies business impact of technical risks and opportunities.

    This quantifier translates WAFR assessment findings into business metrics
    that stakeholders can use for prioritization and budget justification.
    """

    # Workload type cost multipliers (cost per hour of outage)
    WORKLOAD_COST_MULTIPLIERS = {
        "production_api": 5000,
        "production_web": 3000,
        "production_data": 4000,
        "production_batch": 1000,
        "staging": 100,
        "development": 50,
        "internal_tool": 500,
        "customer_facing": 4000,
        "mission_critical": 10000
    }

    # Compliance framework requirements mapping
    COMPLIANCE_FRAMEWORKS = {
        "SOC 2": {
            "encryption_at_rest": "CC6.1 - Encryption of data at rest",
            "encryption_in_transit": "CC6.1 - Encryption of data in transit",
            "access_logging": "CC7.2 - System monitoring and logging",
            "backup": "A1.2 - Backup and recovery procedures",
            "monitoring": "CC7.2 - Continuous monitoring",
            "mfa": "CC6.2 - Multi-factor authentication",
            "least_privilege": "CC6.3 - Least privilege access"
        },
        "HIPAA": {
            "encryption_at_rest": "164.312(a)(2)(iv) - Encryption",
            "encryption_in_transit": "164.312(e)(1) - Transmission security",
            "access_logging": "164.312(b) - Audit controls",
            "backup": "164.308(a)(7)(ii)(A) - Data backup plan",
            "access_control": "164.312(a)(1) - Access control"
        },
        "PCI-DSS": {
            "encryption_at_rest": "Requirement 3.4 - Encryption of cardholder data",
            "encryption_in_transit": "Requirement 4.1 - Encryption during transmission",
            "access_logging": "Requirement 10 - Track and monitor access",
            "network_segmentation": "Requirement 1 - Network segmentation",
            "vulnerability_scanning": "Requirement 11.2 - Vulnerability scans"
        },
        "GDPR": {
            "encryption": "Article 32 - Security of processing",
            "access_logging": "Article 30 - Records of processing activities",
            "backup": "Article 32 - Availability and resilience",
            "data_retention": "Article 5 - Storage limitation"
        }
    }

    # CVSS score mappings for common security gaps
    SECURITY_CVSS_SCORES = {
        "no_encryption_at_rest": 7.5,
        "no_encryption_in_transit": 8.1,
        "no_waf": 7.3,
        "public_s3_bucket": 9.1,
        "no_mfa": 6.5,
        "overly_permissive_iam": 7.8,
        "no_vpc": 8.5,
        "missing_security_groups": 7.0,
        "no_logging": 5.3,
        "no_monitoring": 4.8
    }

    def __init__(self):
        """Initialize the BusinessImpactQuantifier."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("BusinessImpactQuantifier initialized")

    def estimate_downtime_risk(
        self,
        reliability_score: float,
        detected_services: List[str],
        workload_type: str = "production_api"
    ) -> DowntimeRisk:
        """
        Estimate potential downtime risk based on reliability score.

        Args:
            reliability_score: Reliability pillar score (0-100)
            detected_services: List of AWS services in architecture
            workload_type: Type of workload (production_api, staging, etc.)

        Returns:
            DowntimeRisk object with estimates
        """
        self.logger.info(
            f"Estimating downtime risk: score={reliability_score}, "
            f"workload={workload_type}, services={len(detected_services)}"
        )

        # Calculate downtime hours based on score
        if reliability_score >= 90:
            hours_range = "0.5-1"
            probability = "low"
        elif reliability_score >= 75:
            hours_range = "1-2"
            probability = "low"
        elif reliability_score >= 60:
            hours_range = "2-4"
            probability = "medium"
        elif reliability_score >= 40:
            hours_range = "4-8"
            probability = "medium"
        else:
            hours_range = "8-16"
            probability = "high"

        # Determine affected users based on workload type
        workload_str = str(workload_type).lower() if workload_type else "general"
        if "production" in workload_str:
            affected_users = "All production users"
        elif "staging" in workload_str:
            affected_users = "Development and QA teams"
        elif "internal" in workload_str:
            affected_users = "Internal employees"
        else:
            affected_users = "Subset of users"

        return DowntimeRisk(
            hours_per_month=hours_range,
            probability=probability,
            affected_users=affected_users
        )

    def calculate_outage_cost(
        self,
        workload_type: str,
        criticality: str,
        detected_services: List[str],
        downtime_hours: Optional[str] = None
    ) -> OutageCost:
        """
        Calculate financial impact of potential outages.

        Args:
            workload_type: Type of workload
            criticality: Criticality level (critical, high, medium, low)
            detected_services: List of AWS services
            downtime_hours: Optional downtime estimate (e.g., "2-4")

        Returns:
            OutageCost object with financial estimates
        """
        self.logger.info(
            f"Calculating outage cost: workload={workload_type}, "
            f"criticality={criticality}"
        )

        # Get base cost per hour
        workload_str = str(workload_type).lower() if workload_type else "production_api"
        base_cost = self.WORKLOAD_COST_MULTIPLIERS.get(
            workload_str,
            2000  # Default
        )

        # Apply criticality multiplier
        criticality_multipliers = {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5
        }
        criticality_str = str(criticality).lower() if criticality else "medium"
        multiplier = criticality_multipliers.get(criticality_str, 1.0)
        cost_per_hour = int(base_cost * multiplier)

        # Calculate monthly risk if downtime hours provided
        if downtime_hours:
            try:
                # Parse range like "2-4"
                parts = downtime_hours.split("-")
                min_hours = float(parts[0])
                max_hours = float(parts[1]) if len(parts) > 1 else min_hours
                min_cost = int(min_hours * cost_per_hour)
                max_cost = int(max_hours * cost_per_hour)
                per_month_risk = f"${min_cost:,}-${max_cost:,}"
            except (ValueError, IndexError):
                per_month_risk = f"${cost_per_hour * 2:,}-${cost_per_hour * 4:,}"
        else:
            per_month_risk = f"${cost_per_hour * 2:,}-${cost_per_hour * 4:,}"

        # Generate calculation basis
        calculation_basis = (
            f"Based on {workload_type} workload with {criticality} criticality. "
            f"Includes revenue loss, SLA penalties, and recovery costs."
        )

        return OutageCost(
            per_hour=f"${cost_per_hour:,}",
            per_month_risk=per_month_risk,
            calculation_basis=calculation_basis
        )

    def assess_security_risk(
        self,
        security_score: float,
        missing_capabilities: List[str]
    ) -> SecurityRisk:
        """
        Assess security risk using CVSS scoring.

        Args:
            security_score: Security pillar score (0-100)
            missing_capabilities: List of missing security capabilities

        Returns:
            SecurityRisk object with CVSS score and details
        """
        self.logger.info(
            f"Assessing security risk: score={security_score}, "
            f"missing_capabilities={len(missing_capabilities)}"
        )

        # Calculate CVSS score based on missing capabilities
        cvss_scores = []
        attack_vectors = []

        for capability in missing_capabilities:
            capability_lower = capability.lower()

            # Check for known security gaps
            for gap_key, cvss in self.SECURITY_CVSS_SCORES.items():
                if gap_key.replace("_", " ") in capability_lower or \
                   capability_lower in gap_key.replace("_", " "):
                    cvss_scores.append(cvss)

                    # Determine attack vector
                    if "encryption" in capability_lower:
                        attack_vectors.append("Data interception")
                    elif "waf" in capability_lower:
                        attack_vectors.append("Web application attacks")
                    elif "iam" in capability_lower or "access" in capability_lower:
                        attack_vectors.append("Unauthorized access")
                    elif "vpc" in capability_lower or "network" in capability_lower:
                        attack_vectors.append("Network intrusion")
                    elif "logging" in capability_lower or "monitoring" in capability_lower:
                        attack_vectors.append("Undetected breaches")

        # Use highest CVSS score or calculate from security score
        if cvss_scores:
            cvss_score = max(cvss_scores)
        else:
            # Derive CVSS from security score
            cvss_score = round(10.0 - (security_score / 10.0), 1)

        # Determine severity
        if cvss_score >= 9.0:
            severity = "Critical"
        elif cvss_score >= 7.0:
            severity = "High"
        elif cvss_score >= 4.0:
            severity = "Medium"
        else:
            severity = "Low"

        # Generate description
        if missing_capabilities:
            description = (
                f"Missing {len(missing_capabilities)} security capabilities: "
                f"{', '.join(missing_capabilities[:3])}"
                + ("..." if len(missing_capabilities) > 3 else "")
            )
        else:
            description = "General security posture needs improvement"

        # Combine attack vectors
        attack_vector = ", ".join(set(attack_vectors)) if attack_vectors else "Multiple vectors"

        return SecurityRisk(
            cvss_score=cvss_score,
            severity=severity,
            attack_vector=attack_vector,
            description=description
        )

    def identify_compliance_gaps(
        self,
        detected_capabilities: List[str],
        industry: Optional[str] = None,
        workload_type: Optional[str] = None
    ) -> List[ComplianceGap]:
        """
        Identify compliance framework gaps.

        Args:
            detected_capabilities: List of capabilities present in architecture
            industry: Industry type (healthcare, finance, etc.)
            workload_type: Type of workload

        Returns:
            List of ComplianceGap objects
        """
        self.logger.info(
            f"Identifying compliance gaps: industry={industry}, "
            f"capabilities={len(detected_capabilities)}"
        )

        gaps = []
        # Handle both string and dict formats for detected_capabilities
        detected_lower = []
        for cap in detected_capabilities:
            if isinstance(cap, dict):
                detected_lower.append(cap.get('name', '').lower())
            elif isinstance(cap, str):
                detected_lower.append(cap.lower())
            else:
                detected_lower.append(str(cap).lower())

        # Determine applicable frameworks
        applicable_frameworks = ["SOC 2"]  # Always applicable

        if industry:
            industry_lower = industry.lower()
            if "health" in industry_lower or "medical" in industry_lower:
                applicable_frameworks.append("HIPAA")
            if "finance" in industry_lower or "payment" in industry_lower:
                applicable_frameworks.append("PCI-DSS")

        # Always check GDPR for data processing
        applicable_frameworks.append("GDPR")

        # Check each framework
        for framework in applicable_frameworks:
            if framework not in self.COMPLIANCE_FRAMEWORKS:
                continue

            requirements = self.COMPLIANCE_FRAMEWORKS[framework]

            for capability, requirement in requirements.items():
                # Check if capability is present
                capability_present = any(
                    capability.replace("_", " ") in cap or
                    cap in capability.replace("_", " ")
                    for cap in detected_lower
                )

                if not capability_present:
                    # Determine priority
                    if "encryption" in capability or "access" in capability:
                        priority = "Critical"
                    elif "logging" in capability or "monitoring" in capability:
                        priority = "High"
                    elif "backup" in capability:
                        priority = "High"
                    else:
                        priority = "Medium"

                    gaps.append(ComplianceGap(
                        framework=framework,
                        requirement=requirement,
                        gap=f"Missing {capability.replace('_', ' ')}",
                        remediation_priority=priority
                    ))

        self.logger.info(f"Identified {len(gaps)} compliance gaps")
        return gaps

    def calculate_cost_savings(
        self,
        cost_optimization_score: float,
        detected_services: List[str]
    ) -> CostSavingsPotential:
        """
        Calculate potential cost savings from optimization.

        Args:
            cost_optimization_score: Cost optimization pillar score (0-100)
            detected_services: List of AWS services in architecture

        Returns:
            CostSavingsPotential object with savings estimates
        """
        self.logger.info(
            f"Calculating cost savings: score={cost_optimization_score}, "
            f"services={len(detected_services)}"
        )

        # Estimate savings based on score gap
        score_gap = 100 - cost_optimization_score
        base_savings = int(score_gap * 10)  # $10 per point

        # Service-specific savings opportunities
        actions = []
        service_savings = 0

        services_lower = [s.lower() for s in detected_services]

        if any("lambda" in s for s in services_lower):
            actions.append("Right-size Lambda memory allocation")
            service_savings += 200

        if any("dynamodb" in s for s in services_lower):
            actions.append("Enable DynamoDB auto-scaling and on-demand pricing")
            service_savings += 300

        if any("s3" in s for s in services_lower):
            actions.append("Implement S3 Intelligent-Tiering and lifecycle policies")
            service_savings += 150

        if any("ec2" in s or "rds" in s for s in services_lower):
            actions.append("Use Reserved Instances or Savings Plans")
            service_savings += 500

        if any("cloudwatch" in s for s in services_lower):
            actions.append("Optimize CloudWatch Logs retention")
            service_savings += 100

        if any("nat" in s or "vpc" in s for s in services_lower):
            actions.append("Optimize NAT Gateway usage")
            service_savings += 200

        # Calculate total savings
        total_savings = base_savings + service_savings
        min_savings = int(total_savings * 0.8)
        max_savings = int(total_savings * 1.2)

        # Calculate ROI (assume implementation cost is 20 hours at $150/hour)
        implementation_cost = 3000
        roi_months = round(implementation_cost / total_savings, 1)

        if not actions:
            actions = ["Review and optimize resource utilization"]

        return CostSavingsPotential(
            monthly_savings=f"${min_savings:,}-${max_savings:,}",
            actions=actions,
            roi_months=roi_months
        )

    def quantify_business_impact(
        self,
        pillar_scores: Dict[str, float],
        detected_services: List[str],
        detected_capabilities: List[str],
        missing_capabilities: Dict[str, List[str]],
        workload_type: str = "production_api",
        criticality: str = "high",
        industry: Optional[str] = None
    ) -> BusinessImpact:
        """
        Generate comprehensive business impact assessment.

        Args:
            pillar_scores: Dictionary of pillar scores
            detected_services: List of AWS services
            detected_capabilities: List of present capabilities
            missing_capabilities: Dictionary of missing capabilities by pillar
            workload_type: Type of workload
            criticality: Criticality level
            industry: Industry type

        Returns:
            BusinessImpact object with all quantified metrics
        """
        self.logger.info("Generating comprehensive business impact assessment")

        impact = BusinessImpact()

        # Estimate downtime risk from reliability score
        if "reliability" in pillar_scores:
            downtime = self.estimate_downtime_risk(
                pillar_scores["reliability"],
                detected_services,
                workload_type
            )
            impact.potential_downtime = downtime

            # Calculate outage cost
            impact.outage_cost = self.calculate_outage_cost(
                workload_type,
                criticality,
                detected_services,
                downtime.hours_per_month
            )

        # Assess security risk
        if "security" in pillar_scores:
            security_missing = missing_capabilities.get("security", [])
            impact.security_risk = self.assess_security_risk(
                pillar_scores["security"],
                security_missing
            )

        # Identify compliance gaps
        impact.compliance_gaps = self.identify_compliance_gaps(
            detected_capabilities,
            industry,
            workload_type
        )

        # Calculate cost savings potential
        if "cost_optimization" in pillar_scores:
            impact.cost_savings_potential = self.calculate_cost_savings(
                pillar_scores["cost_optimization"],
                detected_services
            )

        self.logger.info("Business impact assessment completed")
        return impact
