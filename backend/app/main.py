from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.app.db.session import init_db
from backend.app.routes import creator, health, marketplace, payments, telegram, tools, users

app = FastAPI()


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
    init_db()


app.include_router(health.router)
app.include_router(payments.router)
app.include_router(tools.router)
app.include_router(marketplace.router)
app.include_router(creator.router)
app.include_router(users.router)
app.include_router(telegram.router)
