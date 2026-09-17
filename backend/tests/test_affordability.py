"""Affordability flow tests — engine integration, decision persistence, ownership."""
import uuid

from app.models import AffordabilityDecision, PurchaseRequest


def _register(client):
    suffix = uuid.uuid4().hex[:8]
    payload = {"email": f"aff-{suffix}@example.com", "password": "Sup3rSecret!"}
    resp = client.post("/api/auth/signup", json=payload)
    return {"Authorization": f"Bearer {token_of(resp)}"}, payload


def token_of(resp):
    return resp.json()["access_token"]


def _profiled_client(client, balance="6000.00", minimum="1000.00", currency="USD"):
    headers, payload = _register(client)
    r = client.post("/api/profile", json={
        "currency": currency, "current_balance": balance, "minimum_safe_balance": minimum,
    }, headers=headers)
    assert r.status_code == 201, r.text
    # Steady monthly salary for a stable forecast
    r = client.post("/api/profile/income", json={
        "name": "Salary", "amount": "2500.00", "frequency": "monthly", "next_date": "2026-10-15",
    }, headers=headers)
    assert r.status_code == 201, r.text
    return headers, payload


def test_affordable_now(client, db):
    headers, _ = _profiled_client(client, balance="6000.00", minimum="500.00")
    resp = client.post("/api/affordability/check", json={
        "item_name": "Coffee machine", "amount": "150.00",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["decision"]["affordability_status"] == "buy_now"
    assert body["decision"]["amount_safe_to_pay"] == "150.00"
    assert body["decision"]["decision_explanation"]
    # persisted
    assert body["decision"]["id"]
    assert body["id"] == body["decision"]["request_id"]


def test_wait_decision_has_earliest_date(client):
    headers, _ = _profiled_client(client, balance="300.00", minimum="200.00")
    resp = client.post("/api/affordability/check", json={
        "item_name": "Expensive monitor", "amount": "1200.00",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    decision = resp.json()["decision"]
    assert decision["affordability_status"] in ("wait", "affordable_with_plan",
                                                "not_affordable")
    if decision["affordability_status"] == "wait":
        assert decision["earliest_date_for_full_payment"]
        assert decision["earliest_date_for_full_payment"] > resp.json()["created_at"][:10]


def test_not_affordable_tiny_budget(client):
    headers, _ = _profiled_client(client, balance="100.00", minimum="90.00")
    resp = client.post("/api/affordability/check", json={
        "item_name": "Yacht", "amount": "5000000.00",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["decision"]["affordability_status"] == "not_affordable"


def test_check_requires_profile_404(client):
    headers, _ = _register(client)
    resp = client.post("/api/affordability/check", json={
        "item_name": "Thing", "amount": "10.00",
    }, headers=headers)
    assert resp.status_code == 404


def test_check_requires_auth(client):
    assert client.post("/api/affordability/check", json={
        "item_name": "Thing", "amount": "10.00"}).status_code == 401


def test_negative_amount_422(client):
    headers, _ = _profiled_client(client)
    resp = client.post("/api/affordability/check", json={
        "item_name": "Thing", "amount": "-10.00",
    }, headers=headers)
    assert resp.status_code == 422


def test_decision_history_and_detail(client):
    headers, _ = _profiled_client(client)
    for name, amount in [("Item A", "50.00"), ("Item B", "75.00")]:
        r = client.post("/api/affordability/check", json={
            "item_name": name, "amount": amount}, headers=headers)
        assert r.status_code == 201

    lst = client.get("/api/affordability/decisions", headers=headers)
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] == 2
    names = {i["item_name"] for i in body["items"]}
    assert names == {"Item A", "Item B"}

    first = body["items"][0]
    detail = client.get(f"/api/affordability/decisions/{first['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["decision"]["decision_explanation"]


def test_decision_isolation_between_users(client):
    headers_a, _ = _profiled_client(client)
    headers_b, _ = _profiled_client(client)

    r = client.post("/api/affordability/check", json={
        "item_name": "A's gadget", "amount": "20.00"}, headers=headers_a)
    request_id = r.json()["id"]

    # B cannot see or delete A's decision
    assert client.get(f"/api/affordability/decisions/{request_id}",
                      headers=headers_b).status_code == 404
    assert client.delete(f"/api/affordability/decisions/{request_id}",
                         headers=headers_b).status_code == 404

    # B's history doesn't include A's item
    lst = client.get("/api/affordability/decisions", headers=headers_b)
    assert all(i["item_name"] != "A's gadget" for i in lst.json()["items"])


def test_delete_decision(client):
    headers, _ = _profiled_client(client)
    r = client.post("/api/affordability/check", json={
        "item_name": "To delete", "amount": "30.00"}, headers=headers)
    request_id = r.json()["id"]
    assert client.delete(f"/api/affordability/decisions/{request_id}",
                         headers=headers).status_code == 204
    assert client.get(f"/api/affordability/decisions/{request_id}",
                      headers=headers).status_code == 404


def test_dashboard_summary(client):
    headers, _ = _profiled_client(client)
    r = client.get("/api/affordability/summary", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["profile_exists"] is True
    assert body["currency"] == "USD"
    assert "amount_safe_to_pay" in body
    assert "recent_decisions" in body


def test_dashboard_summary_no_profile(client):
    headers, _ = _register(client)
    r = client.get("/api/affordability/summary", headers=headers)
    assert r.status_code == 200
    assert r.json()["profile_exists"] is False
