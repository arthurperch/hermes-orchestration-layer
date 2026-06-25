# Hermes MCP Orchestration Server — container
FROM python:3.11-slim

# keep the image lean + non-root
RUN useradd -m -u 10001 syndrax
WORKDIR /app

COPY mcp-requirements.txt .
RUN pip install --no-cache-dir -r mcp-requirements.txt

COPY hermes_mcp_orchestration.py .
COPY orchestration_backend.py .
COPY mcp-test.py .

USER syndrax

# Default to SSE transport in a container (dashboard/backend mode).
# For Hermes Desktop stdio, run the script directly instead of the container.
ENV TRANSPORT=sse \
    SYNDRAX_ENV=prod \
    LOG_LEVEL=INFO

EXPOSE 3000

# Healthcheck hits the status tool path on the backend it proxies.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import os,httpx,sys; \
  sys.exit(0 if httpx.get(os.getenv('SYNDRAX_API_ENDPOINT','http://localhost:8000')+'/v1/status', timeout=4).status_code==200 else 1)" || exit 1

CMD ["python", "-m", "hermes_mcp_orchestration"]
