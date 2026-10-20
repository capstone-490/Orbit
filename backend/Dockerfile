FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    # copy files from the cache instead of hardlinking across filesystems
    UV_LINK_MODE=copy \
    PATH="/backend/.venv/bin:$PATH"

WORKDIR /backend

# install dependencies first
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . /backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8001

CMD ["sh", "-c", "python manage.py migrate && python load_feature_flags.py && fastapi run app/main.py --host 0.0.0.0 --port 8001"]