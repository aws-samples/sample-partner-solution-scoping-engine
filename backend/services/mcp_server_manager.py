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
Singleton manager for MCP servers.
This class manages MCP server connections at the application level,
allowing multiple users to share the same tool mapping.
"""
import logging
import asyncio
import json
import threading
import time
from typing import Dict, Optional
from .mcp_client_service import MCPClient
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPChatConnection:
    """Represents a persistent MCP server connection for a specific chat."""
    
    def __init__(self, server_name: str, server_config: dict):
        self.server_name = server_name
        self.server_config = server_config
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self.last_used = time.time()
        self.is_connected = False
        
    async def connect(self):
        """Establish connection to the MCP server."""
        try:
            import os
            
            # CRITICAL FIX: Inherit parent process environment variables
            # This ensures EC2 instance role credentials are available to MCP servers
            # Start with the parent process's environment
            processed_env = os.environ.copy()
            
            # Process and override with server-specific environment variables
            env_vars = self.server_config.get("env", {})
            
            for key, value in env_vars.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract config key from ${CONFIG_KEY} format
                    config_key = value[2:-1]  # Remove ${ and }
                    from ..config.app_config import CustomerConfig
                    processed_env[key] = CustomerConfig.get_value(config_key)
                else:
                    processed_env[key] = value
            
            params = StdioServerParameters(
                command=self.server_config["command"],
                args=self.server_config.get("args", []),
                env=processed_env
            )
            
            # Create the stdio connection
            self.read_stream, self.write_stream = await stdio_client(params).__aenter__()
            
            # Create and initialize the session
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            
            self.is_connected = True
            self.last_used = time.time()
            logger.debug(f"Connected to MCP server {self.server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {e}")
            self.is_connected = False
            return False
    
    async def execute_tool(self, tool_name: str, arguments: dict):
        """Execute a tool on this connection."""
        if not self.is_connected or not self.session:
            raise Exception(f"Not connected to server {self.server_name}")
            
        self.last_used = time.time()
        
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            
            # Format the result for Bedrock
            if hasattr(result, 'isError') and result.isError:
                return {
                    "content": result.content,
                    "status": "error"
                }
            else:
                return {
                    "content": result.content,
                    "status": "success"
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on server {self.server_name}: {e}")
            return {
                "content": [{"text": f"Error executing tool: {str(e)}"}],
                "status": "error"
            }
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None
                
            if self.read_stream and self.write_stream:
                # stdio_client context manager handles cleanup
                pass
                
            self.is_connected = False
            logger.debug(f"Disconnected from MCP server {self.server_name}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server {self.server_name}: {e}")

class MCPServerManager:
    _instance = None
    _initialized = False
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the MCPServerManager"""
        if cls._instance is None:
            cls._instance = MCPServerManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the manager (only once)"""
        if MCPServerManager._initialized:
            return
        
        self.tools = None
        self.server_configs = None
        self.tool_mapping = {}
        
        # Chat-scoped connection pools
        self.chat_pools = {}  # chat_id -> {server_name -> MCPChatConnection}
        self.pool_locks = {}  # chat_id -> asyncio.Lock
        self.chat_cleanup_timers = {}  # chat_id -> Timer for cleanup
        
        MCPServerManager._initialized = True
        logger.debug("MCPServerManager singleton created with connection pooling")
    
    async def initialize(self, server_configs):
        """
        Initialize MCP servers and retrieve tools
        
        Args:
            server_configs (dict): Dictionary of server configurations
            
        Returns:
            List of available tools from all MCP servers
        """
        if self.tools is not None:
            logger.debug("MCP tools already initialized, returning cached tools")
            return self.tools
            
        logger.debug("Initializing MCP tools at application level")
        self.server_configs = server_configs
        
        try:
            # Create a temporary MCPClient to initialize the tool mapping
            mcp_client = MCPClient(server_configs)
            
            # Initialize the tool mapping
            self.tool_mapping = await mcp_client.initialize_tool_mapping()
            logger.debug(f"Initialized tool mapping with {len(self.tool_mapping)} tools")
            
            # Get all tools for Bedrock
            self.tools = await mcp_client.get_all_tools()
            logger.debug(f"Retrieved {len(self.tools)} tools for Bedrock")
            
            return self.tools
        except Exception as e:
            logger.error(f"Error initializing MCP tools: {e}")
            return []
    
    async def get_chat_connection(self, chat_id: str, server_name: str) -> Optional[MCPChatConnection]:
        """Get or create a persistent connection for a chat-server combination."""
        # Initialize chat pools if needed
        if chat_id not in self.chat_pools:
            self.chat_pools[chat_id] = {}
            self.pool_locks[chat_id] = asyncio.Lock()
            logger.debug(f"Initialized connection pool for chat {chat_id}")
            
        # Use lock to ensure thread safety
        async with self.pool_locks[chat_id]:
            if server_name not in self.chat_pools[chat_id]:
                # Create new connection
                server_config = self.server_configs.get(server_name)
                if not server_config:
                    logger.error(f"No configuration found for server {server_name}")
                    return None
                    
                connection = MCPChatConnection(server_name, server_config)
                if await connection.connect():
                    self.chat_pools[chat_id][server_name] = connection
                    logger.debug(f"Created new connection for chat {chat_id}, server {server_name}")
                else:
                    logger.error(f"Failed to create connection for chat {chat_id}, server {server_name}")
                    return None
            
            # Reset cleanup timer for this chat
            self._reset_cleanup_timer(chat_id)
            
            return self.chat_pools[chat_id][server_name]
    
    def _reset_cleanup_timer(self, chat_id: str):
        """Reset the cleanup timer for a chat (15 minutes idle)."""
        if chat_id in self.chat_cleanup_timers:
            self.chat_cleanup_timers[chat_id].cancel()
            
        # Create a timer to cleanup connections after 15 minutes of inactivity
        timer = threading.Timer(900, self._cleanup_chat_connections, args=[chat_id])
        timer.start()
        self.chat_cleanup_timers[chat_id] = timer
        logger.debug(f"Reset cleanup timer for chat {chat_id}")
    
    def _cleanup_chat_connections(self, chat_id: str):
        """Cleanup connections for a specific chat."""
        logger.debug(f"Cleaning up connections for chat {chat_id}")
        
        if chat_id in self.chat_pools:
            # Schedule cleanup in the event loop
            asyncio.create_task(self._async_cleanup_chat(chat_id))
    
    async def _async_cleanup_chat(self, chat_id: str):
        """Async cleanup of chat connections."""
        try:
            if chat_id in self.chat_pools:
                connections = self.chat_pools[chat_id]
                for server_name, connection in connections.items():
                    try:
                        await connection.disconnect()
                        logger.debug(f"Disconnected {server_name} for chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Error disconnecting {server_name} for chat {chat_id}: {e}")
                
                # Remove from pools
                del self.chat_pools[chat_id]
                if chat_id in self.pool_locks:
                    del self.pool_locks[chat_id]
                if chat_id in self.chat_cleanup_timers:
                    del self.chat_cleanup_timers[chat_id]
                    
                logger.debug(f"Cleaned up all connections for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error during async cleanup for chat {chat_id}: {e}")

    async def get_tools(self):
        """
        Get the cached tools or initialize if not already done
        
        Returns:
            List of available tools from all MCP servers
        """
        if self.tools is not None:
            return self.tools
            
        # If tools aren't initialized yet, initialize with default server configs
        return await self.initialize(self.server_configs if self.server_configs else {})
            
    async def execute_tool(self, tool_name, arguments, chat_id=None):
        """
        Execute a tool with the given arguments using chat-scoped connections if available
        
        Args:
            tool_name (str): Name of the tool to execute
            arguments (dict): Arguments to pass to the tool
            chat_id (str, optional): Chat ID for connection pooling
            
        Returns:
            Tool execution result
        """
        if not self.server_configs:
            logger.error("MCP server configurations not initialized")
            return {"content": [{"text": "MCP server configurations not initialized"}], "status": "error"}
            
        # Add chat_id as metadata if provided
        if chat_id and tool_name == 'create_pricing_calculator_link':
            arguments['metadata'] = {'chat_id': chat_id}
        server_name = self.tool_mapping.get(tool_name)
        if not server_name:
            logger.error(f"No server found for tool: {tool_name}")
            return {
                "content": [{"text": f"Tool {tool_name} not found in any server"}],
                "status": "error"
            }
            
        # WAFR FIX #2: Authentication Resolution
        # Add authentication context for WAFR MCP server
        server_config = self.server_configs.get(server_name, {}).copy()
        if server_name == "aws-well-architected-framework-mcp-server":
            try:
                from flask import session
                from ..middleware.auth_middleware import get_current_user
                
                # Get current user and session information
                current_user = get_current_user()
                if current_user:
                    # Add user context to environment
                    if 'env' not in server_config:
                        server_config['env'] = {}
                    
                    server_config['env']['SERA_USER_ID'] = current_user.user_id
                    server_config['env']['SERA_USER_EMAIL'] = current_user.email
                    
                    # Add session token if available
                    if 'sera_session' in session:
                        server_config['env']['SERA_SESSION_TOKEN'] = session['sera_session']
                    
                    logger.debug(f"Added authentication context for WAFR MCP server: user={current_user.user_id}")
                else:
                    logger.warning("No current user found for WAFR MCP server authentication")
                    
            except Exception as e:
                logger.warning(f"Failed to add authentication context for WAFR MCP server: {e}")
            
        # Inject chat_id for cost analysis tools if chat_id is provided
        if chat_id and tool_name == "generate_cost_report":
            logger.debug(f"Injecting chat_id {chat_id} into cost analysis tool arguments")
            arguments = arguments.copy()  # Don't modify the original arguments
            arguments["chat_id"] = chat_id
            
        # Inject chat_id for WAFR tools if chat_id is provided
        wafr_tools = [
            "analyze_architecture_documents",
            "assess_pillar_compliance", 
            "generate_comprehensive_wafr_assessment",
            "generate_professional_report"
        ]
        if chat_id and tool_name in wafr_tools:
            logger.debug(f"Injecting chat_id {chat_id} into WAFR tool arguments")
            arguments = arguments.copy()  # Don't modify the original arguments
            arguments["chat_id"] = chat_id
            
        try:
            # TEMPORARILY DISABLE CONNECTION POOLING DUE TO ASYNC ISSUES
            # Re-enable after fixing event loop conflicts
            if False and chat_id:  # Disabled
                connection = await self.get_chat_connection(chat_id, server_name)
                if connection and connection.is_connected:
                    logger.debug(f"Using pooled connection for tool '{tool_name}' in chat {chat_id}")
                    result = await connection.execute_tool(tool_name, arguments)
                    logger.debug(f"Tool '{tool_name}' execution completed with status: {result.get('status', 'unknown')}")
                    return result
                else:
                    logger.warning(f"Failed to get pooled connection for chat {chat_id}, falling back to new connection")
            
            # Use original behavior with new connections (with updated server config)
            logger.debug(f"Creating new MCPClient to execute tool '{tool_name}'")
            
            # Use the potentially modified server configs (with auth context)
            configs_to_use = self.server_configs.copy()
            if server_config != self.server_configs.get(server_name, {}):
                configs_to_use[server_name] = server_config
            
            mcp_client = MCPClient(configs_to_use)
            
            # The tool_mapping is already initialized, so copy it to the new client
            mcp_client.tool_mapping = self.tool_mapping.copy()
            
            # Execute the tool
            logger.debug(f"Executing tool '{tool_name}' with new connection")
            result = await mcp_client.call_tool(tool_name, arguments)
            logger.debug(f"Tool '{tool_name}' execution completed with status: {result.get('status', 'unknown')}")
            
            # Log only result summary to reduce overhead
            result_size = len(str(result)) if result else 0
            logger.debug(f"MCP server response size: {result_size} bytes")
            
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "content": [{"text": f"Error executing tool: {str(e)}"}],
                "status": "error"
            }
