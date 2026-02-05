# Makefile for Pi-hole Sentinel
# ==============================
#
# Quick commands for common development tasks

.PHONY: help install install-dev test test-unit test-integration test-cov test-fast clean lint format check-security docker-build docker-up docker-down docker-test docker-logs

help:
	@echo "Pi-hole Sentinel Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests with coverage"
	@echo "  make test-unit        Run only unit tests"
	@echo "  make test-integration Run only integration tests"
	@echo "  make test-cov         Generate HTML coverage report"
	@echo "  make test-fast        Run tests without coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (pylint, flake8)"
	@echo "  make format           Format code with black and isort"
	@echo "  make check-security   Run security checks (bandit, safety)"
	@echo ""
	@echo "Docker Testing:"
	@echo "  make docker-build     Build test Docker image"
	@echo "  make docker-up        Start docker-compose test environment"
	@echo "  make docker-down      Stop docker-compose test environment"
	@echo "  make docker-test      Run full test suite in Docker"
	@echo "  make docker-logs      View Docker container logs"
	@echo ""
	@echo "Automated Tests:"
	@echo "  make run-all-tests         Run all automated test scripts"
	@echo "  make run-syntax-checks     Validate Python/Bash syntax"
	@echo "  make run-quality-checks    Check code quality"
	@echo "  make run-security-scans    Security audit"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Testing
test:
	pytest --cov=dashboard --cov=setup --cov-report=term-missing --cov-report=html

test-unit:
	pytest -m unit -v

test-integration:
	pytest -m integration -v

test-cov:
	pytest --cov=dashboard --cov=setup --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-fast:
	pytest -v

# Code Quality
lint:
	pylint dashboard/monitor.py setup.py
	flake8 dashboard/ setup.py tests/

format:
	black dashboard/ setup.py tests/
	isort dashboard/ setup.py tests/

check-security:
	bandit -r dashboard/ setup.py
	safety check

# Cleanup
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.pyc
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage.*" -delete

# Docker Testing
docker-build:
	docker-compose -f docker-compose.test.yml build

docker-up:
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services to start..."
	@sleep 5
	@echo "Monitor API available at: http://localhost:8080/api/docs"

docker-down:
	docker-compose -f docker-compose.test.yml down -v

docker-test: docker-down docker-build docker-up
	@echo "🧪 Running tests in Docker environment..."
	@sleep 3
	docker exec sentinel-monitor ./.github/scripts/run-all-tests.sh || true
	@echo "✅ Docker environment ready at http://localhost:8080"
	@echo "📊 View logs with: make docker-logs"

docker-logs:
	docker-compose -f docker-compose.test.yml logs -f

# Automated Test Scripts
run-all-tests:
	@./.github/scripts/run-all-tests.sh

run-syntax-checks:
	@./.github/scripts/run-syntax-checks.sh

run-quality-checks:
	@./.github/scripts/run-quality-checks.sh

run-security-scans:
	@./.github/scripts/run-security-scans.sh

