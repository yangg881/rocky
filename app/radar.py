"""Lightweight, user-scoped job recommendation store for 职达岗位雷达.

The first release intentionally uses SQLite: it keeps the public product usable on
the existing small server without adding a database process.  It is isolated from
the resume object store and can be moved to PostgreSQL without changing the API.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

HIDDEN_ACTIONS = {"applied", "not_interested"}
FEEDBACK_ACTIONS = {"viewed", "saved", "applied", "not_interested", "later"}
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,12}|[a-zA-Z][a-zA-Z0-9+#./-]{1,30}")
PUBLISHED_WINDOWS = {"all": 0, "1d": 1, "3d": 3, "7d": 7, "30d": 30}

# 同义词/近义词扩展：让近义技能与岗位也能命中（数据分析↔数据治理、java↔Java开发…）。
# 这是把"纯关键词计数"升级为"语义级覆盖"的核心，且完全本地、零依赖、可离线。
SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("数据分析", "数据治理", "数据建模", "商业分析", "BI", "经营分析", "数据运营"),
    ("后端", "服务端", "后台", "backend", "server", "后端开发"),
    ("前端", "web开发", "web前端", "frontend", "前端开发"),
    ("全栈", "全栈开发", "fullstack"),
    ("java", "java开发", "java工程师", "java后端"),
    ("python", "python开发", "python工程师", "python后端"),
    ("golang", "go", "go语言", "go开发"),
    ("人工智能", "AI", "大模型", "机器学习", "深度学习", "AIGC", "智能体", "算法"),
    ("产品经理", "产品", "product manager", "pm", "产品运营"),
    ("用户运营", "活动运营", "内容运营", "社群运营", "运营"),
    ("供应链", "物流", "采购", "计划", "跟单", "报关", "货代"),
    ("销售", "客户经理", "大客户", "BD", "商务拓展", "渠道", "销售经理"),
    ("测试", "qa", "质量保障", "测试工程师", "测试开发"),
    ("数据库", "mysql", "sql", "postgresql", "redis", "mongodb", "oracle"),
    ("云计算", "aws", "阿里云", "腾讯云", "devops", "k8s", "kubernetes", "云原生"),
    ("ui", "ux", "交互设计", "视觉设计", "设计"),
    ("财务", "会计", "审计", "税务", "出纳"),
    ("人力资源", "hr", "招聘", "薪酬", "绩效"),
    ("嵌入式", "单片机", "stm32", "rtos", "固件"),
    ("项目实施", "交付", "售前", "解决方案", "客户成功"),
)
_SYN_INDEX: dict[str, set[str]] = {}
for _grp in SYNONYM_GROUPS:
    for _w in _grp:
        _SYN_INDEX.setdefault(_w.lower(), set()).update(w.lower() for w in _grp)


def expand_synonyms(words: list[str]) -> set[str]:
    """Return input words plus their known synonyms (case-folded) for fuzzy matching."""
    result: set[str] = set()
    for w in words:
        w = (w or "").lower()
        if not w:
            continue
        result.add(w)
        result |= _SYN_INDEX.get(w, set())
    return result


def _gap_analysis(profile_expanded: set[str], requirements: list[str]) -> dict[str, Any]:
    """Split a JD's requirements into satisfied / missing against the (synonym-expanded) resume."""
    satisfied: list[str] = []
    missing: list[str] = []
    for req in requirements:
        req_l = (req or "").strip()
        if not req_l:
            continue
        req_terms = expand_synonyms(tokens(req_l))
        if req_terms & profile_expanded:
            satisfied.append(req_l)
        else:
            missing.append(req_l)
    total = len(satisfied) + len(missing)
    coverage = round(len(satisfied) / total, 2) if total else 0.0
    return {"satisfied": satisfied, "missing": missing, "coverage": coverage}


def _salary_min(salary_text: str) -> int:
    """Extract the lower monthly salary bound (CNY) for sorting; 0 when unparsable."""
    text = (salary_text or "").lower()
    match = re.search(r"(\d[\d,]*)\s*[kK]?", text)
    if not match:
        return 0
    try:
        val = int(match.group(1).replace(",", ""))
    except ValueError:
        return 0
    if "k" in text and val < 1000:
        val *= 1000
    return val
RADAR_MAX_PUBLISHED_DAYS = 30

NEW_JOB_WINDOW = timedelta(days=1)
GENERIC_JOB_TITLES = frozenset({"招聘", "岗位", "职位", "急聘", "诚聘", "不限"})
LOW_QUALITY_TEXT_MARKERS = ("扫码进群", "加微信了解", "招工群", "日结小时工")



@dataclass(frozen=True)
class RecommendationBatch:
    """The capped recommendation list plus the uncapped match count."""

    jobs: list[dict[str, Any]]
    matched_total: int
    is_limited: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_published_at(value: Any) -> datetime | None:
    """Best-effort parser for ISO and common Chinese job-site dates."""
    text = compact_text(value, 80)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except ValueError:
        pass
    match = re.search(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})", text)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def compact_text(value: Any, limit: int = 6000) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def normalize_city_label(value: Any) -> str:
    """Return one stable city/area label from the messy labels supplied by job sites."""
    text = compact_text(value, 120)
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    parts = [part for part in re.split(r"[,，、/|·—-]+", text) if part]
    # A publisher commonly returns “南宁·青秀区”. Keeping the final district
    # makes the selector useful, while normalising punctuation prevents duplicates.
    label = parts[-1] if parts else text
    return label.replace("自治区", "").replace("壮族", "").strip()


