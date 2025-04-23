from fastapi import FastAPI, File, UploadFile, Request, Depends, status, HTTPException, Query
from typing import List, Optional, Callable
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from tournament import run_tournament
import os
import subprocess
import uuid
import docker
from pathlib import Path
from starlette.middleware.sessions import SessionMiddleware
from oauth_routes import router as auth_router
from auth import require_user, get_current_user
from auth import init_oauth
from dotenv import load_dotenv
import logging
import secrets
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text
from fastapi import Request, Depends
from fastapi import FastAPI, APIRouter
from database import engine, Base, get_db
import models
from routes import tournaments, users, bots, matches
import traceback


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file

# Initialize OAuth
oauth = init_oauth()

def create_tables():
    Base.metadata.create_all(bind=engine)

# Create FastAPI app with explicit root_path to handle URL normalization
app = FastAPI(root_path="")

# Add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path
        }
    )

# Call this function when starting the app
create_tables()

# Define BYPASS_AUTH global variable
BYPASS_AUTH = os.getenv('BYPASS_AUTH', 'false').lower() == 'true'

v2_router = APIRouter(prefix="/v2")

# Include your route modules in the v2_router
v2_router.include_router(users.router)
v2_router.include_router(bots.router)
v2_router.include_router(matches.router)
v2_router.include_router(tournaments.router)

app.include_router(v2_router)

# Generate a strong secret key if not provided
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = secrets.token_hex(32)
    logger.warning(f"No SECRET_KEY found in environment. Generated random key: {secret_key}")

# Add a robust debug endpoint to check the exact URL and route matching
@app.get("/debug/url")
async def debug_url(request: Request):
    """Debug endpoint to check URL and route matching"""
    try:
        # Safely extract headers
        headers_dict = {}
        try:
            headers_dict = dict(request.headers)
        except Exception as e:
            headers_dict = {"error": f"Could not extract headers: {str(e)}"}

        # Safely extract query params
        query_params = {}
        try:
            query_params = dict(request.query_params)
        except Exception as e:
            query_params = {"error": f"Could not extract query params: {str(e)}"}

        # Build response with error handling for each component
        response_data = {
            "url": str(request.url),
            "path": request.url.path,
            "raw_path": "unknown",
            "headers": headers_dict,
            "query_params": query_params,
        }

        # Try to add additional data with error handling
        try:
            response_data["raw_path"] = request.scope.get("raw_path", b"").decode()
        except Exception as e:
            response_data["raw_path_error"] = str(e)

        try:
            response_data["route"] = str(request.scope.get("route"))
        except Exception as e:
            response_data["route_error"] = str(e)

        try:
            endpoint = request.scope.get("endpoint")
            response_data["endpoint"] = endpoint.__name__ if endpoint else None
        except Exception as e:
            response_data["endpoint_error"] = str(e)

        try:
            response_data["app_root_path"] = request.scope.get("root_path", "")
        except Exception as e:
            response_data["app_root_path_error"] = str(e)

        return response_data
    except Exception as e:
        # Catch-all error handler
        logger.error(f"Error in debug_url endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error in debug endpoint",
                "message": str(e),
                "url": str(request.url) if request else "unknown"
            }
        )

# Add a rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit_per_minute=60):
        super().__init__(app)
        self.rate_limit = rate_limit_per_minute
        self.requests = {}

    async def dispatch(self, request, call_next):
        # Get client IP
        client_ip = request.client.host
        current_time = time.time()

        # Clean up old entries
        self.requests = {ip: times for ip, times in self.requests.items()
                        if any(t > current_time - 60 for t in times)}

        # Initialize if needed
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Check rate limit
        if len(self.requests[client_ip]) >= self.rate_limit:
            oldest_allowed_time = current_time - 60
            if all(t > oldest_allowed_time for t in self.requests[client_ip]):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many requests", "message": "Please try again later"}
                )

        # Add current request time
        self.requests[client_ip].append(current_time)

        # Process the request
        return await call_next(request)

