"""Health check and connectivity testing for WAFR MCP Server"""

import asyncio
import sys
from typing import Dict, Any, List
from datetime import datetime
import platform

from .logger import setup_logger

logger = setup_logger(__name__)


class HealthChecker:
    """
    Comprehensive health checker for WAFR MCP Server components.
    
    Validates system requirements, dependencies, and connectivity.
    """
    
    def __init__(self):
        self.checks = [
            self._check_python_version,
            self._check_dependencies,
            self._check_mcp_framework,
            self._check_aws_sdk,
            self._check_system_resources,
            self._check_environment_variables
        ]
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status with detailed component information
        """
        logger.info("Starting health check")
        start_time = datetime.utcnow()
        
        health_status = {
            "status": "healthy",
            "timestamp": start_time.isoformat(),
            "server_info": {
                "name": "aws-well-architected-framework-mcp-server",
                "version": "0.2.0",
                "python_version": platform.python_version(),
                "platform": platform.platform()
            },
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        # Run all health checks
        for check in self.checks:
            try:
                check_name = check.__name__.replace("_check_", "")
                logger.debug(f"Running health check: {check_name}")
                
                check_result = await check()
                health_status["checks"][check_name] = check_result
                
                if not check_result["passed"]:
                    health_status["status"] = "unhealthy"
                    health_status["errors"].append({
                        "check": check_name,
                        "message": check_result.get("message", "Check failed")
                    })
                elif check_result.get("warnings"):
                    health_status["warnings"].extend([
                        {"check": check_name, "message": warning}
                        for warning in check_result["warnings"]
                    ])
                
            except Exception as e:
                logger.error(f"Health check {check.__name__} failed: {e}")
                health_status["status"] = "unhealthy"
                health_status["errors"].append({
                    "check": check.__name__.replace("_check_", ""),
                    "message": f"Check failed with exception: {str(e)}"
                })
        
        # Calculate check duration
        end_time = datetime.utcnow()
        health_status["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"Health check completed: {health_status['status']} ({health_status['duration_ms']}ms)")
        return health_status
    
    async def _check_python_version(self) -> Dict[str, Any]:
        """Check Python version compatibility."""
        required_version = (3, 10)
        current_version = sys.version_info[:2]
        
        passed = current_version >= required_version
        
        return {
            "passed": passed,
            "current_version": f"{current_version[0]}.{current_version[1]}",
            "required_version": f"{required_version[0]}.{required_version[1]}",
            "message": "Python version compatible" if passed else f"Python {required_version[0]}.{required_version[1]}+ required"
        }
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check required dependencies."""
        required_packages = {
            "mcp": "mcp",
            "boto3": "boto3", 
            "pydantic": "pydantic",
            "python-docx": "docx"
        }
        
        missing_packages = []
        installed_packages = {}
        
        for package_name, import_name in required_packages.items():
            try:
                module = __import__(import_name)
                version = getattr(module, "__version__", "unknown")
                installed_packages[package_name] = version
            except ImportError:
                missing_packages.append(package_name)
        
        passed = len(missing_packages) == 0
        
        result = {
            "passed": passed,
            "installed_packages": installed_packages,
            "missing_packages": missing_packages
        }
        
        if not passed:
            result["message"] = f"Missing required packages: {', '.join(missing_packages)}"
        else:
            result["message"] = "All required dependencies installed"
        
        return result
    
    async def _check_mcp_framework(self) -> Dict[str, Any]:
        """Check MCP framework functionality."""
        try:
            from mcp.server.fastmcp import FastMCP
            
            # Test basic MCP server creation
            test_server = FastMCP("test-server")
            
            return {
                "passed": True,
                "message": "MCP framework operational",
                "framework_version": getattr(__import__("mcp"), "__version__", "unknown")
            }
        except Exception as e:
            return {
                "passed": False,
                "message": f"MCP framework error: {str(e)}"
            }
    
    async def _check_aws_sdk(self) -> Dict[str, Any]:
        """Check AWS SDK availability and basic functionality."""
        try:
            import boto3
            from ..consts import get_aws_region
            
            # Test basic boto3 functionality
            session = boto3.Session()
            
            # Check if we can create clients (without credentials)
            try:
                # This should work even without credentials
                client = session.client('wellarchitected', region_name=get_aws_region())
                
                return {
                    "passed": True,
                    "message": "AWS SDK operational",
                    "boto3_version": boto3.__version__,
                    "available_services": len(session.get_available_services())
                }
            except Exception as client_error:
                return {
                    "passed": True,
                    "message": "AWS SDK available (credentials not tested)",
                    "boto3_version": boto3.__version__,
                    "warnings": [f"Client creation test failed: {str(client_error)}"]
                }
                
        except ImportError:
            return {
                "passed": False,
                "message": "AWS SDK (boto3) not available"
            }
        except Exception as e:
            return {
                "passed": False,
                "message": f"AWS SDK error: {str(e)}"
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources and performance."""
        try:
            import psutil
            
            # Get system information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_count = psutil.cpu_count()
            
            warnings = []
            
            # Check memory (recommend at least 1GB available)
            if memory.available < 1024 * 1024 * 1024:  # 1GB
                warnings.append(f"Low available memory: {memory.available // (1024*1024)}MB")
            
            # Check disk space (recommend at least 1GB free)
            if disk.free < 1024 * 1024 * 1024:  # 1GB
                warnings.append(f"Low disk space: {disk.free // (1024*1024*1024)}GB")
            
            return {
                "passed": True,
                "message": "System resources checked",
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "cpu_count": cpu_count,
                "warnings": warnings
            }
            
        except ImportError:
            return {
                "passed": True,
                "message": "System resource monitoring not available (psutil not installed)",
                "warnings": ["Install psutil for detailed system monitoring"]
            }
        except Exception as e:
            return {
                "passed": True,
                "message": f"System resource check failed: {str(e)}",
                "warnings": ["Could not check system resources"]
            }
    
    async def _check_environment_variables(self) -> Dict[str, Any]:
        """Check environment variables and configuration."""
        import os
        
        # Optional environment variables
        optional_vars = {
            "AWS_REGION": "Default AWS region",
            "AWS_PROFILE": "AWS profile to use",
            "WAFR_DEBUG": "Debug mode flag",
            "WAFR_LOG_LEVEL": "Logging level"
        }
        
        found_vars = {}
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                found_vars[var] = value
        
        return {
            "passed": True,
            "message": "Environment variables checked",
            "found_variables": found_vars,
            "optional_variables": optional_vars
        }
    
    async def check_connectivity(self) -> Dict[str, Any]:
        """
        Test external connectivity (AWS services, documentation APIs).
        
        Returns:
            Connectivity test results
        """
        logger.info("Testing external connectivity")
        
        connectivity_results = {
            "aws_services": await self._test_aws_connectivity(),
            "documentation_apis": await self._test_documentation_connectivity()
        }
        
        return connectivity_results
    
    async def _test_aws_connectivity(self) -> Dict[str, Any]:
        """Test AWS service connectivity."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            from ..consts import get_aws_region, DEFAULT_REGIONS
            
            # Test basic AWS connectivity (without credentials)
            session = boto3.Session()
            
            # Test different regions - use configured region plus defaults
            configured_region = get_aws_region()
            test_regions = list(set([configured_region] + DEFAULT_REGIONS[:2]))
            region_results = {}
            
            for region in test_regions:
                try:
                    client = session.client('sts', region_name=region)
                    # This will fail with credentials but should connect
                    await asyncio.get_event_loop().run_in_executor(
                        None, client.get_caller_identity
                    )
                    region_results[region] = {"status": "connected", "message": "Authenticated"}
                except NoCredentialsError:
                    region_results[region] = {"status": "connected", "message": "No credentials (expected)"}
                except ClientError as e:
                    if "InvalidUserID.NotFound" in str(e):
                        region_results[region] = {"status": "connected", "message": "Connected but invalid credentials"}
                    else:
                        region_results[region] = {"status": "error", "message": str(e)}
                except Exception as e:
                    region_results[region] = {"status": "error", "message": str(e)}
            
            return {
                "overall_status": "available",
                "regions": region_results
            }
            
        except Exception as e:
            return {
                "overall_status": "error",
                "message": str(e)
            }
    
    async def _test_documentation_connectivity(self) -> Dict[str, Any]:
        """Test AWS documentation API connectivity."""
        try:
            import aiohttp
            
            # Test AWS documentation endpoints
            test_urls = [
                "https://docs.aws.amazon.com",
                "https://aws.amazon.com/architecture/well-architected"
            ]
            
            url_results = {}
            
            async with aiohttp.ClientSession() as session:
                for url in test_urls:
                    try:
                        async with session.get(url, timeout=10) as response:
                            url_results[url] = {
                                "status": "connected",
                                "status_code": response.status,
                                "message": f"HTTP {response.status}"
                            }
                    except Exception as e:
                        url_results[url] = {
                            "status": "error",
                            "message": str(e)
                        }
            
            return {
                "overall_status": "available",
                "endpoints": url_results
            }
            
        except ImportError:
            return {
                "overall_status": "unavailable",
                "message": "aiohttp not available for connectivity testing"
            }
        except Exception as e:
            return {
                "overall_status": "error",
                "message": str(e)
            }