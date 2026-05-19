"""
Main Flask application entry point for the SeraV2 Solutions Assistant.

Uses the application factory pattern.
"""

import os
import sys
import json
import logging
import asyncio
import socket
from flask import Flask, jsonify, request, current_app
from flask_session import Session
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
import boto3
from botocore.config import Config

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def load_configuration():
    """Load configuration from config.json and return it."""
    from backend.config.app_config import CustomerConfig
    CustomerConfig.load_config()
    return CustomerConfig.get_config()

def create_app(config_name='default'):
    """Creates and configures the Flask application.

    Args:
        config_name (str): The configuration environment (e.g., 'development', 'production').

    Returns:
        Flask: The configured Flask application instance.
    """
    # Import required modules
    import os
    import json
    import asyncio
    
    # Set up basic logging first
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting Flask application creation")
    
    # --- Flask App Initialization ---
    app = Flask(__name__)
    logger.info("Flask application initialized")
    

    # Load configuration and store in app context
    customer_config = load_configuration()
    app.config['CUSTOMER_CONFIG'] = customer_config
    
    # Store critical config values directly in app config for easy access
    app.config['DYNAMODB_TABLE_NAME'] = customer_config.get('DYNAMODB_TABLE_NAME')
    app.config['AWS_REGION'] = customer_config.get('AWS_REGION')
    app.config['S3_DOCUMENTS_BUCKET'] = customer_config.get('S3_DOCUMENTS_BUCKET', 'sera-v3-chat-docs')
    
    # Store file classification config for easy access by routes
    app.config['FILE_CLASSIFICATION_CONFIG'] = customer_config.get('FILE_CLASSIFICATION_CONFIG', {})
    
    logger.info(f"Customer configuration loaded into app context. DynamoDB table: {app.config['DYNAMODB_TABLE_NAME']}")

    # Configure AWS region
    region = app.config['AWS_REGION']
    logger.info(f"Configuring AWS region: {region}")
    
    # Configure boto3 with retry settings
    boto3_config = Config(
        region_name=region,
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    # Store the config in app context for reuse
    app.config['AWS_CONFIG'] = boto3_config
    logger.info("AWS configuration stored in app context")

    # Import dependencies after config is loaded
    logger.info("Importing dependencies")
    from backend.utils.logger import setup_logging
    from backend.routes.chat_routes import chat_bp
    from backend.routes.persona_routes import persona_bp
    from backend.routes.file_routes import file_bp  # Import the new file routes
    from backend.routes.document_routes import document_bp  # Import document management routes
    # from backend.routes.sow_routes import sow_bp  # Import SOW review routes - DISABLED pending security fixes
    from backend.routes.auth_routes import auth_bp  # Import auth routes
    # from backend.routes.admin_routes import admin_bp  # Import admin routes - DISABLED: stub endpoints not production ready
    # from backend.routes.test_routes import test_bp  # Import test routes (temporary) - COMMENTED OUT FOR SECURITY
    from backend.routes.sa_review_routes import sa_review_bp  # Import SA review routes
    from backend.routes.support_routes import support_bp  # Import support routes
    from backend.routes.wafr_routes import wafr_bp  # Import WAFR routes
    from backend.routes.nova_act_routes import nova_act_bp  # Import Nova Act routes
    from backend.services.mcp_server_manager import MCPServerManager
    
    # --- Logging Setup ---
    log_level_name = app.config['CUSTOMER_CONFIG'].get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_file = app.config['CUSTOMER_CONFIG'].get('LOG_FILE', 'backend.log')
    setup_logging(log_level=log_level, log_file=log_file)
    logger = logging.getLogger(__name__)
    logger.info("--- Starting SeraV2 Backend Application --- Configuraton: %s", config_name)

    # --- Initialize MCP Server Manager ---
    # Load MCP configuration
    mcp_config_path = os.path.join(os.path.dirname(__file__), 'config', 'mcp.json')
    with open(mcp_config_path, 'r') as f:
        mcp_data = json.load(f)
        if 'mcpServers' in mcp_data:
            mcp_servers = mcp_data['mcpServers']
        else:
            mcp_servers = {}
    
    # Inject backend log level into MCP server environment variables
    backend_log_level = app.config['CUSTOMER_CONFIG'].get('LOG_LEVEL', 'INFO').upper()
    logger.info(f"Injecting backend log level '{backend_log_level}' into MCP server configurations")
    
    for server_name, server_config in mcp_servers.items():
        if 'env' not in server_config:
            server_config['env'] = {}
        
        # Set the backend log level for MCP servers, but preserve any existing FASTMCP_LOG_LEVEL if explicitly set
        if 'FASTMCP_LOG_LEVEL' not in server_config['env']:
            server_config['env']['FASTMCP_LOG_LEVEL'] = backend_log_level
            logger.debug(f"Set FASTMCP_LOG_LEVEL={backend_log_level} for MCP server '{server_name}'")
        else:
            logger.debug(f"MCP server '{server_name}' already has FASTMCP_LOG_LEVEL={server_config['env']['FASTMCP_LOG_LEVEL']}, keeping existing value")
        
        # Also pass the backend log file path so MCP servers can use the same log file
        backend_log_file = app.config['CUSTOMER_CONFIG'].get('LOG_FILE', 'backend.log')
        server_config['env']['BACKEND_LOG_FILE'] = backend_log_file
        server_config['env']['BACKEND_LOG_LEVEL'] = backend_log_level
    
    # Initialize MCP servers during startup with app context
    with app.app_context():
        logger.info("Initializing MCP Server Manager during startup")
        mcp_manager = MCPServerManager.get_instance()
        
        # Create an event loop for async initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the initialization
            tools = loop.run_until_complete(mcp_manager.initialize(mcp_servers))
            logger.info(f"MCP Server Manager initialized with {len(tools)} tools")
        except Exception as e:
            logger.error(f"Error initializing MCP Server Manager: {e}", exc_info=True)
        finally:
            loop.close()

    # --- CORS Configuration ---
    CORS(app, 
         resources={r"/api/*": {
             "origins": ["http://localhost:7001", "http://localhost", "http://localhost:5001", "https://cors-domain-name"],  # -- CORS SETTING -- Frontend - replace domain name with your valid domain name
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "Accept", "X-CSRFToken"],
             "expose_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "max_age": 600  # Cache preflight requests for 10 minutes
         }},
         supports_credentials=True)
         
    # Add a route to set a test cookie
    @app.route('/api/test-cookie')
    def set_test_cookie():
        """Set a test cookie to verify cookie functionality."""
        response = jsonify({"status": "cookie set"})
        response.set_cookie('test_cookie', 'test_value', httponly=False, secure=False, samesite=None)
        return response

    # --- Request Logging ---
    @app.before_request
    def log_request_info():
        # Only log non-polling requests at INFO, everything else at DEBUG
        if request.endpoint not in ['chat_bp.get_chat_session', 'persona_bp.health_check']:
            logger.info(f"REQUEST: {request.method} {request.path}, endpoint={request.endpoint}")
        else:
            logger.debug(f"REQUEST: {request.method} {request.path}, endpoint={request.endpoint}")
        
    # --- Session Logging ---
    @app.before_request
    def log_session_info():
        """Log session information for debugging."""
        from flask import session
        try:
            session_data = {} 
            for key in session:
                try:
                    session_data[key] = session[key]
                except Exception as e:
                    session_data[key] = f"[Error serializing: {str(e)}]"
            # logger.info(f"Session data for request {request.path}: {session_data}") # really verbose
        except Exception as e:
            logger.error(f"Session logging failed: error={str(e)[:50]}...")

    # --- Security Headers and CORS ---
    @app.after_request
    def add_security_headers(response):
        from backend.config.app_config import CustomerConfig
        
        # Set security headers
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # CSP - Environment aware
        is_dev = CustomerConfig.get_run_mode() == 'DEV'
        cloudfront_domain = CustomerConfig.get_value('CLOUDFRONT_DOMAIN') or ''
        
        if is_dev:
            csp = (
                "default-src 'none'; "
                "script-src 'self' http://localhost:7001; "
                "style-src 'self' 'unsafe-inline' http://localhost:7001; "
                "img-src 'self' data: http: https:; "
                "font-src 'self' http://localhost:7001; "
                f"connect-src 'self' http://localhost:5001 http://localhost:7001 https://bedrock-runtime.*.amazonaws.com {cloudfront_domain}; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "object-src 'none'"
            )
        else:
            csp = (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "media-src 'self' https:; "
                f"connect-src 'self' {cloudfront_domain}; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "object-src 'none'; "
                "upgrade-insecure-requests"
            )
        
        response.headers['Content-Security-Policy'] = csp
        
        # Handle OPTIONS requests specifically (for CORS preflight)
        if request.method == 'OPTIONS':
            # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:7001'
            # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
            # response.headers['Access-Control-Allow-Origin'] = 'https://your-domain.com'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With, X-CSRFToken'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '600'
            
        return response

    # --- Configuration ---
    secrets_client = boto3.client('secretsmanager', region_name=app.config['AWS_REGION'], config=boto3_config)
    stack_prefix = app.config['CUSTOMER_CONFIG']['STACK_PREFIX']
    flask_secret_name = f"{stack_prefix}-flask-secret-key"
    secret_response = secrets_client.get_secret_value(SecretId=flask_secret_name)
    secret_data = json.loads(secret_response['SecretString'])
    app.config['SECRET_KEY'] = secret_data['secret_key']
    
    # Create Redis client for session management
    import redis
    from backend.utils.redis_credential_provider import ElastiCacheIAMProvider
    
    try:
        redis_host = app.config['CUSTOMER_CONFIG'].get('REDIS_HOST')
        redis_port = int(app.config['CUSTOMER_CONFIG'].get('REDIS_PORT'))
        
        if redis_host == 'localhost':
            # Local development
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=False)
        else:
            # Production with IAM auth using credential provider for auto-refresh
            cluster_name = app.config['CUSTOMER_CONFIG'].get('REDIS_REPLICATION_GROUP_ID')
            user_name = app.config['CUSTOMER_CONFIG'].get('REDIS_IAM_USER_NAME')
            region = app.config['AWS_REGION']
            
            # Create credential provider for automatic token refresh
            creds_provider = ElastiCacheIAMProvider(
                user=user_name,
                cluster_name=cluster_name,
                region=region
            )
            
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                credential_provider=creds_provider,
                ssl=True,
                decode_responses=False
            )
        
        redis_client.ping()
        app.config['SESSION_TYPE'] = 'redis'
        app.config['SESSION_REDIS'] = redis_client
        
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise RuntimeError(f"Redis connection failed: {e}") from e
    
    # Session configuration
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for local development (ALB enforces HTTPS in production)
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS-based session theft
    app.config['SESSION_COOKIE_SAMESITE'] = None  # Allow cross-site requests (required for webhooks)
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Use the default domain
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['SESSION_COOKIE_NAME'] = 'sera_session'  # Custom session cookie name

    logger.debug("Application configuration loaded")
    logger.debug("AWS Region: %s", app.config['AWS_REGION'])
    logger.debug("DynamoDB Table: %s", app.config['DYNAMODB_TABLE_NAME'])
    logger.debug("S3 Documents Bucket: %s", app.config['S3_DOCUMENTS_BUCKET'])
    
    # Log Redis host only if Redis is configured
    if app.config['SESSION_TYPE'] == 'redis' and app.config['SESSION_REDIS'] is not None:
        logger.debug("Redis Host: %s", app.config['CUSTOMER_CONFIG'].get('REDIS_HOST'))
    else:
        logger.debug("Using %s for session storage", app.config['SESSION_TYPE'])

    # Initialize extensions
    Session(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Configure CSRF
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # No expiration
    app.config['WTF_CSRF_SSL_STRICT'] = False  # ALB terminates SSL
    app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'DELETE', 'PATCH']
    
    # Exempt auth endpoints from CSRF (they use their own protection)
    csrf.exempt('auth_bp.auth')
    csrf.exempt('auth_bp.callback')
    csrf.exempt(nova_act_bp)
    
    logger.info("CSRF protection initialized")
    
    # Add before_request handler to log session data
    @app.before_request
    def log_session_data():
        from flask import session
        try:
            session_data = {}
            for key in session:
                try:
                    session_data[key] = session[key]
                except Exception as e:
                    session_data[key] = f"[Error serializing: {str(e)}]"
            # logger.debug(f"Session data for request {request.path}: {session_data}") # really verbose
        except Exception as e:
            logger.error(f"Error logging session data: {e}", exc_info=True)

    # Register blueprints
    logger.info("REGISTERING BLUEPRINTS - Starting blueprint registration")
    
    logger.info("REGISTERING auth_bp with url_prefix='/api'")
    app.register_blueprint(auth_bp, url_prefix='/api')  # Register auth routes
    
    # logger.info("REGISTERING admin_bp with url_prefix='/api'")
    # app.register_blueprint(admin_bp, url_prefix='/api')  # Register admin routes - DISABLED: stub endpoints not production ready
    
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(persona_bp, url_prefix='/api')
    app.register_blueprint(file_bp, url_prefix='/api')  # Register the file routes
    app.register_blueprint(document_bp, url_prefix='/api')  # Register document management routes

    # app.register_blueprint(sow_bp, url_prefix='/api')  # Register SOW review routes - DISABLED pending security fixes
    
    app.register_blueprint(nova_act_bp, url_prefix='/api')  # Register Nova Act routes
    # app.register_blueprint(test_bp, url_prefix='/api')  # Register test routes (temporary) - COMMENTED OUT FOR SECURITY
    app.register_blueprint(sa_review_bp, url_prefix='/api')  # Register SA review routes
    app.register_blueprint(support_bp, url_prefix='/api')  # Register support routes
    app.register_blueprint(wafr_bp)  # Register WAFR routes (already has /api/wafr prefix)

    logger.info("BLUEPRINT REGISTRATION COMPLETE")
    
    # Log all registered routes
    logger.info("REGISTERED ROUTES:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule.rule} -> {rule.endpoint} (methods: {rule.methods})")
    logger.info("END REGISTERED ROUTES")

    # --- Frontend Routes with Authentication ---
    @app.route('/')
    @app.route('/home')
    @app.route('/chats')
    @app.route('/admin')
    @app.route('/sow-review')
    def frontend_routes():
        """Frontend routes that require authentication."""
        from backend.services.auth_service import get_auth_service
        from flask import redirect, url_for
        
        auth_service = get_auth_service()
        
        # Check if user is authenticated
        if not auth_service.is_authenticated():
            logger.info(f"Unauthenticated access to {request.path}, redirecting to login")
            # Redirect to login with return URL
            # Validate that the return path is internal (starts with / and doesn't contain ://)
            return_path = request.path
            if return_path.startswith('/') and '://' not in return_path:
                # Use urllib.parse.quote to properly encode the path
                from urllib.parse import quote
                encoded_return_path = quote(return_path)
                return redirect(url_for('auth_bp.auth') + f'?return_to={encoded_return_path}')
            else:
                # If the path is suspicious, just redirect to the auth page without a return_to
                return redirect(url_for('auth_bp.auth'))
        
        # User is authenticated, serve the frontend
        # This would typically serve your React/Vue/etc frontend
        # For now, return a simple response
        current_user = auth_service.get_current_user()
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>SERA - Authenticated</title></head>
        <body>
            <h1>Welcome to SERA, {current_user.display_name}!</h1>
            <p>You are logged in as: {current_user.email}</p>
            <p>Your roles: {', '.join(current_user.groups)}</p>
            <p>Permissions:</p>
            <ul>
                <li>Is Solutions Architect: {current_user.is_solutions_architect()}</li>
                <li>Can review SOW: {current_user.can_review_sow()}</li>
                <li>Is Solutions Architect: {current_user.is_solutions_architect()}</li>
            </ul>
            <p><a href="/api/logout">Logout</a></p>
            <p><a href="/api/status">Check Auth Status (API)</a></p>
        </body>
        </html>
        """

    # --- Basic Routes (Health Check) ---
    @app.route('/health')
    def health_check():
        """Basic health check endpoint."""
        logger.debug("Health check endpoint hit.")
        return jsonify({"status": "ok"}), 200
    
    # --- CSRF Token Endpoint ---
    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        """Get CSRF token for the current session."""
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        return jsonify({"csrf_token": token})
    
    # --- Login Page Route ---
    @app.route('/login')
    def login_page():
        """Login page for unauthenticated users."""
        from backend.services.auth_service import get_auth_service
        from flask import redirect, url_for
        
        auth_service = get_auth_service()
        
        # If already authenticated, redirect to home
        if auth_service.is_authenticated():
            return redirect(url_for('frontend_routes'))
        
        # Show login page
        return """
        <!DOCTYPE html>
        <html>
        <head><title>SERA - Login</title></head>
        <body>
            <h1>SERA Login</h1>
            <p>Please choose your authentication method:</p>
            <div style="margin: 20px 0;">
                <a href="/api/auth?provider=saml" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; margin-right: 10px;">
                    Login with SAML
                </a>
                <a href="/api/auth?provider=oauth2" style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none;">
                    Login with OAuth2
                </a>
            </div>
            <p><small>Note: SAML may have dependency issues in development. OAuth2 requires provider configuration.</small></p>
        </body>
        </html>
        """
        
    # Session debug route removed - exposed session data and raw cookies without authentication

    # --- Error Handling ---
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 Not Found: path={request.path[:50]}..., error={str(error)[:50]}...")
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Server Error: path={request.path[:50]}..., error={str(error)[:50]}...", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

    # --- Global OPTIONS Handler ---
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        """Handle OPTIONS requests for all paths."""
        logger.debug(f"OPTIONS request: path=/{path[:50]}...")
        response = jsonify({'success': True})
        # -- CORS SETTING -- Uncomment the below line for local development, comment out for production
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:7001'
        # -- CORS SETTING -- Uncomment the below line for a procution server (use your registered domain name)
        # response.headers['Access-Control-Allow-Origin'] = 'https://your-domain.com'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With, X-CSRFToken'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '600'
        return response, 200

    # Force suppress AWS SDK debug spam
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    logging.getLogger('botocore.httpsession').setLevel(logging.WARNING)
    logging.getLogger('botocore.parsers').setLevel(logging.WARNING)
    logging.getLogger('botocore.retryhandler').setLevel(logging.WARNING)
    logging.getLogger('botocore.hooks').setLevel(logging.WARNING)
    
    logger.info("Application setup complete.")
    return app

# --- Main Execution Guard ---
# This allows running with `python app.py` for development
# For production, use a WSGI server like Gunicorn or Waitress
if __name__ == '__main__':
    # Create the app using the factory
    app = create_app()
    # Get port from environment variable or default to 5001
    port = int(os.environ.get("PORT", 5001))
    # Run the app
    # nosec B104 - Binding to 0.0.0.0 is required for ALB health checks in AWS private subnets
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
