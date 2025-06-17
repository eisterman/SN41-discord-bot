# syntax=docker/dockerfile:1
FROM python:3.11.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # discord.py voice dependencies
  && apt-get install -y libffi-dev libnacl-dev \
  # cleaning up unused files
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

