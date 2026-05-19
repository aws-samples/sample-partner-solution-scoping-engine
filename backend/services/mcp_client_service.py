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

"""
MCP Client Service for connecting to MCP servers and executing tools.
This implementation follows the example code pattern from the MCP documentation.
"""
import logging
import os
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, server_configs: dict):
        """
        Initialize the MCP client with server configurations.
        
        Args:
            server_configs (dict): Dictionary of server configurations
        """
        self.server_configs = server_configs
        self.tool_mapping = {}  # Maps tool names to server names
        
    async def __aenter__(self):
        """Async context manager entry"""
        # We don't connect to any servers here, just return self
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Nothing to clean up since we don't maintain persistent connections
        pass

    async def initialize_tool_mapping(self):
        """
        Initialize the tool mapping by connecting to each server briefly,
        getting its tools, and then disconnecting.
        This is only done once at application startup.
        """
        logger.debug("Initializing tool mapping from all configured MCP servers")
        self.tool_mapping = {}
        
        for server_name, config in self.server_configs.items():
            logger.debug(f"Connecting to MCP server {server_name} to get tools")
            try:
                # CRITICAL FIX: Inherit parent process environment variables
                # This ensures EC2 instance role credentials are available to MCP servers
                server_env = os.environ.copy()
                # Remove VIRTUAL_ENV to prevent uv from using the wrong venv in MCP server subprocesses
                server_env.pop('VIRTUAL_ENV', None)
                config_env = config.get("env", {})
                server_env.update(config_env)
                
                # Connect to the server
                params = StdioServerParameters(
                    command=config["command"],
                    args=config.get("args", []),
                    env=server_env
                )
                
                # Use the stdio_client as a context manager
                async with stdio_client(params) as (read_stream, write_stream):
                    # Use the ClientSession as a context manager
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        # Get the tools from this server
                        tools_response = await session.list_tools()
                        logger.debug(f"Server {server_name} has {len(tools_response.tools)} tools")
                        
                        # Map each tool to this server
                        for tool in tools_response.tools:
                            self.tool_mapping[tool.name] = server_name
                            logger.debug(f"Mapped tool '{tool.name}' to server '{server_name}'")
                
                logger.debug(f"Successfully initialized tools from server {server_name}")
            except Exception as e:
                logger.error(f"Error initializing tools from server {server_name}: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception details: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        logger.debug(f"Tool mapping initialization complete. {len(self.tool_mapping)} tools mapped.")
        return self.tool_mapping

    async def get_all_tools(self):
        """
        Get all tools in Bedrock-compatible format.
        This connects to each server, gets its tools, and then disconnects.
        """
        logger.debug("Getting all tools from configured MCP servers")
        bedrock_tools = []
        
        for server_name, config in self.server_configs.items():
            logger.debug(f"Connecting to MCP server {server_name} to get tools")
            try:
                # CRITICAL FIX: Inherit parent process environment variables
                # This ensures EC2 instance role credentials are available to MCP servers
                server_env = os.environ.copy()
                # Remove VIRTUAL_ENV to prevent uv from using the wrong venv in MCP server subprocesses
                server_env.pop('VIRTUAL_ENV', None)
                config_env = config.get("env", {})
                server_env.update(config_env)
                
                # Connect to the server
                params = StdioServerParameters(
                    command=config["command"],
                    args=config.get("args", []),
                    env=server_env
                )
                
                # Use the stdio_client as a context manager
                async with stdio_client(params) as (read_stream, write_stream):
                    # Use the ClientSession as a context manager
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        
                        # Get the tools from this server
                        tools_response = await session.list_tools()
                        logger.debug(f"Server {server_name} has {len(tools_response.tools)} tools")
                        
                        # Format each tool for Bedrock
                        for tool in tools_response.tools:
                            tool_spec = {
                                "toolSpec": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": {
                                        "json": tool.inputSchema
                                    }
                                }
                            }
                            bedrock_tools.append(tool_spec)
                            
                            # Also update the tool mapping
                            self.tool_mapping[tool.name] = server_name
                            logger.debug(f"Added tool '{tool.name}' from server '{server_name}'")
                
                logger.debug(f"Successfully retrieved tools from server {server_name}")
            except Exception as e:
                logger.error(f"Error retrieving tools from server {server_name}: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception details: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        logger.debug(f"Retrieved {len(bedrock_tools)} tools in total")
        return bedrock_tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """
        Call a tool with the given arguments.
        This connects to the appropriate server, calls the tool, and then disconnects.
        
        Args:
            tool_name (str): Name of the tool to call
            arguments (dict): Arguments to pass to the tool
            
        Returns:
            dict: Tool result with content and status
        """
        # Find which server has this tool
        server_name = self.tool_mapping.get(tool_name)
        if not server_name:
            logger.error(f"No server found for tool: {tool_name}")
            return {
                "content": [{"text": f"Tool {tool_name} not found in any server"}],
                "status": "error"
            }
        
        # Get the server configuration
        server_config = self.server_configs.get(server_name)
        if not server_config:
            logger.error(f"No configuration found for server: {server_name}")
            return {
                "content": [{"text": f"No configuration for server {server_name}"}],
                "status": "error"
            }
        
        logger.debug(f"Calling tool '{tool_name}' from server '{server_name}'")
        logger.debug(f"Tool arguments: {arguments}")
        
        try:
            # Connect to the server
            logger.debug(f"Creating server parameters for {server_name}")
            
            # CRITICAL FIX: Inherit parent process environment variables
            # This ensures EC2 instance role credentials are available to MCP servers
            # Start with the parent process's environment
            server_env = os.environ.copy()
            # Remove VIRTUAL_ENV to prevent uv from using the wrong venv in MCP server subprocesses
            server_env.pop('VIRTUAL_ENV', None)
            
            # Override with server-specific environment variables from config
            config_env = server_config.get("env", {}).copy()
            
            # Process template substitution for environment variables
            for key, value in config_env.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract config key from ${CONFIG_KEY} format
                    config_key = value[2:-1]  # Remove ${ and }
                    from ..config.app_config import CustomerConfig
                    server_env[key] = CustomerConfig.get_value(config_key)
                else:
                    server_env[key] = value
            
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            server_env["BACKEND_LOG_FILE"] = os.path.join(backend_dir, "backend.log")
            logger.info(f"Starting MCP server {server_name} with BACKEND_LOG_FILE: {server_env['BACKEND_LOG_FILE']}")
            
            params = StdioServerParameters(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_env
            )
            
            # Use the stdio_client as a context manager
            logger.debug(f"Connecting to stdio client...")
            async with stdio_client(params) as (read_stream, write_stream):
                # Use the ClientSession as a context manager
                logger.debug(f"Creating client session...")
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # Call the tool
                    logger.debug(f"Session initialized, calling tool...")
                    logger.debug(f"Executing tool '{tool_name}' on server '{server_name}'")
                    logger.debug(f"Arguments size: {len(str(arguments))} chars")
                    result = await session.call_tool(tool_name, arguments=arguments)
                    logger.debug(f"Tool call completed, result type: {type(result)}")
                    
                    # Log result size
                    result_str = str(result)
                    result_size = len(result_str)
                    logger.debug(f"Tool result size: {result_size:,} chars ({result_size/1024:.1f} KB)")
                    if result_size > 100000:
                        logger.warning(f"Large result detected: {result_size:,} chars")
                        logger.debug(f"Tool result: size={result_size} chars (content redacted)")
                    else:
                        logger.debug(f"Tool result: size={result_size} chars")
                    # Format the result for Bedrock
                    if hasattr(result, 'isError') and result.isError:
                        logger.debug(f"Tool '{tool_name}' returned an error: length={len(str(result.content))}")
                        return {
                            "content": result.content,
                            "status": "error"
                        }
                    else:
                        logger.debug(f"Tool '{tool_name}' executed successfully")
                        return {
                            "content": result.content,
                            "status": "success"
                        }
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}")
            # Return a structured error response that won't break document creation
            return {
                "content": [{"text": f"Error calling tool: {str(e)}"}],
                "status": "error"
            }
