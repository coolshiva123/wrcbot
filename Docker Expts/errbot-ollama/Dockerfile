FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    build-essential \
    net-tools \
    curl \  
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
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY requirements.txt ./

# Create data directory
RUN mkdir -p /errbot/data

# Create a non-root user and group
RUN addgroup --system errbot && adduser --system --ingroup errbot errbot

# Set ownership for /errbot
RUN chown -R errbot:errbot /errbot

# Switch to non-root user
USER errbot

# Expose Redis port if needed
EXPOSE 6379

# Command to run the bot (do not start redis-server)
CMD ["errbot", "-c", "src/config.py"]
