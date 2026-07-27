#!/usr/bin/env python3
"""Submit a HAL harvest job to rq-dashboard and poll it until it finishes.

Usage:
  python scripts/harvest_hal_watch.py
  python scripts/harvest_hal_watch.py --base-url http://localhost:12104
  python scripts/harvest_hal_watch.py --job-id <existing-job-id> --watch-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ApiResponse:
    status: str
    payload: dict[str, Any]


def _request_json(method: str, url: str) -> dict[str, Any]:
    request = Request(url, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", "application/json")

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc}") from exc


def submit_job(base_url: str) -> str:
    data = _request_json("POST", urljoin(base_url.rstrip("/") + "/", "harvest/hal"))
    job_id = data.get("job_id")
    if not job_id:
        raise RuntimeError(f"Missing job_id in response: {data}")
    print(f"Queued HAL harvest job: {job_id}")
    return str(job_id)


def fetch_job_status(base_url: str, job_id: str, detail: bool) -> ApiResponse:
    suffix = "/detail" if detail else ""
    data = _request_json(
        "GET",
        urljoin(base_url.rstrip("/") + "/", f"result/{job_id}{suffix}"),
    )
    status = str(data.get("status", "unknown"))
    return ApiResponse(status=status, payload=data)


def poll_job(base_url: str, job_id: str, detail: bool, interval: int, timeout: int) -> int:
    start = time.time()
    while True:
        response = fetch_job_status(base_url, job_id, detail)
        payload = response.payload
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))

        if response.status == "finished":
            return 0
        if response.status == "failed":
            return 1
        if response.status == "not found":
            return 2

        elapsed = time.time() - start
        if elapsed >= timeout:
            print(f"Timed out after {timeout}s waiting for job {job_id}", file=sys.stderr)
            return 3

        time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit and watch a HAL harvest job")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RQ_DASHBOARD_API_URL", "http://localhost:12104"),
        help="rq-dashboard API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--job-id",
        help="Existing job id to watch instead of submitting a new one",
    )
    parser.add_argument(
        "--watch-only",
        action="store_true",
        help="Do not submit a new harvest job; only watch --job-id",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Use the /result/<job_id>/detail endpoint while polling",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Stop after this many seconds (default: %(default)s)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 1:
        parser.error("--interval must be at least 1 second")
    if args.timeout < 1:
        parser.error("--timeout must be at least 1 second")

    if args.watch_only and not args.job_id:
        parser.error("--watch-only requires --job-id")

    job_id = args.job_id
    if not args.watch_only:
        job_id = submit_job(args.base_url)

    assert job_id is not None
    print(f"Watching job: {job_id}")
    return poll_job(args.base_url, job_id, args.detail, args.interval, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())

