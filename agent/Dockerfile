# Cloud Run image: ADK web UI + agent + headless Chromium for chrome-devtools-mcp + demo page.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends chromium nodejs npm fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g chrome-devtools-mcp@1.13.0 && npm cache clean --force
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY copilot ./copilot
COPY demo ./demo
ENV COPILOT_HEADLESS=1 CHROME_PATH=/usr/bin/chromium PATH="/app/.venv/bin:$PATH"
# Demo bank page on :8765 inside the container; the agent opens http://localhost:8765.
CMD python -m http.server 8765 --directory demo & exec adk web --host 0.0.0.0 --port ${PORT:-8080} .
