from fastapi import FastAPI

from backend.app.db.session import init_db
from backend.app.routes import health, payments, tools, users

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()


app.include_router(health.router)
app.include_router(payments.router)
app.include_router(tools.router)
app.include_router(users.router)
