"""
Main entry point for running the SeraV2 backend as a module.
"""
import os
import sys

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add the parent directory to the Python path for config imports
parent_dir = os.path.dirname(backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.app import create_app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    # Flask needs to bind to 0.0.0.0 for ALB connectivity in private subnets
    # nosec B104 - Binding to 0.0.0.0 is required for ALB health checks in AWS private subnets
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')  # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host: Application runs on EC2 instance behind Application Load Balancer in a private VPC subnet # nosec B104 - Binding to 0.0.0.0 is required for ALB health checks in AWS private subnets
