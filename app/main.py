import asyncio
import hashlib
import logging
import mimetypes
import posixpath
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError

from app.ai import AIServiceError, SenseNovaClient
from app.config import get_settings
from app.metadata_store import MetadataStore
from app.models import (
    AdminCreditUpdateRequest,
    AdminOrderUpdateRequest,
    AdminUpdatePhoneRequest,
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    CareerFactBuildRequest,
    CareerFactDecisionRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    DeleteAccountRequest,
    GenerateRequest,
    JDRequest,
    LoginRequest,
    OrderCreateRequest,
    RadarCompanyPreferenceRequest,
    RadarFeedbackRequest,
    RadarImportRequest,
    RegenerateRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResumeCreateRequest,
    ResumeUpdateRequest,
    ReviewCreateRequest,
    ReviewDecisionRequest,
    SmsCodeRequest,
    SmsLoginRequest,
)
from app.observability import enforce_rate_limit, log_event, privacy_hash
from app.radar import JobRadarStore
from app.radar_sources import GxrcCollectionError, GxrcPublicCollector
from app.security import decode_file_token, decode_token, hash_password, issue_file_token, issue_token, verify_password
from app.services import (
    build_career_profile,
    build_jd_insight,
    apply_catalog_template,
    extract_document_text,
    extract_resume_avatar,
    fallback_resume_design,
    fetch_job_page,
    normalize_resume_content,
    prepare_avatar_image,
    resolve_resume_design,
    resume_to_docx,
    resume_to_lapiscv_pdf,
    resume_to_pdf,
    score_generated_resume,
    validate_jd_result,
)
from app.template_catalog import catalog_key, default_templates, public_template, sample_resume_for_template
from app.sms import AliyunSmsVerifier, SmsServiceError, mask_phone
from app.storage import ObjectStore
from app.task_queue import TaskQueue

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
file_store = ObjectStore(settings)
store = MetadataStore(file_store, settings.database_url) if settings.database_url else file_store
ai = SenseNovaClient(settings, store)
sms = AliyunSmsVerifier(settings, store)
task_queue = TaskQueue(settings)
STATIC_DIR = Path(__file__).parent / "static"
radar = JobRadarStore(Path(__file__).parent.parent / "data" / "job-radar.sqlite3")
radar_detail_collector = GxrcPublicCollector(timeout_seconds=20)
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_JD_IMAGE_COUNT = 10
MAX_JD_IMAGE_TOTAL_BYTES = 30 * 1024 * 1024
JD_IMAGE_EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def username_index_key(username: str) -> str:
    digest = hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()
    return f"indexes/usernames/{digest}.json"


def phone_index_key(phone: str) -> str:
    digest = hashlib.sha256(phone.encode("utf-8")).hexdigest()
    return f"indexes/phones/{digest}.json"


def public_user(user: dict) -> dict:
    public = {
        key: user.get(key)
        for key in ("id", "username", "role", "phone", "avatar_key", "created_at", "updated_at")
    }
    public["phone_masked"] = mask_phone(user["phone"]) if user.get("phone") else ""
    if user.get("avatar_key"):
        token = issue_file_token(
            "c",
            user["avatar_key"],
            settings,
            "account-avatar.jpg",
            minutes=60,
            owner_id=user["id"],
            purpose="avatar",
        )
        public["avatar_url"] = f"{settings.app_base_path}/api/file-preview/{token}"
    else:
        public["avatar_url"] = ""
    return public


def get_user_by_username(username: str) -> dict | None:
    index = store.get_json("a", username_index_key(username))
    if not index:
        return None
    return store.get_json("a", f"users/{index['user_id']}.json")


def get_user_by_phone(phone: str) -> dict | None:
    index = store.get_json("a", phone_index_key(phone))
    if not index:
        return None
    return store.get_json("a", f"users/{index['user_id']}.json")


def save_user(user: dict, previous_phone: str | None = None) -> None:
    user.setdefault("session_version", 1)
    store.put_json("a", f"users/{user['id']}.json", user)
    store.put_json("a", username_index_key(user["username"]), {"user_id": user["id"]})
    current_phone = user.get("phone")
    if current_phone:
        store.put_json("a", phone_index_key(current_phone), {"user_id": user["id"]})
    if previous_phone and previous_phone != current_phone:
        store.delete("a", phone_index_key(previous_phone))


def audit(action: str, actor_id: str, details: dict | None = None) -> None:
    event = {
        "id": str(uuid.uuid4()),
        "action": action,
        "actor_id": actor_id,
        "details": details or {},
        "created_at": now_iso(),
    }
    store.put_json("a", f"audit/{event['created_at'][:10]}/{event['id']}.json", event)


def save_task_log(task: dict) -> None:
    store.put_json("a", f"tasks/{task['id']}.json", task)


def update_task_log(task_id: str, **changes) -> None:
    task = store.get_json("a", f"tasks/{task_id}.json")
    if not task:
        return
    task.update(changes)
    task["updated_at"] = now_iso()
    save_task_log(task)


def dispatch_task(
    background_tasks: BackgroundTasks,
    queue_function: str,
    queue_job_id: str,
    local_function,
    **kwargs,
) -> None:
    """Use Redis in production; retain deterministic in-process execution for local tests."""
    if task_queue.enqueue(queue_function, job_id=queue_job_id, kwargs=kwargs):
        return
    background_tasks.add_task(local_function, **kwargs)


def delete_user_data(target: dict) -> None:
    user_id = target["id"]
    store.delete_prefix("a", f"resumes/{user_id}/")
    store.delete_prefix("a", f"generations/{user_id}/")
    store.delete_prefix("a", f"jd-tasks/{user_id}/")
    for task in store.list_json("a", "tasks/"):
        if task.get("user_id") == user_id:
            store.delete("a", f"tasks/{task['id']}.json")
    store.delete_prefix("b", f"users/{user_id}/")
    store.delete_prefix("c", f"users/{user_id}/")
    store.delete("a", username_index_key(target["username"]))
    if target.get("phone"):
        store.delete("a", phone_index_key(target["phone"]))
    store.delete("a", f"users/{user_id}.json")
    radar.delete_user_data(user_id)


def ensure_admin() -> None:
    existing = get_user_by_username(settings.admin_username)
    if existing:
        if existing.get("role") != "admin":
            raise RuntimeError("ADMIN_USERNAME conflicts with an existing normal user")
        return
    admin = {
        "id": str(uuid.uuid4()),
        "username": settings.admin_username,
        "password_hash": hash_password(settings.admin_password),
        "role": "admin",
        "session_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    save_user(admin)


def ensure_system_templates() -> None:
    """Replace the old 40 licensed-docx catalog with 8 real layout templates."""
    existing = store.list_json("a", "resume-templates/")
    for item in existing:
        template_id = str(item.get("id") or "")
        # Drop legacy licensed originals that only changed colour swatches.
        if template_id.startswith("licensed-") or not item.get("builtin"):
            store.delete("a", catalog_key(template_id))
    for template in default_templates():
        template = dict(template)
        template["updated_at"] = now_iso()
        store.put_json("a", catalog_key(template["id"]), template)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if isinstance(store, MetadataStore):
        store.initialize()
    ensure_admin()
    ensure_system_templates()
    radar.initialize()
    # Self-check APK installer presence and version match on startup
    try:
        apk_file = STATIC_DIR / "downloads" / "zhiday-resume-android.apk"
        if not apk_file.is_file():
            logging.warning("[APK CHECK] ⚠️ Android installer APK file not found at %s", apk_file)
        else:
            cleaned = apk_file.read_bytes()[:64000].replace(b"\x00", b"")
            versions = re.findall(b"1\\.\\d+\\.\\d+", cleaned)
            apk_version = versions[0].decode("utf-8") if versions else "unknown"
            logging.info("[APK CHECK] ✅ Live Android installer found (%d bytes, version: %s)", apk_file.stat().st_size, apk_version)
    except Exception as exc:
        logging.warning("[APK CHECK] Failed to inspect APK version: %s", exc)
    yield


app = FastAPI(title=settings.app_name, docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    )
api = APIRouter(prefix=f"{settings.app_base_path}/api")


def error_payload(code: str, message: str, request: Request, details=None) -> dict:
    """Keep ``detail`` during the transition so existing Web/App clients do not break."""
    payload = {
        "code": code,
        "message": message,
        "detail": message,
        "request_id": getattr(request.state, "request_id", ""),
    }
    if details is not None:
        payload["details"] = details
    return payload


@app.middleware("http")
async def request_context_and_security_headers(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")[:80]
    request.state.request_id = supplied if re.fullmatch(r"[A-Za-z0-9._-]{8,80}", supplied) else uuid.uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log_event(
            "request.unhandled_error",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
        )
        raise
    elapsed_ms = round((perf_counter() - started) * 1000, 1)
    response.headers["X-Request-ID"] = request.state.request_id
    if settings.security_headers_enabled:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        # The legacy standalone document preview contains a small inline loader.
        # Main user/admin pages only load same-origin scripts and assets.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; "
            "object-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:;",
        )
    log_event(
        "request.completed",
        request_id=request.state.request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=elapsed_ms,
    )
    return response


@app.exception_handler(AIServiceError)
async def handle_ai_service_error(request: Request, exc: AIServiceError) -> JSONResponse:
    return JSONResponse(status_code=502, content=error_payload(exc.category, str(exc), request))


@app.exception_handler(SmsServiceError)
async def handle_sms_service_error(request: Request, exc: SmsServiceError) -> JSONResponse:
    return JSONResponse(status_code=400, content=error_payload("sms_verification_failed", str(exc), request))


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "请求未能完成"
    details = None if isinstance(exc.detail, str) else exc.detail
    code = {
        400: "invalid_request",
        401: "authentication_required",
        403: "permission_denied",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_failed",
        429: "rate_limited",
    }.get(exc.status_code, "request_failed")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message, request, details),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = jsonable_encoder(exc.errors())
    log_event(
        "request.validation_failed",
        request_id=getattr(request.state, "request_id", ""),
        path=request.url.path,
        errors=details,
    )
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "validation_failed",
            "提交信息不完整或格式不正确",
            request,
            details,
        ),
    )


def access_token_from_request(request: Request, authorization: str | None) -> str | None:
    """Prefer explicit Bearer credentials for Android, otherwise use the Web HttpOnly cookie."""
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return request.cookies.get(settings.auth_cookie_name)


