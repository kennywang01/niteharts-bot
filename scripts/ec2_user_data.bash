#!/bin/bash
set -e
exec > >(tee /var/log/user-data.log | logger -t user-data) 2>&1

AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="701154485405"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/niteharts/niteharts-docker:latest"
SQS_QUEUE_URL="https://sqs.us-east-2.amazonaws.com/$AWS_ACCOUNT_ID/niteharts-configs"
TWOCAPTCHA_API_KEY="@@TWOCAPTCHA_API_KEY@@"
EVENT_URL="@@EVENT_URL@@"
DEPLOY_ID="@@DEPLOY_ID@@"
S3_BUCKET="@@S3_BUCKET@@"
FORM_INPUTS_PATH="/home/ec2-user/form_inputs.json"

# Install Docker (Amazon Linux 2023)
echo "Installing Docker..."
dnf install -y docker
systemctl start docker
systemctl enable docker
echo "Docker installed: $(docker --version)"

# Get instance ID from EC2 metadata (IMDSv2)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# Claim one config from SQS queue
echo "Claiming config from SQS..."
MESSAGE=$(aws sqs receive-message \
  --queue-url $SQS_QUEUE_URL \
  --region $AWS_REGION \
  --max-number-of-messages 1 \
  --visibility-timeout 300 \
  --output json)

if [ -z "$MESSAGE" ] || [ "$(echo $MESSAGE | jq '.Messages | length')" -eq 0 ]; then
  echo "ERROR: No config available in SQS queue"
  exit 1
fi

RECEIPT_HANDLE=$(echo $MESSAGE | jq -r '.Messages[0].ReceiptHandle')
echo $MESSAGE | jq -r '.Messages[0].Body' > $FORM_INPUTS_PATH
echo "Config written to $FORM_INPUTS_PATH"

# Delete the message so no other instance claims it
aws sqs delete-message \
  --queue-url $SQS_QUEUE_URL \
  --region $AWS_REGION \
  --receipt-handle "$RECEIPT_HANDLE"
echo "Message deleted from queue"

# Authenticate Docker with ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Pull the latest image
echo "Pulling Docker image..."
docker pull $ECR_URI

# Run the container
echo "Running niteharts..."
docker run --rm \
  --log-driver=awslogs \
  --log-opt awslogs-region=$AWS_REGION \
  --log-opt awslogs-group=/niteharts \
  --log-opt awslogs-stream=$INSTANCE_ID \
  -e AWS_REGION=$AWS_REGION \
  -e TWOCAPTCHA_API_KEY=$TWOCAPTCHA_API_KEY \
  -e EVENT_URL=$EVENT_URL \
  -e DEPLOY_ID=$DEPLOY_ID \
  -e S3_BUCKET=$S3_BUCKET \
  -v $FORM_INPUTS_PATH:/app/form_inputs.json \
  $ECR_URI
