# syntax=docker/dockerfile:1
FROM python:3.13-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# dependencies for building Python packages
# discord.py voice dependencies
# cleaning up unused files
RUN apt-get update \
  && apt-get install -y build-essential \
  && apt-get install -y libffi-dev libnacl-dev \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
# Requirements are installed here to ensure they will be cached
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Use uv to run the application
CMD ["uv", "run", "main.py"]

