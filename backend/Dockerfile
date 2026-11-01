FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    # copy files from the cache instead of hardlinking across filesystems
    UV_LINK_MODE=copy \
    PYTHONPATH="/backend" \ 
    PATH="/backend/.venv/bin:$PATH"

WORKDIR /backend

# install dependencies first
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-build --no-install-project

COPY app /backend/app
COPY migrations /backend/migrations
COPY scripts /backend/scripts
COPY config /backend/config
COPY manage.py /backend/manage.py
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-build

RUN addgroup --system app && adduser --system --ingroup app app
USER app

EXPOSE 8001

CMD ["sh", "-c", "python manage.py migrate && python scripts/load_feature_flags.py && fastapi run app/main.py --host 0.0.0.0 --port 8001"]
