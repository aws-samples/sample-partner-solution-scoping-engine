"""
Nova Act API Routes
Direct API endpoints for Nova Act execution and status checking
"""

from flask import Blueprint, jsonify, request
import logging
import uuid
import os
from ..models.chat import get_chat_documents, update_chat_document, get_chat_by_chat_id
from ..middleware.auth_middleware import login_required, get_current_user
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

nova_act_bp = Blueprint('nova_act', __name__)


def _localhost_or_login_required(f):
    """Allow localhost requests without auth, require login for all others."""
    @wraps(f)
    def decorated(*args, **kwargs):
        remote = request.remote_addr
        if remote in ('127.0.0.1', '::1'):
            return f(*args, **kwargs)
        return login_required(f)(*args, **kwargs)
    return decorated

def _update_job_status(chat_id: str, job_id: str, status_update: dict):
    """Update job status in DynamoDB"""
    try:
        documents = get_chat_documents(chat_id)
        if job_id in documents:
            doc_data = documents[job_id]
            doc_data.update(status_update)
            update_chat_document(chat_id, job_id, doc_data)
    except Exception as e:
        logger.error(f"Update job status failed: error={str(e)}")

@nova_act_bp.route('/nova/execute', methods=['POST'])
@_localhost_or_login_required
def execute_nova_act():
    """Execute Nova Act with provided instructions - Direct API"""
    try:
        current_user = get_current_user()
        logger.debug("Nova Act execution request received")
        
        data = request.get_json()
        if not data:
            logger.warning("Nova Act request missing data")
            return jsonify({"error": "No data provided"}), 400
            
        instructions = data.get('instructions')
        if not instructions:
            logger.warning("Nova Act request missing instructions")
            return jsonify({"error": "instructions required"}), 400
            
        actions = instructions.get('actions', [])
        if not actions:
            logger.warning("Nova Act request has no actions")
            return jsonify({"error": "No actions found in instructions"}), 400
            
        chat_id = data.get('chat_id')
        if not chat_id:
            logger.warning("Nova Act request missing chat_id")
            return jsonify({"error": "chat_id required"}), 400
        
        # Validate user can access the chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        # Skip user access check for internal localhost calls (already authenticated upstream)
        if request.remote_addr not in ('127.0.0.1', '::1'):
            if not current_user or not current_user.can_access_chat(chat['user_id']):
                logger.warning(f"Access denied: user={getattr(current_user, 'user_id', 'unknown')}, chat_owner={chat['user_id']}")
                return jsonify({"error": "Access denied"}), 403
            
        logger.info(f"Nova Act execution starting: chat_id={chat_id}, actions={len(actions)}")
        
        # Generate document ID (which serves as job ID)
        doc_id = f"{str(uuid.uuid4())}"
        
        doc_data = {
            "document_type": "calculator_link",
            "status": "pending",
            "progress": "Initializing Nova Act execution...",
            "result": None,
            "error": None,
            "actions_total": len(actions),
            "actions_completed": 0,
            "created_timestamp": datetime.now().isoformat(),
            "instructions": instructions
        }
        
        success = update_chat_document(chat_id, doc_id, doc_data)
        if not success:
            return jsonify({"error": "Failed to create job document"}), 500
        
        logger.info(f"Started Nova Act job {doc_id} with {len(actions)} actions")
        
        # Return 200 immediately
        response = jsonify({
            "job_id": doc_id,
            "chat_id": chat_id,
            "status": "started",
            "message": "Nova Act execution started"
        })
        
        # Continue processing after response is sent
        @response.call_on_close
        def execute_after_response():
            _execute_nova_act_sync(doc_id, chat_id, instructions)
        
        return response
        
    except Exception as e:
        logger.error(f"Start Nova Act failed: error={str(e)}")
        return jsonify({"error": "Operation failed"}), 500


def _execute_enhanced_scroll(nova, act_command: str, job_id: str):
    """Enhanced scroll function that continues until target is found or page is fully traversed"""
    import time
    
    logger.info(f"Job {job_id}: Enhanced scroll for: {act_command}")
    
    # Extract target from command (e.g., "Dashboards and Alarms card")
    target = act_command.lower().replace('scroll down to ', '').replace('scroll to ', '').replace(' if not visible', '')
    
    max_scrolls = 20  # Prevent infinite scrolling
    scroll_attempts = 0
    last_page_height = 0
    result = None  # Initialize result to prevent UnboundLocalError
    
    while scroll_attempts < max_scrolls:
        try:
            # Try the original scroll command first
            result = nova.act(act_command, max_steps=5)
            
            # Check if we can find the target element on the page
            current_page_height = nova.page.evaluate("document.body.scrollHeight")
            
            # If page height hasn't changed in 3 attempts, we've likely reached the end
            if current_page_height == last_page_height:
                scroll_attempts += 1
                if scroll_attempts >= 3:
                    logger.info(f"Job {job_id}: Page height unchanged, likely at end of page")
                    break
            else:
                scroll_attempts = 0  # Reset counter if page is still changing
                
            last_page_height = current_page_height
            
            # Small delay to allow page to load
            time.sleep(1)
            
            # Try to continue scrolling down if target not found
            try:
                nova.act("Scroll down", max_steps=3)
            except:
                break
                
        except Exception as e:
            logger.warning(f"Scroll failed: job_id={job_id}, error={str(e)}")
            break
    
    logger.info(f"Job {job_id}: Enhanced scroll completed after {scroll_attempts} attempts")
    return result


