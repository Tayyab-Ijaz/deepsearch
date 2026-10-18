from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from .config import settings
from .models import (DeleteAccountRequest, ForgotPasswordRequest, LoginRequest, RefreshRequest, RegisterRequest,
                     ResetPasswordRequest, SavedPersonRequest, SearchRequest, SummaryRequest, UsernameRequest)
from . import pages
from .services import accounts, mailer, metrics, summarizer, username_prober
from .services.accounts import AuthError
from .services.providers import ProviderError
from .services.search_service import search_people

log = logging.getLogger(__name__)
CONSENT_MESSAGE = "Please confirm you are searching for yourself, someone who agreed, or a well-known public figure."
bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    accounts.jwt_secret()  # fail at start-up, not on the first login
    accounts.init()
    metrics.init()
    app.state.http = httpx.AsyncClient(timeout=settings.request_timeout)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="DeepSearch AI API", version="1.0.0", lifespan=lifespan,
    docs_url="/docs" if settings.debug else None, redoc_url=None, openapi_url="/openapi.json" if settings.debug else None,
)


_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# Browsers (the web build) ask permission with an OPTIONS request before they call the API.
# Pages served from this same computer (localhost) are always allowed, so local testing just works.
# Add your live web address in CORS_ORIGINS. Phones never need this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(AuthError)
async def auth_error_handler(_: Request, e: AuthError):
    headers = {"WWW-Authenticate": "Bearer"} if e.status == 401 else None
    return JSONResponse({"detail": e.message}, status_code=e.status, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, e: RequestValidationError):
    # One readable sentence instead of a technical list.
    first = e.errors()[0] if e.errors() else {}
    msg = str(first.get("msg", "Check your input.")).removeprefix("Value error, ")
    loc = first.get("loc", ())
    if any("password" in str(part) for part in loc) and first.get("type") == "string_too_short":
        msg = "Use at least 8 characters for the password."
    return JSONResponse({"detail": msg}, status_code=422)


def current_user_id(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> int:
    if cred is None:
        raise AuthError("Please sign in.")
    user_id, password_version = accounts.read_access_claims(cred.credentials)
    user = accounts.get_user(user_id)
    # A password reset signs out every session that started before it.
    if user is None or password_version != int(user.get("password_changed_at", 0)):
        raise AuthError("Please sign in again.")
    return user_id


def _ip(request: Request) -> str:
    # Behind Vercel the socket peer is the proxy; Vercel sets the real client address in these headers.
    forwarded = request.headers.get("x-vercel-forwarded-for") or request.headers.get("x-forwarded-for") or ""
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


async def _log_run(*args) -> None:
    """Metrics are best effort: a Firestore hiccup must not turn a finished search into an error."""
    try:
        await run_in_threadpool(metrics.log_run, *args)
    except Exception:
        pass


# ---------------- public pages (the App Store needs working privacy and support URLs) ----------------
def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(pages.render(title, body), headers={"Cache-Control": "public, max-age=3600"})


@app.get("/privacy", include_in_schema=False)
def privacy_page():
    return _page("Privacy Policy", pages.PRIVACY)


@app.get("/terms", include_in_schema=False)
def terms_page():
    return _page("Terms of Use", pages.TERMS)


@app.get("/support", include_in_schema=False)
def support_page():
    return _page("Support", pages.SUPPORT)


# ---------------- public ----------------
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------------- accounts ----------------
@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest, request: Request):
    key = f"reg:{_ip(request)}"
    accounts.check_rate(key)
    accounts.note_failure(key)  # counts every sign-up from this address
    return accounts.register(req.email, req.password, req.display_name)


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    key = f"login:{_ip(request)}:{req.email}"
    accounts.check_rate(key)
    try:
        out = accounts.login(req.email, req.password)
    except AuthError:
        accounts.note_failure(key)
        raise
    accounts.clear_failures(key)
    return out


RESET_MIN_SECONDS = 1.2
RESET_REQUESTED = "If an account exists for that email, we have sent a 6-digit code. It expires in a few minutes."


def _pad(started: float, seconds: float) -> None:
    """Take about the same time whether or not the address has an account, so timing reveals nothing."""
    time.sleep(max(0.0, seconds - (time.perf_counter() - started)))


