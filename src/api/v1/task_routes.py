import os
from importlib import import_module
import redis
from fastapi import APIRouter, HTTPException
from rq import Queue
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry
try:
    from src.infra.task import PROVIDER_REGISTRY, run_harvest, long_task
except ModuleNotFoundError:
    _task = import_module("infra.task")
    PROVIDER_REGISTRY = _task.PROVIDER_REGISTRY
    run_harvest = _task.run_harvest
    long_task = _task.long_task
router = APIRouter()
redis_conn = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)
q = Queue(connection=redis_conn)
started_registry = StartedJobRegistry(queue=q)
finished_registry = FinishedJobRegistry(queue=q)
failed_registry = FailedJobRegistry(queue=q)
def _job_summary(job_id: str) -> dict:
    job = q.fetch_job(job_id)
    if job is None:
        return {"job_id": job_id, "status": "not found"}
    payload = {
        "job_id": job.id,
        "status": job.get_status(),
        "result": job.return_value,
    }
    if job.is_failed:
        payload["error"] = job.exc_info
    return payload
@router.get("/")
def root():
    return {"message": "RQ + FastAPI running"}
@router.post("/task")
def run_task(x: int, y: int):
    job = q.enqueue(long_task, x, y)
    return {"job_id": job.id}
@router.get("/harvest/providers")
def list_providers():
    """Return all registered harvest providers."""
    return {"providers": list(PROVIDER_REGISTRY.keys())}
@router.post("/harvest/{provider}")
def trigger_harvest(provider: str):
    """Enqueue a harvest job for the given provider.
    Known providers: hal, vip, biobb, workflowhub, usegalaxy-org
    """
    if provider not in PROVIDER_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider '{provider}'. "
                   f"Known providers: {', '.join(sorted(PROVIDER_REGISTRY))}",
        )
    job = q.enqueue(run_harvest, provider, job_timeout=7200)
    return {"job_id": job.id, "provider": provider, "status": "queued"}
@router.get("/result/{job_id}")
def get_result(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        return {"status": "not found"}
    payload = {
        "status": job.get_status(),
        "result": job.return_value,
    }
    if job.is_failed:
        payload["error"] = job.exc_info
    return payload
@router.get("/result/{job_id}/detail")
def get_result_detail(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        return {"status": "not found"}
    payload = {
        "status": job.get_status(),
        "result": job.return_value,
    }
    if job.is_failed:
        payload["exc_info"] = job.exc_info
    return payload
@router.get("/jobs")
def list_jobs(limit: int = 20):
    limit = max(1, min(limit, 100))
    job_ids = []
    for registry in (started_registry, failed_registry, finished_registry):
        job_ids.extend(registry.get_job_ids())
    seen: set[str] = set()
    unique_ids: list[str] = []
    for job_id in job_ids:
        if job_id in seen:
            continue
        seen.add(job_id)
        unique_ids.append(job_id)
    return {"jobs": [_job_summary(job_id) for job_id in unique_ids[:limit]]}
