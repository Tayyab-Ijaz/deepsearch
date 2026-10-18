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

    search_provider: str = "auto"
    brave_api_key: str = ""
    serper_api_key: str = ""
    brave_cost_per_request: float = 0.005
    serper_cost_per_request: float = 0.001

    enable_ai_summary: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # Show each result's own preview picture (the page's og:image). Free: no search credits are used.
    enable_result_images: bool = True
    # Also ask Google Images when a page has no preview picture. Costs one Serper request per result and is
    # often not the profile photo, so it is off by default.
    enable_google_images: bool = False
    daily_search_limit: int = 40
    daily_summary_limit: int = 40
    cache_ttl_seconds: int = 900
    request_timeout: float = 8.0
    # Keep enough ranked hits to show several real profiles from each platform.
    results_limit: int = 30

    @property
    def has_brave(self) -> bool:
        return is_set(self.brave_api_key)

    @property
    def has_serper(self) -> bool:
        return is_set(self.serper_api_key)

    @property
    def has_gemini(self) -> bool:
        return is_set(self.gemini_api_key)


settings = Settings()
