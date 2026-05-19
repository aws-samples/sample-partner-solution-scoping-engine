#!/bin/bash

# POC Funding Reviewer MCP Server Health Check Script
# This script performs comprehensive health checks on the server

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HEALTH_URL="${HEALTH_URL:-http://localhost:8080/health}"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"

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

# Check if server is responding
check_server_response() {
    log_info "Checking server response at $HEALTH_URL..."
    
    local response
    local http_code
    
    if ! command -v curl >/dev/null 2>&1; then
        log_error "curl is not installed"
        return $EXIT_FAILURE
    fi
    
    # Make health check request
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null || echo "HTTPSTATUS:000")
    
    # Extract HTTP status code
    http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    # Extract response body
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    case "$http_code" in
        200)
            log_success "Server is responding (HTTP $http_code)"
            if [[ -n "$body" ]]; then
                log_info "Response: $body"
            fi
            return $EXIT_SUCCESS
            ;;
        000)
            log_error "Server is not responding (connection failed)"
            return $EXIT_FAILURE
            ;;
        *)
            log_error "Server returned HTTP $http_code"
            if [[ -n "$body" ]]; then
                log_error "Response: $body"
            fi
            return $EXIT_FAILURE
            ;;
    esac
}

# Check process status
check_process_status() {
    local pid_file="${PID_FILE:-/var/run/poc-funding-reviewer.pid}"
    
    log_info "Checking process status..."
    
    if [[ ! -f "$pid_file" ]]; then
        log_warn "PID file not found at $pid_file"
        return $EXIT_WARNING
    fi
    
    local pid=$(cat "$pid_file")
    
    if kill -0 "$pid" 2>/dev/null; then
        log_success "Process is running (PID: $pid)"
        
        # Get process info
        if command -v ps >/dev/null 2>&1; then
            local process_info=$(ps -p "$pid" -o pid,ppid,cmd --no-headers 2>/dev/null || echo "")
            if [[ -n "$process_info" ]]; then
                log_info "Process info: $process_info"
            fi
        fi
        
        return $EXIT_SUCCESS
    else
        log_error "Process with PID $pid is not running"
        return $EXIT_FAILURE
    fi
}

# Check system resources
check_system_resources() {
    log_info "Checking system resources..."
    
    local warnings=0
    
    # Check memory usage
    if command -v free >/dev/null 2>&1; then
        local mem_info=$(free -m | awk 'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)", $3,$2,$3*100/$2 }')
        log_info "$mem_info"
        
        local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
        if [[ $mem_usage -gt 90 ]]; then
            log_warn "High memory usage: ${mem_usage}%"
            ((warnings++))
        fi
    fi
    
    # Check disk usage
    if command -v df >/dev/null 2>&1; then
        local disk_usage=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
        log_info "Disk Usage: ${disk_usage}%"
        
        if [[ $disk_usage -gt 90 ]]; then
            log_warn "High disk usage: ${disk_usage}%"
            ((warnings++))
        fi
    fi
    
    # Check load average
    if [[ -f /proc/loadavg ]]; then
        local load_avg=$(cat /proc/loadavg | cut -d' ' -f1-3)
        log_info "Load Average: $load_avg"
    fi
    
    if [[ $warnings -gt 0 ]]; then
        return $EXIT_WARNING
    else
        return $EXIT_SUCCESS
    fi
}

# Check log files
check_log_files() {
    log_info "Checking log files..."
    
    local log_file="${LOG_FILE:-/var/log/poc-funding-reviewer/startup.log}"
    local warnings=0
    
    if [[ -f "$log_file" ]]; then
        local log_size=$(du -h "$log_file" | cut -f1)
        log_info "Log file size: $log_size"
        
        # Check for recent errors
        local recent_errors=$(tail -n 100 "$log_file" | grep -c "ERROR" || echo "0")
        if [[ $recent_errors -gt 0 ]]; then
            log_warn "Found $recent_errors recent errors in log file"
            ((warnings++))
        fi
        
        # Check for recent warnings
        local recent_warnings=$(tail -n 100 "$log_file" | grep -c "WARN" || echo "0")
        if [[ $recent_warnings -gt 5 ]]; then
            log_warn "Found $recent_warnings recent warnings in log file"
            ((warnings++))
        fi
    else
        log_warn "Log file not found at $log_file"
        ((warnings++))
    fi
    
    if [[ $warnings -gt 0 ]]; then
        return $EXIT_WARNING
    else
        return $EXIT_SUCCESS
    fi
}

# Check AWS connectivity
check_aws_connectivity() {
    log_info "Checking AWS connectivity..."
    
    # Check if AWS CLI is available
    if ! command -v aws >/dev/null 2>&1; then
        log_warn "AWS CLI not available, skipping AWS connectivity check"
        return $EXIT_WARNING
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured or invalid"
        return $EXIT_FAILURE
    fi
    
    # Check Bedrock service availability
    local region="${AWS_REGION:-us-west-2}"
    if aws bedrock list-foundation-models --region "$region" >/dev/null 2>&1; then
        log_success "AWS Bedrock connectivity verified"
        return $EXIT_SUCCESS
    else
        log_error "Cannot connect to AWS Bedrock in region $region"
        return $EXIT_FAILURE
    fi
}

# Comprehensive health check
comprehensive_check() {
    log_info "Starting comprehensive health check..."
    
    local overall_status=$EXIT_SUCCESS
    local checks_passed=0
    local checks_warned=0
    local checks_failed=0
    
    # Run all checks
    local checks=(
        "check_server_response"
        "check_process_status"
        "check_system_resources"
        "check_log_files"
        "check_aws_connectivity"
    )
    
    for check in "${checks[@]}"; do
        echo
        if $check; then
            ((checks_passed++))
        else
            local exit_code=$?
            if [[ $exit_code -eq $EXIT_WARNING ]]; then
                ((checks_warned++))
                if [[ $overall_status -eq $EXIT_SUCCESS ]]; then
                    overall_status=$EXIT_WARNING
                fi
            else
                ((checks_failed++))
                overall_status=$EXIT_FAILURE
            fi
        fi
    done
    
    # Summary
    echo
    log_info "Health check summary:"
    log_info "  Passed: $checks_passed"
    log_info "  Warned: $checks_warned"
    log_info "  Failed: $checks_failed"
    
    case $overall_status in
        $EXIT_SUCCESS)
            log_success "Overall health status: HEALTHY"
            ;;
        $EXIT_WARNING)
            log_warn "Overall health status: WARNING"
            ;;
        $EXIT_FAILURE)
            log_error "Overall health status: UNHEALTHY"
            ;;
    esac
    
    return $overall_status
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -u, --url URL          Health check URL (default: $HEALTH_URL)"
    echo "  -t, --timeout SECONDS  Request timeout (default: $TIMEOUT)"
    echo "  -c, --comprehensive    Run comprehensive health check"
    echo "  -h, --help            Show this help message"
    echo
    echo "Exit codes:"
    echo "  0  Success (healthy)"
    echo "  1  Failure (unhealthy)"
    echo "  2  Warning (degraded)"
}

# Main function
main() {
    local comprehensive=false
    
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
            -c|--comprehensive)
                comprehensive=true
                shift
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
    
    if [[ "$comprehensive" == true ]]; then
        comprehensive_check
    else
        check_server_response
    fi
}

# Run main function
main "$@"