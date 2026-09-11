from fastapi import Request
from fastapi.responses import JSONResponse


def internal_error_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred."
        }
    )