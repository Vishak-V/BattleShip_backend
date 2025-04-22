from fastapi import APIRouter, Request, Depends, HTTPException, Query, status, Header
from starlette.responses import RedirectResponse, JSONResponse
import os
import logging
import time
from auth import oauth, require_user, get_current_user, is_alabama_email
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a router for auth routes
router = APIRouter(prefix="/auth")

# Add a debug endpoint to check the exact URL and route matching
@router.get("/debug-url")
async def debug_url(request: Request):
    """Debug endpoint to check URL and route matching"""
    return {
        "url": str(request.url),
        "path": request.url.path,
        "raw_path": request.scope.get("raw_path", b"").decode(),
        "route": request.scope.get("route"),
        "endpoint": request.scope.get("endpoint", {}).__name__ if request.scope.get("endpoint") else None,
        "app_root_path": request.scope.get("root_path", ""),
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
    }

@router.get("/debug-session")
async def debug_session(request: Request):
    """Debug endpoint to check session data"""
    return {
        "session_exists": "session" in request.scope,
        "session_data": {k: v for k, v in request.session.items()} if "session" in request.scope else {},
        "cookies": request.cookies,
        "headers": {k: v for k, v in request.headers.items()},
        "user": request.session.get("user")
    }

@router.get("/bypass-auth")
async def bypass_auth(request: Request):
    """Temporary endpoint to bypass authentication for testing"""
    # Create a mock user
    mock_user = {
        'id': 'mock-user-id',
        'name': 'Mock User',
        'email': 'mock@crimson.ua.edu',
        'provider': 'mock',
        'university': 'University of Alabama'
    }

    # Store in session
    request.session['user'] = mock_user
    request.session['last_activity'] = time.time()

    logger.info(f"Bypass auth: Created mock user in session: {mock_user}")
    logger.info(f"Session data after bypass: {dict(request.session)}")

    return {
        "success": True,
        "message": "Authentication bypassed for testing",
        "user": mock_user,
        "session_data": dict(request.session)
    }

@router.get("/me")
async def me(request: Request):
    """Get current user info"""
    try:
        # Add detailed logging
        logger.info(f"ME endpoint called with session: {dict(request.session) if 'session' in request.scope else 'No session'}")
        logger.info(f"Cookies: {request.cookies}")
        logger.info(f"User in session: {request.session.get('user')}")

        # Check if session has expired flag
        if request.session.get('session_expired'):
            logger.info("Expired session detected in /me endpoint")
            raise HTTPException(
                status_code=401,
                detail="Session expired",
                headers={"X-Session-Status": "expired"}
            )

        user = get_current_user(request)
        if user:
            # Update last activity timestamp
            request.session['last_activity'] = time.time()
            logger.info(f"Returning user from session: {user}")
            return user
        else:
            # Return 401 instead of using the dependency to avoid redirects
            logger.info("No user found in session, returning 401")
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
    except HTTPException:
        # Re-raise HTTPExceptions without modifying them
        raise
    except Exception as e:
        logger.error(f"Error in /me endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving user information"
        )

