# Orbit — Developer Workflow Guide

## Project Structure

```text
.
├── Makefile                    # Cross-platform task runner
├── compose.yaml                # Base application topology (production)
├── compose.dev.yaml            # Local development overrides
├── compose.test.yaml           # Isolated, ephemeral test topology
├── compose.monitoring.yaml     # Optional Prometheus monitoring
├── prometheus.yml              # Prometheus scrape configuration
├── .env                        # Local environment variables (not committed)
├── .env.example                # Environment variable template
│
├── backend/                    # Python 3.14 + FastAPI + SQLAlchemy + Alembic + uv
│   ├── app/                    # Application source (api, core, db, domain)
│   ├── migrations/             # Alembic migrations
│   ├── scripts/                # DB provisioning, feature flags and seeders
│   └── tests/                  # Pytest suites
│
└── frontend/                   # Node 22 + pnpm + Vite + Vitest + Biome
```

### Docker Compose Architecture

Compose files are layered rather than independent. Development and monitoring inherit the base configuration.

| File                      | Responsibility                                                          |
| ------------------------- | ----------------------------------------------------------------------- |
| `compose.yaml`            | Base configuration: PostgreSQL, migrations and backend                  |
| `compose.dev.yaml`        | Development overrides: hot reload, bind mounts, frontend and host ports |
| `compose.test.yaml`       | Isolated test environment with in-memory PostgreSQL                     |
| `compose.monitoring.yaml` | Optional Prometheus monitoring                                          |

---

## Installing Docker Desktop

Follow the official installation guides for your system:

