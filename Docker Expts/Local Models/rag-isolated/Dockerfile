FROM python:3.11-slim

# System dependencies for PDF and DOCX
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpoppler-cpp-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    llama-index==0.10.28 \
    chromadb==0.4.22 \
    sentence-transformers \
    pdfplumber \
    python-docx \
    docx2txt \
    llama-index-vector-stores-chroma==0.1.2 \
    requests \
    fastapi \
    uvicorn

# Create data directories
RUN mkdir -p data/documents data/chroma_db

# Copy application files
COPY . /app

# Expose the API port
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
