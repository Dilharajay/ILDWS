"""ILEWS backend – standard API response envelope and error helpers."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    *,
    meta: dict | None = None,
    status_code: int = 200,
) -> dict:
    """Build the standard success envelope."""
    body: dict[str, Any] = {
        "status": "success",
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if meta is not None:
        body["meta"] = meta
    return body


def error_body(code: str, message: str, *, details: dict | None = None) -> dict:
    """Build the standard error envelope (dict only, for raising)."""
    body: dict[str, Any] = {
        "status": "error",
        "error": {"code": code, "message": message},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        body["error"]["details"] = details
    return body


def paginated_meta(*, page: int, per_page: int, total: int) -> dict:
    """Build pagination metadata."""
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, -(-total // per_page)),  # ceil division
    }


# ---------------------------------------------------------------------------
# Exception handlers to register on the FastAPI app
# ---------------------------------------------------------------------------

async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap FastAPI HTTPExceptions in the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(
            code=f"ERR_{exc.status_code}",
            message=str(exc.detail),
        ),
        headers=getattr(exc, "headers", None),
    )


async def generic_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content=error_body(
            code="ERR_INTERNAL",
            message="An unexpected error occurred.",
        ),
    )
