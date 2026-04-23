from fastapi import FastAPI

from backend.app.routes import health, payments, tools

app = FastAPI()

app.include_router(health.router)
app.include_router(payments.router)
app.include_router(tools.router)
