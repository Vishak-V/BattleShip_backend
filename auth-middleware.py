from fastapi import Request, HTTPException, status
from starlette.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """
    Middleware to check if a user is authenticated for all routes except auth routes
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope)
        path = request.url.path

        # Skip authentication check for auth routes and static files
        if path.startswith("/auth/") or path == "/api/auth-status" or path.startswith("/static/"):
            return await self.app(scope, receive, send)

        # Check if user is authenticated
        user = request.session.get('user')

        if not user and path != "/":
            # If not authenticated and not trying to access the home page, redirect to login
            logger.info(f"Unauthenticated access attempt to {path}, redirecting to login")
            response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
            await response(scope, receive, send)
            return

        # Continue with the request
        await self.app(scope, receive, send)