# Add a session timeout middleware
class SessionTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds=1800):  # 30 minutes = 1800 seconds
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        logger.info(f"Session timeout set to {timeout_seconds} seconds ({timeout_seconds/60} minutes)")

    async def dispatch(self, request, call_next):
        # Skip for non-HTTP requests
        if request.scope["type"] != "http":
            return await call_next(request)

        # Skip for login and logout routes
        if request.url.path.startswith('/auth/login') or request.url.path.startswith('/auth/logout'):
            return await call_next(request)

        # Check if user is authenticated
        if "session" in request.scope and 'user' in request.session:
            # Check if last_activity timestamp exists
            if 'last_activity' not in request.session:
                request.session['last_activity'] = time.time()
                logger.debug("Initializing last_activity timestamp")

            # Check if session has expired
            last_activity = request.session.get('last_activity', 0)
            current_time = time.time()
            elapsed_time = current_time - last_activity

            # Log session activity for debugging
            if request.url.path.startswith('/api/') or request.url.path.startswith('/auth/'):
                logger.debug(f"Session activity: {elapsed_time:.2f} seconds elapsed, timeout at {self.timeout_seconds} seconds")

            if elapsed_time > self.timeout_seconds:
                # Session expired, log the user out
                user_email = request.session.get('user', {}).get('email', 'unknown')
                logger.info(f"Session expired for user {user_email} after {elapsed_time:.2f} seconds (timeout: {self.timeout_seconds})")

                # Save the frontend URL before clearing the session
                frontend_url = request.session.get('frontend_url')

                # Create a new session with only the expired flag
                # This effectively invalidates the old session
                for key in list(request.session.keys()):
                    request.session.pop(key, None)

                # Set a flag to indicate session timeout
                request.session['session_expired'] = True
                request.session['timeout_time'] = current_time

                # Restore the frontend URL
                if frontend_url:
                    request.session['frontend_url'] = frontend_url

                # Only redirect if it's not an API call
                if not request.url.path.startswith('/api/') and not request.url.path.startswith('/auth/'):
                    logger.info(f"Redirecting to login page due to session timeout")
                    return RedirectResponse(
                        url="/auth/login?reason=timeout",
                        status_code=status.HTTP_303_SEE_OTHER
                    )
                else:
                    # For API calls, return a JSON response
                    return JSONResponse(
                        status_code=401,
                        content={
                            "authenticated": False,
                            "reason": "timeout",
                            "message": "Your session has expired. Please log in again."
                        }
                    )
            else:
                # Update last activity timestamp
                request.session['last_activity'] = current_time

        # Continue with the request
        response = await call_next(request)

        # For API responses, check if we need to add a header for session expiration
        if "session" in request.scope and 'last_activity' in request.session:
            last_activity = request.session.get('last_activity', 0)
            current_time = time.time()
            remaining = max(0, self.timeout_seconds - (current_time - last_activity))

            # Add a header with the remaining session time
            if isinstance(response, (JSONResponse, RedirectResponse)):
                response.headers["X-Session-Remaining"] = str(int(remaining))

        return response

# Add this class definition after the existing middleware classes but before adding any middleware to the app
class NormalizePathMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        logger.info("NormalizePathMiddleware initialized")

    async def dispatch(self, request, call_next):
        # Normalize path to remove double slashes
        if '//' in request.url.path:
            path = request.url.path
            while '//' in path:
                path = path.replace('//', '/')

            # Log the normalization
            logger.info(f"Normalizing path: {request.url.path} -> {path}")

            # IMPORTANT: Instead of redirecting, modify the request path in-place
            # This preserves all cookies, headers, and session data
            request.scope["path"] = path

            # Update the raw_path as well
            request.scope["raw_path"] = path.encode("utf-8")

            logger.info(f"Modified request path in-place instead of redirecting")

        # Continue with the request
        return await call_next(request)

# Update the CORS middleware configuration to allow dynamic origins
def get_allowed_origins():
    """Get allowed origins from environment or use defaults"""
    # Get from environment variable if available
    env_origins = os.getenv('ALLOWED_ORIGINS')
    if env_origins:
        origins = [origin.strip() for origin in env_origins.split(',')]
        logger.info(f"Using origins from environment: {origins}")
        return origins

    default_origins = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
        "https://battleshiptournament.vercel.app",  # Ensure this is included
        os.getenv('FRONTEND_URL', 'https://battleshiptournament.vercel.app')
    ]
    logger.info(f"Using default origins: {default_origins}")
    return default_origins

