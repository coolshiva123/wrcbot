FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for documents
RUN mkdir -p /app/data/documents

# Copy the application code
COPY . .

# Make sure the script is executable
RUN chmod +x test_sdr.py

ENTRYPOINT ["python"]
