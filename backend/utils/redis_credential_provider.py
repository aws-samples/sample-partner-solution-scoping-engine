"""
Redis ElastiCache IAM Credential Provider for automatic token refresh.

This provider integrates with Redis 6.4+ credential provider interface
to automatically refresh IAM authentication tokens every 15 minutes.
"""

import datetime
import hashlib
import hmac
from collections import OrderedDict
from typing import Tuple, Union
from urllib.parse import urlencode

import redis
from boto3 import Session
from cachetools import TTLCache, cached
import logging

logger = logging.getLogger(__name__)

class ElastiCacheIAMProvider(redis.CredentialProvider):
    """
    ElastiCache IAM credential provider that automatically refreshes tokens.
    
    Generates AWS4-HMAC-SHA256 signed authentication tokens for ElastiCache IAM auth.
    """
    
    # AWS signing constants
    ALGORITHM = 'AWS4-HMAC-SHA256'
    PARAM_ACTION = "Action"
    PARAM_USER = "User"
    HEADER_HOST = "host"
    TOKEN_EXPIRY_SECONDS = 900
    
    X_AMZ_ALGORITHM = 'X-Amz-Algorithm'
    X_AMZ_CREDENTIAL = 'X-Amz-Credential' #nosec B105 required for IAM credential provider
    X_AMZ_SECURITY_TOKEN = 'X-Amz-Security-Token' #nosec B105 required for IAM credential provider
    X_AMZ_DATE = 'X-Amz-Date'
    X_AMZ_EXPIRES = 'X-Amz-Expires'
    X_AMZ_SIGNED_HEADERS = 'X-Amz-SignedHeaders'
    X_AMZ_SIGNATURE = 'X-Amz-Signature'
    
    DATE_FORMAT = '%Y%m%d'
    DATETIME_FORMAT = '%Y%m%dT%H%M%SZ'
    
    def __init__(self, user: str, cluster_name: str, region: str = None):
        """
        Initialize the credential provider.
        
        Args:
            user (str): IAM username for ElastiCache access
            cluster_name (str): ElastiCache replication group ID
            region (str): AWS region where the cluster is located. If None, uses config system.
        """
        try:
            from backend.config.app_config import CustomerConfig
        except ImportError:
            from config.app_config import CustomerConfig
        
        self.user = user
        self.cluster_name = cluster_name
        self.region = region or CustomerConfig.get_config()['AWS_REGION']
        
        logger.info(f"ElastiCacheIAMProvider initialized for user '{user}', "
                   f"cluster '{cluster_name}', region '{region}'")

    @cached(cache=TTLCache(maxsize=128, ttl=900))  # Cache for 15 minutes
    def get_credentials(self) -> Tuple[str, str]:
        """
        Get IAM credentials for ElastiCache authentication.
        
        This method is called automatically by Redis when credentials
        are needed or when the cached token expires.
        
        Returns:
            Tuple[str, str]: (username, auth_token)
        """
        
        try:
            token = self._generate_iam_auth_token()
            logger.debug("Successfully generated IAM auth token")
            return (self.user, token)
            
        except Exception as e:
            logger.error(f"Failed to generate IAM auth token: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate IAM auth token: {e}") from e
    
    def _generate_iam_auth_token(self) -> str:
        """Generate IAM auth token using AWS4-HMAC-SHA256 signing."""
        logger.debug("Creating boto3 session...")
        session = Session()
        credentials = session.get_credentials()
        
        if not credentials:
            raise ValueError("No AWS credentials available")
            
        frozen_creds = credentials.get_frozen_credentials()
        access_key = frozen_creds.access_key
        secret_key = frozen_creds.secret_key
        session_token = frozen_creds.token
        
        if not access_key or not secret_key:
            raise ValueError("Invalid AWS credentials")
        
        now = datetime.datetime.utcnow()
        params = {
            self.PARAM_ACTION: 'connect',
            self.PARAM_USER: self.user,
        }
        
        if session_token:
            params[self.X_AMZ_SECURITY_TOKEN] = session_token
            
        return self._get_auth_token(access_key, secret_key, now, params)
    
    def _get_auth_token(self, access_key: str, secret_key: str, now: datetime.datetime, params: dict) -> str:
        """Generate the signed auth token."""
        amz_date = now.strftime(self.DATETIME_FORMAT)
        credential_scope = self._get_credentials_scope(now)
        
        query_params = {
            **params,
            self.X_AMZ_ALGORITHM: self.ALGORITHM,
            self.X_AMZ_DATE: amz_date,
            self.X_AMZ_SIGNED_HEADERS: self.HEADER_HOST,
            self.X_AMZ_EXPIRES: self.TOKEN_EXPIRY_SECONDS,
            self.X_AMZ_CREDENTIAL: access_key + '/' + credential_scope,
        }
        
        query_params = OrderedDict(sorted(query_params.items()))
        encoded_query_params = urlencode(query_params)
        
        canonical_request = self._get_canonical_request(encoded_query_params)
        request_hash = self._hash(canonical_request)
        
        string_to_sign = f"{self.ALGORITHM}\n{amz_date}\n{credential_scope}\n{request_hash}"
        
        signing_key = self._get_signature_key(secret_key, now)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return f"{self.cluster_name}/?{urlencode(query_params)}&{self.X_AMZ_SIGNATURE}={signature}"
    
    def _get_canonical_request(self, query_string: str, method: str = 'GET', uri: str = '/') -> str:
        """Build canonical request string."""
        headers = f"{self.HEADER_HOST}:{self.cluster_name}\n"
        payload_hash = self._hash('')
        
        return f"{method}\n{uri}\n{query_string}\n{headers}\n{self.HEADER_HOST}\n{payload_hash}"
    
    def _get_credentials_scope(self, now: datetime.datetime) -> str:
        """Get credential scope for signing."""
        datestr = (now + datetime.timedelta(seconds=self.TOKEN_EXPIRY_SECONDS)).strftime(self.DATE_FORMAT)
        return f"{datestr}/{self.region}/elasticache/aws4_request"
    
    def _get_signature_key(self, secret_key: str, now: datetime.datetime) -> bytes:
        """Generate signing key."""
        datestr = (now + datetime.timedelta(seconds=self.TOKEN_EXPIRY_SECONDS)).strftime(self.DATE_FORMAT)
        
        k_date = self._sign(('AWS4' + secret_key).encode('utf-8'), datestr)
        k_region = self._sign(k_date, self.region)
        k_service = self._sign(k_region, 'elasticache')
        k_signing = self._sign(k_service, 'aws4_request')
        
        return k_signing
    
    def _sign(self, key: bytes, msg: str) -> bytes:
        """Sign message with key."""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    
    def _hash(self, msg: str) -> str:
        """SHA256 hash of message."""
        return hashlib.sha256(msg.encode('utf-8')).hexdigest()