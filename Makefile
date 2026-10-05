# ==============================================================================
# ILEWS – Intelligent Landslide Early Warning System
# Project-level Makefile for local development
# ==============================================================================

.DEFAULT_GOAL := help

# ---------- Docker Compose ----------

## Start all docker-compose services in detached mode
dev-up:
	docker compose up -d

## Stop and remove all docker-compose services
dev-down:
	docker compose down

## Tail logs from all docker-compose services
dev-logs:
	docker compose logs -f

# ---------- Database ----------

## Run Alembic database migrations (FastAPI backend)
db-migrate:
	cd cloud/services/fastapi-backend && alembic upgrade head

## Run the database seed script
db-seed:
	cd cloud/services/fastapi-backend && python -m scripts.seed

# ---------- Testing ----------

## Run all tests – pytest for Python services, jest for dashboard
test-all:
	cd cloud/services/fastapi-backend && pytest
	cd cloud/services/etl-processor && pytest
	cd cloud/services/ml-inference && pytest
	cd cloud/services/notification-svc && pytest
	cd edge && pytest
	cd dashboard && npx jest

# ---------- Linting ----------

## Lint all Python code with flake8 and dashboard with eslint
lint:
	flake8 cloud/ edge/
	cd dashboard && npx eslint .

# ---------- Build ----------

## Build all Docker images defined in docker-compose
build-all:
	docker compose build

# ---------- Edge ----------

## Install Python dependencies for the edge gateway service
edge-install:
	cd edge && pip install -r requirements.txt

# ---------- Firmware ----------

## Build ESP32 firmware using PlatformIO
firmware-build:
	cd firmware && platformio run

# ---------- Help ----------

## Print available make targets with descriptions
help:
	@echo ""
	@echo "ILEWS – Available targets"
	@echo "========================="
	@awk '/^[a-zA-Z_-]+:/ { \
		target = $$1; \
		sub(/:.*/, "", target); \
		if (desc) printf "  \033[36m%-18s\033[0m %s\n", target, desc; \
		desc = "" \
	} /^## / { \
		desc = substr($$0, 4) \
	}' $(MAKEFILE_LIST)
	@echo ""

.PHONY: dev-up dev-down dev-logs db-migrate db-seed test-all lint build-all edge-install firmware-build help
