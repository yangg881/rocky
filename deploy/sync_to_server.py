#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-way deploy: local git working tree -> server /opt/jd-resume-ai.

Local git is the single source of truth. The server is a pull consumer and must
never be hand-edited. This script pushes the server-relevant, git-tracked files
(app/** plus top-level *.py / requirements) to the server, verifying an exact
md5 match for every file, then restarts the app + worker and smoke-tests.

Credentials come from the environment (never commit them). Prefer SSH keys; the
password path exists only for the current transition period:

    SYNC_HOST=115.120.206.64  SYNC_USER=root  SYNC_PASSWORD=***  \
        python deploy/sync_to_server.py [--restart] [--dry-run]

Requires: paramiko  (pip install paramiko)
"""
from __future__ import annotations
import base64
import hashlib
import os
import subprocess
import sys

REMOTE_ROOT = "/opt/jd-resume-ai"
# Files whose local edits should propagate to the running server.
INCLUDE_PREFIXES = ("app/",)
INCLUDE_TOPLEVEL = {
    "config.py", "observability.py", "security.py", "self_test.py",
    "requirements.txt", "pyproject.toml",
}
# Never push these even if tracked (server owns them / not runtime).
EXCLUDE_SUBSTRINGS = ("/__pycache__/", ".env")


def sh(*args: str) -> str:
    return subprocess.check_output(args, encoding="utf-8", errors="replace").strip()


def tracked_files() -> list[str]:
    repo_root = sh("git", "rev-parse", "--show-toplevel")
    os.chdir(repo_root)
    files = sh("git", "ls-files").splitlines()
    out = []
    for f in files:
        if any(x in f for x in EXCLUDE_SUBSTRINGS):
            continue
        if f.startswith(INCLUDE_PREFIXES) or f in INCLUDE_TOPLEVEL:
            out.append(f)
    return out


def md5_local(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def main() -> int:
    restart = "--restart" in sys.argv
    dry = "--dry-run" in sys.argv
    host = os.environ.get("SYNC_HOST", "115.120.206.64")
    user = os.environ.get("SYNC_USER", "root")
    pwd = os.environ.get("SYNC_PASSWORD")
    key = os.environ.get("SYNC_KEY")  # path to private key, preferred
    if not pwd and not key:
        print("ERROR: set SYNC_PASSWORD or SYNC_KEY (SSH key preferred).", file=sys.stderr)
        return 2

    import paramiko

    files = tracked_files()
    print(f"{len(files)} tracked server files to sync -> {user}@{host}:{REMOTE_ROOT}")
    if dry:
        for f in files:
            print("  would push", f)
        return 0

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kw = dict(hostname=host, username=user, timeout=25, allow_agent=False, look_for_keys=False)
    if key:
        connect_kw["key_filename"] = key
    else:
        connect_kw["password"] = pwd
    client.connect(**connect_kw)

    def run(cmd: str, stdin_data: str | None = None, timeout: int = 120):
        si, so, se = client.exec_command(cmd, timeout=timeout)
        if stdin_data is not None:
            si.write(stdin_data); si.flush(); si.channel.shutdown_write()
        out = so.read().decode("utf-8", "replace")
        err = se.read().decode("utf-8", "replace")
        return so.channel.recv_exit_status(), out, err

    # Snapshot before overwriting anything.
    rc, out, _ = run("date +%Y%m%d-%H%M%S")
    ts = out.strip()
    backup = f"{REMOTE_ROOT}/.deploy-backups/sync-{ts}"
    run(f"mkdir -p '{backup}'")

    failures = []
    for f in files:
        remote = f"{REMOTE_ROOT}/{f}"
        rdir = remote.rsplit("/", 1)[0]
        run(f"mkdir -p '{rdir}'")
        run(f"[ -f '{remote}' ] && install -D '{remote}' '{backup}/{f}' || true")
        with open(f, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        tmp = remote + ".upload.tmp"
        rc, out, err = run(f"base64 -d > '{tmp}' && mv -f '{tmp}' '{remote}' && md5sum '{remote}'", stdin_data=b64)
        rmd5 = out.split()[0] if out.split() else ""
        if rmd5 != md5_local(f):
            failures.append((f, rmd5, err.strip()))
            print(f"  MISMATCH {f}: local={md5_local(f)} remote={rmd5} {err.strip()}")
        else:
            print(f"  ok {f}")

    if failures:
        print(f"\n{len(failures)} file(s) failed md5 verification. Backup at {backup}. Aborting restart.", file=sys.stderr)
        client.close()
        return 1

    # Import-check before touching the running service.
    rc, out, err = run(
        "sudo -u jdresume bash -c 'cd /opt/jd-resume-ai && set -a && . ./.env && set +a && "
        ".venv/bin/python -c \"import app.main\"'"
    )
    if rc != 0:
        print(f"IMPORT CHECK FAILED (service NOT restarted). Backup at {backup}.\n{err}", file=sys.stderr)
        client.close()
        return 1
    print("import app.main OK")

    if restart:
        run("systemctl restart jd-resume-ai.service jd-resume-ai-worker.service jd-resume-worker.service")
        rc, out, _ = run("sleep 4; systemctl is-active jd-resume-ai.service; "
                         "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8100/")
        print("post-restart:", out.replace("\n", " "))
    else:
        print("(skipped restart; pass --restart to apply)")

    print(f"\nDone. Backup at {backup}.")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
