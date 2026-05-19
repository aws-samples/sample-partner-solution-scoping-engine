#!/usr/bin/env python3
"""
WAFR Feature Flags System
Safe rollout and configuration management for AI enhancements
"""

import logging
import os
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class WAFRFeatureFlags:
    """
    Feature flags system for WAFR AI enhancements
    Enables safe rollout and A/B testing of new capabilities
    """
    
    def __init__(self):
        """Initialize feature flags system"""
        self.flags = self._load_default_flags()
        self._load_environment_overrides()
        
        logger.info(f"🚩 WAFR Feature Flags initialized with {len(self.flags)} features")
    
    def _load_default_flags(self) -> Dict[str, Dict[str, Any]]:
        """Load default feature flag configurations"""
        
        return {
            'ai_analysis': {
                'enabled': True,  # MANDATORY: Enable AI for funding reviewer-level quality
                'description': 'AI-powered document analysis using Bedrock (MANDATORY for quality)',
                'rollout_percentage': 100,  # Full rollout for quality
                'allowed_chat_ids': [],  # All users get AI analysis
                'blocked_chat_ids': [],  # No blocking unless explicitly needed
                'requirements': ['bedrock_available', 'aws_credentials'],
                'fallback_enabled': True,  # Still allow fallback for reliability
                'mandatory': True  # Mark as mandatory feature
            },
            
            'vision_analysis': {
                'enabled': True,  # MANDATORY: Enable vision for diagram analysis
                'description': 'Vision analysis for architecture diagrams (MANDATORY for accuracy)',
                'rollout_percentage': 100,  # Full rollout
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': ['ai_analysis', 'bedrock_vision_model'],
                'fallback_enabled': True,
                'mandatory': True  # Mark as mandatory feature
            },
            
            'evidence_based_scoring': {
                'enabled': True,  # Safe to enable - enhances existing scoring
                'description': 'Enhanced scoring with evidence citations',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': [],
                'fallback_enabled': True
            },
            
            'cross_document_correlation': {
                'enabled': True,  # Safe enhancement
                'description': 'Cross-document consistency analysis',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': [],
                'fallback_enabled': True
            },
            
            'enhanced_recommendations': {
                'enabled': True,  # MANDATORY: Enhanced recommendations for funding reviewer quality
                'description': 'Architecture-specific recommendations with evidence (MANDATORY)',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': [],
                'fallback_enabled': True,
                'mandatory': True
            },
            
            'business_impact_quantification': {
                'enabled': True,  # MANDATORY: Business impact analysis
                'description': 'Quantified business impact analysis with ROI calculations (MANDATORY)',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': [],
                'fallback_enabled': False,  # No fallback - this is core functionality
                'mandatory': True
            },
            
            'advanced_visualizations': {
                'enabled': True,  # MANDATORY: Advanced visualizations
                'description': 'Capability coverage matrices and advanced charts (MANDATORY)',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': [],
                'fallback_enabled': False,  # No fallback - this is core functionality
                'mandatory': True
            },
            
            'funding_reviewer_mode': {
                'enabled': True,  # MANDATORY: Funding reviewer-level analysis
                'description': 'Complete funding reviewer-level analysis and reporting (MANDATORY)',
                'rollout_percentage': 100,
                'allowed_chat_ids': [],
                'blocked_chat_ids': [],
                'requirements': ['ai_analysis', 'enhanced_recommendations', 'business_impact_quantification'],
                'fallback_enabled': False,  # No fallback - this is the target quality
                'mandatory': True
            }
        }
    
    def _load_environment_overrides(self):
        """Load feature flag overrides from environment variables"""
        
        # Check for global AI enable/disable
        ai_enabled = os.getenv('WAFR_AI_ENABLED', '').lower()
        if ai_enabled in ['true', '1', 'yes']:
            self.flags['ai_analysis']['enabled'] = True
            self.flags['vision_analysis']['enabled'] = True
            logger.info("🤖 AI features enabled via environment variable")
        elif ai_enabled in ['false', '0', 'no']:
            self.flags['ai_analysis']['enabled'] = False
            self.flags['vision_analysis']['enabled'] = False
            logger.info("🚫 AI features disabled via environment variable")
        
        # Check for specific feature overrides
        for feature_name in self.flags.keys():
            env_var = f'WAFR_FEATURE_{feature_name.upper()}'
            env_value = os.getenv(env_var, '').lower()
            
            if env_value in ['true', '1', 'yes']:
                self.flags[feature_name]['enabled'] = True
                logger.info(f"✅ Feature '{feature_name}' enabled via environment")
            elif env_value in ['false', '0', 'no']:
                self.flags[feature_name]['enabled'] = False
                logger.info(f"❌ Feature '{feature_name}' disabled via environment")
        
        # Load rollout percentages
        for feature_name in self.flags.keys():
            rollout_var = f'WAFR_ROLLOUT_{feature_name.upper()}'
            rollout_value = os.getenv(rollout_var)
            
            if rollout_value and rollout_value.isdigit():
                percentage = int(rollout_value)
                if 0 <= percentage <= 100:
                    self.flags[feature_name]['rollout_percentage'] = percentage
                    logger.info(f"📊 Feature '{feature_name}' rollout set to {percentage}%")
    
    def is_enabled(self, feature_name: str, chat_id: Optional[str] = None) -> bool:
        """
        Check if a feature is enabled for a specific context
        
        Args:
            feature_name: Name of the feature to check
            chat_id: Optional chat ID for user-specific checks
            
        Returns:
            True if feature is enabled, False otherwise
        """
        
        if feature_name not in self.flags:
            logger.warning(f"⚠️ Unknown feature flag: {feature_name}")
            return False
        
        flag = self.flags[feature_name]
        
        # Check if feature is globally disabled
        if not flag['enabled']:
            return False
        
        # Check if chat_id is blocked
        if chat_id and chat_id in flag.get('blocked_chat_ids', []):
            logger.info(f"🚫 Feature '{feature_name}' blocked for chat_id: {chat_id}")
            return False
        
        # Check if chat_id is explicitly allowed
        allowed_chat_ids = flag.get('allowed_chat_ids', [])
        if allowed_chat_ids and chat_id:
            if chat_id in allowed_chat_ids:
                logger.info(f"✅ Feature '{feature_name}' explicitly allowed for chat_id: {chat_id}")
                return True
            else:
                logger.info(f"❌ Feature '{feature_name}' not in allowed list for chat_id: {chat_id}")
                return False
        
        # Check rollout percentage
        rollout_percentage = flag.get('rollout_percentage', 0)
        if rollout_percentage < 100:
            # Simple hash-based rollout (deterministic for same chat_id)
            if chat_id:
                hash_value = hash(chat_id) % 100
                enabled = hash_value < rollout_percentage
                logger.info(f"📊 Feature '{feature_name}' rollout check: {hash_value} < {rollout_percentage} = {enabled}")
                return enabled
            else:
                # No chat_id, use random rollout
                import random
                return random.randint(0, 99) < rollout_percentage
        
        # Check requirements
        requirements = flag.get('requirements', [])
        if requirements:
            for requirement in requirements:
                if not self._check_requirement(requirement):
                    logger.warning(f"⚠️ Feature '{feature_name}' requirement not met: {requirement}")
                    return False
        
        return True
    
    def _check_requirement(self, requirement: str) -> bool:
        """Check if a feature requirement is met"""
        
        if requirement == 'bedrock_available':
            # Check if Bedrock is available (simplified check)
            try:
                import boto3
                from ..consts import get_aws_region
                # Try to create client (doesn't validate credentials)
                boto3.client('bedrock-runtime', region_name=get_aws_region())
                return True
            except Exception:
                return False
        
        elif requirement == 'aws_credentials':
            # Check if AWS credentials are available
            try:
                import boto3
                session = boto3.Session()
                credentials = session.get_credentials()
                return credentials is not None
            except Exception:
                return False
        
        elif requirement == 'bedrock_vision_model':
            # Check if vision model is available
            return self._check_requirement('bedrock_available')
        
        elif requirement == 'ai_analysis':
            # Check if AI analysis feature is enabled
            return self.is_enabled('ai_analysis')
        
        elif requirement == 'enhanced_recommendations':
            # Check if enhanced recommendations feature is enabled
            return self.is_enabled('enhanced_recommendations')
        
        elif requirement == 'business_impact_quantification':
            # Check if business impact quantification feature is enabled
            return self.is_enabled('business_impact_quantification')
        
        elif requirement == 'advanced_visualizations':
            # Check if advanced visualizations feature is enabled
            return self.is_enabled('advanced_visualizations')
        
        else:
            logger.warning(f"⚠️ Unknown requirement: {requirement}")
            return False
    
    def get_feature_status(self, feature_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific feature"""
        
        if feature_name not in self.flags:
            return {'error': f'Unknown feature: {feature_name}'}
        
        flag = self.flags[feature_name]
        requirements_status = {}
        
        for requirement in flag.get('requirements', []):
            requirements_status[requirement] = self._check_requirement(requirement)
        
        return {
            'feature_name': feature_name,
            'enabled': flag['enabled'],
            'description': flag['description'],
            'rollout_percentage': flag['rollout_percentage'],
            'requirements': requirements_status,
            'fallback_enabled': flag.get('fallback_enabled', True),
            'allowed_chat_ids_count': len(flag.get('allowed_chat_ids', [])),
            'blocked_chat_ids_count': len(flag.get('blocked_chat_ids', []))
        }
    
    def get_all_features_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all features"""
        
        status = {}
        for feature_name in self.flags.keys():
            status[feature_name] = self.get_feature_status(feature_name)
        
        return status
    
    def enable_feature(self, feature_name: str, chat_id: Optional[str] = None):
        """Enable a feature globally or for specific chat_id"""
        
        if feature_name not in self.flags:
            logger.error(f"❌ Cannot enable unknown feature: {feature_name}")
            return False
        
        if chat_id:
            # Add to allowed list
            allowed_list = self.flags[feature_name].setdefault('allowed_chat_ids', [])
            if chat_id not in allowed_list:
                allowed_list.append(chat_id)
                logger.info(f"✅ Feature '{feature_name}' enabled for chat_id: {chat_id}")
        else:
            # Enable globally
            self.flags[feature_name]['enabled'] = True
            logger.info(f"✅ Feature '{feature_name}' enabled globally")
        
        return True
    
    def disable_feature(self, feature_name: str, chat_id: Optional[str] = None):
        """Disable a feature globally or for specific chat_id"""
        
        if feature_name not in self.flags:
            logger.error(f"❌ Cannot disable unknown feature: {feature_name}")
            return False
        
        if chat_id:
            # Add to blocked list
            blocked_list = self.flags[feature_name].setdefault('blocked_chat_ids', [])
            if chat_id not in blocked_list:
                blocked_list.append(chat_id)
                logger.info(f"🚫 Feature '{feature_name}' disabled for chat_id: {chat_id}")
        else:
            # Disable globally
            self.flags[feature_name]['enabled'] = False
            logger.info(f"❌ Feature '{feature_name}' disabled globally")
        
        return True
    
    def set_rollout_percentage(self, feature_name: str, percentage: int):
        """Set rollout percentage for a feature"""
        
        if feature_name not in self.flags:
            logger.error(f"❌ Cannot set rollout for unknown feature: {feature_name}")
            return False
        
        if not 0 <= percentage <= 100:
            logger.error(f"❌ Invalid rollout percentage: {percentage}")
            return False
        
        self.flags[feature_name]['rollout_percentage'] = percentage
        logger.info(f"📊 Feature '{feature_name}' rollout set to {percentage}%")
        
        return True
    
    def get_enabled_features(self, chat_id: Optional[str] = None) -> List[str]:
        """Get list of enabled features for a context"""
        
        enabled_features = []
        
        for feature_name in self.flags.keys():
            if self.is_enabled(feature_name, chat_id):
                enabled_features.append(feature_name)
        
        return enabled_features
    
    def should_use_fallback(self, feature_name: str) -> bool:
        """Check if fallback should be used when feature fails"""
        
        if feature_name not in self.flags:
            return True  # Default to fallback for unknown features
        
        return self.flags[feature_name].get('fallback_enabled', True)

# Global feature flags instance
_feature_flags_instance = None

def get_feature_flags() -> WAFRFeatureFlags:
    """Get global feature flags instance (singleton pattern)"""
    global _feature_flags_instance
    
    if _feature_flags_instance is None:
        _feature_flags_instance = WAFRFeatureFlags()
    
    return _feature_flags_instance

def reset_feature_flags():
    """Reset feature flags instance (for testing)"""
    global _feature_flags_instance
    _feature_flags_instance = None