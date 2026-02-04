FROM python:3.11-slim

# Install FFmpeg
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY static/ ./static/

# Create directories
RUN mkdir -p /tmp/poster_cache /output

# Non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /tmp/poster_cache /output
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
