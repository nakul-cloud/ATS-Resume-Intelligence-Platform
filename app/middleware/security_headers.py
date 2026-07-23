import secure
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

secure_headers = secure.Secure()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        secure_headers.set_headers(response)
        return response
