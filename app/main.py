import json, os, shutil, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import stripe
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import Base, engine, get_db, SessionLocal, User, Project, StripeEvent
from .security import hash_pw, check_pw, make_token, current_user, require_access, has_access, rate_limit
from . import reset as reset_mod, paypal as paypal_mod
from . import audio

Base.metadata.create_all(engine)  # en prod : utiliser Alembic
app = FastAPI(title="MixLab AI")
app.include_router(reset_mod.router)
app.include_router(paypal_mod.router)
app.add_middleware(CORSMiddleware, allow_origins=[settings.app_url], allow_methods=["*"], allow_headers=["*"])
STORE = Path(settings.storage_dir)

# ---------- Auth ----------
class Register(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

def user_out(u: User):
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
            "trial_ends_at": u.trial_ends_at, "sub_status": u.sub_status, "provider": u.sub_provider, "has_access": has_access(u)}

@app.post("/auth/register", status_code=201, dependencies=[Depends(rate_limit)])
def register(b: Register, db: Session = Depends(get_db)):
    u = User(email=b.email.lower(), name=b.name.strip(), password_hash=hash_pw(b.password),
             trial_ends_at=datetime.now(timezone.utc) + timedelta(days=settings.trial_days))
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cet e-mail est déjà utilisé")
    return {"token": make_token(u.id), "user": user_out(u)}

@app.post("/auth/login", dependencies=[Depends(rate_limit)])
def login(b: Login, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == b.email.lower()).first()
    if not u or not check_pw(b.password, u.password_hash):
        raise HTTPException(401, "E-mail ou mot de passe incorrect")
    return {"token": make_token(u.id), "user": user_out(u)}

@app.get("/me")
def me(u: User = Depends(current_user)):
    return user_out(u)

# ---------- Projets ----------
def project_out(p: Project):
    return {"id": p.id, "name": p.name, "style": p.style, "status": p.status, "error": p.error,
            "created_at": p.created_at, "settings": json.loads(p.settings_json)}

