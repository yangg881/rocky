"""Copy the existing TOS metadata namespace into PostgreSQL safely and idempotently."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.metadata_store import MetadataStore
from app.storage import ObjectStore


def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is required")
    files = ObjectStore(settings)
    metadata = MetadataStore(files, settings.database_url)
    metadata.initialize()
    entries = files.iter_json_entries("a")
    for key, value in entries:
        metadata.put_json("a", key, value)
    print(f"Migrated {len(entries)} metadata records into PostgreSQL.")


if __name__ == "__main__":
    main()
