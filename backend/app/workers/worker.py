"""RQ worker entry point: python -m app.workers.worker"""
from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

from app.core.config import get_settings
from app.core.logging import configure_logging


def main() -> None:
    configure_logging()
    conn = Redis.from_url(get_settings().redis_url)
    Worker([Queue("assessments", connection=conn)], connection=conn).work(with_scheduler=False)


if __name__ == "__main__":
    main()
