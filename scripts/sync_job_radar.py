"""Scheduled multi-source collection for the standalone 职达岗位雷达 catalog.

Aggregates the public GXRC collector with any number of compliant JSON feeds
configured in data/job-feeds.json (a list of {"source": "<file-or-url>", "label": "..."}).
A failing source never blocks the others.

Usage:
    python scripts/sync_job_radar.py [--pages 20] [--feeds data/job-feeds.json]
"""

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
from app.radar_sources import GxrcPublicCollector, JsonFeedCollector, collect_all  # noqa: E402

DATA_DIR = ROOT / "data"
REPORT_PATH = DATA_DIR / "job-radar-last-sync.json"
DEFAULT_FEEDS = DATA_DIR / "job-feeds.json"


def load_feed_sources(feeds_path: Path) -> list:
    sources: list = [GxrcPublicCollector()]
    if feeds_path.exists():
        try:
            feeds = json.loads(feeds_path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            feeds = []
        for feed in feeds if isinstance(feeds, list) else []:
            src = feed.get("source") if isinstance(feed, dict) else None
            if not src:
                continue
            label = feed.get("label", src)
            sources.append(JsonFeedCollector(src, label=label))
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect jobs from all configured sources")
    parser.add_argument("--pages", type=int, default=20, help="GXRC public result pages to collect")
    parser.add_argument("--feeds", type=str, default=str(DEFAULT_FEEDS), help="Path to feeds JSON config")
    args = parser.parse_args()

    sources = load_feed_sources(Path(args.feeds))
    gxrc = sources[0]
    jobs, reports = collect_all(sources)
    # GXRC ignores pages arg positionally; re-run it with pages for completeness.
    gxrc_jobs, gxrc_meta = gxrc.collect(pages=args.pages)
    if gxrc_jobs and gxrc_jobs != jobs:
        jobs = gxrc_jobs + jobs

    if not jobs:
        report = {"ok": False, "finished_at": datetime.now(timezone.utc).isoformat(), "sources": reports}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 1

    store = JobRadarStore(DATA_DIR / "job-radar.sqlite3")
    store.initialize()
    imported = store.import_jobs(jobs, replace=False)
    expired = store.expire_stale_jobs(days=30)
    report = {
        "ok": True,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "sources": reports,
        "gxrc": gxrc_meta,
        **imported,
        "expired": expired,
        "active_jobs": store.job_count(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
