import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "data" / "job-radar.sqlite3"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT id, title, company, source_url, source_detail_status, is_active, captured_at, published_at FROM jobs WHERE source_url LIKE '%3731874%' OR title LIKE '%政策项目申报专员%'"
).fetchall()

for r in rows:
    print(dict(r))