def source_text(value: Any, limit: int = 12000) -> str:
    """Preserve publisher paragraph structure for a job detail surface."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t \f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:limit]


def text_list(value: Any, limit: int = 24) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = re.split(r"[\n,，、;；/|]+", value)
    else:
        items = []
    result: list[str] = []
    for item in items:
        item = compact_text(item, 80)
        if item and item not in result:
            result.append(item)
    return result[:limit]


def tokens(value: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in TOKEN_RE.findall(compact_text(value, 12000).lower()):
        if len(item) < 2 or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


class JobRadarStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=8)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    salary TEXT NOT NULL DEFAULT '',
                    experience TEXT NOT NULL DEFAULT '',
                    education TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    responsibilities TEXT NOT NULL DEFAULT '[]',
                    requirements TEXT NOT NULL DEFAULT '[]',
                    benefits TEXT NOT NULL DEFAULT '[]',
                    source_sections TEXT NOT NULL DEFAULT '{}',
                    source_detail_status TEXT NOT NULL DEFAULT '',
                    source_detail_updated_at TEXT NOT NULL DEFAULT '',
                    link_check_failures INTEGER NOT NULL DEFAULT 0,
                    last_link_check_at TEXT NOT NULL DEFAULT '',
                    last_link_check_status TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    source_url TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    captured_at TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_active_updated
                    ON jobs(is_active, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
                CREATE INDEX IF NOT EXISTS idx_jobs_source_url ON jobs(source_url);
                CREATE TABLE IF NOT EXISTS user_job_feedback (
                    user_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    remind_until TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, job_id)
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_user_action
                    ON user_job_feedback(user_id, action);
                CREATE TABLE IF NOT EXISTS user_company_preferences (
                    user_id TEXT NOT NULL,
                    company TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, company)
                );
                CREATE TABLE IF NOT EXISTS recommendation_impressions (
                    user_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, job_id)
                );
                CREATE TABLE IF NOT EXISTS user_job_adaptations (
                    user_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    generation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, job_id)
                );
                CREATE INDEX IF NOT EXISTS idx_adaptations_user_created
                    ON user_job_adaptations(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS user_filter_presets (
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    filters_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, name)
                );
                CREATE TABLE IF NOT EXISTS user_filter_usage (
                    user_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    value TEXT NOT NULL DEFAULT '',
                    result_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_filter_usage_user_created
                    ON user_filter_usage(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS semantic_match_cache (                    profile_hash TEXT NOT NULL,                    job_id TEXT NOT NULL,                    relevance_score REAL NOT NULL DEFAULT 0,                    matched_strengths TEXT NOT NULL DEFAULT '[]' ,                    key_gaps TEXT NOT NULL DEFAULT '[]' ,                    recommendation TEXT NOT NULL DEFAULT '' ,                    created_at TEXT NOT NULL DEFAULT '' ,                    PRIMARY KEY (profile_hash, job_id)                );
                """
            )
            # Existing installations already have the original table. SQLite has
            # no ADD COLUMN IF NOT EXISTS, so keep this migration idempotent.
            existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            for name, definition in (
                ("benefits", "TEXT NOT NULL DEFAULT '[]'"),
                ("source_sections", "TEXT NOT NULL DEFAULT '{}'"),
                ("source_detail_status", "TEXT NOT NULL DEFAULT ''"),
                ("source_detail_updated_at", "TEXT NOT NULL DEFAULT ''"),
                ("link_check_failures", "INTEGER NOT NULL DEFAULT 0"),
                ("last_link_check_at", "TEXT NOT NULL DEFAULT ''"),
                ("last_link_check_status", "TEXT NOT NULL DEFAULT ''"),
            ):
                if name not in existing:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
        self.purge_outdated_published_jobs(max_deactivation_ratio=0.10)

    def import_jobs(self, records: list[dict[str, Any]], replace: bool = False) -> dict[str, int]:
        cleaned = [self.normalize_job(record) for record in records]
        cleaned = [record for record in cleaned if record]
        with self.connection() as conn:
            existing_by_url = {
                row["source_url"]: row["id"]
                for row in conn.execute("SELECT id, source_url FROM jobs WHERE source_url <> ''").fetchall()
            }
            for record in cleaned:
                if record["source_url"] and record["source_url"] in existing_by_url:
                    record["id"] = existing_by_url[record["source_url"]]
            if replace:
                conn.execute("UPDATE jobs SET is_active = 0, updated_at = ?", (now_iso(),))
            conn.executemany(
                """
                INSERT INTO jobs (
                    id, title, company, location, salary, experience, education, description,
                    responsibilities, requirements, benefits, source_sections, source_detail_status,
                    source_detail_updated_at, link_check_failures, last_link_check_at,
                    last_link_check_status, tags, source_url, published_at, captured_at,
                    is_active, updated_at
                ) VALUES (
                    :id, :title, :company, :location, :salary, :experience, :education, :description,
                    :responsibilities, :requirements, :benefits, :source_sections, :source_detail_status,
                    :source_detail_updated_at, :link_check_failures, :last_link_check_at,
                    :last_link_check_status, :tags, :source_url, :published_at, :captured_at,
                    :is_active, :updated_at
                ) ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, company=excluded.company, location=excluded.location,
                    salary=excluded.salary, experience=excluded.experience, education=excluded.education,
                    description=excluded.description, responsibilities=excluded.responsibilities,
                    requirements=excluded.requirements, benefits=excluded.benefits,
                    source_sections=excluded.source_sections,
                    source_detail_status=excluded.source_detail_status,
                    source_detail_updated_at=excluded.source_detail_updated_at,
                    link_check_failures=excluded.link_check_failures,
                    last_link_check_at=excluded.last_link_check_at,
                    last_link_check_status=excluded.last_link_check_status,
                    tags=excluded.tags, source_url=excluded.source_url,
                    published_at=excluded.published_at, captured_at=excluded.captured_at,
                    is_active=excluded.is_active, updated_at=excluded.updated_at
                """,
                cleaned,
            )
        return {"received": len(records), "imported": len(cleaned)}

    def expire_stale_jobs(self, days: int = 30, max_deactivation_ratio: float = 0.10) -> int:
        """Hide jobs that this radar has not observed recently.

        This mirrors the private system's expiry policy but operates only on the
        commercial catalog.  It never removes the historical record.
        """
        threshold = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        stale_ids: list[str] = []
        with self.connection() as conn:
            rows = conn.execute("SELECT id, captured_at FROM jobs WHERE is_active = 1").fetchall()
            for row in rows:
                value = str(row["captured_at"] or "").strip()
                try:
                    observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if observed.astimezone(timezone.utc) < threshold:
                    stale_ids.append(str(row["id"]))
            active_count = int(conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0])
            limit = max(100, int(active_count * max(0.0, max_deactivation_ratio)))
            if len(stale_ids) > limit:
                return 0
            if stale_ids:
                conn.executemany(
                    "UPDATE jobs SET is_active = 0, updated_at = ? WHERE id = ?",
                    [(now_iso(), job_id) for job_id in stale_ids],
                )
        return len(stale_ids)

    def purge_outdated_published_jobs(
        self, days: int = RADAR_MAX_PUBLISHED_DAYS, max_deactivation_ratio: float = 0.10
    ) -> int:
        """Hide records whose publish date is missing or outside the public window."""
        threshold = datetime.now(timezone.utc) - timedelta(days=max(1, days))
        stale_ids: list[str] = []
        with self.connection() as conn:
            rows = conn.execute("SELECT id, published_at FROM jobs WHERE is_active = 1").fetchall()
            for row in rows:
                published = parse_published_at(row["published_at"])
                if published is None or published < threshold:
                    stale_ids.append(str(row["id"]))
            active_count = int(conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0])
            limit = max(100, int(active_count * max(0.0, max_deactivation_ratio)))
            if len(stale_ids) > limit:
                return 0
            if stale_ids:
                conn.executemany(
                    "UPDATE jobs SET is_active = 0, updated_at = ? WHERE id = ?",
                    [(now_iso(), job_id) for job_id in stale_ids],
                )
        return len(stale_ids)

    def cleanup_inactive_jobs(
        self,
        max_published_days: int = RADAR_MAX_PUBLISHED_DAYS,
        max_stale_days: int = RADAR_MAX_PUBLISHED_DAYS,
        dry_run: bool = False,
        max_deactivation_ratio: float = 0.10,
        max_deactivations: int | None = None,
    ) -> dict[str, Any]:
        """Perform multi-tier dynamic cleanup of inactive / expired / unavailable jobs."""
        now = datetime.now(timezone.utc)
        pub_cutoff = now - timedelta(days=max(1, max_published_days))
        stale_cutoff = now - timedelta(days=max(1, max_stale_days))

        expired_pub_ids: set[str] = set()
        stale_captured_ids: set[str] = set()
        unavailable_ids: set[str] = set()

        with self.connection() as conn:
            rows = conn.execute(
                "SELECT id, published_at, captured_at, source_detail_status FROM jobs WHERE is_active = 1"
            ).fetchall()
            for row in rows:
                job_id = str(row["id"])
                detail_status = str(row["source_detail_status"] or "").strip().lower()

                # Rule 1: Unavailable status
                if detail_status == "unavailable":
                    unavailable_ids.add(job_id)
                    continue

                # Rule 2: Published date expired
                published = parse_published_at(row["published_at"])
                if published is None or published < pub_cutoff:
                    expired_pub_ids.add(job_id)
                    continue

                # Rule 3: Captured date stale
                captured_raw = str(row["captured_at"] or "").strip()
                if captured_raw:
                    try:
                        captured = datetime.fromisoformat(captured_raw.replace("Z", "+00:00"))
                        if captured.tzinfo is None:
                            captured = captured.replace(tzinfo=timezone.utc)
                        if captured.astimezone(timezone.utc) < stale_cutoff:
                            stale_captured_ids.add(job_id)
                    except ValueError:
                        pass

        all_to_deactivate = sorted(list(expired_pub_ids | stale_captured_ids | unavailable_ids))
        active_count = len(rows)
        ratio_limit = max(100, int(active_count * max(0.0, max_deactivation_ratio)))
        allowed_limit = min(ratio_limit, max_deactivations) if max_deactivations is not None else ratio_limit
        guard_blocked = bool(not dry_run and len(all_to_deactivate) > allowed_limit)

        if not dry_run and all_to_deactivate and not guard_blocked:
            with self.connection() as conn:
                conn.executemany(
                    "UPDATE jobs SET is_active = 0, updated_at = ? WHERE id = ?",
                    [(now_iso(), job_id) for job_id in all_to_deactivate],
                )

        return {
            "expired_published": len(expired_pub_ids),
            "stale_captured": len(stale_captured_ids),
            "unavailable": len(unavailable_ids),
            "total_deactivated": 0 if guard_blocked else len(all_to_deactivate),
            "dry_run": 1 if dry_run else 0,
            "guard_blocked": 1 if guard_blocked else 0,
            "proposed_deactivated": len(all_to_deactivate),
            "deactivation_limit": allowed_limit,
            "abort_reason": "batch exceeds safety limit" if guard_blocked else "",
        }

    @staticmethod
    def _is_quality_job(
        title: str,
        company: str,
        description: str,
        responsibilities: list[str],
        requirements: list[str],
    ) -> bool:
        """Reject malformed or promotional listings without excluding occupations."""
        normalized_title = re.sub(r"[\s【】\[\]（）()\-—_·]+", "", title).lower()
        if len(normalized_title) < 2 or normalized_title in GENERIC_JOB_TITLES:
            return False
        combined = " ".join([title, company, description, *responsibilities, *requirements]).lower()
        if any(marker in combined for marker in LOW_QUALITY_TEXT_MARKERS):
            return False
        # A compliant feed can legitimately offer only a title and URL.  Do
        # not convert missing optional metadata into a global job-category ban.
        return True

    @staticmethod
    def _is_new_job(published_at: str, now: datetime | None = None) -> bool:
        published = parse_published_at(published_at)
        if not published:
            return False
        current = now or datetime.now(timezone.utc)
        return published >= current - NEW_JOB_WINDOW

    def normalize_job(self, source: dict[str, Any]) -> dict[str, Any] | None:
        job_id = compact_text(source.get("id") or source.get("job_id") or source.get("external_id"), 120)
        title = compact_text(source.get("title") or source.get("job_title") or source.get("name"), 160)
        if not job_id or not title:
            return None
        published = parse_published_at(source.get("published_at") or source.get("publish_time"))
        if published is None or published < datetime.now(timezone.utc) - timedelta(days=RADAR_MAX_PUBLISHED_DAYS):
            return None
        responsibilities = text_list(source.get("responsibilities") or source.get("duties"))
        requirements = text_list(source.get("requirements") or source.get("qualification"))
        tags = text_list(source.get("tags") or source.get("keywords") or source.get("skills"))
        description = source_text(source.get("description") or source.get("content") or source.get("detail"))
        company = compact_text(source.get("company") or source.get("company_name"), 160)
        if not JobRadarStore._is_quality_job(title, company, description, responsibilities, requirements):
            return None
        benefits = text_list(source.get("benefits") or source.get("welfare"), limit=40)
        raw_sections = source.get("source_sections") if isinstance(source.get("source_sections"), dict) else {}
        source_sections = {
            compact_text(key, 80): source_text(value)
            for key, value in raw_sections.items()
            if compact_text(key, 80) and source_text(value)
        }
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "location": compact_text(source.get("location") or source.get("address") or source.get("city"), 160),
            "salary": compact_text(source.get("salary") or source.get("salary_text"), 100),
            "experience": compact_text(source.get("experience") or source.get("experience_requirement"), 100),
            "education": compact_text(source.get("education") or source.get("education_requirement"), 100),
            "description": description,
            "responsibilities": json.dumps(responsibilities, ensure_ascii=False),
            "requirements": json.dumps(requirements, ensure_ascii=False),
            "benefits": json.dumps(benefits, ensure_ascii=False),
            "source_sections": json.dumps(source_sections, ensure_ascii=False),
            "source_detail_status": compact_text(source.get("source_detail_status"), 30),
            "source_detail_updated_at": compact_text(source.get("source_detail_updated_at"), 80),
            "link_check_failures": int(source.get("link_check_failures") or 0),
            "last_link_check_at": compact_text(source.get("last_link_check_at"), 80),
            "last_link_check_status": compact_text(source.get("last_link_check_status"), 30),
            "tags": json.dumps(tags, ensure_ascii=False),
            "source_url": compact_text(source.get("source_url") or source.get("url") or source.get("job_url"), 1000),
            "published_at": published.isoformat(),
            "captured_at": compact_text(source.get("captured_at") or source.get("fetched_at"), 80),
            "is_active": 1 if source.get("is_active", source.get("active", True)) else 0,
            "updated_at": now_iso(),
        }

    def update_job_details(self, job_id: str, details: dict[str, Any]) -> dict[str, Any] | None:
        """Persist a lazy publisher-page enrichment without changing job identity."""
        current = self.get_job(job_id)
        if not current:
            return None
        merged = {**current, **details, "id": job_id, "source_url": current.get("source_url", "")}
        record = self.normalize_job(merged)
        if not record:
            return current
        if record.get("source_detail_status") == "unavailable":
            record["is_active"] = 0
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE jobs SET title=:title, company=:company, location=:location, salary=:salary,
                    experience=:experience, education=:education, description=:description,
                    responsibilities=:responsibilities, requirements=:requirements, benefits=:benefits,
                    source_sections=:source_sections, source_detail_status=:source_detail_status,
                    source_detail_updated_at=:source_detail_updated_at, tags=:tags,
                    published_at=:published_at, captured_at=:captured_at, is_active=:is_active, updated_at=:updated_at
                WHERE id=:id
                """,
                record,
            )
        return self.get_job(job_id)

    def job_count(self) -> int:
        with self.connection() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0])

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ? AND is_active = 1", (job_id,)).fetchone()
        return self.serialize_job(row) if row else None

    def mark_adapted(self, user_id: str, job_id: str, generation_id: str) -> None:
        """Persist a user-scoped 'already adapted' marker for radar cards."""
        if not user_id or not job_id or not generation_id:
            return
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_job_adaptations(user_id, job_id, generation_id, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, job_id) DO UPDATE SET
                    generation_id=excluded.generation_id, created_at=excluded.created_at
                """,
                (user_id, job_id, generation_id, now_iso()),
            )

    def sync_completed_adaptations(self, user_id: str, generations: list[dict[str, Any]]) -> None:
        """Backfill indicators for successful records created before marker rollout."""
        rows = [
            (user_id, str(item.get("radar_job_id")), str(item.get("id")), str(item.get("updated_at") or now_iso()))
            for item in generations
            if item.get("status") == "completed" and item.get("radar_job_id") and item.get("id")
        ]
        if not rows:
            return
        with self.connection() as conn:
            conn.executemany(
                """
                INSERT INTO user_job_adaptations(user_id, job_id, generation_id, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, job_id) DO UPDATE SET
                    generation_id=excluded.generation_id, created_at=excluded.created_at
                """,
                rows,
            )

    def set_feedback(self, user_id: str, job_id: str, action: str, remind_until: str = "") -> dict[str, Any]:
        if action not in FEEDBACK_ACTIONS:
            raise ValueError("不支持的岗位反馈")
        if not self.get_job(job_id):
            raise LookupError("岗位不存在或已失效")
        current = now_iso()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_job_feedback(user_id, job_id, action, remind_until, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, job_id) DO UPDATE SET
                    action=excluded.action, remind_until=excluded.remind_until, updated_at=excluded.updated_at
                """,
                (user_id, job_id, action, compact_text(remind_until, 40), current, current),
            )
        return {"job_id": job_id, "action": action, "remind_until": remind_until}

    def set_company_preference(self, user_id: str, company: str, blocked: bool) -> None:
        company = compact_text(company, 160)
        if not company:
            raise ValueError("该岗位缺少公司名称，暂时无法设置公司偏好")
        with self.connection() as conn:
            if not blocked:
                conn.execute(
                    "DELETE FROM user_company_preferences WHERE user_id = ? AND company = ?",
                    (user_id, company),
                )
                return
            current = now_iso()
            conn.execute(
                """
                INSERT INTO user_company_preferences(user_id, company, action, created_at, updated_at)
                VALUES (?, ?, 'blocked', ?, ?)
                ON CONFLICT(user_id, company) DO UPDATE SET action='blocked', updated_at=excluded.updated_at
                """,
                (user_id, company, current, current),
            )

    async def recommend(
        self,
        user_id: str,
        profile_text: str,
        max_results: int = 10000,
        query: str = "",
        city: str = "",
        published_within: str = "30d",
        saved_only: bool = False,
        *,
        experience: str = "",
        education: str = "",
        salary_min: int = 0,
        sort_by: str = "match",
        topic: str = "",
        source: str = "",
        only_new: bool = False,
    ) -> RecommendationBatch:
        profile_tokens = tokens(profile_text)
        # 同义词扩展后的画像词集，用于语义级覆盖与差距分析。
        profile_expanded = expand_synonyms(profile_tokens)
        query = compact_text(query, 120).lower()
        city = compact_text(city, 120).lower()
        experience = compact_text(experience, 40).lower()
        education = compact_text(education, 40).lower()
        source = compact_text(source, 40).lower()
        try:
            salary_min = int(salary_min or 0)
        except (TypeError, ValueError):
            salary_min = 0
        sort_by = sort_by if sort_by in {"match", "latest", "salary"} else "match"
        published_within = published_within if published_within in PUBLISHED_WINDOWS else "30d"
        requested_days = PUBLISHED_WINDOWS[published_within] or RADAR_MAX_PUBLISHED_DAYS
        cutoff = datetime.now(timezone.utc) - timedelta(days=min(requested_days, RADAR_MAX_PUBLISHED_DAYS))
        # Push cheap filters into SQL to avoid scoring 10k rows on every page flip.
        sql = """
            SELECT j.*, f.action AS feedback_action, f.remind_until,
                   a.generation_id AS adapted_generation_id, a.created_at AS adapted_at
            FROM jobs j
            LEFT JOIN user_job_feedback f ON f.job_id = j.id AND f.user_id = ?
            LEFT JOIN user_job_adaptations a ON a.job_id = j.id AND a.user_id = ?
            LEFT JOIN user_company_preferences cp
                ON cp.company = j.company AND cp.user_id = ? AND cp.action = 'blocked'
            WHERE j.is_active = 1 AND cp.company IS NULL
        """
        params: list[Any] = [user_id, user_id, user_id]
        if city:
            sql += " AND lower(j.location) LIKE ?"
            params.append(f"%{city}%")
        if query:
            sql += " AND (lower(j.title) LIKE ? OR lower(j.company) LIKE ? OR lower(j.description) LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like])
        if saved_only:
            sql += " AND f.action = 'saved'"
        sql += " ORDER BY COALESCE(NULLIF(j.published_at, ''), j.updated_at) DESC LIMIT 15000"
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        current = now_iso()
        items: list[dict[str, Any]] = []
        for row in rows:
            action = row["feedback_action"] or ""
            if action in HIDDEN_ACTIONS:
                continue
            if saved_only and action != "saved":
                continue
            if action == "later" and row["remind_until"] and row["remind_until"] > current:
                continue
            job = self.serialize_job(row)
            if not self._published_after(job["published_at"], cutoff):
                continue
            # 岗位来源（平台）筛选
            if source:
                s_url = (job.get("source_url") or "").lower()
                if source in ("gxrc", "广西人才网"):
                    if "gxrc.com" not in s_url:
                        continue
                elif source in ("51job", "前程无忧", "前程无忧(51job)"):
                    if "51job.com" not in s_url:
                        continue
                elif source in ("liepin", "猎聘", "猎聘网"):
                    if "liepin.com" not in s_url:
                        continue
                elif source in ("zhipin", "boss", "boss直聘"):
                    if "zhipin.com" not in s_url:
                        continue
                elif source in ("zhaopin", "智联", "智联招聘"):
                    if "zhaopin.com" not in s_url and "zhaopin.meituan" not in s_url:
                        continue
            haystack = " ".join(
                [job["title"], job["company"], job["description"], *job["tags"], *job["requirements"]]
            ).lower()
            if query and query not in haystack and query not in job["title"].lower() and query not in job["company"].lower():
                # SQL used LIKE; keep a light second pass for tags/requirements only when needed.
                if query not in " ".join(job["tags"]).lower() and query not in " ".join(job["requirements"]).lower():
                    continue
            # 职能方向筛选：复用发现阶段的 TOPIC_GROUPS，命中任一标签才保留。
            if topic:
                try:
                    from app.radar_sources import TOPIC_GROUPS

                    labels = dict(TOPIC_GROUPS).get(topic, ())
                    if labels and not any(label in haystack for label in labels):
                        continue
                except Exception:
                    pass
            # 语义级匹配：把岗位文本也做同义词扩展，再用扩展后的画像词集求交集。
            job_terms = expand_synonyms(tokens(haystack))
            matched_terms = sorted(profile_expanded & job_terms)
            title_match = sorted(profile_expanded & expand_synonyms(tokens(job["title"])))
            # 任职要求覆盖度 + 差距分析（这是“忠于事实”产品的核心价值：告诉用户缺什么）。
            gap = _gap_analysis(profile_expanded, job["requirements"])
            coverage = gap["coverage"]
            # 加权打分：任职要求覆盖(0-50) + 标题契合(0-15) + 通用关键词(0-25) + 基础(5)。
            raw = min(50, coverage * 50) + min(15, len(title_match) * 7) + min(25, len(matched_terms) * 4)
            score = int(min(99, 5 + raw)) if profile_tokens else 50
            if action == "saved":
                score = min(99, score + 8)
            reasons = []
            if title_match:
                reasons.append(f"岗位名称与您的 {title_match[0]} 方向相符")
            if matched_terms:
                reasons.append(f"匹配到 {', '.join(matched_terms[:3])} 等经历关键词")
            if coverage >= 0.6:
                reasons.append(f"任职要求覆盖度 {int(coverage * 100)}%")
            elif gap["missing"]:
                reasons.append(f"可补强：{', '.join(gap['missing'][:2])}")
            if job["location"]:
                reasons.append(f"工作地点：{job['location']}")
            job["match_score"] = score
            job["match_reason"] = "；".join(reasons) or "基于您的简历和职业画像进行初步匹配"
            job["gap_analysis"] = gap
            job["coverage"] = coverage
            job["feedback_action"] = action
            # 结构化硬筛选（经验/学历/薪资），命中才进入结果集；“不限/经验”类宽松门槛放行。
            exp = (job["experience"] or "").lower()
            if experience and experience not in exp and "不限" not in exp and "经验" not in exp:
                continue
            edu = (job["education"] or "").lower()
            if education and education not in edu and "不限" not in edu:
                continue
            if salary_min:
                job_pay = _salary_min(job["salary"])
                if job_pay and job_pay < salary_min:
                    continue
            job["is_new"] = self._is_new_job(job["published_at"])
            if only_new and not job["is_new"]:
                continue
            items.append(job)
        if sort_by == "latest":
            items.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        elif sort_by == "salary":
            items.sort(key=lambda item: _salary_min(item.get("salary", "")), reverse=True)
        else:
            items.sort(key=lambda item: (-item["match_score"], item.get("published_at", "")), reverse=False)
        capped_limit = max(1, max_results)
        matched_total = len(items)
        selected = items[:capped_limit]
        # Only log impressions for the top page-size slice to cut write amplification.
        impression_slice = selected[:20]
        if impression_slice:
            with self.connection() as conn:
                conn.executemany(
                    """
                    INSERT INTO recommendation_impressions(user_id, job_id, score, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, job_id) DO UPDATE SET
                        score=excluded.score, reason=excluded.reason, created_at=excluded.created_at
                    """,
                    [
                        (user_id, job["id"], job["match_score"], job["match_reason"][:240], current)
                        for job in impression_slice
                    ],
                )
        return RecommendationBatch(
            jobs=selected,
            matched_total=matched_total,
            is_limited=matched_total > len(selected),
        )

    def _semantic_cache_get(self, profile_hash: str, job_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT relevance_score, matched_strengths, key_gaps, recommendation "
                "FROM semantic_match_cache WHERE profile_hash=? AND job_id=?",
                (profile_hash, job_id)
            ).fetchone()
        if not row:
            return None
        return {
            "relevance_score": row["relevance_score"],
            "matched_strengths": json.loads(row["matched_strengths"]),
            "key_gaps": json.loads(row["key_gaps"]),
            "recommendation": row["recommendation"],
        }

    def _semantic_cache_set(self, profile_hash: str, job_id: str, data: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO semantic_match_cache"
                "(profile_hash, job_id, relevance_score, matched_strengths, key_gaps, recommendation, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (profile_hash, job_id, data["relevance_score"],
                 json.dumps(data["matched_strengths"]),
                 json.dumps(data["key_gaps"]),
                 data["recommendation"], now_iso()),
            )

    async def enrich_semantic_scores(self, ai_client, jobs, profile_text):
        if not profile_text or not jobs or ai_client is None:
            return jobs
        import hashlib as _hl
        profile_hash = _hl.sha256(profile_text.encode()).hexdigest()[:16]
        top_n = min(len(jobs), 15)
        for job in jobs[:top_n]:
            cached = self._semantic_cache_get(profile_hash, job["id"])
            if cached is not None:
                job["semantic_match"] = cached
                job["match_score"] = max(job.get("match_score", 50), min(99, int(cached["relevance_score"])))
                continue
            try:
                sem = await self._do_semantic_match(ai_client, profile_text, job)
                if sem:
                    self._semantic_cache_set(profile_hash, job["id"], sem)
                    job["semantic_match"] = sem
                    job["match_score"] = max(job.get("match_score", 50), min(99, int(sem["relevance_score"])))
            except Exception:
                pass
        return jobs

    async def _do_semantic_match(self, ai_client, profile_text, job):
        description = (job.get("description") or "")[:800]
        requirements = ", ".join(job.get("requirements", [])[:8])
        prompt = f"""你是一位专业的职业匹配顾问。请评估候选人与以下岗位的匹配度。

