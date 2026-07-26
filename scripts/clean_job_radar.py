#!/usr/bin/env python3
"""Deactivate job-radar records older than the public window or marked unavailable."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.radar import RADAR_MAX_PUBLISHED_DAYS, JobRadarStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up expired/inactive/unavailable job records.")
    parser.add_argument(
        "--days", type=int, default=RADAR_MAX_PUBLISHED_DAYS, help="Max published days cutoff (default: 30)"
    )
    parser.add_argument("--stale-days", type=int, default=30, help="Max captured stale days cutoff (default: 30)")
    parser.add_argument("--apply", action="store_true", help="Apply the cleanup; default is preview only")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without modifying database")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run cannot be used together")

    radar = JobRadarStore(PROJECT_ROOT / "data" / "job-radar.sqlite3")
    radar.initialize()

    before_count = radar.job_count()
    result = radar.cleanup_inactive_jobs(
        max_published_days=args.days,
        max_stale_days=args.stale_days,
        dry_run=not args.apply,
        max_deactivation_ratio=0.10,
    )
    after_count = radar.job_count()

    output = {
        "status": "success" if args.apply and not result.get("guard_blocked") else "dry-run",
        "before_active_jobs": before_count,
        "after_active_jobs": after_count,
        "summary": result,
    }
    print(output)


if __name__ == "__main__":
    main()