def _is_critical_action(act: str) -> bool:
    """Determine if an action is critical and should stop execution if it fails"""
    act_lower = act.lower()
    
    # Only the final clipboard/link retrieval actions are critical
    if 'copy public link' in act_lower:
        return True
    if 'clipboard' in act_lower:
        return True
    
    # All other actions are non-critical - continue execution even if they fail
    return False

def _execute_nova_act_sync(job_id: str, chat_id: str, instructions: dict):
    """Execute Nova Act directly after response is sent"""
    logger.info(f"Direct execution started for job {job_id}")
    
    try:
        # Update status to running
        _update_job_status(chat_id, job_id, {
            "status": "running",
            "progress": "Starting browser session..."
        })
        
        actions = instructions.get('actions', [])
        if not actions:
            _update_job_status(chat_id, job_id, {
                "status": "failed",
                "error": "No actions found",
                "progress": "Failed: No actions found"
            })
            return
        
        # Load configuration
        from config.app_config import CustomerConfig
        CustomerConfig.load_config()
        
        auth_method = CustomerConfig.get_value('NOVA_ACT_AUTH_METHOD', 'api_key')
        
        # Setup authentication based on method
        if auth_method == 'api_key':
            try:
                import boto3
                import json
                secret_name = CustomerConfig.get_value('NOVA_ACT_API_SECRET')
                if secret_name:
                    secrets_client = boto3.client('secretsmanager', region_name=CustomerConfig.get_value('AWS_REGION'))
                    secret_response = secrets_client.get_secret_value(SecretId=secret_name)
                    secret_data = json.loads(secret_response['SecretString'])
                    nova_key = secret_data.get('api_key')
                    
                    if nova_key:
                        os.environ['NOVA_ACT_API_KEY'] = nova_key
                        logger.info(f"Job {job_id}: Using API key authentication")
                    else:
                        logger.error(f"Job {job_id}: api_key not found in secret {secret_name}")
                else:
                    logger.error(f"Job {job_id}: NOVA_ACT_API_SECRET not found in config")
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to load API key: {e}")
        else:
            logger.info(f"Job {job_id}: Using IAM authentication")
        
        from nova_act import NovaAct, Workflow
        
        logger.info(f"Job {job_id}: Starting Nova Act with {len(actions)} actions")
        
        # Use IAM authentication with Workflow context manager
        if auth_method == 'iam':
            workflow_name = CustomerConfig.get_value('NOVA_ACT_WORKFLOW_NAME', 'sera-pricing-calculator-workflow')
            model_id = CustomerConfig.get_value('NOVA_ACT_MODEL_ID', 'nova-act-latest')
            
            with Workflow(workflow_definition_name=workflow_name, model_id=model_id) as workflow:
                with NovaAct(
                    starting_page="https://calculator.aws/#/addService",
                    workflow=workflow,
                    headless=True,
                    screen_height=910,
                    screen_width=1300
                ) as nova:
                    _execute_nova_actions(nova, job_id, chat_id, actions)
        else:
            # Use API key authentication
            with NovaAct(
                starting_page="https://calculator.aws/#/addService",
                headless=True,
                screen_height=976,
                screen_width=1280
            ) as nova:
                _execute_nova_actions(nova, job_id, chat_id, actions)
                
    except Exception as e:
        logger.error(f"Job {job_id}: Nova Act execution failed: {e}", exc_info=True)
        _update_job_status(chat_id, job_id, {
            "status": "failed",
            "error": str(e),
            "progress": f"Failed: {str(e)}"
        })

