#!/usr/bin/env python3
"""
WSGI entry point for the SERA backend application.
This file is used by production WSGI servers like Gunicorn.
"""

import os
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import the Flask application factory
from app import create_app

# Create the Flask application instance
application = create_app()

if __name__ == "__main__":
    # This allows running the WSGI file directly for testing
    application.run(debug=False, host='0.0.0.0', port=5001) # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host: Application runs on EC2 instance behind Application Load Balancer in a private VPC subnet # nosec B104 - Binding to 0.0.0.0 is required for ALB health checks in AWS private subnets