.PHONY: install dev down down-clean migrate seed test lint format build \
        docker-build docker-push docker-build-push logs shell-db hadolint pre-commit

REGISTRY   := sherozshaikh
APP        := refund-pilot
VERSION    := $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
PLATFORMS  := linux/amd64,linux/arm64
BUILDER    := mybuilder

# -- local dev ----------------------------------------------------------------

install:
	uv sync

dev:
	docker compose up --build

down:
	docker compose down

down-clean:
	docker compose down -v

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m refund_pilot.data.seed

test:
	uv run pytest -v

pre-commit:
	uv run pre-commit run --all-files

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff format src/ tests/

build:
	uv build --wheel

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -type f -delete
	find . -name "*.pyo" -type f -delete
	find . -name ".DS_Store" -type f -delete
	find . -type d -name ".vscode" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".idea" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true

# -- docker -------------------------------------------------------------------
# Each service is an independently deployable image.
# Tags: :<version> (immutable) + :latest (mutable pointer).

docker-build:
	docker build -f docker/Dockerfile.backend \
	    -t $(REGISTRY)/$(APP)-backend:latest .
	docker build -f docker/Dockerfile.worker \
	    -t $(REGISTRY)/$(APP)-worker:latest .
	docker build -f docker/Dockerfile.frontend \
	    -t $(REGISTRY)/$(APP)-frontend:latest .

docker-push:
	docker push $(REGISTRY)/$(APP)-backend:latest
	docker push $(REGISTRY)/$(APP)-worker:latest
	docker push $(REGISTRY)/$(APP)-frontend:latest

docker-build-push:
	docker buildx build --builder $(BUILDER) --platform $(PLATFORMS) --push \
	    -f docker/Dockerfile.backend \
	    -t $(REGISTRY)/$(APP)-backend:latest .
	docker buildx build --builder $(BUILDER) --platform $(PLATFORMS) --push \
	    -f docker/Dockerfile.worker \
	    -t $(REGISTRY)/$(APP)-worker:latest .
	docker buildx build --builder $(BUILDER) --platform $(PLATFORMS) --push \
	    -f docker/Dockerfile.frontend \
	    -t $(REGISTRY)/$(APP)-frontend:latest .

hadolint:
	docker run --rm -i hadolint/hadolint < docker/Dockerfile.backend
	docker run --rm -i hadolint/hadolint < docker/Dockerfile.worker
	docker run --rm -i hadolint/hadolint < docker/Dockerfile.frontend

# -- ops ----------------------------------------------------------------------

logs:
	docker compose logs -f

shell-db:
	docker compose exec postgres psql -U refund_pilot
