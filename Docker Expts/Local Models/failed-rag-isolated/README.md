# RAG Service API

This is a standalone RAG (Retrieval Augmented Generation) service that provides a REST API for document indexing and querying.

## Features

- Upload and index PDF, DOCX, and TXT files
- Query indexed documents
- Persistent vector storage with ChromaDB
- RESTful API interface

## Setup

1. Build the Docker image:
```bash
docker build -t rag-service:0.1 .
```

2. Run the container:
```bash
docker run -d --name rag-service \
  --network wrcnet \
  -p 8000:8000 \
  -v "$(pwd)"/data:/app/data \
  rag-service:0.1
```

## API Endpoints

### Upload a Document
```bash
# For PDF files
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -F "file=@your-document.pdf"

# For TXT files
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -F "file=@your-document.txt"

# For DOCX files
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -F "file=@your-document.docx"
```

### Query Documents
```bash
curl -X POST "http://localhost:8000/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the architecture of the system?"}'
```

### Reload Index
```bash
curl -X POST "http://localhost:8000/reload" \
  -H "accept: application/json"
```

### Check Status
```bash
curl "http://localhost:8000/status" \
  -H "accept: application/json"
```

## Directory Structure

```
.
├── Dockerfile
├── app.py
├── README.md
└── data/
    ├── documents/    # Place your docs here
    └── chroma_db/    # Vector store data
```

## Test Script

Save this as `test.sh`:
```bash
#!/bin/bash

# Test document upload
echo "Testing document upload..."
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/documents/sample.txt"

# Test querying
echo -e "\n\nTesting query..."
curl -X POST "http://localhost:8000/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is this document about?"}'

# Check status
echo -e "\n\nChecking status..."
curl "http://localhost:8000/status" \
  -H "accept: application/json"
```
