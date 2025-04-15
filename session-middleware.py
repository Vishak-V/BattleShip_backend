import os
import secrets
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class DebugSessionMiddleware(SessionMiddleware):
    """
    A version of SessionMiddleware that logs session operations for debugging
    """

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Check if the session cookie exists
        session_cookie = request.cookies.get(self.cookie_name)
        logger.info(f"Session cookie exists: {session_cookie is not None}")

        # Call the original middleware
        await super().__call__(scope, receive, send)

def get_session_middleware():
    """
    Create a properly configured session middleware
    """
    # Generate a strong secret key if not provided
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_key = secrets.token_hex(32)
        logger.warning(f"No SECRET_KEY found in environment. Generated random key: {secret_key}")

    # Create the middleware with secure settings
    return DebugSessionMiddleware(
        app=None,  # This will be set when added to the app
        secret_key=secret_key,
        session_cookie="battleship_session",
        max_age=86400,  # 1 day
        same_site="lax",  # Prevents CSRF
        https_only=False,  # Set to True in production with HTTPS
    )

