"""
Utility for setting up application-wide logging.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO, log_file="backend.log"):
    """Configures the root logger for the application.

    Args:
        log_level (int): The minimum logging level (e.g., logging.INFO, logging.DEBUG).
        log_file (str): The path to the log file.
    """
    from ..config.app_config import CustomerConfig
    
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates if called multiple times
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Check logging mode from config
    logging_mode = CustomerConfig.get_value('LOGGING_MODE', 'local')
    
    if logging_mode == 'cloudwatch':
        try:
            import watchtower
            import boto3
            
            stack_prefix = CustomerConfig.get_value('STACK_PREFIX', 'sera')
            aws_region = CustomerConfig.get_value('AWS_REGION', 'us-east-1')
            
            # Get EC2 instance ID from metadata service using IMDSv2
            try:
                import urllib.request
                # Get IMDSv2 token
                token_req = urllib.request.Request(
                    'http://169.254.169.254/latest/api/token',
                    headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
                    method='PUT'
                )
                token = urllib.request.urlopen(token_req, timeout=1).read().decode('utf-8')
                
                # Get instance ID using token
                instance_req = urllib.request.Request(
                    'http://169.254.169.254/latest/meta-data/instance-id',
                    headers={'X-aws-ec2-metadata-token': token}
                )
                instance_id = urllib.request.urlopen(instance_req, timeout=1).read().decode('utf-8')
            except Exception:
                # Fallback to PID if not on EC2
                instance_id = f'local-{os.getpid()}'
            
            # CloudWatch handler for application logs
            cw_handler = watchtower.CloudWatchLogHandler(
                log_group_name=f'{stack_prefix}-ec2-application-logs',
                stream_name=f'{stack_prefix}-backend-{instance_id}',
                boto3_client=boto3.client('logs', region_name=aws_region),
                send_interval=5,
                create_log_group=False
            )
            cw_handler.setFormatter(log_formatter)
            cw_handler.setLevel(log_level)
            root_logger.addHandler(cw_handler)
            
            # Stream handler for console output
            log_handler_stream = logging.StreamHandler(sys.stdout)
            log_handler_stream.setFormatter(log_formatter)
            root_logger.addHandler(log_handler_stream)
            
            root_logger.info("Logging configured: Mode=CloudWatch, LogGroup=%s-ec2-application-logs, Stream=%s-backend-%s", stack_prefix, stack_prefix, instance_id)
            
        except Exception as e:
            # Fallback to file logging if CloudWatch fails
            print(f"CloudWatch logging failed, falling back to file: {e}", file=sys.stderr)
            logging_mode = 'local'
    
    if logging_mode == 'local':
        # Local file logging
        log_handler_file = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        log_handler_file.setFormatter(log_formatter)
        root_logger.addHandler(log_handler_file)
        
        log_handler_stream = logging.StreamHandler(sys.stdout)
        log_handler_stream.setFormatter(log_formatter)
        root_logger.addHandler(log_handler_stream)
        
        root_logger.info("Logging configured: Mode=Local, Level=%s, File=%s", logging.getLevelName(log_level), log_file)
    
    # Silence noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)

# Example of getting a logger in another module:
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is an info message from another module.") 