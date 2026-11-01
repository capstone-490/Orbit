# syntax=docker/dockerfile:1.7
FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# -----------------------------------------------------------------------------
# production dependencies builder
# -----------------------------------------------------------------------------
FROM base AS prod-builder

COPY pyproject.toml uv.lock .python-version ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY config ./config
COPY scripts ./scripts

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# -----------------------------------------------------------------------------
# dev target
# -----------------------------------------------------------------------------
FROM prod-builder AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --dev --no-install-project

ENV PYTEST_ADDOPTS="-o cache_dir=/tmp/.pytest_cache" \
    MYPY_CACHE_DIR="/tmp/.mypy_cache" \
    RUFF_CACHE_DIR="/tmp/.ruff_cache"

# Run dev/test as UID 1000 instead of root so any generated files (like Alembic revisions)
# match standard Linux host user
RUN groupadd -g 1000 app && useradd -u 1000 -g app -m -d /home/app app \
    && chown -R app:app /opt/venv /app

USER app

CMD ["pytest"]

# -----------------------------------------------------------------------------
# cloud production runtime
# -----------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent app

COPY --from=prod-builder --chown=app:app /opt/venv /opt/venv
COPY --from=prod-builder --chown=app:app /app /app

USER app

EXPOSE 8001
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8001"]
