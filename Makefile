.PHONY: install dev up pull restart ps status urls tunnels down down-clean \
        migrate seed test lint format build clean _gate \
        docker-build docker-push docker-build-push logs shell-db hadolint pre-commit

REGISTRY   := sherozshaikh
APP        := refund-pilot
VERSION    := $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
PLATFORMS  := linux/amd64,linux/arm64
BUILDER    := mybuilder

# -- stack (one command) ------------------------------------------------------
# Bring up the ENTIRE stack detached, then print how to reach everything.

up:
	@test -f .env || echo "  (note: no .env found — run 'cp .env.example .env' to customize; using defaults)"
	docker compose up -d
	@echo ""
	@echo "============================================================"
	@echo "  Refund Pilot is up."
	@echo "============================================================"
	@user=$$(grep -E '^GATE_USER=' .env 2>/dev/null | cut -d= -f2- || true); user=$${user:-admin}; \
	pass=$$(grep -E '^GATE_PASS=' .env 2>/dev/null | cut -d= -f2- || true); pass=$${pass:-admin}; \
	echo "  Frontend (login):  http://localhost"; \
	echo "      Login:         $$user / $$pass"
	@echo "  Grafana:           http://localhost:3000   (admin / admin)"
	@echo "  API docs:          http://localhost:8000/docs"
	@echo "  Prometheus:        http://localhost:9090"
	@echo "============================================================"
	@echo "  Resolving public tunnel URLs (may take ~30s)..."
	@./scripts/cf-urls.sh

pull:
	docker compose pull

restart:
	docker compose restart

ps status:
	docker compose ps

urls tunnels:
	@./scripts/cf-urls.sh

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
	uv run ruff check src/ tests/ --fix

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
#
# docker-build      → full gate (clean/format/lint/pre-commit/test/hadolint) + local build
# docker-push       → push already-built local images (run docker-build + verify first)
# docker-build-push → full gate + multi-platform buildx + push in one shot

.PHONY: _gate

_gate:
	$(MAKE) clean
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) pre-commit
	$(MAKE) test
	$(MAKE) hadolint

docker-build: _gate
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

docker-build-push: _gate
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
