# syntax=docker/dockerfile:1
FROM python:3.11.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # discord.py voice dependencies
  && apt-get install -y libffi-dev libnacl-dev \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Requirements are installed here to ensure they will be cached.
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY . .

WORKDIR /app

CMD ["python3", "main.py"]

