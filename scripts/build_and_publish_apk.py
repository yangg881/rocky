#!/usr/bin/env python3
"""Build and publish Android APK to local distribution paths and remote server in lockstep.

Usage:
    python scripts/build_and_publish_apk.py [--bump] [--no-deploy]

Flags:
    --bump       Automatically increment versionCode (+1) and patch versionName (1.8.17 -> 1.8.18)
    --no-deploy  Skip SSH/SCP upload to remote server (build and update local static files only)
"""

import sys
import os
import re
import subprocess
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = PROJECT_ROOT / "app" / "main.py"
GRADLE_KTS = PROJECT_ROOT / "android" / "app" / "build.gradle.kts"
RELEASE_APK_OUTPUT = PROJECT_ROOT / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
LOCAL_DIST_APK = PROJECT_ROOT / "android" / "dist" / "zhiday-resume-android.apk"
STATIC_DOWNLOAD_APK = PROJECT_ROOT / "app" / "static" / "downloads" / "zhiday-resume-android.apk"

REMOTE_HOST = "115.120.206.64"
REMOTE_USER = "root"
REMOTE_WWW_APK = "/var/www/zhiday-downloads/zhiday-resume-android.apk"
REMOTE_APP_APK = "/opt/jd-resume-ai/app/static/downloads/zhiday-resume-android.apk"
REMOTE_MAIN_PY = "/opt/jd-resume-ai/app/main.py"


def parse_main_py_version():
    content = MAIN_PY.read_text(encoding="utf-8")
    code_match = re.search(r"latest_code\s*=\s*(\d+)", content)
    name_match = re.search(r'latest_name\s*=\s*["\']([^"\']+)["\']', content)
    if not code_match or not name_match:
        raise ValueError("Could not parse latest_code or latest_name from app/main.py")
    return int(code_match.group(1)), name_match.group(1)


def parse_gradle_version():
    content = GRADLE_KTS.read_text(encoding="utf-8")
    code_match = re.search(r"versionCode\s*=\s*(\d+)", content)
    name_match = re.search(r'versionName\s*=\s*["\']([^"\']+)["\']', content)
    if not code_match or not name_match:
        raise ValueError("Could not parse versionCode or versionName from android/app/build.gradle.kts")
    return int(code_match.group(1)), name_match.group(1)


def update_versions(new_code: int, new_name: str):
    print(f"--> Bumping versions in main.py and build.gradle.kts to versionCode={new_code}, versionName={new_name}")
    
    # Update main.py
    content = MAIN_PY.read_text(encoding="utf-8")
    content = re.sub(r"latest_code\s*=\s*\d+", f"latest_code = {new_code}", content)
    content = re.sub(r'latest_name\s*=\s*["\'][^"\']+["\']', f'latest_name = "{new_name}"', content)
    content = re.sub(r'zhiday-resume-android-full-1\.8\.\d+\.apk', f'zhiday-resume-android-full-{new_name}.apk', content)
    MAIN_PY.write_text(content, encoding="utf-8")

    # Update build.gradle.kts
    gradle_content = GRADLE_KTS.read_text(encoding="utf-8")
    gradle_content = re.sub(r"versionCode\s*=\s*\d+", f"versionCode = {new_code}", gradle_content)
    gradle_content = re.sub(r'versionName\s*=\s*["\'][^"\']+["\']', f'versionName = "{new_name}"', gradle_content)
    GRADLE_KTS.write_text(gradle_content, encoding="utf-8")


def locate_java_home():
    if os.environ.get("JAVA_HOME") and os.path.isdir(os.environ["JAVA_HOME"]):
        return os.environ["JAVA_HOME"]
    as_jbr = Path(r"C:\Program Files\Android\Android Studio\jbr")
    if as_jbr.is_dir():
        return str(as_jbr)
    return None


def locate_android_home():
    if os.environ.get("ANDROID_HOME") and os.path.isdir(os.environ["ANDROID_HOME"]):
        return os.environ["ANDROID_HOME"]
    sdk_dir = Path(os.path.expanduser(r"~\AppData\Local\Android\Sdk"))
    if sdk_dir.is_dir():
        return str(sdk_dir)
    return None


def inspect_apk(apk_path: Path):
    with zipfile.ZipFile(apk_path, "r") as z:
        manifest_bytes = z.read("AndroidManifest.xml")
    cleaned = manifest_bytes.replace(b"\x00", b"")
    versions = re.findall(b"1\\.\\d+\\.\\d+", cleaned)
    version_name = versions[0].decode("utf-8") if versions else None
    return apk_path.stat().st_size, version_name


