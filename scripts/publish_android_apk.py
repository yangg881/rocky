"""Publish the Android installer to TOS so installation traffic bypasses the app server."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.storage import ObjectStore  # noqa: E402

apk_path = PROJECT_ROOT / "app/static/downloads/zhiday-resume-android.apk"
if not apk_path.is_file():
    raise SystemExit(f"APK not found: {apk_path}")

store = ObjectStore(get_settings())
key = "releases/zhiday-resume-android-1.8.11.apk"
store.put_bytes("b", key, apk_path.read_bytes(), "application/vnd.android.package-archive")
print(f"Published {apk_path.stat().st_size} bytes to TOS bucket B: {key}")
