#!/bin/bash
set -e

# Configuration
STACK_PREFIX="${1:-sera}"
REGION="${2:-us-east-1}"
WORKFLOW_NAME="sera-pricing-calculator-workflow"
S3_BUCKET="${STACK_PREFIX}-logfiles-$(aws sts get-caller-identity --query Account --output text)"
S3_PREFIX="nova-logs"

echo "Creating Nova Act workflow definition..."
echo "  Name: ${WORKFLOW_NAME}"
echo "  Region: ${REGION}"
echo "  S3 Bucket: ${S3_BUCKET}"
echo "  S3 Prefix: ${S3_PREFIX}"

# Create workflow definition (check if exists first)
if aws nova-act get-workflow-definition --name "${WORKFLOW_NAME}" --region "${REGION}" &>/dev/null; then
  echo "✓ Workflow definition already exists, skipping creation"
else
  if aws nova-act create-workflow-definition \
    --name "${WORKFLOW_NAME}" \
    --description "SERA workflow for automating AWS Pricing Calculator interactions" \
    --export-config "s3BucketName=${S3_BUCKET},s3KeyPrefix=${S3_PREFIX}" \
    --region "${REGION}" 2>&1 | grep -q "ConflictException"; then
    echo "✓ Workflow definition already exists, skipping creation"
  else
    echo "✓ Workflow definition created successfully"
  fi
fi

# Get EC2 role name
echo ""
echo "Finding EC2 IAM role..."
ROLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-12-ec2role" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='SeraEC2InstanceRoleName'].OutputValue" \
  --output text)

if [ -z "$ROLE_NAME" ]; then
  echo "✗ Could not find EC2 role. Please add permissions manually."
  exit 1
fi

echo "  Role: ${ROLE_NAME}"

# Create inline policy for Nova Act permissions
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_DOCUMENT=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "NovaActPermissions",
      "Effect": "Allow",
      "Action": [
        "nova-act:*"
      ],
      "Resource": [
        "arn:aws:nova-act:${REGION}:${ACCOUNT_ID}:workflow-definition/${WORKFLOW_NAME}",
        "arn:aws:nova-act:${REGION}:${ACCOUNT_ID}:workflow-definition/${WORKFLOW_NAME}/*"
      ]
    }
  ]
}
EOF
)

echo ""
echo "Adding Nova Act permissions to EC2 role..."
aws iam put-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-name "NovaActWorkflowAccess" \
  --policy-document "${POLICY_DOCUMENT}"

echo "✓ Permissions added successfully"
echo ""
echo "Setup complete! Nova Act is ready to use with IAM authentication."
echo "Workflow name: ${WORKFLOW_NAME}"
