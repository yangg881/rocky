#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report md5 drift between the local git tree and the running server.

Flags any server-relevant file that differs (server was hand-edited, or a deploy
was missed). Read-only: never writes to the server.

    SYNC_HOST=115.120.206.64 SYNC_USER=root SYNC_PASSWORD=*** \
        python deploy/check_parity.py
"""
from __future__ import annotations
import hashlib, os, subprocess, sys

REMOTE_ROOT = "/opt/jd-resume-ai"
INCLUDE_PREFIXES = ("app/",)
INCLUDE_TOPLEVEL = {"config.py", "observability.py", "security.py", "self_test.py",
                    "requirements.txt", "pyproject.toml"}
EXCLUDE = ("/__pycache__/", ".env")


def sh(*a): return subprocess.check_output(a, encoding="utf-8", errors="replace").strip()


def main() -> int:
    root = sh("git", "rev-parse", "--show-toplevel"); os.chdir(root)
    files = [f for f in sh("git", "ls-files").splitlines()
             if not any(x in f for x in EXCLUDE)
             and (f.startswith(INCLUDE_PREFIXES) or f in INCLUDE_TOPLEVEL)]

    host = os.environ.get("SYNC_HOST", "115.120.206.64")
    user = os.environ.get("SYNC_USER", "root")
    pwd = os.environ.get("SYNC_PASSWORD"); key = os.environ.get("SYNC_KEY")
    if not pwd and not key:
        print("ERROR: set SYNC_PASSWORD or SYNC_KEY.", file=sys.stderr); return 2

    import paramiko
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(hostname=host, username=user, timeout=25, allow_agent=False, look_for_keys=False)
    kw["key_filename"] = key if key else None
    if not key:
        kw["password"] = pwd
    kw = {k: v for k, v in kw.items() if v is not None}
    c.connect(**kw)

    paths = " ".join(f"'{REMOTE_ROOT}/{f}'" for f in files)
    _, so, _ = c.exec_command(f"md5sum {paths} 2>/dev/null", timeout=120)
    remote = {}
    for line in so.read().decode("utf-8", "replace").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            remote[parts[1].strip().replace(REMOTE_ROOT + "/", "")] = parts[0]
    c.close()

    drift, missing, ok = [], [], 0
    for f in files:
        lm = hashlib.md5(open(f, "rb").read()).hexdigest()
        rm = remote.get(f)
        if rm is None:
            missing.append(f)
        elif rm != lm:
            drift.append(f)
        else:
            ok += 1

    print(f"in sync: {ok}/{len(files)}")
    for f in drift:
        print(f"  DRIFT   {f}  (server differs from local)")
    for f in missing:
        print(f"  MISSING {f}  (not present on server)")
    return 0 if not drift and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
