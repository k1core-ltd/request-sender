FROM microsoft/devcontainers-python:3.12

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN uv sync
