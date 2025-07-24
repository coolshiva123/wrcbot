# Embedding Service (Ollama + FastAPI)

This microservice provides an `/embed` endpoint to generate vector embeddings for text using Ollama's Llama 3 model.

## Usage

1. **Build the Docker image:**
   ```bash
   docker build -t embedding-svc .
   ```
2. **Run the service (ensure Ollama is running and accessible):**
   ```bash
   docker run --rm -p 8000:8000 embedding-svc
   ```
3. **Send a request:**
   ```bash
   curl -X POST http://localhost:8000/embed \
     -H 'Content-Type: application/json' \
     -d '{"texts": ["Hello world", "Another sentence"]}'
   ```

## Configuration
- The service expects Ollama to be running at `http://localhost:11434` with the `llama3` model available.
- Edit `app.py` to change the model or Ollama endpoint if needed.

## Health Check
- `GET /` returns `{ "status": "ok" }`
