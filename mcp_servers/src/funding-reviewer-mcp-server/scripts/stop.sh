#!/bin/bash

# POC Funding Reviewer MCP Server Stop Script
# This script handles graceful shutdown of the server

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

# Stop the server
stop_server() {
    log_info "Stopping POC Funding Reviewer MCP Server..."
    
    if [[ ! -f "$PID_FILE" ]]; then
        log_warn "PID file not found. Server may not be running."
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    
    # Check if process is running
    if ! kill -0 "$pid" 2>/dev/null; then
        log_warn "Process with PID $pid is not running"
        rm -f "$PID_FILE"
        return 0
    fi
    
    log_info "Sending SIGTERM to process $pid..."
    kill -TERM "$pid"
    
    # Wait for graceful shutdown
    local max_wait=30
    local wait_time=0
    
    while kill -0 "$pid" 2>/dev/null && [[ $wait_time -lt $max_wait ]]; do
        sleep 1
        ((wait_time++))
        if [[ $((wait_time % 5)) -eq 0 ]]; then
            log_info "Waiting for graceful shutdown... ($wait_time/${max_wait}s)"
        fi
    done
    
    # Check if process is still running
    if kill -0 "$pid" 2>/dev/null; then
        log_warn "Process did not shut down gracefully, sending SIGKILL..."
        kill -KILL "$pid"
        sleep 2
        
        if kill -0 "$pid" 2>/dev/null; then
            log_error "Failed to stop process $pid"
            return 1
        fi
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    log_success "POC Funding Reviewer MCP Server stopped successfully"
}

# Main function
main() {
    log_info "Starting POC Funding Reviewer MCP Server stop script..."
    stop_server
}

# Run main function
main "$@"