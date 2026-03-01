"""ILEWS ML Inference Service – FastAPI application."""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from loguru import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.config import settings
from app.model_loader import load_model, reload_model, get_model_info
from app.scheduler import (
    run_scheduler,
    get_last_inference_times,
    score_all_slopes,
)
from app.scorer import score_slope

import asyncio

_http_client = None
_scheduler_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load model and start scheduler."""
    global _http_client, _scheduler_task

    _http_client = httpx.AsyncClient(timeout=30)

    # Load model (non-blocking — service starts even if model unavailable)
    await load_model()

    # Start scheduler
    _scheduler_task = asyncio.create_task(run_scheduler(_http_client))
    logger.info("ML Inference Service started")

    yield

    # Cleanup
    _scheduler_task.cancel()
    await _http_client.aclose()
    logger.info("ML Inference Service stopped")


app = FastAPI(
    title="ILEWS ML Inference Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    model_info = get_model_info()
    return {
        "status": "success",
        "data": {
            "service": "ml-inference",
            "status": "healthy",
            "model_loaded": model_info["loaded"],
        },
    }


@app.get("/status")
async def status():
    """Status endpoint showing model and inference state."""
    model_info = get_model_info()
    inference_times = get_last_inference_times()

    return {
        "status": "success",
        "data": {
            "model": model_info,
            "last_inference": inference_times,
            "score_interval_minutes": settings.SCORE_INTERVAL_MINUTES,
        },
    }


@app.post("/score/{slope_id}")
async def score_slope_endpoint(slope_id: str):
    """Trigger immediate re-scoring for a slope."""
    if _http_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    result = await score_slope(_http_client, slope_id)

    if "error" in result:
        return {
            "status": "error",
            "error": {
                "code": result["error"],
                "message": f"Scoring failed for {slope_id}",
            },
        }

    return {"status": "success", "data": result}


@app.post("/score-all")
async def score_all_endpoint():
    """Trigger immediate scoring of all active slopes."""
    if _http_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    result = await score_all_slopes(_http_client)
    return {"status": "success", "data": result}


@app.post("/reload-model")
async def reload_model_endpoint():
    """Hot-reload the model without restart."""
    success = await reload_model()
    if success:
        return {
            "status": "success",
            "data": {"message": "Model reloaded", **get_model_info()},
        }
    return {
        "status": "error",
        "error": {"code": "reload_failed", "message": "Model reload failed"},
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
