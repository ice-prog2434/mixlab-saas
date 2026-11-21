from datetime import datetime, timedelta, timezone
import bcrypt, jwt
import time, collections
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, User

bearer = HTTPBearer(auto_error=False)

def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def check_pw(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())

def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.secret_key, algorithm="HS256")

def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Connexion requise")
    try:
        uid = int(jwt.decode(cred.credentials, settings.secret_key, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Session invalide ou expirée")
    user = db.get(User, uid)
    if not user or user.suspended:
        raise HTTPException(403, "Compte indisponible")
    return user

def has_access(user: User) -> bool:
    if user.sub_status in ("active", "trialing"):
        return True

    if not user.trial_ends_at:
        return False

    trial_ends_at = user.trial_ends_at

    # SQLite peut retourner une date sans fuseau horaire.
    if trial_ends_at.tzinfo is None:
        trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

    return trial_ends_at > datetime.now(timezone.utc)


def require_access(user: User = Depends(current_user)) -> User:
    if not has_access(user):
        raise HTTPException(402, "Essai terminé : abonne-toi pour continuer")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Réservé aux administrateurs")
    return user


_hits = collections.defaultdict(list)


def rate_limit(req: Request):
    """Limite simple en mémoire (1 processus)."""
    xff = req.headers.get("x-forwarded-for")
    ip = xff.split(",")[-1].strip() if xff else (
        req.client.host if req.client else "?"
    )

    t = time.time()
    h = [x for x in _hits[ip] if t - x < 60]

    if len(h) >= settings.rate_limit_per_min:
        raise HTTPException(429, "Trop de tentatives, réessaie dans une minute")

    h.append(t)
    _hits[ip] = h
