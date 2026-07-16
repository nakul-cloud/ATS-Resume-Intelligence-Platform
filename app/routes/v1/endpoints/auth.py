from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.exceptions.custom_exceptions import AppError
from app.services.auth import AuthService
from app.utils.response import error_response, success_response

router = APIRouter()

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticates recruiter credentials and returns a JWT access token.
    """
    try:
        data = await AuthService.authenticate_and_generate_token(
            username=form_data.username,
            password=form_data.password
        )
        return success_response(data=data, message="Authentication successful")
    except AppError as e:
        return error_response(message=e.message, code="APP_ERROR", status_code=e.status_code)
    except Exception as e:
        return error_response(
            message="Authentication failed",
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=str(e)
        )
