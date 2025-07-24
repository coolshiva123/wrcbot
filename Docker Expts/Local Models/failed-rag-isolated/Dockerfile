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
    llama-index==0.9.43 \
    langchain==0.0.352 \
    transformers \
    sentence-transformers \
    chromadb==0.4.22 \
    pdfplumber \
    python-docx \
    docx2txt \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    typing-extensions>=4.5.0 \
    nltk

# Set environment variables
ENV ANONYMIZED_TELEMETRY=False
ENV NLTK_DATA=/usr/local/share/nltk_data

# Set up NLTK data
RUN python -c "import nltk; nltk.download('punkt', download_dir='/usr/local/share/nltk_data')" && \
    chmod -R 777 /usr/local/share/nltk_data

# Create data directories with proper permissions
RUN mkdir -p /app/data/documents /app/data/chroma_db && \
    chmod -R 777 /app/data

# Expose the API port
EXPOSE 8000

# Copy application files
COPY . /app

# Run the FastAPI server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