def current_user(request: Request, authorization: Annotated[str | None, Header()] = None) -> dict:
    token = access_token_from_request(request, authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    try:
        payload = decode_token(token, settings)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录") from exc
    user = store.get_json("a", f"users/{payload['sub']}.json")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在")
    if int(payload.get("sv", 1)) != int(user.get("session_version", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    return user


def _resolve_cookie_secure(request):
    """Decide whether the session cookie should carry the Secure flag.

    The flag follows the actual transport of the incoming request so the
    same build works on HTTPS (Secure) and HTTP IP access (non-Secure)
    without an operator toggle. ``settings.auth_cookie_secure`` is used
    as a fallback when no request context is available.
    """
    if request is not None:
        return request.url.scheme == "https"
    return settings.auth_cookie_secure


def issue_auth_response(user: dict, *, status_code: int = 200, request=None) -> JSONResponse:
    """Return Android-compatible JSON while moving Web browsers to an HttpOnly session cookie."""
    token = issue_token(user["id"], user["role"], settings, int(user.get("session_version", 1)))
    response = JSONResponse(status_code=status_code, content={"token": token, "user": public_user(user)})
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        secure=_resolve_cookie_secure(request),
        samesite=settings.auth_cookie_same_site,
        path=settings.app_base_path or "/",
    )
    return response


def revoke_all_sessions(user: dict) -> None:
    user["session_version"] = int(user.get("session_version", 1)) + 1
    user["updated_at"] = now_iso()
    save_user(user)


def admin_user(user: Annotated[dict, Depends(current_user)]) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def require_owner(resource: dict | None, user: dict) -> dict:
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    if resource.get("user_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权访问该资源")
    return resource


def get_catalog_template(template_id: str | None, *, active_only: bool = True) -> dict | None:
    if not template_id:
        return None
    template = store.get_json("a", catalog_key(template_id))
    if not isinstance(template, dict) or (active_only and not template.get("active", False)):
        return None
    return template


async def read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="单个文件不能超过 15MB")
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")
    return data


def jd_image_magic_matches(content_type: str, data: bytes) -> bool:
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


@api.get("/health")
def health() -> dict:
    https_ready = settings.public_origin.startswith("https://")
    return {
        "ok": True,
        "service": settings.app_name,
        "storage": settings.storage_backend,
        "time": now_iso(),
        "readiness": {
            "https_configured": https_ready,
            "public_origin": settings.public_origin or None,
            "rate_limit": settings.rate_limit_enabled,
        },
    }


@api.get("/career/dashboard")
def career_dashboard(user: Annotated[dict, Depends(current_user)]) -> dict:
    resumes = store.list_json("a", f"resumes/{user['id']}/")
    generations = sorted(
        store.list_json("a", f"generations/{user['id']}/"),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    jd_tasks = sorted(
        store.list_json("a", f"jd-tasks/{user['id']}/"),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    profile = build_career_profile(resumes, generations)
    latest_completed = next((item for item in generations if item.get("status") == "completed"), None)
    latest_jd = next((item for item in jd_tasks if item.get("status") == "completed" and item.get("result")), None)
    return {
        "profile": profile,
        "latest_generation": latest_completed,
        "latest_jd": latest_jd,
        "counts": {
            "resumes": len(resumes),
            "jd_tasks": len(jd_tasks),
            "generations": len(generations),
            "completed_generations": len([item for item in generations if item.get("status") == "completed"]),
        },
        "updated_at": now_iso(),
    }


PLAN_CATALOG = {
    "starter": {"name": "入门包", "credits": 10, "price_cents": 1990},
    "pro": {"name": "进阶包", "credits": 40, "price_cents": 6990},
    "career_plus": {"name": "职业加速包", "credits": 100, "price_cents": 14900},
}

# 一次“生成/换模板重排”消耗 1 次额度；岗位解析免费，避免用户还没产出就扣光试用。
CREDIT_COSTS = {
    "resume_generation": 1,
    "resume_regenerate": 1,
    "jd_parse": 0,
}


def account_key(user_id: str) -> str:
    return f"billing/accounts/{user_id}.json"


def billing_account(user_id: str) -> dict:
    account = store.get_json("a", account_key(user_id))
    if account:
        account.setdefault("reserved", 0)
        account.setdefault("suspended", False)
        return account
    account = {
        "user_id": user_id,
        "plan": "free_trial",
        "credits": 3,
        "reserved": 0,
        "suspended": False,
        "updated_at": now_iso(),
    }
    store.put_json("a", account_key(user_id), account)
    return account


def available_credits(account: dict) -> int:
    if account.get("suspended"):
        return 0
    return max(0, int(account.get("credits", 0)) - int(account.get("reserved", 0)))


def record_ledger(user_id: str, kind: str, credits: int, detail: str, reference_id: str = "") -> dict:
    entry = {
        "id": str(uuid.uuid4()), "user_id": user_id, "kind": kind, "credits": credits,
        "detail": detail, "reference_id": reference_id, "created_at": now_iso(),
    }
    store.put_json("a", f"billing/ledger/{user_id}/{entry['id']}.json", entry)
    return entry


def _default_account(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "plan": "free_trial",
        "credits": 3,
        "reserved": 0,
        "suspended": False,
        "updated_at": now_iso(),
    }


def reserve_credits(user_id: str, amount: int, *, kind: str, reference_id: str, detail: str) -> dict:
    """Freeze credits before an async job starts. amount=0 is a no-op.

    The balance check and the ``reserved`` increment happen inside a single
    ``store.atomic_update_json`` (SELECT ... FOR UPDATE on PostgreSQL), so two
    concurrent reservations can no longer both pass the check and double-spend
    the same credit (P0-1).
    """
    if amount <= 0:
        return billing_account(user_id)

    def _apply(account):
        account = dict(account) if account else _default_account(user_id)
        account.setdefault("reserved", 0)
        account.setdefault("suspended", False)
        if account.get("suspended"):
            raise HTTPException(status_code=403, detail="该账号额度已被管理员暂停，请联系管理员后再试。")
        free = available_credits(account)
        if free < amount:
            raise HTTPException(
                status_code=402,
                detail=f"可用额度不足（剩余 {free} 次，需要 {amount} 次）。请到「我的额度」创建次数包订单，或联系管理员调整额度。",
            )
        account["reserved"] = int(account.get("reserved", 0)) + amount
        account["updated_at"] = now_iso()
        return account

    account = store.atomic_update_json("a", account_key(user_id), _apply, default=_default_account(user_id))
    record_ledger(user_id, "reserve", amount, detail, reference_id)
    audit("billing.reserve", user_id, {"amount": amount, "kind": kind, "reference_id": reference_id})
    return account


def commit_credits(user_id: str, amount: int, *, reference_id: str, detail: str) -> dict:
    """Convert reserved credits into consumed credits after success (atomic, P0-1)."""
    if amount <= 0:
        return billing_account(user_id)
    box: dict = {}

    def _apply(account):
        account = dict(account) if account else _default_account(user_id)
        reserved = int(account.get("reserved", 0))
        credits = int(account.get("credits", 0))
        use = min(amount, reserved, credits)
        account["reserved"] = max(0, reserved - amount)
        account["credits"] = max(0, credits - use)
        account["updated_at"] = now_iso()
        box["use"] = use
        return account

    account = store.atomic_update_json("a", account_key(user_id), _apply, default=_default_account(user_id))
    use = int(box.get("use", 0))
    record_ledger(user_id, "consume", -use, detail, reference_id)
    audit("billing.consume", user_id, {"amount": use, "reference_id": reference_id})
    return account


def release_credits(user_id: str, amount: int, *, reference_id: str, detail: str) -> dict:
    """Unfreeze reserved credits after failure/cancel (atomic, P0-1)."""
    if amount <= 0:
        return billing_account(user_id)
    box: dict = {}

    def _apply(account):
        account = dict(account) if account else _default_account(user_id)
        reserved = int(account.get("reserved", 0))
        release = min(amount, reserved)
        account["reserved"] = max(0, reserved - release)
        account["updated_at"] = now_iso()
        box["release"] = release
        return account

    account = store.atomic_update_json("a", account_key(user_id), _apply, default=_default_account(user_id))
    release = int(box.get("release", 0))
    record_ledger(user_id, "release", release, detail, reference_id)
    audit("billing.release", user_id, {"amount": release, "reference_id": reference_id})
    return account


def settle_generation_credits(record: dict, *, success: bool) -> None:
    amount = int(record.get("credit_cost") or 0)
    if amount <= 0 or record.get("credit_settled"):
        return
    user_id = str(record.get("user_id") or "")
    job_id = str(record.get("id") or "")
    if success:
        commit_credits(user_id, amount, reference_id=job_id, detail=f"简历生成扣减：{record.get('jd', {}).get('title') or job_id}")
    else:
        release_credits(user_id, amount, reference_id=job_id, detail=f"简历生成失败退回：{record.get('jd', {}).get('title') or job_id}")
    record["credit_settled"] = True
    record["credit_status"] = "consumed" if success else "released"


def fact_text(item: dict) -> str:
    return " · ".join(str(value).strip() for value in item.values() if value not in (None, ""))


@api.get("/career/facts")
def list_career_facts(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    records = store.list_json("a", f"career-facts/{user['id']}/")
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


@api.post("/career/facts/rebuild")
def rebuild_career_facts(payload: CareerFactBuildRequest, user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    resume = require_owner(store.get_json("a", f"resumes/{user['id']}/{payload.resume_id}.json"), user)
    store.delete_prefix("a", f"career-facts/{user['id']}/")
    content = resume.get("content") or {}
    collected: list[tuple[str, str, int]] = []
    for section in ("experience", "projects", "education"):
        for row in content.get(section) or []:
            if isinstance(row, dict) and fact_text(row):
                collected.append((section, fact_text(row), 2 if section == "experience" else 1))
    for skill in content.get("skills") or []:
        if str(skill).strip():
            collected.append(("skill", str(skill).strip(), 1))
    facts: list[dict] = []
    for category, text, risk_level in collected:
        fact = {
            "id": str(uuid.uuid4()), "user_id": user["id"], "resume_id": resume["id"], "category": category,
            "raw_text": text, "display_text": text, "status": "confirmed", "risk_level": risk_level,
            "source": {"type": "resume", "resume_id": resume["id"]}, "created_at": now_iso(), "updated_at": now_iso(),
        }
        store.put_json("a", f"career-facts/{user['id']}/{fact['id']}.json", fact)
        facts.append(fact)
    audit("career.facts_rebuilt", user["id"], {"resume_id": resume["id"], "count": len(facts)})
    return facts


@api.post("/career/facts/{fact_id}/decision")
def decide_career_fact(
    fact_id: str, payload: CareerFactDecisionRequest, user: Annotated[dict, Depends(current_user)]
) -> dict:
    key = f"career-facts/{user['id']}/{fact_id}.json"
    fact = require_owner(store.get_json("a", key), user)
    fact["status"] = payload.status
    if payload.edited_text is not None:
        fact["display_text"] = payload.edited_text.strip()
    fact["updated_at"] = now_iso()
    store.put_json("a", key, fact)
    audit("career.fact_decision", user["id"], {"fact_id": fact_id, "status": payload.status})
    return fact


@api.get("/reviews")
def list_reviews(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    records = store.list_json("a", f"reviews/{user['id']}/")
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


@api.post("/reviews", status_code=201)
def create_review(payload: ReviewCreateRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    resume = require_owner(store.get_json("a", f"resumes/{user['id']}/{payload.resume_id}.json"), user)
    jd = validate_jd_result(dict(payload.jd or {}))
    facts = [item for item in store.list_json("a", f"career-facts/{user['id']}/") if item.get("status") == "confirmed"]
    if not facts:
        facts = rebuild_career_facts(CareerFactBuildRequest(resume_id=resume["id"]), user)
    keywords = [str(item).strip() for item in jd.get("keywords") or [] if str(item).strip()][:12]
    evidence = " ".join(item.get("display_text", "") for item in facts).lower()
    proposals = [
        {
            "id": str(uuid.uuid4()), "before": fact.get("display_text", ""),
            "after": fact.get("display_text", ""), "reason": "保留已确认的原始经历，仅按岗位关键词组织表达。",
            "source_fact_ids": [fact["id"]], "risk": "low", "decision": "pending",
        }
        for fact in facts[:20]
    ]
    coverage = {word: (word.lower() in evidence) for word in keywords}
    review = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "resume_id": resume["id"], "jd": jd,
        "status": "review_required", "proposals": proposals, "keyword_coverage": coverage,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    store.put_json("a", f"reviews/{user['id']}/{review['id']}.json", review)
    audit("review.created", user["id"], {"review_id": review["id"], "facts": len(facts)})
    return review


@api.post("/reviews/{review_id}/proposals/{proposal_id}")
def decide_review_proposal(
    review_id: str,
    proposal_id: str,
    payload: ReviewDecisionRequest,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    key = f"reviews/{user['id']}/{review_id}.json"
    review = require_owner(store.get_json("a", key), user)
    proposal = next((item for item in review.get("proposals", []) if item.get("id") == proposal_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail="审阅项不存在")
    proposal["decision"] = payload.decision
    proposal["note"] = payload.note
    pending = any(item.get("decision") == "pending" for item in review.get("proposals", []))
    review["status"] = "review_required" if pending else "confirmed"
    review["updated_at"] = now_iso()
    store.put_json("a", key, review)
    return review


@api.get("/billing/summary")
def billing_summary(user: Annotated[dict, Depends(current_user)]) -> dict:
    account = billing_account(user["id"])
    account = {
        **account,
        "available": available_credits(account),
        "reserved": int(account.get("reserved", 0)),
        "suspended": bool(account.get("suspended")),
    }
    ledger = sorted(
        store.list_json("a", f"billing/ledger/{user['id']}/"),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    orders = sorted(
        store.list_json("a", f"orders/{user['id']}/"),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    return {
        "account": account,
        "plans": PLAN_CATALOG,
        "costs": CREDIT_COSTS,
        "ledger": ledger[:30],
        "orders": orders[:30],
        "payment_provider": "manual_admin",
        "payment_note": "支付通道尚未直连：请创建待支付订单后联系管理员确认到账；到账后额度立即生效。",
    }


@api.post("/billing/orders", status_code=201)
def create_order(payload: OrderCreateRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    product = PLAN_CATALOG[payload.product_code]
    order = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "product_code": payload.product_code,
        "product_name": product["name"], "credits": product["credits"], "amount_cents": product["price_cents"],
        "status": "pending", "payment_url": "", "created_at": now_iso(), "updated_at": now_iso(),
    }
    store.put_json("a", f"orders/{user['id']}/{order['id']}.json", order)
    audit("billing.order_created", user["id"], {"order_id": order["id"], "product": payload.product_code})
    return order


@api.get("/applications")
def list_applications(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    records = store.list_json("a", f"applications/{user['id']}/")
    return sorted(records, key=lambda item: item.get("updated_at", ""), reverse=True)


@api.post("/applications", status_code=201)
def create_application(payload: ApplicationCreateRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    if payload.generation_id:
        require_owner(store.get_json("a", f"generations/{user['id']}/{payload.generation_id}.json"), user)
    item = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        **payload.model_dump(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.put_json("a", f"applications/{user['id']}/{item['id']}.json", item)
    audit("application.created", user["id"], {"application_id": item["id"], "status": item["status"]})
    return item


@api.patch("/applications/{application_id}")
def update_application(
    application_id: str, payload: ApplicationUpdateRequest, user: Annotated[dict, Depends(current_user)]
) -> dict:
    key = f"applications/{user['id']}/{application_id}.json"
    item = require_owner(store.get_json("a", key), user)
    item.update({name: value for name, value in payload.model_dump().items() if value is not None})
    item["updated_at"] = now_iso()
    store.put_json("a", key, item)
    audit("application.updated", user["id"], {"application_id": application_id, "status": item.get("status")})
    return item


@api.delete("/applications/{application_id}")
def delete_application(application_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    key = f"applications/{user['id']}/{application_id}.json"
    require_owner(store.get_json("a", key), user)
    store.delete("a", key)
    audit("application.deleted", user["id"], {"application_id": application_id})
    return {"ok": True}


def radar_profile_text(user: dict, resume_ids: list[str] | None = None) -> str:
    """Build recommendation input from user's resume(s).
    
    When resume_ids is None, uses the default resume (original behaviour).
    When resume_ids is provided, merges key info from those resumes into a combined profile.
    """
    resumes = store.list_json("a", f"resumes/{user['id']}/")
    generations = store.list_json("a", f"generations/{user['id']}/")
    profile = build_career_profile(resumes, generations)
    
    if not resume_ids:
        # Original behaviour: use default resume
        resume = next((item for item in resumes if item.get("is_default")), resumes[0] if resumes else {})
        content = resume.get("content") if isinstance(resume, dict) else {}
        if not isinstance(content, dict):
            content = {}
        experience = content.get("experience") if isinstance(content.get("experience"), list) else []
        experience_text = " ".join(
            " ".join(str(part or "") for part in item.values()) for item in experience if isinstance(item, dict)
        )
        return " ".join(
            [
                str(profile.get("direction") or ""),
                str(profile.get("title") or ""),
                " ".join(str(item) for item in profile.get("recommended_roles") or []),
                str(content.get("title") or ""),
                str(content.get("summary") or ""),
                " ".join(str(item) for item in content.get("skills") or []),
                experience_text,
            ]
        )
    
    # Merge multiple resumes
    selected = [r for r in resumes if r.get("id") in resume_ids]
    if not selected:
        # Fallback to default resume if none of the specified IDs found
        resume = next((item for item in resumes if item.get("is_default")), resumes[0] if resumes else {})
        content = resume.get("content") if isinstance(resume, dict) else {}
        if not isinstance(content, dict):
            content = {}
        experience = content.get("experience") if isinstance(content.get("experience"), list) else []
        experience_text = " ".join(
            " ".join(str(part or "") for part in item.values()) for item in experience if isinstance(item, dict)
        )
        return " ".join(
            [
                str(profile.get("direction") or ""),
                str(profile.get("title") or ""),
                " ".join(str(item) for item in profile.get("recommended_roles") or []),
                str(content.get("title") or ""),
                str(content.get("summary") or ""),
                " ".join(str(item) for item in content.get("skills") or []),
                experience_text,
            ]
        )
    
    # Selected resumes must also determine the profile direction. Otherwise a
    # resume the user did not choose can still influence the recommendation.
    profile = build_career_profile(selected, [])

    # Collect merged fields from all selected resumes
    merged_titles = []
    merged_summaries = []
    merged_skills = []
    merged_experiences = []
    
    for resume in selected:
        content = resume.get("content") if isinstance(resume, dict) else {}
        if not isinstance(content, dict):
            continue
        if content.get("title"):
            merged_titles.append(str(content["title"]))
        if content.get("summary"):
            merged_summaries.append(str(content["summary"]))
        skills = content.get("skills") if isinstance(content.get("skills"), list) else []
        merged_skills.extend(str(s) for s in skills)
        experience = content.get("experience") if isinstance(content.get("experience"), list) else []
        merged_experiences.extend(experience)
    
    # Deduplicate skills while preserving order
    seen_skills = set()
    unique_skills = []
    for s in merged_skills:
        if s not in seen_skills:
            seen_skills.add(s)
            unique_skills.append(s)
    
    # Deduplicate experiences by key fields (company + title)
    seen_exp_keys = set()
    unique_experiences = []
    for exp in merged_experiences:
        if not isinstance(exp, dict):
            continue
        key = (str(exp.get("company", "")).strip().lower(), str(exp.get("title", "")).strip().lower())
        if key not in seen_exp_keys:
            seen_exp_keys.add(key)
            unique_experiences.append(exp)
    
    experience_text = " ".join(
        " ".join(str(part or "") for part in item.values()) for item in unique_experiences
    )
    
    return " ".join(
        [
            str(profile.get("direction") or ""),
            str(profile.get("title") or ""),
            " ".join(str(item) for item in profile.get("recommended_roles") or []),
            " | ".join(merged_titles),
            " ".join(merged_summaries),
            " ".join(unique_skills),
            experience_text,
        ]
    )


def radar_job_as_jd(job: dict) -> dict:
    """Translate a neutral catalog record into the existing JD optimizer input."""
    return {
        "title": job.get("title") or "目标岗位",
        "company": job.get("company") or "",
        "responsibilities": job.get("responsibilities") or job.get("description") or [],
        "requirements": job.get("requirements") or [],
        "preferred": [],
        "keywords": job.get("tags") or [],
        "source_url": job.get("source_url") or "",
    }


@api.get("/radar/summary")
def radar_summary(user: Annotated[dict, Depends(current_user)]) -> dict:
    return radar.summary(user["id"])


@api.get("/radar/recommendations")
async def radar_recommendations(
    user: Annotated[dict, Depends(current_user)],
    query: str = "",
    city: str = "",
    published_within: str = "30d",
    page: int = 1,
    page_size: int = 20,
    limit: int = 10000,
    saved_only: bool = False,
    experience: str = "",
    education: str = "",
    salary_min: int = 0,
    sort_by: str = "match",
    min_score: int = 0,
    topic: str = "",
    source: str = "",
    only_new: bool = False,
    resume_ids: str = "",
) -> dict:
    # Parse and validate up to three user-owned resumes for merged recommendations.
    _resume_id_list = list(dict.fromkeys(rid.strip() for rid in resume_ids.split(",") if rid.strip())) if resume_ids else []
    if len(_resume_id_list) > 3:
        raise HTTPException(status_code=422, detail="最多可选择 3 份简历进行合并推荐")
    if _resume_id_list:
        owned_resume_ids = {str(item.get("id")) for item in store.list_json("a", f"resumes/{user['id']}/")}
        if any(resume_id not in owned_resume_ids for resume_id in _resume_id_list):
            raise HTTPException(status_code=422, detail="所选简历不存在或不属于当前账号")

    # Reconcile adaptation markers only on first page to avoid O(n) work each flip.
    if page <= 1 and not query and not saved_only:
        radar.sync_completed_adaptations(user["id"], store.list_json("a", f"generations/{user['id']}/"))
    limit = max(1, min(limit, 10000))
    page = max(1, page)
    page_size = max(1, min(page_size, 20))
    recommendation = await radar.recommend(
        user["id"],
        radar_profile_text(user, _resume_id_list or None),
        max_results=limit,
        query=query,
        city=city,
        published_within=published_within,
        saved_only=saved_only,
        experience=experience,
        education=education,
        salary_min=salary_min,
        sort_by=sort_by,
        topic=topic,
        source=source,
        only_new=only_new,
    )
    # `recommend` already calculates deterministic per-profile scores. Running an
    # additional AI call for every result made ordinary keyword searches wait for
    # minutes and allowed old responses to overwrite newer searches on the app.
    jobs = recommendation.jobs
    if min_score:
        jobs = [job for job in jobs if job.get("match_score", 0) >= min_score]
    total = len(jobs)
    start = (page - 1) * page_size
    cities = radar.available_cities() if page <= 1 else []
    facets = radar.facets() if page <= 1 else {}
    return {
        "jobs": jobs[start : start + page_size],
        "summary": radar.summary(user["id"]),
        "cities": cities,
        "facets": facets,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "max_results": limit,
            "matched_total": recommendation.matched_total,
            "is_limited": recommendation.is_limited,
        },
        "generated_at": now_iso(),
    }


@api.get("/radar/facets")
def radar_facets(user: Annotated[dict, Depends(current_user)]) -> dict:
    """Expose data-driven filter dimensions (experience / education / salary / topics)."""
    return radar.facets()


@api.post("/radar/filter-usage")
def radar_filter_usage(payload: dict, user: Annotated[dict, Depends(current_user)]) -> dict:
    """Record which filter dimensions a user actually applied, for later iteration."""
    radar.log_filter_usage(
        user["id"],
        str(payload.get("dimension") or ""),
        str(payload.get("value") or ""),
        int(payload.get("result_count") or 0),
    )
    return {"ok": True}


@api.get("/radar/filter-usage")
def radar_filter_usage_summary(user: Annotated[dict, Depends(current_user)]) -> dict:
    return {"usage": radar.filter_usage_summary(user["id"])}


@api.get("/radar/filter-presets")
def radar_list_presets(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    return radar.list_filter_presets(user["id"])


@api.post("/radar/filter-presets")
def radar_save_preset(payload: dict, user: Annotated[dict, Depends(current_user)]) -> dict:
    name = str(payload.get("name") or "")
    filters = payload.get("filters") or {}
    return radar.save_filter_preset(user["id"], name, filters)


@api.delete("/radar/filter-presets/{name}")
def radar_delete_preset(name: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    radar.delete_filter_preset(user["id"], name)
    return {"ok": True}


@api.get("/radar/jobs/{job_id}")
def radar_job_detail(job_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    """Return a cached publisher-page detail, enriching a catalogue row on demand."""
    job = radar.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在或已失效")
    status_value = str(job.get("source_detail_status") or "")
    updated_value = str(job.get("source_detail_updated_at") or "")
    is_fresh = False
    if updated_value:
        try:
            updated_at = datetime.fromisoformat(updated_value.replace("Z", "+00:00"))
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            # Completed public content remains stable enough for seven days;
            # temporary unavailable responses get a shorter backoff.
            max_age = 7 * 24 * 3600 if status_value == "complete" else 6 * 3600
            is_fresh = (datetime.now(timezone.utc) - updated_at.astimezone(timezone.utc)).total_seconds() < max_age
        except ValueError:
            is_fresh = False
    if not is_fresh:
        try:
            details = radar_detail_collector.enrich_job_detail(job)
            updated = radar.update_job_details(job_id, details)
            if updated:
                job = updated
        except GxrcCollectionError:
            updated = radar.update_job_details(
                job_id,
                {"source_detail_status": "unavailable", "source_detail_updated_at": now_iso()},
            )
            if updated:
                job = updated
    try:
        radar.set_feedback(user["id"], job_id, "viewed")
    except LookupError:
        # A source detail page may be temporarily unavailable. The detail we
        # already loaded is still valid enough to return; viewing it must not 500.
        pass
    audit("radar.detail_opened", user["id"], {"job_id": job_id, "detail_status": job.get("source_detail_status")})
    return job


@api.post("/radar/jobs/{job_id}/feedback")
def radar_feedback(
    job_id: str,
    payload: RadarFeedbackRequest,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    try:
        result = radar.set_feedback(user["id"], job_id, payload.action, payload.remind_until)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit("radar.feedback", user["id"], {"job_id": job_id, "action": payload.action})
    return {"ok": True, "feedback": result}


@api.post("/radar/jobs/{job_id}/company-preference")
def radar_company_preference(
    job_id: str,
    payload: RadarCompanyPreferenceRequest,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    job = radar.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在或已失效")
    try:
        radar.set_company_preference(user["id"], job.get("company") or "", payload.blocked)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    audit("radar.company_preference", user["id"], {"job_id": job_id, "blocked": payload.blocked})
    return {"ok": True, "company": job.get("company") or "", "blocked": payload.blocked}


@api.post("/radar/jobs/{job_id}/prepare-optimization")
def radar_prepare_optimization(job_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    job = radar.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在或已失效")
    radar.set_feedback(user["id"], job_id, "viewed")
    audit("radar.optimize_intent", user["id"], {"job_id": job_id})
    return {"job": job, "jd": radar_job_as_jd(job)}


@api.post("/admin/radar/jobs/import")
def admin_import_radar_jobs(
    payload: RadarImportRequest, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    result = radar.import_jobs(payload.jobs, payload.replace)
    audit("radar.jobs_import", admin["id"], {**result, "replace": payload.replace})
    return {"ok": True, **result, "active_jobs": radar.job_count()}


@api.post("/admin/radar/jobs/clean")
def admin_clean_radar_jobs(
    admin: Annotated[dict, Depends(admin_user)],
    days: int = 30,
    stale_days: int = 30,
    dry_run: bool = False,
) -> dict:
    result = radar.cleanup_inactive_jobs(max_published_days=days, max_stale_days=stale_days, dry_run=dry_run)
    audit("radar.jobs_clean", admin["id"], result)
    return {"ok": True, "active_jobs": radar.job_count(), "cleanup": result}


@api.get("/app/version")
def app_version(
    request: Request, platform: str = "android", version_code: int = 0
) -> dict:
    if platform != "android":
        raise HTTPException(status_code=400, detail="暂时只支持 Android 版本检测")
    apk_path = STATIC_DIR / "downloads" / "zhiday-resume-android.apk"
    # Bump together with a newly published APK under static/downloads.
    # Keep this value in lockstep with android/app/build.gradle.kts and the APK below.
    latest_code = 36
    minimum_code = 5
    latest_name = "1.8.21"
    # CRITICAL: many mobile carriers RST HTTPS to zhidajob.top, while HTTP to
    # the server IP works. Always advertise the HTTP/IP download first so old
    # and new clients can actually fetch the installer.
    ip_download_url = f"http://115.120.206.64/download/app-update?v={latest_code}"
    https_download_url = f"https://zhidajob.top/download/app-update?v={latest_code}"
    download_url = ip_download_url
    installer_url = f"http://115.120.206.64/download/zhiday-resume-android.apk?v={latest_code}"
    alt_urls = [
        ip_download_url,
        f"http://115.120.206.64/download/zhiday-resume-android.apk?v={latest_code}",
        https_download_url,
        f"https://zhidajob.top/download/zhiday-resume-android.apk?v={latest_code}",
    ]
    return {
        "platform": "android",
        "current_version_code": version_code,
        "latest_version_code": latest_code,
        "latest_version_name": latest_name,
        "minimum_version_code": minimum_code,
        "force_update": version_code > 0 and version_code < minimum_code,
        "update_available": version_code > 0 and version_code < latest_code,
        "download_url": download_url,
        "installer_url": installer_url,
        "download_urls": alt_urls,
        "filename": f"zhiday-resume-android-full-{latest_name}.apk",
        "package_type": "full_installer",
        "size": apk_path.stat().st_size if apk_path.is_file() else None,
        "release_notes": [
            "修复原文件预览、简历读取重复、岗位详情匹配归零与岗位关键词搜索失败",
            "【安全升级】改用正式发布证书签名，修复旧版调试证书带来的升级劫持风险；若安装提示“应用未安装/签名冲突”，请先卸载旧版再安装本版",
            "应用内更新增加安装包签名指纹校验，杜绝被下发伪造安装包",
            "修复岗位来源筛选：Android 应用与网页端现在都会正确按来源刷新岗位列表",
            "修复 1.8.13 业务接口“像断网”：API 主入口改回手机可达的 IP 路径",
            "接口失败自动切换备用地址（IP / 域名）",
            "修复应用内更新 Connection reset：下载与 API 同入口",
            "安装包 Nginx 直出 + 中性路径 /download/pkg，降低运营商拦截",
            "生成额度预扣与失败退回：每次生成/换模板消耗 1 次",
            "失败任务支持一键重试，错误原因更清晰",
            "模板预期说明：原件预览仅供风格参考，最终以生成文件为准",
            "岗位雷达筛选加速，列表翻页更轻量",
            "套餐订单可创建，管理员确认到账后额度生效",
            "账号页展示可用额度与预扣中额度",
            "作品中心预览即真实下载文件",
            "主路径引导：准备简历 → 选岗 → 生成下载",
            "管理员可后台增减/暂停/清零用户额度",
            "修复网页登录页脚本异常导致无法切换登录方式",
            "删除 40 套伪模板，改为 8 套真实不同版式",
            "模板预览改为同源 PDF 引擎，结构与生成一致",
            "长 Word 简历上传结构化更稳健，失败可降级草稿",
            "已适配岗位按钮改为「换模板重新生成」",
            "Web 与 Android 统一为岗位雷达、简历优化、求职记录、我的四个主入口",
        ],
        "checked_at": now_iso(),
    }


@api.post("/auth/register", status_code=201)
def register(payload: RegisterRequest, request: Request) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "auth.register",
            f"{payload.username}:{privacy_hash(payload.phone)}",
            limit=settings.auth_rate_limit_per_minute,
            window_seconds=60,
        )
    # Atomically claim the username and phone index keys before creating the
    # account, so two concurrent registrations of the same name/phone can no
    # longer both pass a check-then-act and produce a permanently-unloginnable
    # orphan record (P0-2). Claims are released if any later step fails.
    user_id = str(uuid.uuid4())
    if not store.claim_key("a", username_index_key(payload.username), {"user_id": user_id}):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if not store.claim_key("a", phone_index_key(payload.phone), {"user_id": user_id}):
        store.delete("a", username_index_key(payload.username))
        raise HTTPException(status_code=409, detail="该手机号已注册")
    try:
        sms.check_code(payload.phone, payload.code, "register")
    except Exception:
        store.delete("a", username_index_key(payload.username))
        store.delete("a", phone_index_key(payload.phone))
        raise
    user = {
        "id": user_id,
        "username": payload.username.strip(),
        "phone": payload.phone,
        "password_hash": hash_password(payload.password),
        "role": "user",
        "session_version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    save_user(user)
    audit("user.register", user["id"])
    return issue_auth_response(user, status_code=201, request=request)


@api.post("/auth/login")
def login(payload: LoginRequest, request: Request) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "auth.login",
            payload.username,
            limit=settings.auth_rate_limit_per_minute,
            window_seconds=60,
        )
    user = get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    audit("user.login", user["id"])
    return issue_auth_response(user, request=request)


@api.post("/auth/sms-login")
def sms_login(payload: SmsLoginRequest, request: Request) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "auth.sms_login",
            privacy_hash(payload.phone),
            limit=settings.auth_rate_limit_per_minute,
            window_seconds=60,
        )
    user = get_user_by_phone(payload.phone)
    if not user or user.get("role") == "admin":
        raise HTTPException(status_code=404, detail="该手机号未绑定普通用户账号")
    sms.check_code(payload.phone, payload.code, "login")
    audit("user.sms_login", user["id"], {"phone": mask_phone(payload.phone)})
    return issue_auth_response(user, request=request)


@api.post("/auth/sms-code")
def send_sms_code(
    payload: SmsCodeRequest,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "auth.sms_code",
            f"{payload.scene}:{privacy_hash(payload.phone)}",
            limit=max(3, settings.auth_rate_limit_per_minute // 2),
            window_seconds=60,
        )
    actor_id = "anonymous"
    if payload.scene == "register" and get_user_by_phone(payload.phone):
        raise HTTPException(status_code=409, detail="该手机号已注册")
    if payload.scene == "reset_password" and not get_user_by_phone(payload.phone):
        raise HTTPException(status_code=404, detail="该手机号尚未注册")
    if payload.scene == "login":
        user = get_user_by_phone(payload.phone)
        if not user or user.get("role") == "admin":
            raise HTTPException(status_code=404, detail="该手机号未绑定普通用户账号")
    if payload.scene == "change_phone":
        actor_id = current_user(request, authorization)["id"]
    result = sms.send_code(payload.phone, payload.scene)
    audit("sms.code_send", actor_id, {"scene": payload.scene, "phone": result["phone"]})
    return result


@api.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "auth.reset_password",
            privacy_hash(payload.phone),
            limit=max(3, settings.auth_rate_limit_per_minute // 2),
            window_seconds=60,
        )
    user = get_user_by_phone(payload.phone)
    if not user or user.get("role") == "admin":
        raise HTTPException(status_code=404, detail="普通用户账号不存在")
    sms.check_code(payload.phone, payload.code, "reset_password")
    user["password_hash"] = hash_password(payload.new_password)
    revoke_all_sessions(user)
    audit("user.password_self_reset", user["id"])
    return {"ok": True}


@api.get("/auth/me")
def me(user: Annotated[dict, Depends(current_user)]) -> dict:
    return public_user(user)


@api.post("/auth/avatar")
async def upload_account_avatar(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    data = await read_upload(file)
    try:
        avatar_data = prepare_avatar_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    previous_key = user.get("avatar_key")
    avatar_key = f"users/{user['id']}/profile/avatar.jpg"
    store.put_bytes("c", avatar_key, avatar_data, "image/jpeg")
    if previous_key and previous_key != avatar_key:
        store.delete("c", previous_key)
    user["avatar_key"] = avatar_key
    user["updated_at"] = now_iso()
    save_user(user)
    audit("user.avatar_update", user["id"])
    return {"user": public_user(user)}


@api.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    if not payload.current_password or not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")
    user["password_hash"] = hash_password(payload.new_password)
    revoke_all_sessions(user)
    audit("user.password_change", user["id"])
    return {"ok": True}


@api.post("/auth/change-phone")
def change_phone(payload: ChangePhoneRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    existing = get_user_by_phone(payload.phone)
    if existing and existing.get("id") != user["id"]:
        raise HTTPException(status_code=409, detail="该手机号已被其他账号使用")
    sms.check_code(payload.phone, payload.code, "change_phone")
    previous_phone = user.get("phone")
    user["phone"] = payload.phone
    user["updated_at"] = now_iso()
    save_user(user, previous_phone=previous_phone)
    audit("user.phone_change", user["id"], {"phone": mask_phone(payload.phone)})
    return {"user": public_user(user)}


@api.post("/auth/delete-account")
def delete_own_account(payload: DeleteAccountRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    if user.get("role") == "admin":
        raise HTTPException(status_code=403, detail="管理员账号不能在此注销")
    if payload.confirm_username.strip() != user["username"]:
        raise HTTPException(status_code=400, detail="输入的用户名不一致")
    if not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")
    user_id = user["id"]
    username = user["username"]
    delete_user_data(user)
    audit("user.self_delete", user_id, {"username": username})
    return {"ok": True}


@api.post("/auth/logout")
def logout(request: Request) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=settings.app_base_path or "/",
        secure=_resolve_cookie_secure(request),
        samesite=settings.auth_cookie_same_site,
    )
    return response


@api.post("/auth/logout-all")
def logout_all(request: Request, user: Annotated[dict, Depends(current_user)]) -> Response:
    revoke_all_sessions(user)
    audit("user.logout_all", user["id"])
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=settings.app_base_path or "/",
        secure=_resolve_cookie_secure(request),
        samesite=settings.auth_cookie_same_site,
    )
    return response


@api.get("/resume-templates")
def list_resume_templates(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    templates = [item for item in store.list_json("a", "resume-templates/") if item.get("active", False)]
    return [public_template(item) for item in sorted(templates, key=lambda item: (int(item.get("sort_order") or 9999), item.get("id", "")))]


@api.get("/resume-templates/{template_id}")
def get_resume_template(template_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="简历模板不存在或已下架")
    return public_template(template)


def _template_render_design(template: dict) -> dict:
    return apply_catalog_template(fallback_resume_design({}, str(template.get("base_theme") or "auto")), template)


@api.get("/resume-templates/{template_id}/source")
def preview_resume_template_source(template_id: str, user: Annotated[dict, Depends(current_user)]) -> Response:
    """Serve a real DOCX rendered with the same engine as final generation."""
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="简历模板不存在或已下架")
    sample = sample_resume_for_template(template)
    design = _template_render_design(template)
    data = resume_to_docx(sample, design=design)
    filename = f"{template_id}-preview.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.get("/resume-templates/{template_id}/preview.pdf")
async def preview_resume_template_pdf(template_id: str, user: Annotated[dict, Depends(current_user)]) -> Response:
    """Serve a real PDF preview — same layout pipeline as production generation."""
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="简历模板不存在或已下架")
    sample = sample_resume_for_template(template)
    design = _template_render_design(template)
    try:
        data = await resume_to_lapiscv_pdf(sample, design=design)
    except Exception:
        data = resume_to_pdf(sample, design=design)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(template_id + '-preview.pdf')}",
            "Cache-Control": "private, max-age=60",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.get("/resume-templates/{template_id}/source-link")
def resume_template_source_link(template_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="简历模板不存在或已下架")
    # Same-origin authenticated PDF preview for App WebView.
    return {
        "url": f"{settings.app_base_path}/api/resume-templates/{quote(template_id)}/preview.pdf",
        "filename": f"{template_id}-preview.pdf",
        "format": "pdf",
    }


@api.get("/resume-templates/{template_id}/preview-link")
def resume_template_preview_link(template_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    """Return a same-origin authenticated PDF preview for Android WebView."""
    template = get_catalog_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="简历模板不存在或已下架")
    return {
        "url": f"{settings.app_base_path}/api/resume-templates/{quote(template_id)}/preview.pdf",
        "filename": f"{template_id}-preview.pdf",
        "format": "pdf",
    }


@api.get("/resumes")
def list_resumes(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    items = store.list_json("a", f"resumes/{user['id']}/")
    return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)


@api.post("/resumes", status_code=201)
def create_resume(payload: ResumeCreateRequest, user: Annotated[dict, Depends(current_user)]) -> dict:
    resume_id = str(uuid.uuid4())
    existing = store.list_json("a", f"resumes/{user['id']}/")
    resume = {
        "id": resume_id,
        "user_id": user["id"],
        "name": payload.name,
        "content": payload.content.model_dump(),
        "source_type": "editor",
        "is_default": not existing,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.put_json("a", f"resumes/{user['id']}/{resume_id}.json", resume)
    audit("resume.create", user["id"], {"resume_id": resume_id, "source": "editor"})
    return resume


def _fallback_resume_from_text(text: str, filename: str) -> dict:
    """Heuristic structure so long/formal DOCX uploads still become editable resumes."""
    raw = str(text or "")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    name_guess = Path(filename).stem[:40] if filename else "未命名简历"
    # Prefer a short Chinese name near the top.
    skip_names = {"个人简历", "简历", "基本信息", "求职意向", "自我评价", "工作经历", "教育经历", "项目经历"}
    for line in lines[:20]:
        pure = re.sub(r"\s+", "", line)
        if pure in skip_names:
            continue
        if 2 <= len(pure) <= 4 and re.fullmatch(r"[\u4e00-\u9fff]+", pure):
            name_guess = pure
            break
        if "姓名" in line:
            m = re.search(r"姓名[:：\s]*([\u4e00-\u9fff]{2,4})", line)
            if m:
                name_guess = m.group(1)
                break
    # English resume header with Chinese name nearby (幸运日 etc.)
    if name_guess in {Path(filename).stem[:40], "未命名简历", "个人简历"} or name_guess in skip_names:
        for line in lines[:25]:
            m = re.search(r"([\u4e00-\u9fff]{2,4})", line)
            if m and m.group(1) not in skip_names:
                name_guess = m.group(1)
                break
    phone = ""
    email = ""
    for line in lines[:40]:
        if not phone:
            m = re.search(r"1[3-9]\d{9}", line.replace(" ", ""))
            if m:
                phone = m.group(0)
        if not email:
            m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", line)
            if m:
                email = m.group(0)
    # Split rough experience blocks by year patterns.
    experience: list[dict] = []
    current: dict | None = None
    for line in lines:
        if re.search(r"20\d{2}\s*[-–—至到]\s*(20\d{2}|至今|现在)", line) or re.search(
            r"20\d{2}[./年]\d{1,2}", line
        ):
            if current:
                experience.append(current)
            current = {"company": line[:80], "role": "", "period": line[:40], "details": []}
        elif current is not None:
            if len(current["details"]) < 8:
                current["details"].append(line[:120])
            elif not current.get("role") and len(line) <= 30:
                current["role"] = line
    if current:
        experience.append(current)
    if not experience and lines:
        experience = [{"company": "", "role": "待补充", "period": "", "details": lines[1:18]}]
    return {
        "name": name_guess,
        "title": next((line for line in lines[1:8] if 4 <= len(line) <= 24 and "简历" not in line), ""),
        "contact": {"phone": phone, "email": email},
        "summary": "\n".join(lines[:10])[:400],
        "skills": [],
        "experience": experience[:8],
        "projects": [],
        "education": [],
        "certificates": [],
    }


@api.post("/resumes/upload", status_code=201)
async def upload_resume(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    data = await read_upload(file)
    filename = file.filename or "resume"
    try:
        text = extract_document_text(filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not text:
        raise HTTPException(status_code=422, detail="文件中未提取到可用文字，可改用截图 OCR")
    try:
        # Cap wait so mobile/web clients do not sit on a spinner until nginx/proxy times out.
        structured = await asyncio.wait_for(ai.structure_resume(text), timeout=25)
        # Keep useful AI wording, but fill every missing section from the locally
        # extracted document instead of accepting an incomplete AI response.
        content = normalize_resume_content(structured, _fallback_resume_from_text(text, filename))
    except (AIServiceError, asyncio.TimeoutError, TimeoutError) as exc:
        # Prefer a usable draft over hard-failing the whole upload on model limits/timeouts.
        content = normalize_resume_content(_fallback_resume_from_text(text, filename))
        reason = "超时" if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) else str(exc)
        content["summary"] = (
            f"{content.get('summary') or ''}\n（AI 结构化未完全完成：{reason}。已生成可编辑草稿，请在本页核对补充。）".strip()
        )
    resume_id = str(uuid.uuid4())
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    object_key = f"users/{user['id']}/originals/{resume_id}.{suffix}"
    avatar_data = extract_resume_avatar(filename, data)
    avatar_key = f"users/{user['id']}/avatars/{resume_id}.jpg" if avatar_data else None
    existing = store.list_json("a", f"resumes/{user['id']}/")
    resume = {
        "id": resume_id,
        "user_id": user["id"],
        "name": Path(filename).stem[:80],
        "content": content,
        "source_type": "document",
        "source_key": object_key,
        "is_default": not existing,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    if avatar_key:
        resume["avatar_key"] = avatar_key
    stored: list[tuple[str, str]] = []
    try:
        store.put_bytes("b", object_key, data, file.content_type or "application/octet-stream")
        stored.append(("b", object_key))
        if avatar_key and avatar_data:
            store.put_bytes("c", avatar_key, avatar_data, "image/jpeg")
            stored.append(("c", avatar_key))
        store.put_json("a", f"resumes/{user['id']}/{resume_id}.json", resume)
    except BaseException:
        for bucket, key in stored:
            store.delete(bucket, key)
        raise
    audit("resume.upload", user["id"], {"resume_id": resume_id})
    return resume


@api.post("/resumes/ocr", status_code=201)
async def ocr_resume(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    data = await read_upload(file)
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传 PNG、JPG 或 WebP 图片")
    resume_id = str(uuid.uuid4())
    suffix = (file.filename or "resume.png").rsplit(".", 1)[-1].lower()
    object_key = f"users/{user['id']}/resume-images/{resume_id}.{suffix}"
    store.put_bytes("c", object_key, data, file.content_type or "image/png")
    content = normalize_resume_content(await ai.structure_resume("", store.presigned_url("c", object_key)))
    existing = store.list_json("a", f"resumes/{user['id']}/")
    resume = {
        "id": resume_id,
        "user_id": user["id"],
        "name": f"截图简历 {datetime.now().strftime('%m-%d %H:%M')}",
        "content": content,
        "source_type": "image",
        "source_key": object_key,
        "is_default": not existing,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.put_json("a", f"resumes/{user['id']}/{resume_id}.json", resume)
    audit("resume.ocr", user["id"], {"resume_id": resume_id})
    return resume


@api.post("/resumes/{resume_id}/avatar")
async def upload_resume_avatar(
    resume_id: str, file: UploadFile = File(...), user: dict = Depends(current_user)
) -> dict:
    resume_key = f"resumes/{user['id']}/{resume_id}.json"
    resume = require_owner(store.get_json("a", resume_key), user)
    data = await read_upload(file)
    try:
        avatar_data = prepare_avatar_image(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    avatar_key = f"users/{user['id']}/avatars/{resume_id}.jpg"
    store.put_bytes("c", avatar_key, avatar_data, "image/jpeg")
    resume["avatar_key"] = avatar_key
    resume["updated_at"] = now_iso()
    store.put_json("a", resume_key, resume)
    audit("resume.avatar_update", user["id"], {"resume_id": resume_id})
    return resume


@api.get("/resumes/{resume_id}")
def get_resume(resume_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    return require_owner(store.get_json("a", f"resumes/{user['id']}/{resume_id}.json"), user)


@api.get("/resumes/{resume_id}/download-original")
def download_resume_original(resume_id: str, user: Annotated[dict, Depends(current_user)]) -> Response:
    resume = require_owner(store.get_json("a", f"resumes/{user['id']}/{resume_id}.json"), user)
    key = resume.get("source_key")
    if not key:
        raise HTTPException(status_code=404, detail="这份简历没有原始文件")
    bucket = "c" if resume.get("source_type") == "image" else "b"
    data = store.get_bytes(bucket, key)
    if not data:
        raise HTTPException(status_code=404, detail="原始文件不存在或已过期")
    suffix = key.rsplit(".", 1)[-1].lower() if "." in key else "bin"
    content_type = mimetypes.types_map.get(f".{suffix}", "application/octet-stream")
    filename = f"{resume.get('name') or '原简历'}.{suffix}"
    store.mark_download(len(data))
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.patch("/resumes/{resume_id}")
def update_resume(payload: ResumeUpdateRequest, resume_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    key = f"resumes/{user['id']}/{resume_id}.json"
    resume = require_owner(store.get_json("a", key), user)
    if payload.name is not None:
        resume["name"] = payload.name
    if payload.content is not None:
        resume["content"] = payload.content.model_dump()
    resume["updated_at"] = now_iso()
    store.put_json("a", key, resume)
    audit("resume.update", user["id"], {"resume_id": resume_id})
    return resume


@api.post("/resumes/{resume_id}/default")
def set_default_resume(resume_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    resumes = store.list_json("a", f"resumes/{user['id']}/")
    target = None
    for resume in resumes:
        resume["is_default"] = resume["id"] == resume_id
        if resume["is_default"]:
            target = resume
        store.put_json("a", f"resumes/{user['id']}/{resume['id']}.json", resume)
    if not target:
        raise HTTPException(status_code=404, detail="简历不存在")
    audit("resume.set_default", user["id"], {"resume_id": resume_id})
    return target


@api.delete("/resumes/{resume_id}")
def delete_resume(resume_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    key = f"resumes/{user['id']}/{resume_id}.json"
    resume = require_owner(store.get_json("a", key), user)
    if resume.get("source_key"):
        bucket = "c" if resume.get("source_type") == "image" else "b"
        store.delete(bucket, resume["source_key"])
    if resume.get("avatar_key"):
        store.delete("c", resume["avatar_key"])
    store.delete("a", key)
    remaining = store.list_json("a", f"resumes/{user['id']}/")
    if resume.get("is_default") and remaining:
        remaining[0]["is_default"] = True
        store.put_json("a", f"resumes/{user['id']}/{remaining[0]['id']}.json", remaining[0])
    audit("resume.delete", user["id"], {"resume_id": resume_id})
    return {"ok": True}


def queue_jd_task(user: dict, source: str, detail: str) -> dict:
    task_id = str(uuid.uuid4())
    record = {
        "id": task_id,
        "user_id": user["id"],
        "username": user["username"],
        "source": source,
        "source_detail": detail,
        "status": "processing",
        "progress_message": "正在后台解析岗位，可以离开此页面",
        "result": None,
        "error": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.put_json("a", f"jd-tasks/{user['id']}/{task_id}.json", record)
    save_task_log(
        {
            "id": task_id,
            "task_type": "jd_parse",
            "user_id": user["id"],
            "username": user["username"],
            "detail": detail,
            "status": "processing",
            "error": None,
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
    )
    return record


async def process_jd_job(
    task_id: str,
    user: dict,
    source: str,
    text: str = "",
    url: str = "",
    image_urls: list[str] | None = None,
    stored_keys: list[str] | None = None,
    raise_on_failure: bool = False,
) -> None:
    record_key = f"jd-tasks/{user['id']}/{task_id}.json"
    try:
        record = store.get_json("a", record_key)
        if not record:
            return
        record.update({"status": "processing", "updated_at": now_iso()})
        store.put_json("a", record_key, record)
        update_task_log(task_id, status="processing", error=None)
        if source == "url":
            page_text, structured = await fetch_job_page(url)
            result = structured or await ai.structure_jd(page_text)
        elif source == "image":
            result = await ai.structure_jd(image_urls=image_urls or [])
            result["source_keys"] = stored_keys or []
            result["image_count"] = len(stored_keys or [])
            if len(stored_keys or []) == 1:
                result["source_key"] = (stored_keys or [""])[0]
        else:
            result = await ai.structure_jd(text)
        result = validate_jd_result(result)
        result["insight"] = build_jd_insight(result)
        record = store.get_json("a", record_key)
        if not record:
            return
        record.update(
            {
                "status": "completed",
                "progress_message": "岗位解析完成",
                "result": result,
                "updated_at": now_iso(),
            }
        )
        store.put_json("a", record_key, record)
        update_task_log(task_id, status="completed", detail=result.get("title") or "岗位解析")
        audit("jd.parse.complete", user["id"], {"task_id": task_id, "source": source})
    except Exception as exc:
        if source == "image":
            for key in stored_keys or []:
                try:
                    store.delete("c", key)
                except Exception:
                    pass
        message = (
            str(exc)
            if isinstance(exc, (AIServiceError, ValueError, httpx.HTTPError))
            else "岗位解析过程中出现异常，请稍后重试"
        )
        record = store.get_json("a", record_key)
        if record:
            record.update(
                {
                    "status": "failed",
                    "progress_message": "岗位解析失败",
                    "error": message,
                    "updated_at": now_iso(),
                }
            )
            store.put_json("a", record_key, record)
        task_changes = {"status": "failed", "error": message}
        if isinstance(exc, AIServiceError):
            safe_metadata = {
                key: value
                for key, value in exc.metadata.items()
                if key in {"model", "finish_reason", "retry_count"}
            }
            task_changes.update(error_category=exc.category, model_metadata=safe_metadata)
        update_task_log(task_id, **task_changes)
        audit("jd.parse.failed", user["id"], {"task_id": task_id, "source": source, "reason": message})
        if raise_on_failure:
            raise


@api.post("/jd/parse", status_code=202)
async def parse_jd(
    payload: JDRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "task.jd_parse",
            user["id"],
            limit=settings.task_rate_limit_per_hour,
            window_seconds=3600,
        )
    if payload.source_type == "url":
        if not payload.url:
            raise HTTPException(status_code=400, detail="请填写岗位链接")
        text = ""
        detail = payload.url
    else:
        text = (payload.text or "").strip()
        if len(text) < 20:
            raise HTTPException(status_code=400, detail="岗位描述至少需要 20 个字符")
        detail = "文本岗位描述"
    record = queue_jd_task(dict(user), payload.source_type, detail)
    dispatch_task(
        background_tasks,
        "app.worker.process_jd_task",
        record["id"],
        process_jd_job,
        task_id=record["id"],
        user=dict(user),
        source=payload.source_type,
        text=text,
        url=payload.url or "",
    )
    audit("jd.parse.queued", user["id"], {"task_id": record["id"], "source": payload.source_type})
    return record


@api.get("/jd/tasks")
def list_jd_tasks(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    records = store.list_json("a", f"jd-tasks/{user['id']}/")
    for record in records:
        if not record.get("source_detail"):
            task_log = store.get_json("a", f"tasks/{record.get('id', '')}.json") or {}
            record["source_detail"] = task_log.get("detail") or "岗位解析"
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


@api.delete("/jd/tasks/{task_id}")
def delete_jd_task(task_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    """Remove a user's parsed-job record and its uploaded screenshots, if any."""
    key = f"jd-tasks/{user['id']}/{task_id}.json"
    record = require_owner(store.get_json("a", key), user)
    for source_key in (record.get("result") or {}).get("source_keys") or []:
        if source_key:
            store.delete("c", source_key)
    source_key = (record.get("result") or {}).get("source_key")
    if source_key:
        store.delete("c", source_key)
    store.delete("a", key)
    task_queue.cancel(task_id)
    update_task_log(task_id, status="cancelled", error=None)
    # The all-site task log is an operational audit trail, so it intentionally remains.
    audit("jd.parse.delete", user["id"], {"task_id": task_id})
    return {"ok": True}


@api.get("/jd/tasks/{task_id}")
def get_jd_task(task_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    return require_owner(store.get_json("a", f"jd-tasks/{user['id']}/{task_id}.json"), user)


@api.post("/jd/ocr", status_code=202)
async def parse_jd_image(
    background_tasks: BackgroundTasks,
    request: Request,
    files: list[UploadFile] | None = File(default=None),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(current_user),
) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "task.jd_ocr",
            user["id"],
            limit=settings.task_rate_limit_per_hour,
            window_seconds=3600,
        )
    uploads = list(files or [])
    if file:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="请至少上传一张岗位截图")
    if len(uploads) > MAX_JD_IMAGE_COUNT:
        raise HTTPException(status_code=413, detail=f"岗位截图最多上传 {MAX_JD_IMAGE_COUNT} 张")
    validated_uploads: list[tuple[bytes, str, str]] = []
    total_bytes = 0
    for index, upload in enumerate(uploads, start=1):
        content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
        extension = JD_IMAGE_EXTENSIONS.get(content_type)
        if not extension:
            raise HTTPException(status_code=400, detail=f"第 {index} 个文件仅支持 PNG、JPG/JPEG 或 WebP 图片")
        data = await read_upload(upload)
        if not jd_image_magic_matches(content_type, data):
            raise HTTPException(status_code=400, detail=f"第 {index} 个文件内容与图片格式不匹配")
        total_bytes += len(data)
        if total_bytes > MAX_JD_IMAGE_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="岗位截图合计不能超过 30MB")
        validated_uploads.append((data, content_type, extension))

    batch_id = str(uuid.uuid4())
    stored_keys: list[str] = []
    image_urls: list[str] = []
    try:
        for index, (data, content_type, extension) in enumerate(validated_uploads, start=1):
            key = f"users/{user['id']}/jd-images/{batch_id}-{index:02d}.{extension}"
            stored_keys.append(key)
            store.put_bytes("c", key, data, content_type)
            image_urls.append(store.presigned_url("c", key))
        record = queue_jd_task(dict(user), "image", f"{len(stored_keys)} 张岗位截图")
        dispatch_task(
            background_tasks,
            "app.worker.process_jd_task",
            record["id"],
            process_jd_job,
            task_id=record["id"],
            user=dict(user),
            source="image",
            text="",
            url="",
            image_urls=image_urls,
            stored_keys=stored_keys,
        )
        audit(
            "jd.ocr.queued",
            user["id"],
            {"task_id": record["id"], "batch_id": batch_id, "image_count": len(stored_keys)},
        )
        return record
    except BaseException:
        for key in stored_keys:
            try:
                store.delete("c", key)
            except Exception:
                pass
        raise


async def process_generation_job(
    job_id: str,
    user: dict,
    resume: dict,
    jd: dict,
    requested_theme: str = "auto",
    catalog_template: dict | None = None,
    optimized_content: dict | None = None,
    requested_language: str = "zh",
    requested_highlights: list[str] | None = None,
    raise_on_failure: bool = False,
) -> None:
    record_key = f"generations/{user['id']}/{job_id}.json"
    docx_key = f"users/{user['id']}/generated/{job_id}.docx"
    pdf_key = f"users/{user['id']}/generated/{job_id}.pdf"
    stored_keys: list[str] = []
    try:
        starting_record = store.get_json("a", record_key)
        if not starting_record:
            return
        starting_record.update({"status": "processing", "updated_at": now_iso()})
        store.put_json("a", record_key, starting_record)
        update_task_log(job_id, status="processing", error=None)
        planned_design = None
        if optimized_content is not None:
            optimized_raw = optimized_content
        elif requested_theme == "auto":
            optimized_raw, planned_design = await asyncio.gather(
                ai.rewrite_resume(resume["content"], jd, requested_language, requested_highlights),
                ai.plan_resume_design(jd),
                return_exceptions=True,
            )
            if isinstance(optimized_raw, Exception):
                raise optimized_raw
            if isinstance(planned_design, Exception):
                planned_design = None
        else:
            optimized_raw = await ai.rewrite_resume(resume["content"], jd, requested_language, requested_highlights)
        design = apply_catalog_template(resolve_resume_design(jd, requested_theme, planned_design), catalog_template)
        optimized = normalize_resume_content(optimized_raw, resume["content"])
        jd_insight = build_jd_insight(jd, optimized)
        ai_score = score_generated_resume(optimized, jd, design)
        avatar_data = store.get_bytes("c", resume["avatar_key"]) if resume.get("avatar_key") else None
        docx_data = resume_to_docx(optimized, avatar_data=avatar_data, design=design)
        design = dict(design)
        try:
            pdf_data = await resume_to_lapiscv_pdf(optimized, avatar_data=avatar_data, design=design)
            design["render_engine"] = "lapiscv_chromium"
        except Exception as render_exc:
            pdf_data = resume_to_pdf(optimized, avatar_data=avatar_data, design=design)
            design["render_engine"] = "reportlab_fallback"
            design["render_warning"] = str(render_exc)[:160]
        if store.get_json("a", record_key) is None:
            return
        store.put_bytes(
            "b",
            docx_key,
            docx_data,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        stored_keys.append(docx_key)
        store.put_bytes("b", pdf_key, pdf_data, "application/pdf")
        stored_keys.append(pdf_key)
        record = store.get_json("a", record_key)
        if record is None:
            for key in stored_keys:
                store.delete("b", key)
            return
        record.update(
            {
                "optimized": optimized,
                "design": design,
                "jd_insight": jd_insight,
                "ai_score": ai_score,
                "ai_report": {
                    "summary": "AI已完成岗位需求分析、经历表达优化、关键词覆盖检查和版式匹配。",
                    "optimizations": ai_score.get("highlights", []),
                    "quality_checks": ai_score.get("checks", []),
                },
                "status": "completed",
                "progress_message": "适配简历已生成，可下载 Word 或 PDF",
                "files": {
                    "docx": {"key": docx_key, "size": len(docx_data)},
                    "pdf": {"key": pdf_key, "size": len(pdf_data)},
                },
                "updated_at": now_iso(),
            }
        )
        settle_generation_credits(record, success=True)
        store.put_json("a", record_key, record)
        update_task_log(job_id, status="completed", detail=(jd.get("title") or "简历适配"))
        radar_job_id = str(record.get("radar_job_id") or "")
        if radar_job_id:
            radar.mark_adapted(user["id"], radar_job_id, job_id)
        audit("generation.complete", user["id"], {"generation_id": job_id, "radar_job_id": radar_job_id})
    except Exception as exc:
        for key in stored_keys:
            try:
                store.delete("b", key)
            except Exception:
                pass
        message = str(exc) if isinstance(exc, AIServiceError) else "生成过程中出现异常，请稍后重试"
        if isinstance(exc, AIServiceError):
            # Keep category for retry UX without leaking upstream payloads.
            message = f"{message}（可点「重试」再次生成）"
        record = store.get_json("a", record_key)
        if record:
            record.update(
                {
                    "status": "failed",
                    "progress_message": "生成失败",
                    "error": message,
                    "error_category": getattr(exc, "category", type(exc).__name__),
                    "retryable": True,
                    "updated_at": now_iso(),
                }
            )
            settle_generation_credits(record, success=False)
            store.put_json("a", record_key, record)
        update_task_log(job_id, status="failed", error=message)
        audit(
            "generation.failed",
            user["id"],
            {"generation_id": job_id, "error_type": type(exc).__name__, "reason": message[:200]},
        )
        if raise_on_failure:
            raise


@api.post("/generations", status_code=202)
async def generate_resume(
    payload: GenerateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "task.generation",
            user["id"],
            limit=settings.task_rate_limit_per_hour,
            window_seconds=3600,
        )
    resumes = store.list_json("a", f"resumes/{user['id']}/")
    resume = next((item for item in resumes if item["id"] == payload.resume_id), None)
    if resume is None and payload.resume_id is None:
        resume = next((item for item in resumes if item.get("is_default")), None)
    if resume is None:
        raise HTTPException(status_code=404, detail="请先选择或设置一份默认简历")
    if payload.radar_job_id and not radar.get_job(payload.radar_job_id):
        raise HTTPException(status_code=404, detail="关联岗位不存在或已失效，请重新从岗位雷达选择")
    allowed_themes = {"auto", "tech_indigo", "operations_terra", "executive_navy", "care_teal", "creative_plum", "ats_mono"}
    requested_theme = payload.design_theme if payload.design_theme in allowed_themes else "auto"
    requested_language = payload.language if payload.language in {"zh", "en", "bilingual"} else "zh"
    requested_highlights = [str(item).strip() for item in (payload.highlights or []) if str(item).strip()][:5]
    template = get_catalog_template(payload.template_id)
    if payload.template_id and not template:
        raise HTTPException(status_code=404, detail="所选简历模板不存在或已下架")
    try:
        jd = validate_jd_result(dict(payload.jd or {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # If the client still holds a deleted licensed-* id (or none), auto-pick a
    # built-in layout family so generated PDFs never all collapse to one skeleton.
    if not template:
        theme_guess = fallback_resume_design(jd, requested_theme)
        preferred_variant = str(theme_guess.get("layout_variant") or "top_profile")
        for item in default_templates():
            if item.get("layout_variant") == preferred_variant and item.get("active", True):
                template = get_catalog_template(item["id"]) or item
                break
        if not template:
            template = get_catalog_template(default_templates()[0]["id"]) or default_templates()[0]
    job_id = str(uuid.uuid4())
    credit_cost = int(CREDIT_COSTS["resume_generation"])
    reserve_credits(
        user["id"],
        credit_cost,
        kind="resume_generation",
        reference_id=job_id,
        detail=f"预扣：生成简历 {jd.get('title') or ''}".strip(),
    )
    design = apply_catalog_template(fallback_resume_design(jd, requested_theme), template)
    record = {
        "id": job_id,
        "user_id": user["id"],
        "username": user["username"],
        "resume_id": resume["id"],
        "resume_name": resume["name"],
        "radar_job_id": payload.radar_job_id,
        "jd": jd,
        "optimized": None,
        "design": design,
        "catalog_template_id": template.get("id") if template else None,
        "status": "processing",
        "progress_message": "正在后台优化内容并生成文件，可离开此页面",
        "progress_steps": [
            {"label": "读取职业经历", "status": "processing"},
            {"label": "分析岗位需求", "status": "pending"},
            {"label": "提取核心关键词", "status": "pending"},
            {"label": "优化经历表达", "status": "pending"},
            {"label": "设计简历版式", "status": "pending"},
        ],
        "files": {},
        "credit_cost": credit_cost,
        "credit_settled": False,
        "credit_status": "reserved" if credit_cost else "free",
        "retryable": False,
        "requested_theme": requested_theme,
        "requested_language": requested_language,
        "requested_highlights": requested_highlights,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.put_json("a", f"generations/{user['id']}/{job_id}.json", record)
    save_task_log(
        {
            "id": job_id,
            "task_type": "resume_generation",
            "user_id": user["id"],
            "username": user["username"],
            "detail": str(jd.get("title") or "简历适配"),
            "status": "processing",
            "error": None,
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
    )
    dispatch_task(
        background_tasks,
        "app.worker.process_generation_task",
        job_id,
        process_generation_job,
        job_id=job_id,
        user={"id": user["id"], "username": user.get("username"), "role": user.get("role")},
        resume={"id": resume["id"], "name": resume.get("name"), "content": resume.get("content"), "avatar_key": resume.get("avatar_key")},
        jd=dict(jd),
        requested_theme=requested_theme,
        requested_language=requested_language,
        requested_highlights=requested_highlights,
        catalog_template=template,
    )
    audit("generation.queued", user["id"], {"generation_id": job_id, "radar_job_id": payload.radar_job_id})
    return record


@api.post("/generations/{generation_id}/regenerate", status_code=202)
async def regenerate_with_theme(
    generation_id: str,
    payload: RegenerateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "task.regenerate",
            user["id"],
            limit=settings.task_rate_limit_per_hour,
            window_seconds=3600,
        )
    source = require_owner(store.get_json("a", f"generations/{user['id']}/{generation_id}.json"), user)
    if source.get("status") != "completed" or not source.get("optimized"):
        raise HTTPException(status_code=409, detail="原简历尚未生成完成")
    resume = require_owner(
        store.get_json("a", f"resumes/{user['id']}/{source.get('resume_id')}.json"), user
    )
    job_id = str(uuid.uuid4())
    created_at = now_iso()
    try:
        jd = validate_jd_result(dict(source.get("jd") or {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    inherited_template_id = str((source.get("design") or {}).get("catalog_template_id") or source.get("catalog_template_id") or "")
    selected_template_id = payload.template_id or inherited_template_id or None
    template = get_catalog_template(selected_template_id)
    if selected_template_id and not template:
        raise HTTPException(status_code=404, detail="所选简历模板不存在或已下架")
    credit_cost = int(CREDIT_COSTS["resume_regenerate"])
    reserve_credits(
        user["id"],
        credit_cost,
        kind="resume_regenerate",
        reference_id=job_id,
        detail=f"预扣：更换模板 {jd.get('title') or ''}".strip(),
    )
    record = {
        "id": job_id,
        "user_id": user["id"],
        "username": user["username"],
        "resume_id": resume["id"],
        "resume_name": resume["name"],
        "parent_generation_id": generation_id,
        "jd": jd,
        "optimized": source["optimized"],
        "design": apply_catalog_template(fallback_resume_design(jd, payload.design_theme), template),
        "catalog_template_id": template.get("id") if template else None,
        "radar_job_id": source.get("radar_job_id"),
        "status": "processing",
        "progress_message": "正在按新模板重新排版，可离开此页面",
        "jd_insight": source.get("jd_insight"),
        "ai_score": source.get("ai_score"),
        "ai_report": source.get("ai_report"),
        "progress_steps": [
            {"label": "复用已优化内容", "status": "completed"},
            {"label": "应用新模板风格", "status": "processing"},
            {"label": "重新生成 Word/PDF", "status": "pending"},
        ],
        "files": {},
        "credit_cost": credit_cost,
        "credit_settled": False,
        "credit_status": "reserved" if credit_cost else "free",
        "retryable": False,
        "requested_theme": payload.design_theme,
        "requested_language": source.get("requested_language", "zh"),
        "created_at": created_at,
        "updated_at": created_at,
    }
    store.put_json("a", f"generations/{user['id']}/{job_id}.json", record)
    save_task_log(
        {
            "id": job_id,
            "task_type": "resume_generation",
            "user_id": user["id"],
            "username": user["username"],
            "detail": f"更换模板：{jd.get('title') or '简历适配'}",
            "status": "processing",
            "error": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    dispatch_task(
        background_tasks,
        "app.worker.process_generation_task",
        job_id,
        process_generation_job,
        job_id=job_id,
        user={"id": user["id"], "username": user.get("username"), "role": user.get("role")},
        resume={"id": resume["id"], "name": resume.get("name"), "content": resume.get("content"), "avatar_key": resume.get("avatar_key")},
        jd=jd,
        requested_theme=payload.design_theme,
        requested_language=source.get("requested_language", "zh"),
        catalog_template=template,
        optimized_content=dict(source["optimized"]),
    )
    audit("generation.regenerate_queued", user["id"], {"generation_id": job_id, "source_id": generation_id})
    return record


@api.post("/generations/{generation_id}/retry", status_code=202)
async def retry_generation(
    generation_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    user: Annotated[dict, Depends(current_user)],
) -> dict:
    """Re-queue a failed generation with a fresh credit reserve."""
    if settings.rate_limit_enabled:
        enforce_rate_limit(
            request,
            "task.generation_retry",
            user["id"],
            limit=settings.task_rate_limit_per_hour,
            window_seconds=3600,
        )
    source = require_owner(store.get_json("a", f"generations/{user['id']}/{generation_id}.json"), user)
    if source.get("status") != "failed":
        raise HTTPException(status_code=409, detail="仅失败的任务可以重试")
    resume = require_owner(store.get_json("a", f"resumes/{user['id']}/{source.get('resume_id')}.json"), user)
    try:
        jd = validate_jd_result(dict(source.get("jd") or {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    template = get_catalog_template(source.get("catalog_template_id"))
    theme = str(source.get("requested_theme") or (source.get("design") or {}).get("base_theme") or "auto")
    payload = GenerateRequest(
        resume_id=resume["id"],
        jd=jd,
        design_theme=theme if theme in {"auto", "tech_indigo", "operations_terra", "executive_navy", "care_teal", "creative_plum", "ats_mono"} else "auto",
        radar_job_id=source.get("radar_job_id"),
        template_id=source.get("catalog_template_id"),
        language=source.get("requested_language", "zh"),
    )
    return await generate_resume(payload, background_tasks, request, user)


@api.get("/generations")
def generation_history(user: Annotated[dict, Depends(current_user)]) -> list[dict]:
    records = store.list_json("a", f"generations/{user['id']}/")
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


def remove_generation(record: dict) -> None:
    for file_info in (record.get("files") or {}).values():
        if file_info.get("key"):
            store.delete("b", file_info["key"])
    if (record.get("cover") or {}).get("key"):
        store.delete("c", record["cover"]["key"])
    store.delete("a", f"generations/{record['user_id']}/{record['id']}.json")


@api.delete("/generations/{generation_id}")
def delete_generation(generation_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    key = f"generations/{user['id']}/{generation_id}.json"
    record = require_owner(store.get_json("a", key), user)
    if record.get("status") == "processing" and not record.get("credit_settled"):
        settle_generation_credits(record, success=False)
        store.put_json("a", key, record)
    remove_generation(record)
    task_queue.cancel(generation_id)
    update_task_log(generation_id, status="cancelled", error=None)
    audit("generation.delete", user["id"], {"generation_id": generation_id})
    return {"ok": True}


@api.get("/generations/{generation_id}/download/{file_type}")
def download_generation(
    generation_id: str,
    file_type: str,
    user: Annotated[dict, Depends(current_user)],
) -> Response:
    record = require_owner(store.get_json("a", f"generations/{user['id']}/{generation_id}.json"), user)
    return generation_file_response(record, file_type)


def generation_file_response(record: dict, file_type: str) -> Response:
    if file_type not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="仅支持下载 Word 或 PDF")
    if record.get("status") != "completed":
        raise HTTPException(status_code=409, detail="简历尚未生成完成")
    file_info = (record.get("files") or {}).get(file_type) or {}
    key = file_info.get("key")
    data = store.get_bytes("b", key) if key else None
    if not data:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    title = str((record.get("jd") or {}).get("title") or "适配简历")
    safe_title = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", title)[:50] or "适配简历"
    filename = f"{safe_title}-{record.get('resume_name') or '简历'}.{file_type}"
    content_type = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }[file_type]
    store.mark_download(len(data))
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _ensure_file_access(user: dict, key: str) -> str:
    """Validate that ``key`` belongs to the caller and return the normalised key.

    The previous ``f"users/{id}/" in key`` substring test could be bypassed with a
    traversal payload such as ``users/<self>/../../users/<victim>/resume.docx`` —
    the substring matched while the object actually resolved to another user's
    file (P0-3). We normalise the path first (collapsing ``..``), reject any
    residual traversal, then require the caller's own prefix; admins may read any
    key. The normalised key is returned so all downstream store calls use it.
    """
    normalized = posixpath.normpath(key).lstrip("/")
    if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        raise HTTPException(status_code=400, detail="非法文件路径")
    if user.get("role") != "admin" and not normalized.startswith(f"users/{user['id']}/"):
        raise HTTPException(status_code=403, detail="无权访问该文件")
    return normalized


@api.get("/files/{bucket}/{key:path}")
def download_file(bucket: str, key: str, user: Annotated[dict, Depends(current_user)]) -> RedirectResponse:
    if bucket not in {"b", "c"}:
        raise HTTPException(status_code=400, detail="文件分区无效")
    key = _ensure_file_access(user, key)
    safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", key.rsplit("/", 1)[-1])
    try:
        size = store.object_size(bucket, key)
        url = store.presigned_url(bucket, key, safe_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc
    store.mark_download(size)
    return RedirectResponse(url=url, status_code=307)


@api.get("/file-link")
def file_link(bucket: str, key: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    if bucket not in {"b", "c"}:
        raise HTTPException(status_code=400, detail="文件分区无效")
    key = _ensure_file_access(user, key)
    safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", key.rsplit("/", 1)[-1])
    try:
        size = store.object_size(bucket, key)
        url = store.presigned_url(bucket, key, safe_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc
    store.mark_download(size)
    owner_id = user["id"]
    matched = re.match(r"users/([^/]+)/", key)
    if matched:
        owner_id = matched.group(1)
    token = issue_file_token(bucket, key, settings, safe_name, owner_id=owner_id, purpose="preview")
    proxy_url = f"{settings.app_base_path}/api/file-preview/{token}"
    return {"url": url, "proxy_url": proxy_url, "expires_in": min(settings.tos_presign_seconds, 20 * 60)}


@api.get("/file-preview/{token}")
def preview_file(token: str) -> Response:
    try:
        payload = decode_file_token(token, settings)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=403, detail="文件预览链接已失效，请返回后重新打开") from exc
    bucket = payload.get("bucket")
    key = payload.get("key")
    if bucket not in {"b", "c"} or not key:
        raise HTTPException(status_code=400, detail="文件预览链接无效")
    owner_id = str(payload.get("owner_id") or "")
    matched = re.match(r"users/([^/]+)/", str(key))
    if not owner_id or (matched and owner_id != matched.group(1)):
        raise HTTPException(status_code=403, detail="文件预览链接无权访问该资源")
    data = store.get_bytes(bucket, key)
    if not data:
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    filename = payload.get("filename") or key.rsplit("/", 1)[-1]
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else key.rsplit(".", 1)[-1].lower()
    content_type = mimetypes.types_map.get(f".{suffix}", "application/octet-stream")
    store.mark_download(len(data))
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.get("/admin/resume-templates")
def admin_resume_templates(_: Annotated[dict, Depends(admin_user)]) -> list[dict]:
    templates = store.list_json("a", "resume-templates/")
    return sorted(templates, key=lambda item: (int(item.get("sort_order") or 9999), item.get("id", "")))


@api.patch("/admin/resume-templates/{template_id}")
def admin_update_resume_template(
    template_id: str, payload: dict, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    template = store.get_json("a", catalog_key(template_id))
    if not isinstance(template, dict):
        raise HTTPException(status_code=404, detail="简历模板不存在")
    allowed = {"name", "category", "display_category", "tags", "accent", "soft", "ribbon", "ink", "base_theme", "layout_id", "layout_variant", "header_mode", "section_style", "avatar_mode", "word_layout", "density", "active", "sort_order", "preview_note"}
    for key, value in payload.items():
        if key not in allowed:
            continue
        if key == "tags":
            template[key] = [str(item)[:40] for item in value[:12]] if isinstance(value, list) else template.get(key, [])
        elif key == "active":
            template[key] = bool(value)
        elif key == "sort_order":
            template[key] = max(1, min(9999, int(value)))
        elif key in {"base_theme"}:
            if value in {"tech_indigo", "operations_terra", "executive_navy", "care_teal", "creative_plum", "ats_mono"}:
                template[key] = value
        else:
            template[key] = str(value)[:160]
    template["version"] = int(template.get("version") or 1) + 1
    template["updated_at"] = now_iso()
    store.put_json("a", catalog_key(template_id), template)
    audit("admin.resume_template_update", admin["id"], {"template_id": template_id})
    return template


@api.get("/admin/users")
def admin_users(_: Annotated[dict, Depends(admin_user)]) -> list[dict]:
    users = store.list_json("a", "users/")
    payload = []
    for user in users:
        item = public_user(user)
        if user.get("role") != "admin":
            account = billing_account(user["id"])
            item["billing"] = {
                "credits": int(account.get("credits", 0)),
                "reserved": int(account.get("reserved", 0)),
                "available": available_credits(account),
                "suspended": bool(account.get("suspended")),
                "plan": account.get("plan") or "free_trial",
            }
        payload.append(item)
    return sorted(payload, key=lambda item: item.get("created_at", ""), reverse=True)


@api.patch("/admin/users/{user_id}/credits")
def admin_update_user_credits(
    user_id: str,
    payload: AdminCreditUpdateRequest,
    admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Manually set / adjust / clear / suspend a user's generation credits."""
    target = store.get_json("a", f"users/{user_id}.json")
    if not target or target.get("role") == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    account = billing_account(user_id)
    before = {
        "credits": int(account.get("credits", 0)),
        "reserved": int(account.get("reserved", 0)),
        "suspended": bool(account.get("suspended")),
    }
    note = (payload.note or "").strip() or f"管理员{payload.mode}"
    mode = payload.mode
    amount = int(payload.amount or 0)

    if mode == "set":
        if payload.amount is None:
            raise HTTPException(status_code=422, detail="请填写要设置的额度")
        account["credits"] = max(0, amount)
        account["reserved"] = min(int(account.get("reserved", 0)), account["credits"])
        record_ledger(user_id, "admin_set", account["credits"] - before["credits"], note, admin["id"])
    elif mode == "add":
        if amount <= 0:
            raise HTTPException(status_code=422, detail="增加额度必须大于 0")
        account["credits"] = int(account.get("credits", 0)) + amount
        record_ledger(user_id, "admin_add", amount, note, admin["id"])
    elif mode == "sub":
        if amount <= 0:
            raise HTTPException(status_code=422, detail="减少额度必须大于 0")
        credits = int(account.get("credits", 0))
        reserved = int(account.get("reserved", 0))
        free = max(0, credits - reserved)
        use = min(amount, free)
        account["credits"] = credits - use
        record_ledger(user_id, "admin_sub", -use, note, admin["id"])
    elif mode == "clear":
        reserved = int(account.get("reserved", 0))
        # Keep reserved slots for in-flight jobs, wipe the rest.
        cleared = max(0, int(account.get("credits", 0)) - reserved)
        account["credits"] = reserved
        record_ledger(user_id, "admin_clear", -cleared, note or "管理员一键清零", admin["id"])
    elif mode == "suspend":
        account["suspended"] = True
        record_ledger(user_id, "admin_suspend", 0, note or "管理员暂停额度", admin["id"])
    elif mode == "resume":
        account["suspended"] = False
        record_ledger(user_id, "admin_resume", 0, note or "管理员恢复额度", admin["id"])
    else:
        raise HTTPException(status_code=422, detail="不支持的额度操作")

    account["updated_at"] = now_iso()
    account["updated_by"] = admin["id"]
    store.put_json("a", account_key(user_id), account)
    audit(
        "admin.credit_update",
        admin["id"],
        {
            "user_id": user_id,
            "mode": mode,
            "amount": amount,
            "before": before,
            "after": {
                "credits": int(account.get("credits", 0)),
                "reserved": int(account.get("reserved", 0)),
                "suspended": bool(account.get("suspended")),
            },
            "note": note,
        },
    )
    return {
        "user_id": user_id,
        "username": target.get("username"),
        "billing": {
            "credits": int(account.get("credits", 0)),
            "reserved": int(account.get("reserved", 0)),
            "available": available_credits(account),
            "suspended": bool(account.get("suspended")),
            "plan": account.get("plan") or "free_trial",
        },
    }


@api.patch("/admin/users/{user_id}/password")
def admin_reset_user_password(
    user_id: str, payload: ChangePasswordRequest, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    target = store.get_json("a", f"users/{user_id}.json")
    if not target or target.get("role") == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    target["password_hash"] = hash_password(payload.new_password)
    target["updated_at"] = now_iso()
    save_user(target)
    audit("admin.user_password_reset", admin["id"], {"user_id": user_id})
    return {"ok": True}


@api.patch("/admin/users/{user_id}/phone")
def admin_update_user_phone(
    user_id: str, payload: AdminUpdatePhoneRequest, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    target = store.get_json("a", f"users/{user_id}.json")
    if not target or target.get("role") == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    existing = get_user_by_phone(payload.phone)
    if existing and existing.get("id") != user_id:
        raise HTTPException(status_code=409, detail="该手机号已被其他账号使用")
    previous_phone = target.get("phone")
    target["phone"] = payload.phone
    target["updated_at"] = now_iso()
    save_user(target, previous_phone=previous_phone)
    audit("admin.user_phone_update", admin["id"], {"user_id": user_id, "phone": mask_phone(payload.phone)})
    return {"user": public_user(target)}


@api.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str, admin: Annotated[dict, Depends(admin_user)]) -> dict:
    target = store.get_json("a", f"users/{user_id}.json")
    if not target or target.get("role") == "admin":
        raise HTTPException(status_code=404, detail="普通用户不存在")
    delete_user_data(target)
    audit("admin.user_delete", admin["id"], {"user_id": user_id})
    return {"ok": True}


@api.get("/admin/generations")
def admin_generations(_: Annotated[dict, Depends(admin_user)]) -> list[dict]:
    records = store.list_json("a", "generations/")
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


@api.get("/admin/generations/{user_id}/{generation_id}/download/{file_type}")
def admin_download_generation(
    user_id: str,
    generation_id: str,
    file_type: str,
    _: Annotated[dict, Depends(admin_user)],
) -> Response:
    record = store.get_json("a", f"generations/{user_id}/{generation_id}.json")
    if not record:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    return generation_file_response(record, file_type)


@api.get("/admin/tasks")
def admin_tasks(_: Annotated[dict, Depends(admin_user)]) -> list[dict]:
    records = store.list_json("a", "tasks/")
    return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)


@api.get("/admin/operations")
def admin_operations(_: Annotated[dict, Depends(admin_user)]) -> dict:
    tasks = store.list_json("a", "tasks/")
    applications = store.list_json("a", "applications/")
    orders = store.list_json("a", "orders/")
    status_counts: dict[str, int] = {}
    for task in tasks:
        label = str(task.get("status") or "unknown")
        status_counts[label] = status_counts.get(label, 0) + 1
    application_counts: dict[str, int] = {}
    for item in applications:
        label = str(item.get("status") or "saved")
        application_counts[label] = application_counts.get(label, 0) + 1
    return {
        "task_statuses": status_counts,
        "application_statuses": application_counts,
        "orders": {
            "pending": len([item for item in orders if item.get("status") == "pending"]),
            "paid": len([item for item in orders if item.get("status") == "paid"]),
        },
        "latest_failures": [
            item
            for item in sorted(tasks, key=lambda value: value.get("updated_at", ""), reverse=True)
            if item.get("status") == "failed"
        ][:20],
    }


@api.get("/admin/orders")
def admin_orders(_: Annotated[dict, Depends(admin_user)]) -> list[dict]:
    orders = store.list_json("a", "orders/")
    enriched: list[dict] = []
    for order in orders:
        if not isinstance(order, dict):
            continue
        row = dict(order)
        user_id = str(row.get("user_id") or "")
        user = store.get_json("a", f"users/{user_id}.json") if user_id else None
        if isinstance(user, dict):
            row["username"] = user.get("username") or ""
            row["phone_masked"] = public_user(user).get("phone_masked") or user.get("phone_masked") or ""
        else:
            row.setdefault("username", "")
            row.setdefault("phone_masked", "")
        # Human-readable package name fallback for older records.
        if not row.get("product_name") and row.get("product_code") in PLAN_CATALOG:
            row["product_name"] = PLAN_CATALOG[row["product_code"]]["name"]
        enriched.append(row)
    return sorted(enriched, key=lambda item: item.get("created_at", ""), reverse=True)


@api.patch("/admin/orders/{user_id}/{order_id}")
def admin_update_order(
    user_id: str, order_id: str, payload: AdminOrderUpdateRequest, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    key = f"orders/{user_id}/{order_id}.json"
    order = store.get_json("a", key)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    original = order.get("status")
    order["status"] = payload.status
    order["updated_at"] = now_iso()
    if payload.status == "paid" and original != "paid":
        account = billing_account(user_id)
        account["credits"] = int(account.get("credits", 0)) + int(order.get("credits", 0))
        account["plan"] = order.get("product_code")
        account["updated_at"] = now_iso()
        store.put_json("a", account_key(user_id), account)
        record_ledger(user_id, "purchase", int(order.get("credits", 0)), order.get("product_name", "套餐"), order_id)
    if payload.status == "refunded" and original == "paid":
        record_ledger(user_id, "refund", 0, order.get("product_name", "套餐"), order_id)
    store.put_json("a", key, order)
    audit("admin.order_update", admin["id"], {"order_id": order_id, "status": payload.status})
    return order


@api.delete("/admin/generations/{user_id}/{generation_id}")
def admin_delete_generation(
    user_id: str, generation_id: str, admin: Annotated[dict, Depends(admin_user)]
) -> dict:
    record = store.get_json("a", f"generations/{user_id}/{generation_id}.json")
    if not record:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    remove_generation(record)
    audit("admin.generation_delete", admin["id"], {"generation_id": generation_id, "user_id": user_id})
    return {"ok": True}


@api.get("/admin/stats")
def admin_stats(_: Annotated[dict, Depends(admin_user)]) -> dict:
    users = store.list_json("a", "users/")
    resumes = store.list_json("a", "resumes/")
    generations = store.list_json("a", "generations/")
    models = store.get_json("a", "metrics/models.json") or {}
    return {
        "users": len([item for item in users if item.get("role") == "user"]),
        "resumes": len(resumes),
        "generations": len(generations),
        "models": models,
        "storage": store.bucket_usage(),
    }


app.include_router(api)


@app.get(f"{settings.app_base_path}/download/android", include_in_schema=False)
@app.get(f"{settings.app_base_path}/download/zhiday-resume-android.apk", include_in_schema=False)
@app.get(f"{settings.app_base_path}/download/android-full.apk", include_in_schema=False)
def download_android_app() -> FileResponse:
    """Serve the installer locally until a TOS/CDN custom domain is configured.

    TOS blocks APK distribution from its default endpoint. The APK remains mirrored to
    TOS by the publish script, while this stable route guarantees that Android users can
    install it without a custom CNAME.
    """
    apk_path = STATIC_DIR / "downloads" / "zhiday-resume-android.apk"
    if not apk_path.is_file():
        raise HTTPException(status_code=404, detail="Android 安装包正在更新，请稍后再试")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="zhiday-resume-android-full-1.8.21.apk",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff"},
    )


# Headless installer route used by the in-app updater. The path intentionally
# omits ".apk" so mobile carrier / corporate firewalls that inspect the URL and
# reset the connection don't kick in. Both GET and HEAD are accepted so any
# download manager probe (HEAD for size/etag) is answered correctly.
@app.api_route(
    f"{settings.app_base_path}/download/app-update",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@app.api_route(
    f"{settings.app_base_path}/download/pkg",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
@app.api_route(
    f"{settings.app_base_path}/download/full",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
def download_android_app_update() -> FileResponse:
    apk_path = STATIC_DIR / "downloads" / "zhiday-resume-android.apk"
    if not apk_path.is_file():
        raise HTTPException(status_code=404, detail="Android 安装包正在更新，请稍后再试")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="zhiday-resume-android-full-1.8.21.apk",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Accept-Ranges": "bytes",
        },
    )




@app.get("/privacy", include_in_schema=False)
@app.get(f"{settings.app_base_path}/privacy", include_in_schema=False)
def privacy_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "privacy.html")


@app.get("/terms", include_in_schema=False)
@app.get(f"{settings.app_base_path}/terms", include_in_schema=False)
def terms_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "terms.html")

app.mount(f"{settings.app_base_path}/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def root() -> Response:
    # 当 APP_BASE_PATH 为空（根域部署）时直接渲染首页，避免 `/` -> `/` 死循环重定向；
    # 当配置了子路径（如 /resume-ai）时再 307 跳转到该子路径。
    target = (settings.app_base_path or "").rstrip("/")
    if target:
        return RedirectResponse(f"{target}/")
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
    )


@app.get(f"{settings.app_base_path}/", include_in_schema=False)
def user_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
    )


@app.get(f"{settings.app_base_path}/admin", include_in_schema=False)
def admin_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get(f"{settings.app_base_path}/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type=mimetypes.types_map.get(".svg", "image/svg+xml"))


@app.get(f"{settings.app_base_path}/manifest.webmanifest", include_in_schema=False)
def webmanifest() -> FileResponse:
    manifest_path = STATIC_DIR / "manifest.webmanifest"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return Response(status_code=404)
