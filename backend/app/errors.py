"""Consistent JSON error envelope.

Every error response — HTTP errors, request-validation failures, and unexpected
exceptions — is normalised to ``{"error": <human message>, "code": <MACHINE_CODE>}``
with the right status code. The frontend reads ``error`` to show a clean message
instead of dumping a raw response body.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("opd")

# Default machine code per status, used when a raiser doesn't supply its own.
_CODE_FOR_STATUS = {
    400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND",
    409: "CONFLICT", 422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
    500: "INTERNAL_ERROR", 502: "UPSTREAM_ERROR", 503: "SERVICE_UNAVAILABLE",
}


def _envelope(message: str, code: str) -> dict:
    return {"error": message, "code": code}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # A raiser may pass detail as {"message", "code"} to set a specific code,
        # or as a plain string (the common FastAPI form).
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("error") or "Request failed"
            code = detail.get("code") or _CODE_FOR_STATUS.get(exc.status_code, "ERROR")
        else:
            message = str(detail) if detail else "Request failed"
            code = _CODE_FOR_STATUS.get(exc.status_code, "ERROR")
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(message, code),
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        parts: list[str] = []
        for err in exc.errors()[:5]:
            loc = ".".join(str(x) for x in err.get("loc", ())
                           if x not in ("body", "query", "path"))
            msg = err.get("msg", "invalid value")
            parts.append(f"{loc}: {msg}" if loc else msg)
        message = "Request validation failed — " + "; ".join(p for p in parts if p)
        return JSONResponse(status_code=422,
                            content=_envelope(message, "VALIDATION_ERROR"))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side; never leak internals to the client.
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_envelope("An unexpected error occurred. Please try again.",
                              "INTERNAL_ERROR"))
