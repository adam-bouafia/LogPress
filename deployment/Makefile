.PHONY: help build run-compression run-queries clean test docker-build docker-up docker-down

help:
	@echo "logpress - Available Commands:"
	@echo ""
	@echo "  make build          - Build Docker image"
	@echo "  make run-compression - Run compression evaluation"
	@echo "  make run-queries    - Run query benchmarks"
	@echo "  make docker-up      - Start all services with Docker Compose"
	@echo "  make docker-down    - Stop all Docker services"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Clean temporary files"
	@echo "  make install        - Install dependencies locally"

install:
	python3.11 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

build:
	docker build -t logpress:latest .

docker-up:
	docker-compose up

docker-down:
	docker-compose down

run-compression:
	python run_full_evaluation.py

run-queries:
	python run_query_benchmarks.py

test:
	pytest logpress/tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/
