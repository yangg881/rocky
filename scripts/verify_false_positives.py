import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "data" / "job-radar.sqlite3"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

now = datetime.now(timezone.utc)
pub_30d = (now - timedelta(days=30)).isoformat()

# 1. Total jobs in database
total_all = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

# 2. Currently active jobs
currently_active = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]

# 3. Jobs published within 30 days and NOT marked as unavailable
valid_pub_30d = conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE (source_detail_status IS NULL OR source_detail_status != 'unavailable') AND published_at >= ?",
    (pub_30d,)
).fetchone()[0]

# 4. Jobs marked as unavailable
unavailable_count = conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE source_detail_status = 'unavailable'"
).fetchone()[0]

# 5. Sample of jobs that were deactivated due to captured_at
sample_deactivated = conn.execute(
    "SELECT id, title, company, source_url, captured_at, published_at FROM jobs WHERE is_active = 0 AND (source_detail_status IS NULL OR source_detail_status != 'unavailable') AND published_at >= ? LIMIT 5",
    (pub_30d,)
).fetchall()

print(f"Total jobs in DB: {total_all}")
print(f"Currently active: {currently_active}")
print(f"Valid 30d jobs (not unavailable): {valid_pub_30d}")
print(f"Unavailable dead link jobs: {unavailable_count}")
print("\nSample of mis-deactivated jobs:")
for r in sample_deactivated:
    print(dict(r))
