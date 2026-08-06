from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from apps.api.models.response import ErrorResponse

async def global_exception_handler(request: Request, exc: Exception):
    error = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        details=str(exc)
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder(error))

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=exc.errors()
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(error))
