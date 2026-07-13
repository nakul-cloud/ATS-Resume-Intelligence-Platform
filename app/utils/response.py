from typing import Any
from fastapi.responses import JSONResponse

def success_response(data: Any, message: str = "Success", status_code: int = 200) -> JSONResponse:
    """Standard success JSON response wrapper"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data
        }
    )

def error_response(message: str, code: str = "ERROR", status_code: int = 400, details: Any = None, errors: Any = None) -> JSONResponse:
    """Standard error JSON response wrapper"""
    content = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details is not None:
        content["error"]["details"] = details
    if errors is not None:
        content["error"]["errors"] = errors
    return JSONResponse(
        status_code=status_code,
        content=content
    )
