import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.config import Settings
from app.storage import ObjectStore


class SmsServiceError(RuntimeError):
    pass


def normalize_phone(value: str) -> str:
    phone = "".join(ch for ch in str(value or "") if ch.isdigit())
    if phone.startswith("86") and len(phone) == 13:
        phone = phone[2:]
    if len(phone) != 11 or not phone.startswith("1"):
        raise ValueError("请输入有效的中国大陆手机号")
    return phone


def mask_phone(value: str | None) -> str:
    if not value:
        return ""
    phone = normalize_phone(value)
    return f"{phone[:3]}****{phone[-4:]}"


class AliyunSmsVerifier:
    def __init__(self, settings: Settings, store: ObjectStore) -> None:
        self.settings = settings
        self.store = store

    def _metric_key(self, phone: str, scene: str, scope: str) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        digest = hashlib.sha256(f"{scope}:{scene}:{phone}".encode("utf-8")).hexdigest()
        return f"sms-rate/{today}/{digest}.json"

    def _rate_limit(self, phone: str, scene: str) -> None:
        now = int(time.time())
        key = self._metric_key(phone, scene, "phone")
        record = self.store.get_json("a", key) or {"count": 0, "last_sent_at": 0}
        if now - int(record.get("last_sent_at") or 0) < self.settings.sms_send_cooldown_seconds:
            raise SmsServiceError("验证码发送太频繁，请稍后再试")
        if int(record.get("count") or 0) >= self.settings.sms_daily_limit_per_phone:
            raise SmsServiceError("该手机号今日验证码次数已达上限，请明天再试")
        record.update({"count": int(record.get("count") or 0) + 1, "last_sent_at": now})
        self.store.put_json("a", key, record)

    def _sign(self, params: dict[str, Any]) -> str:
        canonical = "&".join(f"{self._percent(key)}={self._percent(params[key])}" for key in sorted(params))
        string_to_sign = f"GET&%2F&{self._percent(canonical)}"
        digest = hmac.new(
            f"{self.settings.aliyun_access_key_secret}&".encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _percent(value: Any) -> str:
        return quote(str(value), safe="").replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    def _request(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.settings.sms_mock:
            return {"Code": "OK", "Model": {"VerifyResult": "PASS"}}
        if not self.settings.aliyun_access_key_id or not self.settings.aliyun_access_key_secret:
            raise SmsServiceError("短信服务未配置 AccessKey")
        base_params: dict[str, Any] = {
            "Action": action,
            "Version": "2017-05-25",
            "Format": "JSON",
            "AccessKeyId": self.settings.aliyun_access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid4()),
            "SignatureVersion": "1.0",
            "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "RegionId": self.settings.aliyun_dypns_region_id,
        }
        base_params.update(params)
        base_params["Signature"] = self._sign(base_params)
        try:
            response = httpx.get(
                self.settings.aliyun_dypns_endpoint,
                params=base_params,
                timeout=self.settings.sms_request_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SmsServiceError("短信服务请求失败，请稍后再试") from exc
        data = response.json()
        if data.get("Code") not in {None, "OK"}:
            raise SmsServiceError(str(data.get("Message") or "短信服务返回失败"))
        return data

    def send_code(self, phone: str, scene: str) -> dict[str, Any]:
        phone = normalize_phone(phone)
        if scene not in self.settings.sms_allowed_scenes:
            raise SmsServiceError("验证码场景无效")
        self._rate_limit(phone, scene)
        template_code = self.settings.sms_template_for_scene(scene)
        if not self.settings.sms_mock and (not self.settings.sms_sign_name or not template_code):
            raise SmsServiceError("请在阿里云号码认证控制台填写预置系统签名名称和对应场景的模板 Code")
        data = self._request(
            "SendSmsVerifyCode",
            {
                "PhoneNumber": phone,
                "SignName": self.settings.sms_sign_name,
                "TemplateCode": template_code,
                "TemplateParam": json.dumps(
                    {"code": "##code##", "min": str(self.settings.sms_code_valid_minutes)},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "SchemeName": self.settings.sms_scheme_name,
            },
        )
        return {"ok": True, "request_id": data.get("RequestId"), "phone": mask_phone(phone)}

    def check_code(self, phone: str, code: str, scene: str) -> None:
        phone = normalize_phone(phone)
        code = str(code or "").strip()
        if not code:
            raise SmsServiceError("请输入短信验证码")
        if self.settings.sms_mock:
            if code != self.settings.sms_mock_code:
                raise SmsServiceError("短信验证码不正确或已过期")
            return
        data = self._request(
            "CheckSmsVerifyCode",
            {"PhoneNumber": phone, "VerifyCode": code, "SchemeName": self.settings.sms_scheme_name},
        )
        result = ((data.get("Model") or {}).get("VerifyResult") or data.get("VerifyResult") or "").upper()
        if result != "PASS":
            raise SmsServiceError("短信验证码不正确或已过期")
