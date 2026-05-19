#!/bin/bash

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$SCRIPT_DIR/parameters.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Create deployment zip file
create_deployment_zip() {
    local branch_name=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD)
    local zip_name="SERA-${branch_name}.zip"
    local folder_name="SERA-${branch_name}"
    local zip_path="$SCRIPT_DIR/$zip_name"
    local temp_dir=$(mktemp -d)
    local repo_url=$(git -C "$(dirname "$SCRIPT_DIR")" remote get-url origin)
    
    log "Creating deployment zip: $zip_name"
    
    # Clone fresh copy to temp directory
    cd "$temp_dir"
    rm -rf "$folder_name"
    git clone "$repo_url" "$folder_name"
    cd "$folder_name"
    git checkout -b "$branch_name" "origin/$branch_name" 2>/dev/null || git checkout "$branch_name"
    cd ..
    
    # Create zip with proper folder structure
    zip -r "$zip_path" "$folder_name" -x "$folder_name/.git/*" "$folder_name/.amazonq/*" "$folder_name/.DS_Store" "$folder_name/node_modules/*" "$folder_name/__pycache__/*" "$folder_name/*.pyc" "$folder_name/.venv/*" "$folder_name/.kiro/*"
    
    # Cleanup temp directory and return to script dir
    rm -rf "$temp_dir"
    cd "$SCRIPT_DIR"
    
    # Update SeraVersion in parameters.json
    local temp_params=$(mktemp)
    jq --arg version "SERA-${branch_name}" '.SeraVersion = $version' "$PARAMS_FILE" > "$temp_params"
    mv "$temp_params" "$PARAMS_FILE"
    
    log "Updated SeraVersion to: SERA-${branch_name}"
    log "Deployment zip created: $zip_path"
}

# Upload deployment zip to S3
upload_deployment_zip() {
    local branch_name=$(git rev-parse --abbrev-ref HEAD)
    local zip_name="SERA-${branch_name}.zip"
    local zip_path="$SCRIPT_DIR/$zip_name"
    local bucket_name="$(jq -r '.StackPrefix' "$PARAMS_FILE")-code-artifacts-$(aws sts get-caller-identity --query Account --output text)"
    
    log "Uploading $zip_name to S3 bucket: $bucket_name"
    aws s3 cp "$zip_path" "s3://$bucket_name/$zip_name"
    
    log "Deployment zip uploaded successfully"
    rm -f "$zip_path"  # Clean up local zip file
}

# Update compute stack
update_compute_stack() {
    local sera_version=$(jq -r '.SeraVersion' "$PARAMS_FILE")
    local partner_name=$(jq -r '.PartnerName' "$PARAMS_FILE")
    local partner_logo=$(jq -r '.PartnerLogoUrl' "$PARAMS_FILE")
    local partner_email=$(jq -r '.PartnerEmail' "$PARAMS_FILE")
    
    local stack_prefix=$(jq -r '.StackPrefix' "$PARAMS_FILE")
    
    local ami_trigger=$(date +%s)
    
    log "Updating compute stack with version: $sera_version"
    
    aws cloudformation update-stack \
        --stack-name "${stack_prefix}-13-compute" \
        --template-body file://$SCRIPT_DIR/13-compute.yaml \
        --parameters \
            ParameterKey=StackPrefix,UsePreviousValue=true \
            ParameterKey=PublicReachableDomainName,UsePreviousValue=true \
            ParameterKey=SeraVersion,ParameterValue="$sera_version" \
            ParameterKey=PartnerName,ParameterValue="$partner_name" \
            ParameterKey=PartnerLogoUrl,ParameterValue="$partner_logo" \
            ParameterKey=PartnerEmail,ParameterValue="$partner_email" \
            ParameterKey=EnableExternalIdP,UsePreviousValue=true \
            ParameterKey=AMIUpdateTrigger,ParameterValue="$ami_trigger" \
            ParameterKey=LogLevel,UsePreviousValue=true \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
    
    log "Waiting for compute stack update to complete..."
    aws cloudformation wait stack-update-complete --stack-name "${stack_prefix}-13-compute"
    
    log "Compute stack updated successfully!"
}

# Main function
main() {
    log "Starting SERA code update..."
    
    # Check if compute stack exists
    if ! aws cloudformation describe-stacks --stack-name "$(jq -r '.StackPrefix' "$PARAMS_FILE")-13-compute" >/dev/null 2>&1; then
        error "Compute stack does not exist. Run deploy-sera.sh first."
    fi
    
    # Create and upload new deployment zip
    create_deployment_zip
    upload_deployment_zip
    
    # Update compute stack
    update_compute_stack
    
    log "SERA code update completed successfully!"
}

# Run main function
main "$@"
