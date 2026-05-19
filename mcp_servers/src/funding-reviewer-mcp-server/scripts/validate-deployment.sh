#!/bin/bash

# POC Funding Reviewer MCP Server Deployment Validation Script
# This script validates that the server is properly deployed and configured

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HEALTH_URL="${HEALTH_URL:-http://localhost:8080/health}"
TIMEOUT="${TIMEOUT:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Exit codes
EXIT_SUCCESS=0
EXIT_FAILURE=1
EXIT_WARNING=2

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Test result tracking
test_passed() {
    ((TESTS_PASSED++))
    log_success "$1"
}

test_failed() {
    ((TESTS_FAILED++))
    log_error "$1"
}

test_warned() {
    ((TESTS_WARNED++))
    log_warn "$1"
}

# Test functions
test_project_structure() {
    log_info "Testing project structure..."
    
    local required_files=(
        "pyproject.toml"
        "README.md"
        "LICENSE"
        "NOTICE"
        "Dockerfile"
        "docker-compose.yml"
        ".env.template"
        ".env.example"
        ".dockerignore"
        "scripts/start.sh"
        "scripts/stop.sh"
        "scripts/health-check.sh"
        "awslabs/poc_funding_reviewer_mcp_server/server.py"
        "awslabs/poc_funding_reviewer_mcp_server/config.py"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_DIR/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        test_passed "All required project files are present"
    else
        test_failed "Missing required files: ${missing_files[*]}"
    fi
}

test_script_permissions() {
    log_info "Testing script permissions..."
    
    local scripts=(
        "scripts/start.sh"
        "scripts/stop.sh"
        "scripts/health-check.sh"
    )
    
    local non_executable=()
    
    for script in "${scripts[@]}"; do
        if [[ ! -x "$PROJECT_DIR/$script" ]]; then
            non_executable+=("$script")
        fi
    done
    
    if [[ ${#non_executable[@]} -eq 0 ]]; then
        test_passed "All scripts have correct permissions"
    else
        test_failed "Scripts not executable: ${non_executable[*]}"
    fi
}

test_python_dependencies() {
    log_info "Testing Python dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Check if virtual environment exists
    if [[ ! -d ".venv" ]]; then
        test_failed "Virtual environment not found. Run 'uv sync' first."
        return
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Check required packages
    local required_packages=(
        "mcp"
        "boto3"
        "fastapi"
        "uvicorn"
        "pypdf"
        "PIL"
        "pandas"
        "docx"
        "pydantic"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -eq 0 ]]; then
        test_passed "All required Python packages are installed"
    else
        test_failed "Missing Python packages: ${missing_packages[*]}"
    fi
}

test_configuration_loading() {
    log_info "Testing configuration loading..."
    
    cd "$PROJECT_DIR"
    
    # Test with minimal configuration
    export AWS_REGION="us-west-2"
    export BEDROCK_MODEL_ID="us.anthropic.claude-3-haiku-20240307-v1:0"
    export MOCK_BEDROCK="true"
    
    if source .venv/bin/activate && python -c "
from awslabs.poc_funding_reviewer_mcp_server.config import get_config
try:
    config = get_config()
    print(f'Configuration loaded successfully: {config.bedrock.region}')
except Exception as e:
    print(f'Configuration error: {e}')
    exit(1)
" 2>/dev/null; then
        test_passed "Configuration loads successfully"
    else
        test_failed "Configuration loading failed"
    fi
}

test_docker_files() {
    log_info "Testing Docker configuration..."
    
    # Test Dockerfile syntax
    if command -v docker >/dev/null 2>&1; then
        if docker build --dry-run -f "$PROJECT_DIR/Dockerfile" "$PROJECT_DIR" >/dev/null 2>&1; then
            test_passed "Dockerfile syntax is valid"
        else
            test_failed "Dockerfile has syntax errors"
        fi
    else
        test_warned "Docker not available, skipping Dockerfile validation"
    fi
    
    # Test docker-compose.yml syntax
    if command -v docker-compose >/dev/null 2>&1; then
        if docker-compose -f "$PROJECT_DIR/docker-compose.yml" config >/dev/null 2>&1; then
            test_passed "docker-compose.yml syntax is valid"
        else
            test_failed "docker-compose.yml has syntax errors"
        fi
    else
        test_warned "docker-compose not available, skipping compose file validation"
    fi
}

test_environment_files() {
    log_info "Testing environment configuration files..."
    
    # Test .env.template
    if [[ -f "$PROJECT_DIR/.env.template" ]]; then
        local required_vars=(
            "AWS_REGION"
            "BEDROCK_MODEL_ID"
            "MCP_SERVER_PORT"
            "LOG_LEVEL"
        )
        
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^$var=" "$PROJECT_DIR/.env.template"; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -eq 0 ]]; then
            test_passed "Environment template contains all required variables"
        else
            test_failed "Environment template missing variables: ${missing_vars[*]}"
        fi
    else
        test_failed "Environment template file not found"
    fi
    
    # Test .env.example
    if [[ -f "$PROJECT_DIR/.env.example" ]]; then
        if grep -q "AWS_REGION=us-west-2" "$PROJECT_DIR/.env.example"; then
            test_passed "Environment example file has valid values"
        else
            test_failed "Environment example file has invalid or missing values"
        fi
    else
        test_failed "Environment example file not found"
    fi
}

test_server_startup() {
    log_info "Testing server startup (dry run)..."
    
    cd "$PROJECT_DIR"
    
    # Set test configuration
    export AWS_REGION="us-west-2"
    export BEDROCK_MODEL_ID="us.anthropic.claude-3-haiku-20240307-v1:0"
    export MOCK_BEDROCK="true"
    export LOG_LEVEL="ERROR"
    
    # Test server import and basic initialization
    if source .venv/bin/activate && python -c "
import sys
import os
sys.path.insert(0, '.')

try:
    from awslabs.poc_funding_reviewer_mcp_server.server import create_health_app
    app = create_health_app()
    print('Server application created successfully')
except Exception as e:
    print(f'Server startup test failed: {e}')
    exit(1)
" 2>/dev/null; then
        test_passed "Server startup test passed"
    else
        test_failed "Server startup test failed"
    fi
}

test_health_endpoints() {
    log_info "Testing health endpoints (if server is running)..."
    
    # Check if server is running
    if curl -f -s "$HEALTH_URL" >/dev/null 2>&1; then
        log_info "Server is running, testing health endpoints..."
        
        # Test basic health check
        if curl -f -s "$HEALTH_URL" | grep -q '"status"'; then
            test_passed "Basic health check endpoint works"
        else
            test_failed "Basic health check endpoint failed"
        fi
        
        # Test detailed health check
        local detailed_url="${HEALTH_URL}/detailed"
        if curl -f -s "$detailed_url" | grep -q '"status"'; then
            test_passed "Detailed health check endpoint works"
        else
            test_failed "Detailed health check endpoint failed"
        fi
        
        # Test readiness check
        local ready_url="${HEALTH_URL%/health}/ready"
        if curl -f -s "$ready_url" | grep -q '"ready"'; then
            test_passed "Readiness check endpoint works"
        else
            test_failed "Readiness check endpoint failed"
        fi
        
        # Test metrics endpoint
        local metrics_url="${HEALTH_URL%/health}/metrics"
        if curl -f -s "$metrics_url" | grep -q '"uptime_seconds"'; then
            test_passed "Metrics endpoint works"
        else
            test_failed "Metrics endpoint failed"
        fi
    else
        test_warned "Server not running, skipping health endpoint tests"
    fi
}

test_aws_configuration() {
    log_info "Testing AWS configuration..."
    
    # Check if AWS CLI is available
    if ! command -v aws >/dev/null 2>&1; then
        test_warned "AWS CLI not available, skipping AWS configuration tests"
        return
    fi
    
    # Test AWS credentials
    if aws sts get-caller-identity >/dev/null 2>&1; then
        test_passed "AWS credentials are configured and valid"
        
        # Test Bedrock access
        local region="${AWS_REGION:-us-west-2}"
        if aws bedrock list-foundation-models --region "$region" >/dev/null 2>&1; then
            test_passed "AWS Bedrock access verified"
        else
            test_failed "Cannot access AWS Bedrock in region $region"
        fi
    else
        test_warned "AWS credentials not configured (may be using IAM roles)"
    fi
}

test_documentation() {
    log_info "Testing documentation..."
    
    local doc_files=(
        "README.md"
        "DEPLOYMENT.md"
        "CONFIGURATION.md"
    )
    
    local missing_docs=()
    
    for doc in "${doc_files[@]}"; do
        if [[ ! -f "$PROJECT_DIR/$doc" ]]; then
            missing_docs+=("$doc")
        fi
    done
    
    if [[ ${#missing_docs[@]} -eq 0 ]]; then
        test_passed "All documentation files are present"
    else
        test_failed "Missing documentation files: ${missing_docs[*]}"
    fi
    
    # Check README content
    if [[ -f "$PROJECT_DIR/README.md" ]]; then
        if grep -q "POC Funding Reviewer" "$PROJECT_DIR/README.md"; then
            test_passed "README.md contains project information"
        else
            test_warned "README.md may be incomplete"
        fi
    fi
}

# Main validation function
run_validation() {
    log_info "Starting POC Funding Reviewer MCP Server deployment validation..."
    echo
    
    # Run all tests
    test_project_structure
    test_script_permissions
    test_python_dependencies
    test_configuration_loading
    test_docker_files
    test_environment_files
    test_server_startup
    test_health_endpoints
    test_aws_configuration
    test_documentation
    
    # Summary
    echo
    log_info "Validation Summary:"
    log_info "  Tests Passed: $TESTS_PASSED"
    log_info "  Tests Warned: $TESTS_WARNED"
    log_info "  Tests Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Deployment validation FAILED"
        return $EXIT_FAILURE
    elif [[ $TESTS_WARNED -gt 0 ]]; then
        log_warn "Deployment validation completed with WARNINGS"
        return $EXIT_WARNING
    else
        log_success "Deployment validation PASSED"
        return $EXIT_SUCCESS
    fi
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -u, --url URL          Health check URL (default: $HEALTH_URL)"
    echo "  -t, --timeout SECONDS  Request timeout (default: $TIMEOUT)"
    echo "  -h, --help            Show this help message"
    echo
    echo "Exit codes:"
    echo "  0  All tests passed"
    echo "  1  One or more tests failed"
    echo "  2  Tests passed with warnings"
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--url)
                HEALTH_URL="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Run validation
    run_validation
}

# Run main function
main "$@"