# rq-dashboard

## Run API server

Run the FastAPI app directly from `src/main.py` (Uvicorn is started by the script).

PyCharm run/debug (Script path):

- Script path: `src/main.py`
- Working directory: project root (`rq-dashboard`)
- Optional env: `EXPOSE_PORT=12104`

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
python -u src/main.py
```

Optional environment variables:

- `EXPOSE_PORT` (default: `12104`)
- `BASE_DIR` (optional; defaults to the project root, parent of `conf/`)

Example with custom port:

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
EXPOSE_PORT=12104 python -u src/main.py
```

## Docker Compose

Start all services (`redis`, `api`, `worker`, `dashboard`):

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
docker compose up --build -d
```

## Trigger and watch a HAL harvest

The helper script submits a HAL harvest job and polls until it finishes:

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
python scripts/harvest_hal_watch.py --base-url http://localhost:12104 --detail
```

Watch an existing job instead:

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
python scripts/harvest_hal_watch.py --job-id <job-id> --watch-only --detail
```

If the RQ Dashboard ever shows a stale loading page again, check and remove orphaned
entries from Redis:

```zsh
HARVESTER_DIR=../toolmeta0719 docker compose exec redis redis-cli ZRANGE rq:wip:default 0 -1
```

Endpoints:

- API: `http://localhost:12104/`
- RQ Dashboard: `http://localhost:9181/`

Useful commands:

```zsh
cd /Users/akmi/dev/work/datacommons/rq-dashboard
docker compose ps
docker compose logs -f api worker
docker compose down
```

