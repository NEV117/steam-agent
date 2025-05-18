# Dockerfile for Autogen (ag2) Environment on Linux
FROM python:3.13-slim

# Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to root to install system dependencies
USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
    # Clean up apt cache to reduce image size
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /app

# Create a group and user named 'appuser'
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure proper permissions for the app directory
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to the non-root user
USER appuser

# Default command
CMD ["bash"]