#!/bin/bash

# POC Funding Reviewer MCP Server Startup Script
# This script handles the startup process with proper error handling and logging

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${LOG_FILE:-/var/log/poc-funding-reviewer/startup.log}"
PID_FILE="${PID_FILE:-/var/run/poc-funding-reviewer.pid}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$*"
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    log "WARN" "$*"
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    log "ERROR" "$*"
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    log "INFO" "$*"
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
    fi
}

# Signal handlers
handle_sigterm() {
    log_info "Received SIGTERM, shutting down gracefully..."
    cleanup
    exit 0
}

handle_sigint() {
    log_info "Received SIGINT, shutting down gracefully..."
    cleanup
    exit 0
}

# Set up signal handlers
trap handle_sigterm SIGTERM
trap handle_sigint SIGINT

# Check if already running
check_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_error "Server is already running with PID $pid"
            exit 1
        else
            log_warn "Stale PID file found, removing..."
            rm -f "$PID_FILE"
        fi
    fi
}

# Validate environment
validate_environment() {
    log_info "Validating environment..."
    
    # Check Python version
    if ! python3 --version | grep -q "Python 3.1[0-9]"; then
        log_error "Python 3.10+ is required"
        exit 1
    fi
    
    # Check required environment variables
    local required_vars=(
        "AWS_REGION"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check AWS credentials
    if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]] && [[ -z "${AWS_PROFILE:-}" ]]; then
        log_warn "No AWS credentials found. Make sure IAM roles are configured or set AWS_PROFILE/AWS_ACCESS_KEY_ID"
    fi
    
    log_success "Environment validation passed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    local dirs=(
        "$(dirname "$LOG_FILE")"
        "$(dirname "$PID_FILE")"
        "${TEMP_DIR:-/tmp/funding-reviewer}"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if virtual environment exists
    if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
        log_error "Virtual environment not found. Run 'uv sync' first."
        exit 1
    fi
    
    # Activate virtual environment
    source "$PROJECT_DIR/.venv/bin/activate"
    
    # Check if required packages are installed
    local required_packages=(
        "mcp"
        "boto3"
        "pypdf2"
        "pillow"
        "pandas"
        "python-docx"
        "pydantic"
    )
    
    for package in "${required_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            log_error "Required package '$package' is not installed"
            exit 1
        fi
    done
    
    log_success "Dependencies check passed"
}

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    local health_url="http://${MCP_SERVER_HOST:-localhost}:${MCP_SERVER_PORT:-8080}/health"
    
    log_info "Waiting for server to be ready..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$health_url" >/dev/null 2>&1; then
            log_success "Server is ready and healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Server not ready yet, waiting..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Server failed to become ready within $((max_attempts * 2)) seconds"
    return 1
}

# Start the server
start_server() {
    log_info "Starting POC Funding Reviewer MCP Server..."
    
    cd "$PROJECT_DIR"
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Set default environment variables if not set
    export AWS_REGION="${AWS_REGION:-us-west-2}"
    export BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-us.anthropic.claude-3-7-sonnet-20250219-v1:0}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    export MCP_SERVER_HOST="${MCP_SERVER_HOST:-0.0.0.0}"
    export MCP_SERVER_PORT="${MCP_SERVER_PORT:-8080}"
    
    # Start the server in background
    python -m awslabs.poc_funding_reviewer_mcp_server.server &
    local server_pid=$!
    
    # Save PID
    echo "$server_pid" > "$PID_FILE"
    
    log_info "Server started with PID $server_pid"
    
    # Wait a moment for the server to initialize
    sleep 5
    
    # Check if server is still running
    if ! kill -0 "$server_pid" 2>/dev/null; then
        log_error "Server failed to start"
        exit 1
    fi
    
    # Perform health check
    if health_check; then
        log_success "POC Funding Reviewer MCP Server started successfully"
        log_info "Server is running on http://${MCP_SERVER_HOST:-localhost}:${MCP_SERVER_PORT:-8080}"
        log_info "Health check endpoint: http://${MCP_SERVER_HOST:-localhost}:${MCP_SERVER_PORT:-8080}/health"
        log_info "PID file: $PID_FILE"
        log_info "Log file: $LOG_FILE"
    else
        log_error "Server started but failed health check"
        kill "$server_pid" 2>/dev/null || true
        exit 1
    fi
    
    # Wait for the server process
    wait "$server_pid"
}

# Main function
main() {
    log_info "Starting POC Funding Reviewer MCP Server startup script..."
    
    # Load environment file if it exists
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        log_info "Loading environment from .env file..."
        set -a
        source "$PROJECT_DIR/.env"
        set +a
    fi
    
    check_running
    create_directories
    validate_environment
    check_dependencies
    start_server
}

# Run main function
main "$@"