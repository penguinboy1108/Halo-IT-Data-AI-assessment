.PHONY: install prepare db test lint typecheck run docker-up

install:
	pip install -e ".[dev]"

prepare:
	python src/prepare_data.py

db:
	python scripts/build_duckdb.py

test:
	pytest

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy agent

run:
	streamlit run agent/app.py

docker-up:
	docker compose up --build
