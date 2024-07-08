# Variables
DOCKER_IMAGE_NAME = personal-webhooks
DOCKER_IMAGE_TAG = latest
DOCKER_CONTAINER_NAME = personal-webhooks-container
VENV_NAME = venv
LOG_LEVEL = INFO  # Can be changed to DEBUG for more verbose output

# Colors for output
COLOR_RESET = \033[0m
COLOR_INFO = \033[32m
COLOR_WARNING = \033[33m
COLOR_ERROR = \033[31m

# Default target
.PHONY: all
all: build

# Build the Docker image
.PHONY: build
build:
	@echo "$(COLOR_INFO)Building Docker image $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)...$(COLOR_RESET)"
	@DOCKER_BUILDKIT=0 docker build -t $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) . || \
		(echo "$(COLOR_ERROR)Failed to build Docker image. Check your Dockerfile and try again.$(COLOR_RESET)" && exit 1)
	@echo "$(COLOR_INFO)Docker image built successfully.$(COLOR_RESET)"

# Run the Docker container
.PHONY: run
run: build
	@echo "$(COLOR_INFO)Running Docker container $(DOCKER_CONTAINER_NAME)...$(COLOR_RESET)"
	@docker run -d --name $(DOCKER_CONTAINER_NAME) -p 8000:8000 $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) || \
		(echo "$(COLOR_ERROR)Failed to run Docker container. The container might already exist or there might be a port conflict.$(COLOR_RESET)" && exit 1)
	@echo "$(COLOR_INFO)Docker container is now running.$(COLOR_RESET)"

# Stop the Docker container
.PHONY: stop
stop:
	@echo "$(COLOR_INFO)Stopping Docker container $(DOCKER_CONTAINER_NAME)...$(COLOR_RESET)"
	@docker stop $(DOCKER_CONTAINER_NAME) || echo "$(COLOR_WARNING)Container $(DOCKER_CONTAINER_NAME) is not running.$(COLOR_RESET)"

# Remove the Docker container
.PHONY: rm
rm: stop
	@echo "$(COLOR_INFO)Removing Docker container $(DOCKER_CONTAINER_NAME)...$(COLOR_RESET)"
	@docker rm $(DOCKER_CONTAINER_NAME) || echo "$(COLOR_WARNING)Container $(DOCKER_CONTAINER_NAME) does not exist.$(COLOR_RESET)"

# Stop and remove the Docker container
.PHONY: down
down: rm

# Rebuild the Docker image and restart the container
.PHONY: rebuild
rebuild: down build run

# Run the container with volume mounting for development
.PHONY: dev
dev: build
	@echo "$(COLOR_INFO)Running Docker container $(DOCKER_CONTAINER_NAME) in development mode...$(COLOR_RESET)"
	@docker run -d --name $(DOCKER_CONTAINER_NAME) -p 8000:8000 -v $(CURDIR):/app $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) || \
		(echo "$(COLOR_ERROR)Failed to run Docker container in development mode. The container might already exist or there might be a port conflict.$(COLOR_RESET)" && exit 1)

# View container logs
.PHONY: logs
logs:
	@echo "$(COLOR_INFO)Viewing logs for Docker container $(DOCKER_CONTAINER_NAME)...$(COLOR_RESET)"
	@docker logs -f $(DOCKER_CONTAINER_NAME) || echo "$(COLOR_ERROR)Failed to retrieve logs. Make sure the container is running.$(COLOR_RESET)"

# Run tests in the container
.PHONY: test
test:
	@echo "$(COLOR_INFO)Running tests in Docker container $(DOCKER_CONTAINER_NAME)...$(COLOR_RESET)"
	@docker exec -it $(DOCKER_CONTAINER_NAME) pytest || echo "$(COLOR_ERROR)Failed to run tests. Make sure the container is running.$(COLOR_RESET)"

# Set up virtual environment, install requirements, and run tests locally with logging
.PHONY: test-local
test-local:
	@echo "$(COLOR_INFO)Setting up virtual environment and running tests locally...$(COLOR_RESET)"
	@python3 -m venv $(VENV_NAME) || (echo "$(COLOR_ERROR)Failed to create virtual environment. Make sure python3-venv is installed.$(COLOR_RESET)" && exit 1)
	@. $(VENV_NAME)/bin/activate && \
		pip install -r requirements.txt && \
		PYTHONPATH=$$PYTHONPATH:$$(pwd):$$(pwd)/app \
		LOG_LEVEL=$(LOG_LEVEL) \
		pytest -s -o log_cli=true -o log_cli_level=$(LOG_LEVEL) tests/ 2>&1 && \
		deactivate || \
		(echo "$(COLOR_ERROR)Failed to run tests. Check the output above for details.$(COLOR_RESET)" && exit 1)
	@echo "$(COLOR_INFO)Local tests completed.$(COLOR_RESET)"

# Add a new target for verbose testing
.PHONY: test-local-verbose
test-local-verbose:
	@$(MAKE) test-local LOG_LEVEL=DEBUG

# Clean up: stop and remove container, and remove image
.PHONY: clean
clean: down
	@echo "$(COLOR_INFO)Removing Docker image $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)...$(COLOR_RESET)"
	@docker rmi $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) || echo "$(COLOR_WARNING)Image $(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG) does not exist.$(COLOR_RESET)"

# Test webhook
.PHONY: test-webhook
test-webhook:
	@echo "$(COLOR_INFO)Sending test webhook to the application...$(COLOR_RESET)"
	@chmod +x test_webhook.sh
	@./test_webhook.sh || echo "$(COLOR_ERROR)Failed to send test webhook. Make sure the application is running and the script has execute permissions.$(COLOR_RESET)"

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build         - Build the Docker image"
	@echo "  run           - Build the image and run the Docker container"
	@echo "  stop          - Stop the Docker container"
	@echo "  rm            - Stop and remove the Docker container"
	@echo "  down          - Stop and remove the Docker container"
	@echo "  rebuild       - Rebuild the image and restart the container"
	@echo "  dev           - Build and run the container with volume mounting for development"
	@echo "  logs          - View container logs"
	@echo "  test          - Run tests in the container"
	@echo "  clean         - Stop and remove container, and remove image"
	@echo "  test-webhook  - Send a test webhook to the application"
	@echo "  help          - Show this help message"
