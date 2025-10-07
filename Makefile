.PHONY: help install install-dev format lint test clean run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest
	pre-commit install

format: ## Format code with black and isort
	black elasticache_scanner/ tests/
	isort elasticache_scanner/ tests/

lint: ## Run linting checks
	flake8 elasticache_scanner/ tests/
	mypy elasticache_scanner/
	black --check elasticache_scanner/ tests/
	isort --check-only elasticache_scanner/ tests/

test: ## Run tests
	pytest tests/ -v

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run: ## Run a basic scan (requires --regions argument)
	python3 -m elasticache_scanner --regions us-east-1

# Example targets for common use cases
run-example: ## Run example scan with multiple regions
	python3 -m elasticache_scanner --regions us-east-1 sa-east-1 --tags Team Environment

run-incremental: ## Run incremental scan
	python3 -m elasticache_scanner --regions us-east-1 --incremental

run-full: ## Run full scan with replication groups and node info
	python3 -m elasticache_scanner --regions us-east-1 sa-east-1 --include-replication-groups --node-info

dry-run: ## Run dry-run from existing CSV
	python3 -m elasticache_scanner --dry-run --sample-file elasticache_report.csv --regions us-east-1