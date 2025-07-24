#!/bin/bash

# Clean up any existing containers
echo "Cleaning up..."
docker rm -f sdr-test 2>/dev/null || true

# Create data directory if it doesn't exist
echo "Setting up directories..."
mkdir -p data/documents

# Build the Docker image
echo "Building Docker image..."
docker build -t sdr-test:latest .

# Run the container with volume mount
echo "Running SDR tests..."
docker run --name sdr-test \
  -v "$(pwd)/data:/app/data" \
  sdr-test:latest

# Display the logs
echo -e "\nTest Results:"
docker logs sdr-test
