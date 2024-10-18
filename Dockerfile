FROM python:3.12-slim

ENV \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  PYTHONPATH=/app \
  PATH="/root/.local/bin:$PATH" \
  POETRY_VIRTUALENVS_CREATE=false \
  LANG=ru_RU.UTF-8 \
  LC_ALL=ru_RU.UTF-8

RUN apt-get update \
    && apt-get install -yqq --no-install-recommends \
      curl \
      libpq-dev \
      libssl-dev \
      locales \
    && echo ru_RU.UTF-8 UTF-8 >> /etc/locale.gen \
    && locale-gen \
    && apt-get autoclean \
    && apt-get autoremove --yes \
    && /bin/bash -c "rm -rf /var/lib/{apt,dpkg,cache,log}/*"

RUN pip install --upgrade pip setuptools

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN poetry install --no-interaction --no-cache

COPY . .

EXPOSE 8000
