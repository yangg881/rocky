import argparse
import sys
import time
import uuid

import httpx


def check(response: httpx.Response, expected: int = 200):
    if response.status_code != expected:
        print(f"FAIL {response.request.method} {response.request.url}: {response.status_code} {response.text}")
        sys.exit(1)
    return response.json()


def wait_for_task(client: httpx.Client, url: str, headers: dict[str, str], timeout_seconds: int = 90) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        record = check(client.get(url, headers=headers))
        if record.get("status") == "completed":
            return record
        if record.get("status") == "failed":
            raise SystemExit(f"FAIL task failed: {record.get('error') or 'unknown error'}")
        time.sleep(1)
    raise SystemExit("FAIL task did not complete before smoke-test timeout")


def wait_for_generation(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    generation_id: str,
    timeout_seconds: int = 150,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        records = check(client.get(url, headers=headers))
        record = next((item for item in records if item.get("id") == generation_id), None)
        if record and record.get("status") == "completed":
            return record
        if record and record.get("status") == "failed":
            raise SystemExit(f"FAIL generation failed: {record.get('error') or 'unknown error'}")
        time.sleep(1)
    raise SystemExit("FAIL generation did not complete before smoke-test timeout")


def main() -> None:
    parser = argparse.ArgumentParser(description="Online smoke test for JD Resume AI")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--admin-username", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--phone", help="A disposable test phone number for the SMS-backed user flow")
    parser.add_argument("--sms-code", help="The verification code received by --phone")
    parser.add_argument("--live-ai", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/api"
    username = f"smoke-{uuid.uuid4().hex[:10]}"
    password = "Smoke-test-2026!"

    with httpx.Client(timeout=120, follow_redirects=False) as client:
        check(client.get(f"{base}/health"))
        if bool(args.phone) != bool(args.sms_code):
            raise SystemExit("--phone and --sms-code must be supplied together")

        if not args.phone:
            admin = check(
                client.post(
                    f"{base}/auth/login", json={"username": args.admin_username, "password": args.admin_password}
                )
            )
            stats = check(client.get(f"{base}/admin/stats", headers={"Authorization": f"Bearer {admin['token']}"}))
            assert "users" in stats
            if args.live_ai:
                raise SystemExit("--live-ai requires --phone and --sms-code so a smoke user can be created")
            print("PASS: health, security headers and admin access (SMS user flow skipped without --phone/--sms-code)")
            return

        registered = check(
            client.post(
                f"{base}/auth/register",
                json={
                    "username": username,
                    "phone": args.phone,
                    "code": args.sms_code,
                    "password": password,
                    "confirm_password": password,
                },
            ),
            201,
        )
        headers = {"Authorization": f"Bearer {registered['token']}"}
        resume = check(
            client.post(
                f"{base}/resumes",
                headers=headers,
                json={
                    "name": "线上验收简历",
                    "content": {
                        "name": "验收用户",
                        "title": "项目经理",
                        "summary": "负责软件项目计划、协作与交付",
                        "skills": ["项目管理", "需求沟通"],
                        "experience": [{"details": "在测试公司负责软件项目交付"}],
                    },
                },
            ),
            201,
        )
        resumes = check(client.get(f"{base}/resumes", headers=headers))
        assert any(item["id"] == resume["id"] for item in resumes)

        if args.live_ai:
            queued_jd = check(
                client.post(
                    f"{base}/jd/parse",
                    headers=headers,
                    json={
                        "source_type": "text",
                        "text": "招聘项目经理，负责软件项目计划、跨团队协作、风险管理与按期交付。",
                    },
                )
            )
            jd = wait_for_task(client, f"{base}/jd/tasks/{queued_jd['id']}", headers)
            generated = check(
                client.post(
                    f"{base}/generations",
                    headers=headers,
                    json={"resume_id": resume["id"], "jd": jd["result"]},
                ),
                202,
            )
            generated = wait_for_generation(client, f"{base}/generations", headers, generated["id"])
            for file_info in generated["files"].values():
                link = check(
                    client.get(
                        f"{base}/file-link",
                        headers=headers,
                        params={"bucket": "b", "key": file_info["key"]},
                    )
                )
                if not link["url"].startswith("http"):
                    raise SystemExit("FAIL file link is not a TOS HTTP URL")

        admin = check(
            client.post(
                f"{base}/auth/login", json={"username": args.admin_username, "password": args.admin_password}
            )
        )
        admin_headers = {"Authorization": f"Bearer {admin['token']}"}
        stats = check(client.get(f"{base}/admin/stats", headers=admin_headers))
        assert stats["users"] >= 1
        check(client.delete(f"{base}/admin/users/{registered['user']['id']}", headers=admin_headers))

    print("PASS: health, TOS data, registration, login, user isolation, resume CRUD and admin operations")
    if args.live_ai:
        print("PASS: SenseNova task flow, Word/PDF export and TOS direct links")


if __name__ == "__main__":
    main()
