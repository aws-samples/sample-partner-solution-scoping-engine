"""AWS Cost Analysis Client

This module provides cost analysis capabilities including Cost Explorer integration,
pricing optimization, and financial impact assessment for WAFR assessments.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from .core.logger import setup_logger
from .core.error_handler import AWSIntegrationError, handle_graceful_degradation

logger = setup_logger(__name__)


class AWSCostAnalysisClient:
    """
    Client for AWS cost analysis and optimization.
    
    Provides cost optimization analysis, Reserved Instance recommendations,
    and financial impact assessment for WAFR assessments.
    """
    
    def __init__(self, aws_credentials: Optional[Dict[str, str]] = None):
        """
        Initialize AWS cost analysis client.
        
        Args:
            aws_credentials: Optional AWS credentials
        """
        from .consts import get_aws_region
        
        self.aws_credentials = aws_credentials
        self.region = get_aws_region()
        
        # Initialize clients (would use actual credentials in production)
        try:
            if aws_credentials:
                session = boto3.Session(
                    aws_access_key_id=aws_credentials.get('access_key_id'),
                    aws_secret_access_key=aws_credentials.get('secret_access_key'),
                    aws_session_token=aws_credentials.get('session_token')
                )
            else:
                session = boto3.Session()
            
            # Note: Cost Explorer and Pricing APIs are global services but require us-east-1
            self.cost_explorer = session.client('ce', region_name='us-east-1')
            self.pricing = session.client('pricing', region_name='us-east-1')
            
        except Exception as e:
            logger.warning(f"Could not initialize AWS clients: {e}")
            self.cost_explorer = None
            self.pricing = None
        
        # Load pricing data and optimization rules
        self.pricing_data = self._load_pricing_data()
        self.optimization_rules = self._load_optimization_rules()
        
        logger.info("Initialized AWS Cost Analysis Client")
    
    async def analyze_cost_optimization(self, services: List[str], usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze cost optimization opportunities.
        
        Args:
            services: List of AWS services in use
            usage_patterns: Expected or current usage patterns
            
        Returns:
            Cost optimization analysis with recommendations
        """
        try:
            logger.info(f"Analyzing cost optimization for {len(services)} services")
            
            optimization_analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "services_analyzed": services,
                "usage_patterns": usage_patterns,
                "optimization_opportunities": [],
                "potential_savings": 0.0,
                "recommendations": [],
                "reserved_instance_analysis": {},
                "savings_plan_analysis": {}
            }
            
            # Analyze each service for optimization opportunities
            total_savings = 0.0
            
            for service in services:
                service_analysis = await self._analyze_service_cost_optimization(service, usage_patterns)
                optimization_analysis["optimization_opportunities"].append(service_analysis)
                total_savings += service_analysis.get("potential_savings", 0.0)
            
            optimization_analysis["potential_savings"] = total_savings
            
            # Generate Reserved Instance recommendations
            if "ec2" in services:
                ri_analysis = await self._analyze_reserved_instances(usage_patterns)
                optimization_analysis["reserved_instance_analysis"] = ri_analysis
            
            # Generate Savings Plan recommendations
            sp_analysis = await self._analyze_savings_plans(services, usage_patterns)
            optimization_analysis["savings_plan_analysis"] = sp_analysis
            
            # Generate overall recommendations
            optimization_analysis["recommendations"] = self._generate_cost_recommendations(
                optimization_analysis["optimization_opportunities"],
                optimization_analysis["reserved_instance_analysis"],
                optimization_analysis["savings_plan_analysis"]
            )
            
            logger.info(f"Cost optimization analysis completed: ${total_savings:.2f} potential savings")
            return optimization_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing cost optimization: {e}")
            return handle_graceful_degradation(e, "cost_optimization", {
                "services_analyzed": services,
                "error": str(e),
                "potential_savings": 0.0
            })
    
    async def get_current_pricing(self, services: List[str], regions: List[str]) -> Dict[str, Any]:
        """
        Get current AWS pricing information.
        
        Args:
            services: List of AWS services
            regions: List of AWS regions
            
        Returns:
            Current pricing data for services and regions
        """
        try:
            logger.info(f"Retrieving pricing for {len(services)} services in {len(regions)} regions")
            
            pricing_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": services,
                "regions": regions,
                "service_pricing": {},
                "regional_variations": {},
                "pricing_models": {}
            }
            
            # Get pricing for each service
            for service in services:
                service_pricing = await self._get_service_pricing(service, regions)
                pricing_info["service_pricing"][service] = service_pricing
            
            # Analyze regional pricing variations
            pricing_info["regional_variations"] = self._analyze_regional_pricing_variations(
                pricing_info["service_pricing"], regions
            )
            
            # Get available pricing models
            pricing_info["pricing_models"] = self._get_pricing_models(services)
            
            logger.info(f"Retrieved pricing information for {len(services)} services")
            return pricing_info
            
        except Exception as e:
            logger.error(f"Error retrieving pricing information: {e}")
            return handle_graceful_degradation(e, "pricing_information", {
                "services": services,
                "regions": regions,
                "error": str(e),
                "service_pricing": {}
            })
    
    async def estimate_financial_impact(
        self, 
        risk_items: List[Dict[str, Any]], 
        current_costs: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Estimate financial impact of identified risks.
        
        Args:
            risk_items: List of identified risk items
            current_costs: Optional current cost information
            
        Returns:
            Financial impact analysis
        """
        try:
            logger.info(f"Estimating financial impact for {len(risk_items)} risk items")
            
            impact_analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "risk_items_analyzed": len(risk_items),
                "current_costs": current_costs or {},
                "financial_impacts": [],
                "total_potential_cost": 0.0,
                "cost_avoidance_opportunities": 0.0,
                "roi_analysis": {}
            }
            
            total_potential_cost = 0.0
            total_cost_avoidance = 0.0
            
            # Analyze financial impact of each risk
            for risk_item in risk_items:
                financial_impact = self._calculate_risk_financial_impact(risk_item, current_costs)
                impact_analysis["financial_impacts"].append(financial_impact)
                
                total_potential_cost += financial_impact.get("potential_cost", 0.0)
                total_cost_avoidance += financial_impact.get("cost_avoidance", 0.0)
            
            impact_analysis["total_potential_cost"] = total_potential_cost
            impact_analysis["cost_avoidance_opportunities"] = total_cost_avoidance
            
            # Calculate ROI for addressing risks
            impact_analysis["roi_analysis"] = self._calculate_risk_roi(
                impact_analysis["financial_impacts"]
            )
            
            logger.info(f"Financial impact analysis: ${total_potential_cost:.2f} potential cost, ${total_cost_avoidance:.2f} avoidance")
            return impact_analysis
            
        except Exception as e:
            logger.error(f"Error estimating financial impact: {e}")
            return handle_graceful_degradation(e, "financial_impact", {
                "risk_items_analyzed": len(risk_items),
                "error": str(e),
                "total_potential_cost": 0.0
            })
    
    def _load_pricing_data(self) -> Dict[str, Any]:
        """Load AWS pricing data (simplified for demonstration)."""
        
        return {
            "ec2": {
                "on_demand": {
                    "t3.micro": {"us-east-1": 0.0104, "us-west-2": 0.0104, "eu-west-1": 0.0114},
                    "t3.small": {"us-east-1": 0.0208, "us-west-2": 0.0208, "eu-west-1": 0.0228},
                    "m5.large": {"us-east-1": 0.096, "us-west-2": 0.096, "eu-west-1": 0.105}
                },
                "reserved": {
                    "t3.micro": {"us-east-1": 0.0062, "us-west-2": 0.0062, "eu-west-1": 0.0068},
                    "t3.small": {"us-east-1": 0.0125, "us-west-2": 0.0125, "eu-west-1": 0.0137},
                    "m5.large": {"us-east-1": 0.058, "us-west-2": 0.058, "eu-west-1": 0.063}
                }
            },
            "s3": {
                "standard": {"us-east-1": 0.023, "us-west-2": 0.023, "eu-west-1": 0.024},
                "ia": {"us-east-1": 0.0125, "us-west-2": 0.0125, "eu-west-1": 0.013},
                "glacier": {"us-east-1": 0.004, "us-west-2": 0.004, "eu-west-1": 0.0045}
            },
            "lambda": {
                "requests": {"us-east-1": 0.0000002, "us-west-2": 0.0000002, "eu-west-1": 0.0000002},
                "duration_gb_second": {"us-east-1": 0.0000166667, "us-west-2": 0.0000166667, "eu-west-1": 0.0000166667}
            }
        }
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load cost optimization rules."""
        
        return {
            "ec2": {
                "right_sizing": {
                    "cpu_threshold": 0.1,  # 10% average CPU utilization
                    "memory_threshold": 0.2,  # 20% average memory utilization
                    "savings_potential": 0.3  # 30% potential savings
                },
                "reserved_instances": {
                    "utilization_threshold": 0.7,  # 70% utilization for RI recommendation
                    "savings_potential": 0.4  # 40% potential savings
                },
                "spot_instances": {
                    "fault_tolerance_required": True,
                    "savings_potential": 0.7  # 70% potential savings
                }
            },
            "s3": {
                "lifecycle_policies": {
                    "ia_transition_days": 30,
                    "glacier_transition_days": 90,
                    "savings_potential": 0.5  # 50% potential savings
                },
                "intelligent_tiering": {
                    "object_size_threshold": 128,  # 128KB minimum
                    "savings_potential": 0.3  # 30% potential savings
                }
            },
            "lambda": {
                "memory_optimization": {
                    "duration_threshold": 1000,  # 1 second
                    "savings_potential": 0.2  # 20% potential savings
                }
            }
        }
    
    async def _analyze_service_cost_optimization(self, service: str, usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cost optimization for a specific service."""
        
        service_rules = self.optimization_rules.get(service.lower(), {})
        service_usage = usage_patterns.get(service.lower(), {})
        
        optimization = {
            "service": service,
            "current_usage": service_usage,
            "optimization_opportunities": [],
            "potential_savings": 0.0,
            "recommendations": []
        }
        
        if service.lower() == "ec2":
            # Right-sizing analysis
            if service_usage.get("cpu_utilization", 1.0) < service_rules.get("right_sizing", {}).get("cpu_threshold", 0.1):
                savings = service_usage.get("monthly_cost", 100) * service_rules.get("right_sizing", {}).get("savings_potential", 0.3)
                optimization["optimization_opportunities"].append({
                    "type": "right_sizing",
                    "description": "Instance appears over-provisioned based on CPU utilization",
                    "potential_savings": savings
                })
                optimization["potential_savings"] += savings
            
            # Reserved Instance analysis
            if service_usage.get("utilization", 1.0) > service_rules.get("reserved_instances", {}).get("utilization_threshold", 0.7):
                savings = service_usage.get("monthly_cost", 100) * service_rules.get("reserved_instances", {}).get("savings_potential", 0.4)
                optimization["optimization_opportunities"].append({
                    "type": "reserved_instances",
                    "description": "High utilization makes Reserved Instances cost-effective",
                    "potential_savings": savings
                })
                optimization["potential_savings"] += savings
        
        elif service.lower() == "s3":
            # Lifecycle policy analysis
            if not service_usage.get("lifecycle_policies", False):
                savings = service_usage.get("monthly_cost", 50) * service_rules.get("lifecycle_policies", {}).get("savings_potential", 0.5)
                optimization["optimization_opportunities"].append({
                    "type": "lifecycle_policies",
                    "description": "Implement lifecycle policies to transition to cheaper storage classes",
                    "potential_savings": savings
                })
                optimization["potential_savings"] += savings
        
        # Generate recommendations
        for opportunity in optimization["optimization_opportunities"]:
            optimization["recommendations"].append(f"Implement {opportunity['type']} for {service}")
        
        return optimization
    
    async def _analyze_reserved_instances(self, usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Reserved Instance opportunities."""
        
        ec2_usage = usage_patterns.get("ec2", {})
        
        return {
            "eligible_instances": ec2_usage.get("instance_count", 0),
            "utilization_rate": ec2_usage.get("utilization", 0.8),
            "recommended_ris": ec2_usage.get("instance_count", 0) if ec2_usage.get("utilization", 0) > 0.7 else 0,
            "potential_savings": ec2_usage.get("monthly_cost", 100) * 0.4 if ec2_usage.get("utilization", 0) > 0.7 else 0,
            "payback_period_months": 12
        }
    
    async def _analyze_savings_plans(self, services: List[str], usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Savings Plan opportunities."""
        
        total_compute_cost = 0
        for service in ["ec2", "lambda", "fargate"]:
            if service in services:
                total_compute_cost += usage_patterns.get(service, {}).get("monthly_cost", 0)
        
        return {
            "eligible_services": [s for s in services if s.lower() in ["ec2", "lambda", "fargate"]],
            "monthly_compute_cost": total_compute_cost,
            "recommended_commitment": total_compute_cost * 0.8,  # 80% of usage
            "potential_savings": total_compute_cost * 0.17,  # 17% average savings
            "commitment_term": "1-year"
        }
    
    def _generate_cost_recommendations(
        self, 
        optimization_opportunities: List[Dict[str, Any]], 
        ri_analysis: Dict[str, Any], 
        sp_analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate cost optimization recommendations."""
        
        recommendations = []
        
        # Service-specific recommendations
        for opportunity in optimization_opportunities:
            for rec in opportunity.get("recommendations", []):
                recommendations.append({
                    "type": "service_optimization",
                    "service": opportunity["service"],
                    "recommendation": rec,
                    "potential_savings": f"${opportunity['potential_savings']:.2f}/month"
                })
        
        # Reserved Instance recommendations
        if ri_analysis.get("recommended_ris", 0) > 0:
            recommendations.append({
                "type": "reserved_instances",
                "service": "ec2",
                "recommendation": f"Purchase {ri_analysis['recommended_ris']} Reserved Instances",
                "potential_savings": f"${ri_analysis['potential_savings']:.2f}/month"
            })
        
        # Savings Plan recommendations
        if sp_analysis.get("potential_savings", 0) > 0:
            recommendations.append({
                "type": "savings_plans",
                "service": "compute",
                "recommendation": f"Commit to ${sp_analysis['recommended_commitment']:.2f}/month Savings Plan",
                "potential_savings": f"${sp_analysis['potential_savings']:.2f}/month"
            })
        
        return recommendations
    
    async def _get_service_pricing(self, service: str, regions: List[str]) -> Dict[str, Any]:
        """Get pricing information for a service across regions."""
        
        service_pricing = self.pricing_data.get(service.lower(), {})
        
        pricing_info = {
            "service": service,
            "pricing_models": list(service_pricing.keys()),
            "regional_pricing": {}
        }
        
        for region in regions:
            pricing_info["regional_pricing"][region] = {}
            
            for model, model_pricing in service_pricing.items():
                if isinstance(model_pricing, dict):
                    pricing_info["regional_pricing"][region][model] = {}
                    
                    for resource, resource_pricing in model_pricing.items():
                        if isinstance(resource_pricing, dict):
                            pricing_info["regional_pricing"][region][model][resource] = resource_pricing.get(region, 0.0)
                        else:
                            pricing_info["regional_pricing"][region][model] = resource_pricing
        
        return pricing_info
    
    def _analyze_regional_pricing_variations(self, service_pricing: Dict[str, Any], regions: List[str]) -> Dict[str, Any]:
        """Analyze pricing variations across regions."""
        
        variations = {}
        
        for service, pricing_info in service_pricing.items():
            regional_pricing = pricing_info.get("regional_pricing", {})
            
            if len(regions) > 1:
                # Find cheapest and most expensive regions
                region_costs = {}
                
                for region in regions:
                    region_data = regional_pricing.get(region, {})
                    # Simplified cost calculation
                    total_cost = 0
                    count = 0
                    
                    for model, model_data in region_data.items():
                        if isinstance(model_data, dict):
                            for resource, cost in model_data.items():
                                if isinstance(cost, (int, float)):
                                    total_cost += cost
                                    count += 1
                        elif isinstance(model_data, (int, float)):
                            total_cost += model_data
                            count += 1
                    
                    if count > 0:
                        region_costs[region] = total_cost / count
                
                if region_costs:
                    cheapest_region = min(region_costs, key=region_costs.get)
                    most_expensive_region = max(region_costs, key=region_costs.get)
                    
                    variations[service] = {
                        "cheapest_region": cheapest_region,
                        "most_expensive_region": most_expensive_region,
                        "cost_difference_percent": ((region_costs[most_expensive_region] - region_costs[cheapest_region]) / region_costs[cheapest_region]) * 100 if region_costs[cheapest_region] > 0 else 0
                    }
        
        return variations
    
    def _get_pricing_models(self, services: List[str]) -> Dict[str, List[str]]:
        """Get available pricing models for services."""
        
        pricing_models = {}
        
        for service in services:
            service_data = self.pricing_data.get(service.lower(), {})
            pricing_models[service] = list(service_data.keys())
        
        return pricing_models
    
    def _calculate_risk_financial_impact(self, risk_item: Dict[str, Any], current_costs: Dict[str, float]) -> Dict[str, Any]:
        """Calculate financial impact of a specific risk."""
        
        risk_type = risk_item.get("type", "unknown")
        severity = risk_item.get("severity", "medium")
        affected_services = risk_item.get("affected_services", [])
        
        # Base impact multipliers by severity
        impact_multipliers = {
            "high": 0.5,    # 50% potential cost increase
            "medium": 0.2,  # 20% potential cost increase
            "low": 0.05     # 5% potential cost increase
        }
        
        multiplier = impact_multipliers.get(severity, 0.2)
        
        # Calculate potential cost based on affected services
        potential_cost = 0.0
        cost_avoidance = 0.0
        
        for service in affected_services:
            service_cost = current_costs.get(service, 100)  # Default $100/month
            
            if risk_type in ["security", "compliance"]:
                # Security/compliance risks can have high financial impact
                potential_cost += service_cost * multiplier * 2  # Double impact
                cost_avoidance += service_cost * multiplier * 1.5
            elif risk_type in ["performance", "reliability"]:
                # Performance/reliability risks affect operational costs
                potential_cost += service_cost * multiplier
                cost_avoidance += service_cost * multiplier * 0.8
            else:
                # General risks
                potential_cost += service_cost * multiplier * 0.5
                cost_avoidance += service_cost * multiplier * 0.3
        
        return {
            "risk_id": risk_item.get("id", "unknown"),
            "risk_type": risk_type,
            "severity": severity,
            "affected_services": affected_services,
            "potential_cost": potential_cost,
            "cost_avoidance": cost_avoidance,
            "impact_description": f"{severity.title()} {risk_type} risk with potential ${potential_cost:.2f}/month impact"
        }
    
    def _calculate_risk_roi(self, financial_impacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate ROI for addressing risks."""
        
        total_potential_cost = sum(impact.get("potential_cost", 0) for impact in financial_impacts)
        total_cost_avoidance = sum(impact.get("cost_avoidance", 0) for impact in financial_impacts)
        
        # Estimate implementation cost (simplified)
        implementation_cost = total_cost_avoidance * 0.2  # 20% of potential savings
        
        # Calculate ROI
        roi_percentage = ((total_cost_avoidance - implementation_cost) / implementation_cost * 100) if implementation_cost > 0 else 0
        payback_months = (implementation_cost / (total_cost_avoidance / 12)) if total_cost_avoidance > 0 else 0
        
        return {
            "total_potential_cost": total_potential_cost,
            "total_cost_avoidance": total_cost_avoidance,
            "implementation_cost": implementation_cost,
            "roi_percentage": roi_percentage,
            "payback_period_months": payback_months,
            "net_benefit_annual": (total_cost_avoidance * 12) - implementation_cost
        }
