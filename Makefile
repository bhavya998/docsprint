.PHONY: install dev server worker migrate test lint clean

install:
	uv sync
	cd ui && npm install

dev:
	docker-compose up -d postgres redis
	uv run alembic upgrade head
	uv run uvicorn docsprint.main:app --reload --port 8000

server:
	docker-compose up -d

worker:
	uv run rq worker doc-processing --url redis://localhost:6379/0

migrate:
	uv run alembic revision --autogenerate -m "$(MSG)"
	uv run alembic upgrade head

test:
	uv run pytest -v

lint:
	uv run ruff check src tests

clean:
	rm -rf .pytest_cache .ruff_cache data/
