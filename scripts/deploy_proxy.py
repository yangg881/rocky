#!/usr/bin/env python3
"""Deploy the sing-box proxy solution to the remote server."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import paramiko

HOST = "115.120.206.64"
USER = "root"
PASS = "125389abcD@"
LOCAL_DIR = Path(r"C:\Users\Administrator\Desktop\简历生成器\output\proxy-solution")
REMOTE_DIR = "/opt/jd-resume-ai/proxy"


def ssh_client():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=20, banner_timeout=20, allow_agent=False, look_for_keys=False)
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def sftp_put(sftp, local: Path, remote: str, mode: int = 0o644):
    sftp.put(str(local), remote)
    sftp.chmod(remote, mode)


def main() -> int:
    client = ssh_client()
    sftp = client.open_sftp()
    print(f"Connected to {HOST}")

    # Step 1: stop old broken xray, backup, create proxy dir
    print("\n[Step 1] Stop old xray and prepare proxy directory")
    cmds = [
        "timeout 5 pkill -9 -f '/opt/jd-resume-ai/xray/config' || true",
        "mkdir -p /opt/jd-resume-ai/proxy",
        "if [ -d /opt/jd-resume-ai/xray ]; then mv /opt/jd-resume-ai/xray /opt/jd-resume-ai/xray.bak.$(date +%Y%m%d-%H%M%S); fi",
    ]
    for c in cmds:
        code, out, err = run(client, c, timeout=15)
        print(f"  $ {c}\n  code={code}\n  out={out.strip()}\n  err={err.strip()}")
        # pkill may return 1 if no process matched; that's ok
        if code not in (0, 1, -1):
            print("FAILED")
            return 1

    # Step 2: upload files
    print("\n[Step 2] Upload files")
    sftp_put(sftp, LOCAL_DIR / "gen_singbox_config.py", f"{REMOTE_DIR}/gen_singbox_config.py", 0o755)
    sftp_put(sftp, LOCAL_DIR / "radar_proxy_probe.py", f"{REMOTE_DIR}/radar_proxy_probe.py", 0o755)
    sftp_put(sftp, LOCAL_DIR / "jd-resume-radar-proxy.service", "/tmp/jd-resume-radar-proxy.service", 0o644)
    print("  uploaded")

    # Step 3: generate config, validate, install service, start
    print("\n[Step 3] Generate config and install service")
    cmds = [
        f"/opt/jd-resume-ai/.venv/bin/python {REMOTE_DIR}/gen_singbox_config.py --out {REMOTE_DIR}/singbox_radar.json",
        f"/usr/local/bin/sing-box check -c {REMOTE_DIR}/singbox_radar.json",
        "cp /tmp/jd-resume-radar-proxy.service /etc/systemd/system/",
        "systemctl daemon-reload",
        "systemctl enable jd-resume-radar-proxy.service",
        "systemctl start jd-resume-radar-proxy.service",
        "sleep 3 && systemctl status jd-resume-radar-proxy.service --no-pager",
    ]
    for c in cmds:
        code, out, err = run(client, c, timeout=90)
        print(f"  $ {c}\n  code={code}\n  out={out[:400].strip()}\n  err={err[:400].strip()}")
        if code != 0:
            print("FAILED")
            return 1

    # Step 4: verify proxy unblocks GXRC
    print("\n[Step 4] Verify proxy unblocks GXRC")
    code, out, err = run(
        client,
        """
curl -s -m 30 -x http://127.0.0.1:8118 -X POST 'https://s.gxrc.com/api/Position/Search?districtId=2&from=0' \
  -H 'Content-Type: application/json-patch+json' \
  -H 'User-Agent: Mozilla/5.0 Chrome/126' \
  -H 'Referer: https://s.gxrc.com/sJob?keyword=' \
  -d '{"page":1,"pageSize":10,"orderBy":"0","keyword":"","schType":1}' | head -c 120
""",
        timeout=40,
    )
    print(f"  code={code}\n  out={out.strip()}")
    if '"code":1' not in out and "totalCount" not in out:
        print("  WARNING: GXRC did not return expected data")

    sftp.close()
    client.close()
    print("\nProxy deployment complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
