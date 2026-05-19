"""AWS Well-Architected Tool API Client

This module provides integration with AWS Well-Architected Tool APIs for
comprehensive WAFR assessments using official AWS frameworks and scoring.
Enhanced with improved diagnostics and graceful fallback mechanisms.
"""

import asyncio
import time
import os
import sys
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from .core.logger import WAFRLogger
from .core.error_handler import AWSIntegrationError, handle_graceful_degradation
from .models.assessment import PillarName, RiskLevel
from .improved_aws_client import ImprovedAWSClient, APITestResult, QuestionRetrievalResult

logger = WAFRLogger(__name__)


def get_aws_config() -> Dict[str, str]:
    """Get AWS configuration from SERA CustomerConfig or environment fallback."""
    from .consts import get_aws_region
    
    try:
        # Try to import SERA CustomerConfig first
        # Calculate the correct path to backend from MCP server location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_path = os.path.join(current_dir, '..', '..', '..', '..', '..', 'backend')
        sys.path.append(backend_path)
        # Import after path modification
        from config.app_config import CustomerConfig
        
        # Load configuration if not already loaded
        if not CustomerConfig._config:
            CustomerConfig.load_config()
        
        return {
            "region": CustomerConfig.get_aws_region(),
            "profile": CustomerConfig.get_value('AWS_PROFILE', 'default'),
        }
    except Exception as e:
        logger.warning(f"Could not load SERA config, using environment fallback: {e}")
        # Fallback to environment variables using centralized get_aws_region()
        return {
            "region": get_aws_region(),
            "profile": os.getenv("AWS_PROFILE", "default"),
        }


