import asyncio
import json
import re
import time
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings
from app.storage import ObjectStore


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


class AIServiceError(RuntimeError):
    """Raised when SenseNova does not return a complete usable result."""

    def __init__(self, message: str, *, category: str = "upstream_error", metadata: dict | None = None):
        super().__init__(message)
        self.category = category
        self.metadata = metadata or {}


class SenseNovaClient:
    def __init__(self, settings: Settings, store: ObjectStore):
        self.settings = settings
        self.store = store
        self.client = AsyncOpenAI(
            base_url=settings.sensenova_base_url,
            api_key=settings.sensenova_api_key or "missing",
            timeout=settings.sensenova_request_timeout_seconds,
            max_retries=0,
        )
        self._semaphore = asyncio.Semaphore(settings.sensenova_max_concurrency)
        self._rate_lock = asyncio.Lock()
        self._last_request = 0.0

    async def _throttle(self) -> None:
        async with self._rate_lock:
            elapsed = time.monotonic() - self._last_request
            delay = self.settings.sensenova_min_interval_seconds - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()

    async def _chat_once(
        self, model: str, messages: list[dict[str, Any]], max_tokens: int = 5000
    ) -> tuple[str, dict[str, Any]]:
        async with self._semaphore:
            await self._throttle()
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=max_tokens,
            )
        stats = self.store.get_json("a", "metrics/models.json") or {}
        stats[model] = int(stats.get(model, 0)) + 1
        self.store.put_json("a", "metrics/models.json", stats)
        choice = response.choices[0]
        return choice.message.content or "", {
            "model": getattr(response, "model", None) or model,
            "finish_reason": choice.finish_reason,
        }

    @staticmethod
    def _compact_retry_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compact = [dict(message) for message in messages]
        compact.append(
            {
                "role": "user",
                "content": (
                    "上次输出被截断或格式不完整。请跳过分析过程，只输出最终 JSON。"
                    "每个列表最多保留 12 项，每项使用短句；raw_text 最多 1500 字，不要复述网页无关内容。"
                ),
            }
        )
        return compact

    async def _chat_json(
        self, model: str, messages: list[dict[str, Any]], max_tokens: int = 5000
    ) -> dict[str, Any]:
        attempts = max(1, self.settings.sensenova_max_retries)
        last_category = "upstream_error"
        last_metadata: dict[str, Any] = {"model": model, "retry_count": 0}
        last_error: Exception | None = None
        for attempt in range(attempts):
            request_messages = messages if attempt == 0 else self._compact_retry_messages(messages)
            try:
                response = await self._chat_once(model, request_messages, max_tokens)
                if isinstance(response, tuple):
                    content, metadata = response
                else:  # 保持测试替身和旧扩展的兼容性
                    content, metadata = response, {"model": model, "finish_reason": None}
                last_metadata = {**metadata, "retry_count": attempt}
                if metadata.get("finish_reason") == "length":
                    last_category = "output_truncated"
                    raise ValueError("model output truncated")
                if not content.strip():
                    last_category = "empty_content"
                    raise ValueError("model returned empty content")
                try:
                    result = _json_from_text(content)
                except (json.JSONDecodeError, TypeError) as exc:
                    last_category = "invalid_json"
                    raise ValueError("model returned invalid JSON") from exc
                if not isinstance(result, dict):
                    last_category = "invalid_json"
                    raise ValueError("model returned a non-object JSON value")
                return result
            except Exception as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                if status_code == 429:
                    last_category = "rate_limited"
                elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in type(exc).__name__.lower():
                    last_category = "upstream_timeout"
                if attempt + 1 < attempts:
                    await asyncio.sleep(min(2**attempt, 4))

        messages_by_category = {
            "output_truncated": "AI 返回内容过长，系统已自动精简重试但仍未完成",
            "empty_content": "AI 暂时没有返回有效内容，系统已自动重试",
            "invalid_json": "AI 返回的数据格式不完整，系统已自动修复重试",
            "rate_limited": "AI 服务当前请求较多，请稍后重试",
            "upstream_timeout": "AI 服务响应超时，请稍后重试",
        }
        raise AIServiceError(
            messages_by_category.get(last_category, "AI 服务暂时不可用，请稍后重试"),
            category=last_category,
            metadata=last_metadata,
        ) from last_error

    async def structure_resume(self, text: str, image_url: str | None = None) -> dict[str, Any]:
        if self.settings.ai_mock:
            return {
                "name": "测试用户",
                "title": "候选人",
                "contact": {},
                "summary": text[:180],
                "skills": ["沟通", "执行"],
                "experience": [],
                "projects": [],
                "education": [],
                "certificates": [],
            }
        # Compact schema + higher token budget: long formal resumes were truncating
        # at the default 5000 tokens and failing the whole upload.
        instruction = (
            "你是简历结构化工具。只提取原文真实信息，禁止编造。"
            "只输出一个紧凑 JSON（不要 markdown、不要解释），字段："
            "name,title,contact,summary,skills,experience,projects,education,certificates。"
            "contact 仅含出现的 phone/email/age/birth_date/location/wechat；"
            "skills 最多 12 个短词；experience/projects/education 各最多 8 段；"
            "每段 details 最多 5 条，每条不超过 80 字；summary 不超过 120 字。"
            "缺失用 \"\" 或 []。"
        )
        if image_url:
            content: Any = [
                {"type": "text", "text": instruction},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
            return await self._chat_json(
                self.settings.sensenova_preprocess_model,
                [{"role": "user", "content": content}],
                max_tokens=7000,
            )

        cleaned = re.sub(r"[ \t]+\n", "\n", str(text or ""))
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        # Prefer the densest front section but keep a tail for education/certs.
        if len(cleaned) > 14000:
            cleaned = cleaned[:10000] + "\n...\n" + cleaned[-3500:]
        # One compact pass only — double retries made uploads wait 2–3 minutes
        # and clients appeared to "fail" while the server was still working.
        if len(cleaned) > 9000:
            cleaned = cleaned[:6500] + "\n...\n" + cleaned[-2200:]
            instruction += " 原文已截断，请优先提取姓名联系方式与最近经历。"
        return await self._chat_json(
            self.settings.sensenova_preprocess_model,
            [{"role": "user", "content": f"{instruction}\n\n简历原文：\n{cleaned}"}],
            max_tokens=6000,
        )

    async def structure_jd(
        self,
        text: str = "",
        image_url: str | None = None,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        if self.settings.ai_mock:
            return {
                "title": "测试岗位",
                "company": "",
                "responsibilities": [text[:120] or "完成岗位工作"],
                "requirements": ["沟通能力"],
                "keywords": ["执行"],
                "raw_text": text,
            }
        instruction = (
            "你是岗位描述结构化工具。不要输出思考过程或解释，只输出一个紧凑 JSON 对象。"
            "提取职位名称、公司、职责、硬性要求、加分项和关键词，去除网页导航和广告，不编造缺失信息。"
            "字段为 title,company,responsibilities,requirements,preferred,keywords,raw_text。"
            "职责和要求各最多 12 条，关键词最多 15 个，raw_text 仅保留岗位正文且最多 1500 字。"
        )
        urls = image_urls or ([image_url] if image_url else [])
        if len(urls) > 1:
            pages = [await self.structure_jd(image_url=url) for url in urls]
            merged: dict[str, Any] = {
                "title": "",
                "company": "",
                "responsibilities": [],
                "requirements": [],
                "preferred": [],
                "keywords": [],
                "raw_text": "",
            }
            for page in pages:
                merged["title"] = merged["title"] or page.get("title", "")
                merged["company"] = merged["company"] or page.get("company", "")
                for field in ("responsibilities", "requirements", "preferred", "keywords"):
                    values = page.get(field, [])
                    if isinstance(values, str):
                        values = [values]
                    for value in values:
                        if value and value not in merged[field]:
                            merged[field].append(value)
                raw_text = str(page.get("raw_text") or "").strip()
                if raw_text and raw_text not in merged["raw_text"]:
                    merged["raw_text"] = (merged["raw_text"] + "\n" + raw_text).strip()
            merged["raw_text"] = merged["raw_text"][:5000]
            return merged
        if urls:
            content: Any = [
                {
                    "type": "text",
                    "text": instruction + "多张图片按给定顺序从上到下拼接理解，合并重叠内容并去重。",
                },
            ]
            content.extend({"type": "image_url", "image_url": {"url": url}} for url in urls)
        else:
            content = f"{instruction}\n\n岗位原文：\n{text[:50000]}"
        return await self._chat_json(
            self.settings.sensenova_preprocess_model,
            [{"role": "user", "content": content}],
            max_tokens=6000,
        )

    async def rewrite_resume(self, resume: dict[str, Any], jd: dict[str, Any], language: str = "zh", highlights: list[str] | None = None) -> dict[str, Any]:
        if self.settings.ai_mock:
            result = dict(resume)
            result["title"] = jd.get("title") or result.get("title", "")
            suffix = " (中英双语)" if language == "bilingual" else " (English CV)" if language == "en" else ""
            result["summary"] = f"针对{jd.get('title', '目标岗位')}优化：{result.get('summary', '')}{suffix}".strip()
            return result
        language_instruction = ""
        if language == "en":
            language_instruction = (
                "本简历面向外企/跨境岗位，所有文字字段（summary、skills、experience、projects 等的表述）必须使用英文撰写，"
                "生成一份英文简历（English CV）；事实与中文版保持一致，仅做语言转换。"
            )
        elif language == "bilingual":
            language_instruction = (
                "生成中英双语简历：每段概述、职责与成果在中文之后，用独立英文段落补充对应翻译；"
                "保持真实事实不变，仅增加英文表达。"
            )
        system = (
            "你是资深简历顾问"
            + ("，专做英文简历" if language == "en" else "，专做中英双语简历" if language == "bilingual" else "，要把真实经历改写成清晰、有重点、适合招聘方快速阅读的专业简历")
            + "。绝对禁止编造公司、岗位、项目、日期、学历、证书、技能、结果或任何数字；原文没有数字就不能添加数字。"
            "summary字段作为“经验与能力概述”，控制在60至120字，完整概括与目标岗位最相关的经验、能力和方向。"
            "skills字段只保留真实的内部匹配关键词，禁止重复summary内容、罗列长技能清单、刻意堆关键词或展示无关工具。"
            "每段工作和项目经历必须保留原公司、岗位、日期/时间段，日期/时间段要原样放在period字段；"
            "禁止删除、改写、补造或猜测任何经历时间，没有日期的经历也不要凭空添加日期。"
            "职责与成果改写成2至5条短句；"
            "每条优先使用动作+对象+方法+真实结果的表达，但没有结果事实时只写职责，不能虚构亮点。"
            "按岗位相关度排序和强调内容，自然融入岗位关键词，不机械堆词。"
            + language_instruction
            + (self._highlight_instruction(highlights) if highlights else "")
            + "只返回一个JSON对象，最外层必须直接包含name,title,contact,summary,skills,experience,projects,"
            "education,certificates，禁止再套resume或content字段，不要附加解释。"
        )
        payload = json.dumps({"resume": resume, "job_description": jd}, ensure_ascii=False)
        return await self._chat_json(
            self.settings.sensenova_rewrite_model,
            [{"role": "system", "content": system}, {"role": "user", "content": payload}],
            max_tokens=8000,
        )

    async def plan_resume_design(self, jd: dict[str, Any]) -> dict[str, Any]:
        if self.settings.ai_mock:
            return {
                "theme_id": "tech_indigo",
                "layout_id": "accent_header",
                "role_family": "通用岗位",
                "reason": "测试默认",
            }
        instruction = (
            "你是中文简历的视觉设计策划。只根据岗位描述中明确出现的职位、行业、职责和公司信息，"
            "从 tech_indigo、operations_terra、executive_navy、care_teal、creative_plum 五个受控主题中选一个。"
            "不允许根据候选人的个人特征推测，也不能编造公司类型。"
            "返回单个 JSON 对象，字段为 theme_id,layout_id,layout_variant,template_id,density,role_family,company_type,reason。"
            "layout_id 只能是 accent_header 或 timeline_focus；template_id 只能是 classic 或 serif；"
            "layout_variant 必须从 left_sidebar,banner_timeline,executive_minimal,creative_asymmetry,split_columns,campus_compact,top_profile 中选一个，"
            "且要让版式结构明显不同：技术倾向 left_sidebar，医疗教育 banner_timeline，管理 executive_minimal，营销 creative_asymmetry。"
            "density 只能是 compact、balanced 或 airy；reason 不超过 28 个汉字。"
        )
        return await self._chat_json(
            self.settings.sensenova_design_model,
            [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(jd, ensure_ascii=False)},
            ],
            max_tokens=500,
        )

    @staticmethod
    def _highlight_instruction(highlights: list[str]) -> str:
        items = [str(item).strip() for item in (highlights or []) if str(item).strip()][:5]
        if not items:
            return ""
        bullet = "；".join(items)
        return (
            f"用户补充的真实亮点（来自本人填写，必须原样、如实融入对应经历，不得夸大或添加数字）：{bullet}。"
            "优先把这些量化或结果性信息写进相关经历的成果句，让简历更可信、更有竞争力。"
        )

    async def generate_image(self, prompt: str) -> str:
        if self.settings.ai_mock:
            return "https://example.invalid/mock-image.png"
        async with self._semaphore:
            await self._throttle()
            response = await self.client.images.generate(
                model=self.settings.sensenova_image_model,
                prompt=prompt,
                n=1,
            )
        stats = self.store.get_json("a", "metrics/models.json") or {}
        model = self.settings.sensenova_image_model
        stats[model] = int(stats.get(model, 0)) + 1
        self.store.put_json("a", "metrics/models.json", stats)
        return response.data[0].url or ""