# Add a debug endpoint to check CORS configuration
@app.get("/debug/cors")
async def debug_cors(request: Request):
    """Debug endpoint to check CORS configuration"""
    try:
        # Get all headers
        headers = {k: v for k, v in request.headers.items()}

        # Get CORS-related headers
        cors_headers = {
            "origin": request.headers.get("origin"),
            "referer": request.headers.get("referer"),
            "host": request.headers.get("host"),
        }

        # Get allowed origins
        allowed_origins = get_allowed_origins()

        return {
            "message": "CORS debug information",
            "cors_headers": cors_headers,
            "all_headers": headers,
            "allowed_origins": allowed_origins,
            "request_url": str(request.url),
            "base_url": str(request.base_url),
        }
    except Exception as e:
        logger.error(f"Error in CORS debug: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "CORS debug failed", "message": str(e)}
        )

# Add a debug endpoint to log cookies and headers
@app.get("/debug/cookies")
async def debug_cookies(request: Request):
    """Debug endpoint to check cookies and headers"""
    try:
        # Get all cookies
        cookies = request.cookies

        # Get all headers
        headers = {k: v for k, v in request.headers.items()}

        # Get session data if available
        session_data = {}
        if "session" in request.scope:
            session_data = {k: v for k, v in request.session.items()}

        return {
            "cookies": cookies,
            "headers": headers,
            "session_data": session_data,
            "has_session": "session" in request.scope,
            "session_cookie_name": "battleship_session",
            "session_cookie_present": "battleship_session" in cookies
        }
    except Exception as e:
        logger.error(f"Error in debug-cookies: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Debug cookies failed", "message": str(e)}
        )

# Update the middleware order - add NormalizePathMiddleware first
app.add_middleware(NormalizePathMiddleware)

# Then add the other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel app domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Session-Remaining", "X-Session-Status"],
)

# Add the rate limiting middleware
app.add_middleware(RateLimitMiddleware, rate_limit_per_minute=120)  # 2 requests per second

# IMPORTANT: Add session middleware BEFORE the session timeout middleware
# This ensures the session is available when the timeout middleware runs
# Set session timeout to 30 minutes (1800 seconds)
SESSION_TIMEOUT = 1800  # 30 minutes in seconds
# Update the session middleware configuration for cross-origin cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    session_cookie="battleship_session",
    max_age=SESSION_TIMEOUT,  # 30 minutes
    same_site="none",  # CRITICAL: Change from "lax" to "none" to allow cross-site requests
    https_only=True,  # CRITICAL: Must be True for SameSite=None to work in production
)

# Add the session timeout middleware with the same timeout value
app.add_middleware(SessionTimeoutMiddleware, timeout_seconds=SESSION_TIMEOUT)

# Directory to save uploaded Python files
UPLOAD_DIR = "./uploads/"

# Ensure the upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Include the auth router
app.include_router(auth_router)


# Add direct routes for session invalidation to ensure they're accessible
@app.get("/api/invalidate-session")
@app.post("/api/invalidate-session")
async def api_invalidate_session(request: Request):
    """Invalidate the current session without redirecting (API version)"""
    try:
        # Get user info for logging
        user_email = request.session.get('user', {}).get('email', 'unknown')
        logger.info(f"API: Invalidating session for user {user_email}")

        # Clear the entire session
        for key in list(request.session.keys()):
            request.session.pop(key, None)

        # Set the expired flag
        request.session['session_expired'] = True
        request.session['timeout_time'] = time.time()

        return {
            "success": True,
            "message": "Session invalidated successfully"
        }
    except Exception as e:
        logger.error(f"Error in API invalidate-session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Session invalidation failed", "message": str(e)}
        )

