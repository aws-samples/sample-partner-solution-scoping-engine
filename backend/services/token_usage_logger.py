"""S3-based token usage logging for Bedrock API calls."""
import json
import logging
from datetime import datetime
import boto3

logger = logging.getLogger(__name__)

class TokenUsageLogger:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        
    def log_usage(self, user_id, chat_id, input_tokens, output_tokens, model_id=None):
        """Log token usage to S3 in partitioned structure for Athena."""
        try:
            timestamp = datetime.utcnow()
            
            log_entry = {
                'timestamp': timestamp.isoformat() + 'Z',
                'user_id': user_id,
                'chat_id': chat_id,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'model_id': model_id or 'unknown'
            }
            
            # Partitioned S3 key for Athena
            s3_key = f"year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}/{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.json"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(log_entry),
                ContentType='application/json'
            )
            
            logger.debug(f"Token usage logged: {user_id[:8]}... {input_tokens}+{output_tokens} tokens")
            
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
