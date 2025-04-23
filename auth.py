import os
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import JSONResponse
from functools import wraps
from fastapi import Depends, HTTPException, status
from models import User

# Initialize OAuth
oauth = OAuth()

def init_oauth():
    """
    Initialize OAuth for FastAPI and return the oauth object
    """
    # Microsoft Entra ID (Azure AD) OAuth setup for University of Alabama
    tenant_id = os.getenv('AZURE_TENANT_ID')  # University of Alabama tenant ID

    oauth.register(
        name='azure',
        client_id=os.getenv('AZURE_CLIENT_ID'),
        client_secret=os.getenv('AZURE_CLIENT_SECRET'),
        access_token_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
        access_token_params=None,
        authorize_url=f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
        authorize_params=None,
        api_base_url='https://graph.microsoft.com/v1.0/',
        client_kwargs={
            'scope': 'openid email profile User.Read',
            'prompt': 'select_account',  # Forces account selection each time
        },
        server_metadata_url=f'https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration'
    )

    return oauth

async def require_user(request: Request)->User:
    """
    FastAPI dependency to require a logged-in user
    """
    # user_data = {
    #     "id": "cb37c794-bfa3-4e37-86db-492cd0b6a124",
    #     "name": "Andrew Boothe",
    #     "email": "atboothe@crimson.ua.edu",
    #     "oauth_provider": "azure_ad",
    #     "university": "University of Alabama"
    # }
    # return User(**user_data)

    # Check if session has expired
    if request.session.get('session_expired'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"X-Session-Status": "expired"}
        )

    user = request.session.get('user')
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Alias for backward compatibility
login_required = require_user

def get_current_user(request: Request):
    """
    Get user info from session
    """
    return request.session.get('user')

# Alias for backward compatibility
get_user_info = get_current_user

def is_alabama_email(email):
    """
    Check if the email is from University of Alabama
    """
    return email and (email.endswith('@ua.edu') or email.endswith('@crimson.ua.edu'))
