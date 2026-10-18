"""Stable, non-sensitive HTTP error responses for the OOSYS API."""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.errors import ApplicationError


class ErrorDetail(BaseModel):
    """Safe validation detail without rejected input values."""

    location: list[str | int]
    message: str
    code: str


class ErrorBody(BaseModel):
    """Stable error envelope shared by all HTTP error handlers."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Top-level error response contract."""

    error: ErrorBody


def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only safe, stable fields from Pydantic validation errors."""
    return [
        {
            "location": list(error.get("loc", ())),
            "message": "Invalid value.",
            "code": str(error.get("type", "invalid_value")),
        }
        for error in errors
    ]


def install_error_handlers(application: FastAPI) -> None:
    """Install safe handlers for HTTP, validation and unexpected errors."""

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        del request
        if exc.status_code == 404:
            code, message = "not_found", "Resource not found."
        elif exc.status_code == 405:
            code, message = "method_not_allowed", "Method not allowed."
        else:
            code, message = "http_error", "Request could not be completed."
        body = ErrorResponse(error=ErrorBody(code=code, message=message))
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(exclude_none=True),
            headers=exc.headers,
        )

    @application.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        del request
        body = ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(exclude_none=True))

    @application.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request
        body = ErrorResponse(
            error=ErrorBody(
                code="validation_error",
                message="Request validation failed.",
                details=_validation_details(exc.errors()),
            )
        )
        return JSONResponse(status_code=422, content=body.model_dump(exclude_none=True))

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        del request, exc
        body = ErrorResponse(
            error=ErrorBody(
                code="internal_error",
                message="An unexpected error occurred.",
            )
        )
        return JSONResponse(status_code=500, content=body.model_dump(exclude_none=True))
