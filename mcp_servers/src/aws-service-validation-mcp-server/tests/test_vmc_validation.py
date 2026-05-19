"""Test VMC service validation behavior."""

import pytest
from unittest.mock import AsyncMock, patch
from mcp.server.fastmcp import Context

from awslabs.aws_service_validation_mcp_server.server import validate_aws_service


@pytest.mark.asyncio
async def test_vmc_deprecated_service_validation():
    """Test that VMC service returns deprecated status with EVS alternative and search guidance."""
    
    # Mock context
    ctx = AsyncMock(spec=Context)
    
    # Mock boto3 validation to return False (service doesn't exist in boto3)
    with patch('awslabs.aws_service_validation_mcp_server.server.validate_service_boto3', return_value=False), \
         patch('awslabs.aws_service_validation_mcp_server.server.is_service_available', return_value=False):
        
        # Test case-insensitive "vmc" service
        result = await validate_aws_service("vmc", ctx)
        
        # Assertions
        assert result.service == "vmc"
        assert result.status == "deprecated"
        assert result.exists_in_boto3 is False
        assert result.exists_in_available_list is False
        assert result.alternatives == ['evs']
        assert "VMware Cloud on AWS (VMC) is deprecated" in result.suggestion
        assert "Amazon Elastic VMware Service (EVS)" in result.suggestion
        assert "Search for EVS documentation" in result.suggestion


@pytest.mark.asyncio
async def test_vmc_case_insensitive():
    """Test that VMC validation works regardless of case."""
    
    ctx = AsyncMock(spec=Context)
    
    with patch('awslabs.aws_service_validation_mcp_server.server.validate_service_boto3', return_value=False), \
         patch('awslabs.aws_service_validation_mcp_server.server.is_service_available', return_value=False):
        
        # Test different cases
        test_cases = ["vmc", "VMC", "Vmc", "VmC"]
        
        for service_name in test_cases:
            result = await validate_aws_service(service_name, ctx)
            
            assert result.service == service_name.lower()  # Should be normalized to lowercase
            assert result.status == "deprecated"
            assert result.alternatives == ['evs']
            assert "EVS" in result.suggestion


@pytest.mark.asyncio
async def test_evs_valid_service():
    """Test that EVS (the replacement) is recognized as valid."""
    
    ctx = AsyncMock(spec=Context)
    
    # Mock EVS as valid in boto3
    with patch('awslabs.aws_service_validation_mcp_server.server.validate_service_boto3', return_value=True), \
         patch('awslabs.aws_service_validation_mcp_server.server.is_service_available', return_value=True):
        
        result = await validate_aws_service("evs", ctx)
        
        assert result.service == "evs"
        assert result.status == "valid"
        assert result.exists_in_boto3 is True
        assert result.exists_in_available_list is True
        assert result.alternatives is None
        assert result.suggestion is None
