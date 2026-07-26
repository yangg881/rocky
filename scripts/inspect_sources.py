import sqlite3
import urllib.parse
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "data" / "job-radar.sqlite3"
conn = sqlite3.connect(db_path)

rows = conn.execute("SELECT source_url FROM jobs WHERE is_active = 1").fetchall()
domains = {}
for (url,) in rows:
    netloc = urllib.parse.urlparse(url or "").netloc.lower()
    domains[netloc] = domains.get(netloc, 0) + 1

print("Job Source Domains:", domains)
