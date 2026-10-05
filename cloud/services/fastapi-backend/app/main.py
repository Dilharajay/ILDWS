"""ILEWS backend – FastAPI application entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as redis

from app.config import settings
from app.database import async_session_factory
from app.routers import auth
from app.routers import slopes as slopes_router
from app.routers import nodes as nodes_router
from app.routers import readings as readings_router
from app.routers import risk as risk_router
from app.routers import alerts as alerts_router
from app.routers import map as map_router
from app.routers import users as users_router
from app.routers import system as system_router
from app.routers import reports as reports_router
from app.routers import websocket as ws_router
from app.utils.metrics import router as metrics_router, MetricsMiddleware
from app.utils.response import (
    http_exception_handler,
    generic_exception_handler,
)

app = FastAPI(
    title="ILEWS API",
    description="Intelligent Landslide Early Warning System – backend API",
    version="0.1.0",
)

# --- Exception handlers (standard error envelope) ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS – locked down unless overridden
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://dashboard.ilews.gov"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)


app.include_router(auth.router)
app.include_router(slopes_router.router)
app.include_router(nodes_router.router)
app.include_router(readings_router.router)
app.include_router(risk_router.router)
app.include_router(alerts_router.router)
app.include_router(map_router.router)
app.include_router(users_router.router)
app.include_router(system_router.router)
app.include_router(reports_router.router)
app.include_router(ws_router.router)
app.include_router(metrics_router)


@app.get("/health")
async def health_check():
    checks = {"api": "ok"}
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    
    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(checks, status_code=status_code)
