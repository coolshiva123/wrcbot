# HuggingFaceXformer Summarization API

This Dockerized FastAPI app serves the `google/pegasus-xsum` model for text summarization.

## Usage

### 1. Build the Docker image
```sh
cd Docker\ Expts/Local\ Models/HuggingFaceXformer
docker build -t huggingface-xformer .
```

### 2. Run the container
```sh
docker run -p 8000:8000 huggingface-xformer
```

### 3. Test the API
```sh
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your long text here."}'
```

**Optional parameters:** `max_length`, `min_length`, `do_sample`

## Notes
- The model will use GPU if available, otherwise CPU.
- You can change the model in `app.py` if needed.
- For large texts, chunk and summarize in pieces (see summarization best practices).
