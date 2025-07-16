FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpoppler-cpp-dev \
    poppler-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    errbot \
    slack-sdk \
    slackclient \
    ollama \
    llama-index==0.10.28 \
    chromadb==0.4.22 \
    sentence-transformers \
    llama-index-vector-stores-chroma==0.1.2 \
    llama-index-readers-confluence \
    pdfplumber \
    python-docx \
    docx2txt \
    requests

# Copy bot files
COPY . /app

CMD ["errbot", "-c", "src/config.py"]
