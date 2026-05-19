#!/bin/bash

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="$SCRIPT_DIR/deploy-manifest.json"
PARAMS_FILE="$SCRIPT_DIR/parameters.json"
REPO_URL=""  # Set to your repository URL if using deploy-from-github.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Check if required tools are installed
check_dependencies() {
    command -v aws >/dev/null 2>&1 || error "AWS CLI is required but not installed"
    command -v jq >/dev/null 2>&1 || error "jq is required but not installed"
}

# Validate parameters file
validate_parameters() {
    if [[ ! -f "$PARAMS_FILE" ]]; then
        error "Parameters file not found: $PARAMS_FILE"
    fi
    
    # Check for REQUIRED in core parameters
    local required_params=("StackPrefix" "PublicReachableDomainName")
    for param in "${required_params[@]}"; do
        local value=$(jq -r ".$param // empty" "$PARAMS_FILE")
        if [[ -z "$value" || "$value" == "REQUIRED" ]]; then
            error "Required parameter '$param' not set in $PARAMS_FILE"
        fi
    done
    
    # Validate IdP parameters only if EnableExternalIdP is true
    local enable_idp=$(jq -r '.EnableExternalIdP // "false"' "$PARAMS_FILE")
    if [[ "$enable_idp" == "true" ]]; then
        local idp_required=("IdPProviderName" "IdPClientId" "IdPClientSecret" "IdPOIDCIssuer")
        for param in "${idp_required[@]}"; do
            local value=$(jq -r ".$param // empty" "$PARAMS_FILE")
            if [[ -z "$value" || "$value" == "REQUIRED" ]]; then
                error "Required IdP parameter '$param' not set when EnableExternalIdP=true"
            fi
        done
    fi
    
    # Validate domain name format
    domain=$(jq -r '.PublicReachableDomainName' "$PARAMS_FILE")
    if [[ ! "$domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](\.[a-zA-Z]{2,})+$ ]]; then
        error "Invalid domain name format: $domain"
    fi
}

# Get parameter value from parameters.json
get_parameter() {
    local param_name="$1"
    jq -r ".$param_name // empty" "$PARAMS_FILE"
}

# Get export value by suffix (e.g., "cognito-auth-domain-name")
get_export() {
    local suffix="$1"
    local stack_prefix=$(get_parameter "StackPrefix")
    local export_name="${stack_prefix}-${suffix}"
    aws cloudformation list-exports --query "Exports[?Name=='${export_name}'].Value" --output text
}

# Get parameter value - checks exports first (for Export:xxx format), then parameters.json
get_param_or_export() {
    local param_name="$1"
    local param_value=$(get_parameter "$param_name")
    
    # If value starts with "Export:", look it up in exports
    if [[ "$param_value" == Export:* ]]; then
        local export_suffix="${param_value#Export:}"
        param_value=$(get_export "$export_suffix")
    fi
    
    echo "$param_value"
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

# Generate CloudFront key pair
generate_cloudfront_keys() {
    local private_key_file="$SCRIPT_DIR/cloudfront-private-key.pem"
    local public_key_file="$SCRIPT_DIR/cloudfront-public-key.pem"
    
    log "Generating CloudFront RSA-2048 key pair..."
    openssl genrsa -out "$private_key_file" 2048
    openssl rsa -pubout -in "$private_key_file" -out "$public_key_file"
    chmod 600 "$private_key_file"
    log "CloudFront key pair generated"
}

# Clean up local key files
cleanup_cloudfront_keys() {
    local private_key_file="$SCRIPT_DIR/cloudfront-private-key.pem"
    local public_key_file="$SCRIPT_DIR/cloudfront-public-key.pem"
    
    if [[ -f "$private_key_file" ]]; then
        rm -f "$private_key_file"
        log "Cleaned up private key file"
    fi
    if [[ -f "$public_key_file" ]]; then
        rm -f "$public_key_file"
        log "Cleaned up public key file"
    fi
}

# Build CloudFormation parameters array
build_cf_parameters() {
    local template_params="$1"
    local cf_params=""
    
    echo "$template_params" | jq -r 'keys[]' | while read -r param; do
        case "$param" in
            "CloudFrontPrivateKey")
                value=$(cat "$SCRIPT_DIR/cloudfront-private-key.pem")
                ;;
            "CloudFrontPublicKey")
                value=$(cat "$SCRIPT_DIR/cloudfront-public-key.pem")
                ;;
            *)
                value=$(get_parameter "$param")
                ;;
        esac
        
        if [[ -n "$value" && "$value" != "null" ]]; then
            if [[ -n "$cf_params" ]]; then
                cf_params="$cf_params "
            fi
            cf_params="${cf_params}ParameterKey=$param,ParameterValue=$value"
        fi
    done
    
    echo "$cf_params"
}

