#!/bin/bash

set -e

# Configuration - UPDATE THESE
GITHUB_REPO="Sera"
GITHUB_BRANCH="deploy"
REPO_URL=""  # Set to your repository URL (e.g., https://github.com/your-org/sera/tree/main/cloudformation)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check dependencies
command -v aws >/dev/null 2>&1 || error "AWS CLI is required"
command -v jq >/dev/null 2>&1 || error "jq is required"
command -v curl >/dev/null 2>&1 || error "curl is required"

# Download manifest and parameters from GitHub
log "Downloading deployment manifest from GitHub..."
curl -s "$REPO_URL/deploy-manifest.json" > deploy-manifest.json || error "Failed to download manifest"

log "Downloading parameters template from GitHub..."
curl -s "$REPO_URL/parameters.json" > parameters-template.json || error "Failed to download parameters"

# Check if local parameters file exists
if [[ ! -f "parameters.json" ]]; then
    log "Creating parameters.json from template - please update with your values"
    cp parameters-template.json parameters.json
    error "Please update parameters.json with your actual values and run again"
fi

# Validate parameters
if grep -q "REQUIRED\|PASTE_YOUR\|example.com" parameters.json; then
    error "Please update all placeholder values in parameters.json"
fi

# Get parameter value
get_parameter() {
    jq -r ".$1 // empty" parameters.json
}

# Deploy stack from GitHub
deploy_stack() {
    local stack_name="$1"
    local template_file="$2"
    local template_params="$3"
    
    log "Deploying stack: $stack_name from $template_file"
    
    # Build parameters
    local cf_params=""
    if [[ "$template_params" != "{}" ]]; then
        while IFS= read -r param; do
            local param_name=$(echo "$param" | jq -r '.key')
            local param_value=$(get_parameter "$param_name")
            
            if [[ -n "$param_value" && "$param_value" != "null" ]]; then
                if [[ -n "$cf_params" ]]; then
                    cf_params="$cf_params "
                fi
                cf_params="${cf_params}ParameterKey=$param_name,ParameterValue=$param_value"
            fi
        done < <(echo "$template_params" | jq -r 'to_entries[]')
    fi
    
    # Deploy from GitHub URL
    local deploy_cmd="aws cloudformation create-stack --stack-name $stack_name --template-url $REPO_URL/$template_file --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM"
    
    if [[ -n "$cf_params" ]]; then
        deploy_cmd="$deploy_cmd --parameters $cf_params"
    fi
    
    eval "$deploy_cmd"
    
    log "Waiting for stack $stack_name to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    
    if [[ $? -eq 0 ]]; then
        log "Stack $stack_name deployed successfully"
    else
        error "Stack $stack_name deployment failed"
    fi
}

# Main deployment
log "Starting SERA deployment from GitHub..."

jq -c '.deployment_order[]' deploy-manifest.json | while read -r stack; do
    name=$(echo "$stack" | jq -r '.name')
    template=$(echo "$stack" | jq -r '.template')
    parameters=$(echo "$stack" | jq -r '.parameters')
    
    deploy_stack "$name" "$template" "$parameters"
done

log "SERA deployment completed successfully!"
