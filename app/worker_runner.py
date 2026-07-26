"""Run the persistent RQ worker using the application's own settings."""

from redis import Redis
from rq import Queue, Worker

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise SystemExit("REDIS_URL is required")
    connection = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(settings.task_queue_name, connection=connection)], connection=connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
