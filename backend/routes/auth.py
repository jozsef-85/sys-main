from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from database import get_db, User
from auth import verify_password, create_token, get_current_user
from security import MemoryRateLimiter, get_client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])

login_limiter = MemoryRateLimiter(
    limit=5,
    window_seconds=15 * 60,
    key_builder=lambda request: f"login:{get_client_ip(request)}",
    detail="Demasiados intentos de inicio de sesión. Intenta nuevamente en unos minutos.",
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

class LoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    username:     str
    message:      str

class UserResponse(BaseModel):
    id:        int
    username:  str
    email:     str
    is_active: bool
    class Config:
        from_attributes = True

@router.post("/login", response_model=LoginResponse, dependencies=[Depends(login_limiter)])
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Credenciales incorrectas.",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada.")
    token = create_token(user.id, user.username)
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "token_type": "bearer",
            "username": user.username, "message": f"Bienvenido, {user.username}."}

@router.get("/me", response_model=UserResponse)
def get_me(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return current_user

@router.post("/logout")
def logout(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Sesión cerrada correctamente."}
