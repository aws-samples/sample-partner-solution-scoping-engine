"""
Comprehensive document access error handling system for WAFR MCP Server.

This module provides detailed error handling, diagnostics, and recovery guidance
for document access failures, particularly S3 access issues.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.error_handler import DocumentProcessingError, WAFRAssessmentError
from ..core.production_monitoring import (
    production_logger, 
    document_access_monitor, 
    metrics_collector,
    correlation_context,
    EventType,
    ErrorEvent
)
from ..core.user_guidance_system import user_guidance_system, UserRole, GuidanceLevel
from .analysis_engine import EnhancedS3DocumentLoader, AWSCredentialManager


@dataclass
class DocumentAccessDiagnostics:
    """Comprehensive diagnostics for document access issues"""
    document_url: str
    access_attempted: datetime
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    s3_diagnostics: Optional[Dict[str, Any]]
    credential_info: Dict[str, Any]
    recommendations: List[str]
    correlation_id: str


class DocumentAccessErrorHandler:
    """
    Comprehensive error handler for document access failures.
    
    Provides detailed diagnostics, user-friendly error messages, and recovery
    action recommendations for different types of document access errors.
    """
    
    def __init__(self, region_name: str = None):
        from ..consts import get_aws_region
        self.region_name = region_name or get_aws_region()
        self.logger = logging.getLogger(__name__)
        self.s3_loader = EnhancedS3DocumentLoader(region_name)
        self.credential_manager = AWSCredentialManager()
        
        # Error type mappings for user-friendly messages
        self.error_type_messages = {
            'credential_error': {
                'user_message': (
                    "Unable to access your uploaded document due to AWS credential issues. "
                    "The system administrator needs to configure proper AWS access for document analysis."
                ),
                'admin_guidance': [
                    'Configure valid AWS credentials for the WAFR MCP server',
                    'Ensure IAM permissions include s3:GetObject and s3:ListBucket',
                    'Verify AWS region configuration matches S3 bucket region',
                    'Check credential provider chain (environment variables, IAM roles, credential files)'
                ]
            },
            'bucket_access_error': {
                'user_message': (
                    "Unable to access the document storage bucket. "
                    "This appears to be a configuration issue that requires administrator attention."
                ),
                'admin_guidance': [
                    'Verify S3 bucket name configuration in backend settings',
                    'Check bucket-level IAM policies and permissions',
                    'Ensure bucket exists in the correct AWS region',
                    'Verify bucket policy allows access from WAFR MCP server credentials'
                ]
            },
            'object_not_found': {
                'user_message': (
                    "Your uploaded document could not be found in storage. "
                    "Please try uploading the document again."
                ),
                'admin_guidance': [
                    'Verify document upload process completed successfully',
                    'Check S3 object key format and naming conventions',
                    'Ensure backend properly stores documents after upload',
                    'Verify document reference resolution in chat service'
                ]
            },
            'object_access_denied': {
                'user_message': (
                    "Unable to access your uploaded document due to permission restrictions. "
                    "The system administrator needs to review document access permissions."
                ),
                'admin_guidance': [
                    'Check object-level IAM permissions for s3:GetObject',
                    'Verify bucket policy allows access to specific objects',
                    'Ensure no conflicting bucket ACLs or object ACLs',
                    'Check for resource-based policies blocking access'
                ]
            },
            'network_error': {
                'user_message': (
                    "There was a network issue accessing your uploaded document. "
                    "Please try again in a moment."
                ),
                'admin_guidance': [
                    'Check network connectivity to AWS S3 endpoints',
                    'Verify VPC endpoints or NAT gateway configuration if applicable',
                    'Check for firewall or security group restrictions',
                    'Monitor AWS service health status'
                ]
            },
            'document_format_error': {
                'user_message': (
                    "There was an issue processing your document format. "
                    "Please ensure the document is a valid PDF, PNG, JPEG, or text file."
                ),
                'admin_guidance': [
                    'Verify document format validation in upload process',
                    'Check file size limits and processing capabilities',
                    'Ensure document processing libraries are properly configured',
                    'Review document validation error logs'
                ]
            },
            'timeout_error': {
                'user_message': (
                    "Document access timed out. This may be due to a large file size or network issues. "
                    "Please try again or contact support if the issue persists."
                ),
                'admin_guidance': [
                    'Check S3 client timeout configuration',
                    'Verify network latency to S3 endpoints',
                    'Consider increasing timeout values for large documents',
                    'Monitor S3 request performance metrics'
                ]
            },
            'unknown_error': {
                'user_message': (
                    "There was an unexpected issue accessing your uploaded document. "
                    "Please try uploading the document again or contact support if the issue persists."
                ),
                'admin_guidance': [
                    'Review detailed error logs for root cause analysis',
                    'Check system resource availability (memory, disk space)',
                    'Verify all required dependencies are properly installed',
                    'Consider enabling debug logging for more detailed information'
                ]
            }
        }
    
    def handle_s3_access_error(self, error: Exception, s3_url: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle S3 access errors with detailed diagnostics and recovery guidance.
        
        Args:
            error: The exception that occurred
            s3_url: The S3 URL that failed to access
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Comprehensive error response with diagnostics and recovery actions
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Use production monitoring for structured logging
        with correlation_context(production_logger, correlation_id, "s3_access_error", document_url=s3_url):
            production_logger.error(f"S3 document access failed for {s3_url}: {error}")
            
            # Record error metrics
            metrics_collector.record_counter(
                "s3_access_errors",
                1,
                correlation_id,
                {"error_type": type(error).__name__, "url": s3_url}
            )
            
            try:
                # Generate comprehensive diagnostic report
                diagnostic_report = self.s3_loader.generate_diagnostic_report(s3_url)
                
                # Determine error type based on diagnostics
                error_type = self._classify_error_type(error, diagnostic_report)
                
                # Get credential information
                credential_info = self.s3_loader.get_credential_source_info()
                
                # Create diagnostics object
                diagnostics = DocumentAccessDiagnostics(
                    document_url=s3_url,
                    access_attempted=datetime.utcnow(),
                    success=False,
                    error_type=error_type,
                    error_message=str(error),
                    s3_diagnostics=diagnostic_report,
                    credential_info=credential_info,
                    recommendations=self._get_recovery_actions(error_type, diagnostic_report),
                    correlation_id=correlation_id
                )
                
                # Log error event for monitoring
                error_event = ErrorEvent(
                    error_type=error_type,
                    error_message=str(error),
                    error_code=getattr(error, 'response', {}).get('Error', {}).get('Code') if hasattr(error, 'response') else None,
                    correlation_id=correlation_id,
                    operation="s3_document_access",
                    timestamp=datetime.utcnow(),
                    stack_trace=None,  # Don't include stack trace in production logs
                    recovery_action=f"See recovery actions for {error_type}",
                    user_impact="Document analysis will continue with fallback"
                )
                production_logger.log_error_event(error_event)
                
                # Get comprehensive user guidance
                user_guidance = user_guidance_system.get_user_guidance(
                    error_type=error_type,
                    user_role=UserRole.END_USER,
                    guidance_level=GuidanceLevel.BASIC,
                    include_technical_details=False
                )
                
                admin_guidance = user_guidance_system.get_user_guidance(
                    error_type=error_type,
                    user_role=UserRole.ADMINISTRATOR,
                    guidance_level=GuidanceLevel.DETAILED,
                    include_technical_details=True
                )
                
                # Create comprehensive error response
                error_response = {
                    'success': False,
                    'error_type': 'document_access_failure',
                    'error_classification': error_type,
                    'correlation_id': correlation_id,
                    'user_message': user_guidance['user_message'],
                    'technical_details': {
                        'original_error': str(error),
                        'error_class': type(error).__name__,
                        'document_url': s3_url,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    'diagnostic_report': diagnostic_report,
                    'credential_info': credential_info,
                    'user_guidance': user_guidance,
                    'admin_guidance': admin_guidance,
                    'recovery_actions': {
                        'user_actions': self._get_user_recovery_actions(error_type),
                        'admin_actions': self._get_admin_recovery_actions(error_type)
                    },
                    'fallback_available': True,
                    'assessment_impact': self._get_assessment_impact_message(error_type),
                    'monitoring_info': {
                        'correlation_id': correlation_id,
                        'log_context': f"Document access failure for {s3_url}",
                        'troubleshooting_guide': self._get_troubleshooting_guide_url(error_type)
                    }
                }
                
                # Log structured diagnostic information
                self._log_diagnostic_info(diagnostics)
                
                # Record diagnostic completion metrics
                metrics_collector.record_counter(
                    "diagnostic_reports_generated",
                    1,
                    correlation_id,
                    {"error_type": error_type}
                )
                
                return error_response
                
            except Exception as diagnostic_error:
                production_logger.error(f"Error generating diagnostics: {diagnostic_error}")
                
                # Record diagnostic failure metrics
                metrics_collector.record_counter(
                    "diagnostic_failures",
                    1,
                    correlation_id,
                    {"original_error": type(error).__name__}
                )
                
                # Fallback error response when diagnostics fail
                return self._create_fallback_error_response(error, s3_url, correlation_id)
    
    def _classify_error_type(self, error: Exception, diagnostic_report: Dict[str, Any]) -> str:
        """Classify the error type based on the error and diagnostic information."""
        
        error_str = str(error).lower()
        error_class = type(error).__name__
        
        # Check credential issues first
        creds = diagnostic_report.get('credentials_check', {})
        if not creds.get('valid', False):
            return 'credential_error'
        
        # Check bucket access issues
        bucket_check = diagnostic_report.get('bucket_access_check', {})
        if bucket_check and not bucket_check.get('accessible', False):
            error_code = bucket_check.get('error_code', '')
            if error_code == 'NoSuchBucket':
                return 'bucket_access_error'
            elif error_code == 'AccessDenied':
                return 'bucket_access_error'
        
        # Check object access issues
        object_check = diagnostic_report.get('object_access_check', {})
        if object_check:
            if not object_check.get('exists', True):
                return 'object_not_found'
            elif not object_check.get('accessible', False):
                error_code = object_check.get('error_code', '')
                if error_code == 'AccessDenied':
                    return 'object_access_denied'
        
        # Check for specific error patterns
        if 'timeout' in error_str or 'timed out' in error_str:
            return 'timeout_error'
        elif 'network' in error_str or 'connection' in error_str:
            return 'network_error'
        elif 'format' in error_str or 'invalid' in error_str:
            return 'document_format_error'
        elif 'not found' in error_str or '404' in error_str:
            return 'object_not_found'
        elif 'access denied' in error_str or 'forbidden' in error_str or '403' in error_str:
            return 'object_access_denied'
        
        return 'unknown_error'
    
    def _get_user_friendly_message(self, error_type: str) -> str:
        """Get user-friendly error message for the error type."""
        return self.error_type_messages.get(error_type, self.error_type_messages['unknown_error'])['user_message']
    
    def _get_user_recovery_actions(self, error_type: str) -> List[str]:
        """Get recovery actions that users can take."""
        
        user_actions = {
            'credential_error': [
                'Contact your system administrator about AWS credential configuration',
                'Verify you have permission to access the document storage system'
            ],
            'bucket_access_error': [
                'Contact your system administrator about document storage configuration',
                'Verify the system is properly configured for document storage'
            ],
            'object_not_found': [
                'Try uploading the document again',
                'Verify the document upload completed successfully',
                'Check that you selected the correct file for upload'
            ],
            'object_access_denied': [
                'Contact your system administrator about document access permissions',
                'Verify you have permission to access uploaded documents'
            ],
            'network_error': [
                'Check your internet connection',
                'Try again in a few moments',
                'Contact support if the issue persists'
            ],
            'document_format_error': [
                'Verify your document is in a supported format (PDF, PNG, JPEG, TXT)',
                'Check that the document is not corrupted',
                'Try converting the document to PDF format',
                'Ensure the document size is within limits (typically under 50MB)'
            ],
            'timeout_error': [
                'Try uploading a smaller version of the document',
                'Check your internet connection speed',
                'Try again during off-peak hours',
                'Contact support for assistance with large documents'
            ],
            'unknown_error': [
                'Try uploading the document again',
                'Verify the document format is supported',
                'Check your internet connection',
                'Contact support if the issue persists'
            ]
        }
        
        return user_actions.get(error_type, user_actions['unknown_error'])
    
    def _get_admin_recovery_actions(self, error_type: str) -> List[str]:
        """Get recovery actions for system administrators."""
        return self.error_type_messages.get(error_type, self.error_type_messages['unknown_error'])['admin_guidance']
    
    def _get_recovery_actions(self, error_type: str, diagnostic_report: Dict[str, Any]) -> List[str]:
        """Get comprehensive recovery actions based on error type and diagnostics."""
        
        actions = []
        
        # Add specific actions based on diagnostic results
        recommendations = diagnostic_report.get('recommendations', [])
        actions.extend(recommendations)
        
        # Add general actions based on error type
        admin_actions = self._get_admin_recovery_actions(error_type)
        actions.extend(admin_actions)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in actions:
            if action not in seen:
                seen.add(action)
                unique_actions.append(action)
        
        return unique_actions
    
    def _get_assessment_impact_message(self, error_type: str) -> str:
        """Get message explaining impact on WAFR assessment."""
        
        impact_messages = {
            'credential_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Results may be less specific to your architecture."
            ),
            'bucket_access_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Results may be less specific to your architecture."
            ),
            'object_not_found': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Please re-upload the document and run the assessment again for more accurate results."
            ),
            'object_access_denied': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Results may be less specific to your architecture."
            ),
            'network_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "You may retry the assessment once network connectivity is restored."
            ),
            'document_format_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Please upload a supported document format for more accurate results."
            ),
            'timeout_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Consider uploading a smaller document or trying again later."
            ),
            'unknown_error': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Results may be less specific to your architecture."
            )
        }
        
        return impact_messages.get(error_type, impact_messages['unknown_error'])
    
    def _get_troubleshooting_guide_url(self, error_type: str) -> str:
        """Get URL to troubleshooting guide for the error type."""
        
        # In a real implementation, these would be actual documentation URLs
        base_url = "https://docs.sera.internal/troubleshooting/wafr-document-access"
        
        guide_urls = {
            'credential_error': f"{base_url}#aws-credentials",
            'bucket_access_error': f"{base_url}#s3-bucket-access",
            'object_not_found': f"{base_url}#document-not-found",
            'object_access_denied': f"{base_url}#document-permissions",
            'network_error': f"{base_url}#network-issues",
            'document_format_error': f"{base_url}#document-formats",
            'timeout_error': f"{base_url}#timeout-issues",
            'unknown_error': f"{base_url}#general-troubleshooting"
        }
        
        return guide_urls.get(error_type, guide_urls['unknown_error'])
    
    def _log_diagnostic_info(self, diagnostics: DocumentAccessDiagnostics) -> None:
        """Log structured diagnostic information for monitoring and troubleshooting."""
        
        # Use production monitoring for structured logging
        production_logger.log_event(
            EventType.DOCUMENT_ACCESS_FAILURE,
            document_url=diagnostics.document_url,
            error_type=diagnostics.error_type,
            error_message=diagnostics.error_message,
            credential_source=diagnostics.credential_info.get('source', 'unknown'),
            recommendations_count=len(diagnostics.recommendations),
            s3_diagnostics_summary={
                'credentials_valid': diagnostics.s3_diagnostics.get('credentials_check', {}).get('valid', False),
                'bucket_accessible': diagnostics.s3_diagnostics.get('bucket_access_check', {}).get('accessible', False),
                'object_exists': diagnostics.s3_diagnostics.get('object_access_check', {}).get('exists', False),
                'object_accessible': diagnostics.s3_diagnostics.get('object_access_check', {}).get('accessible', False)
            }
        )
        
        # Record detailed metrics for monitoring
        metrics_collector.record_counter(
            "diagnostic_recommendations_generated",
            len(diagnostics.recommendations),
            diagnostics.correlation_id,
            {"error_type": diagnostics.error_type}
        )
        
        # Record credential source metrics
        metrics_collector.record_counter(
            "credential_source_usage",
            1,
            diagnostics.correlation_id,
            {"source": diagnostics.credential_info.get('source', 'unknown')}
        )
    
    def _create_fallback_error_response(self, error: Exception, s3_url: str, correlation_id: str) -> Dict[str, Any]:
        """Create fallback error response when diagnostics fail."""
        
        return {
            'success': False,
            'error_type': 'document_access_failure',
            'error_classification': 'unknown_error',
            'correlation_id': correlation_id,
            'user_message': (
                "There was an issue accessing your uploaded document. "
                "Please try uploading the document again or contact support if the issue persists."
            ),
            'technical_details': {
                'original_error': str(error),
                'error_class': type(error).__name__,
                'document_url': s3_url,
                'timestamp': datetime.utcnow().isoformat(),
                'diagnostic_failure': True
            },
            'recovery_actions': {
                'user_actions': [
                    'Try uploading the document again',
                    'Verify the document format is supported',
                    'Contact support if the issue persists'
                ],
                'admin_actions': [
                    'Check WAFR MCP server logs for detailed error information',
                    'Verify AWS credentials and S3 access configuration',
                    'Review system resource availability and dependencies'
                ]
            },
            'fallback_available': True,
            'assessment_impact': (
                "The WAFR assessment will continue without analyzing your uploaded document. "
                "Results may be less specific to your architecture."
            ),
            'monitoring_info': {
                'correlation_id': correlation_id,
                'log_context': f"Document access failure with diagnostic error for {s3_url}",
                'troubleshooting_guide': self._get_troubleshooting_guide_url('unknown_error')
            }
        }
    
    def create_graceful_degradation_response(self, 
                                           original_error: Exception, 
                                           s3_url: str, 
                                           fallback_message: str,
                                           correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a graceful degradation response that allows assessment to continue.
        
        Args:
            original_error: The original error that occurred
            s3_url: The S3 URL that failed
            fallback_message: Message explaining the fallback behavior
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Response indicating graceful degradation with clear user guidance
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Determine error type for appropriate guidance
        error_type = self._classify_error_type(original_error, {})
        
        # Get user guidance for graceful degradation
        user_guidance = user_guidance_system.get_user_guidance(
            error_type=error_type,
            user_role=UserRole.END_USER,
            guidance_level=GuidanceLevel.BASIC
        )
        
        return {
            'success': True,  # Assessment can continue
            'partial_success': True,
            'document_access_failed': True,
            'correlation_id': correlation_id,
            'fallback_message': fallback_message,
            'user_guidance': user_guidance['user_message'],
            'quick_recovery_options': user_guidance.get('quick_fixes', []),
            'technical_details': {
                'original_error': str(original_error),
                'failed_document_url': s3_url,
                'timestamp': datetime.utcnow().isoformat()
            },
            'next_steps': [
                'The assessment will proceed with general WAFR best practices',
                'Results will include recommendations based on common architectural patterns',
                'Consider re-running the assessment after resolving document access issues'
            ],
            'assessment_limitations': [
                'Service identification may be incomplete without document analysis',
                'Recommendations may be less specific to your actual architecture',
                'Security and compliance findings may miss document-specific configurations'
            ],
            'progressive_help': {
                'available': True,
                'levels': ['basic_help', 'detailed_steps', 'contact_support'],
                'current_level': 'basic_help'
            }
        }
    
    def get_interactive_troubleshooting(self, 
                                      error_type: str, 
                                      user_responses: Dict[str, Any],
                                      correlation_id: str) -> Dict[str, Any]:
        """
        Get interactive troubleshooting guidance based on user responses.
        
        Args:
            error_type: Type of error being troubleshot
            user_responses: User's responses to previous questions
            correlation_id: Correlation ID for tracking
            
        Returns:
            Next troubleshooting step or resolution
        """
        
        # Use production monitoring for tracking
        with correlation_context(production_logger, correlation_id, "interactive_troubleshooting", error_type=error_type):
            production_logger.info(f"Interactive troubleshooting session for {error_type}")
            
            # Get troubleshooting guidance
            troubleshooting_result = user_guidance_system.get_interactive_troubleshooting(
                error_type, user_responses
            )
            
            # Record troubleshooting metrics
            metrics_collector.record_counter(
                "interactive_troubleshooting_steps",
                1,
                correlation_id,
                {"error_type": error_type, "status": troubleshooting_result["status"]}
            )
            
            # Enhance result with correlation tracking
            troubleshooting_result.update({
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": error_type,
                "session_progress": len(user_responses)
            })
            
            return troubleshooting_result
    
    def get_contextual_help(self, 
                           error_type: str, 
                           user_role: UserRole,
                           help_level: GuidanceLevel,
                           correlation_id: str) -> Dict[str, Any]:
        """
        Get contextual help based on user role and desired detail level.
        
        Args:
            error_type: Type of error needing help
            user_role: Role of the user requesting help
            help_level: Level of detail requested
            correlation_id: Correlation ID for tracking
            
        Returns:
            Contextual help response
        """
        
        # Use production monitoring for tracking
        with correlation_context(production_logger, correlation_id, "contextual_help", 
                               error_type=error_type, user_role=user_role.value):
            
            # Get comprehensive guidance
            guidance = user_guidance_system.get_user_guidance(
                error_type=error_type,
                user_role=user_role,
                guidance_level=help_level,
                include_technical_details=(help_level in [GuidanceLevel.TECHNICAL, GuidanceLevel.DEBUG])
            )
            
            # Record help request metrics
            metrics_collector.record_counter(
                "contextual_help_requests",
                1,
                correlation_id,
                {
                    "error_type": error_type,
                    "user_role": user_role.value,
                    "help_level": help_level.value
                }
            )
            
            # Enhance guidance with correlation tracking
            guidance.update({
                "correlation_id": correlation_id,
                "help_session_id": str(uuid.uuid4()),
                "requested_by": user_role.value,
                "detail_level": help_level.value
            })
            
            return guidance


class PerformanceMonitor:
    """Monitor document access performance and generate metrics using production monitoring."""
    
    def __init__(self):
        # Use production monitoring system
        self.document_monitor = document_access_monitor
        self.metrics = metrics_collector
    
    def record_access_attempt(self, correlation_id: str, document_url: str, start_time: datetime) -> None:
        """Record the start of a document access attempt."""
        self.document_monitor.start_document_access(correlation_id, document_url, "document_analysis")
    
    def record_access_result(self, correlation_id: str, success: bool, error_type: Optional[str] = None) -> None:
        """Record the result of a document access attempt."""
        self.document_monitor.complete_document_access(
            correlation_id, 
            success, 
            error_type
        )
        
        # Record additional performance metrics
        if success:
            self.metrics.record_counter(
                "document_access_success_total",
                1,
                correlation_id,
                {"operation": "document_analysis"}
            )
        else:
            self.metrics.record_counter(
                "document_access_failure_total",
                1,
                correlation_id,
                {"operation": "document_analysis", "error_type": error_type or "unknown"}
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of document access performance from production metrics."""
        
        # Get metrics from the production metrics collector
        success_metrics = self.metrics.get_metric_summary("document_access_success", 60)
        failure_metrics = self.metrics.get_metric_summary("document_access_failures", 60)
        duration_metrics = self.metrics.get_metric_summary("document_access_duration", 60)
        
        total_attempts = success_metrics.get("count", 0) + failure_metrics.get("count", 0)
        success_rate = success_metrics.get("count", 0) / total_attempts if total_attempts > 0 else 0
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'time_window_minutes': 60,
            'total_attempts': total_attempts,
            'successful_attempts': success_metrics.get("count", 0),
            'failed_attempts': failure_metrics.get("count", 0),
            'success_rate': round(success_rate, 3),
            'average_duration_ms': duration_metrics.get("avg", 0),
            'p95_duration_ms': duration_metrics.get("p95", 0),
            'p99_duration_ms': duration_metrics.get("p99", 0),
            'active_operations': self.document_monitor.get_operation_status()
        }