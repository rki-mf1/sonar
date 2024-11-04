FROM continuumio/miniconda3:24.9.2-0

RUN apt-get -qq update --yes \
 && apt-get -qq install --yes --no-install-recommends \
    build-essential git make clang libboost-dev postgresql-client ca-certificates libmagic1 \
 && rm -rf /var/lib/apt/lists/*

RUN /opt/conda/bin/conda config --add channels conda-forge \
  && /opt/conda/bin/conda config --add channels bioconda \
  && /opt/conda/bin/conda clean --all --yes

# Copy only requirements to cache them in the docker layer
WORKDIR /code

# The reason for copying certain core files and folders beforehand is to address failures in GH action (during poetry install)
COPY README.md environment.yml poetry.lock pyproject.toml ./
COPY env.template .env
COPY src/ /code/src

RUN conda config --set solver classic
RUN conda env create -n sonar-cli -f environment.yml --yes
RUN conda run -n sonar-cli poetry install --only main --no-interaction
RUN conda run -n sonar-cli pip install git+https://git@github.com/kcleal/pywfa.git@9c5e192

ENTRYPOINT ["conda", "run", "-n", "sonar-cli", "sonar-cli"]
