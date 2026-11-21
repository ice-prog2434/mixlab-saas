import hashlib, secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, User, PasswordReset
from .security import hash_pw, rate_limit
from . import mailer

router = APIRouter()

def _h(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()

class Forgot(BaseModel):
    email: EmailStr

class Reset(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)

@router.post("/auth/forgot", dependencies=[Depends(rate_limit)])
def forgot(b: Forgot, bg: BackgroundTasks, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == b.email.lower()).first()
    if u and not u.suspended:
        token = secrets.token_urlsafe(32)
        db.add(PasswordReset(user_id=u.id, token_hash=_h(token),
                             expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_minutes)))
        db.commit()
        link = f"{settings.app_url}/?reset={token}"
        bg.add_task(mailer.send_mail, u.email, "MixLab AI : nouveau mot de passe",
                    f"Salut {u.name},\n\nPour choisir un nouveau mot de passe (lien valable {settings.reset_minutes} min) :\n{link}\n\n"
                    "Si tu n’as rien demandé, ignore ce message.")
    return {"ok": True}  # même réponse que l'e-mail existe ou non

@router.post("/auth/reset", dependencies=[Depends(rate_limit)])
def reset(b: Reset, db: Session = Depends(get_db)):
    r = db.query(PasswordReset).filter(PasswordReset.token_hash == _h(b.token)).first()
    if not r or r.used or r.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Lien invalide ou expiré")
    u = db.get(User, r.user_id)
    u.password_hash = hash_pw(b.password)
    r.used = True
    for o in db.query(PasswordReset).filter(PasswordReset.user_id == u.id, PasswordReset.used == False):  # noqa: E712
        o.used = True
    db.commit()
    return {"ok": True}
