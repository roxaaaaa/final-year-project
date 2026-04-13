from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import jwt
from pydantic import BaseModel
import os

from database import get_db
from models import User, PersonaEnum

router = APIRouter(prefix="/api/user", tags=["User"])
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-for-dev")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid token user id")

        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

class PersonaUpdate(BaseModel):
    persona: str

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "persona": user.persona.value if user.persona else None,
        "generations_number": user.generations_number,
    }

@router.post("/persona")
async def set_persona(data: PersonaUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.persona is not None:
        raise HTTPException(status_code=400, detail="Persona already set")
        
    if data.persona not in ['student', 'teacher']:
        raise HTTPException(status_code=400, detail="Invalid persona")
        
    user.persona = PersonaEnum(data.persona)
    await db.commit()
    
    return {"status": "success", "persona": user.persona}