# Add routes with and without trailing slashes to handle both cases
@router.get("/login")
@router.get("/login/")
async def login(request: Request, redirect_uri: str = Query(None), reason: str = Query(None), frontend_url: str = Query(None)):
    """Redirect to University of Alabama login"""
    logger.info(f"Login request received with params: redirect_uri={redirect_uri}, reason={reason}, frontend_url={frontend_url}")
    logger.info(f"Full URL: {request.url}")
    logger.info(f"Query params: {request.query_params}")

    # Store the frontend URL in the session for later use
    if frontend_url:
        request.session['frontend_url'] = frontend_url
        logger.info(f"Stored frontend URL from param: {frontend_url}")
    elif redirect_uri:
        # Extract origin from redirect_uri
        from urllib.parse import urlparse
        parsed_url = urlparse(redirect_uri)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        request.session['frontend_url'] = origin
        request.session['redirect_uri'] = redirect_uri
        logger.info(f"Stored frontend URL from redirect_uri: {origin}")
    else:
        # Try to determine frontend URL from request
        detected_url = get_frontend_url(request)
        request.session['frontend_url'] = detected_url
        logger.info(f"Detected and stored frontend URL: {detected_url}")

    # Store the redirect_uri if provided
    if redirect_uri:
        request.session['redirect_uri'] = redirect_uri
        logger.info(f"Stored redirect_uri: {redirect_uri}")

    # Clear any expired session flag
    if 'session_expired' in request.session:
        logger.info("Clearing expired session flag during login")
        for key in list(request.session.keys()):
            if key != 'frontend_url' and key != 'redirect_uri':
                request.session.pop(key, None)

    # Log the reason if provided
    if reason:
        logger.info(f"Login requested with reason: {reason}")

    # Redirect directly to Azure AD login
    return RedirectResponse(url="/auth/login/azure")

def get_frontend_url(request: Request, referer: Optional[str] = Header(None)) -> str:
    """
    Determine the frontend URL dynamically based on request information

    This function tries multiple methods to determine the frontend URL:
    1. Check for a frontend_url query parameter
    2. Check the redirect_uri query parameter
    3. Check the referer header
    4. Check the origin header
    5. Fall back to environment variable or default
    """
    # First check if it's explicitly provided in query params
    frontend_url = request.query_params.get('frontend_url')
    if frontend_url:
        logger.info(f"Using frontend URL from query param: {frontend_url}")
        return frontend_url

    # Check redirect_uri parameter (common in OAuth flows)
    redirect_uri = request.query_params.get('redirect_uri')
    if redirect_uri:
        # Extract origin from redirect_uri
        from urllib.parse import urlparse
        parsed_url = urlparse(redirect_uri)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.info(f"Using frontend URL from redirect_uri: {origin}")
        return origin

    # Check referer header
    if referer:
        # Extract origin from referer (e.g., http://localhost:3000/some/path -> http://localhost:3000)
        from urllib.parse import urlparse
        parsed_url = urlparse(referer)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.info(f"Using frontend URL from referer: {origin}")
        return origin

    # Check origin header
    origin = request.headers.get('origin')
    if origin:
        logger.info(f"Using frontend URL from origin header: {origin}")
        return origin

    # Fall back to environment variable or default
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    logger.info(f"Using default frontend URL: {frontend_url}")
    return frontend_url

@router.get("/login/azure")
async def azure_login(request: Request):
    """Azure AD OAuth login for University of Alabama"""
    try:
        # Preserve important session values
        frontend_url = request.session.get('frontend_url')
        redirect_uri = request.session.get('redirect_uri')

        logger.info(f"Azure login with frontend_url={frontend_url}, redirect_uri={redirect_uri}")

        # Clear any existing session data except what we want to keep
        preserved_data = {}
        if frontend_url:
            preserved_data['frontend_url'] = frontend_url
        if redirect_uri:
            preserved_data['redirect_uri'] = redirect_uri

        for key in list(request.session.keys()):
            request.session.pop(key, None)

        # Restore preserved data
        for key, value in preserved_data.items():
            request.session[key] = value

        # Get the redirect URI for after authentication
        # Use absolute URL to ensure correct callback URL
        callback_uri = str(request.base_url).rstrip('/') + "/auth/login/callback"
        logger.info(f"Redirecting to Azure with callback URL: {callback_uri}")

        # Make sure the session is working by setting a test value
        request.session['test_key'] = 'test_value'
        logger.info(f"Session test: {request.session.get('test_key')}")

        # Use a custom state parameter that we'll verify in the callback
        state = os.urandom(16).hex()
        request.session['oauth_state'] = state
        logger.info(f"Setting OAuth state: {state}")

        return await oauth.azure.authorize_redirect(request, callback_uri, state=state)
    except Exception as e:
        logger.error(f"Error in azure_login: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Authentication failed", "message": str(e)}
        )

