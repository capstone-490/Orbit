.PHONY: help dev mon monitoring prod prod-mon down mon-logs monitoring-logs \
        test test-cov test-be test-be-cov test-fe test-fe-int test-fe-cov migration clean

# -------------------------------------------------------------------

COMPOSE          := docker compose -f compose.yml
COMPOSE_DEV      := $(COMPOSE) -f compose.dev.yml
COMPOSE_MON      := $(COMPOSE_DEV) -f compose.monitoring.yml
COMPOSE_PROD_MON := $(COMPOSE) -f compose.monitoring.yml
COMPOSE_ALL      := $(COMPOSE) -f compose.dev.yml -f compose.monitoring.yml
COMPOSE_TEST     := docker compose -f compose.test.yml

# OS Detection: Windows (PowerShell) vs. Unix (Linux / macOS / WSL2)
ifeq ($(OS),Windows_NT)
    SHELL := powershell.exe
    .SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
    run_ephemeral = try { $(1); $$code = $$LASTEXITCODE; if ($$code -ne 0) { exit $$code } } finally { $(COMPOSE_TEST) down -v --remove-orphans }
    CLEAN_CACHES = Get-ChildItem -Path backend -Include __pycache__,.pytest_cache,.mypy_cache,.ruff_cache -Recurse -Directory -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
else
    SHELL := /bin/sh
    run_ephemeral = trap '$(COMPOSE_TEST) down -v --remove-orphans' EXIT INT TERM; $(1)
    CLEAN_CACHES = find backend -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" \) -prune -exec rm -rf {} +
endif

# -------------------------------------------------------------------

## Start full development stack
dev:
	$(COMPOSE_DEV) up --build

## Start development stack with Prometheus
mon monitoring:
	$(COMPOSE_MON) up --build

## Start production stack
prod:
	$(COMPOSE) up -d --build

## Start production stack with Prometheus
prod-mon:
	$(COMPOSE_PROD_MON) up -d --build

## Stop ALL stacks (dev, mon, prod, prod-mon, and leftover test containers)
down:
	$(COMPOSE_ALL) down --remove-orphans
	$(COMPOSE_TEST) down --remove-orphans

mon-logs monitoring-logs:
	$(COMPOSE_MON) logs -f prometheus backend

# -------------------------------------------------------------------

## Run backend tests
test-be:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build backend-test pytest $(ARGS))

## Backend coverage
test-be-cov:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build backend-test pytest $(ARGS) \
		--cov=. \
		--cov-branch \
		--cov-report=term-missing:skip-covered \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml)

## Run isolated frontend unit tests
test-fe:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build --no-deps frontend-test pnpm vitest run $(ARGS))

## Frontend coverage
test-fe-cov:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build --no-deps frontend-test pnpm vitest run --coverage $(ARGS))

## Run frontend integration tests
test-fe-int:
	@$(call run_ephemeral,$(COMPOSE_TEST) up -d --build --wait backend; $(COMPOSE_TEST) run --rm --build frontend-test pnpm vitest run $(ARGS))

## Run backend and frontend tests
test:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build backend-test pytest $(ARGS); $(COMPOSE_TEST) run --rm --build --no-deps frontend-test pnpm vitest run)

test-cov:
	@$(call run_ephemeral,$(COMPOSE_TEST) run --rm --build backend-test pytest --cov=. \
		--cov-branch \
		--cov-report=term-missing:skip-covered \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml $(ARGS); \
		$(COMPOSE_TEST) run --rm --build --no-deps frontend-test pnpm vitest run --coverage $(FARGS))

# -------------------------------------------------------------------

## Generate a new Alembic revision
migration:
ifndef msg
	$(error Missing migration message. Usage: make migration msg="add_audit_table")
endif
	$(COMPOSE_DEV) run --rm migration alembic revision -m "$(msg)"

# -------------------------------------------------------------------

## Deep clean all containers, volumes (including Prometheus/dev), and caches
clean:
	$(COMPOSE_ALL) down -v --remove-orphans
	$(COMPOSE_TEST) down -v --remove-orphans
	$(CLEAN_CACHES)
