from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def is_set(value: str) -> bool:
    """A key counts as configured only if it is not empty and not a placeholder."""
    v = (value or "").strip()
    if not v:
        return False
    up = v.upper()
    return not (up.startswith("PASTE_") or "YOUR_" in up or up.endswith("_HERE") or up.startswith("REPLACE"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    debug: bool = False
    # Comma-separated web addresses allowed to call the API from a browser. Empty = phones only.
    cors_origins: str = ""
    jwt_secret: str = ""
    firebase_project_id: str = ""
    firebase_credentials: str = ""
    access_token_minutes: int = 60
    refresh_token_days: int = 30

    # Password-reset emails go through Resend (https://resend.com). The sender must be on a domain verified there.
    resend_api_key: str = ""
    email_from: str = "DeepSearch AI <info@wellminddatasolutions.com>"
    reset_code_minutes: int = 15

    search_provider: str = "auto"
    brave_api_key: str = ""
    serper_api_key: str = ""
    brave_cost_per_request: float = 0.005
    serper_cost_per_request: float = 0.001

    enable_ai_summary: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # Pictures: Google Images is searched once per platform (not once per result) and matched to each profile's
    # own page, so a picture is only ever the one that page shows.
    enable_platform_images: bool = True
    # Fill remaining gaps with the page's own preview picture (og:image). Free: no search credits are used.
    enable_result_images: bool = True
    # Depth. A platform asks for another page only while the last one still held real name matches, so common
    # names go deep and unusual names stop early. One page is one provider request.
    search_pages: int = 3
    image_pages: int = 2
    search_concurrency: int = 16
    # Profiles still without a picture after everything above get one targeted Google Images lookup each (1 request).
    image_lookups: int = 10
    daily_search_limit: int = 40
    daily_summary_limit: int = 40
    cache_ttl_seconds: int = 900
    request_timeout: float = 8.0
    # The most ranked profiles one search returns.
    results_limit: int = 80

    @property
    def has_brave(self) -> bool:
        return is_set(self.brave_api_key)

    @property
    def has_email(self) -> bool:
        return is_set(self.resend_api_key)

    @property
    def has_serper(self) -> bool:
        return is_set(self.serper_api_key)

    @property
    def has_gemini(self) -> bool:
        return is_set(self.gemini_api_key)


settings = Settings()
