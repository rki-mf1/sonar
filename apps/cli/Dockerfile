FROM mambaorg/micromamba:2.0.5 AS builder

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV POETRY_VERSION=2.3.3

WORKDIR /code

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    git \
    ca-certificates \
    libboost-dev \
    libmagic1 \
 && rm -rf /var/lib/apt/lists/*

COPY README.md environment.docker.yml pyproject.toml poetry.lock ./
COPY src/ /code/src

RUN micromamba create -y -n sonar-cli -f environment.docker.yml \
 && micromamba clean --all --yes

RUN micromamba run -n sonar-cli pip install --no-cache-dir "poetry==${POETRY_VERSION}"
RUN micromamba run -n sonar-cli poetry config virtualenvs.create false \
 && micromamba run -n sonar-cli poetry install --only main --no-root --no-interaction

FROM mambaorg/micromamba:2.0.5

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=/opt/conda/envs/sonar-cli/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV PYTHONPATH=/code/src
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV _JAVA_OPTIONS="-Xms128m -Xmx4g"

WORKDIR /code

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
    libmagic1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/conda/envs/sonar-cli /opt/conda/envs/sonar-cli

COPY README.md pyproject.toml ./
COPY src/ /code/src

ENTRYPOINT ["python", "-m", "sonar_cli.sonar"]