@router.get("/login/callback")
async def azure_authorize(request: Request):
    """Azure AD OAuth callback"""
    try:
        logger.info("Received callback from Azure")

        # Log session data for debugging
        logger.info(f"Session test in callback: {request.session.get('test_key')}")
        logger.info(f"OAuth state in session: {request.session.get('oauth_state')}")
        logger.info(f"Query parameters: {request.query_params}")
        logger.info(f"Frontend URL in session: {request.session.get('frontend_url')}")
        logger.info(f"Redirect URI in session: {request.session.get('redirect_uri')}")

        # Get the token
        try:
            token = await oauth.azure.authorize_access_token(request)
            logger.info("Successfully retrieved access token")
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Authentication failed", "message": f"Token error: {str(e)}"}
            )

        # Get user info from Microsoft Graph API
        try:
            resp = await oauth.azure.get('me', token=token)
            user_info = resp.json()
            logger.info(f"Retrieved user info: {user_info}")
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Authentication failed", "message": f"User info error: {str(e)}"}
            )

        # Verify the email is from University of Alabama
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        logger.info(f"User email: {email}")

        if not is_alabama_email(email):
            logger.warning(f"Non-Alabama email attempted login: {email}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Authentication failed",
                    "message": "You must use a University of Alabama email address to login."
                }
            )

        # Store user info in session
        try:
            # Preserve important session values
            frontend_url = request.session.get('frontend_url')
            redirect_uri = request.session.get('redirect_uri')

            # Clear any existing session data first
            for key in list(request.session.keys()):
                request.session.pop(key, None)

            # Restore important values
            if frontend_url:
                request.session['frontend_url'] = frontend_url
            if redirect_uri:
                request.session['redirect_uri'] = redirect_uri

            request.session['user'] = {
                'id': user_info['id'],
                'name': user_info.get('displayName', ''),
                'email': email,
                'provider': 'azure_ad',
                'university': 'University of Alabama'
            }
            # Initialize last activity timestamp for session timeout
            request.session['last_activity'] = time.time()
            logger.info("User info stored in session")
        except Exception as e:
            logger.error(f"Error storing user in session: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Authentication failed", "message": f"Session error: {str(e)}"}
            )

        # Use the stored redirect_uri if available, otherwise construct from frontend_url
        final_redirect_url = None
        if redirect_uri:
            final_redirect_url = redirect_uri
            logger.info(f"Using stored redirect_uri for final redirect: {final_redirect_url}")
        elif frontend_url:
            final_redirect_url = f"{frontend_url}/login-success"
            logger.info(f"Constructed redirect URL from frontend_url: {final_redirect_url}")
        else:
            # Fall back to environment variable or default
            default_frontend = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            final_redirect_url = f"{default_frontend}/login-success"
            logger.info(f"Using default redirect URL: {final_redirect_url}")

        # Create a response with a cookie
        # In the azure_authorize function (callback)
        # When creating the response:
        response = RedirectResponse(url=final_redirect_url)
        response.set_cookie(
            key="auth_status",
            value="authenticated",
            httponly=False,  # Allow JavaScript access
            max_age=1800,    # 30 minutes
            samesite="none",  # CRITICAL: Allow cross-site
            secure=True      # CRITICAL: Required for SameSite=None
        )
        return response

    except Exception as e:
        logger.error(f"Unhandled error in callback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Authentication failed", "message": str(e)}
        )

