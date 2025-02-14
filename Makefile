PYTHON = python
POETRY = poetry
PROJECT_NAME = Online-Cinema-API
CONTAINER_NAME = ${PROJECT_NAME}_container
DOCKER_COMPOSE = docker-compose -f compose.yaml

.PHONY: help
help:
	@echo "Usage: make [target] [path=<path>]"
	@echo ""
	@echo "Targets:"
	@echo "  deps      Install dependencies"
	@echo "  build     Build Docker container"
	@echo "  up        Start the application in Docker"
	@echo "  up-build  Build and start the application in Docker"
	@echo "  down      Down the container"
	@echo "  run       Start the app with uvicorn"
	@echo "  lint      Run isort and Ruff on a specific path"
	@echo "  clean     Remove __pycache__ files"

.PHONY: deps
deps:
	${POETRY} install

.PHONY: build
build:
	${DOCKER_COMPOSE} build

.PHONY: up-build
up-build:
	${DOCKER_COMPOSE} up --build

.PHONY: up
up:
	${DOCKER_COMPOSE} up

.PHONY: down
down:
	${DOCKER_COMPOSE} down

.PHONY: run
run:
	${POETRY} run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

.PHONY: lint
lint:
	@echo "Running isort and Ruff on: $(path)"
	${POETRY} run isort $(path)
	${POETRY} run ruff check --fix $(path)

.PHONY: clean
clean:
	find . -name "__pycache__" -exec rm -rf {} +
