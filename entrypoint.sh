#!/bin/bash
set -e

# Install harvester if the source directory is mounted
if [ -d "/harvester" ] && [ -f "/harvester/pyproject.toml" ]; then
    echo "Installing harvester package with uv..."
    uv pip install -e /harvester
fi

# Ensure DB schema exists before worker starts processing jobs.
if [ -d "/harvester" ] && [[ "$*" == *"src.infra.worker"* ]]; then
    echo "Bootstrapping harvester DB schema..."
    python - <<'PY'
from toolmeta_models import Base
from toolmeta_harvester.db.engine import engine
import toolmeta_harvester.db.models  # ensure all ORM models are imported

Base.metadata.create_all(bind=engine)
PY

    # Mark current Alembic head without replaying historical migrations
    # because a fresh DB is created from current ORM metadata above.
    if [ -f "/harvester/alembic.ini" ]; then
        (cd /harvester && alembic stamp head)
    fi

    # Clean stale RQ registry entries so rq-dashboard does not crash.
    echo "Cleaning stale RQ job registry entries..."
    python /code/scripts/cleanup_stale_rq_jobs.py || true
fi

# Run the passed command
exec "$@"