@router.get("/logout")
async def logout(request: Request, reason: str = Query(None)):
    """Logout route"""
    try:
        # Log the reason if provided
        if reason:
            logger.info(f"Logout requested with reason: {reason}")

        # Get user info for logging
        user_email = request.session.get('user', {}).get('email', 'unknown')
        logger.info(f"Logging out user {user_email}")

        # Get the frontend URL before clearing the session
        frontend_url = request.session.get('frontend_url') or get_frontend_url(request)

        # Clear the entire session
        for key in list(request.session.keys()):
            request.session.pop(key, None)

        # If the reason is timeout, redirect to login with timeout reason
        if reason == "timeout":
            return RedirectResponse(url=f"{frontend_url}/login?reason=timeout")

        return RedirectResponse(url=f"{frontend_url}/login")
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Logout failed", "message": str(e)}
        )

@router.get("/status")
async def status(request: Request):
    """Check authentication status"""
    try:
        # Check if session has expired flag
        if request.session.get('session_expired'):
            logger.info("Expired session detected in /status endpoint")
            return {
                "authenticated": False,
                "reason": "timeout",
                "message": "Your session has expired. Please log in again."
            }

        user = get_current_user(request)
        if user:
            # Update last activity timestamp
            request.session['last_activity'] = time.time()

            # Calculate remaining session time
            last_activity = request.session.get('last_activity', time.time())
            elapsed = time.time() - last_activity
            remaining_seconds = max(0, 1800 - elapsed)  # 30 minutes in seconds

            return {
                "authenticated": True,
                "user": user,
                "session_remaining_seconds": remaining_seconds,
                "session_timeout_minutes": 30
            }
        else:
            return {"authenticated": False}
    except Exception as e:
        logger.error(f"Error in status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Status check failed", "message": str(e)}
        )

@router.get("/test-session")
async def test_session(request: Request):
    """Test route to verify session functionality"""
    try:
        # Set a value in the session
        request.session['test_time'] = str(time.time())

        # Get all values from the session
        session_data = {k: v for k, v in request.session.items()}

        return {
            "message": "Session test",
            "session_data": session_data
        }
    except Exception as e:
        logger.error(f"Error in test-session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Session test failed", "message": str(e)}
        )

@router.post("/refresh")
async def refresh_session(request: Request):
    """Refresh the user's session to prevent timeout"""
    try:
        # Check if session has expired flag
        if request.session.get('session_expired'):
            logger.info("Expired session detected in /refresh endpoint")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Session expired",
                    "reason": "timeout",
                    "message": "Your session has expired. Please log in again."
                }
            )

        user = get_current_user(request)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated", "message": "You must be logged in to refresh your session"}
            )

        # Update the last activity timestamp
        request.session['last_activity'] = time.time()
        logger.debug(f"Session refreshed for user {user.get('email')}")

        return {
            "success": True,
            "message": "Session refreshed",
            "session_timeout_minutes": 30
        }
    except Exception as e:
        logger.error(f"Error in refresh-session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Session refresh failed", "message": str(e)}
        )

# Add both GET and POST methods for the invalidate-session endpoint
@router.get("/invalidate-session")
@router.post("/invalidate-session")
async def invalidate_session(request: Request):
    """Invalidate the current session without redirecting"""
    try:
        # Get user info for logging
        user_email = request.session.get('user', {}).get('email', 'unknown')
        logger.info(f"Invalidating session for user {user_email}")

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
        logger.error(f"Error in invalidate-session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Session invalidation failed", "message": str(e)}
        )

# Add a dedicated endpoint for force-timeout that's separate from the debug endpoint
@router.get("/force-timeout")
@router.post("/force-timeout")
async def force_timeout(request: Request):
    """Force a session timeout for testing"""
    try:
        if "session" in request.scope and 'user' in request.session:
            user_email = request.session.get('user', {}).get('email', 'unknown')
            logger.info(f"Forcing session timeout for user {user_email}")

            # Save the user info temporarily
            user_info = request.session.get('user')

            # Clear the entire session
            for key in list(request.session.keys()):
                request.session.pop(key, None)

            # Set the expired flag
            request.session['session_expired'] = True
            request.session['timeout_time'] = time.time()

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
