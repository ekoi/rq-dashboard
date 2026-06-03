import os
import uvicorn

import redis
from fastapi import FastAPI
from rq import Queue

try:
    from src.commons import app_settings, get_project_details
except ModuleNotFoundError:
    from commons import app_settings, get_project_details

try:
    from src.task import long_task
except ModuleNotFoundError:
    from task import long_task
APP_NAME = os.environ.get("APP_NAME", "RQ + FastAPI Service")

project_details = get_project_details(
    os.environ.get("BASE_DIR", os.getcwd()),
    ["name", "description", "version"],
)
APP_TITLE = project_details.get("name", APP_NAME)
APP_DESCRIPTION = project_details.get("description", "")
APP_VERSION = project_details.get("version", "0.0.0")


def get_expose_port() -> int:
    return int(os.environ.get("EXPOSE_PORT", "12104"))

import logging
from logging.handlers import TimedRotatingFileHandler

build_date = os.environ.get("BUILD_DATE", "unknown")
log_file = app_settings.get("log_file", "rqf.log")
os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",  # rotate every second for testing
    interval=1,
    backupCount=7,
    encoding="utf-8",
    utc=True
)
handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[handler]
)
app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, version=APP_VERSION)

redis_conn = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)
q = Queue(connection=redis_conn)

@app.get("/")
def root():
    return {"message": "RQ + FastAPI running"}

@app.post("/task")
def run_task(x: int, y: int):
    job = q.enqueue(long_task, x, y)
    return {"job_id": job.id}

@app.get("/result/{job_id}")
def get_result(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        return {"status": "not found"}
    return {
        "status": job.get_status(),
        "result": job.return_value
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_expose_port())