# Modified authentication dependency that can be bypassed
async def auth_required(
    request: Request,
    bypass: bool = Query(False, description="Set to true to bypass authentication (only works if BYPASS_AUTH is enabled)")
):
    """
    Dependency to check if a user is authenticated
    Redirects to login if not authenticated
    """
    # user_data = {
    #     "id": "cb37c794-bfa3-4e37-86db-492cd0b6a124",
    #     "name": "Andrew Boothe",
    #     "email": "atboothe@crimson.ua.edu",
    #     "provider": "azure_ad",
    #     "university": "University of Alabama"
    # }
    # return user_data
    # Check for session expiration first
    if request.session.get('session_expired'):
        logger.info(f"Expired session detected for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"X-Session-Status": "expired"}
        )

    user = request.session.get('user')
    if not user:
        # If not authenticated, redirect to login
        logger.info(f"Unauthenticated access attempt to {request.url.path}, redirecting to login")
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/auth/login"},
            detail="Authentication required"
        )
    return user

@app.get("/debug/ping")
async def ping():
    """Simple ping endpoint for debugging connectivity"""
    return {"status": "ok", "message": "API is reachable"}

@app.get("/debug/auth-check")
async def auth_check(request: Request):
    """Debug endpoint to check authentication state"""
    try:
        # Check if session exists
        session_exists = "session" in request.scope

        # Get all cookies
        cookies = request.cookies

        # Get session data if available
        session_data = {}
        if session_exists:
            session_data = {k: v for k, v in request.session.items()}

        # Check if user is authenticated
        user = None
        if session_exists:
            user = request.session.get('user')

        # Calculate remaining session time if applicable
        remaining_time = None
        if session_exists and 'last_activity' in request.session:
            last_activity = request.session.get('last_activity', 0)
            elapsed = time.time() - last_activity
            remaining_time = max(0, SESSION_TIMEOUT - elapsed)

        # Check if session has expired
        session_expired = request.session.get('session_expired', False)

        # Get frontend URL
        frontend_url = request.session.get('frontend_url', 'Not set')

        # Get request headers for debugging
        headers = {k: v for k, v in request.headers.items()}

        return {
            "session_exists": session_exists,
            "cookies": cookies,
            "session_data": session_data,
            "authenticated": user is not None,
            "user": user,
            "session_remaining_seconds": remaining_time,
            "session_timeout_seconds": SESSION_TIMEOUT,
            "session_timeout_minutes": SESSION_TIMEOUT / 60,
            "session_expired": session_expired,
            "current_time": time.time(),
            "frontend_url": frontend_url,
            "request_headers": headers,
            "bypass_auth_enabled": BYPASS_AUTH
        }
    except Exception as e:
        logger.error(f"Error in auth-check: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Auth check failed", "message": str(e)}
        )

# Debug endpoint to simulate session timeout
@app.post("/debug/force-timeout")
@app.get("/debug/force-timeout")
async def force_timeout(request: Request):
    """Force a session timeout for testing"""
    try:
        if "session" in request.scope and 'user' in request.session:
            user_email = request.session.get('user', {}).get('email', 'unknown')
            logger.info(f"Forcing session timeout for user {user_email}")

            # Save the user info temporarily
            user_info = request.session.get('user')
            frontend_url = request.session.get('frontend_url')

            # Clear the entire session
            for key in list(request.session.keys()):
                request.session.pop(key, None)

            # Set the expired flag
            request.session['session_expired'] = True
            request.session['timeout_time'] = time.time()

            # Restore the frontend URL
            if frontend_url:
                request.session['frontend_url'] = frontend_url

            return {
                "success": True,
                "message": "Session forcibly expired",
                "user": user_info
            }
        else:
            return {
                "success": False,
                "message": "No active session to expire"
            }
    except Exception as e:
        logger.error(f"Error in force-timeout: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Force timeout failed", "message": str(e)}
        )

# Add a simple test route
@app.get("/test")
async def test(user=Depends(auth_required)):
    return {"message": "API is working", "user": user}

@app.get("/")
async def hello(user=Depends(auth_required)):
    # User is already authenticated due to the dependency
    return {"message": "Hello World", "user": user}

