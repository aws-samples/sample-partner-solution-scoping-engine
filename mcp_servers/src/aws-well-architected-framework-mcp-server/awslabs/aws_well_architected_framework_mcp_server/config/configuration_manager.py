"""Configuration Manager for WAFR Enterprise Scoring

This module provides centralized configuration management for capability-based scoring.
Follows the same pattern as backend/config/config.json for consistency.

Features:
- Hot-reload capabilities for production tuning
- Configuration validation on load
- Version tracking and rollback support
- JSON-based configuration (following established patterns)
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ConfigVersion:
    """Configuration version information"""
    version: str
    timestamp: datetime
    config_hash: str
    description: str


class ConfigurationValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigurationManager:
    """
    Centralized configuration management for WAFR scoring.
    
    Features:
    - Load JSON configuration files
    - Hot-reload without restart
    - Validation on load
    - Version tracking
    - Rollback support
    
    Follows the pattern from backend/config/config.json
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory. 
                       Defaults to config/ in the same directory as this file.
        """
        if config_dir is None:
            # Default to config/ directory relative to this file
            config_dir = os.path.join(os.path.dirname(__file__))
        
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Any] = {}
        self.version: Optional[ConfigVersion] = None
        self.logger = logging.getLogger(__name__)
        
        # Configuration file paths
        self.capability_files = {
            'security': self.config_dir / 'capabilities' / 'security_capabilities.json',
            'reliability': self.config_dir / 'capabilities' / 'reliability_capabilities.json',
            'performance': self.config_dir / 'capabilities' / 'performance_capabilities.json',
            'cost': self.config_dir / 'capabilities' / 'cost_capabilities.json',
            'operational': self.config_dir / 'capabilities' / 'operational_capabilities.json',
            'sustainability': self.config_dir / 'capabilities' / 'sustainability_capabilities.json'
        }
        
        self.pattern_file = self.config_dir / 'patterns' / 'architecture_patterns.json'
        self.scoring_file = self.config_dir / 'scoring' / 'scoring_parameters.json'
        
        # Load all configurations
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Load all configuration files"""
        try:
            self.logger.info("Loading WAFR scoring configurations...")
            
            # Load capability configurations
            self.configs['capabilities'] = self._load_capability_configs()
            
            # Load pattern configurations
            self.configs['patterns'] = self._load_pattern_configs()
            
            # Load scoring parameters
            self.configs['scoring'] = self._load_scoring_config()
            
            # Validate all configurations
            self._validate_configs()
            
            # Set version
            self.version = self._get_config_version()
            
            self.logger.info(f"✅ Configuration loaded successfully: v{self.version.version}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load configurations: {e}")
            raise ConfigurationValidationError(f"Configuration loading failed: {e}")
    
    def _load_capability_configs(self) -> Dict[str, Any]:
        """Load all capability configuration files"""
        capabilities = {}
        
        for pillar, file_path in self.capability_files.items():
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        capabilities[pillar] = json.load(f)
                    self.logger.debug(f"Loaded {pillar} capabilities from {file_path}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON in {file_path}: {e}")
                    raise ConfigurationValidationError(f"Invalid JSON in {file_path}: {e}")
            else:
                self.logger.warning(f"Capability file not found: {file_path}")
                capabilities[pillar] = {}
        
        return capabilities
    
    def _load_pattern_configs(self) -> Dict[str, Any]:
        """Load architecture pattern configurations"""
        if self.pattern_file.exists():
            try:
                with open(self.pattern_file, 'r') as f:
                    patterns = json.load(f)
                self.logger.debug(f"Loaded {len(patterns)} architecture patterns")
                return patterns
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in {self.pattern_file}: {e}")
                raise ConfigurationValidationError(f"Invalid JSON in {self.pattern_file}: {e}")
        else:
            self.logger.warning(f"Pattern file not found: {self.pattern_file}")
            return {}
    
    def _load_scoring_config(self) -> Dict[str, Any]:
        """Load scoring parameters configuration"""
        if self.scoring_file.exists():
            try:
                with open(self.scoring_file, 'r') as f:
                    scoring = json.load(f)
                self.logger.debug("Loaded scoring parameters")
                return scoring
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in {self.scoring_file}: {e}")
                raise ConfigurationValidationError(f"Invalid JSON in {self.scoring_file}: {e}")
        else:
            self.logger.warning(f"Scoring file not found: {self.scoring_file}")
            return self._get_default_scoring_config()
    
    def _get_default_scoring_config(self) -> Dict[str, Any]:
        """Return default scoring configuration as fallback"""
        return {
            "baseline_scores": {
                "security": 35,
                "reliability": 40,
                "performance": 40,
                "cost_optimization": 35,
                "operational_excellence": 40,
                "sustainability": 30
            },
            "complexity_adjustments": {
                "high_complexity": {"adjustment": -5, "threshold": 20},
                "medium_complexity": {"adjustment": -2, "threshold": 10},
                "low_complexity": {"adjustment": 3, "threshold": 5}
            },
            "score_caps": {"maximum": 95, "minimum": 0},
            "confidence_thresholds": {"high": 0.8, "medium": 0.6, "low": 0.4}
        }
    
    def _validate_configs(self) -> None:
        """
        Validate all loaded configurations.
        
        Checks:
        - All required fields present
        - Weights sum to reasonable values
        - No duplicate capability names
        - Pattern definitions are complete
        """
        self.logger.debug("Validating configurations...")
        
        # Validate capability configurations
        for pillar, capabilities in self.configs.get('capabilities', {}).items():
            self._validate_capability_config(pillar, capabilities)
        
        # Validate pattern configurations
        patterns = self.configs.get('patterns', {})
        self._validate_pattern_config(patterns)
        
        # Validate scoring parameters
        scoring = self.configs.get('scoring', {})
        self._validate_scoring_config(scoring)
        
        self.logger.debug("✅ Configuration validation passed")
    
    def _validate_capability_config(self, pillar: str, capabilities: Dict[str, Any]) -> None:
        """Validate capability configuration for a pillar"""
        if not capabilities:
            self.logger.warning(f"No capabilities defined for {pillar} pillar")
            return
        
        total_weight = 0.0
        for cap_name, cap_config in capabilities.items():
            # Check required fields
            if 'weight' not in cap_config:
                raise ConfigurationValidationError(
                    f"Missing 'weight' in {pillar}.{cap_name}"
                )
            if 'services' not in cap_config:
                raise ConfigurationValidationError(
                    f"Missing 'services' in {pillar}.{cap_name}"
                )
            
            total_weight += cap_config['weight']
        
        # Warn if weights don't sum to ~1.0
        if abs(total_weight - 1.0) > 0.1:
            self.logger.warning(
                f"{pillar} capability weights sum to {total_weight:.2f}, expected ~1.0"
            )
    
    def _validate_pattern_config(self, patterns: Dict[str, Any]) -> None:
        """Validate pattern configurations"""
        if not patterns:
            self.logger.warning("No architecture patterns defined")
            return
        
        for pattern_name, pattern_config in patterns.items():
            # Check required fields
            required_fields = ['description', 'indicator_services']
            for field in required_fields:
                if field not in pattern_config:
                    raise ConfigurationValidationError(
                        f"Missing '{field}' in pattern {pattern_name}"
                    )
    
    def _validate_scoring_config(self, scoring: Dict[str, Any]) -> None:
        """Validate scoring parameters"""
        if not scoring:
            self.logger.warning("Using default scoring configuration")
            return
        
        # Check required fields
        required_fields = ['baseline_scores', 'score_caps']
        for field in required_fields:
            if field not in scoring:
                raise ConfigurationValidationError(
                    f"Missing '{field}' in scoring configuration"
                )
        
        # Validate baseline scores
        baseline = scoring.get('baseline_scores', {})
        expected_pillars = ['security', 'reliability', 'performance', 
                          'cost_optimization', 'operational_excellence', 'sustainability']
        for pillar in expected_pillars:
            if pillar not in baseline:
                self.logger.warning(f"Missing baseline score for {pillar}")
    
    def _get_config_version(self) -> ConfigVersion:
        """Generate configuration version information"""
        import hashlib
        
        # Create hash of all configurations
        config_str = json.dumps(self.configs, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
        
        return ConfigVersion(
            version=f"1.0.{config_hash}",
            timestamp=datetime.utcnow(),
            config_hash=config_hash,
            description="WAFR Enterprise Scoring Configuration"
        )
    
    def hot_reload(self) -> bool:
        """
        Reload configurations without restart.
        
        Use case: Tune scoring weights in production
        
        Returns:
            True if reload successful, False otherwise
        """
        try:
            self.logger.info("🔄 Hot-reloading configurations...")
            
            # Store current configs as backup
            backup_configs = self.configs.copy()
            backup_version = self.version
            
            # Attempt to load new configs
            self._load_all_configs()
            
            self.logger.info(f"✅ Configuration reloaded successfully: v{self.version.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration reload failed: {e}")
            
            # Restore backup
            self.configs = backup_configs
            self.version = backup_version
            self.logger.info("Restored previous configuration")
            
            return False
    
    def get_capability_definition(self, pillar: str, capability_name: str) -> Optional[Dict[str, Any]]:
        """
        Get capability definition from configuration.
        
        Args:
            pillar: Pillar name (security, reliability, etc.)
            capability_name: Capability name (encryption, redundancy, etc.)
            
        Returns:
            Capability definition dict or None if not found
        """
        capabilities = self.configs.get('capabilities', {}).get(pillar, {})
        return capabilities.get(capability_name)
    
    def get_all_capabilities_for_pillar(self, pillar: str) -> Dict[str, Any]:
        """Get all capability definitions for a pillar"""
        return self.configs.get('capabilities', {}).get(pillar, {})
    
    def get_pattern_definition(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Get pattern definition from configuration"""
        return self.configs.get('patterns', {}).get(pattern_name)
    
    def get_all_patterns(self) -> Dict[str, Any]:
        """Get all pattern definitions"""
        return self.configs.get('patterns', {})
    
    def get_baseline_scores(self) -> Dict[str, float]:
        """Get baseline scores for all pillars"""
        return self.configs.get('scoring', {}).get('baseline_scores', {})
    
    def get_complexity_adjustments(self) -> Dict[str, Any]:
        """Get complexity adjustment parameters"""
        return self.configs.get('scoring', {}).get('complexity_adjustments', {})
    
    def get_score_caps(self) -> Dict[str, float]:
        """Get score cap parameters (maximum, minimum)"""
        return self.configs.get('scoring', {}).get('score_caps', {'maximum': 95, 'minimum': 0})
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Get confidence threshold parameters"""
        return self.configs.get('scoring', {}).get('confidence_thresholds', {})
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information for debugging"""
        return {
            'version': self.version.version if self.version else 'unknown',
            'timestamp': self.version.timestamp.isoformat() if self.version else None,
            'config_hash': self.version.config_hash if self.version else None,
            'capabilities_loaded': {
                pillar: len(caps) for pillar, caps in self.configs.get('capabilities', {}).items()
            },
            'patterns_loaded': len(self.configs.get('patterns', {})),
            'scoring_config_loaded': bool(self.configs.get('scoring'))
        }


# Singleton instance for global access
_config_manager_instance: Optional[ConfigurationManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigurationManager:
    """
    Get singleton ConfigurationManager instance.
    
    Args:
        config_dir: Optional config directory path (only used on first call)
        
    Returns:
        ConfigurationManager instance
    """
    global _config_manager_instance
    
    if _config_manager_instance is None:
        _config_manager_instance = ConfigurationManager(config_dir)
    
    return _config_manager_instance


def reload_config() -> bool:
    """
    Hot-reload configuration.
    
    Returns:
        True if reload successful, False otherwise
    """
    config_manager = get_config_manager()
    return config_manager.hot_reload()
