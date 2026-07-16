from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Any | None = None

class ErrorResponseDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None

class APIErrorResponse(BaseModel):
    success: bool = False
    error: ErrorResponseDetail
