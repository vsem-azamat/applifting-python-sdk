.PHONY: help install test lint format type-check build clean dev-install

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in development mode
	uv sync

dev-install:  ## Install package and dev dependencies
	uv sync --dev

test:  ## Run tests
	uv run pytest tests/ -v

test-cov:  ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/applifting_python_sdk --cov-report=html

lint:  ## Run linting
	uv run ruff check .

format:  ## Format code
	uv run ruff format .

type-check:  ## Run type checking
	uv run mypy ./src/applifting_python_sdk ./tests

ci:  ## Run all CI checks (lint, format, type-check, test)
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy ./src/applifting_python_sdk ./tests
	uv run pytest tests/ -v

build:  ## Build package
	uv build

clean:  ## Clean build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

pre-commit-install:  ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run:  ## Run pre-commit on all files
	uv run pre-commit run --all-files
