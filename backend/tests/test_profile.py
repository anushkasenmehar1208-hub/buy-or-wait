"""Profile CRUD + ownership + user-data-isolation tests."""
import uuid

from app.models import FinancialProfile, IncomeSource, User
from app.repositories.user_repository import UserRepository


def _register(client):
    suffix = uuid.uuid4().hex[:8]
    payload = {"email": f"iso-{suffix}@example.com", "password": "Sup3rSecret!"}
    resp = client.post("/api/auth/signup", json=payload)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, payload


def _make_profile(client, headers, **overrides):
    payload = {
        "currency": "USD",
        "current_balance": "5000.00",
        "minimum_safe_balance": "1000.00",
        **overrides,
    }
    resp = client.post("/api/profile", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_profile_create_and_get(client, auth_headers):
    headers, _ = auth_headers
    created = _make_profile(client, headers)
    got = client.get("/api/profile", headers=headers)
    assert got.status_code == 200
    assert got.json()["current_balance"] == "5000.00"
    assert got.json()["id"] == created["id"]


def test_profile_get_before_create_returns_204(client, auth_headers):
    headers, _ = auth_headers
    resp = client.get("/api/profile", headers=headers)
    assert resp.status_code == 204


def test_profile_duplicate_create_409(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    resp = client.post("/api/profile", json={
        "currency": "USD", "current_balance": "10.00", "minimum_safe_balance": "0",
    }, headers=headers)
    assert resp.status_code == 409


def test_profile_update_balance(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    resp = client.put("/api/profile", json={
        "currency": "USD", "current_balance": "7000.00", "minimum_safe_balance": "1500.00",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["current_balance"] == "7000.00"
    assert resp.json()["minimum_safe_balance"] == "1500.00"


def test_profile_minimum_above_balance_422(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post("/api/profile", json={
        "currency": "USD", "current_balance": "100.00", "minimum_safe_balance": "500.00",
    }, headers=headers)
    assert resp.status_code == 422


def test_profile_bad_currency_422(client, auth_headers):
    headers, _ = auth_headers
    resp = client.post("/api/profile", json={
        "currency": "DOLLAR", "current_balance": "100.00", "minimum_safe_balance": "50.00",
    }, headers=headers)
    assert resp.status_code == 422


def test_income_add_edit_delete(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    add = client.post("/api/profile/income", json={
        "name": "Salary", "amount": "3000.00", "frequency": "monthly", "next_date": "2026-10-01",
    }, headers=headers)
    assert add.status_code == 201
    income_id = add.json()["id"]

    upd = client.put(f"/api/profile/income/{income_id}", json={
        "name": "Salary", "amount": "3500.00", "frequency": "monthly", "next_date": "2026-10-01",
    }, headers=headers)
    assert upd.status_code == 200
    assert upd.json()["amount"] == "3500.00"

    dele = client.delete(f"/api/profile/income/{income_id}", headers=headers)
    assert dele.status_code == 204
    assert client.get("/api/profile", headers=headers).json()["has_income"] is False


def test_income_negative_amount_422(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    resp = client.post("/api/profile/income", json={
        "name": "Salary", "amount": "-5", "frequency": "monthly", "next_date": "2026-10-01",
    }, headers=headers)
    assert resp.status_code == 422


def test_expense_add_edit_delete(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    add = client.post("/api/profile/expenses", json={
        "name": "Rent", "category": "rent", "amount": "1200.00", "frequency": "monthly",
        "next_date": "2026-10-01", "minimum_allowed_amount": "1200.00", "essential": True,
    }, headers=headers)
    assert add.status_code == 201
    expense_id = add.json()["id"]

    upd = client.put(f"/api/profile/expenses/{expense_id}", json={
        "name": "Rent", "category": "rent", "amount": "1300.00", "frequency": "monthly",
        "next_date": "2026-10-01", "minimum_allowed_amount": "1300.00", "essential": True,
    }, headers=headers)
    assert upd.status_code == 200
    assert upd.json()["amount"] == "1300.00"

    assert client.delete(f"/api/profile/expenses/{expense_id}",
                         headers=headers).status_code == 204


def test_expense_min_above_amount_422(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    resp = client.post("/api/profile/expenses", json={
        "name": "Rent", "category": "rent", "amount": "500", "frequency": "monthly",
        "next_date": "2026-10-01", "minimum_allowed_amount": "900",
    }, headers=headers)
    assert resp.status_code == 422


def test_commitment_and_pending_roundtrip(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    c = client.post("/api/profile/commitments", json={
        "name": "Laptop loan", "amount": "400.00", "due_date": "2026-11-15",
        "is_installment": True, "installment_total": 6,
    }, headers=headers)
    assert c.status_code == 201
    p = client.post("/api/profile/pending", json={
        "name": "Utility bill", "amount": "80.00", "due_date": "2026-10-05",
    }, headers=headers)
    assert p.status_code == 201

    # Edit both (PUT endpoints).
    cu = client.put(f"/api/profile/commitments/{c.json()['id']}", json={
        "name": "Laptop loan", "amount": "450.00", "due_date": "2026-11-20",
        "is_installment": True, "installment_total": 6,
    }, headers=headers)
    assert cu.status_code == 200
    assert cu.json()["amount"] == "450.00"
    assert cu.json()["due_date"] == "2026-11-20"

    pu = client.put(f"/api/profile/pending/{p.json()['id']}", json={
        "name": "Utility bill", "amount": "95.00", "due_date": "2026-10-08",
    }, headers=headers)
    assert pu.status_code == 200
    assert pu.json()["amount"] == "95.00"

    assert client.delete(f"/api/profile/commitments/{c.json()['id']}",
                         headers=headers).status_code == 204
    assert client.delete(f"/api/profile/pending/{p.json()['id']}",
                         headers=headers).status_code == 204


def test_commitment_edit_by_non_owner_404(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    c = client.post("/api/profile/commitments", json={
        "name": "Loan", "amount": "400.00", "due_date": "2026-11-15",
    }, headers=headers)
    commitment_id = c.json()["id"]

    headers_other, _ = _register(client)
    resp = client.put(f"/api/profile/commitments/{commitment_id}", json={
        "name": "Hacked", "amount": "1", "due_date": "2026-11-15",
    }, headers=headers_other)
    assert resp.status_code == 404
    assert client.delete(f"/api/profile/commitments/{commitment_id}",
                         headers=headers_other).status_code == 404


def test_pending_edit_by_non_owner_404(client, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    p = client.post("/api/profile/pending", json={
        "name": "Bill", "amount": "80.00", "due_date": "2026-10-05",
    }, headers=headers)
    pending_id = p.json()["id"]

    headers_other, _ = _register(client)
    resp = client.put(f"/api/profile/pending/{pending_id}", json={
        "name": "Hacked", "amount": "1", "due_date": "2026-10-05",
    }, headers=headers_other)
    assert resp.status_code == 404
    assert client.delete(f"/api/profile/pending/{pending_id}",
                         headers=headers_other).status_code == 404


# ------------------------------------------------------- user data isolation
def test_cross_user_profile_access_isolated(client, db):
    headers_a, _ = _register(client)
    headers_b, _ = _register(client)
    profile_a = _make_profile(client, headers_a)

    # B has no profile; B's GET must not see A's.
    assert client.get("/api/profile", headers=headers_b).status_code == 204

    # A's profile row must belong to A only.
    user_b = db.query(User).filter(
        User.email.like("iso-%")).order_by(User.created_at.desc()).first()
    profiles_b = db.query(FinancialProfile).filter(
        FinancialProfile.user_id == user_b.id).all()
    assert all(p.id != profile_a["id"] for p in profiles_b)


def test_income_edit_by_non_owner_404(client, db, auth_headers):
    headers, _ = auth_headers
    _make_profile(client, headers)
    add = client.post("/api/profile/income", json={
        "name": "Salary", "amount": "3000", "frequency": "monthly", "next_date": "2026-10-01",
    }, headers=headers)
    income_id = add.json()["id"]

    headers_other, _ = _register(client)
    resp = client.put(f"/api/profile/income/{income_id}", json={
        "name": "Hacked", "amount": "1", "frequency": "monthly", "next_date": "2026-10-01",
    }, headers=headers_other)
    assert resp.status_code == 404

    resp_delete = client.delete(f"/api/profile/income/{income_id}", headers=headers_other)
    assert resp_delete.status_code == 404
