# ============================================================================
# Multi-stage Dockerfile for Book Crawler
# ============================================================================

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Stage 2: Runtime stage
FROM python:3.11-slim

# Set metadata
LABEL maintainer="your.email@example.com"
LABEL description="Book Crawler - Web Scraping & Monitoring System"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Add Python packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY api/ ./api/
COPY crawler/ ./crawler/
COPY scheduler/ ./scheduler/
COPY utils/ ./utils/
COPY tests/ ./tests/
COPY run_crawler.py .
COPY run_scheduler.py .
COPY run_api.py .
COPY pytest.ini .

# Create directories for logs and reports
RUN mkdir -p logs data/reports

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "run_api.py"]
