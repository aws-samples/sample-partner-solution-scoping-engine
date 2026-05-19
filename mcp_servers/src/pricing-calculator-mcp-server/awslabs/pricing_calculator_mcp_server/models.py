"""Data models for the pricing calculator agent"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class AWSService(BaseModel):
    """Generic AWS service configuration"""
    service_name: str = Field(description="AWS service name (e.g., 'Amazon SQS', 'AWS Lambda')")
    service_type: str = Field(description="Service type identifier (e.g., 'sqs', 'lambda', 'ec2')")
    configuration: Dict[str, Any] = Field(description="Service-specific configuration parameters")
    usage_metrics: Dict[str, Any] = Field(description="Usage metrics and quantities")


class PricingRequest(BaseModel):
    """Request to generate pricing calculator link from markdown file"""
    file_path: str = Field(description="Path to the markdown file containing pricing specifications")
    definitions_path: Optional[str] = Field(
        default=None, 
        description="Optional path to AWS service definitions directory"
    )


class PricingResponse(BaseModel):
    """Response containing the calculator link and instructions"""
    calculator_url: str = Field(description="AWS pricing calculator URL")
    nova_act_instructions: str = Field(description="Nova Act instructions for automating the calculator")
    summary: str = Field(description="Summary of all services and configurations")
    parsed_services: List[AWSService] = Field(description="List of parsed AWS services from the file")