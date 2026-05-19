"""
Shared logging utility for MCP servers that uses backend configuration passed via environment variables.
This ensures consistent logging across all MCP servers and the main backend application.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_mcp_logging(server_name, custom_log_file=None):
    """Set up logging for MCP servers using backend configuration passed via environment variables.
    
    Args:
        server_name (str): Name of the MCP server (used in log messages)
        custom_log_file (str, optional): Custom log file name. If None, uses backend log file or server_name.log
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get log level from environment variable set by backend
    log_level_name = os.getenv('BACKEND_LOG_LEVEL', os.getenv('FASTMCP_LOG_LEVEL', 'INFO')).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Determine log file - priority: custom_log_file > BACKEND_LOG_FILE env var > server_name.log
    if custom_log_file:
        log_file = custom_log_file
    elif os.getenv('BACKEND_LOG_FILE'):
        # Use the same log file as backend for unified logging
        log_file = os.getenv('BACKEND_LOG_FILE')
    else:
        log_file = f"{server_name}.log"
    
    # Create formatter matching backend logger format
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Set up file handler with rotation (same settings as backend)
    log_handler_file = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB per file, 5 backups
    )
    log_handler_file.setFormatter(log_formatter)
    
    # Set up console handler - CRITICAL: Use stderr for MCP compatibility (stdout is reserved for JSON-RPC)
    log_handler_stream = logging.StreamHandler(sys.stderr)
    log_handler_stream.setFormatter(log_formatter)
    
    # Get the root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates if called multiple times
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the new handlers
    root_logger.addHandler(log_handler_file)
    root_logger.addHandler(log_handler_stream)
    
    # Create and return a logger for this specific server with mcp.server prefix
    logger_name = f"mcp.server.{server_name}"
    server_logger = logging.getLogger(logger_name)
    server_logger.info(f"MCP Server logging configured: Level={logging.getLevelName(log_level)}, File={log_file}")
    
    # Suppress AWS SDK debug spam (same as backend)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    logging.getLogger('botocore.httpsession').setLevel(logging.WARNING)
    logging.getLogger('botocore.parsers').setLevel(logging.WARNING)
    logging.getLogger('botocore.retryhandler').setLevel(logging.WARNING)
    logging.getLogger('botocore.hooks').setLevel(logging.WARNING)

    # Suppress specific MCP framework low-level debug spam (but keep our mcp.server.* loggers)
    logging.getLogger('mcp.server.lowlevel').setLevel(logging.WARNING)
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
    logging.getLogger('mcp.client.lowlevel').setLevel(logging.WARNING)
    
    return server_logger

# Example usage for MCP servers:
# from backend.utils.mcp_logger import setup_mcp_logging
# logger = setup_mcp_logging("aws-diagram-mcp-server")
# logger.info("Server starting up")
# logger.debug("Debug message with data: %.50s", str(some_data))  # Truncate data to 50 chars
