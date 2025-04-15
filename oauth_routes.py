from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from starlette.responses import RedirectResponse, JSONResponse
import os
import logging
import time
from auth import oauth, require_user, get_current_user, is_alabama_email

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a router for auth routes
router = APIRouter(prefix="/auth")

@router.get("/login")
async def login(request: Request, redirect_uri: str = Query(None), reason: str = Query(None)):
    """Redirect to University of Alabama login"""
    # Clear any expired session flag
    if 'session_expired' in request.session:
        logger.info("Clearing expired session flag during login")
        for key in list(request.session.keys()):
            request.session.pop(key, None)

    # Log the reason if provided
    if reason:
        logger.info(f"Login requested with reason: {reason}")

    # Redirect directly to Azure AD login
    return RedirectResponse(url="/auth/login/azure")

@router.get("/login/azure")
async def azure_login(request: Request):
    """Azure AD OAuth login for University of Alabama"""
    try:
        # Clear any existing session data
        for key in list(request.session.keys()):
            request.session.pop(key, None)

        # Get the redirect URI for after authentication
        # Use absolute URL to ensure correct callback URL
        redirect_uri = str(request.base_url)[:-1] + "/auth/login/callback"
        logger.info(f"Redirecting to Azure with callback URL: {redirect_uri}")

        # Make sure the session is working by setting a test value
        request.session['test_key'] = 'test_value'
        logger.info(f"Session test: {request.session.get('test_key')}")

        # Use a custom state parameter that we'll verify in the callback
        state = os.urandom(16).hex()
        request.session['oauth_state'] = state
        logger.info(f"Setting OAuth state: {state}")

        return await oauth.azure.authorize_redirect(request, redirect_uri, state=state)
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
            # Clear any existing session data first
            for key in list(request.session.keys()):
                request.session.pop(key, None)

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

        # Redirect to frontend after successful login
        # Use localhost:3000 for local development
        frontend_url = "http://localhost:3000"
        logger.info(f"Redirecting to frontend: {frontend_url}/login-success")

        # Create a response with a cookie
        response = RedirectResponse(url=f"{frontend_url}/login-success")
        response.set_cookie(
            key="auth_status",
            value="authenticated",
            httponly=False,  # Allow JavaScript access
            max_age=1800,    # 30 minutes
            samesite="lax",  # Prevents CSRF
            secure=False     # Set to True in production with HTTPS
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

        # Clear the entire session
        for key in list(request.session.keys()):
            request.session.pop(key, None)

        # Redirect to frontend after logout
        # Use localhost:3000 for local development
        frontend_url = "http://localhost:3000"

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

@router.get("/me")
async def me(request: Request):
    """Get current user info"""
    try:
        # Check if session has expired flag
        if request.session.get('session_expired'):
            logger.info("Expired session detected in /me endpoint")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
                headers={"X-Session-Status": "expired"}
            )

        user = get_current_user(request)
        if user:
            # Update last activity timestamp
            request.session['last_activity'] = time.time()
            return user
        else:
            # Return 401 instead of using the dependency to avoid redirects
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    except Exception as e:
        logger.error(f"Error in /me endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user information"
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