@app.post("/api/auth/forgot-password", status_code=202)
def forgot_password(req: ForgotPasswordRequest, request: Request):
    if not mailer.configured():
        raise HTTPException(503, "Password reset is not available right now. Please contact support.")
    started = time.perf_counter()
    ip_key, email_key = f"forgot:{_ip(request)}", f"forgot-email:{req.email}"
    accounts.check_rate(ip_key, 10)
    accounts.check_rate(email_key, 3)
    accounts.note_failure(ip_key)      # every request counts, so this cannot be used to flood anyone with emails
    accounts.note_failure(email_key)
    code = accounts.start_password_reset(req.email)
    if code:
        try:
            mailer.send_reset_code(req.email, code, settings.reset_code_minutes)
        except mailer.MailError:
            log.error("Could not send a password reset email")  # the caller still gets the same answer
    _pad(started, RESET_MIN_SECONDS)
    return {"detail": RESET_REQUESTED}


@app.post("/api/auth/reset-password", status_code=204)
def reset_password(req: ResetPasswordRequest, request: Request):
    ip_key, email_key = f"reset:{_ip(request)}", f"reset-email:{req.email}"
    accounts.check_rate(ip_key, 20)
    accounts.check_rate(email_key, 10)
    accounts.note_failure(ip_key)
    accounts.note_failure(email_key)
    accounts.finish_password_reset(req.email, req.code, req.new_password)
    accounts.clear_failures(email_key)
    accounts.clear_failures(f"login:{_ip(request)}:{req.email}")  # a locked-out user can try the new password straight away


@app.post("/api/auth/refresh")
def refresh(req: RefreshRequest):
    return accounts.refresh(req.refresh_token)


@app.post("/api/auth/logout", status_code=204)
def logout(req: RefreshRequest):
    accounts.logout(req.refresh_token)


@app.get("/api/auth/me")
def me(user_id: int = Depends(current_user_id)):
    user = accounts.get_user(user_id)
    return {"user": accounts.public_user(user), "usage": accounts.usage_today(user_id)}


@app.delete("/api/auth/account", status_code=204)
def delete_account(req: DeleteAccountRequest, user_id: int = Depends(current_user_id)):
    accounts.delete_account(user_id, req.password)


@app.get("/api/features")
def features(_: int = Depends(current_user_id)):
    return {"ai_summary": summarizer.disabled_reason() is None}


@app.get("/api/saved")
def list_saved_people(user_id: int = Depends(current_user_id)):
    return {"results": accounts.list_saved_people(user_id)}


@app.post("/api/saved", status_code=201)
def save_person(req: SavedPersonRequest, user_id: int = Depends(current_user_id)):
    return accounts.save_person(user_id, req.model_dump())


@app.delete("/api/saved/{saved_id}", status_code=204)
def delete_saved_person(saved_id: str, user_id: int = Depends(current_user_id)):
    if not accounts.delete_saved_person(user_id, saved_id):
        raise HTTPException(404, "Saved profile not found.")


# ---------------- tools (sign-in required) ----------------
@app.post("/api/search")
async def api_search(req: SearchRequest, user_id: int = Depends(current_user_id)):
    if not req.consent:
        raise HTTPException(400, CONSENT_MESSAGE)
    await run_in_threadpool(accounts.spend, user_id, "search", settings.daily_search_limit)
    try:
        out = await search_people(app.state.http, req.name, req.location, "auto")
    except ProviderError as e:
        raise HTTPException(502, str(e))
    await _log_run("search", out["provider"], out["took_ms"], out["cost_usd"], len(out["results"]), len(out["warnings"]))
    return {"results": out["results"], "took_ms": out["took_ms"], "warnings": out["warnings"]}


@app.post("/api/username")
async def api_username(req: UsernameRequest, user_id: int = Depends(current_user_id)):
    if not req.consent:
        raise HTTPException(400, CONSENT_MESSAGE)
    await run_in_threadpool(accounts.spend, user_id, "search", settings.daily_search_limit)
    t0 = time.perf_counter()
    rows = await username_prober.probe_username(app.state.http, req.username)
    took = int((time.perf_counter() - t0) * 1000)
    await _log_run("username", "probe", took, 0.0, sum(1 for r in rows if r["verdict"] == "confirmed"))
    return {"username": req.username, "platforms": rows, "took_ms": took}


@app.post("/api/summary")
async def api_summary(req: SummaryRequest, user_id: int = Depends(current_user_id)):
    if not req.consent:
        raise HTTPException(400, CONSENT_MESSAGE)
    reason = summarizer.disabled_reason()
    if reason:
        raise HTTPException(503, reason)
    await run_in_threadpool(accounts.spend, user_id, "summary", settings.daily_summary_limit)
    try:
        return await summarizer.summarize(app.state.http, req)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach the AI service. Try again.")
