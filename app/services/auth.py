from datetime import timedelta

from app.config.security import create_access_token
from app.config.settings import settings
from app.exceptions.custom_exceptions import AuthError


class AuthService:
    @classmethod
    async def authenticate_and_generate_token(
        cls, username: str, password: str
    ) -> dict:
        """
        Validates username and password and generates a JWT access token.
        """
        if (
            username != settings.recruiter_email
            or password != settings.recruiter_password
        ):
            raise AuthError("Invalid username or password credentials")

        # Generate JWT Token payload
        expires_delta = timedelta(minutes=settings.jwt_expires_in_minutes)
        token_data = {"sub": username, "role": "recruiter"}

        access_token = create_access_token(data=token_data, expires_delta=expires_delta)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": settings.jwt_expires_in_minutes,
        }
