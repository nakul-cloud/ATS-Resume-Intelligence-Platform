from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class ErrorResponseDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class APIErrorResponse(BaseModel):
    success: bool = False
    error: ErrorResponseDetail
