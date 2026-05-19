"""Document processing module for AWS Well-Architected Framework MCP Server.

This module provides comprehensive document processing capabilities including:
- Claude Bedrock integration for multimodal analysis
- Document format validation and processing
- AWS service identification and configuration extraction
- Architectural pattern recognition
- Draw.io/diagrams.net XML decoding
"""

from .bedrock_client import ClaudeBedrockClient, DocumentValidator
from .analysis_engine import DocumentAnalysisEngine
from .service_extractor import ServiceExtractor
from .drawio_decoder import DrawioDecoder

__all__ = [
    "ClaudeBedrockClient",
    "DocumentValidator", 
    "DocumentAnalysisEngine",
    "ServiceExtractor",
    "DrawioDecoder"
]
