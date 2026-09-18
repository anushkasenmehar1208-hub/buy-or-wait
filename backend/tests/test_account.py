"""Account feature tests — profile update, avatar storage, account deletion.

Ownership: every route derives the target user from the JWT only.
"""
import struct
import zlib

from app.models import FinancialProfile, User, UserAvatar


def _png_bytes() -> bytes:
    """1x1 transparent PNG (real magic bytes for the validator)."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + chunk(b"IEND", b"")


# ------------------------------------------------------------------ profile
def test_update_display_name(client, auth_headers):
    headers, _ = auth_headers
    resp = client.put("/api/account/profile", json={"full_name": "  Ada Lovelace "},
                      headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Ada Lovelace"


def test_update_name_requires_auth(client):
    assert client.put("/api/account/profile", json={"full_name": "X"}).status_code == 401


def test_update_name_rejects_blank(client, auth_headers):
    headers, _ = auth_headers
    resp = client.put("/api/account/profile", json={"full_name": "   "}, headers=headers)
    assert resp.status_code == 422


def test_me_reflects_name_change(client, auth_headers):
    headers, payload = auth_headers
    client.put("/api/account/profile", json={"full_name": "Renamed"}, headers=headers)
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["full_name"] == "Renamed"
    assert me["email"] == payload["email"]


# ------------------------------------------------------------------ avatar
def test_avatar_roundtrip(client, auth_headers):
    headers, _ = auth_headers
    me0 = client.get("/api/auth/me", headers=headers).json()
    assert me0["avatar_url"] is None

    upload = client.put("/api/account/avatar", files={
        "file": ("me.png", _png_bytes(), "image/png")}, headers=headers)
    assert upload.status_code == 200, upload.text
    assert upload.json()["avatar_url"]

    serve = client.get("/api/account/avatar", headers=headers)
    assert serve.status_code == 200
    assert serve.headers["content-type"] == "image/png"
    assert serve.content.startswith(b"\x89PNG")

    me1 = client.get("/api/auth/me", headers=headers).json()
    assert me1["avatar_url"] and me1["avatar_url"].startswith("/api/account/avatar?user_id=")


def test_avatar_rejects_disallowed_type(client, auth_headers):
    headers, _ = auth_headers
    resp = client.put("/api/account/avatar", files={
        "file": ("e.gif", b"GIF89a" + b"\x00" * 8, "image/gif")}, headers=headers)
    assert resp.status_code == 422
    assert "Unsupported image type" in resp.json()["error"]["message"]


def test_avatar_rejects_fake_image(client, auth_headers):
    """Declared PNG but garbage magic bytes → rejected by the byte check."""
    headers, _ = auth_headers
    resp = client.put("/api/account/avatar", files={
        "file": ("fake.png", b"this is not an image at all", "image/png")}, headers=headers)
    assert resp.status_code == 422
    assert "does not look like a valid image" in resp.json()["error"]["message"]


def test_avatar_rejects_oversize(client, auth_headers):
    headers, _ = auth_headers
    big = _png_bytes() + b"\x00" * (3 * 1024 * 1024)
    resp = client.put("/api/account/avatar", files={
        "file": ("big.png", big, "image/png")}, headers=headers)
    assert resp.status_code == 422
    assert "too large" in resp.json()["error"]["message"]


def test_avatar_requires_auth(client):
    resp = client.put("/api/account/avatar", files={
        "file": ("me.png", _png_bytes(), "image/png")})
    assert resp.status_code == 401


def test_avatar_delete_returns_to_initials(client, auth_headers):
    headers, _ = auth_headers
    client.put("/api/account/avatar", files={
        "file": ("me.png", _png_bytes(), "image/png")}, headers=headers)
    gone = client.delete("/api/account/avatar", headers=headers)
    assert gone.status_code == 200
    assert gone.json()["avatar_url"] is None
    assert client.get("/api/account/avatar", headers=headers).status_code == 404


def test_avatar_reupload_replaces_bytes(client, auth_headers):
    headers, _ = auth_headers
    client.put("/api/account/avatar", files={
        "file": ("a.png", _png_bytes(), "image/png")}, headers=headers)
    second = client.put("/api/account/avatar", files={
        "file": ("b.png", _png_bytes() + b"x", "image/png")}, headers=headers)
    assert second.status_code == 200
    assert client.get("/api/account/avatar", headers=headers).content.endswith(b"x")


def test_avatar_signature_path_for_img_tags(client, auth_headers):
    """<img> cannot send JWTs; the signed URL must work without any header,
    and must fail closed without a valid signature."""
    headers, _ = auth_headers
    me = client.get("/api/auth/me", headers=headers).json()
    user_id = me["id"]
    client.put("/api/account/avatar", files={
        "file": ("me.png", _png_bytes(), "image/png")}, headers=headers)
    signed_url = client.get("/api/auth/me", headers=headers).json()["avatar_url"]

    ok = client.get(signed_url)  # no Authorization header at all
    assert ok.status_code == 200
    assert ok.content.startswith(b"\x89PNG")

    no_sig = client.get(f"/api/account/avatar?user_id={user_id}&v=123")
    assert no_sig.status_code == 401
    bad_sig = client.get(f"/api/account/avatar?user_id={user_id}&v=123&sig=deadbeef")
    assert bad_sig.status_code == 401
    # And a foreign user cannot mint access by guessing ids with any sig.
    forged = client.get(f"/api/account/avatar?user_id={'f' * 32}&v=1&sig={signed_url.split('sig=')[1]}")
    assert forged.status_code == 401


# ------------------------------------------------------------------ deletion
def test_delete_account_cascades_owned_data(client, db, auth_headers):
    headers, payload = auth_headers
    me = client.get("/api/auth/me", headers=headers).json()
    user_id = me["id"]
    # Give the user a financial profile + an avatar so cascades are exercised.
    assert client.post("/api/profile", json={
        "currency": "USD", "current_balance": "500", "minimum_safe_balance": "50",
    }, headers=headers).status_code == 201
    client.put("/api/account/avatar", files={
        "file": ("me.png", _png_bytes(), "image/png")}, headers=headers)

    assert client.delete("/api/account", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401

    assert db.query(User).filter(User.id == user_id).one_or_none() is None
    assert db.query(UserAvatar).filter(UserAvatar.user_id == user_id).one_or_none() is None
    profile = db.query(FinancialProfile).filter(
        FinancialProfile.user_id == user_id).one_or_none()
    assert profile is None


def test_delete_account_only_deletes_self(client, db, auth_headers):
    headers, _ = auth_headers
    # A second, unrelated user must survive.
    r2 = client.post("/api/auth/signup", json={
        "email": "bystander@example.com", "password": "Sup3rSecret!", "full_name": "Other"})
    other_token = r2.json()["access_token"]

    assert client.delete("/api/account", headers=headers).status_code == 204

    me_other = client.get("/api/auth/me",
                          headers={"Authorization": f"Bearer {other_token}"})
    assert me_other.status_code == 200
    assert me_other.json()["email"] == "bystander@example.com"
    assert db.query(User).filter(User.email == "bystander@example.com").one()


def test_delete_account_requires_auth(client):
    assert client.delete("/api/account").status_code == 401


def test_deleted_account_cannot_sign_back_in(client, auth_headers):
    headers, payload = auth_headers
    client.delete("/api/account", headers=headers)
    again = client.post("/api/auth/signin", json={
        "email": payload["email"], "password": payload["password"]})
    assert again.status_code == 401
