# logpress - Semantic Log Compression System
# Production Docker Image

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    git \
    bash \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (including rich for interactive CLI)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY logpress/ logpress/
COPY setup.py .
COPY evaluation/ evaluation/
COPY scripts/ scripts/

# Install logpress package in editable mode
RUN pip install -e .

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create directories for data
RUN mkdir -p /app/data /app/evaluation/compressed /app/evaluation/results

# Set Python path
ENV PYTHONPATH=/app

# Default command - interactive CLI
CMD ["python", "-m", "logpress.cli.interactive"]
