import logging
import os
import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import jwt

from database import get_db
from models import User, PersonaEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    client_kwargs={
        'scope': 'openid email profile'
    }
)

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-for-dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

def create_jwt_token(user_id: str, persona: str | None) -> str:
    payload = {
        "sub": user_id,
        "persona": persona,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@router.get("/google")
async def login_google(request: Request, redirect_to: str = "/generate"):
    request.session['redirect_to'] = redirect_to
    redirect_uri = str(request.url_for('auth_callback'))
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.exception("Google OAuth callback failed during token exchange")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {e}")

    user_info = token.get('userinfo')
    if not user_info:
        try:
            user_info = oauth.google.parse_id_token(token)
        except Exception as e:
            logger.warning("Failed to parse id_token, attempting userinfo endpoint: %s", e)
            try:
                user_info = await oauth.google.userinfo(token=token)
            except Exception as e2:
                logger.exception("Google OAuth callback failed while fetching userinfo")
                raise HTTPException(status_code=400, detail=f"Authentication failed: {e2}")

    if not user_info:
        raise HTTPException(status_code=400, detail="No user info returned")

    email = getattr(user_info, "email", None) or user_info.get("email")
    google_id = getattr(user_info, "sub", None) or user_info.get("sub")
    name = getattr(user_info, "name", None) or user_info.get("name")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Incomplete user info returned")

    result = await db.execute(select(User).filter(User.google_id == google_id))
    user = result.scalars().first()
    
    if not user:
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        if user:
            user.google_id = google_id
            user.last_sign_in_at = datetime.datetime.now().replace(tzinfo=None)
            await db.commit()
    
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.last_sign_in_at = datetime.datetime.now().replace(tzinfo=None)
        await db.commit()

    jwt_token = create_jwt_token(str(user.id), user.persona.value if user.persona else None)
    
    intent_redirect = request.session.pop('redirect_to', "/generate")
    redirect_url = f"{FRONTEND_URL}/auth/callback?token={jwt_token}&redirect_to={intent_redirect}"
    return RedirectResponse(url=redirect_url)
