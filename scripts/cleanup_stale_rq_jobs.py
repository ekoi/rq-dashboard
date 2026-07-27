#!/usr/bin/env python3
"""Remove stale RQ registry entries whose job records no longer exist in Redis.

This prevents the rq-dashboard from crashing with:
  AttributeError: 'NoneType' object has no attribute 'id'

Run manually:
  python scripts/cleanup_stale_rq_jobs.py
  python scripts/cleanup_stale_rq_jobs.py --redis-url redis://localhost:6379
  python scripts/cleanup_stale_rq_jobs.py --dry-run

It is also executed automatically by entrypoint.sh on worker startup.
"""

from __future__ import annotations

import argparse
import os

import redis
from rq import Queue
from rq.registry import (
    DeferredJobRegistry,
    FailedJobRegistry,
    FinishedJobRegistry,
    ScheduledJobRegistry,
    StartedJobRegistry,
)


def build_registries(q: Queue):
    return [
        StartedJobRegistry(queue=q),
        FailedJobRegistry(queue=q),
        FinishedJobRegistry(queue=q),
        DeferredJobRegistry(queue=q),
        ScheduledJobRegistry(queue=q),
    ]


def cleanup(redis_url: str, dry_run: bool) -> int:
    conn = redis.from_url(redis_url)
    q = Queue(connection=conn)
    removed = 0

    for registry in build_registries(q):
        job_ids = registry.get_job_ids()
        for job_id in job_ids:
            # For WIP/started, the key may be "job_id:execution_id"
            bare_job_id = job_id.split(":")[0]
            key = f"rq:job:{bare_job_id}"
            if not conn.exists(key):
                print(f"  stale [{registry.__class__.__name__}] {job_id}")
                if not dry_run:
                    registry.remove(job_id, delete_job=False)
                removed += 1

    if removed:
        action = "would remove" if dry_run else "removed"
        print(f"{action} {removed} stale job reference(s)")
    else:
        print("no stale entries found")

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove stale RQ job registry entries")
    parser.add_argument(
        "--redis-url",
        default=os.environ.get(
            "REDIS_URL",
            f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', '6379')}",
        ),
        help="Redis URL (default: from REDIS_URL env or redis://localhost:6379)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stale entries without removing them",
    )
    args = parser.parse_args()

    print(f"Connecting to {args.redis_url}")
    cleanup(args.redis_url, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

