FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final image
FROM python:3.11-slim

WORKDIR /errbot

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY requirements.txt ./

# Create data directory
RUN mkdir -p /errbot/data

# Expose Redis port if needed
EXPOSE 6379

# Command to run the bot (do not start redis-server)
CMD ["errbot", "-c", "src/config.py"]
