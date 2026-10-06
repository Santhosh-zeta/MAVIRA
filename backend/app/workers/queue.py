"""Dispatch assessment runs: Redis/RQ worker in Docker, or an in-process thread
for single-process development."""
from __future__ import annotations

import threading

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
JOB = "app.services.pipeline.orchestrator.run_assessment"


def dispatch(run_id: str) -> str:
    s = get_settings()
    if s.worker_mode.lower() == "rq":
        try:
            from redis import Redis
            from rq import Queue
            q = Queue("assessments", connection=Redis.from_url(s.redis_url))
            q.enqueue(JOB, run_id, job_timeout=3600, result_ttl=86400)
            return "rq"
        except Exception as exc:  # noqa: BLE001 - fall back so the run is never lost
            log.error("rq enqueue failed, running inline", extra={"error": str(exc)})
    from app.services.pipeline.orchestrator import run_assessment
    threading.Thread(target=run_assessment, args=(run_id,), daemon=True, name=f"run-{run_id[:8]}").start()
    return "inline"
