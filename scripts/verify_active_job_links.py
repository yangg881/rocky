#!/usr/bin/env python3
"""Conservatively check active GXRC links without mass-deactivating records."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "job-radar.sqlite3"
REPORT_PATH = ROOT / "data" / "job-radar-last-link-check.json"
INVALID_TOKENS = tuple(
    token
    for token in (
        "\u804c\u4f4d\u4e0d\u5b58\u5728",
        "\u5c97\u4f4d\u4e0d\u5b58\u5728",
        "\u804c\u4f4d\u5df2\u8fc7\u671f",
        "\u5c97\u4f4d\u5df2\u8fc7\u671f",
        "\u804c\u4f4d\u5df2\u4e0b\u67b6",
        "\u5c97\u4f4d\u5df2\u4e0b\u67b6",
        "\u627e\u4e0d\u5230\u8be5\u804c\u4f4d",
    )
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36"
}


def checked_url(source_url: str) -> str:
    return source_url.replace("://www.gxrc.com/", "://m.gxrc.com/")


def check_job(job: sqlite3.Row, timeout: float) -> tuple[str, str]:
    source_url = str(job["source_url"] or "").strip()
    if not source_url:
        return str(job["id"]), "unknown"
    request = Request(checked_url(source_url), headers=HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            final_url = response.geturl()
            title_match = TITLE_RE.search(body)
            title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
            if "NoPosition" in final_url or any(token in title for token in INVALID_TOKENS):
                return str(job["id"]), "invalid"
            if "\u62db\u8058\u804c\u4f4d\u4fe1\u606f" in title or (
                "window.__NUXT__" in body and "positionName" in body
            ):
                return str(job["id"]), "valid"
            return str(job["id"]), "unknown"
    except HTTPError as exc:
        return str(job["id"]), "invalid" if exc.code in {404, 410} else "unknown"
    except (TimeoutError, URLError, OSError):
        return str(job["id"]), "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GXRC job links with a multi-failure safety gate")
    parser.add_argument("--apply", action="store_true", help="Write link-check state and confirmed deactivations")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--require-failures", type=int, default=3)
    parser.add_argument("--max-deactivate-ratio", type=float, default=0.10)
    parser.add_argument("--max-deactivate-count", type=int, default=0)
    parser.add_argument("--max-rows", type=int, default=0, help="Only check this many rows; useful for smoke tests")
    args = parser.parse_args()
    if args.require_failures < 1 or args.concurrency < 1:
        parser.error("--require-failures and --concurrency must be positive")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        query = """SELECT id, source_url, link_check_failures
                   FROM jobs WHERE is_active = 1 AND source_url LIKE '%gxrc.com%'
                   ORDER BY updated_at DESC"""
        if args.max_rows > 0:
            query += f" LIMIT {int(args.max_rows)}"
        rows = conn.execute(query).fetchall()
        active_count = int(conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0])
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(check_job, row, args.timeout) for row in rows]
            for future in as_completed(futures):
                job_id, status = future.result()
                results[job_id] = status

        now = datetime.now(timezone.utc).isoformat()
        candidates: list[tuple[str, int]] = []
        for row in rows:
            status = results.get(str(row["id"]), "unknown")
            failures = int(row["link_check_failures"] or 0)
            next_failures = failures + 1 if status == "invalid" else 0
            if status == "invalid" and next_failures >= args.require_failures:
                candidates.append((str(row["id"]), next_failures))

        limit = max(100, math.ceil(active_count * max(0.0, args.max_deactivate_ratio)))
        if args.max_deactivate_count > 0:
            limit = min(limit, args.max_deactivate_count)
        guard_blocked = bool(args.apply and len(candidates) > limit)
        if args.apply and not guard_blocked:
            for row in rows:
                job_id = str(row["id"])
                status = results.get(job_id, "unknown")
                failures = int(row["link_check_failures"] or 0)
                next_failures = failures + 1 if status == "invalid" else 0
                conn.execute(
                    """UPDATE jobs SET link_check_failures=?, last_link_check_at=?,
                       last_link_check_status=?, source_detail_status=CASE
                       WHEN ? = 'valid' AND is_active = 1 THEN ''
                       ELSE source_detail_status END, updated_at=? WHERE id=?""",
                    (next_failures, now, status, status, now, job_id),
                )
            conn.executemany(
                """UPDATE jobs SET is_active=0, source_detail_status='unavailable',
                   updated_at=? WHERE id=?""",
                [(now, job_id) for job_id, _ in candidates],
            )
            conn.commit()

        counts = {
            status: sum(1 for value in results.values() if value == status)
            for status in ("valid", "invalid", "unknown")
        }
        report = {
            "ok": not guard_blocked,
            "finished_at": now,
            "apply": bool(args.apply),
            "checked": len(rows),
            "active_jobs": active_count,
            "counts": counts,
            "confirmed_deactivation_candidates": len(candidates),
            "deactivation_limit": limit,
            "guard_blocked": guard_blocked,
            "abort_reason": "confirmed failures exceed safety limit" if guard_blocked else "",
        }
        DATA_DIR = REPORT_PATH.parent
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 2 if guard_blocked else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
