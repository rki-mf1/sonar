FROM python:3.11 AS build-stage

# PRODUCTION STAGE
FROM python:3.11

# Ensure logging is up to date despite possible buffering
ENV PYTHONUNBUFFERED=1
# Suppress warnings about running pip as root
ENV PIP_ROOT_USER_ACTION=ignore

# install poetry and dependencies
RUN pip install poetry

# Copy only requirements to cache them in the docker layer
WORKDIR /code

# The reason for copying certain core files and folders beforehand is to address failures in GH action (during poetry install)
COPY manage.py README.md pyproject.toml poetry.lock requirements-testing.txt ./
COPY permission_model/ /code/permission_model
COPY covsonar_backend/ /code/covsonar_backend
COPY rest_api/ /code/rest_api

RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction
