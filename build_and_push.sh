set -e

echo "Initializing AWS session..."
aws sso login --profile personal-aws

echo "Initializing ECR repository..."
aws ecr get-login-password \
  --region ap-southeast-1 \
  --profile personal-aws | \
  docker login --username AWS --password-stdin 958193682749.dkr.ecr.ap-southeast-1.amazonaws.com

# Build the Docker image with correct flags for Lambda compatibility
echo "Building Docker image..."
docker build --no-cache -t ai-agent-image .

# Tag the image for ECR
echo "Tagging image..."
docker tag ai-agent-image:latest 958193682749.dkr.ecr.ap-southeast-1.amazonaws.com/ai-agent-image:latest

# Push the image to ECR
echo "Pushing image to ECR..."
docker push 958193682749.dkr.ecr.ap-southeast-1.amazonaws.com/ai-agent-image:latest

echo "Build and push completed successfully!" 