# Multi-stage build for lighter final image
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set working directory
WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage - minimal Alpine image
FROM python:3.11-alpine

# Install only runtime dependencies
RUN apk add --no-cache \
    libffi \
    openssl \
    curl \
    jq \
    && addgroup -g 1000 errbot \
    && adduser -D -u 1000 -G errbot errbot

# Copy installed packages from builder
COPY --from=builder /root/.local /home/errbot/.local

# Create data directory and set ownership
RUN mkdir -p /errbot/data && chown -R errbot:errbot /errbot

# Set working directory
WORKDIR /errbot

# Copy application code and set ownership
COPY --chown=errbot:errbot src/ ./src/

# Switch to non-root user
USER errbot

# Add local packages to PATH
ENV PATH="/home/errbot/.local/bin:$PATH"

# Command to run the bot
CMD ["errbot", "-c", "src/config.py"]
