.PHONY: run login import stats test lint reset-db

run:
	uv run uvicorn app.main:app --reload

login:
	uv run python -m webbrowser http://localhost:8000/auth/login

import:
	curl -s -X POST http://localhost:8000/import | uv run python -m json.tool

stats:
	curl -s http://localhost:8000/library/stats | uv run python -m json.tool

test:
	uv run pytest --cov=app --cov-fail-under=80 tests/ -v

lint:
	uv run ruff check . && uv run ruff format --check .

reset-db:
	rm -f library.db
	@echo "DB supprimée."
