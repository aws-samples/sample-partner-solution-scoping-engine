"""AWS Service Information Client

This module provides real-time AWS service information including availability,
limits, quotas, and regional capabilities for WAFR assessments.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from .core.logger import setup_logger
from .core.error_handler import AWSIntegrationError, handle_graceful_degradation

logger = setup_logger(__name__)


class AWSServiceInfoClient:
    """
    Client for real-time AWS service information.
    
    Provides current service availability, limits, quotas, and regional
    capabilities for accurate WAFR assessments.
    """
    
    def __init__(self, aws_credentials: Optional[Dict[str, str]] = None):
        """
        Initialize AWS service info client.
        
        Args:
            aws_credentials: Optional AWS credentials
        """
        self.aws_credentials = aws_credentials
        self.region_clients = {}
        
        # Service availability data (would be updated from AWS APIs in production)
        self.service_availability = self._load_service_availability_data()
        
        logger.info("Initialized AWS Service Info Client")
    
    async def check_service_availability(self, services: List[str], regions: List[str]) -> Dict[str, Any]:
        """
        Check current service availability across regions.
        
        Args:
            services: List of AWS services to check
            regions: List of AWS regions to validate
            
        Returns:
            Service availability information by region
        """
        try:
            logger.info(f"Checking availability for {len(services)} services in {len(regions)} regions")
            
            availability_results = {
                "timestamp": datetime.utcnow().isoformat(),
                "services_checked": services,
                "regions_checked": regions,
                "availability_matrix": {},
                "unavailable_combinations": [],
                "regional_recommendations": {}
            }
            
            # Check each service in each region
            for region in regions:
                availability_results["availability_matrix"][region] = {}
                
                for service in services:
                    availability = await self._check_service_in_region(service, region)
                    availability_results["availability_matrix"][region][service] = availability
                    
                    if not availability["available"]:
                        availability_results["unavailable_combinations"].append({
                            "service": service,
                            "region": region,
                            "reason": availability.get("reason", "Service not available")
                        })
            
            # Generate regional recommendations
            availability_results["regional_recommendations"] = self._generate_regional_recommendations(
                services, regions, availability_results["availability_matrix"]
            )
            
            logger.info(f"Availability check completed: {len(availability_results['unavailable_combinations'])} unavailable combinations")
            return availability_results
            
        except Exception as e:
            logger.error(f"Error checking service availability: {e}")
            return handle_graceful_degradation(e, "service_availability", {
                "services_checked": services,
                "regions_checked": regions,
                "error": str(e),
                "availability_matrix": {}
            })
    
    async def get_service_limits(self, services: List[str], region: str) -> Dict[str, Any]:
        """
        Get current service limits and quotas.
        
        Args:
            services: List of AWS services
            region: AWS region to check
            
        Returns:
            Service limits and quotas information
        """
        try:
            logger.info(f"Retrieving service limits for {len(services)} services in {region}")
            
            limits_results = {
                "timestamp": datetime.utcnow().isoformat(),
                "region": region,
                "services": services,
                "service_limits": {},
                "quota_warnings": [],
                "increase_procedures": {}
            }
            
            # Get limits for each service
            for service in services:
                service_limits = await self._get_service_limits_for_service(service, region)
                limits_results["service_limits"][service] = service_limits
                
                # Check for potential quota issues
                warnings = self._check_quota_warnings(service, service_limits)
                limits_results["quota_warnings"].extend(warnings)
            
            # Add quota increase procedures
            limits_results["increase_procedures"] = self._get_quota_increase_procedures()
            
            logger.info(f"Retrieved limits for {len(services)} services with {len(limits_results['quota_warnings'])} warnings")
            return limits_results
            
        except Exception as e:
            logger.error(f"Error retrieving service limits: {e}")
            return handle_graceful_degradation(e, "service_limits", {
                "region": region,
                "services": services,
                "error": str(e),
                "service_limits": {}
            })
    
    async def get_regional_capabilities(self, services: List[str], regions: List[str]) -> Dict[str, Any]:
        """
        Get service-specific capabilities by region.
        
        Args:
            services: List of AWS services
            regions: List of AWS regions
            
        Returns:
            Regional capabilities information
        """
        try:
            logger.info(f"Retrieving regional capabilities for {len(services)} services in {len(regions)} regions")
            
            capabilities_results = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": services,
                "regions": regions,
                "regional_capabilities": {},
                "feature_availability": {},
                "recommendations": []
            }
            
            # Get capabilities for each region
            for region in regions:
                capabilities_results["regional_capabilities"][region] = {}
                
                for service in services:
                    capabilities = await self._get_service_capabilities_in_region(service, region)
                    capabilities_results["regional_capabilities"][region][service] = capabilities
            
            # Analyze feature availability across regions
            capabilities_results["feature_availability"] = self._analyze_feature_availability(
                services, regions, capabilities_results["regional_capabilities"]
            )
            
            # Generate recommendations
            capabilities_results["recommendations"] = self._generate_capability_recommendations(
                services, regions, capabilities_results["regional_capabilities"]
            )
            
            logger.info(f"Retrieved regional capabilities with {len(capabilities_results['recommendations'])} recommendations")
            return capabilities_results
            
        except Exception as e:
            logger.error(f"Error retrieving regional capabilities: {e}")
            return handle_graceful_degradation(e, "regional_capabilities", {
                "services": services,
                "regions": regions,
                "error": str(e),
                "regional_capabilities": {}
            })
    
    async def validate_architecture_feasibility(
        self, 
        services: List[str], 
        regions: List[str],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate if architecture is feasible given service availability and limits.
        
        Args:
            services: List of AWS services required
            regions: List of target regions
            requirements: Architecture requirements (performance, compliance, etc.)
            
        Returns:
            Feasibility analysis with recommendations
        """
        try:
            logger.info(f"Validating architecture feasibility for {len(services)} services")
            
            # Check service availability
            availability = await self.check_service_availability(services, regions)
            
            # Check service limits
            limits_checks = []
            for region in regions:
                limits = await self.get_service_limits(services, region)
                limits_checks.append(limits)
            
            # Check regional capabilities
            capabilities = await self.get_regional_capabilities(services, regions)
            
            # Analyze feasibility
            feasibility_analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": services,
                "regions": regions,
                "requirements": requirements,
                "feasibility_score": 0.0,
                "feasible": False,
                "blocking_issues": [],
                "warnings": [],
                "recommendations": [],
                "alternative_regions": []
            }
            
            # Calculate feasibility score
            feasibility_score = self._calculate_feasibility_score(
                availability, limits_checks, capabilities, requirements
            )
            
            feasibility_analysis["feasibility_score"] = feasibility_score
            feasibility_analysis["feasible"] = feasibility_score >= 0.7
            
            # Identify blocking issues
            feasibility_analysis["blocking_issues"] = self._identify_blocking_issues(
                availability, limits_checks, capabilities
            )
            
            # Generate recommendations
            feasibility_analysis["recommendations"] = self._generate_feasibility_recommendations(
                availability, limits_checks, capabilities, requirements
            )
            
            logger.info(f"Architecture feasibility: {feasibility_score:.2f} ({'feasible' if feasibility_analysis['feasible'] else 'not feasible'})")
            return feasibility_analysis
            
        except Exception as e:
            logger.error(f"Error validating architecture feasibility: {e}")
            return handle_graceful_degradation(e, "architecture_feasibility", {
                "services": services,
                "regions": regions,
                "error": str(e),
                "feasible": False
            })
    
    def _load_service_availability_data(self) -> Dict[str, Any]:
        """Load service availability data (would be from AWS APIs in production)."""
        
        # This is a simplified version - in production this would be loaded from AWS APIs
        return {
            "ec2": {
                "available_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                "instance_types": ["t3.micro", "t3.small", "m5.large", "c5.large"],
                "features": ["spot_instances", "reserved_instances", "auto_scaling"]
            },
            "s3": {
                "available_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                "storage_classes": ["standard", "ia", "glacier", "deep_archive"],
                "features": ["versioning", "encryption", "cross_region_replication"]
            },
            "lambda": {
                "available_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                "runtimes": ["python3.9", "python3.10", "nodejs18.x", "java11"],
                "features": ["provisioned_concurrency", "layers", "destinations"]
            },
            "rds": {
                "available_regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                "engines": ["mysql", "postgresql", "aurora-mysql", "aurora-postgresql"],
                "features": ["multi_az", "read_replicas", "automated_backups"]
            }
        }
    
    async def _check_service_in_region(self, service: str, region: str) -> Dict[str, Any]:
        """Check if service is available in specific region."""
        
        service_data = self.service_availability.get(service.lower(), {})
        available_regions = service_data.get("available_regions", [])
        
        available = region in available_regions
        
        return {
            "service": service,
            "region": region,
            "available": available,
            "features": service_data.get("features", []) if available else [],
            "reason": "" if available else f"{service} not available in {region}"
        }
    
    async def _get_service_limits_for_service(self, service: str, region: str) -> Dict[str, Any]:
        """Get service limits for specific service in region."""
        
        # Default limits (would be retrieved from AWS APIs in production)
        default_limits = {
            "ec2": {
                "running_instances": {"limit": 20, "current": 0},
                "elastic_ips": {"limit": 5, "current": 0},
                "security_groups": {"limit": 2500, "current": 0}
            },
            "s3": {
                "buckets": {"limit": 100, "current": 0},
                "objects_per_bucket": {"limit": "unlimited", "current": 0}
            },
            "lambda": {
                "concurrent_executions": {"limit": 1000, "current": 0},
                "function_count": {"limit": 1000, "current": 0}
            },
            "rds": {
                "db_instances": {"limit": 40, "current": 0},
                "db_snapshots": {"limit": 100, "current": 0}
            }
        }
        
        return default_limits.get(service.lower(), {})
    
    async def _get_service_capabilities_in_region(self, service: str, region: str) -> Dict[str, Any]:
        """Get service capabilities in specific region."""
        
        service_data = self.service_availability.get(service.lower(), {})
        
        return {
            "service": service,
            "region": region,
            "available_features": service_data.get("features", []),
            "instance_types": service_data.get("instance_types", []),
            "storage_classes": service_data.get("storage_classes", []),
            "runtimes": service_data.get("runtimes", []),
            "engines": service_data.get("engines", [])
        }
    
    def _generate_regional_recommendations(
        self, 
        services: List[str], 
        regions: List[str], 
        availability_matrix: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> List[Dict[str, str]]:
        """Generate regional recommendations based on availability."""
        
        recommendations = []
        
        # Find regions with best service coverage
        region_scores = {}
        for region in regions:
            available_services = sum(
                1 for service in services 
                if availability_matrix.get(region, {}).get(service, {}).get("available", False)
            )
            region_scores[region] = available_services / len(services)
        
        # Recommend best regions
        best_regions = sorted(region_scores.items(), key=lambda x: x[1], reverse=True)
        
        for region, score in best_regions[:3]:  # Top 3 regions
            if score > 0.8:  # 80% service availability
                recommendations.append({
                    "type": "regional_recommendation",
                    "region": region,
                    "message": f"Region {region} has {score:.1%} service availability - recommended for deployment"
                })
        
        return recommendations
    
    def _check_quota_warnings(self, service: str, service_limits: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check for potential quota warnings."""
        
        warnings = []
        
        for limit_name, limit_data in service_limits.items():
            if isinstance(limit_data, dict) and "limit" in limit_data and "current" in limit_data:
                limit_value = limit_data["limit"]
                current_value = limit_data["current"]
                
                if isinstance(limit_value, int) and isinstance(current_value, int):
                    utilization = current_value / limit_value if limit_value > 0 else 0
                    
                    if utilization > 0.8:  # 80% utilization warning
                        warnings.append({
                            "service": service,
                            "limit": limit_name,
                            "message": f"{service} {limit_name} is at {utilization:.1%} capacity"
                        })
        
        return warnings
    
    def _get_quota_increase_procedures(self) -> Dict[str, str]:
        """Get quota increase procedures."""
        
        return {
            "service_quotas": "Use AWS Service Quotas console to request increases",
            "support_case": "Create AWS Support case for quota increases",
            "documentation": "https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html"
        }
    
    def _analyze_feature_availability(
        self, 
        services: List[str], 
        regions: List[str], 
        regional_capabilities: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze feature availability across regions."""
        
        feature_analysis = {}
        
        for service in services:
            service_features = {}
            
            for region in regions:
                capabilities = regional_capabilities.get(region, {}).get(service, {})
                features = capabilities.get("available_features", [])
                
                for feature in features:
                    if feature not in service_features:
                        service_features[feature] = []
                    service_features[feature].append(region)
            
            feature_analysis[service] = service_features
        
        return feature_analysis
    
    def _generate_capability_recommendations(
        self, 
        services: List[str], 
        regions: List[str], 
        regional_capabilities: Dict[str, Dict[str, Dict[str, Any]]]
    ) -> List[Dict[str, str]]:
        """Generate capability-based recommendations."""
        
        recommendations = []
        
        for service in services:
            # Find regions with most features for this service
            region_feature_counts = {}
            
            for region in regions:
                capabilities = regional_capabilities.get(region, {}).get(service, {})
                feature_count = len(capabilities.get("available_features", []))
                region_feature_counts[region] = feature_count
            
            if region_feature_counts:
                best_region = max(region_feature_counts, key=region_feature_counts.get)
                max_features = region_feature_counts[best_region]
                
                if max_features > 0:
                    recommendations.append({
                        "type": "capability_recommendation",
                        "service": service,
                        "region": best_region,
                        "message": f"Region {best_region} offers the most features ({max_features}) for {service}"
                    })
        
        return recommendations
    
    def _calculate_feasibility_score(
        self, 
        availability: Dict[str, Any], 
        limits_checks: List[Dict[str, Any]], 
        capabilities: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> float:
        """Calculate overall feasibility score."""
        
        score = 0.0
        factors = 0
        
        # Service availability factor (40% weight)
        unavailable_count = len(availability.get("unavailable_combinations", []))
        total_combinations = len(availability.get("services_checked", [])) * len(availability.get("regions_checked", []))
        
        if total_combinations > 0:
            availability_score = 1.0 - (unavailable_count / total_combinations)
            score += availability_score * 0.4
            factors += 0.4
        
        # Quota warnings factor (30% weight)
        total_warnings = sum(len(limits.get("quota_warnings", [])) for limits in limits_checks)
        if total_warnings == 0:
            score += 0.3
        else:
            # Reduce score based on number of warnings
            warning_penalty = min(total_warnings * 0.1, 0.3)
            score += max(0, 0.3 - warning_penalty)
        factors += 0.3
        
        # Feature availability factor (30% weight)
        # Simplified - assume good feature availability
        score += 0.25
        factors += 0.3
        
        return score / factors if factors > 0 else 0.0
    
    def _identify_blocking_issues(
        self, 
        availability: Dict[str, Any], 
        limits_checks: List[Dict[str, Any]], 
        capabilities: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Identify blocking issues for architecture deployment."""
        
        blocking_issues = []
        
        # Service availability issues
        for unavailable in availability.get("unavailable_combinations", []):
            blocking_issues.append({
                "type": "service_unavailable",
                "severity": "high",
                "message": f"{unavailable['service']} not available in {unavailable['region']}"
            })
        
        # Critical quota issues
        for limits in limits_checks:
            for warning in limits.get("quota_warnings", []):
                if "90%" in warning.get("message", "") or "95%" in warning.get("message", ""):
                    blocking_issues.append({
                        "type": "quota_limit",
                        "severity": "high", 
                        "message": warning["message"]
                    })
        
        return blocking_issues
    
    def _generate_feasibility_recommendations(
        self, 
        availability: Dict[str, Any], 
        limits_checks: List[Dict[str, Any]], 
        capabilities: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate feasibility recommendations."""
        
        recommendations = []
        
        # Regional recommendations
        recommendations.extend(availability.get("regional_recommendations", []))
        
        # Quota recommendations
        for limits in limits_checks:
            if limits.get("quota_warnings"):
                recommendations.append({
                    "type": "quota_management",
                    "message": f"Request quota increases for {limits['region']} before deployment"
                })
        
        # Capability recommendations
        recommendations.extend(capabilities.get("recommendations", []))
        
        return recommendations
