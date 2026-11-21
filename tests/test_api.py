import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["RATE_LIMIT_PER_MIN"] = "1000"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

c = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def reg(email):
    return c.post("/auth/register", json={"email": email, "name": "Beat", "password": "motdepasse1"})

def test_register_gives_trial():
    r = reg("a@test.com"); assert r.status_code == 201
    assert r.json()["user"]["has_access"] is True

def test_duplicate_email():
    reg("b@test.com"); assert reg("b@test.com").status_code == 409

def test_login_wrong_password():
    reg("c@test.com")
    assert c.post("/auth/login", json={"email": "c@test.com", "password": "mauvais123"}).status_code == 401

def test_projects_need_auth():
    assert c.get("/projects").status_code == 401

def test_user_cannot_read_others_project():
    t1 = reg("d@test.com").json()["token"]; t2 = reg("e@test.com").json()["token"]
    assert c.get("/projects/1", headers={"Authorization": f"Bearer {t2}"}).status_code == 404

def test_webhook_bad_signature():
    assert c.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "x"}).status_code == 400

def test_forgot_unknown_email_is_silent():
    assert c.post("/auth/forgot", json={"email": "inconnu@test.com"}).json() == {"ok": True}

def test_reset_flow(monkeypatch):
    sent = {}
    from app import reset as r
    monkeypatch.setattr(r.mailer, "send_mail", lambda to, subj, body: sent.update(body=body))
    reg("f@test.com")
    c.post("/auth/forgot", json={"email": "f@test.com"})
    token = sent["body"].split("?reset=")[1].split()[0]
    assert c.post("/auth/reset", json={"token": token, "password": "nouveaumdp1"}).status_code == 200
    assert c.post("/auth/reset", json={"token": token, "password": "autremdp12"}).status_code == 400  # usage unique
    assert c.post("/auth/login", json={"email": "f@test.com", "password": "nouveaumdp1"}).status_code == 200

def test_reset_bad_token():
    assert c.post("/auth/reset", json={"token": "faux", "password": "motdepasse1"}).status_code == 400

def test_paypal_not_configured():
    t = reg("g@test.com").json()["token"]
    assert c.post("/billing/paypal/subscribe", headers={"Authorization": f"Bearer {t}"}).status_code == 503
