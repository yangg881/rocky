from app.radar import JobRadarStore
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "data" / "job-radar.sqlite3"
store = JobRadarStore(db_path)
res = store.recommend("test-user", "产品经理 运营", max_results=100, source="gxrc")
print("[SUCCESS] recommend() returned:", res.matched_total, "jobs, jobs in list:", len(res.jobs))