async def save_upload(f: UploadFile, dest: Path):
    ext = Path(f.filename or "").suffix.lower()
    if ext not in settings.allowed_ext:
        raise HTTPException(400, "Format non pris en charge (WAV, MP3, FLAC)")
    limit = settings.max_upload_mb * 1024 * 1024
    size = 0
    dest = dest.with_suffix(ext)
    with open(dest, "wb") as out:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close(); dest.unlink(missing_ok=True)
                raise HTTPException(413, f"Fichier trop lourd (max {settings.max_upload_mb} Mo)")
            out.write(chunk)
    try:
        info = audio.probe(str(dest))
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "Fichier audio invalide")
    if info["duration"] > settings.max_duration_sec:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Durée max : {settings.max_duration_sec // 60} min")
    return str(dest)

def run_job(pid: int):
    db = SessionLocal()
    out = None

    try:
        p = db.get(Project, pid)

        if p is None:
            return

        p.status = "processing"
        p.error = None
        db.commit()

        out = str(Path(p.voice_path).parent / "mix.mp3")

        audio.render(
            p.voice_path,
            p.instru_path,
            out,
            p.style,
            json.loads(p.settings_json)
        )

        # Vérifier que le projet existe toujours.
        db.expire_all()
        p = db.get(Project, pid)

        if p is None:
            Path(out).unlink(missing_ok=True)
            return

        p.output_path = out
        p.status = "done"
        db.commit()

    except Exception as e:
        db.rollback()

        if out:
            Path(out).unlink(missing_ok=True)

        p = db.get(Project, pid)

        if p is not None:
            p.status = "error"
            p.error = "Le traitement a échoué"
            db.commit()

        print("job error", e)

    finally:
        db.close()
@app.get("/styles")
def styles():
    return [{"key": k, "reverb": v["reverb"], "delay": v["delay"]} for k, v in audio.STYLES.items()]

@app.get("/config")
def public_config():
    return {"stripe": bool(settings.stripe_secret_key and settings.stripe_price_id), "paypal": paypal_mod.configured()}

@app.get("/health")
def health():
    return {"ok": True}

class Rename(BaseModel):
    name: str = Field(min_length=1, max_length=120)

@app.patch("/projects/{pid}")
def rename_project(pid: int, b: Rename, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = own(db, u, pid); p.name = b.name.strip(); db.commit()
    return project_out(p)

@app.post("/projects", status_code=202)
async def create_project(bg: BackgroundTasks, name: str = Form(...), style: str = Form(...),
                         options: str = Form("{}"), voice: UploadFile = File(...), instru: UploadFile = File(...),
                         u: User = Depends(require_access), db: Session = Depends(get_db)):
    if style not in audio.STYLES:
        raise HTTPException(400, "Style inconnu")
    try:
        opts = json.loads(options)
    except ValueError:
        raise HTTPException(400, "Réglages invalides")
    running = db.query(Project).filter(Project.user_id == u.id, Project.status.in_(["pending", "processing"])).count()
    if running >= 2:  # anti double soumission
        raise HTTPException(429, "Un traitement est déjà en cours")
    folder = STORE / str(u.id) / uuid.uuid4().hex
    folder.mkdir(parents=True)
    try:
        vp = await save_upload(voice, folder / "voice")
        ip = await save_upload(instru, folder / "instru")
    except HTTPException:
        shutil.rmtree(folder, ignore_errors=True); raise
    p = Project(user_id=u.id, name=name[:120], style=style, settings_json=json.dumps(opts), voice_path=vp, instru_path=ip)
    db.add(p); db.commit()
    bg.add_task(run_job, p.id)
    return project_out(p)

def own(db, u, pid) -> Project:
    p = db.get(Project, pid)
    if not p or p.user_id != u.id:
        raise HTTPException(404, "Projet introuvable")
    return p

@app.get("/projects")
def list_projects(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [project_out(p) for p in db.query(Project).filter(Project.user_id == u.id).order_by(Project.id.desc())]

@app.get("/projects/{pid}")
def get_project(pid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return project_out(own(db, u, pid))

@app.get("/projects/{pid}/audio/{kind}")
def get_audio(pid: int, kind: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = own(db, u, pid)
    path = {"mix": p.output_path, "voice": p.voice_path, "instru": p.instru_path}.get(kind)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Fichier indisponible")
    return FileResponse(path, filename=f"{p.name}-{kind}{Path(path).suffix}")

@app.delete("/projects/{pid}", status_code=204)
def delete_project(pid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = own(db, u, pid)
    shutil.rmtree(Path(p.voice_path).parent, ignore_errors=True)  # suppression réelle du stockage
    db.delete(p); db.commit()

# ---------- Paiement Stripe ----------
@app.post("/billing/checkout")
def checkout(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not (settings.stripe_secret_key and settings.stripe_price_id):
        raise HTTPException(503, "Paiement non configuré")
    if u.sub_status in ("active", "trialing"):
        raise HTTPException(409, "Tu as déjà un abonnement actif")
    stripe.api_key = settings.stripe_secret_key
    if not u.stripe_customer_id:
        c = stripe.Customer.create(email=u.email, metadata={"user_id": str(u.id)})
        u.stripe_customer_id = c.id; db.commit()
    s = stripe.checkout.Session.create(
        mode="subscription", customer=u.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=f"{settings.app_url}/?ok=1", cancel_url=f"{settings.app_url}/",
        client_reference_id=str(u.id))
    return {"url": s.url}

@app.post("/billing/portal")
def portal(u: User = Depends(current_user)):
    if not (settings.stripe_secret_key and u.stripe_customer_id):
        raise HTTPException(400, "Aucun abonnement à gérer")
    stripe.api_key = settings.stripe_secret_key
    s = stripe.billing_portal.Session.create(customer=u.stripe_customer_id, return_url=settings.app_url)
    return {"url": s.url}

@app.post("/billing/webhook")
async def webhook(req: Request, db: Session = Depends(get_db)):
    payload = await req.body()
    try:
        ev = stripe.Webhook.construct_event(payload, req.headers.get("stripe-signature", ""), settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(400, "Signature invalide")
    if db.get(StripeEvent, ev["id"]):
        return {"ok": True}  # déjà traité
    db.add(StripeEvent(id=ev["id"]))
    obj = ev["data"]["object"]
    if ev["type"] in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        u = db.query(User).filter(User.stripe_customer_id == obj["customer"]).first()
        if u:
            u.sub_status = obj["status"]  # active, trialing, past_due, canceled...
            u.sub_provider = "stripe"
    db.commit()
    return {"ok": True}

# Frontend statique servi par l'app (doit rester en dernier)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True), name="static")
