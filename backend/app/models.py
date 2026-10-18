import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{2,40}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


class SearchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    location: Optional[str] = Field(default=None, max_length=60)
    consent: bool = False

    @field_validator("name", "location")
    @classmethod
    def clean(cls, v):
        if v is None:
            return v
        v = _CTRL.sub(" ", v).strip()
        return re.sub(r"\s+", " ", v)

    @field_validator("name")
    @classmethod
    def name_ok(cls, v):
        v = v.replace('"', "")
        if len(v) < 2:
            raise ValueError("Enter at least 2 characters.")
        return v


class UsernameRequest(BaseModel):
    username: str
    consent: bool = False

    @field_validator("username")
    @classmethod
    def valid(cls, v):
        v = v.strip().lstrip("@")
        if not USERNAME_RE.match(v):
            raise ValueError("Use 2-40 characters: letters, numbers, dot, dash or underscore.")
        return v


class SummaryItem(BaseModel):
    platform: str
    title: str
    description: str = ""
    profile_url: str

    @field_validator("platform", "title", "description", "profile_url", mode="before")
    @classmethod
    def shorten(cls, v):
        # Cut long text instead of rejecting the whole request.
        return _CTRL.sub(" ", str(v))[:600] if v is not None else ""


class SummaryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    results: list[SummaryItem] = Field(max_length=8)
    consent: bool = False


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=60)

    @field_validator("email")
    @classmethod
    def email_ok(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("display_name")
    @classmethod
    def name_clean(cls, v):
        if v is None:
            return None
        v = re.sub(r"\s+", " ", _CTRL.sub(" ", v)).strip()
        return v or None


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lower(cls, v):
        return v.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class DeleteAccountRequest(BaseModel):
    password: Optional[str] = Field(default=None, min_length=1, max_length=128)


class FirebaseSignInRequest(BaseModel):
    id_token: str = Field(min_length=40, max_length=8192)


class Result(BaseModel):
    name: str
    platform: str
    platform_key: str
    title: str
    description: str = ""
    profile_url: str
    image_url: Optional[str] = None
    match_label: Literal["strong_match", "possible_match", "weak_match"]
    match_score: float
    source: str


class SavedPersonRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platform: str = Field(min_length=1, max_length=80)
    platform_key: str = Field(min_length=1, max_length=80)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=1000)
    profile_url: str = Field(min_length=1, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    match_label: Literal["strong_match", "possible_match", "weak_match"]
    match_score: float = Field(ge=0, le=1)
    source: str = Field(default="", max_length=200)

    @field_validator("name", "platform", "platform_key", "title", "description", "source", mode="before")
    @classmethod
    def clean_saved_text(cls, value):
        return re.sub(r"\s+", " ", _CTRL.sub(" ", str(value or ""))).strip()

    @field_validator("profile_url", "image_url")
    @classmethod
    def public_https_url(cls, value):
        if value is not None and not value.lower().startswith("https://"):
            raise ValueError("Saved profile links must use HTTPS.")
        return value
