"""Scheduled public GXRC collection for the standalone 职达岗位雷达 catalog."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.radar import JobRadarStore  # noqa: E402
from app.radar_sources import GxrcPublicCollector  # noqa: E402

DATA_DIR = ROOT / "data"
REPORT_PATH = DATA_DIR / "job-radar-last-sync.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public Guangxi Talent Network jobs")
    parser.add_argument("--pages", type=int, default=20, help="Public all-category result pages to collect")
    parser.add_argument("--min-jobs", type=int, default=0, help="Minimum jobs required before importing")
    args = parser.parse_args()

    collector = GxrcPublicCollector()
    try:
        jobs, collection = collector.collect(pages=args.pages)
    except Exception as exc:  # Keep a durable failure report for unexpected upstream errors.
        report = {
            "ok": False,
            "guard_rejected": True,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 2
    minimum_jobs = args.min_jobs or max(50, min(200, args.pages * 50 // 4))
    if len(jobs) < minimum_jobs:
        report = {
            "ok": False,
            "guard_rejected": True,
            "minimum_jobs": minimum_jobs,
            "discovered": len(jobs),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            **collection,
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 2

    store = JobRadarStore(DATA_DIR / "job-radar.sqlite3")
    store.initialize()
    imported = store.import_jobs(jobs, replace=False)
    active_before = store.job_count()
    expired = store.expire_stale_jobs(days=30, max_deactivation_ratio=0.10)
    report = {
        "ok": True,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "group_name": "all-categories",
        **collection,
        **imported,
        "expired": expired,
        "active_jobs_before_expiry": active_before,
        "active_jobs": store.job_count(),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