@app.post("/tournament/")
async def upload_tournament_files(request: Request, user=Depends(auth_required)):
    form = await request.form()
    bot_files = []
    for key in form.keys():
        if key.startswith('file'):
            file = form[key]

            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())

            bot_files.append(file.filename)


    rankings = run_tournament(bot_files,3)
    return {"rankings": rankings}

@app.post("/upload/")
async def upload_files(request: Request, user=Depends(auth_required)):
    form = await request.form()

    for key in form.keys():
        if key.startswith('file'):
            file = form[key]

            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)

            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())


    return {"message": "Files uploaded successfully"}

@app.post("/play/")
async def play_two_bots(file1: UploadFile, file2: UploadFile, user=Depends(auth_required)):
    bot_files = []

    # Save both files
    for file in [file1, file2]:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        bot_files.append(file.filename)

    #print(bot_files)

    # Run the tournament with the uploaded files
    rankings = run_tournament(bot_files,3)
    print(rankings)
    return {"rankings": rankings}

# Add OAuth-specific endpoints
@app.get("/api/protected-resource")
async def protected_resource(user=Depends(auth_required)):
    return {"message": "This is a protected resource", "user": user}

# Add a public endpoint to check if user is authenticated
@app.get("/api/auth-status")
async def auth_status(request: Request):
    # If authentication bypass is enabled, return a mock authenticated user
    if BYPASS_AUTH:
        return {
            "authenticated": True,
            "user": {
                'id': 'dev-user-id',
                'name': 'Development User',
                'email': 'dev@example.com',
                'provider': 'dev',
                'university': 'Development University'
            },
            "session_remaining_seconds": 1800,
            "session_timeout_minutes": 30,
            "bypass_enabled": True
        }

    # Check if session has expired flag
    if request.session.get('session_expired'):
        return {
            "authenticated": False,
            "reason": "timeout",
            "message": "Your session has expired. Please log in again."
        }

    user = request.session.get('user')
    if user:
        # Calculate remaining session time
        last_activity = request.session.get('last_activity', time.time())
        elapsed = time.time() - last_activity
        remaining_seconds = max(0, SESSION_TIMEOUT - elapsed)

        return {
            "authenticated": True,
            "user": user,
            "session_remaining_seconds": remaining_seconds,
            "session_timeout_minutes": SESSION_TIMEOUT / 60
        }
    return {"authenticated": False}

# Add an endpoint to extend the session
@app.post("/api/extend-session")
async def extend_session(request: Request):
    """Extend the user's session timeout"""
    # If authentication bypass is enabled, just return success
    if BYPASS_AUTH:
        return {
            "success": True,
            "message": "Session extended (bypass mode)",
            "session_timeout_minutes": SESSION_TIMEOUT / 60,
            "bypass_enabled": True
        }

    # Check if session has expired
    if request.session.get('session_expired'):
        return JSONResponse(
            status_code=401,
            content={
                "error": "Session expired",
                "reason": "timeout",
                "message": "Your session has expired. Please log in again."
            }
        )

    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "Not authenticated", "message": "You must be logged in to extend your session"}
        )

    # Update the last activity timestamp
    request.session['last_activity'] = time.time()

    return {
        "success": True,
        "message": "Session extended",
        "session_timeout_minutes": SESSION_TIMEOUT / 60
    }

# Add a debug endpoint to toggle authentication bypass
@app.get("/debug/toggle-auth-bypass")
async def toggle_auth_bypass(enable: bool = Query(..., description="Set to true to enable auth bypass, false to disable")):
    """Toggle authentication bypass for development purposes"""
    global BYPASS_AUTH

    # Only allow this in development environments
    if os.getenv('ENVIRONMENT', 'development') == 'production':
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "message": "This endpoint is not available in production"}
        )

    previous_state = BYPASS_AUTH
    BYPASS_AUTH = enable

    if enable:
        logger.warning("⚠️ AUTHENTICATION BYPASS ENABLED - DO NOT USE IN PRODUCTION ⚠️")
    else:
        logger.info("Authentication bypass disabled")

    return {
        "success": True,
        "previous_state": previous_state,
        "current_state": BYPASS_AUTH,
        "message": f"Authentication bypass {'enabled' if enable else 'disabled'}"
    }