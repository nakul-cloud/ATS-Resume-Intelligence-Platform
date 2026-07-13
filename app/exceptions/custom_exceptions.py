from app.constants.status_code import (
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE_ENTITY,
    HTTP_BAD_GATEWAY,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_UNAUTHORIZED,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_SERVICE_UNAVAILABLE,
)

class AppError(Exception):
    """
    Custom Error Class for Application Errors
    """

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.status = "fail" if str(status_code).startswith("4") else "error"
        self.is_operational = True


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_NOT_FOUND)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_UNPROCESSABLE_ENTITY)


class AIServiceError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_BAD_GATEWAY)


class StorageError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_INTERNAL_SERVER_ERROR)


class AuthError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_UNAUTHORIZED)


class RateLimitError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_TOO_MANY_REQUESTS)


class QdrantError(AppError):
    def __init__(self, message: str):
        super().__init__(message, HTTP_SERVICE_UNAVAILABLE)
