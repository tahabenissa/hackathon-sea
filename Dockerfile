# One image for all Python services (simulator, attacker, engine, api).
# The service is chosen by the `command:` in docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY seashield ./seashield
RUN pip install --no-cache-dir .

COPY config ./config
COPY models ./models

RUN useradd --create-home seashield
USER seashield
