.PHONY: install dev-install test lint format type-check clean serve

install:
	poetry install

dev-install:
	poetry install --with dev
	poetry run pre-commit install

test:
	poetry run pytest tests/unit -v

test-cov:
	poetry run pytest tests/unit \
		--cov=phantom \
		--cov-report=html \
		--cov-report=term-missing

lint:
	poetry run ruff check phantom/ tests/
	poetry run ruff format --check phantom/ tests/

format:
	poetry run ruff check --fix phantom/ tests/
	poetry run ruff format phantom/ tests/

type-check:
	poetry run mypy phantom/ --ignore-missing-imports

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml

serve:
	poetry run phantom serve

docker-build:
	docker build -f containers/app/Dockerfile -t phantom-orchestra:latest .

docker-run:
	docker compose up --build