# Check for NS delegation requirement
check_ns_delegation() {
    local domain=$(get_parameter "PublicReachableDomainName")
    local stack_prefix=$(get_parameter "StackPrefix")
    
    # Check if this is a subdomain (more than 2 parts)
    local domain_parts=$(echo "$domain" | tr '.' '\n' | wc -l)
    if [[ $domain_parts -gt 2 ]]; then
        log "Detected subdomain: $domain"
        
        # Get NS records from Route53
        local hosted_zone_id=$(aws cloudformation describe-stacks --stack-name "${stack_prefix}-01-dns" --query 'Stacks[0].Outputs[?OutputKey==`SeraHostedZoneId1`].OutputValue' --output text)
        local ns_records=$(aws route53 get-hosted-zone --id "$hosted_zone_id" --query 'DelegationSet.NameServers[]' --output text)
        
        echo ""
        echo "========================================="
        echo "NS RECORDS FOR DELEGATION:"
        echo "========================================="
        echo "Add these NS records to your parent domain for: $domain"
        echo ""
        for ns in $ns_records; do
            echo "  $ns."
        done
        echo ""
        echo "========================================="
        echo ""
        echo "Steps to complete delegation:"
        echo "1. Copy the NS records above"
        echo "2. Add them to your parent domain's DNS"
        echo "3. Wait for DNS propagation (5-15 minutes)"
        echo ""
        echo "DEPLOYMENT PAUSED - Waiting for NS delegation..."
        echo "Press Enter to continue once NS records are configured..."
        read -r < /dev/tty
        log "Continuing deployment after NS delegation confirmation"
    fi
}

# Upload deployment zip to S3
upload_deployment_zip() {
    local branch_name=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD)
    local zip_name="SERA-${branch_name}.zip"
    local zip_path="$SCRIPT_DIR/$zip_name"
    local stack_prefix=$(get_parameter "StackPrefix")
    local bucket_name="${stack_prefix}-code-artifacts-$(aws sts get-caller-identity --query Account --output text)"
    
    log "Uploading $zip_name to S3 bucket: $bucket_name"
    aws s3 cp "$zip_path" "s3://$bucket_name/$zip_name"
    
    log "Deployment zip uploaded successfully"
    rm -f "$zip_path"  # Clean up local zip file
}

# Ensure deployment zip exists in S3, create/upload if missing
ensure_deployment_zip() {
    local branch_name=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD)
    local zip_name="SERA-${branch_name}.zip"
    local stack_prefix=$(get_parameter "StackPrefix")
    local bucket_name="${stack_prefix}-code-artifacts-$(aws sts get-caller-identity --query Account --output text)"
    
    # Check if zip exists in S3
    if aws s3 ls "s3://$bucket_name/$zip_name" >/dev/null 2>&1; then
        log "Deployment zip $zip_name already exists in S3"
    else
        log "Deployment zip not found in S3, creating..."
        create_deployment_zip
        upload_deployment_zip
    fi
}