def _execute_nova_actions(nova, job_id: str, chat_id: str, actions: list):
    """Execute Nova Act actions"""
    logger.info(f"Job {job_id}: Nova Act initialized successfully")
    
    for i, action in enumerate(actions):
        act_command = action.get('act', '') if isinstance(action, dict) else str(action)
        if not act_command:
            continue
            
        logger.info(f"Job {job_id}: Executing action {i+1}/{len(actions)}: {act_command}")
        
        # Update status with current action
        _update_job_status(chat_id, job_id, {
            "progress": f"Executing action {i+1}/{len(actions)}: {act_command}",
            "actions_completed": i
        })
        
        try:
            # Handle scroll actions with enhanced logic
            if 'scroll' in act_command.lower() and 'if not visible' in act_command.lower():
                result = _execute_enhanced_scroll(nova, act_command, job_id)
            else:
                # Execute action directly (Nova ACT handles its own timeouts)
                result = nova.act(act_command, max_steps=10)
            logger.info(f"Job {job_id}: Action {i+1} completed successfully")
        except TimeoutError as e:
            logger.error(f"Action timeout: job_id={job_id}, action={i+1}, error={str(e)}")
            is_critical = _is_critical_action(act_command)
            if is_critical:
                raise e
            else:
                logger.info(f"Job {job_id}: Continuing execution after non-critical action timeout")
        except Exception as e:
            is_critical = _is_critical_action(act_command)
            logger.warning(f"Action failed: job_id={job_id}, action={i+1}, critical={is_critical}, error={str(e)}")
            
            if is_critical:
                # Critical action failed, stop execution
                raise e
            else:
                # Non-critical action failed, continue execution
                logger.info(f"Job {job_id}: Continuing execution after non-critical action failure")
        
        # Update completion
        _update_job_status(chat_id, job_id, {
            "actions_completed": i + 1
        })
        
    logger.info(f"Job {job_id}: All Nova Act actions completed")
    
    # Read clipboard for public link
    try:
        logger.info(f"Job {job_id}: Reading clipboard for public link...")
        nova.page.context.grant_permissions(["clipboard-read"])
        
        clipboard_text = nova.page.evaluate("""
            async () => {
                return await navigator.clipboard.readText();
            }
        """)
        
        if clipboard_text and 'calculator.aws' in clipboard_text:
            logger.info(f"Job {job_id}: Retrieved public link: {clipboard_text}")
            _update_job_status(chat_id, job_id, {
            "status": "completed",
            "progress": "✅ Public link generated successfully",
            "result": clipboard_text,
            "actions_completed": len(actions)
        })
        else:
            logger.info(f"Job {job_id}: No valid link found in clipboard")
            _update_job_status(chat_id, job_id, {
                "status": "completed",
                "progress": "✅ Configuration completed (no public link)",
                "result": "Calculator configured but no public link generated",
                "actions_completed": len(actions)
            })
    except Exception as e:
        logger.warning(f"Clipboard retrieval failed: job_id={job_id}, error={str(e)}")
        _update_job_status(chat_id, job_id, {
            "status": "completed",
            "progress": "✅ Configuration completed (no public link)",
            "result": "Calculator configured but no public link generated",
            "actions_completed": len(actions)
        })
                
    except Exception as e:
        # Find the current action index for better error reporting
        current_action = "Unknown action"
        current_index = 0
        try:
            # Get the action that was being executed when the error occurred
            actions = instructions.get('actions', [])
            if actions:
                # This is a rough estimate - the actual failed action might be different
                # but it gives context about where in the process the failure occurred
                current_action = str(actions[min(len(actions)-1, current_index)])
        except:
            pass
            
        _update_job_status(chat_id, job_id, {
            "status": "failed",
            "error": str(e),
            "progress": f"Failed on action: {current_action}"
        })
        logger.error(f"Job failed: job_id={job_id}, error={str(e)}")

@nova_act_bp.route('/nova/status/<job_id>', methods=['GET'])
@login_required
def get_job_status(job_id):
    """Get Nova Act job status by job ID from DynamoDB""" 
    try:
        current_user = get_current_user()
        chat_id = request.args.get('chat_id')
        if not chat_id:
            return jsonify({
                "error": "chat_id parameter required",
                "job_id": job_id
            }), 400
        
        # Validate user owns the chat
        chat = get_chat_by_chat_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found", "job_id": job_id}), 404
        
        if not current_user.can_access_chat(chat['user_id']):
            return jsonify({"error": "Access denied", "job_id": job_id}), 403
        
        documents = get_chat_documents(chat_id)
        
        # Use job_id as document ID directly
        if job_id in documents:
            doc_data = documents[job_id]
            status = doc_data.get('status', 'unknown')
                
            # Check if job is still active and has been pending/running for at least an hour
            if status in ['pending', 'running']:
                created_at = doc_data.get('created_timestamp')
                if created_at:

                    # Parse created_at timestamp (isoformat only)
                    created_time = datetime.fromisoformat(created_at)
                    
                    # Compare using the same method: datetime.now()
                    current_time = datetime.now()
                    time_diff = current_time - created_time
                    
                    if time_diff.total_seconds() >= 3600:  # 1 hour = 3600 seconds
                        logger.info(f"Job {job_id} has been running for {time_diff.total_seconds()/60:.1f} minutes, marking as timed out")
                        
                        # Mark job as failed/timed out
                        _update_job_status(chat_id, job_id, {
                            'status': 'failed',
                            'error': 'Job timed out after 1 hour',
                            'progress': 'Failed: Timed out after 1 hour'
                        })
                        logger.info(f"Updated job {job_id} status to failed due to timeout")
            
            return jsonify({
                "job_id": job_id,
                "status": doc_data.get('status', 'unknown'),
                "progress": doc_data.get('progress', 'No progress info'),
                "actions_completed": doc_data.get('actions_completed', 0),
                "actions_total": doc_data.get('actions_total', 0),
                "result": doc_data.get('result'),
                "error": doc_data.get('error')
            })
        
        # Job not found in documents
        return jsonify({
            "error": "Job not found",
            "job_id": job_id
        }), 404
        
    except Exception as e:
        logger.error(f"Get job status failed: error={str(e)}")
        return jsonify({
            "error": str(e),
            "job_id": job_id
        }), 500