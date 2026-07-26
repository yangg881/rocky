#!/usr/bin/env python3
"""Read-only health check for the job radar catalog and its last sync report."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "job-radar.sqlite3"
REPORT_PATH = ROOT / "data" / "job-radar-last-sync.json"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        active = int(conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0])
    finally:
        conn.close()

    issues: list[str] = []
    report: dict = {}
    if REPORT_PATH.exists():
        try:
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            issues.append("last sync report is unreadable")
    else:
        issues.append("last sync report is missing")

    if not report.get("ok"):
        issues.append("last sync was rejected or failed")
        error = str(report.get("error") or "")
        failures = report.get("failures") or []
        if error:
            issues.append(f"upstream error: {error[:180]}")
        elif failures:
            issues.append(f"upstream error: {str(failures[0])[:180]}")
    finished_at = str(report.get("finished_at") or "")
    if finished_at:
        try:
            finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - finished.astimezone(timezone.utc)).total_seconds() / 3600
            if age_hours > 8:
                issues.append(f"last sync is {age_hours:.1f} hours old")
        except ValueError:
            issues.append("last sync timestamp is invalid")
    expected = int(report.get("active_jobs") or 0)
    if expected and active < max(100, int(expected * 0.90)):
        issues.append(f"active jobs dropped below 90% of last sync ({active} vs {expected})")

    result = {
        "ok": not issues,
        "total_jobs": total,
        "active_jobs": active,
        "last_sync_finished_at": finished_at,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
