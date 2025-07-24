
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import requests


app = FastAPI()

# Use OLLAMA_URL from environment, fallback to localhost
OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = "nomic-embed-text"

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    vectors: List[List[float]]

@app.post("/embed", response_model=EmbedResponse)
def embed_texts(req: EmbedRequest):
    vectors = []
    try:
        for text in req.texts:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": text,
                "options": {
                    "temperature": 0
                }
            }
            full_url = f"{OLLAMA_BASE_URL}/api/embeddings"
            print(f"Sending request to URL: {full_url}")
            print(f"Sending request to Ollama with payload: {payload}")  # Log the request payload
            response = requests.post(full_url, json=payload)
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Ollama Response for '{text[:50]}...': {response.text}")  # Log the raw response
            data = response.json()
            print(f"Parsed response data: {data}")  # Log the parsed data
            # Ollama returns {"embedding": [...]} or {"embeddings": [...]}
            embedding = data.get("embedding") or (data.get("embeddings", [None])[0])
            if not embedding:
                print(f"Ollama Response Data: {data}")  # Log the parsed data
                raise HTTPException(status_code=500, detail=f"No embedding returned from Ollama for text: {text[:50]}...")
            vectors.append(embedding)
        return {"vectors": vectors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health():
    return {"status": "ok"}
