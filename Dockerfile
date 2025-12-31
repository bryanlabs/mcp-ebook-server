# Multi-stage build for MCP Ebook Server

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.12-slim

# Labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/bryanlabs/mcp-ebook-server"
LABEL org.opencontainers.image.description="MCP server providing AI access to ebook libraries"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="MCP Ebook Server"
LABEL org.opencontainers.image.vendor="BryanLabs"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/mcp_ebook_server/ ./mcp_ebook_server/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    EBOOK_LIBRARY_PATH=/ebooks \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8080

# Switch to non-root user
USER appuser

# Expose the MCP server port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/sse')" || exit 1

# Run the MCP server
CMD ["python", "-m", "mcp_ebook_server"]
