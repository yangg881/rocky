from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.sms import normalize_phone


class PhoneCodeMixin(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=10)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class RegisterRequest(PhoneCodeMixin):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[\w\-\u4e00-\u9fff]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info) -> str:
        if value != info.data.get("password"):
            raise ValueError("两次输入的密码不一致")
        return value


class LoginRequest(BaseModel):
    username: str
    password: str


class SmsLoginRequest(PhoneCodeMixin):
    """Passwordless login, limited to an already-bound phone number."""


class ResetPasswordRequest(PhoneCodeMixin):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info) -> str:
        if value != info.data.get("new_password"):
            raise ValueError("两次输入的密码不一致")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    confirm_username: str = Field(min_length=1, max_length=40)


class SmsCodeRequest(BaseModel):
    phone: str
    scene: Literal["register", "login", "reset_password", "change_phone"]

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class ChangePhoneRequest(PhoneCodeMixin):
    pass


class AdminUpdatePhoneRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class ResumeContent(BaseModel):
    name: str = ""
    title: str = ""
    contact: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)


class ResumeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    content: ResumeContent


class ResumeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    content: ResumeContent | None = None


class JDRequest(BaseModel):
    source_type: Literal["text", "url"]
    text: str | None = None
    url: str | None = None


class GenerateRequest(BaseModel):
    resume_id: str | None = None
    jd: dict[str, Any]
    radar_job_id: str | None = Field(default=None, max_length=120)
    # Keep installed clients from older UI releases compatible. Unknown values
    # are normalised to auto by the endpoint instead of rejecting a valid JD.
    design_theme: str = "auto"
    template_id: str | None = Field(default=None, max_length=120)
    language: str = "zh"  # zh | en | bilingual
    highlights: list[str] = Field(default_factory=list, max_length=5)  # 用户补充的真实量化亮点


class RadarFeedbackRequest(BaseModel):
    action: Literal["viewed", "saved", "applied", "not_interested", "later"]
    remind_until: str = Field(default="", max_length=40)


class RadarCompanyPreferenceRequest(BaseModel):
    blocked: bool


class RadarImportRequest(BaseModel):
    jobs: list[dict[str, Any]] = Field(default_factory=list, max_length=20_000)
    replace: bool = False


class RegenerateRequest(BaseModel):
    design_theme: Literal[
        "auto", "tech_indigo", "operations_terra", "executive_navy", "care_teal", "creative_plum", "ats_mono"
    ] = "auto"
    template_id: str | None = Field(default=None, max_length=120)


class CareerFactBuildRequest(BaseModel):
    resume_id: str


class CareerFactDecisionRequest(BaseModel):
    status: Literal["confirmed", "rejected"]
    edited_text: str | None = Field(default=None, max_length=2000)


class ReviewCreateRequest(BaseModel):
    resume_id: str
    jd: dict[str, Any]


class ReviewDecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]
    note: str = Field(default="", max_length=500)


class ApplicationCreateRequest(BaseModel):
    generation_id: str | None = None
    job_title: str = Field(min_length=1, max_length=120)
    company: str = Field(default="", max_length=120)
    source_url: str = Field(default="", max_length=1000)
    status: Literal["saved", "applied", "interview", "offer", "rejected", "closed"] = "saved"
    next_action_at: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=3000)


class ApplicationUpdateRequest(BaseModel):
    status: Literal["saved", "applied", "interview", "offer", "rejected", "closed"] | None = None
    next_action_at: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=3000)


class OrderCreateRequest(BaseModel):
    product_code: Literal["starter", "pro", "career_plus"]


class AdminOrderUpdateRequest(BaseModel):
    status: Literal["paid", "cancelled", "refunded"]


class AdminCreditUpdateRequest(BaseModel):
    """Admin-side manual credit controls for a single user."""

    mode: Literal["set", "add", "sub", "clear", "suspend", "resume"]
    amount: int | None = Field(default=None, ge=0, le=1_000_000)
    note: str = Field(default="", max_length=200)
