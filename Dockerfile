FROM python:3.13-slim

# Pin uv; Git is needed to install the locked toon-format dependency.
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

# Keep source here: FileSystemProvider discovers tools under /app/src.
COPY pyproject.toml uv.lock .python-version README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev \
    && useradd --create-home --uid 10001 app

USER app
EXPOSE 8080
CMD ["/app/.venv/bin/python", "-m", "src.server"]
