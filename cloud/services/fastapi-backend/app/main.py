"""ILEWS backend – FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="ILEWS API",
    description="Intelligent Landslide Early Warning System – backend API",
    version="0.1.0",
)

# CORS – permissive in development, should be locked down in production
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