- **Windows (with WSL2):** [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- **macOS:** [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- **Linux (Ubuntu/Debian):** [Install Docker Engine on Linux](https://docs.docker.com/engine/install/ubuntu/)
  After installation, check that Docker is working:

```bash
# check
docker --version
docker compose version
```

## 1. Setup

Create a `.env` file in the **project root** before starting the development stack:

```bash
cp .env.example .env
```

```bash
cd backend/
uv sync
cd ../frontend/
pnpm install
```

### Automated Tests

You do not need a `.env` file to run:

```bash
make test
make test-be
make test-fe
make test-fe-int
```

The test Compose configuration injects test credentials and uses an in-memory PostgreSQL instance.
Test data and database state are discarded when the test stack is torn down.

---

## 2. Makefile Workflows (Recommended)

The root `Makefile` is cross-platform (automatically uses `/bin/sh` on Linux/macOS/WSL2 and `powershell.exe` on native Windows).

### Development

| Command                | Description                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `make dev`             | Builds and starts PostgreSQL, migrations, DB provisioning, seeders, FastAPI and Vite |
| `make down`            | Stops development containers and removes orphans (preserves database volume)         |
| `make monitoring`      | Starts development with Prometheus                                                   |
| `make monitoring-down` | Stops development and Prometheus                                                     |

### Production

| Command          | Description                                                          |
| ---------------- | -------------------------------------------------------------------- |
| `make prod`      | Builds and starts the production application stack in the background |
| `make prod-down` | Stops production containers without deleting persistent volumes      |

### Testing

| Command            | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `make test`        | Runs backend and frontend tests in one shared lifecycle                    |
| `make test-be`     | Runs backend pytest suite                                                  |
| `make test-be-cov` | Runs backend tests with coverage                                           |
| `make test-fe`     | Runs isolated frontend unit tests                                          |
| `make test-fe-cov` | Runs frontend tests with coverage                                          |
| `make test-fe-int` | Runs frontend integration tests against a live backend and seeded database |

### Database and Cleanup

| Command                                | Description                                                     |
| -------------------------------------- | --------------------------------------------------------------- |
| `make migration msg="add_audit_table"` | Generates an Alembic revision                                   |
| `make clean`                           | Removes development/test containers, volumes and backend caches |

**WARNING:** `make clean` deletes development and test volumes, including local PostgreSQL data. Do not run it if you need to preserve your development database.

### Passing Custom Arguments to Tests via `ARGS`

```bash
# Run a specific backend test file
make test-be ARGS="tests/security/test_pii_redaction.py -vv"

# Run backend tests matching a keyword
make test-be ARGS="-k test_clients"

# Run backend tests with coverage
make test-be-cov ARGS="-k test_clients"

# Run a specific frontend test file
make test-fe ARGS="src/components/ClientList.test.tsx"

# Run frontend tests with coverage
make test-fe-cov ARGS="src/components/ClientList.test.tsx"

# Run the complete test suite
make test
```

---

## 3. Docker Compose Workflows

### Local Development

```bash
# Start full dev stack with hot-reload
docker compose -f compose.yml -f compose.dev.yml up --build

# Start only the database in the background (useful when running backend/frontend on host)
docker compose -f compose.yml -f compose.dev.yml up db -d

# Start the development stack with monitoring, Prometheus: http://localhost:9090
docker compose -f compose.yml -f compose.dev.yml -f compose.monitoring.yml up --build

# Stop stacks (keep database volume)
docker compose -f compose.yml -f compose.dev.yml down --remove-orphans
docker compose -f compose.yml -f compose.dev.yml -f compose.monitoring.yml down --remove-orphans
```

### Ephemeral Containerized Testing

```bash
# Run backend tests (auto-starts RAM db + migrations + seeders)
docker compose -f compose.test.yml run --rm --build backend-test pytest

# Run isolated frontend unit tests
docker compose -f compose.test.yml run --rm --build --no-deps frontend-test pnpm vitest run

# Run frontend integration tests against a live backend:
docker compose -f compose.test.yaml up -d --build backend
docker compose -f compose.test.yaml run --rm frontend-test pnpm vitest run

# Always tear down the test stack & volumes afterward
docker compose -f compose.test.yml down -v --remove-orphans

docker-compose logs -f backend-test
```

---

## 4. Manual Host Workflows (Running Directly with `uv` & `pnpm`)

You can run the backend and frontend directly on your host machine for IDE debugging or rapid iteration.

### Backend (`backend/`)

#### 1. Prerequisites & Environment Variables

:exclamation: Ensure PostgreSQL is running and reachable on `127.0.0.1:5432` (for example, via `docker compose -f compose.yml -f compose.dev.yml up db -d`).

Export the required env variables in your shell or create a `.env` file inside backend:

```bash
export ENVIRONMENT=local
export DEBUG=true

export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=orbit_db
export DB_USER=orbit_app
export DB_PASSWORD=your-local-db-password

export SECRET_KEY=local-only-insecure-secret
export ORBIT_ANONYMIZATION_SECRET=your-local-anonymization-secret
export ORBIT_AUTH_SECRET=...
export ENABLE_DEBUG_ROUTES=false
export METRICS_ENABLED=1
```

#### 2. Install Dependencies (`uv`)

```bash
cd backend
uv sync --frozen --no-build
```

#### 3. Database Migrations & Seeding

```bash
cd backend

# Apply all SQL migrations / seed data
uv run --locked --no-build alembic -c alembic.ini upgrade head

# Provision database credentials if required
uv run --locked --no-build python -m scripts.provision_db_credentials

# Load feature flags
uv run --locked --no-build python -m scripts.load_feature_flags

# Seed baseline data (idempotent)
uv run --locked --no-build python -m scripts.seed_db

# Create a new SQL migration revision; edit manually after in migrations/sql
uv run --locked --no-build alembic -c alembic.ini revision -m "add_new_table"
```

#### 4. Run Backend Tests (`pytest`)

> **Note:** `tests/conftest.py` automatically seeds the database on session start and wraps every test in a SQLAlchemy `SAVEPOINT` transaction that rolls back after each test.

```bash
cd backend

# Run all tests
uv run --locked --no-build pytest

# Run with coverage (matches CI)
uv run --locked --no-build pytest --cov=. --cov-report=xml:coverage.xml --cov-report=term-missing

# Run a specific test directory or file
uv run --locked --no-build pytest tests/security/
```

#### 5. Backend Lint, Format & Typecheck (`ruff` & `mypy`)

```bash
cd backend

# Check linting and formatting (matches CI)
uv run --locked --no-build ruff check .
uv run --locked --no-build ruff format --check .

# Auto-fix lint issues and format code
uv run --locked --no-build ruff check --fix .
uv run --locked --no-build ruff format .

# Run static type checking
uv run --locked --no-build mypy .
```

---

### Frontend (`frontend/`)

#### 1. Install Dependencies (`pnpm`)

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
```

#### 2. Start Local Dev Server

```bash
cd frontend
VITE_API_URL=http://localhost:8001/api/v1 pnpm dev
```

#### 3. Frontend Lint & Format (`biome`)

```bash
cd frontend

# Check linting, formatting, and types (read-only)
pnpm lint
pnpm check
pnpm biome format ./src

# Auto-apply fixes and formatting
pnpm biome lint --write ./src
pnpm biome check --write ./src
pnpm biome format --write ./src
```

#### 4. Frontend Tests (`vitest`)

```bash
cd frontend

# Run unit tests once
pnpm vitest run

# Run tests in interactive watch mode during development
pnpm vitest

# Run unit tests with coverage report (matches CI)
pnpm vitest run --coverage

# Build production bundle
pnpm build
```
