FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV POETRY_VERSION=2.3.3

WORKDIR /code

RUN python -m venv "${VIRTUAL_ENV}"
RUN pip install --upgrade pip setuptools wheel "poetry==${POETRY_VERSION}"

# Copy dependency metadata first to maximize layer cache reuse.
COPY manage.py README.md pyproject.toml poetry.lock ./
COPY permission_model/ /code/permission_model
COPY covsonar_backend/ /code/covsonar_backend
COPY rest_api/ /code/rest_api

RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root --no-interaction

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_NO_CACHE_DIR=1
ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /code

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

COPY manage.py README.md ./
COPY permission_model/ /code/permission_model
COPY covsonar_backend/ /code/covsonar_backend
COPY rest_api/ /code/rest_api

CMD ["/bin/sh", "-c", "eval \"$START_DJANGO_SERVER\""]
