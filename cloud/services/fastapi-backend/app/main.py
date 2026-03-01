"""ILEWS backend – FastAPI application entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth
from app.routers import slopes as slopes_router
from app.routers import nodes as nodes_router
from app.routers import readings as readings_router
from app.routers import risk as risk_router
from app.routers import alerts as alerts_router
from app.utils.metrics import router as metrics_router
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

# CORS – permissive in development, should be locked down in production
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(auth.router)
app.include_router(slopes_router.router)
app.include_router(nodes_router.router)
app.include_router(readings_router.router)
app.include_router(risk_router.router)
app.include_router(alerts_router.router)
app.include_router(metrics_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
