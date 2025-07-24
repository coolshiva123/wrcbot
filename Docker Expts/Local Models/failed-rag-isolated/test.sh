#!/bin/bash

# Clean up and create directories
echo "Cleaning up directories..."
rm -rf data/chroma_db data/documents
mkdir -p data/documents data/chroma_db
chmod -R 777 data  # Ensure container has write permissions

# Create a sample document
echo "This is a sample document for testing the RAG system.

It contains multiple paragraphs to demonstrate the indexing and querying capabilities.

The RAG system uses LlamaIndex for document processing and ChromaDB for vector storage.

This architecture allows for efficient retrieval and answering of questions about the document content." > data/documents/sample.txt

# Clean up any existing container and rebuild
echo "Cleaning up..."
docker rm -f rag-service || true

# Build the Docker image
echo "Building Docker image..."
docker build -t rag-service:0.1 .

# Run the container
echo "Starting RAG service..."
docker run -d --name rag-service \
  -p 8001:8001 \
  -v "$(pwd)/data:/app/data" \
  rag-service:0.1

# Wait for the service to start
echo "Waiting for service to start..."
sleep 15  # Increased wait time to allow full startup

# Verify service is up
echo "Verifying service is up..."
curl -f "http://127.0.0.1:8001" || {
    echo "Service not responding"
    docker logs rag-service
    exit 1
}

# Test document upload
echo "Testing document upload..."
curl -X POST "http://127.0.0.1:8001/upload" \
  -H "accept: application/json" \
  -F "file=@data/documents/sample.txt"

# Wait for indexing to complete
echo "Waiting for indexing to complete..."
sleep 5

# Check logs
echo "Container logs:"
docker logs rag-service

# Test querying
echo -e "\n\nTesting query..."
curl -X POST "http://127.0.0.1:8001/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is this document about?"}'

# Check status
echo -e "\n\nChecking status..."
curl "http://127.0.0.1:8001/status" \
  -H "accept: application/json"
