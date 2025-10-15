FROM ghcr.io/astral-sh/uv:bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        libpq-dev \
        gcc && \
    rm -rf /var/lib/apt/lists/*

RUN uv install --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]