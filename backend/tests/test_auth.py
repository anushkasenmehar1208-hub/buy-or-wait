"""Auth + authorization tests."""
from sqlalchemy.orm import sessionmaker

from app.models import FinancialProfile, User
from app.repositories.user_repository import UserRepository


def test_signup_success(client):
    resp = client.post("/api/auth/signup", json={
        "email": "new-user@example.com", "password": "Sup3rSecret!", "full_name": "New User",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_signup_duplicate_email_409(client):
    payload = {"email": "dup@example.com", "password": "Sup3rSecret!"}
    assert client.post("/api/auth/signup", json=payload).status_code == 201
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 409


def test_signup_weak_password_422(client):
    resp = client.post("/api/auth/signup", json={"email": "weak@example.com",
                                                 "password": "short"})
    assert resp.status_code == 422


def test_signin_ok_and_wrong_password(client, auth_headers):
    headers, payload = auth_headers
    ok = client.post("/api/auth/signin", json={"email": payload["email"],
                                               "password": payload["password"]})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/api/auth/signin", json={"email": payload["email"],
                                                "password": "WrongPass1"})
    assert bad.status_code == 401
    assert "Invalid email or password" in bad.json()["error"]["message"]


def test_signin_unknown_email_same_error(client):
    resp = client.post("/api/auth/signin", json={"email": "ghost@example.com",
                                                 "password": "Whatever1"})
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["error"]["message"]


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client, auth_headers):
    headers, payload = auth_headers
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == payload["email"]


def test_passwords_are_hashed(client, db, auth_headers):
    headers, payload = auth_headers
    user = db.query(User).filter(User.email == payload["email"]).one()
    assert user.password_hash != payload["password"]
    assert user.password_hash.startswith("$2")


def test_garbage_token_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
