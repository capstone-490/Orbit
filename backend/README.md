# Prerequisites

- Docker
- uv

## Installing Docker Desktop

Follow the official installation guides for your system:

- **Windows (with WSL2):** [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)  
- **macOS:** [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)  
- **Linux (Ubuntu/Debian):** [Install Docker Engine on Linux](https://docs.docker.com/engine/install/ubuntu/)  

After installation, check that Docker is working:

```bash
docker --version
docker compose version
```

**IMPORTANT:** Before running any Docker commands, make sure Docker Desktop is running.

## Docker Configuration

- **Backend Service**: Backend running on port 8001 with Python version 3.14-slim
- **Database**: PostgreSQL 16 container on port 6105
- **Volume Mounts**: Code directory for live reload during development

## Local Development

### First Time Setup

```bash
# Build and start containers (first time will download images and build)
docker-compose up -d --build

# If it throws no such file or directory for python:3.14-slim run the command below before
```bash
docker pull python:3.14-slim
docker-compose up -d --build

#Currently it will not be available as no python code is running so the backend will exit with code 2 (remove this when code is present and its running)
After setup, the API will be available at `http://localhost:8001`


### Daily Development

#### Starting the Application
```bash
# Start all services (currently only PostgreSQL)
docker-compose up

# Or run in background (detached mode)
docker-compose up -d

# Stop services (or press Ctrl+C if running in foreground)
docker-compose down
```

## Common Commands

All commands should be run through Docker:

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f backend

# View last 50 lines
docker-compose logs --tail=50 backend
```

### Restart Services

```bash
# Restart just the backend service (after dependency changes)
docker-compose restart backend

# Rebuild after changing requirements.txt
docker-compose up -d --build backend
```

### Stop the Backend

```bash
docker-compose down
```

### To Run the Tests

```bash
docker compose run --rm backend pytest -v
```

## Development Notes

- The backend runs on port **8001**
- PostgreSQL database on port **6105** (to avoid conflicts with local PostgreSQL)
- Hot-reloading is enabled via volume mounting
- Database credentials are in `docker-compose.yml` (Prob need to remove them in the future from it)
- Python packages are installed through pip using information contained in requirements.txt

### Client anonymization

Client creation stores deterministic synthetic values for names, contact details,
addresses, occupations, and age. Real values are never persisted by the client
creation flow. A UUID is generated before anonymization and stored as
`anonymized_client_id`; every synthetic field is derived from that identifier, so
fields for one client remain correlated without storing the original PII.

The in-memory store is only a cache: deterministic fake values come from the HMAC,
while the cache retains generated values for efficiency. Cache eviction therefore
does not change values. Existing database rows are not masked by this feature.
The backend refuses to start unless `ORBIT_ANONYMIZATION_SECRET` is configured,
non-blank, and at least 32 characters long. Use a stable, deployment-managed
secret in development, tests, Docker Compose, and production; never use a shared
development secret in production.

The API accepts `date_of_birth` only to calculate age during client creation.
Only `age` is persisted and returned.
