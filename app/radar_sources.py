"""Public, unauthenticated Guangxi Talent Network collection for 职达岗位雷达.

This is intentionally separate from the private application system: it only reads
the public job-search endpoint, stores no site account, and never attempts a job
application.  The collection pattern is adapted from the validated private source
pipeline: topic discovery -> normalized records -> URL dedupe -> stale-job expiry.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import random
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, ProxyHandler, build_opener, urlopen

from app.radar import compact_text

GXRC_LIST_URL = "https://s.gxrc.com/sJob?keyword="
GXRC_SEARCH_URL = "https://s.gxrc.com/api/Position/Search"
DISTRICT_ID = 2
NANNING_HINTS = (
    "南宁", "广西南宁", "邕宁", "邕宁区", "青秀", "青秀区", "良庆", "良庆区",
    "兴宁", "兴宁区", "江南", "江南区", "西乡塘", "西乡塘区", "五象", "武鸣",
    "武鸣区", "横州", "横州市", "宾阳", "宾阳县", "隆安", "隆安县", "上林",
    "上林县", "马山", "马山县",
)

# Copied from the proven GXRC discovery sources, but consumed by the commercial
# catalog rather than the private user's queue or personal filtering rules.
TOPIC_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ai", ("人工智能", "AI", "大模型", "AIGC", "生成式AI", "智能体", "机器学习", "数据智能", "智能算法", "AI产品")),
    ("supply-chain", ("供应链", "物流", "采购", "计划", "跟单", "报关", "货代", "运输")),
    ("technology", ("技术支持", "IT", "数据", "产品", "设计", "项目", "解决方案", "售前", "实施", "客户成功")),
    ("manufacturing", ("智能制造", "自动化", "机器人", "数据", "产品", "项目", "信息技术", "软件", "SaaS", "数字化")),
    ("commerce", ("电商", "跨境", "外贸", "进出口", "英语", "国际", "海外", "亚马逊", "Shopee", "TikTok")),
    ("service", ("酒店", "餐饮", "门店", "店长", "零售", "商超", "前厅", "客房", "咖啡", "食品")),
    ("sales-operations", ("销售", "客户经理", "业务", "渠道", "市场", "运营", "招商主管", "BD", "商务", "大客户")),
)


class GxrcCollectionError(RuntimeError):
    pass


class GxrcPublicCollector:
    def __init__(self, timeout_seconds: int = 25):
        self.timeout_seconds = timeout_seconds
        proxy = os.environ.get("RADAR_HTTP_PROXY", "").strip()
        if proxy:
            self._opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
        else:
            self._opener = build_opener()

    def collect(
        self, group_index: int | None = None, pages: int = 20, page_size: int = 50
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Collect the public Guangxi-wide feed without category or city restrictions."""
        pages = max(1, min(int(pages), 20))
        page_size = max(1, min(int(page_size), 50))
        collected: list[dict[str, Any]] = []
        failures: list[str] = []
        successful_pages = 0
        for page in range(1, pages + 1):
            try:
                collected.extend(self._fetch_page(page, page_size, ""))
                successful_pages += 1
            except GxrcCollectionError as exc:
                # Keep collecting other pages, but never present an upstream
                # block as a legitimate empty result.
                failures.append(f"page {page}: {exc}")
            # Slow down to avoid obvious bot-like blasting.
            if page < pages:
                time.sleep(random.uniform(1.5, 4.0))
        deduped = self._dedupe(collected)
        return deduped, {
            "source": "gxrc_public_search",
            "groups": ["all-categories"],
            "requests_planned": pages,
            "successful_pages": successful_pages,
            "discovered": len(deduped),
            "failures": failures[:12],
        }

    def _fetch_page(self, page: int, page_size: int, keyword: str) -> list[dict[str, Any]]:
        body = {
            "businessDistinct": [], "workPlace": [], "subwayQueryArr": [], "online": False,
            "emergency": False, "salary": "", "workProperty": [], "workAge": "",
            "enterpriseProperty": [], "enterpriseEmployeeNumber": [], "requirementOfEducationDegree": [],
            "welfare": [], "firstPublishDate": "", "page": page, "pageSize": page_size,
            "orderBy": "0", "positionCaree": [], "positionIndustry": [], "keyword": keyword,
            "schType": 2 if keyword else 1,
        }
        query = urlencode({"districtId": DISTRICT_ID, "from": 0})
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{GXRC_SEARCH_URL}?{query}", data=payload, method="POST",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Content-Type": "application/json-patch+json",
                "Origin": "https://s.gxrc.com",
                "Referer": GXRC_LIST_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            raise GxrcCollectionError(f"HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise GxrcCollectionError("网络请求失败") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GxrcCollectionError("返回内容无法解析") from exc
        if not isinstance(payload, dict):
            raise GxrcCollectionError("upstream returned an invalid response")
        data = payload.get("data")
        if not isinstance(data, dict):
            message = compact_text(payload.get("message"), 160) or "empty response"
            raise GxrcCollectionError(f"upstream rejected request: {message}")
        items = data.get("items") or []
        if not isinstance(items, list):
            raise GxrcCollectionError("upstream returned an invalid job list")
        return [record for item in items if (record := self._normalize_item(item))]

    def _normalize_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        title = self._clean(item.get("positionName"))
        company = self._clean(item.get("enterpriseName"))
        location = self._clean(item.get("workPlace"))
        if not title or not company:
            return None
        external_id = self._clean(item.get("positionGuid") or item.get("positionID"))
        source_url = f"https://www.gxrc.com/jobDetail/{external_id}" if external_id else ""
        if not source_url:
            return None
        description = self._clean(item.get("description"))
        category = self._clean(item.get("positionCareerName") or item.get("positionIndustryName"))
        published_at = self._clean(item.get("publishTime"))
        observed_at = datetime.now(timezone.utc).isoformat()
        return {
            "id": f"gxrc-{external_id}" if external_id else self._fallback_id(source_url),
            "title": title,
            "company": company,
            "location": location or "广西",
            "salary": self._clean(item.get("payPackage")),
            "experience": self._clean(item.get("workAgeName") or item.get("workAge")),
            "education": self._clean(item.get("educationName") or item.get("requirementOfEducationDegreeName")),
            "description": description,
            "requirements": self._clean(item.get("requirement") or item.get("positionRequirement")),
            "tags": [value for value in (category, self._clean(item.get("enterpriseIndustryName")), location) if value],
            "source_url": source_url,
            "published_at": published_at,
            "captured_at": observed_at,
            "is_active": True,
        }

    def enrich_job_detail(self, job: dict[str, Any]) -> dict[str, Any]:
        """Read the public mobile detail page and retain its publisher wording.

        The search API deliberately returns a short teaser.  The mobile detail
        page server-renders a full public position object, which lets the app
        show the same responsibilities, benefits and constraints before the
        user decides whether to open the original page and apply.
        """
        source_url = str(job.get("source_url") or "").strip()
        parsed = urlparse(source_url)
        if not source_url or not parsed.netloc.endswith("gxrc.com"):
            return {"source_detail_status": "unsupported"}
        mobile_url = source_url.replace("://www.gxrc.com/", "://m.gxrc.com/")
        request = Request(
            mobile_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                page = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise GxrcCollectionError("岗位详情暂时无法读取") from exc

        if "NoPosition" in final_url or "NoPosition" in page or "已过期" in page or "不存在" in page or "已下架" in page:
            return {"source_detail_status": "unavailable"}

        description = self._js_string(page, "positionDescription")
        if not description:
            return {"source_detail_status": "unavailable"}
        welfare = self._js_string_list(page, "positionWelfareNames")
        requirements = self._dedupe_texts([
            self._labelled("学历要求", self._js_string(page, "degreeName")),
            self._labelled("经验要求", self._js_string(page, "workAge")),
            self._labelled("职称要求", self._js_string(page, "requirementOfWorkTitleName")),
            self._labelled("年龄要求", self._js_string(page, "ageRangeMessage")),
            self._labelled("语言要求", self._js_string(page, "languageName")),
            self._labelled("专业要求", self._js_string(page, "educationSpecialtyName")),
        ])
        company_info = self._dedupe_texts([
            self._js_string(page, "enterpriseProperty"),
            self._js_string(page, "enterpriseEmployeeNumber"),
            self._js_string(page, "enterpriseIndustry"),
        ])
        other = self._dedupe_texts([
            self._labelled("工作性质", self._js_string(page, "workProperty")),
            self._labelled("招聘人数", self._js_string(page, "positionAmount")),
            self._labelled("工作地址", self._js_string(page, "workAddress")),
            self._labelled("更新时间", self._js_string(page, "updateTime")),
        ])
        sections: dict[str, str] = {"岗位职责与详情": description}
        if requirements:
            sections["任职要求"] = "\n".join(requirements)
        if welfare:
            sections["职位福利"] = "\n".join(welfare)
        if company_info:
            sections["公司信息"] = " · ".join(company_info)
        if other:
            sections["其它要求"] = "\n".join(other)
        return {
            "title": self._js_string(page, "positionName") or job.get("title", ""),
            "company": self._js_string(page, "enterpriseName") or job.get("company", ""),
            "location": self._js_string(page, "workPlace") or job.get("location", ""),
            "salary": self._js_string(page, "payPackage") or job.get("salary", ""),
            "experience": self._js_string(page, "workAge") or job.get("experience", ""),
            "education": self._js_string(page, "degreeName") or job.get("education", ""),
            "description": description,
            "responsibilities": self._paragraphs(description),
            "requirements": requirements,
            "benefits": welfare,
            "source_sections": sections,
            "source_detail_status": "complete",
            "source_detail_updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _js_string(page: str, field: str) -> str:
        match = re.search(rf'{re.escape(field)}:"((?:\\.|[^"\\])*)"', page)
        if not match:
            return ""
        try:
            return json.loads(f'"{match.group(1)}"').strip()
        except json.JSONDecodeError:
            return html.unescape(match.group(1)).strip()

    @staticmethod
    def _js_string_list(page: str, field: str) -> list[str]:
        match = re.search(rf'{re.escape(field)}:(\[(?:[^\[\]]|\\.)*\])', page)
        if not match:
            return []
        try:
            values = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        return [str(value).strip() for value in values if str(value).strip()]

    @staticmethod
    def _labelled(label: str, value: str) -> str:
        return f"{label}：{value}" if value else ""

    @staticmethod
    def _paragraphs(value: str) -> list[str]:
        return [line.strip() for line in re.split(r"\n+", value) if line.strip()]

    @staticmethod
    def _dedupe_texts(values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            value = str(value or "").strip()
            if value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _clean(value: Any) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return compact_text(text, 6000)

    @staticmethod
    def _is_nanning(value: str) -> bool:
        return any(hint in value for hint in NANNING_HINTS)

    @staticmethod
    def _fallback_id(source_url: str) -> str:
        return "gxrc-" + hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for record in records:
            key = str(record.get("source_url") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(record)
        return result

# ---------------------------------------------------------------------------
# P1.4 多数据源：可插拔采集适配器
# 除广西人才网外，运营可将任意“合规、已授权”的岗位数据以 JSON 形式提供
# （本地文件或 HTTP/HTTPS 地址），由 JsonFeedCollector 统一接入同一套目录。
# 新增数据源只需实现一个 collect(pages=...) -> (jobs, meta) 的适配器即可。
# ---------------------------------------------------------------------------


class JsonFeedCollector:
    """Collect jobs from a compliant JSON feed (file path or URL).

    Expected shape (loose): a top-level list, or {"jobs": [...]} where each item
    carries at least title/company and optionally the same fields GXRC uses.
    """

    def __init__(self, source: str, *, timeout_seconds: int = 25, label: str = ""):
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.label = label or source

    def _fetch_text(self) -> str:
        if self.source.startswith(("http://", "https://")):
            req = Request(self.source, headers={"User-Agent": "zhida-job-radar/1.0"}, method="GET")
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                return resp.read().decode("utf-8", "replace")
        return Path(self.source).read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _coerce(item: dict[str, Any]) -> dict[str, Any] | None:
        title = compact_text(item.get("title") or item.get("job_title") or item.get("name"), 160)
        if not title:
            return None
        return {
            "id": compact_text(item.get("id") or item.get("external_id") or item.get("job_id") or item.get("source_url") or title, 120),
            "title": title,
            "company": compact_text(item.get("company") or item.get("company_name"), 160),
            "location": compact_text(item.get("location") or item.get("city") or item.get("address"), 160),
            "salary": compact_text(item.get("salary") or item.get("salary_text"), 100),
            "experience": compact_text(item.get("experience") or item.get("experience_requirement"), 100),
            "education": compact_text(item.get("education") or item.get("education_requirement"), 100),
            "description": compact_text(item.get("description") or item.get("content"), 8000),
            "responsibilities": item.get("responsibilities") or item.get("duties") or [],
            "requirements": item.get("requirements") or item.get("qualification") or [],
            "benefits": item.get("benefits") or item.get("welfare") or [],
            "tags": item.get("tags") or item.get("keywords") or item.get("skills") or [],
            "source_url": compact_text(item.get("source_url") or item.get("url") or item.get("job_url"), 1000),
            "published_at": compact_text(item.get("published_at") or item.get("publish_time") or item.get("captured_at"), 80),
            "captured_at": compact_text(item.get("captured_at") or item.get("fetched_at"), 80),
            "is_active": True,
        }

    def collect(self, pages: int = 1) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        raw = self._fetch_text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GxrcCollectionError(f"JSON 数据源解析失败：{exc}") from exc
        items = data if isinstance(data, list) else data.get("jobs") or data.get("items") or []
        jobs = [job for job in (self._coerce(item) for item in items if isinstance(item, dict)) if job]
        return jobs, {
            "source": self.label,
            "collected": len(items),
            "normalized": len(jobs),
        }


def collect_all(sources: list) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Aggregate multiple JobSource adapters into one de-duplicated job list.

    Returns (jobs, per_source_reports). Each adapter is isolated: a failure in
    one source never blocks the others.
    """
    merged: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source in sources:
        try:
            jobs, meta = source.collect()
            for job in jobs:
                url = str(job.get("source_url") or "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                merged.append(job)
            reports.append({"ok": True, **meta})
        except Exception as exc:  # noqa: BLE001 - isolate sources
            reports.append({"ok": False, "source": getattr(source, "label", str(source)), "error": str(exc)[:200]})
    return merged, reports
