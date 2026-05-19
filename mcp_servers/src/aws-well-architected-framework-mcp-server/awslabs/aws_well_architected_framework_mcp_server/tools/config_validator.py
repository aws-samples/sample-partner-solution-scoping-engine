#!/usr/bin/env python3
"""
Configuration Validation Tool

Validates WAFR Enterprise Scoring configuration files for correctness,
completeness, and best practices.

Requirements: 9.1, 9.2, 9.4
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    level: ValidationLevel
    category: str
    message: str
    file_path: str
    details: Dict[str, Any] = None


class ConfigValidator:
    """Validates configuration files"""
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.results: List[ValidationResult] = []
    
    def validate_directory(self, config_dir: Path) -> bool:
        """Validate all configuration files in directory"""
        print(f"Validating configuration directory: {config_dir}")
        print("=" * 60)
        
        # Validate capabilities
        capabilities_dir = config_dir / "capabilities"
        if capabilities_dir.exists():
            self._validate_capabilities(capabilities_dir)
        else:
            self._add_result(ValidationLevel.ERROR, "structure", 
                           "Capabilities directory not found", str(config_dir))
        
        # Validate patterns
        patterns_dir = config_dir / "patterns"
        if patterns_dir.exists():
            self._validate_patterns(patterns_dir)
        else:
            self._add_result(ValidationLevel.ERROR, "structure",
                           "Patterns directory not found", str(config_dir))
        
        # Validate scoring parameters
        scoring_dir = config_dir / "scoring"
        if scoring_dir.exists():
            self._validate_scoring_parameters(scoring_dir)
        else:
            self._add_result(ValidationLevel.ERROR, "structure",
                           "Scoring directory not found", str(config_dir))
        
        # Print results
        self._print_results()
        
        # Return success if no errors (or only warnings in non-strict mode)
        has_errors = any(r.level == ValidationLevel.ERROR for r in self.results)
        has_warnings = any(r.level == ValidationLevel.WARNING for r in self.results)
        
        if self.strict:
            return not (has_errors or has_warnings)
        return not has_errors
    
    def _validate_capabilities(self, capabilities_dir: Path):
        """Validate capability configuration files"""
        print("\nValidating Capabilities...")
        
        expected_files = [
            "security_capabilities.json",
            "reliability_capabilities.json",
            "performance_capabilities.json",
            "cost_capabilities.json",
            "operational_capabilities.json",
            "sustainability_capabilities.json"
        ]
        
        for filename in expected_files:
            file_path = capabilities_dir / filename
            if not file_path.exists():
                self._add_result(ValidationLevel.ERROR, "capabilities",
                               f"Missing capability file: {filename}", str(file_path))
                continue
            
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                
                self._validate_capability_structure(config, file_path)
                self._validate_capability_weights(config, file_path)
                self._validate_capability_services(config, file_path)
                
            except json.JSONDecodeError as e:
                self._add_result(ValidationLevel.ERROR, "json",
                               f"Invalid JSON: {e}", str(file_path))
            except Exception as e:
                self._add_result(ValidationLevel.ERROR, "validation",
                               f"Validation error: {e}", str(file_path))
    
    def _validate_capability_structure(self, config: Dict, file_path: Path):
        """Validate capability configuration structure"""
        # Check required fields
        required_fields = ["pillar", "capabilities"]
        for field in required_fields:
            if field not in config:
                self._add_result(ValidationLevel.ERROR, "structure",
                               f"Missing required field: {field}", str(file_path))
        
        # Check pillar value
        valid_pillars = ["security", "reliability", "performance", 
                        "cost_optimization", "operational_excellence", "sustainability"]
        if config.get("pillar") not in valid_pillars:
            self._add_result(ValidationLevel.ERROR, "structure",
                           f"Invalid pillar: {config.get('pillar')}", str(file_path))
    
    def _validate_capability_weights(self, config: Dict, file_path: Path):
        """Validate capability weights sum to approximately 1.0"""
        capabilities = config.get("capabilities", {})
        
        if not capabilities:
            self._add_result(ValidationLevel.ERROR, "capabilities",
                           "No capabilities defined", str(file_path))
            return
        
        total_weight = sum(cap.get("weight", 0) for cap in capabilities.values())
        
        if abs(total_weight - 1.0) > 0.15:
            self._add_result(ValidationLevel.WARNING, "weights",
                           f"Capability weights sum to {total_weight:.2f} (should be ~1.0)",
                           str(file_path))
        elif abs(total_weight - 1.0) > 0.05:
            self._add_result(ValidationLevel.INFO, "weights",
                           f"Capability weights sum to {total_weight:.2f}",
                           str(file_path))
    
    def _validate_capability_services(self, config: Dict, file_path: Path):
        """Validate service definitions in capabilities"""
        capabilities = config.get("capabilities", {})
        
        for cap_name, cap_config in capabilities.items():
            # Check required capability fields
            if "weight" not in cap_config:
                self._add_result(ValidationLevel.ERROR, "capabilities",
                               f"Capability {cap_name} missing weight", str(file_path))
            
            if "services" not in cap_config:
                self._add_result(ValidationLevel.ERROR, "capabilities",
                               f"Capability {cap_name} missing services", str(file_path))
                continue
            
            # Validate services
            services = cap_config["services"]
            if not services:
                self._add_result(ValidationLevel.WARNING, "capabilities",
                               f"Capability {cap_name} has no services", str(file_path))
                continue
            
            # Check coverage factors sum
            total_coverage = sum(svc.get("coverage_factor", 0) for svc in services.values())
            if abs(total_coverage - 1.0) > 0.15:
                self._add_result(ValidationLevel.WARNING, "coverage",
                               f"Capability {cap_name} coverage factors sum to {total_coverage:.2f}",
                               str(file_path))
            
            # Validate each service
            for svc_name, svc_config in services.items():
                if "detection_patterns" not in svc_config:
                    self._add_result(ValidationLevel.ERROR, "services",
                                   f"Service {svc_name} missing detection_patterns", str(file_path))
                elif not svc_config["detection_patterns"]:
                    self._add_result(ValidationLevel.WARNING, "services",
                                   f"Service {svc_name} has empty detection_patterns", str(file_path))
    
    def _validate_patterns(self, patterns_dir: Path):
        """Validate pattern configuration files"""
        print("\nValidating Patterns...")
        
        pattern_file = patterns_dir / "architecture_patterns.json"
        if not pattern_file.exists():
            self._add_result(ValidationLevel.ERROR, "patterns",
                           "Missing architecture_patterns.json", str(pattern_file))
            return
        
        try:
            with open(pattern_file, 'r') as f:
                config = json.load(f)
            
            self._validate_pattern_structure(config, pattern_file)
            
        except json.JSONDecodeError as e:
            self._add_result(ValidationLevel.ERROR, "json",
                           f"Invalid JSON: {e}", str(pattern_file))
        except Exception as e:
            self._add_result(ValidationLevel.ERROR, "validation",
                           f"Validation error: {e}", str(pattern_file))
    
    def _validate_pattern_structure(self, config: Dict, file_path: Path):
        """Validate pattern configuration structure"""
        patterns = config.get("patterns", {})
        
        if not patterns:
            self._add_result(ValidationLevel.ERROR, "patterns",
                           "No patterns defined", str(file_path))
            return
        
        for pattern_name, pattern_config in patterns.items():
            # Check required fields
            required_fields = ["indicator_services", "confidence_threshold"]
            for field in required_fields:
                if field not in pattern_config:
                    self._add_result(ValidationLevel.ERROR, "patterns",
                                   f"Pattern {pattern_name} missing {field}", str(file_path))
            
            # Validate indicator services
            indicators = pattern_config.get("indicator_services", [])
            if len(indicators) < 2:
                self._add_result(ValidationLevel.WARNING, "patterns",
                               f"Pattern {pattern_name} has <2 indicator services", str(file_path))
            
            # Validate confidence threshold
            threshold = pattern_config.get("confidence_threshold", 0)
            if not (0.0 <= threshold <= 1.0):
                self._add_result(ValidationLevel.ERROR, "patterns",
                               f"Pattern {pattern_name} invalid confidence threshold: {threshold}",
                               str(file_path))
    
    def _validate_scoring_parameters(self, scoring_dir: Path):
        """Validate scoring parameters configuration"""
        print("\nValidating Scoring Parameters...")
        
        scoring_file = scoring_dir / "scoring_parameters.json"
        if not scoring_file.exists():
            self._add_result(ValidationLevel.ERROR, "scoring",
                           "Missing scoring_parameters.json", str(scoring_file))
            return
        
        try:
            with open(scoring_file, 'r') as f:
                config = json.load(f)
            
            self._validate_scoring_structure(config, scoring_file)
            
        except json.JSONDecodeError as e:
            self._add_result(ValidationLevel.ERROR, "json",
                           f"Invalid JSON: {e}", str(scoring_file))
        except Exception as e:
            self._add_result(ValidationLevel.ERROR, "validation",
                           f"Validation error: {e}", str(scoring_file))
    
    def _validate_scoring_structure(self, config: Dict, file_path: Path):
        """Validate scoring parameters structure"""
        # Check baseline scores
        baseline_scores = config.get("baseline_scores", {})
        required_pillars = ["security", "reliability", "performance",
                          "cost_optimization", "operational_excellence", "sustainability"]
        
        for pillar in required_pillars:
            if pillar not in baseline_scores:
                self._add_result(ValidationLevel.ERROR, "scoring",
                               f"Missing baseline score for {pillar}", str(file_path))
            else:
                score = baseline_scores[pillar]
                if not (0 <= score <= 100):
                    self._add_result(ValidationLevel.ERROR, "scoring",
                                   f"Invalid baseline score for {pillar}: {score}", str(file_path))
        
        # Check score caps
        score_caps = config.get("score_caps", {})
        if "maximum_score" not in score_caps:
            self._add_result(ValidationLevel.ERROR, "scoring",
                           "Missing maximum_score", str(file_path))
        elif score_caps["maximum_score"] > 100:
            self._add_result(ValidationLevel.WARNING, "scoring",
                           f"Maximum score > 100: {score_caps['maximum_score']}", str(file_path))
    
    def _add_result(self, level: ValidationLevel, category: str, 
                   message: str, file_path: str, details: Dict = None):
        """Add validation result"""
        result = ValidationResult(
            level=level,
            category=category,
            message=message,
            file_path=file_path,
            details=details
        )
        self.results.append(result)
    
    def _print_results(self):
        """Print validation results"""
        print("\n" + "=" * 60)
        print("Validation Results")
        print("=" * 60)
        
        # Group by level
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in self.results if r.level == ValidationLevel.WARNING]
        infos = [r for r in self.results if r.level == ValidationLevel.INFO]
        
        # Print errors
        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for result in errors:
                print(f"  [{result.category}] {result.message}")
                print(f"    File: {result.file_path}")
        
        # Print warnings
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for result in warnings:
                print(f"  [{result.category}] {result.message}")
                print(f"    File: {result.file_path}")
        
        # Print infos
        if infos and self.strict:
            print(f"\nℹ️  Info ({len(infos)}):")
            for result in infos:
                print(f"  [{result.category}] {result.message}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")
        
        if not errors and not warnings:
            print("✅ All validations passed!")
        elif not errors:
            print("✅ No errors found (warnings present)")
        else:
            print("❌ Validation failed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate WAFR Enterprise Scoring configuration files"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Configuration directory path (default: config)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if not args.config_dir.exists():
        print(f"Error: Configuration directory not found: {args.config_dir}")
        sys.exit(1)
    
    validator = ConfigValidator(strict=args.strict)
    success = validator.validate_directory(args.config_dir)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
