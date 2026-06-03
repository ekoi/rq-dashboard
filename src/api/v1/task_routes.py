import os
from importlib import import_module

import redis
from fastapi import APIRouter
from rq import Queue

try:
    from src.infra.task import long_task
except ModuleNotFoundError:
    long_task = import_module("infra.task").long_task

router = APIRouter()

redis_conn = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)
q = Queue(connection=redis_conn)


@router.get("/")
def root():
    return {"message": "RQ + FastAPI running"}


@router.post("/task")
def run_task(x: int, y: int):
    job = q.enqueue(long_task, x, y)
    return {"job_id": job.id}


@router.get("/result/{job_id}")
def get_result(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        return {"status": "not found"}
    return {
        "status": job.get_status(),
        "result": job.return_value,
    }


