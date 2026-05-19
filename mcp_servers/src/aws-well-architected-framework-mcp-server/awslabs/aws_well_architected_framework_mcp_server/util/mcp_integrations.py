# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration utilities for communicating with other MCP servers."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
from mcp.server.fastmcp import Context


class MCPServerType(Enum):
    """Types of MCP servers we integrate with."""
    COST_ANALYSIS = "cost-analysis-mcp-server"
    DIAGRAM_ANALYSIS = "aws-diagram-mcp-server"
    ARCHITECTURE_REVIEW = "architecture-review-mcp-server"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    server_type: MCPServerType
    base_url: str
    timeout: int = 30
    retry_attempts: int = 3
    api_key: Optional[str] = None


@dataclass
class CostAnalysisData:
    """Cost analysis data from cost-analysis-mcp-server."""
    solution_id: str
    total_monthly_cost: float
    cost_breakdown_by_service: Dict[str, float]
    cost_optimization_opportunities: List[Dict[str, Any]]
    right_sizing_recommendations: List[Dict[str, Any]]
    reserved_instance_recommendations: List[Dict[str, Any]]
    savings_plan_recommendations: List[Dict[str, Any]]
    sustainability_cost_impact: Dict[str, Any]
    cost_alerts: List[Dict[str, Any]]


@dataclass
class DiagramAnalysisData:
    """Architecture diagram analysis data from aws-diagram-mcp-server."""
    solution_id: str
    diagram_path: str
    identified_services: List[Dict[str, Any]]
    service_relationships: List[Dict[str, Any]]
    data_flows: List[Dict[str, Any]]
    security_boundaries: List[Dict[str, Any]]
    network_topology: Dict[str, Any]
    compliance_indicators: List[str]
    architecture_patterns: List[str]
    potential_issues: List[Dict[str, Any]]


