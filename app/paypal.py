"""Abonnements PayPal (API Billing Subscriptions). Le statut n'est jamais cru sur la simple redirection :
il est relu côté serveur chez PayPal, et le webhook est vérifié par PayPal avant d'être pris en compte."""
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, User, PaypalEvent
from .security import current_user

router = APIRouter()

def configured() -> bool:
    return bool(settings.paypal_client_id and settings.paypal_secret and settings.paypal_plan_id)

def _base() -> str:
    return "https://api-m.paypal.com" if settings.paypal_env == "live" else "https://api-m.sandbox.paypal.com"

def _call(method: str, path: str, **kw):
    try:
        t = httpx.post(_base() + "/v1/oauth2/token", data={"grant_type": "client_credentials"},
                       auth=(settings.paypal_client_id, settings.paypal_secret), timeout=20)
        t.raise_for_status()
        r = httpx.request(method, _base() + path, headers={"Authorization": "Bearer " + t.json()["access_token"]},
                          timeout=20, **kw)
        r.raise_for_status()
    except httpx.HTTPError as e:
        print("PayPal erreur:", e, flush=True)
        raise HTTPException(502, "PayPal est indisponible ou a refusé la demande")
    return r.json() if r.content else {}

def _is_active(u: User) -> bool:
    return u.sub_status in ("active", "trialing")

@router.post("/billing/paypal/subscribe")
def subscribe(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not configured():
        raise HTTPException(503, "PayPal n’est pas configuré")
    if _is_active(u):
        raise HTTPException(409, "Tu as déjà un abonnement actif")
    r = _call("POST", "/v1/billing/subscriptions", json={
        "plan_id": settings.paypal_plan_id, "custom_id": str(u.id),
        "subscriber": {"email_address": u.email},
        "application_context": {"brand_name": "MixLab AI", "locale": "fr-FR", "user_action": "SUBSCRIBE_NOW",
                                "return_url": f"{settings.app_url}/?paypal=ok", "cancel_url": f"{settings.app_url}/?paypal=cancel"}})
    u.paypal_subscription_id = r["id"]
    db.commit()
    link = next((l["href"] for l in r.get("links", []) if l.get("rel") == "approve"), None)
    if not link:
        raise HTTPException(502, "Réponse PayPal inattendue")
    return {"url": link}

@router.post("/billing/paypal/confirm")
def confirm(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Appelé au retour de PayPal : relit l'état réel de l'abonnement chez PayPal."""
    if not u.paypal_subscription_id:
        raise HTTPException(400, "Aucun abonnement PayPal en cours")
    s = _call("GET", f"/v1/billing/subscriptions/{u.paypal_subscription_id}")
    if s.get("custom_id") != str(u.id):
        raise HTTPException(403, "Abonnement non lié à ce compte")
    u.sub_status = s["status"].lower()
    u.sub_provider = "paypal"
    db.commit()
    return {"status": u.sub_status}

@router.post("/billing/paypal/cancel")
def cancel(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not u.paypal_subscription_id or u.sub_provider != "paypal":
        raise HTTPException(400, "Aucun abonnement PayPal à annuler")
    _call("POST", f"/v1/billing/subscriptions/{u.paypal_subscription_id}/cancel", json={"reason": "Annulation par l'utilisateur"})
    u.sub_status = "cancelled"
    db.commit()
    return {"status": u.sub_status}

@router.post("/billing/paypal/webhook")
async def webhook(req: Request, db: Session = Depends(get_db)):
    if not (configured() and settings.paypal_webhook_id):
        raise HTTPException(503, "Webhook PayPal non configuré")
    raw = await req.body()
    try:
        event = json.loads(raw)
        h = req.headers
        v = _call("POST", "/v1/notifications/verify-webhook-signature", json={
            "auth_algo": h["paypal-auth-algo"], "cert_url": h["paypal-cert-url"],
            "transmission_id": h["paypal-transmission-id"], "transmission_sig": h["paypal-transmission-sig"],
            "transmission_time": h["paypal-transmission-time"], "webhook_id": settings.paypal_webhook_id,
            "webhook_event": event})
    except (KeyError, ValueError):
        raise HTTPException(400, "Requête invalide")
    if v.get("verification_status") != "SUCCESS":
        raise HTTPException(400, "Signature invalide")
    if db.get(PaypalEvent, event["id"]):
        return {"ok": True}
    db.add(PaypalEvent(id=event["id"]))
    res = event.get("resource", {})
    if event.get("event_type", "").startswith("BILLING.SUBSCRIPTION.") and res.get("id"):
        u = db.query(User).filter(User.paypal_subscription_id == res["id"]).first()
        if u and res.get("status"):
            u.sub_status = res["status"].lower()  # active, suspended, cancelled, expired...
            u.sub_provider = "paypal"
    db.commit()
    return {"ok": True}
