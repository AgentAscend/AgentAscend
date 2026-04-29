import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.db.session import init_db
from backend.app.routes import auth, creator, health, jobs, marketplace, payments, platform, pumpfun_payments, telegram, tools, users
from backend.app.services.payment_config import validate_payment_startup_env

app = FastAPI()


def _cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    return [
        "https://agentascend.ai",
        "https://www.agentascend.ai",
        "http://localhost:3000",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_origin_regex=os.getenv("CORS_ALLOWED_ORIGIN_REGEX") or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    )
    return response


def _map_error_code(status_code: int, message: str) -> str:
    normalized = (message or "").lower()
    if "not allowed from status" in normalized:
        return "transition_invalid"
    if status_code == 400:
        return "validation_error"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    return "unknown"


@app.exception_handler(HTTPException)
def http_exception_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        payload = detail
    else:
        message = str(detail)
        payload = {
            "code": _map_error_code(exc.status_code, message),
            "message": message,
        }
    return JSONResponse(status_code=exc.status_code, content={"error": payload})


@app.on_event("startup")
def startup():
    validate_payment_startup_env()
    init_db()


app.include_router(auth.router)
app.include_router(health.router)
app.include_router(payments.router)
app.include_router(pumpfun_payments.router)
app.include_router(tools.router)
app.include_router(marketplace.router)
app.include_router(creator.router)
app.include_router(platform.router)
app.include_router(users.router)
app.include_router(telegram.router)
app.include_router(jobs.router)
