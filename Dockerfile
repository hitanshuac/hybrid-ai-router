# Hybrid AI Router — Hugging Face Spaces / Cloud Deployment
# Port 7860 (HF default), non-root user, production-ready
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 appuser

WORKDIR /home/appuser/app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create writable data directory for DuckDB telemetry
RUN mkdir -p /home/appuser/app/data && chown -R appuser:appuser /home/appuser/app/data

USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
