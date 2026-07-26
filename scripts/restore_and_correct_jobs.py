#!/usr/bin/env python3
"""Restore only the known false-positive incident batches after review."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "job-radar.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a bounded, timestamped false-positive batch")
    parser.add_argument("--updated-from", required=True, help="Incident window start in ISO format")
    parser.add_argument("--updated-to", required=True, help="Incident window end in ISO format")
    parser.add_argument("--published-within-days", type=int, default=30)
    parser.add_argument("--max-restore", type=int, default=20000)
    parser.add_argument("--apply", action="store_true", help="Apply the targeted restore; default is preview only")
    args = parser.parse_args()

    try:
        start = datetime.fromisoformat(args.updated_from.replace("Z", "+00:00"))
        end = datetime.fromisoformat(args.updated_to.replace("Z", "+00:00"))
    except ValueError as exc:
        parser.error(f"invalid ISO timestamp: {exc}")
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        parser.error("timestamps must include a timezone and start must be before end")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, args.published_within_days))).isoformat()

    conn = sqlite3.connect(DB_PATH)
    try:
        query = """SELECT id FROM jobs
                   WHERE is_active = 0 AND source_detail_status = 'unavailable'
                     AND source_url LIKE '%gxrc.com%'
                     AND updated_at >= ? AND updated_at <= ?
                     AND published_at >= ?
                   ORDER BY updated_at"""
        ids = [row[0] for row in conn.execute(query, (start.isoformat(), end.isoformat(), cutoff)).fetchall()]
        print(f"Matched {len(ids)} incident records in the requested window.")
        if len(ids) > args.max_restore:
            print(f"Refusing to restore more than {args.max_restore} records.", file=sys.stderr)
            return 2
        if args.apply and ids:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                """UPDATE jobs SET is_active=1, source_detail_status='',
                   link_check_failures=0, last_link_check_at=?, last_link_check_status='restored',
                   updated_at=? WHERE id=?""",
                [(now, now, job_id) for job_id in ids],
            )
            conn.commit()
            print(f"Restored {len(ids)} records.")
        else:
            print("Preview only; database was not changed.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
