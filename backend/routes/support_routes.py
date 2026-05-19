from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import login_required, get_current_user
from ..models.support_relationship import get_support_team, add_support_member, remove_support_member
import logging

logger = logging.getLogger(__name__)

support_bp = Blueprint('support', __name__)

@support_bp.route('/support/team', methods=['GET'])
@login_required
def get_my_support_team():
    """Get current user's support team."""
    current_user = get_current_user()
    
    try:
        logger.debug(f"Getting support team: user={current_user.user_id}")
        support_team = get_support_team(current_user.user_id)
        logger.debug(f"Support team retrieved: user={current_user.user_id}, count={len(support_team)}")
        return jsonify({
            'success': True,
            'support_team': support_team
        })
    except Exception as e:
        logger.error(f"Get support team failed: user={current_user.user_id}, error={str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@support_bp.route('/support/add', methods=['POST'])
@login_required
def add_support():
    """Add a support member."""
    current_user = get_current_user()
    data = request.get_json()
    
    support_member_id = data.get('support_member_id')
    support_member_role = data.get('support_member_role', 'solution_architect')
    
    if not support_member_id:
        logger.warning(f"Add support missing member_id: user={current_user.user_id}")
        return jsonify({
            'success': False,
            'error': 'support_member_id is required'
        }), 400
    
    # Validate support_member_id format (email-like or alphanumeric identifier, max 256 chars)
    import re
    if not isinstance(support_member_id, str) or len(support_member_id) > 256 or not re.match(r'^[\w.@+\-]+$', support_member_id):
        logger.warning(f"Invalid support_member_id format: user={current_user.user_id}")
        return jsonify({'success': False, 'error': 'Invalid support_member_id format'}), 400
    
    # Validate support_member_role against allowlist
    VALID_SUPPORT_ROLES = {'solution_architect', 'sa_manager', 'proserve'}
    if support_member_role not in VALID_SUPPORT_ROLES:
        logger.warning(f"Invalid support_member_role: {support_member_role}, user={current_user.user_id}")
        return jsonify({'success': False, 'error': f'Invalid role. Must be one of: {", ".join(sorted(VALID_SUPPORT_ROLES))}'}), 400
    
    try:
        logger.debug(f"Adding support member: seller={current_user.user_id}, member={support_member_id}, role={support_member_role}")
        add_support_member(current_user.user_id, support_member_id, support_member_role)
        logger.info(f"Support member added: seller={current_user.user_id}, member={support_member_id}, role={support_member_role}")
        return jsonify({
            'success': True,
            'message': f'Added {support_member_id} as {support_member_role}'
        })
    except Exception as e:
        logger.error(f"Add support member failed: seller={current_user.user_id}, member={support_member_id}, error={str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@support_bp.route('/support/remove', methods=['POST'])
@login_required
def remove_support():
    """Remove a support member."""
    current_user = get_current_user()
    data = request.get_json()
    
    support_member_id = data.get('support_member_id')
    
    if not support_member_id:
        logger.warning(f"Remove support missing member_id: user={current_user.user_id}")
        return jsonify({
            'success': False,
            'error': 'support_member_id is required'
        }), 400
    
    try:
        logger.debug(f"Removing support member: seller={current_user.user_id}, member={support_member_id}")
        remove_support_member(current_user.user_id, support_member_id)
        logger.info(f"Support member removed: seller={current_user.user_id}, member={support_member_id}")
        return jsonify({
            'success': True,
            'message': f'Removed {support_member_id} from support team'
        })
    except Exception as e:
        logger.error(f"Remove support member failed: seller={current_user.user_id}, member={support_member_id}, error={str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
