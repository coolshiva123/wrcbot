FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y s3fs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create mount point for S3
RUN mkdir -p /mnt/s3

CMD ["python", "s3_sdr.py"]