def main():
    args = sys.argv[1:]
    do_bump = "--bump" in args
    skip_deploy = "--no-deploy" in args

    main_code, main_name = parse_main_py_version()
    gradle_code, gradle_name = parse_gradle_version()

    print(f"[*] app/main.py:        versionCode={main_code}, versionName={main_name}")
    print(f"[*] build.gradle.kts:   versionCode={gradle_code}, versionName={gradle_name}")

    if do_bump:
        new_code = max(main_code, gradle_code) + 1
        parts = main_name.split(".")
        if len(parts) == 3 and parts[2].isdigit():
            new_name = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
        else:
            new_name = main_name
        update_versions(new_code, new_name)
        main_code, main_name = new_code, new_name
    else:
        if main_code != gradle_code or main_name != gradle_name:
            print("[!] WARNING: Version code/name mismatch between main.py and build.gradle.kts! Aligning to gradle version.")
            update_versions(gradle_code, gradle_name)
            main_code, main_name = gradle_code, gradle_name

    # Setup Environment
    java_home = locate_java_home()
    android_home = locate_android_home()
    if not java_home:
        sys.exit("[!] ERROR: JAVA_HOME not found. Please install JDK or Android Studio.")
    if not android_home:
        sys.exit("[!] ERROR: ANDROID_HOME not found. Please install Android SDK.")

    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["ANDROID_HOME"] = android_home

    print("\n--> Starting Gradle clean assembleRelease...")
    if os.name == "nt":
        cmd = ["cmd.exe", "/c", "gradlew.bat", "clean", "assembleRelease", "--no-daemon"]
    else:
        cmd = ["./gradlew", "clean", "assembleRelease", "--no-daemon"]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT / "android", env=env)
    if result.returncode != 0:
        sys.exit(f"[!] ERROR: Gradle build failed with code {result.returncode}")

    if not RELEASE_APK_OUTPUT.is_file():
        sys.exit(f"[!] ERROR: Expected release APK not found at {RELEASE_APK_OUTPUT}")

    apk_size, apk_vname = inspect_apk(RELEASE_APK_OUTPUT)
    print(f"\n[+] Build Success! APK Size: {apk_size} bytes, VersionName in AXML: {apk_vname}")

    # Copy to local dist and static downloads
    LOCAL_DIST_APK.parent.mkdir(parents=True, exist_ok=True)
    STATIC_DOWNLOAD_APK.parent.mkdir(parents=True, exist_ok=True)

    LOCAL_DIST_APK.write_bytes(RELEASE_APK_OUTPUT.read_bytes())
    STATIC_DOWNLOAD_APK.write_bytes(RELEASE_APK_OUTPUT.read_bytes())
    print(f"[+] Updated local file: {LOCAL_DIST_APK}")
    print(f"[+] Updated local file: {STATIC_DOWNLOAD_APK}")

    if skip_deploy:
        print("\n[+] Done! (--no-deploy specified, skipped server upload)")
        return

    print(f"\n--> Deploying APK and main.py to server {REMOTE_HOST}...")
    temp_remote_apk = "/tmp/zhiday-resume-android-deploy.apk"

    # SCP APK to temp location
    scp_apk = subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", str(RELEASE_APK_OUTPUT), f"{REMOTE_USER}@{REMOTE_HOST}:{temp_remote_apk}"])
    if scp_apk.returncode != 0:
        sys.exit("[!] ERROR: Failed to SCP APK to remote server.")

    # SCP main.py, radar.py, and radar_sources.py
    for app_file in ["main.py", "radar.py", "radar_sources.py"]:
        local_f = REPO_ROOT / "app" / app_file
        remote_f = f"/opt/jd-resume-ai/app/{app_file}"
        if local_f.is_file():
            scp_res = subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", str(local_f), f"{REMOTE_USER}@{REMOTE_HOST}:{remote_f}"])
            if scp_res.returncode != 0:
                sys.exit(f"[!] ERROR: Failed to SCP {app_file} to remote server.")

    # Execute Remote Deploy & AAPT Verification
    remote_script = f"""
set -e
cp {temp_remote_apk} {REMOTE_WWW_APK}
cp {temp_remote_apk} {REMOTE_APP_APK}
chown jdresume:jdresume {REMOTE_APP_APK}
rm -f {temp_remote_apk}

echo "=== AAPT Verification on Server ==="
aapt dump badging {REMOTE_WWW_APK} | head -2

systemctl reload nginx
systemctl restart jd-resume-ai
echo "=== Remote Deployment & Service Reload Complete ==="
"""
    ssh_cmd = subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", f"{REMOTE_USER}@{REMOTE_HOST}", remote_script])
    if ssh_cmd.returncode != 0:
        sys.exit("[!] ERROR: Server deployment command failed.")

    print(f"\n[SUCCESS] App version {main_name} (code {main_code}) built and deployed successfully!")


if __name__ == "__main__":
    main()
