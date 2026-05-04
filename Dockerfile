# Dockerfile — CPU image for HF Spaces (cpu-basic per D-015 / D-DEPLOY-003).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# `uv sync` installs deps into /app/.venv; ensure its bin is on PATH so the
# CMD resolves `uvicorn` directly. Earlier deploys ran a cached image that
# already had this resolved; HF rebuilt fresh and tripped on PATH order.
ENV PATH="/app/.venv/bin:$PATH"

# E7 island bundle + templates ship under app/ui/. `COPY app ./app` is sufficient.
COPY app ./app
COPY rules ./rules
COPY assets ./assets
COPY fixtures ./fixtures
COPY demo ./demo

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
