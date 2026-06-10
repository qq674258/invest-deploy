# 基础镜像可通过构建参数覆盖（国内镜像站失效时用）
# 例: docker compose build --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/invest.db

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

ARG PIP_INDEX_URL=
RUN if [ -n "$PIP_INDEX_URL" ]; then \
      pip install --no-cache-dir -i "$PIP_INDEX_URL" -r requirements-docker.txt; \
    else \
      pip install --no-cache-dir -r requirements-docker.txt; \
    fi

COPY invest ./invest
COPY config ./config
COPY tests ./tests
COPY pyproject.toml setup.py ./

RUN mkdir -p /app/data

CMD ["python", "-m", "invest.jobs.pipeline", "--all"]
