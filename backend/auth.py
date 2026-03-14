import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, User
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DEV_SECRET = "dev-secret-cambiar-en-produccion"


def _load_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    environment = os.getenv("ENVIRONMENT", "production").strip().lower()

    if secret_key:
        if environment != "development" and len(secret_key) < 32:
            raise RuntimeError("SECRET_KEY debe tener al menos 32 caracteres fuera de desarrollo.")
        return secret_key

    if environment == "development":
        print("⚠ SECRET_KEY no configurado; usando clave temporal solo para desarrollo.")
        return DEFAULT_DEV_SECRET

    raise RuntimeError("SECRET_KEY es obligatorio fuera de desarrollo.")


SECRET_KEY  = _load_secret_key()
ALGORITHM   = "HS256"
TOKEN_HOURS = 24
TOKEN_ISSUER = os.getenv("TOKEN_ISSUER", "sysnergia-api").strip() or "sysnergia-api"

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer(auto_error=False)

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":      str(user_id),
        "username": username,
        "iss":      TOKEN_ISSUER,
        "exp":      now + timedelta(hours=TOKEN_HOURS),
        "iat":      now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token inválido.")

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Credenciales requeridas.",
                            headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token inválido.",
                            headers={"WWW-Authenticate": "Bearer"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Usuario no encontrado o inactivo.")
    return user
