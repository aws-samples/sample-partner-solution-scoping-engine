"""
User guidance and error recovery system for WAFR MCP Server.

This module provides clear, actionable guidance for users and administrators
when document access issues occur, with progressive error disclosure and
specific recovery instructions.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class UserRole(Enum):
    """User roles for targeted guidance."""
    END_USER = "end_user"
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"
    SUPPORT = "support"


class GuidanceLevel(Enum):
    """Levels of guidance detail."""
    BASIC = "basic"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    DEBUG = "debug"


@dataclass
class GuidanceStep:
    """Individual guidance step."""
    step_number: int
    title: str
    description: str
    action_required: bool
    estimated_time_minutes: Optional[int]
    prerequisites: List[str]
    verification_steps: List[str]
    troubleshooting_tips: List[str]


@dataclass
class RecoveryPlan:
    """Complete recovery plan for an error scenario."""
    error_type: str
    user_role: UserRole
    guidance_level: GuidanceLevel
    overview: str
    estimated_total_time_minutes: int
    steps: List[GuidanceStep]
    alternative_approaches: List[str]
    escalation_path: Optional[str]
    success_indicators: List[str]


class UserGuidanceSystem:
    """
    Comprehensive user guidance system with progressive error disclosure.
    """
    
    def __init__(self):
        self.guidance_templates = self._initialize_guidance_templates()
        self.common_issues = self._initialize_common_issues()
        self.escalation_paths = self._initialize_escalation_paths()
    
    def get_user_guidance(self, 
                         error_type: str,
                         user_role: UserRole = UserRole.END_USER,
                         guidance_level: GuidanceLevel = GuidanceLevel.BASIC,
                         include_technical_details: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive user guidance for an error scenario.
        
        Args:
            error_type: Type of error that occurred
            user_role: Role of the user requesting guidance
            guidance_level: Level of detail required
            include_technical_details: Whether to include technical details
            
        Returns:
            Comprehensive guidance response
        """
        
        # Get base guidance template
        template = self.guidance_templates.get(error_type, self.guidance_templates['unknown_error'])
        
        # Create recovery plan
        recovery_plan = self._create_recovery_plan(error_type, user_role, guidance_level)
        
        # Build guidance response
        guidance_response = {
            "error_type": error_type,
            "user_role": user_role.value,
            "guidance_level": guidance_level.value,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "what_happened": template["what_happened"],
                "immediate_impact": template["immediate_impact"],
                "can_continue": template["can_continue"],
                "estimated_fix_time": template["estimated_fix_time"]
            },
            "user_message": self._get_role_specific_message(error_type, user_role),
            "recovery_plan": asdict(recovery_plan),
            "quick_fixes": self._get_quick_fixes(error_type, user_role),
            "prevention_tips": self._get_prevention_tips(error_type),
            "support_resources": self._get_support_resources(error_type, user_role)
        }
        
        # Add technical details if requested
        if include_technical_details or guidance_level in [GuidanceLevel.TECHNICAL, GuidanceLevel.DEBUG]:
            guidance_response["technical_details"] = self._get_technical_details(error_type)
        
        # Add progressive disclosure options
        guidance_response["progressive_disclosure"] = self._get_progressive_disclosure_options(error_type, user_role)
        
        return guidance_response
    
    def get_interactive_troubleshooting(self, error_type: str, user_responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide interactive troubleshooting based on user responses.
        
        Args:
            error_type: Type of error being troubleshot
            user_responses: User's responses to previous questions
            
        Returns:
            Next troubleshooting step or resolution
        """
        
        troubleshooting_tree = self._get_troubleshooting_tree(error_type)
        
        # Navigate through troubleshooting tree based on responses
        current_node = troubleshooting_tree
        for question_id, response in user_responses.items():
            if question_id in current_node.get("branches", {}):
                current_node = current_node["branches"][question_id].get(response, current_node)
        
        # Return next step or resolution
        if "resolution" in current_node:
            return {
                "status": "resolved",
                "resolution": current_node["resolution"],
                "next_steps": current_node.get("next_steps", []),
                "verification": current_node.get("verification", [])
            }
        else:
            return {
                "status": "continue",
                "question": current_node.get("question", ""),
                "options": current_node.get("options", []),
                "help_text": current_node.get("help_text", ""),
                "progress": len(user_responses) / len(troubleshooting_tree.get("total_steps", 1))
            }
    
    def _initialize_guidance_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize guidance templates for different error types."""
        
        return {
            "credential_error": {
                "what_happened": "The system cannot access AWS services due to invalid or missing credentials.",
                "immediate_impact": "Document analysis cannot proceed, but the WAFR assessment will continue with general recommendations.",
                "can_continue": True,
                "estimated_fix_time": "5-15 minutes for administrator"
            },
            "bucket_access_error": {
                "what_happened": "The system cannot access the S3 bucket where documents are stored.",
                "immediate_impact": "Document analysis cannot proceed, but the WAFR assessment will continue with general recommendations.",
                "can_continue": True,
                "estimated_fix_time": "10-30 minutes for administrator"
            },
            "object_not_found": {
                "what_happened": "The uploaded document could not be found in storage.",
                "immediate_impact": "This specific document cannot be analyzed, but you can re-upload it.",
                "can_continue": True,
                "estimated_fix_time": "2-5 minutes for user"
            },
            "object_access_denied": {
                "what_happened": "The system has insufficient permissions to access the uploaded document.",
                "immediate_impact": "Document analysis cannot proceed, but the WAFR assessment will continue with general recommendations.",
                "can_continue": True,
                "estimated_fix_time": "10-20 minutes for administrator"
            },
            "network_error": {
                "what_happened": "A network connectivity issue prevented document access.",
                "immediate_impact": "Document analysis is temporarily unavailable, but may work if you try again.",
                "can_continue": True,
                "estimated_fix_time": "1-10 minutes (may resolve automatically)"
            },
            "document_format_error": {
                "what_happened": "The uploaded document format is not supported or the file is corrupted.",
                "immediate_impact": "This specific document cannot be analyzed, but you can upload a different format.",
                "can_continue": True,
                "estimated_fix_time": "5-10 minutes for user"
            },
            "timeout_error": {
                "what_happened": "Document processing took too long and timed out.",
                "immediate_impact": "This document could not be processed, but you can try with a smaller file.",
                "can_continue": True,
                "estimated_fix_time": "5-15 minutes for user"
            },
            "unknown_error": {
                "what_happened": "An unexpected error occurred during document processing.",
                "immediate_impact": "Document analysis cannot proceed, but the WAFR assessment will continue with general recommendations.",
                "can_continue": True,
                "estimated_fix_time": "Variable - contact support if persistent"
            }
        }
    
    def _initialize_common_issues(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common issues and their solutions."""
        
        return {
            "large_file_upload": {
                "symptoms": ["Timeout errors", "Slow upload", "Processing failures"],
                "solutions": [
                    "Compress the document (especially images)",
                    "Convert to PDF format",
                    "Split large documents into smaller sections",
                    "Use a faster internet connection"
                ],
                "prevention": [
                    "Keep documents under 50MB",
                    "Use PDF format for best compatibility",
                    "Optimize images before including in documents"
                ]
            },
            "unsupported_format": {
                "symptoms": ["Format errors", "Processing failures", "Extraction issues"],
                "solutions": [
                    "Convert to PDF format",
                    "Save as PNG or JPEG for images",
                    "Use plain text for simple documents",
                    "Ensure document is not password protected"
                ],
                "prevention": [
                    "Use supported formats: PDF, PNG, JPEG, TXT",
                    "Avoid proprietary formats",
                    "Test with a simple PDF first"
                ]
            },
            "network_connectivity": {
                "symptoms": ["Connection timeouts", "Intermittent failures", "Slow responses"],
                "solutions": [
                    "Check internet connection",
                    "Try again in a few minutes",
                    "Use a different network if available",
                    "Contact IT support if persistent"
                ],
                "prevention": [
                    "Use stable internet connection",
                    "Avoid peak usage times",
                    "Consider using wired connection for large uploads"
                ]
            }
        }
    
    def _initialize_escalation_paths(self) -> Dict[str, Dict[str, Any]]:
        """Initialize escalation paths for different scenarios."""
        
        return {
            "credential_error": {
                "level_1": "System Administrator",
                "level_2": "AWS Infrastructure Team",
                "level_3": "Platform Engineering",
                "contact_info": "Contact your system administrator for AWS credential configuration"
            },
            "bucket_access_error": {
                "level_1": "System Administrator", 
                "level_2": "AWS Infrastructure Team",
                "level_3": "Platform Engineering",
                "contact_info": "Contact your system administrator for S3 bucket configuration"
            },
            "object_not_found": {
                "level_1": "Re-upload document",
                "level_2": "Technical Support",
                "level_3": "Platform Engineering",
                "contact_info": "Try re-uploading first, then contact support if issue persists"
            },
            "network_error": {
                "level_1": "IT Support",
                "level_2": "Network Operations",
                "level_3": "Infrastructure Team",
                "contact_info": "Contact IT support for network connectivity issues"
            },
            "unknown_error": {
                "level_1": "Technical Support",
                "level_2": "Platform Engineering",
                "level_3": "Development Team",
                "contact_info": "Contact technical support with error details and correlation ID"
            }
        }
    
    def _create_recovery_plan(self, error_type: str, user_role: UserRole, guidance_level: GuidanceLevel) -> RecoveryPlan:
        """Create a detailed recovery plan for the error scenario."""
        
        if error_type == "credential_error" and user_role == UserRole.ADMINISTRATOR:
            return RecoveryPlan(
                error_type=error_type,
                user_role=user_role,
                guidance_level=guidance_level,
                overview="Configure valid AWS credentials for the WAFR MCP server to access S3 documents.",
                estimated_total_time_minutes=15,
                steps=[
                    asdict(GuidanceStep(
                        step_number=1,
                        title="Verify AWS Credentials",
                        description="Check if AWS credentials are configured and valid",
                        action_required=True,
                        estimated_time_minutes=5,
                        prerequisites=["Access to server configuration", "AWS account access"],
                        verification_steps=[
                            "Run 'aws sts get-caller-identity' to test credentials",
                            "Verify the returned account ID matches expected account"
                        ],
                        troubleshooting_tips=[
                            "Check environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY",
                            "Verify IAM role if using EC2 instance profiles",
                            "Check ~/.aws/credentials file if using credential files"
                        ]
                    )),
                    asdict(GuidanceStep(
                        step_number=2,
                        title="Configure S3 Permissions",
                        description="Ensure credentials have required S3 permissions",
                        action_required=True,
                        estimated_time_minutes=10,
                        prerequisites=["Valid AWS credentials", "IAM policy management access"],
                        verification_steps=[
                            "Test S3 access with 'aws s3 ls s3://bucket-name'",
                            "Verify GetObject permission on specific documents"
                        ],
                        troubleshooting_tips=[
                            "Required permissions: s3:GetObject, s3:ListBucket",
                            "Check bucket policy for additional restrictions",
                            "Verify region configuration matches bucket region"
                        ]
                    ))
                ],
                alternative_approaches=[
                    "Use IAM roles instead of access keys for better security",
                    "Configure cross-account access if bucket is in different account",
                    "Use temporary credentials with AWS STS"
                ],
                escalation_path="Contact AWS Infrastructure Team if permissions cannot be resolved",
                success_indicators=[
                    "AWS credentials validation succeeds",
                    "S3 bucket access test passes",
                    "Document analysis completes successfully"
                ]
            )
        
        elif error_type == "object_not_found" and user_role == UserRole.END_USER:
            return RecoveryPlan(
                error_type=error_type,
                user_role=user_role,
                guidance_level=guidance_level,
                overview="Re-upload your document to ensure it's properly stored and accessible.",
                estimated_total_time_minutes=5,
                steps=[
                    asdict(GuidanceStep(
                        step_number=1,
                        title="Verify Document Upload",
                        description="Check that your document was successfully uploaded",
                        action_required=True,
                        estimated_time_minutes=2,
                        prerequisites=["Access to upload interface"],
                        verification_steps=[
                            "Look for upload confirmation message",
                            "Check that file size matches your original document"
                        ],
                        troubleshooting_tips=[
                            "Ensure upload completed fully before proceeding",
                            "Check internet connection stability during upload",
                            "Verify file is not corrupted"
                        ]
                    )),
                    asdict(GuidanceStep(
                        step_number=2,
                        title="Re-upload Document",
                        description="Upload your document again to ensure proper storage",
                        action_required=True,
                        estimated_time_minutes=3,
                        prerequisites=["Original document file", "Stable internet connection"],
                        verification_steps=[
                            "Wait for upload completion confirmation",
                            "Proceed with WAFR assessment after successful upload"
                        ],
                        troubleshooting_tips=[
                            "Use supported formats: PDF, PNG, JPEG, TXT",
                            "Keep file size under 50MB for best results",
                            "Ensure document is not password protected"
                        ]
                    ))
                ],
                alternative_approaches=[
                    "Convert document to PDF format if having issues",
                    "Try uploading from a different device or network",
                    "Split large documents into smaller sections"
                ],
                escalation_path="Contact technical support if re-upload continues to fail",
                success_indicators=[
                    "Document upload completes successfully",
                    "WAFR assessment processes the document",
                    "Architecture analysis includes your document content"
                ]
            )
        
        # Default recovery plan for other scenarios
        return RecoveryPlan(
            error_type=error_type,
            user_role=user_role,
            guidance_level=guidance_level,
            overview=f"Resolve {error_type} to restore document analysis functionality.",
            estimated_total_time_minutes=10,
            steps=[
                asdict(GuidanceStep(
                    step_number=1,
                    title="Identify Root Cause",
                    description="Review error details and diagnostic information",
                    action_required=True,
                    estimated_time_minutes=5,
                    prerequisites=["Error details", "Diagnostic report"],
                    verification_steps=["Review all error messages and codes"],
                    troubleshooting_tips=["Check correlation ID for detailed logs"]
                )),
                asdict(GuidanceStep(
                    step_number=2,
                    title="Apply Recommended Solution",
                    description="Follow the specific recommendations for this error type",
                    action_required=True,
                    estimated_time_minutes=5,
                    prerequisites=["Root cause identified"],
                    verification_steps=["Test the solution", "Verify error is resolved"],
                    troubleshooting_tips=["Try alternative approaches if first solution fails"]
                ))
            ],
            alternative_approaches=["Contact support for assistance"],
            escalation_path="Contact technical support with correlation ID",
            success_indicators=["Error no longer occurs", "Document analysis works normally"]
        )
    
    def _get_role_specific_message(self, error_type: str, user_role: UserRole) -> str:
        """Get role-specific message for the error."""
        
        messages = {
            "credential_error": {
                UserRole.END_USER: (
                    "There's a configuration issue preventing access to your uploaded document. "
                    "Your WAFR assessment will continue with general recommendations. "
                    "Please contact your system administrator to resolve the AWS credential configuration."
                ),
                UserRole.ADMINISTRATOR: (
                    "AWS credentials are not properly configured for the WAFR MCP server. "
                    "Please configure valid AWS credentials with S3 access permissions to enable document analysis."
                ),
                UserRole.DEVELOPER: (
                    "The WAFR MCP server lacks valid AWS credentials for S3 access. "
                    "Check credential configuration, environment variables, or IAM role assignments."
                ),
                UserRole.SUPPORT: (
                    "Document access failure due to AWS credential issues. "
                    "Guide the user to contact their administrator for credential configuration."
                )
            },
            "object_not_found": {
                UserRole.END_USER: (
                    "Your uploaded document couldn't be found in storage. "
                    "This sometimes happens if the upload didn't complete properly. "
                    "Please try uploading your document again."
                ),
                UserRole.ADMINISTRATOR: (
                    "Document not found in S3 storage. "
                    "Check upload process, S3 bucket configuration, and object key generation logic."
                ),
                UserRole.DEVELOPER: (
                    "S3 object not found - verify upload process, key generation, and bucket configuration. "
                    "Check backend logs for upload completion status."
                ),
                UserRole.SUPPORT: (
                    "User's document not found in storage. "
                    "Guide them to re-upload, or escalate to technical team if issue persists."
                )
            }
        }
        
        return messages.get(error_type, {}).get(user_role, 
            "An issue occurred with document access. Please follow the recovery steps or contact support.")
    
    def _get_quick_fixes(self, error_type: str, user_role: UserRole) -> List[Dict[str, Any]]:
        """Get quick fixes that users can try immediately."""
        
        quick_fixes = {
            "object_not_found": [
                {
                    "title": "Re-upload Document",
                    "description": "Upload your document again",
                    "time_estimate": "2-3 minutes",
                    "success_rate": "90%",
                    "steps": [
                        "Click the upload button again",
                        "Select your document file",
                        "Wait for upload confirmation",
                        "Proceed with assessment"
                    ]
                }
            ],
            "network_error": [
                {
                    "title": "Retry Operation",
                    "description": "Try the operation again",
                    "time_estimate": "1 minute",
                    "success_rate": "70%",
                    "steps": [
                        "Wait 30 seconds",
                        "Try uploading again",
                        "Check internet connection if it fails again"
                    ]
                }
            ],
            "document_format_error": [
                {
                    "title": "Convert to PDF",
                    "description": "Convert your document to PDF format",
                    "time_estimate": "3-5 minutes",
                    "success_rate": "95%",
                    "steps": [
                        "Open your document in its native application",
                        "Use 'Save As' or 'Export' to PDF",
                        "Upload the PDF version",
                        "Proceed with assessment"
                    ]
                }
            ]
        }
        
        return quick_fixes.get(error_type, [])
    
    def _get_prevention_tips(self, error_type: str) -> List[str]:
        """Get tips to prevent this error in the future."""
        
        prevention_tips = {
            "object_not_found": [
                "Ensure stable internet connection during upload",
                "Wait for upload confirmation before proceeding",
                "Keep document files under 50MB for reliability",
                "Use supported formats: PDF, PNG, JPEG, TXT"
            ],
            "document_format_error": [
                "Use PDF format for best compatibility",
                "Avoid password-protected documents",
                "Ensure documents are not corrupted",
                "Test with a simple PDF first"
            ],
            "network_error": [
                "Use stable internet connection",
                "Avoid uploading during peak hours",
                "Consider using wired connection for large files",
                "Keep documents reasonably sized"
            ],
            "timeout_error": [
                "Keep document size under 50MB",
                "Compress images in documents",
                "Use PDF format for faster processing",
                "Split very large documents into sections"
            ]
        }
        
        return prevention_tips.get(error_type, [
            "Follow system requirements and guidelines",
            "Contact support if issues persist",
            "Keep software and browsers updated"
        ])
    
    def _get_support_resources(self, error_type: str, user_role: UserRole) -> Dict[str, Any]:
        """Get relevant support resources."""
        
        return {
            "documentation": {
                "user_guide": "https://docs.sera.internal/user-guide/document-upload",
                "troubleshooting": f"https://docs.sera.internal/troubleshooting/{error_type}",
                "faq": "https://docs.sera.internal/faq/document-analysis"
            },
            "contact_options": {
                "technical_support": "support@sera.internal",
                "administrator": "Contact your system administrator",
                "emergency": "For critical issues, contact on-call support"
            },
            "self_service": {
                "status_page": "https://status.sera.internal",
                "knowledge_base": "https://kb.sera.internal",
                "community_forum": "https://community.sera.internal"
            },
            "escalation": self.escalation_paths.get(error_type, {})
        }
    
    def _get_technical_details(self, error_type: str) -> Dict[str, Any]:
        """Get technical details for developers and administrators."""
        
        technical_details = {
            "credential_error": {
                "aws_services_affected": ["S3", "STS"],
                "required_permissions": [
                    "s3:GetObject",
                    "s3:ListBucket", 
                    "sts:GetCallerIdentity"
                ],
                "configuration_files": [
                    "~/.aws/credentials",
                    "~/.aws/config",
                    "Environment variables"
                ],
                "diagnostic_commands": [
                    "aws sts get-caller-identity",
                    "aws s3 ls s3://bucket-name",
                    "aws configure list"
                ]
            },
            "bucket_access_error": {
                "aws_services_affected": ["S3"],
                "required_permissions": [
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "common_causes": [
                    "Bucket policy restrictions",
                    "Cross-account access issues",
                    "Region mismatch",
                    "Bucket does not exist"
                ],
                "diagnostic_commands": [
                    "aws s3api head-bucket --bucket bucket-name",
                    "aws s3api get-bucket-policy --bucket bucket-name",
                    "aws s3api get-bucket-location --bucket bucket-name"
                ]
            }
        }
        
        return technical_details.get(error_type, {
            "description": f"Technical details for {error_type}",
            "common_causes": ["Configuration issues", "Permission problems", "Network connectivity"],
            "diagnostic_approach": "Review logs and error messages for specific details"
        })
    
    def _get_progressive_disclosure_options(self, error_type: str, user_role: UserRole) -> Dict[str, Any]:
        """Get progressive disclosure options for different detail levels."""
        
        return {
            "available_levels": [
                {
                    "level": "basic",
                    "title": "Simple Explanation",
                    "description": "What happened and what to do next"
                },
                {
                    "level": "detailed", 
                    "title": "Detailed Steps",
                    "description": "Step-by-step recovery instructions"
                },
                {
                    "level": "technical",
                    "title": "Technical Details",
                    "description": "Technical information for troubleshooting"
                },
                {
                    "level": "debug",
                    "title": "Debug Information",
                    "description": "Detailed diagnostic data for developers"
                }
            ],
            "recommended_level": self._get_recommended_level(user_role),
            "can_escalate": True,
            "escalation_trigger": "If basic steps don't resolve the issue"
        }
    
    def _get_recommended_level(self, user_role: UserRole) -> str:
        """Get recommended guidance level for user role."""
        
        recommendations = {
            UserRole.END_USER: "basic",
            UserRole.ADMINISTRATOR: "detailed", 
            UserRole.DEVELOPER: "technical",
            UserRole.SUPPORT: "detailed"
        }
        
        return recommendations.get(user_role, "basic")
    
    def _get_troubleshooting_tree(self, error_type: str) -> Dict[str, Any]:
        """Get interactive troubleshooting tree for the error type."""
        
        # Example troubleshooting tree for object_not_found
        if error_type == "object_not_found":
            return {
                "total_steps": 3,
                "question": "Did you see a successful upload confirmation?",
                "options": ["yes", "no", "unsure"],
                "help_text": "Look for a green checkmark or 'Upload Complete' message",
                "branches": {
                    "upload_confirmed": {
                        "yes": {
                            "question": "How long ago did you upload the document?",
                            "options": ["less_than_5_minutes", "5_to_30_minutes", "more_than_30_minutes"],
                            "branches": {
                                "timing": {
                                    "less_than_5_minutes": {
                                        "resolution": {
                                            "title": "Processing Delay",
                                            "description": "The document may still be processing. Wait 2-3 minutes and try again.",
                                            "action": "wait_and_retry"
                                        }
                                    },
                                    "more_than_30_minutes": {
                                        "resolution": {
                                            "title": "Storage Issue",
                                            "description": "There may be a storage system issue. Please re-upload your document.",
                                            "action": "re_upload"
                                        }
                                    }
                                }
                            }
                        },
                        "no": {
                            "resolution": {
                                "title": "Upload Failed",
                                "description": "The upload did not complete successfully. Please upload your document again.",
                                "action": "re_upload",
                                "next_steps": [
                                    "Ensure stable internet connection",
                                    "Check document format is supported",
                                    "Verify file size is under 50MB"
                                ]
                            }
                        }
                    }
                }
            }
        
        # Default troubleshooting tree
        return {
            "total_steps": 2,
            "question": "Have you tried the recommended quick fix?",
            "options": ["yes", "no"],
            "branches": {
                "quick_fix_tried": {
                    "no": {
                        "resolution": {
                            "title": "Try Quick Fix",
                            "description": "Please try the recommended quick fix first.",
                            "action": "try_quick_fix"
                        }
                    },
                    "yes": {
                        "resolution": {
                            "title": "Contact Support",
                            "description": "Since the quick fix didn't work, please contact technical support.",
                            "action": "contact_support"
                        }
                    }
                }
            }
        }


# Global instance for user guidance
user_guidance_system = UserGuidanceSystem()