"""Idempotently upload the licensed source Word templates and catalogue metadata."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.metadata_store import MetadataStore
from app.storage import ObjectStore
from app.template_catalog import catalog_key, default_templates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Folder containing the curated template folders")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(args.source)
    if not root.is_dir():
        raise SystemExit(f"Template source folder does not exist: {root}")
    settings = get_settings()
    files = ObjectStore(settings)
    store = MetadataStore(files, settings.database_url) if settings.database_url else files
    if isinstance(store, MetadataStore):
        store.initialize()
    imported = 0
    for template in default_templates():
        source = root / template["source_folder"] / template["source_file"]
        if not source.is_file():
            raise SystemExit(f"Missing expected template: {source}")
        data = source.read_bytes()
        if not data.startswith(b"PK"):
            raise SystemExit(f"Invalid docx package: {source}")
        if not args.dry_run:
            store.put_bytes("c", template["source_key"], data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            template["source_size"] = len(data)
            store.put_json("a", catalog_key(template["id"]), template)
        imported += 1
        print(f"{'would import' if args.dry_run else 'imported'} {template['id']} {template['name']}")
    print(f"TEMPLATES={imported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
