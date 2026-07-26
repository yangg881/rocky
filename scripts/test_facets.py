from app.radar import JobRadarStore
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "data" / "job-radar.sqlite3"
store = JobRadarStore(db_path)
facets = store.facets()
print("Facets topics:", facets["topics"])
