"""Reliable Redis/RQ dispatch with a local BackgroundTasks fallback for tests."""

from __future__ import annotations

from typing import Any

from redis import Redis
from rq import Queue, Retry

from app.config import Settings


class TaskQueue:
    def __init__(self, settings: Settings):
        self.enabled = bool(settings.task_queue_enabled and settings.redis_url)
        self._queue: Queue | None = None
        if self.enabled:
            connection = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=5)
            self._queue = Queue(settings.task_queue_name, connection=connection, default_timeout=600)

    def enqueue(self, function: str, *, job_id: str, kwargs: dict[str, Any]) -> bool:
        if not self._queue:
            return False
        self._queue.enqueue(
            function,
            kwargs=kwargs,
            job_id=job_id,
            retry=Retry(max=2, interval=[30, 120]),
            result_ttl=86_400,
            failure_ttl=604_800,
        )
        return True

    def cancel(self, job_id: str) -> None:
        if self._queue:
            job = self._queue.fetch_job(job_id)
            if job:
                job.cancel()
