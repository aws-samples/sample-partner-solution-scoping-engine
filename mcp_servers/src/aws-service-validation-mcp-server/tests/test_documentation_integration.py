#!/usr/bin/env python3
"""Test documentation integration with service validation."""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add the package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'awslabs'))

# Mock the backend module before importing the server
sys.modules['backend'] = MagicMock()
sys.modules['backend.config'] = MagicMock()
sys.modules['backend.config.app_config'] = MagicMock()

# Create a mock AppConfig class
mock_app_config = MagicMock()
mock_app_config.get_aws_region.return_value = 'us-east-1'
sys.modules['backend.config.app_config'].AppConfig = mock_app_config

from aws_service_validation_mcp_server.server import validate_aws_service
from mcp.server.fastmcp import Context

@pytest.mark.asyncio
async def test_valid_service_with_documentation():
    """Test that valid services return documentation links."""
    # Mock context
    ctx = AsyncMock(spec=Context)
    
    # Mock the documentation search to return sample results
    with patch('aws_service_validation_mcp_server.server.search_service_documentation') as mock_search:
        mock_search.return_value = [
            {
                'url': 'https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html',
                'title': 'What is Amazon S3?',
                'context': 'Amazon Simple Storage Service (Amazon S3) is an object storage service...'
            }
        ]
        
        result = await validate_aws_service("s3", ctx)
        
        # Verify the result
        assert result.service == "s3"
        assert result.status == "valid"
        assert result.exists_in_boto3 == True
        assert result.exists_in_available_list == True
        assert result.documentation is not None
        assert "📚 **Documentation for s3:**" in result.documentation
        assert "What is Amazon S3?" in result.documentation
        
        # Verify documentation search was called
        mock_search.assert_called_once_with("s3", limit=2)

@pytest.mark.asyncio
async def test_deprecated_service_with_alternative_documentation():
    """Test that deprecated services return documentation for alternatives."""
    # Mock context
    ctx = AsyncMock(spec=Context)
    
    # Mock the documentation search to return sample results for EVS
    with patch('aws_service_validation_mcp_server.server.search_service_documentation') as mock_search:
        mock_search.return_value = [
            {
                'url': 'https://docs.aws.amazon.com/evs/latest/userguide/what-is.html',
                'title': 'What is Amazon Elastic VMware Service?',
                'context': 'Amazon Elastic VMware Service (Amazon EVS) is a managed service...'
            }
        ]
        
        result = await validate_aws_service("vmc", ctx)
        
        # Verify the result
        assert result.service == "vmc"
        assert result.status == "deprecated"
        assert result.exists_in_boto3 == False
        assert result.exists_in_available_list == False
        assert result.alternatives == ['evs']
        assert "VMware Cloud on AWS (VMC) is deprecated" in result.suggestion
        assert result.documentation is not None
        assert "📚 **Documentation for alternatives to vmc:**" in result.documentation
        assert "What is Amazon Elastic VMware Service?" in result.documentation
        
        # Verify documentation search was called for the alternative
        mock_search.assert_called_once_with("evs", limit=1)

@pytest.mark.asyncio
async def test_documentation_search_failure_handling():
    """Test that documentation search failures are handled gracefully."""
    # Mock context
    ctx = AsyncMock(spec=Context)
    
    # Mock the documentation search to raise an exception
    with patch('aws_service_validation_mcp_server.server.search_service_documentation') as mock_search:
        mock_search.side_effect = Exception("Network error")
        
        result = await validate_aws_service("s3", ctx)
        
        # Verify the result still works without documentation
        assert result.service == "s3"
        assert result.status == "valid"
        assert result.exists_in_boto3 == True
        assert result.exists_in_available_list == True
        assert result.documentation is None  # Should be None due to exception
        
        # Verify documentation search was attempted
        mock_search.assert_called_once_with("s3", limit=2)

@pytest.mark.asyncio
async def test_invalid_service_no_documentation():
    """Test that invalid services don't attempt documentation search."""
    # Mock context
    ctx = AsyncMock(spec=Context)
    
    with patch('aws_service_validation_mcp_server.server.search_service_documentation') as mock_search:
        result = await validate_aws_service("nonexistent-service", ctx)
        
        # Verify the result
        assert result.service == "nonexistent-service"
        assert result.status == "invalid"
        assert result.exists_in_boto3 == False
        assert result.exists_in_available_list == False
        assert result.documentation is None
        
        # Verify documentation search was NOT called for invalid services
        mock_search.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