class MCPIntegrationClient:
    """Client for integrating with other MCP servers."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.servers: Dict[str, MCPServerConfig] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server for integration."""
        self.servers[config.name] = config
        self.logger.info(f"Registered MCP server: {config.name} ({config.server_type.value})")

    async def get_cost_analysis(
        self,
        solution_id: str,
        solution_text: str,
        aws_services: List[str],
        ctx: Optional[Context] = None
    ) -> Optional[CostAnalysisData]:
        """
        Get cost analysis from cost-analysis-mcp-server.

        Args:
            solution_id: Unique identifier for the solution
            solution_text: Description of the solution
            aws_services: List of AWS services in the solution
            ctx: MCP context for logging

        Returns:
            CostAnalysisData if successful, None otherwise
        """
        server_config = self._get_server_config(MCPServerType.COST_ANALYSIS)
        if not server_config:
            if ctx:
                await ctx.warning("Cost analysis server not configured")
            return None

        try:
            if ctx:
                await ctx.info(f"Requesting cost analysis for solution {solution_id}")

            # Prepare request payload
            payload = {
                "solution_id": solution_id,
                "solution_text": solution_text,
                "aws_services": aws_services,
                "analysis_type": "comprehensive",
                "include_optimization": True,
                "include_sustainability": True
            }

            # Make request to cost analysis server
            response = await self._make_request(
                server_config,
                "POST",
                "/analyze-cost",
                payload,
                ctx
            )

            if response:
                return self._parse_cost_analysis_response(response, solution_id)

        except Exception as e:
            if ctx:
                await ctx.error(f"Error getting cost analysis: {e}")
            self.logger.error(f"Cost analysis request failed: {e}")

        return None

    async def get_diagram_analysis(
        self,
        solution_id: str,
        diagram_path: str,
        solution_context: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> Optional[DiagramAnalysisData]:
        """
        Get architecture diagram analysis from aws-diagram-mcp-server.

        Args:
            solution_id: Unique identifier for the solution
            diagram_path: Path to the architecture diagram (PNG)
            solution_context: Additional context about the solution
            ctx: MCP context for logging

        Returns:
            DiagramAnalysisData if successful, None otherwise
        """
        server_config = self._get_server_config(MCPServerType.DIAGRAM_ANALYSIS)
        if not server_config:
            if ctx:
                await ctx.warning("Diagram analysis server not configured")
            return None

        try:
            if ctx:
                await ctx.info(f"Requesting diagram analysis for solution {solution_id}")

            # Prepare request payload
            payload = {
                "solution_id": solution_id,
                "diagram_path": diagram_path,
                "solution_context": solution_context,
                "analysis_depth": "comprehensive",
                "extract_services": True,
                "extract_relationships": True,
                "identify_patterns": True
            }

            # Make request to diagram analysis server
            response = await self._make_request(
                server_config,
                "POST",
                "/analyze-diagram",
                payload,
                ctx
            )

            if response:
                return self._parse_diagram_analysis_response(response, solution_id, diagram_path)

        except Exception as e:
            if ctx:
                await ctx.error(f"Error getting diagram analysis: {e}")
            self.logger.error(f"Diagram analysis request failed: {e}")

        return None

    async def validate_solution_with_external_tools(
        self,
        solution_id: str,
        solution_text: str,
        diagram_path: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Validate solution using multiple external MCP servers.

        Args:
            solution_id: Unique identifier for the solution
            solution_text: Description of the solution
            diagram_path: Optional path to architecture diagram
            ctx: MCP context for logging

        Returns:
            Dictionary with validation results from all servers
        """
        results = {
            "solution_id": solution_id,
            "cost_analysis": None,
            "diagram_analysis": None,
            "validation_timestamp": asyncio.get_event_loop().time(),
            "integration_status": {}
        }

        # Extract AWS services from solution text for cost analysis
        aws_services = self._extract_aws_services_from_text(solution_text)

        # Run integrations in parallel
        tasks = []

        # Cost analysis task
        if self._get_server_config(MCPServerType.COST_ANALYSIS):
            tasks.append(
                self._run_cost_analysis_task(solution_id, solution_text, aws_services, ctx)
            )

        # Diagram analysis task (if diagram provided)
        if diagram_path and self._get_server_config(MCPServerType.DIAGRAM_ANALYSIS):
            tasks.append(
                self._run_diagram_analysis_task(solution_id, diagram_path, solution_text, ctx)
            )

        # Execute tasks
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Integration task {i} failed: {result}")
                    continue

                if isinstance(result, CostAnalysisData):
                    results["cost_analysis"] = result
                    results["integration_status"]["cost_analysis"] = "success"
                elif isinstance(result, DiagramAnalysisData):
                    results["diagram_analysis"] = result
                    results["integration_status"]["diagram_analysis"] = "success"

        return results

    async def _run_cost_analysis_task(
        self,
        solution_id: str,
        solution_text: str,
        aws_services: List[str],
        ctx: Optional[Context]
    ) -> Optional[CostAnalysisData]:
        """Run cost analysis task."""
        try:
            return await self.get_cost_analysis(solution_id, solution_text, aws_services, ctx)
        except Exception as e:
            if ctx:
                await ctx.error(f"Cost analysis task failed: {e}")
            return None

    async def _run_diagram_analysis_task(
        self,
        solution_id: str,
        diagram_path: str,
        solution_context: str,
        ctx: Optional[Context]
    ) -> Optional[DiagramAnalysisData]:
        """Run diagram analysis task."""
        try:
            return await self.get_diagram_analysis(solution_id, diagram_path, solution_context, ctx)
        except Exception as e:
            if ctx:
                await ctx.error(f"Diagram analysis task failed: {e}")
            return None

    def _get_server_config(self, server_type: MCPServerType) -> Optional[MCPServerConfig]:
        """Get server configuration by type."""
        for config in self.servers.values():
            if config.server_type == server_type:
                return config
        return None

    async def _make_request(
        self,
        server_config: MCPServerConfig,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
        ctx: Optional[Context] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to MCP server with retry logic."""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized. Use async context manager.")

        url = f"{server_config.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if server_config.api_key:
            headers["Authorization"] = f"Bearer {server_config.api_key}"

        for attempt in range(server_config.retry_attempts):
            try:
                if method.upper() == "POST":
                    response = await self._http_client.post(url, json=payload, headers=headers)
                elif method.upper() == "GET":
                    response = await self._http_client.get(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if ctx:
                    await ctx.warning(
                        f"HTTP error {e.response.status_code} for {server_config.name} (attempt {attempt + 1})"
                    )

                if attempt == server_config.retry_attempts - 1:
                    raise

                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                if ctx:
                    await ctx.error(f"Request failed for {server_config.name}: {e}")

                if attempt == server_config.retry_attempts - 1:
                    raise

                await asyncio.sleep(2 ** attempt)

        return None

    def _parse_cost_analysis_response(
        self,
        response: Dict[str, Any],
        solution_id: str
    ) -> CostAnalysisData:
        """Parse cost analysis response into structured data."""
        return CostAnalysisData(
            solution_id=solution_id,
            total_monthly_cost=response.get("total_monthly_cost", 0.0),
            cost_breakdown_by_service=response.get("cost_breakdown_by_service", {}),
            cost_optimization_opportunities=response.get("optimization_opportunities", []),
            right_sizing_recommendations=response.get("right_sizing_recommendations", []),
            reserved_instance_recommendations=response.get("reserved_instance_recommendations", []),
            savings_plan_recommendations=response.get("savings_plan_recommendations", []),
            sustainability_cost_impact=response.get("sustainability_cost_impact", {}),
            cost_alerts=response.get("cost_alerts", [])
        )

    def _parse_diagram_analysis_response(
        self,
        response: Dict[str, Any],
        solution_id: str,
        diagram_path: str
    ) -> DiagramAnalysisData:
        """Parse diagram analysis response into structured data."""
        return DiagramAnalysisData(
            solution_id=solution_id,
            diagram_path=diagram_path,
            identified_services=response.get("identified_services", []),
            service_relationships=response.get("service_relationships", []),
            data_flows=response.get("data_flows", []),
            security_boundaries=response.get("security_boundaries", []),
            network_topology=response.get("network_topology", {}),
            compliance_indicators=response.get("compliance_indicators", []),
            architecture_patterns=response.get("architecture_patterns", []),
            potential_issues=response.get("potential_issues", [])
        )

    def _extract_aws_services_from_text(self, text: str) -> List[str]:
        """Extract AWS service names from solution text."""
        # This is a simplified implementation
        # In practice, you'd use the solution_parser module
        aws_services = []
        text_lower = text.lower()

        # Common AWS service keywords
        service_keywords = {
            "ec2": ["ec2", "elastic compute", "instance"],
            "s3": ["s3", "bucket", "object storage"],
            "rds": ["rds", "relational database"],
            "lambda": ["lambda", "serverless", "function"],
            "dynamodb": ["dynamodb", "nosql"],
            "vpc": ["vpc", "virtual private cloud"],
            "iam": ["iam", "identity", "access management"],
            "cloudwatch": ["cloudwatch", "monitoring"],
            "cloudfront": ["cloudfront", "cdn"],
            "api-gateway": ["api gateway", "rest api"],
            "ecs": ["ecs", "container service"],
            "eks": ["eks", "kubernetes"],
            "sns": ["sns", "notification service"],
            "sqs": ["sqs", "queue service"],
            "kinesis": ["kinesis", "streaming"]
        }

        for service, keywords in service_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                aws_services.append(service)

        return aws_services


class MCPIntegrationManager:
    """Manager for all MCP server integrations."""

    def __init__(self):
        self.client = MCPIntegrationClient()
        self._configured = False

    async def setup_integrations(
        self,
        cost_server_url: Optional[str] = None,
        diagram_server_url: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> None:
        """
        Set up integrations with external MCP servers.

        Args:
            cost_server_url: URL for cost-analysis-mcp-server
            diagram_server_url: URL for aws-diagram-mcp-server
            ctx: MCP context for logging
        """
        if cost_server_url:
            cost_config = MCPServerConfig(
                name="cost-analysis",
                server_type=MCPServerType.COST_ANALYSIS,
                base_url=cost_server_url,
                timeout=60,  # Cost analysis might take longer
                retry_attempts=3
            )
            self.client.register_server(cost_config)

            if ctx:
                await ctx.info(f"Registered cost analysis server: {cost_server_url}")

        if diagram_server_url:
            diagram_config = MCPServerConfig(
                name="diagram-analysis",
                server_type=MCPServerType.DIAGRAM_ANALYSIS,
                base_url=diagram_server_url,
                timeout=45,  # Diagram analysis might take some time
                retry_attempts=2
            )
            self.client.register_server(diagram_config)

            if ctx:
                await ctx.info(f"Registered diagram analysis server: {diagram_server_url}")

        self._configured = True

    async def get_integrated_analysis(
        self,
        solution_id: str,
        solution_text: str,
        diagram_path: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive analysis using all available MCP servers.

        Args:
            solution_id: Unique identifier for the solution
            solution_text: Description of the solution
            diagram_path: Optional path to architecture diagram
            ctx: MCP context for logging

        Returns:
            Comprehensive analysis results
        """
        if not self._configured:
            if ctx:
                await ctx.warning("MCP integrations not configured")
            return {"error": "MCP integrations not configured"}

        async with self.client:
            return await self.client.validate_solution_with_external_tools(
                solution_id, solution_text, diagram_path, ctx
            )

    def is_cost_analysis_available(self) -> bool:
        """Check if cost analysis integration is available."""
        return self.client._get_server_config(MCPServerType.COST_ANALYSIS) is not None

    def is_diagram_analysis_available(self) -> bool:
        """Check if diagram analysis integration is available."""
        return self.client._get_server_config(MCPServerType.DIAGRAM_ANALYSIS) is not None


# Global integration manager instance
integration_manager = MCPIntegrationManager()


# Utility functions for external use
async def setup_mcp_integrations(
    cost_server_url: Optional[str] = None,
    diagram_server_url: Optional[str] = None,
    ctx: Optional[Context] = None
) -> None:
    """Set up MCP server integrations."""
    await integration_manager.setup_integrations(cost_server_url, diagram_server_url, ctx)


async def get_cost_analysis_integration(
    solution_id: str,
    solution_text: str,
    aws_services: List[str],
    ctx: Optional[Context] = None
) -> Optional[CostAnalysisData]:
    """Get cost analysis from integrated server."""
    async with integration_manager.client:
        return await integration_manager.client.get_cost_analysis(
            solution_id, solution_text, aws_services, ctx
        )


async def get_diagram_analysis_integration(
    solution_id: str,
    diagram_path: str,
    solution_context: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Optional[DiagramAnalysisData]:
    """Get diagram analysis from integrated server."""
    async with integration_manager.client:
        return await integration_manager.client.get_diagram_analysis(
            solution_id, diagram_path, solution_context, ctx
        )


def is_integration_available() -> Dict[str, bool]:
    """Check which integrations are available."""
    return {
        "cost_analysis": integration_manager.is_cost_analysis_available(),
        "diagram_analysis": integration_manager.is_diagram_analysis_available()
    }