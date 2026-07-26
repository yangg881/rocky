#!/usr/bin/env python3
"""Convenience alias to run build_and_publish_apk.py."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_and_publish_apk

if __name__ == "__main__":
    build_and_publish_apk.main()
