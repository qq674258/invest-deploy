# 国内用户可换 DaoCloud 镜像: --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/invest.db

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

# 国内用户可换清华 pip 源: --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i "$PIP_INDEX_URL" -r requirements-docker.txt

COPY invest ./invest
COPY config ./config
COPY data ./data
COPY tests ./tests
COPY pyproject.toml setup.py ./

RUN mkdir -p /app/data

CMD ["python", "-m", "invest.jobs.pipeline", "--all"]
