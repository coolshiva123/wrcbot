#!/bin/bash

# WRCPilot01 Golden Copy Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on any error

echo "🚀 Deploying WRCPilot01 Golden Copy..."

# Build the Docker image
echo "📦 Building Docker image wrcbot:0.7..."
docker build -t wrcbot:0.7 .

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker stop wrcbot_golden 2>/dev/null || true
docker rm wrcbot_golden 2>/dev/null || true

# Run the new container
echo "▶️ Starting new container..."
docker run -d --name wrcbot_golden wrcbot:0.7

# Wait for startup
echo "⏳ Waiting for bot to start..."
sleep 5

# Check container status
echo "📊 Container status:"
docker ps | grep wrcbot_golden || echo "❌ Container not running!"

# Show recent logs
echo "📋 Recent logs:"
docker logs wrcbot_golden --tail 10

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Available commands:"
echo "  docker logs wrcbot_golden --tail 50    # View logs"
echo "  docker stop wrcbot_golden              # Stop bot"
echo "  docker start wrcbot_golden             # Start bot"
echo ""
echo "🧪 Test the bot in Slack:"
echo "  @bot collect_name    # Test name collection"
echo "  @bot mypriorlife     # Test prior life collection"
echo "  @bot alive           # Health check"
