"""
Validation Integration Module - Integrates Evidence Validator and IaC Extractor.

This module provides the integration layer that combines:
1. IaC Evidence Extractor (Phase 3) - Direct parsing of CloudFormation/Terraform
2. Evidence Validator (Phase 2) - Validation of Claude's identifications
3. Claude Analysis - AI-based document understanding

Implements the Universal Validation Framework (UNIV-001 to UNIV-010).
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..core.logger import WAFRLogger
from ..core.evidence_validator import EvidenceValidator, ValidationResult
from ..core.iac_evidence_extractor import IaCEvidenceExtractor, IaCExtractionResult


@dataclass
class EnhancedAnalysisResult:
    """Enhanced analysis result with validation."""
    # Original Claude analysis
    claude_services: List[str]
    claude_patterns: List[str]
    
    # IaC extraction results
    iac_services: List[str]
    iac_extraction: Optional[IaCExtractionResult]
    
    # Validation results
    validated_services: List[str]
    rejected_services: List[str]
    potential_services: List[str]
    
    # Feature detection
    security_features: Dict[str, Any]
    reliability_features: Dict[str, Any]
    sustainability_features: Dict[str, Any]
    
    # Final merged results
    final_services: List[str]
    final_patterns: List[str]
    
    # Metadata
    validation_summary: Dict[str, Any]
    confidence_adjustments: Dict[str, float]


class ValidationIntegration:
    """
    Integrates evidence validation with document analysis.
    
    This class orchestrates the validation pipeline:
    1. Extract services from IaC templates (highest confidence)
    2. Validate Claude's identifications against evidence
    3. Merge results with appropriate confidence levels
    4. Extract detailed security/reliability/sustainability features
    """
    
    def __init__(self):
        """Initialize the validation integration."""
        self.logger = WAFRLogger(__name__)
        self.iac_extractor = IaCEvidenceExtractor()
        self.evidence_validator = EvidenceValidator()
    
    def enhance_analysis(
        self,
        document_text: str,
        claude_services: List[str],
        claude_patterns: List[str]
    ) -> EnhancedAnalysisResult:
        """
        Enhance Claude's analysis with evidence-based validation.
        
        Args:
            document_text: Raw document content
            claude_services: Services identified by Claude
            claude_patterns: Patterns identified by Claude
            
        Returns:
            EnhancedAnalysisResult with validated and merged results
        """
        self.logger.info(f"🔍 Starting validation integration for {len(claude_services)} services")
        
        # Step 1: Extract from IaC (highest confidence)
        iac_result = self.iac_extractor.extract_from_document(document_text)
        iac_services = list(iac_result.services)
        
        self.logger.info(f"📦 IaC extraction: {len(iac_services)} services from {iac_result.iac_type.value}")
        
        # Step 2: Validate Claude's identifications
        validation_result = self.evidence_validator.validate_services(
            claude_services, document_text
        )
        
        self.logger.info(f"✅ Validation: {len(validation_result.validated_services)} validated, "
                        f"{len(validation_result.rejected_services)} rejected")
        
        # Step 3: Merge results (IaC takes precedence)
        final_services, confidence_adjustments = self._merge_services(
            iac_services,
            [s.service_name for s in validation_result.validated_services],
            [s.service_name for s in validation_result.rejected_services],
            [s.service_name for s in validation_result.potential_services]
        )
        
        # Step 4: Validate patterns
        final_patterns = self._validate_patterns(
            claude_patterns,
            iac_result.architecture_patterns,
            final_services
        )
        
        # Step 5: Merge feature detection
        security_features = self._merge_security_features(
            iac_result.security_features,
            validation_result.security_features
        )
        
        reliability_features = self._merge_reliability_features(
            iac_result.reliability_features,
            validation_result.reliability_features
        )
        
        sustainability_features = self._merge_sustainability_features(
            iac_result.sustainability_features,
            validation_result.sustainability_features
        )
        
        # Create validation summary
        validation_summary = {
            'claude_services_count': len(claude_services),
            'iac_services_count': len(iac_services),
            'validated_count': len(validation_result.validated_services),
            'rejected_count': len(validation_result.rejected_services),
            'final_services_count': len(final_services),
            'false_positives_eliminated': len(validation_result.rejected_services),
            'accuracy_improvement': self._calculate_accuracy_improvement(
                claude_services, final_services, validation_result.rejected_services
            )
        }
        
        self.logger.info(f"🎯 Final result: {len(final_services)} services, "
                        f"{len(final_patterns)} patterns")
        
        return EnhancedAnalysisResult(
            claude_services=claude_services,
            claude_patterns=claude_patterns,
            iac_services=iac_services,
            iac_extraction=iac_result,
            validated_services=[s.service_name for s in validation_result.validated_services],
            rejected_services=[s.service_name for s in validation_result.rejected_services],
            potential_services=[s.service_name for s in validation_result.potential_services],
            security_features=security_features,
            reliability_features=reliability_features,
            sustainability_features=sustainability_features,
            final_services=final_services,
            final_patterns=final_patterns,
            validation_summary=validation_summary,
            confidence_adjustments=confidence_adjustments
        )

    def _merge_services(
        self,
        iac_services: List[str],
        validated_services: List[str],
        rejected_services: List[str],
        potential_services: List[str]
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Merge services from different sources with confidence levels.
        
        Priority:
        1. IaC services (95% confidence)
        2. Validated services (85% confidence)
        3. Potential services (60% confidence) - only if not rejected
        
        Returns:
            Tuple of (final_services, confidence_adjustments)
        """
        final_services = set()
        confidence_adjustments = {}
        
        # Add IaC services (highest confidence)
        for service in iac_services:
            final_services.add(service)
            confidence_adjustments[service] = 0.95
        
        # Add validated services not already in IaC
        for service in validated_services:
            if service not in final_services:
                final_services.add(service)
                confidence_adjustments[service] = 0.85
        
        # Potential services only if not rejected and not already present
        for service in potential_services:
            if service not in final_services and service not in rejected_services:
                # Only add if it's not a common false positive
                if service not in ['Lambda', 'API Gateway', 'SNS', 'SQS', 'CDK']:
                    final_services.add(service)
                    confidence_adjustments[service] = 0.60
        
        return list(final_services), confidence_adjustments
    
    def _validate_patterns(
        self,
        claude_patterns: List[str],
        iac_patterns: List[str],
        final_services: List[str]
    ) -> List[str]:
        """
        Validate architecture patterns against evidence.
        
        Implements UNIV-003: Architecture Pattern Validation
        """
        validated_patterns = set()
        
        # IaC patterns are pre-validated
        validated_patterns.update(iac_patterns)
        
        # Validate Claude patterns against service evidence
        for pattern in claude_patterns:
            pattern_lower = pattern.lower()
            
            # Multi-Tier requires presentation + logic + data
            if 'multi-tier' in pattern_lower or 'three-tier' in pattern_lower:
                has_presentation = any(s in final_services for s in ['CloudFront', 'ALB', 'ELB', 'S3'])
                has_logic = any(s in final_services for s in ['EC2', 'ECS', 'Lambda', 'EKS'])
                has_data = any(s in final_services for s in ['RDS', 'DynamoDB', 'ElastiCache'])
                if has_presentation and has_logic and has_data:
                    validated_patterns.add(pattern)
            
            # Microservices requires ECS/EKS or multiple compute services
            elif 'microservice' in pattern_lower:
                if 'ECS' in final_services or 'EKS' in final_services:
                    validated_patterns.add(pattern)
                # Don't add if just EC2 - that's not microservices
            
            # Serverless requires Lambda or Fargate
            elif 'serverless' in pattern_lower:
                if 'Lambda' in final_services:
                    validated_patterns.add(pattern)
            
            # Event-Driven requires event services
            elif 'event-driven' in pattern_lower or 'event driven' in pattern_lower:
                event_services = {'SNS', 'SQS', 'EventBridge', 'Kinesis'}
                if any(s in final_services for s in event_services):
                    validated_patterns.add(pattern)
            
            # Infrastructure as Code - always valid for IaC templates
            elif 'infrastructure as code' in pattern_lower or 'iac' in pattern_lower:
                validated_patterns.add(pattern)
            
            # Multi-AZ - check for Multi-AZ services
            elif 'multi-az' in pattern_lower:
                validated_patterns.add(pattern)  # Usually valid if mentioned
            
            # Auto Scaling
            elif 'auto scaling' in pattern_lower or 'autoscaling' in pattern_lower:
                if 'Auto Scaling' in final_services or 'EC2' in final_services:
                    validated_patterns.add(pattern)
            
            # CDN
            elif 'cdn' in pattern_lower or 'content delivery' in pattern_lower:
                if 'CloudFront' in final_services:
                    validated_patterns.add(pattern)
        
        return list(validated_patterns)
    
    def _merge_security_features(
        self,
        iac_features: Dict[str, Any],
        validation_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge security features from IaC and validation."""
        merged = {}
        
        # Combine all features, preferring True values
        all_keys = set(iac_features.keys()) | set(validation_features.keys())
        for key in all_keys:
            iac_val = iac_features.get(key, False)
            val_val = validation_features.get(key, False)
            
            if isinstance(iac_val, bool) and isinstance(val_val, bool):
                merged[key] = iac_val or val_val
            elif isinstance(iac_val, dict) and isinstance(val_val, dict):
                merged[key] = {**val_val, **iac_val}
            elif isinstance(iac_val, list) and isinstance(val_val, list):
                merged[key] = list(set(iac_val + val_val))
            else:
                merged[key] = iac_val if iac_val else val_val
        
        return merged
    
    def _merge_reliability_features(
        self,
        iac_features: Dict[str, Any],
        validation_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge reliability features from IaC and validation."""
        return self._merge_security_features(iac_features, validation_features)
    
    def _merge_sustainability_features(
        self,
        iac_features: Dict[str, Any],
        validation_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge sustainability features from IaC and validation."""
        return self._merge_security_features(iac_features, validation_features)
    
    def _calculate_accuracy_improvement(
        self,
        original_services: List[str],
        final_services: List[str],
        rejected_services: List[str]
    ) -> str:
        """Calculate accuracy improvement from validation."""
        if not original_services:
            return "N/A"
        
        false_positive_rate = len(rejected_services) / len(original_services) * 100
        return f"{false_positive_rate:.1f}% false positives eliminated"


# Global instance for easy access
validation_integration = ValidationIntegration()
