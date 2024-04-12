FROM python:3.11 AS build-stage

# PRODUCTION STAGE
FROM python:3.11

# Ensure logging is up to date despite possible buffering
ENV PYTHONUNBUFFERED 1

# install poetry and dependencies
RUN pip install poetry

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY README.md pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction

ADD . /code

