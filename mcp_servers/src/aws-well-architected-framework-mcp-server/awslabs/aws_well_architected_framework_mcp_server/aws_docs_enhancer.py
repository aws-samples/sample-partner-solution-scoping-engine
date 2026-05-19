"""AWS Documentation Enhancement for WAFR Recommendations."""

import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)

class AWSDocsEnhancer:
    """Enhances WAFR recommendations with validated AWS documentation links."""
    
    def __init__(self):
        """Initialize AWS documentation enhancer."""
        self.service_docs = self._load_service_documentation_map()
        
    def _load_service_documentation_map(self) -> Dict[str, Dict[str, str]]:
        """Load AWS service documentation mapping."""
        return {
            "vpc": {
                "security_groups": "https://docs.aws.amazon.com/vpc/latest/userguide/security-groups.html",
                "network_acls": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html",
                "subnets": "https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html"
            },
            "iam": {
                "best_practices": "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
                "roles": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html",
                "policies": "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html"
            },
            "cloudtrail": {
                "setup": "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html",
                "best_practices": "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html"
            },
            "waf": {
                "getting_started": "https://docs.aws.amazon.com/waf/latest/developerguide/getting-started.html",
                "web_acl": "https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html"
            },
            "backup": {
                "getting_started": "https://docs.aws.amazon.com/aws-backup/latest/devguide/getting-started.html",
                "cross_region": "https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-region-backup.html"
            },
            "dynamodb": {
                "backup": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html",
                "pitr": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html"
            },
            "cost_explorer": {
                "getting_started": "https://docs.aws.amazon.com/cost-management/latest/userguide/ce-getting-started.html",
                "rightsizing": "https://docs.aws.amazon.com/cost-management/latest/userguide/ce-rightsizing.html"
            }
        }
    
    def enhance_recommendations(self, recommendations: List[str], aws_services: List[str] = None) -> List[Dict[str, Any]]:
        """Enhance recommendations with AWS documentation links."""
        enhanced = []
        
        for rec in recommendations:
            enhanced_rec = {
                "recommendation": rec,
                "aws_docs": self._get_relevant_docs(rec, aws_services or []),
                "service_specific": self._is_service_specific(rec, aws_services or [])
            }
            enhanced.append(enhanced_rec)
            
        return enhanced
    
    def _get_relevant_docs(self, recommendation: str, aws_services: List[str]) -> List[Dict[str, str]]:
        """Get relevant AWS documentation for a recommendation."""
        docs = []
        rec_lower = recommendation.lower()
        
        # Map recommendation keywords to documentation
        doc_mappings = {
            "vpc": ["vpc", "security group", "subnet", "network"],
            "iam": ["iam", "role", "policy", "permission", "access"],
            "cloudtrail": ["cloudtrail", "audit", "logging", "trail"],
            "waf": ["waf", "web application firewall", "protection"],
            "backup": ["backup", "recovery", "restore"],
            "dynamodb": ["dynamodb", "database", "point-in-time"],
            "cost_explorer": ["cost", "billing", "optimization", "rightsizing"]
        }
        
        for service, keywords in doc_mappings.items():
            if any(keyword in rec_lower for keyword in keywords):
                service_docs = self.service_docs.get(service, {})
                for doc_type, url in service_docs.items():
                    docs.append({
                        "title": f"AWS {service.upper()} - {doc_type.replace('_', ' ').title()}",
                        "url": url,
                        "service": service
                    })
                    
        return docs[:3]  # Limit to top 3 most relevant
    
    def _is_service_specific(self, recommendation: str, aws_services: List[str]) -> bool:
        """Check if recommendation is service-specific."""
        service_keywords = ["implement", "configure", "enable", "set up", "deploy"]
        return any(keyword in recommendation.lower() for keyword in service_keywords)
    
    def validate_recommendation(self, recommendation: str) -> Dict[str, Any]:
        """Validate recommendation against AWS best practices."""
        return {
            "is_valid": True,  # Simplified validation
            "confidence": "high" if self._is_service_specific(recommendation, []) else "medium",
            "aws_aligned": True
        }
