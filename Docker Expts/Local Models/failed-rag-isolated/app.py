from fastapi import FastAPI, UploadFile, File
from llama_index import (
    LLMPredictor,
    ServiceContext,
    SimpleDirectoryReader, 
    Document,
    get_response_synthesizer,
    VectorStoreIndex,
    StorageContext
)
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from llama_index.vector_stores import ChromaVectorStore

# Configure to use local embeddings with no LLM
embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=None)  # Disable LLM since we're not using OpenAI

import uvicorn
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
import chromadb
import os
import shutil
from typing import List, Optional
from pydantic import BaseModel

# Create FastAPI app
app = FastAPI(
    title="RAG API",
    description="API for RAG (Retrieval Augmented Generation)",
    version="0.1.0",
    root_path="/",
)

# Make sure temp directories exist
os.makedirs("/tmp", exist_ok=True)

# Initialize ChromaDB and vector store
DOCS_DIR = "/app/data/documents"
DB_DIR = "/app/data/chroma_db"
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# Initialize ChromaDB client
print(f"Initializing ChromaDB with DB_DIR: {DB_DIR}")
try:
    # Use EphemeralClient to avoid telemetry issues
    chroma_client = chromadb.EphemeralClient()

    # Create or get collection
    print("Creating/getting collection...")
    collection = chroma_client.get_or_create_collection(name="document_store")

    # Initialize vector store
    print("Initializing vector store...")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    print("Vector store initialized successfully")
    
except Exception as e:
    print(f"Error initializing ChromaDB: {str(e)}")
    import traceback
    print(traceback.format_exc())
    raise

# Global index variable
index = None

def load_or_create_index():
    """Load existing index or create new one if documents exist"""
    global index
    try:
        documents = SimpleDirectoryReader(DOCS_DIR).load_data()
        if documents:
            index = VectorStoreIndex.from_documents(
                documents,
                vector_store=vector_store
            )
            print(f"Loaded {len(documents)} documents into the index")
        else:
            print("No documents found to index")
            index = None
    except Exception as e:
        print(f"Error loading documents: {str(e)}")
        index = None

# Load index on startup
load_or_create_index()

@app.get("/")
def read_root():
    """Root endpoint for health check"""
    return {"status": "ok"}

class Query(BaseModel):
    text: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document (PDF, DOCX, or TXT) for indexing"""
    try:
        print(f"Uploading file {file.filename}...")
        # Save the file
        file_path = os.path.join(DOCS_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        print(f"File saved to {file_path}")
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise Exception(f"File not saved properly to {file_path}")
            
        # List all files in directory
        print(f"Files in {DOCS_DIR}:", os.listdir(DOCS_DIR))
        
        # Reload the index
        print("Reloading index...")
        load_or_create_index()
        
        if not index:
            raise Exception("Index not created after file upload")
            
        return {"message": f"Successfully uploaded and indexed {file.filename}"}
    except Exception as e:
        print(f"Error in upload: {str(e)}")
        return {"error": str(e)}

@app.post("/query")
async def query_documents(query: Query):
    """Query the RAG system"""
    if not index:
        return {"error": "No documents have been indexed yet"}
    
    try:
        query_engine = index.as_query_engine()
        response = query_engine.query(query.text)
        return {"response": str(response)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/reload")
async def reload_index():
    """Reload and reindex all documents"""
    try:
        load_or_create_index()
        return {"message": "Index reloaded successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/status")
async def get_status():
    """Get the current status of the RAG system"""
    try:
        doc_count = len(os.listdir(DOCS_DIR))
        return {
            "status": "operational",
            "indexed_documents": doc_count,
            "has_index": index is not None
        }
    except Exception as e:
        return {"error": str(e)}