# Deploy a single stack
deploy_stack() {
    local stack_name_template="$1"
    local template_file="$2"
    local template_params="$3"
    
    # Replace ${StackPrefix} in stack name
    local stack_prefix=$(get_parameter "StackPrefix")
    local stack_name="${stack_name_template//\$\{StackPrefix\}/$stack_prefix}"
    
    # Check if stack already exists and is complete
    local status=$(aws cloudformation describe-stacks --stack-name "$stack_name" --query 'Stacks[0].StackStatus' --output text 2>/dev/null)
    if [[ "$status" == "CREATE_COMPLETE" || "$status" == "UPDATE_COMPLETE" ]]; then
        log "Stack $stack_name already exists and is complete - skipping"
        
        # Ensure deployment zip exists after S3 stack
        if [[ "$template_file" == "04-s3.yaml" ]]; then
            ensure_deployment_zip
        fi
        return 0
    fi
    
    # Generate keys before CloudFront stack
    if [[ "$template_file" == "05-cloudfront.yaml" ]]; then
        generate_cloudfront_keys
    fi
    
    log "Deploying stack: $stack_name"
    
    # Build parameters
    local cf_params=""
    local params_file=""
    if [[ "$template_params" != "{}" ]]; then
        local param_names=($(echo "$template_params" | jq -r 'keys[]'))
        local has_keys=false
        
        # Check if we need to handle keys
        for param_name in "${param_names[@]}"; do
            if [[ "$param_name" == "CloudFrontPrivateKey" || "$param_name" == "CloudFrontPublicKey" ]]; then
                has_keys=true
                break
            fi
        done
        
        if [[ "$has_keys" == true ]]; then
            # Create temporary parameters file for keys
            params_file=$(mktemp)
            local params_json="["
            local first=true
            
            for param_name in "${param_names[@]}"; do
                local param_value
                
                case "$param_name" in
                    "CloudFrontPrivateKey")
                        param_value=$(cat "$SCRIPT_DIR/cloudfront-private-key.pem")
                        ;;
                    "CloudFrontPublicKey")
                        param_value=$(cat "$SCRIPT_DIR/cloudfront-public-key.pem")
                        ;;
                    *)
                        param_value=$(get_param_or_export "$param_name")
                        ;;
                esac
                
                if [[ -n "$param_value" || "$param_value" == "" ]]; then
                    if [[ "$first" != true ]]; then
                        params_json="$params_json,"
                    fi
                    params_json="$params_json{\"ParameterKey\":\"$param_name\",\"ParameterValue\":$(echo "$param_value" | jq -Rs .)}"
                    first=false
                fi
            done
            params_json="$params_json]"
            echo "$params_json" > "$params_file"
        else
            # Use command line parameters for non-key stacks
            for param_name in "${param_names[@]}"; do
                local param_value=$(get_param_or_export "$param_name")
                
                if [[ -n "$param_value" && "$param_value" != "null" && "$param_value" != "" ]]; then
                    if [[ -n "$cf_params" ]]; then
                        cf_params="$cf_params "
                    fi
                    cf_params="${cf_params}ParameterKey=$param_name,ParameterValue=\"$param_value\""
                fi
            done
        fi
    fi
    
    # Deploy stack
    local deploy_cmd="aws cloudformation create-stack --stack-name $stack_name --template-body file://$SCRIPT_DIR/$template_file --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM"
    
    if [[ -n "$params_file" ]]; then
        deploy_cmd="$deploy_cmd --parameters file://$params_file"
    elif [[ -n "$cf_params" ]]; then
        deploy_cmd="$deploy_cmd --parameters $cf_params"
    fi
    
    eval "$deploy_cmd"
    
    # Clean up temporary parameters file
    if [[ -n "$params_file" ]]; then
        rm -f "$params_file"
    fi
    
    log "Waiting for stack $stack_name to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$stack_name"
    
    if [[ $? -eq 0 ]]; then
        log "Stack $stack_name deployed successfully"
        
        # Ensure deployment zip exists after S3 stack
        if [[ "$template_file" == "04-s3.yaml" ]]; then
            ensure_deployment_zip
        fi
        
        # Clean up keys after CloudFront stack
        if [[ "$template_file" == "05-cloudfront.yaml" ]]; then
            cleanup_cloudfront_keys
        fi
        
        # Check for NS delegation after Route53 stack
        if [[ "$template_file" == "01-route53.yaml" ]]; then
            check_ns_delegation
        fi
    else
        error "Stack $stack_name deployment failed"
    fi
}

# Main deployment function
deploy_sera() {
    log "Starting SERA deployment..."
    
    check_dependencies
    validate_parameters
    
    # Read deployment manifest
    if [[ ! -f "$MANIFEST_FILE" ]]; then
        error "Deployment manifest not found: $MANIFEST_FILE"
    fi
    
    # Deploy each stack in order
    jq -c '.deployment_order[]' "$MANIFEST_FILE" | while read -r stack; do
        local name=$(echo "$stack" | jq -r '.name')
        local template=$(echo "$stack" | jq -r '.template')
        local parameters=$(echo "$stack" | jq -r '.parameters')
        
        deploy_stack "$name" "$template" "$parameters"
    done
    
    log "SERA deployment completed successfully!"
    
    # Configure Bedrock Model Invocation Logging
    local stack_prefix=$(get_parameter "StackPrefix")
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local bucket_name="${stack_prefix}-bedrock-invocation-logs-${account_id}"
    
    log "Configuring Bedrock Model Invocation Logging to S3 bucket: $bucket_name"
    aws bedrock put-model-invocation-logging-configuration \
      --logging-config "{
        \"s3Config\": {
          \"bucketName\": \"${bucket_name}\",
          \"keyPrefix\": \"invocation-logs/\"
        },
        \"textDataDeliveryEnabled\": true,
        \"imageDataDeliveryEnabled\": true,
        \"embeddingDataDeliveryEnabled\": false
      }" && log "Bedrock invocation logging configured successfully" || warn "Failed to configure Bedrock invocation logging - configure manually in Bedrock Settings"
    
    # Setup Nova Act workflow
    log "Setting up Nova Act workflow..."
    bash "$SCRIPT_DIR/setup-nova-act.sh" "$stack_prefix" || warn "Failed to setup Nova Act - run setup-nova-act.sh manually"
    
    log "Next steps:"
    log "1. Add users to Cognito User Pool"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        deploy_sera
        ;;
    "validate")
        check_dependencies
        validate_parameters
        log "Validation passed!"
        ;;
    "help")
        echo "Usage: $0 [deploy|validate|help]"
        echo "  deploy   - Deploy all SERA stacks (default)"
        echo "  validate - Validate parameters and dependencies"
        echo "  help     - Show this help message"
        ;;
    *)
        error "Unknown command: $1. Use 'help' for usage information."
        ;;
esac
