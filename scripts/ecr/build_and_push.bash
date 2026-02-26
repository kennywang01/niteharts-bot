#!/bin/bash
set -e

AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="701154485405"
ECR_REPO="niteharts/niteharts-docker"
IMAGE_TAG="latest"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"

echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Building Docker image..."
docker build -t niteharts .

echo "Tagging image..."
docker tag niteharts:latest $ECR_URI

echo "Pushing to ECR..."
docker push $ECR_URI

echo "Done: $ECR_URI"
