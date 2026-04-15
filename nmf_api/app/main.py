from __future__ import annotations

from fastapi import FastAPI

from .routes import health, notifications, offers, recommendations
from .services.model_service import startup_model
from .state import STATE

app = FastAPI(title="Recomendaciones NMF", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    startup_model(STATE)


app.include_router(health.router)
app.include_router(recommendations.router)
app.include_router(offers.router)
app.include_router(notifications.router)
