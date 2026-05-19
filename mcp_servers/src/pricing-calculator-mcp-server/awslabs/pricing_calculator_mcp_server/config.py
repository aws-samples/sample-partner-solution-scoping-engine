"""Configuration for the pricing calculator agent"""

import os
from pydantic import BaseModel, Field


class BedrockConfig(BaseModel):
    """Bedrock configuration"""
    model_id: str = Field(
        default="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock model ID to use for parsing"
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock"
    )
    max_tokens: int = Field(
        default=8000,
        description="Maximum tokens for Bedrock response"
    )


class AgentConfig(BaseModel):
    """Agent configuration"""
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create config from environment variables"""
        return cls(
            bedrock=BedrockConfig(
                model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6"),
                region=os.getenv("AWS_REGION", "us-east-1"),
                max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "8000"))
            )
        )