FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev 2>/dev/null || uv sync

COPY src/ src/
COPY alembic.ini ./
COPY alembic/ alembic/

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn docsprint.main:app --host 0.0.0.0 --port 8000"]