候选人职业画像：
{profile_text[:600]}

岗位信息：
- 职位：{job.get("title","")}
- 公司：{job.get("company","")}
- 地点：{job.get("location","")}
- 经验要求：{job.get("experience","")}
- 学历要求：{job.get("education","")}
- 薪资：{job.get("salary","")}
- 任职要求：{requirements}
- 职位描述：{description}

请严格按 JSON 格式返回（不要其他文字）：
{{"relevance_score": <0-100 整数>, "matched_strengths": [...], "key_gaps": [...], "recommendation": "..."}}"""
        try:
            result = await ai_client._chat_json(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": "你是职业匹配分析专家，用中文回答，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
            )
            if isinstance(result, dict) and "relevance_score" in result:
                return {
                    "relevance_score": max(0, min(100, int(float(result.get("relevance_score", 50))))),
                    "matched_strengths": result.get("matched_strengths", []) or [],
                    "key_gaps": result.get("key_gaps", []) or [],
                    "recommendation": str(result.get("recommendation", "")) or "",
                }
        except Exception:
            pass
        return None

    def available_cities(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT location, published_at FROM jobs WHERE is_active = 1 AND location <> '' ORDER BY location LIMIT 10000"
            ).fetchall()
        cutoff = datetime.now(timezone.utc) - timedelta(days=RADAR_MAX_PUBLISHED_DAYS)
        labels: dict[str, str] = {}
        for row in rows:
            if not self._published_after(row["published_at"], cutoff):
                continue
            label = normalize_city_label(row["location"])
            if label:
                labels.setdefault(label.casefold(), label)
        return sorted(labels.values(), key=lambda value: value.casefold())[:200]

    def facets(self) -> dict[str, Any]:
        """Return the distinct, data-driven filter dimensions for the radar UI.

        Experience / education / salary ranges are derived from live jobs; the
        topic clusters reuse the discovery taxonomy so the collector and the
        filter surface stay consistent.
        """
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT experience, education, salary FROM jobs WHERE is_active = 1"
            ).fetchall()
        experiences: dict[str, str] = {}
        educations: dict[str, str] = {}
        salaries: list[int] = []
        for row in rows:
            exp = compact_text(row["experience"], 40)
            if exp:
                experiences.setdefault(exp.casefold(), exp)
            edu = compact_text(row["education"], 40)
            if edu:
                educations.setdefault(edu.casefold(), edu)
            pay = _salary_min(row["salary"])
            if pay:
                salaries.append(pay)
        try:
            from app.radar_sources import TOPIC_GROUPS  # lazy import avoids a cycle

            topic_names = {
                "ai": "人工智能 / AI",
                "supply-chain": "供应链 / 物流",
                "technology": "技术 / IT / 软件",
                "manufacturing": "智能制造 / 自动化",
                "commerce": "跨境 / 电商 / 外贸",
                "service": "服务 / 零售 / 门店",
                "sales-operations": "销售 / 运营 / 市场",
            }
            topics = [
                {
                    "key": key,
                    "value": key,
                    "name": topic_names.get(key, labels[0] if labels else key),
                    "label": topic_names.get(key, labels[0] if labels else key),
                    "labels": list(labels),
                }
                for key, labels in TOPIC_GROUPS
            ]
        except Exception:
            topics = []
        sources = [
            {"key": "gxrc", "name": "广西人才网"},
            {"key": "51job", "name": "前程无忧(51job)"},
            {"key": "liepin", "name": "猎聘网"},
            {"key": "zhipin", "name": "BOSS直聘"},
            {"key": "zhaopin", "name": "智联招聘"},
        ]
        return {
            "experiences": sorted(experiences.values()),
            "educations": sorted(educations.values()),
            "salary_min": min(salaries) if salaries else 0,
            "salary_max": max(salaries) if salaries else 0,
            "topics": topics,
            "sources": sources,
        }

    # ---- 筛选维度使用埋点 + 预设（P1.3）----
    def log_filter_usage(self, user_id: str, dimension: str, value: str, result_count: int) -> None:
        """Lightweight analytics: which filter dimensions users actually touch."""
        if not dimension:
            return
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO user_filter_usage(user_id, dimension, value, result_count, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, compact_text(dimension, 40), compact_text(value, 120), int(result_count or 0), now_iso()),
            )

    def filter_usage_summary(self, user_id: str) -> dict[str, int]:
        """Aggregate how often each dimension was used, to guide future iteration."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT dimension, COUNT(*) count FROM user_filter_usage WHERE user_id = ? GROUP BY dimension",
                (user_id,),
            ).fetchall()
        return {row["dimension"]: int(row["count"]) for row in rows}

    def save_filter_preset(self, user_id: str, name: str, filters: dict[str, Any]) -> dict[str, Any]:
        name = compact_text(name, 40)
        if not name:
            raise ValueError("预设名称不能为空")
        record = {"name": name, "filters_json": json.dumps(filters, ensure_ascii=False), "created_at": now_iso()}
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_filter_presets(user_id, name, filters_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, name) DO UPDATE SET filters_json=excluded.filters_json, created_at=excluded.created_at
                """,
                (user_id, name, record["filters_json"], record["created_at"]),
            )
        return record

    def list_filter_presets(self, user_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT name, filters_json, created_at FROM user_filter_presets WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            {"name": row["name"], "filters": json.loads(row["filters_json"] or "{}"), "created_at": row["created_at"]}
            for row in rows
        ]

    def delete_filter_preset(self, user_id: str, name: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM user_filter_presets WHERE user_id = ? AND name = ?",
                (user_id, compact_text(name, 40)),
            )

    @staticmethod
    def _published_after(value: str, cutoff: datetime) -> bool:
        published = parse_published_at(value)
        return bool(published and published >= cutoff)

    def summary(self, user_id: str) -> dict[str, int]:
        with self.connection() as conn:
            jobs = conn.execute("SELECT published_at FROM jobs WHERE is_active = 1").fetchall()
            rows = conn.execute(
                "SELECT action, COUNT(*) count FROM user_job_feedback WHERE user_id = ? GROUP BY action", (user_id,)
            ).fetchall()
        cutoff = datetime.now(timezone.utc) - timedelta(days=RADAR_MAX_PUBLISHED_DAYS)
        total = sum(1 for row in jobs if self._published_after(row["published_at"], cutoff))
        new_jobs = sum(1 for row in jobs if self._is_new_job(row["published_at"]))
        counts = {row["action"]: int(row["count"]) for row in rows}
        return {
            "available_jobs": total,
            "new_jobs": new_jobs,
            "saved": counts.get("saved", 0),
            "applied": counts.get("applied", 0),
            "not_interested": counts.get("not_interested", 0),
        }

    def delete_user_data(self, user_id: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM user_job_feedback WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_company_preferences WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM recommendation_impressions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_job_adaptations WHERE user_id = ?", (user_id,))

    @staticmethod
    def serialize_job(row: sqlite3.Row) -> dict[str, Any]:
        def parse_list(value: Any) -> list[str]:
            try:
                return list(json.loads(value or "[]"))
            except (TypeError, ValueError):
                return []

        def parse_object(value: Any) -> dict[str, str]:
            try:
                parsed = json.loads(value or "{}")
                return parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError):
                return {}

        return {
            "id": row["id"], "title": row["title"], "company": row["company"],
            "location": row["location"], "salary": row["salary"], "experience": row["experience"],
            "education": row["education"], "description": row["description"],
            "responsibilities": parse_list(row["responsibilities"]), "requirements": parse_list(row["requirements"]),
            "benefits": parse_list(row["benefits"]), "source_sections": parse_object(row["source_sections"]),
            "source_detail_status": row["source_detail_status"],
            "source_detail_updated_at": row["source_detail_updated_at"],
            "link_check_failures": int(row["link_check_failures"] or 0) if "link_check_failures" in row.keys() else 0,
            "last_link_check_at": row["last_link_check_at"] if "last_link_check_at" in row.keys() else "",
            "last_link_check_status": row["last_link_check_status"] if "last_link_check_status" in row.keys() else "",
            "tags": parse_list(row["tags"]), "source_url": row["source_url"],
            "published_at": row["published_at"], "captured_at": row["captured_at"],
            "adapted": bool(row["adapted_generation_id"]) if "adapted_generation_id" in row.keys() else False,
            "adapted_at": str(row["adapted_at"] or "") if "adapted_at" in row.keys() else "",
            "adapted_generation_id": str(row["adapted_generation_id"] or "") if "adapted_generation_id" in row.keys() else "",
        }
