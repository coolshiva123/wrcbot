# RAG-enabled Errbot with LlamaIndex

This is a RAG-enabled Errbot implementation that can index and answer questions about your documents using LlamaIndex and Ollama.

## Features

- Document support for PDF, DOCX, and TXT files
- Confluence integration for directly indexing Confluence pages
- Persistent vector storage with ChromaDB
- Integration with Ollama for LLM responses
- Slack interface through Errbot

## Setup

1. Place your documents in `src/plugins/data/documents/`
2. Update `src/config.py` with your:
   - Slack credentials
   - Confluence credentials (if using)
   - Ollama settings

3. Build and run:
```bash
# Build the image
docker build -t ragbot:0.1 .

# Create network if not exists
docker network create wrcnet

# Run Ollama container
docker run -d --name ol --network wrcnet ollama/ollama
docker exec -it ol ollama pull llama3

# Run RAG bot
docker run -d --name ragbot --network wrcnet \
  -v $(pwd)/src/plugins/data:/app/src/plugins/data \
  -e OLLAMA_URL=http://ol:11434 \
  ragbot:0.1
```

## Usage

In Slack:

1. Load documents:
```
!rag_load_docs
```

2. Query your documents:
```
!rag_query What is the architecture of our system?
```

3. Add Confluence pages:
```
!rag_add_confluence SPACE_KEY PAGE_ID1 PAGE_ID2
```

## Directory Structure

```
.
├── Dockerfile
├── src/
│   ├── config.py
│   └── plugins/
│       ├── rag_plugin.py
│       └── data/
│           ├── documents/    # Place your docs here
│           └── chroma_db/    # Vector store data
```

## Requirements

- Python 3.11+
- Ollama
- Slack Workspace
- Confluence instance (optional)
