## Prerequisites
You need Docker installed on your machine to run the backend.

### Installing Docker Desktop
Follow the official installation guides for your system:
- **Windows (with WSL2):** [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)  
- **macOS:** [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)  
- **Linux (Ubuntu/Debian):** [Install Docker Engine on Linux](https://docs.docker.com/engine/install/ubuntu/)  

### Verify Installation
After installation, check that Docker is working:
```bash
docker --version
docker compose version
```

**IMPORTANT:** Before running any Docker commands, make sure Docker Desktop is running.

## Docker Configuration
- **Backend Service**: Backend running on port 8001 with Python version 3.14
- **Database**: PostgreSQL 16 container on port 6105
- **Volume Mounts**: Code directory for live reload during development

## Local Development

### First Time Setup
```bash
# Build and start containers (first time will download images and build)
docker-compose up -d --build

# If it throws no such file or directory for python:3.14 run the command below before
```bash
docker pull python:3.14
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

## Development Notes

- The backend runs on port **8001**
- PostgreSQL database on port **6105** (to avoid conflicts with local PostgreSQL)
- Hot-reloading is enabled via volume mounting
- Database credentials are in `docker-compose.yml` (Prob need to remove them in the future from it)
- Python packages are installed through pip using information contained in requirements.txt
