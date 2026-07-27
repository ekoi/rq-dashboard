FROM python:3.12-slim

# Install git (required for uv to fetch git dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /bin/

WORKDIR /code

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies from lockfile for reproducible builds.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/code/entrypoint.sh"]


