from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "职达简历"
    app_env: str = "development"
    app_base_path: str = "/resume-ai"
    public_base_url: str = ""
    jwt_secret: str = "development-only-change-me"
    jwt_expire_hours: int = 24
    auth_cookie_name: str = "zhiday_session"
    auth_cookie_same_site: str = "lax"
    auth_cookie_secure: bool = False
    admin_username: str = "admin"
    admin_password: str = "change-me"

    sensenova_base_url: str = "https://token.sensenova.cn/v1"
    sensenova_api_key: str = ""
    sensenova_preprocess_model: str = "sensenova-6.7-flash-lite"
    sensenova_rewrite_model: str = "deepseek-v4-flash"
    sensenova_image_model: str = "sensenova-u1-fast"
    sensenova_design_model: str = "sensenova-6.7-flash-lite"
    sensenova_max_concurrency: int = 2
    sensenova_min_interval_seconds: float = 1.2
    sensenova_max_retries: int = 2
    sensenova_request_timeout_seconds: float = 55
    ai_mock: bool = False

    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_dypns_region_id: str = "cn-hangzhou"
    aliyun_dypns_endpoint: str = "https://dypnsapi.aliyuncs.com/"
    sms_sign_name: str = ""
    sms_template_code: str = ""
    sms_template_code_register: str = ""
    sms_template_code_login: str = ""
    sms_template_code_reset_password: str = ""
    sms_template_code_change_phone: str = ""
    sms_scheme_name: str = "jd-resume-ai"
    sms_code_valid_minutes: int = 5
    sms_send_cooldown_seconds: int = 60
    sms_daily_limit_per_phone: int = 10
    sms_request_timeout_seconds: float = 10
    sms_mock: bool = False
    sms_mock_code: str = "123456"

    storage_backend: Literal["tos", "memory"] = "memory"
    tos_access_key_id: str = ""
    tos_secret_access_key: str = ""
    tos_region: str = "cn-beijing"
    tos_s3_endpoint: str = "https://tos-s3-cn-beijing.volces.com"
    tos_public_endpoint: str = "tos-cn-beijing.volces.com"
    tos_bucket_a: str = "system-data"
    tos_bucket_b: str = "resume-files"
    tos_bucket_c: str = "image-assets"
    tos_prefix: str = "jd-resume-ai"
    tos_presign_seconds: int = 3600
    tos_warning_bytes: int = 5 * 1024**3
    tos_warning_requests: int = 500_000
    tos_warning_egress_bytes: int = 5 * 1024**3

    port: int | None = None
    port_scan_start: int = 8100
    port_scan_end: int = 8999
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    cors_allowed_origins: str = ""
    rate_limit_enabled: bool = True
    auth_rate_limit_per_minute: int = 12
    task_rate_limit_per_hour: int = 30
    security_headers_enabled: bool = True
    database_url: str = ""
    redis_url: str = ""
    task_queue_enabled: bool = False
    task_queue_name: str = "resume-ai"

    @field_validator("app_base_path")
    @classmethod
    def normalize_base_path(cls, value: str) -> str:
        if not value:
            return ""
        return "/" + value.strip("/")

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if not value:
            raise ValueError("JWT_SECRET cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Refuse the most dangerous accidental production configurations.

        HTTPS itself is enabled at the reverse proxy, so the application only
        validates configuration it can authoritatively know about.  A bare-IP
        deployment may temporarily leave ``public_base_url`` empty, but the
        health endpoint will expose that as a readiness warning until a domain
        and HTTPS URL are configured.
        """
        if self.app_env.lower() != "production":
            return self
        insecure_values = {"", "development-only-change-me", "replace-with-a-long-random-secret"}
        if self.jwt_secret in insecure_values or len(self.jwt_secret) < 32:
            raise ValueError("production requires a random JWT_SECRET of at least 32 characters")
        if self.admin_password in {"", "change-me", "replace-with-a-strong-password"} or len(self.admin_password) < 12:
            raise ValueError("production requires a strong ADMIN_PASSWORD of at least 12 characters")
        if self.storage_backend != "tos":
            raise ValueError("production requires STORAGE_BACKEND=tos")
        if self.ai_mock or self.sms_mock:
            raise ValueError("production cannot enable AI_MOCK or SMS_MOCK")
        if not self.trusted_host_list or "*" in self.trusted_host_list:
            raise ValueError("production requires explicit TRUSTED_HOSTS")
        if not self.database_url:
            raise ValueError("production requires DATABASE_URL for business metadata")
        if not self.redis_url or not self.task_queue_enabled:
            raise ValueError("production requires REDIS_URL and TASK_QUEUE_ENABLED=true")
        if self.public_origin.startswith("https://") and not self.auth_cookie_secure:
            # Operator opted into non-Secure session cookies (e.g. access via http://IP).
            # Acceptable only on trusted networks; the session cookie may travel over plaintext HTTP.
            import sys
            print(
                "[zhiday.config WARNING] AUTH_COOKIE_SECURE=false while public_origin is HTTPS: "
                "the session cookie can be transmitted over HTTP. Use only on trusted networks.",
                file=sys.stderr,
            )
        return self

    @field_validator("port", mode="before")
    @classmethod
    def empty_port_means_auto(cls, value):
        return None if value in (None, "") else value

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip().rstrip("/") for item in self.cors_allowed_origins.split(",") if item.strip()]

    @property
    def public_origin(self) -> str:
        return self.public_base_url.strip().rstrip("/")

    @property
    def sms_allowed_scenes(self) -> set[str]:
        return {"register", "login", "reset_password", "change_phone"}

    def sms_template_for_scene(self, scene: str) -> str:
        return {
            "register": self.sms_template_code_register or self.sms_template_code,
            "login": self.sms_template_code_login or self.sms_template_code or self.sms_template_code_register,
            "reset_password": self.sms_template_code_reset_password or self.sms_template_code,
            "change_phone": self.sms_template_code_change_phone or self.sms_template_code,
        }.get(scene, "")

    def bucket_name(self, bucket: str) -> str:
        return {"a": self.tos_bucket_a, "b": self.tos_bucket_b, "c": self.tos_bucket_c}[bucket]


@lru_cache
def get_settings() -> Settings:
    return Settings()