class WellArchitectedToolClient:
    """
    AWS Well-Architected Tool API client for official WAFR integration.
    
    Enhanced with improved diagnostics, graceful fallback mechanisms, and
    comprehensive error handling for robust operation.
    Uses SERA AWS credentials automatically with fallback to local question library.
    """
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize Well-Architected Tool client using SERA AWS credentials.
        
        Args:
            region: Optional AWS region override (uses SERA config by default)
        """
        # Get AWS configuration from SERA
        aws_config = get_aws_config()
        self.region = region or aws_config["region"]
        self.profile_name = aws_config["profile"]
        
        logger.info(f"Initializing Enhanced Well-Architected Tool client with SERA credentials")
        logger.info(f"Using AWS profile: {self.profile_name}, region: {self.region}")
        
        # Initialize improved AWS client with enhanced diagnostics
        self.improved_client = ImprovedAWSClient(region=self.region)
        
        # Configure boto3 with retry and timeout settings
        config = Config(
            region_name=self.region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=10,
            read_timeout=10,  # Reduced from 30 to 10 seconds
            connect_timeout=5   # Reduced from 10 to 5 seconds
        )
        
        # Initialize boto3 session using AWS credential chain
        self.session = boto3.Session(region_name=self.region)
        self.client = self.session.client('wellarchitected', config=config)
        logger.info("Successfully initialized Well-Architected Tool client")
        
        # Rate limiting tracking
        self.last_api_call = 0
        self.api_call_count = 0
        self.rate_limit_delay = 0.1  # 100ms between calls
        
        # Enhanced features
        self.fallback_enabled = True
        self.api_health_status = "unknown"
        self.last_health_check = None
    
    async def _rate_limit_check(self):
        """Implement rate limiting to avoid API throttling."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_call
            await asyncio.sleep(sleep_time)
        
        self.last_api_call = time.time()
        self.api_call_count += 1
    
    async def _handle_api_call(self, operation_name: str, **kwargs) -> Dict[str, Any]:
        """
        Handle AWS API calls with error handling and rate limiting.
        
        Args:
            operation_name: Name of the AWS API operation
            **kwargs: Arguments for the API call
            
        Returns:
            API response data
            
        Raises:
            AWSIntegrationError: For API failures
        """
        await self._rate_limit_check()
        
        try:
            logger.debug(f"Making Well-Architected API call: {operation_name}")
            
            # Get the operation method from the client
            operation = getattr(self.client, operation_name)
            response = operation(**kwargs)
            
            logger.debug(f"API call successful: {operation_name}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(f"AWS API error in {operation_name}: {error_code} - {error_message}")
            
            # Handle specific error cases
            if error_code == 'ThrottlingException':
                # Exponential backoff for throttling
                backoff_time = min(2 ** (self.api_call_count % 5), 30)  # Max 30 seconds
                logger.warning(f"API throttled, backing off for {backoff_time} seconds")
                await asyncio.sleep(backoff_time)
                
                # Retry once after backoff
                try:
                    response = operation(**kwargs)
                    logger.info(f"API call successful after backoff: {operation_name}")
                    return response
                except ClientError as retry_error:
                    raise AWSIntegrationError(
                        f"Well-Architected API call failed after retry: {operation_name}",
                        error_code=retry_error.response['Error']['Code'],
                        operation=operation_name
                    )
            
            elif error_code in ['AccessDenied', 'UnauthorizedOperation']:
                raise AWSIntegrationError(
                    f"Insufficient permissions for Well-Architected API: {operation_name}",
                    error_code=error_code,
                    operation=operation_name
                )
            
            elif error_code == 'ResourceNotFoundException':
                raise AWSIntegrationError(
                    f"Well-Architected resource not found: {operation_name}",
                    error_code=error_code,
                    operation=operation_name
                )
            
            else:
                raise AWSIntegrationError(
                    f"Well-Architected API error: {error_message}",
                    error_code=error_code,
                    operation=operation_name
                )
        
        except BotoCoreError as e:
            logger.error(f"Boto3 error in {operation_name}: {str(e)}")
            raise AWSIntegrationError(
                f"AWS SDK error in {operation_name}: {str(e)}",
                operation=operation_name
            )
        
        except Exception as e:
            logger.error(f"Unexpected error in {operation_name}: {str(e)}")
            raise AWSIntegrationError(
                f"Unexpected error in Well-Architected API call: {str(e)}",
                operation=operation_name
            )
    
    async def create_workload(self, workload_data: Dict[str, Any]) -> str:
        """
        Create new Well-Architected workload.
        
        Args:
            workload_data: Workload configuration including name, description, environment, etc.
            
        Returns:
            Workload ID of the created workload
            
        Raises:
            AWSIntegrationError: If workload creation fails
        """
        try:
            logger.info(f"Creating Well-Architected workload: {workload_data.get('WorkloadName', 'Unknown')}")
            
            # Prepare workload creation parameters
            create_params = {
                'WorkloadName': workload_data.get('WorkloadName', f"SERA-Assessment-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"),
                'Description': workload_data.get('Description', 'WAFR Assessment generated by SERA'),
                'Environment': workload_data.get('Environment', 'PRODUCTION'),
                'ReviewOwner': workload_data.get('ReviewOwner', 'sera-assessment'),
                'AwsRegions': workload_data.get('AwsRegions', [self.region]),
                'NonAwsRegions': workload_data.get('NonAwsRegions', []),
                'PillarPriorities': workload_data.get('PillarPriorities', [
                    'security', 'reliability', 'performance', 'cost', 'operational', 'sustainability'
                ]),
                'ArchitecturalDesign': workload_data.get('ArchitecturalDesign', ''),
                'IndustryType': workload_data.get('IndustryType', 'Technology'),
                'Industry': workload_data.get('Industry', 'Technology')
            }
            
            # Add optional fields if provided
            if 'Lenses' in workload_data:
                create_params['Lenses'] = workload_data['Lenses']
            
            if 'Notes' in workload_data:
                create_params['Notes'] = workload_data['Notes']
            
            if 'Tags' in workload_data:
                create_params['Tags'] = workload_data['Tags']
            
            # Create workload
            response = await self._handle_api_call('create_workload', **create_params)
            
            workload_id = response['WorkloadId']
            workload_arn = response['WorkloadArn']
            
            logger.info(f"Successfully created workload: {workload_id}")
            logger.debug(f"Workload ARN: {workload_arn}")
            
            return workload_id
            
        except Exception as e:
            logger.error(f"Failed to create workload: {str(e)}")
            raise AWSIntegrationError(f"Failed to create Well-Architected workload: {str(e)}")
    
    async def get_workload(self, workload_id: str) -> Dict[str, Any]:
        """
        Retrieve existing workload data.
        
        Args:
            workload_id: Well-Architected workload ID
            
        Returns:
            Complete workload information
            
        Raises:
            AWSIntegrationError: If workload retrieval fails
        """
        try:
            logger.info(f"Retrieving workload: {workload_id}")
            
            response = await self._handle_api_call('get_workload', WorkloadId=workload_id)
            
            workload = response['Workload']
            
            logger.info(f"Successfully retrieved workload: {workload['WorkloadName']}")
            logger.debug(f"Workload environment: {workload.get('Environment', 'Unknown')}")
            
            return workload
            
        except Exception as e:
            logger.error(f"Failed to retrieve workload {workload_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to retrieve workload {workload_id}: {str(e)}")
    
    async def list_workloads(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        List available workloads.
        
        Args:
            max_results: Maximum number of workloads to return
            
        Returns:
            List of workload summaries
            
        Raises:
            AWSIntegrationError: If workload listing fails
        """
        try:
            logger.info("Listing Well-Architected workloads")
            
            workloads = []
            next_token = None
            
            while len(workloads) < max_results:
                params = {'MaxResults': min(50, max_results - len(workloads))}
                if next_token:
                    params['NextToken'] = next_token
                
                response = await self._handle_api_call('list_workloads', **params)
                
                workloads.extend(response.get('WorkloadSummaries', []))
                next_token = response.get('NextToken')
                
                if not next_token:
                    break
            
            logger.info(f"Found {len(workloads)} workloads")
            return workloads[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to list workloads: {str(e)}")
            raise AWSIntegrationError(f"Failed to list workloads: {str(e)}")
    
    async def list_answers(self, workload_id: str, pillar_id: str) -> List[Dict[str, Any]]:
        """
        Get pillar answers for workload.
        
        Args:
            workload_id: Well-Architected workload ID
            pillar_id: Pillar identifier (e.g., 'security', 'reliability')
            
        Returns:
            List of answers for the specified pillar
            
        Raises:
            AWSIntegrationError: If answer retrieval fails
        """
        try:
            logger.info(f"Retrieving answers for workload {workload_id}, pillar {pillar_id}")
            
            answers = []
            next_token = None
            
            while True:
                params = {
                    'WorkloadId': workload_id,
                    'PillarId': pillar_id,
                    'MaxResults': 50
                }
                if next_token:
                    params['NextToken'] = next_token
                
                response = await self._handle_api_call('list_answers', **params)
                
                answers.extend(response.get('AnswerSummaries', []))
                next_token = response.get('NextToken')
                
                if not next_token:
                    break
            
            logger.info(f"Retrieved {len(answers)} answers for {pillar_id} pillar")
            return answers
            
        except Exception as e:
            logger.error(f"Failed to list answers for {workload_id}/{pillar_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to list answers: {str(e)}")
    
    async def get_answer(self, workload_id: str, question_id: str) -> Dict[str, Any]:
        """
        Get specific answer details.
        
        Args:
            workload_id: Well-Architected workload ID
            question_id: Question identifier
            
        Returns:
            Detailed answer information
            
        Raises:
            AWSIntegrationError: If answer retrieval fails
        """
        try:
            logger.debug(f"Retrieving answer for question {question_id}")
            
            response = await self._handle_api_call(
                'get_answer',
                WorkloadId=workload_id,
                QuestionId=question_id
            )
            
            answer = response['Answer']
            
            logger.debug(f"Retrieved answer for question: {answer.get('QuestionTitle', question_id)}")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to get answer {workload_id}/{question_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to get answer: {str(e)}")
    
    async def update_answer(self, workload_id: str, question_id: str, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update answer for specific question.
        
        Args:
            workload_id: Well-Architected workload ID
            question_id: Question identifier
            answer_data: Answer update data including selected choices, notes, etc.
            
        Returns:
            Updated answer information
            
        Raises:
            AWSIntegrationError: If answer update fails
        """
        try:
            logger.info(f"Updating answer for question {question_id}")
            
            # Prepare update parameters
            update_params = {
                'WorkloadId': workload_id,
                'QuestionId': question_id
            }
            
            # Add answer data
            if 'SelectedChoices' in answer_data:
                update_params['SelectedChoices'] = answer_data['SelectedChoices']
            
            if 'ChoiceUpdates' in answer_data:
                update_params['ChoiceUpdates'] = answer_data['ChoiceUpdates']
            
            if 'Notes' in answer_data:
                update_params['Notes'] = answer_data['Notes']
            
            if 'IsApplicable' in answer_data:
                update_params['IsApplicable'] = answer_data['IsApplicable']
            
            if 'Reason' in answer_data:
                update_params['Reason'] = answer_data['Reason']
            
            response = await self._handle_api_call('update_answer', **update_params)
            
            answer = response['Answer']
            
            logger.info(f"Successfully updated answer for question: {answer.get('QuestionTitle', question_id)}")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to update answer {workload_id}/{question_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to update answer: {str(e)}")
    
    async def get_workload_summary(self, workload_id: str) -> Dict[str, Any]:
        """
        Get workload summary with pillar scores.
        
        Args:
            workload_id: Well-Architected workload ID
            
        Returns:
            Workload summary with pillar risk counts and scores
            
        Raises:
            AWSIntegrationError: If summary retrieval fails
        """
        try:
            logger.info(f"Retrieving workload summary: {workload_id}")
            
            response = await self._handle_api_call('get_workload', WorkloadId=workload_id)
            
            workload = response['Workload']
            
            # Get pillar risk counts
            pillar_summaries = {}
            for pillar_id in ['security', 'reliability', 'performance', 'cost', 'operational', 'sustainability']:
                try:
                    answers = await self.list_answers(workload_id, pillar_id)
                    
                    # Count risks by level
                    high_risks = sum(1 for answer in answers if answer.get('Risk') == 'HIGH')
                    medium_risks = sum(1 for answer in answers if answer.get('Risk') == 'MEDIUM')
                    low_risks = sum(1 for answer in answers if answer.get('Risk') == 'LOW')
                    no_risks = sum(1 for answer in answers if answer.get('Risk') == 'NONE')
                    
                    pillar_summaries[pillar_id] = {
                        'high_risk_count': high_risks,
                        'medium_risk_count': medium_risks,
                        'low_risk_count': low_risks,
                        'no_risk_count': no_risks,
                        'total_questions': len(answers)
                    }
                    
                except Exception as pillar_error:
                    logger.warning(f"Failed to get {pillar_id} pillar summary: {pillar_error}")
                    pillar_summaries[pillar_id] = {
                        'high_risk_count': 0,
                        'medium_risk_count': 0,
                        'low_risk_count': 0,
                        'no_risk_count': 0,
                        'total_questions': 0,
                        'error': str(pillar_error)
                    }
            
            summary = {
                'workload_id': workload_id,
                'workload_name': workload.get('WorkloadName', 'Unknown'),
                'description': workload.get('Description', ''),
                'environment': workload.get('Environment', 'PRODUCTION'),
                'updated_at': workload.get('UpdatedAt'),
                'pillar_summaries': pillar_summaries,
                'total_high_risks': sum(p.get('high_risk_count', 0) for p in pillar_summaries.values()),
                'total_medium_risks': sum(p.get('medium_risk_count', 0) for p in pillar_summaries.values()),
                'total_low_risks': sum(p.get('low_risk_count', 0) for p in pillar_summaries.values())
            }
            
            logger.info(f"Retrieved workload summary: {summary['total_high_risks']} high risks, {summary['total_medium_risks']} medium risks")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get workload summary {workload_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to get workload summary: {str(e)}")
    
    async def delete_workload(self, workload_id: str) -> bool:
        """
        Delete a workload.
        
        Args:
            workload_id: Well-Architected workload ID
            
        Returns:
            True if deletion was successful
            
        Raises:
            AWSIntegrationError: If workload deletion fails
        """
        try:
            logger.info(f"Deleting workload: {workload_id}")
            
            await self._handle_api_call('delete_workload', WorkloadId=workload_id)
            
            logger.info(f"Successfully deleted workload: {workload_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workload {workload_id}: {str(e)}")
            raise AWSIntegrationError(f"Failed to delete workload: {str(e)}")
    
    async def get_lens_questions(self, lens_alias: str = "wellarchitected") -> Dict[str, Any]:
        """
        Get questions for a specific lens (framework) with enhanced diagnostics and fallback.
        
        Args:
            lens_alias: Lens identifier (default: "wellarchitected" for AWS Well-Architected Framework)
            
        Returns:
            Lens questions organized by pillar (from API or fallback library)
            
        Raises:
            AWSIntegrationError: If both API and fallback fail
        """
        try:
            logger.info(f"🔍 Retrieving lens questions with enhanced diagnostics: {lens_alias}")
            
            # First, try the improved client with diagnostics
            result = await self.improved_client.get_lens_questions_with_diagnostics(lens_alias)
            
            if result.success and result.total_questions > 0:
                logger.info(f"✅ Successfully retrieved {result.total_questions} questions from AWS API")
                self.api_health_status = "healthy"
                
                # Convert to expected format
                return {
                    'lens_alias': lens_alias,
                    'lens_name': 'AWS Well-Architected Framework',
                    'lens_version': '1.0',
                    'description': 'Official AWS Well-Architected Framework questions',
                    'pillar_questions': result.questions_by_pillar,
                    'questions': result.questions,
                    'source': 'aws_api',
                    'diagnostic_info': {
                        'retrieval_time_ms': result.retrieval_time_ms,
                        'total_questions': result.total_questions
                    }
                }
            else:
                logger.warning(f"⚠️ AWS API returned no questions: {result.error_details}")
                logger.info("🔄 Falling back to comprehensive local question library")
                
                # Fall back to comprehensive question library
                fallback_result = await self.improved_client.get_fallback_questions()
                
                if fallback_result and 'pillar_questions' in fallback_result:
                    total_fallback = sum(
                        len(pillar_data.get('questions', [])) 
                        for pillar_data in fallback_result['pillar_questions'].values()
                    )
                    
                    logger.info(f"✅ Successfully loaded {total_fallback} questions from fallback library")
                    self.api_health_status = "degraded"
                    
                    return {
                        **fallback_result,
                        'source': 'fallback_library',
                        'api_diagnostic': {
                            'api_failed': True,
                            'error_details': result.error_details,
                            'diagnostic_logs': result.diagnostic_logs
                        }
                    }
                else:
                    raise AWSIntegrationError("Both AWS API and fallback library failed")
            
        except Exception as e:
            logger.error(f"❌ Failed to get lens questions for {lens_alias}: {str(e)}")
            
            # Last resort: try basic fallback
            try:
                logger.info("🆘 Attempting emergency fallback to basic questions")
                basic_fallback = await self._get_emergency_fallback_questions()
                
                if basic_fallback:
                    logger.warning("⚠️ Using emergency fallback questions - limited functionality")
                    self.api_health_status = "critical"
                    return basic_fallback
                
            except Exception as fallback_error:
                logger.error(f"❌ Emergency fallback also failed: {fallback_error}")
            
            raise AWSIntegrationError(f"All question retrieval methods failed: {str(e)}")
    
    async def _get_emergency_fallback_questions(self) -> Dict[str, Any]:
        """Emergency fallback with minimal questions for basic assessment"""
        return {
            'lens_alias': 'emergency-fallback',
            'lens_name': 'Emergency Fallback Questions',
            'lens_version': '1.0',
            'description': 'Minimal question set for emergency use',
            'pillar_questions': {
                'security': {
                    'pillar_name': 'Security',
                    'questions': [
                        {
                            'question_id': 'SEC-EMERGENCY-001',
                            'question_text': 'How do you manage access to AWS resources?',
                            'category': 'critical',
                            'weight': 3.0
                        },
                        {
                            'question_id': 'SEC-EMERGENCY-002',
                            'question_text': 'How do you protect data at rest and in transit?',
                            'category': 'critical',
                            'weight': 3.0
                        }
                    ]
                },
                'reliability': {
                    'pillar_name': 'Reliability',
                    'questions': [
                        {
                            'question_id': 'REL-EMERGENCY-001',
                            'question_text': 'How do you design for failure?',
                            'category': 'critical',
                            'weight': 3.0
                        }
                    ]
                }
            },
            'source': 'emergency_fallback',
            'warning': 'Limited question set - recommend fixing API access for full assessment'
        }
    
    async def test_api_connectivity(self) -> APITestResult:
        """
        Test AWS API connectivity with comprehensive diagnostics
        
        Returns:
            Detailed test results including diagnostics and recommendations
        """
        logger.info("🧪 Testing AWS API connectivity with enhanced diagnostics")
        
        result = await self.improved_client.test_api_connectivity()
        self.last_health_check = result.test_timestamp
        
        if result.success:
            self.api_health_status = "healthy"
            logger.info(f"✅ API connectivity test passed: {result.question_count} questions available")
        else:
            self.api_health_status = "unhealthy"
            logger.warning(f"⚠️ API connectivity test failed: {result.error_details}")
        
        return result
    
    async def diagnose_api_issues(self) -> Dict[str, Any]:
        """
        Comprehensive diagnosis of API issues with detailed recommendations
        
        Returns:
            Diagnostic report with findings and recommended actions
        """
        logger.info("🔬 Running comprehensive API diagnostics")
        
        diagnostic_report = await self.improved_client.diagnose_empty_response()
        
        # Convert to dictionary format for easier consumption
        return {
            'timestamp': diagnostic_report.timestamp.isoformat(),
            'overall_status': {
                'credentials': diagnostic_report.credentials_status,
                'api_connectivity': diagnostic_report.api_connectivity,
                'lens_accessibility': diagnostic_report.lens_accessibility,
                'question_availability': diagnostic_report.question_availability
            },
            'detailed_findings': diagnostic_report.detailed_findings,
            'recommended_actions': diagnostic_report.recommended_actions,
            'performance_metrics': diagnostic_report.performance_metrics,
            'raw_responses': diagnostic_report.raw_api_responses,
            'summary': self._generate_diagnostic_summary(diagnostic_report)
        }
    
    def _generate_diagnostic_summary(self, report) -> str:
        """Generate human-readable diagnostic summary"""
        if (report.credentials_status == "VALID" and 
            report.api_connectivity == "ACCESSIBLE" and 
            report.lens_accessibility == "AVAILABLE"):
            
            if report.question_availability == "UNAVAILABLE":
                return ("API is working correctly. Empty question responses are expected AWS behavior. "
                       "Questions require workload context. Fallback library is recommended for standalone assessments.")
            else:
                return "All systems operational. API is fully functional."
        else:
            issues = []
            if report.credentials_status != "VALID":
                issues.append("credential issues")
            if report.api_connectivity != "ACCESSIBLE":
                issues.append("API access problems")
            if report.lens_accessibility != "AVAILABLE":
                issues.append("lens access issues")
            
            return f"API issues detected: {', '.join(issues)}. Check recommended actions for resolution."
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get enhanced client configuration and diagnostic information.
        
        Returns:
            Comprehensive client status including diagnostics and health metrics
        """
        # Get diagnostic summary from improved client
        diagnostic_summary = self.improved_client.get_diagnostic_summary()
        
        return {
            'region': self.region,
            'profile_name': self.profile_name,
            'api_call_count': self.api_call_count,
            'rate_limit_delay': self.rate_limit_delay,
            'client_initialized': bool(self.client),
            'api_health_status': self.api_health_status,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'fallback_enabled': self.fallback_enabled,
            'enhanced_diagnostics': diagnostic_summary,
            'capabilities': {
                'api_connectivity_testing': True,
                'comprehensive_diagnostics': True,
                'graceful_fallback': True,
                'performance_monitoring': True,
                'detailed_error_analysis': True
            },
            'recommendations': [
                "Run test_api_connectivity() to verify AWS API access",
                "Use diagnose_api_issues() for detailed troubleshooting",
                "Fallback question library provides reliable assessment capability",
                "Monitor api_health_status for proactive issue detection"
            ]
        }