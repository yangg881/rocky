"""RQ worker entrypoints kept small so retries use the same task logic."""

from __future__ import annotations

import asyncio
from typing import Any


def process_jd_task(**kwargs: Any) -> None:
    from app.main import process_jd_job

    asyncio.run(process_jd_job(**(kwargs | {"raise_on_failure": True})))


def process_generation_task(**kwargs: Any) -> None:
    from app.main import process_generation_job

    asyncio.run(process_generation_job(**(kwargs | {"raise_on_failure": True})))
