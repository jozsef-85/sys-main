import os
import aiosmtplib
from email.message import EmailMessage
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from database import get_db, ContactMessage
from auth import get_current_user, User
from dotenv import load_dotenv
from security import MemoryRateLimiter, get_client_ip

load_dotenv()

router = APIRouter(prefix="/api/contact", tags=["contact"])

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "josalejandro@gmail.com")

contact_limiter = MemoryRateLimiter(
    limit=5,
    window_seconds=60 * 60,
    key_builder=lambda request: f"contact:{get_client_ip(request)}",
    detail="Has enviado demasiados mensajes recientemente. Intenta más tarde.",
)

class ContactRequest(BaseModel):
    name:    str = Field(min_length=2, max_length=100)
    email:   EmailStr
    subject: Optional[str] = Field(default="Mensaje desde sysnergia.com", max_length=200)
    message: str = Field(min_length=10, max_length=5000)

class ContactResponse(BaseModel):
    id:      int
    name:    str
    email:   str
    subject: Optional[str]
    message: str
    read:    bool
    class Config:
        from_attributes = True

async def send_notification(data: ContactRequest):
    if not SMTP_USER or not SMTP_PASSWORD:
        return
    msg = EmailMessage()
    msg["From"]    = SMTP_USER
    msg["To"]      = CONTACT_EMAIL
    subject = (data.subject or "Mensaje desde sysnergia.com").replace("\r", " ").replace("\n", " ").strip()
    msg["Subject"] = f"[sysnergia.com] {subject}"
    msg.set_content(f"De: {data.name}\nEmail: {data.email}\n\n{data.message}")
    try:
        await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT,
                              username=SMTP_USER, password=SMTP_PASSWORD, start_tls=True)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

@router.post("", status_code=201, dependencies=[Depends(contact_limiter)])
async def send_message(data: ContactRequest, background: BackgroundTasks, db: Session=Depends(get_db)):
    subject = (data.subject or "Mensaje desde sysnergia.com").strip()
    msg = ContactMessage(name=data.name.strip(), email=str(data.email),
                         subject=subject, message=data.message.strip())
    db.add(msg); db.commit()
    background.add_task(send_notification, data)
    return {"ok": True, "message": "Mensaje recibido."}

@router.get("", response_model=List[ContactResponse])
def list_messages(db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    return db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()

@router.patch("/{msg_id}/read")
def mark_read(msg_id: int, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    msg = db.query(ContactMessage).filter(ContactMessage.id==msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
    msg.read = True; db.commit()
    return {"ok": True}

@router.delete("/{msg_id}", status_code=204)
def delete_message(msg_id: int, db: Session=Depends(get_db), _: User=Depends(get_current_user)):
    msg = db.query(ContactMessage).filter(ContactMessage.id==msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")
    db.delete(msg); db.commit()
