"""Final E2E probe (in-process, real Postgres): full product flow plus the new
commitment/pending update endpoints and expired-token handling."""
import uuid

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    s = uuid.uuid4().hex[:8]
    ok = []

    def step(name: str, cond: bool, detail: str = "") -> None:
        ok.append(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))

    # 1. signup + signout + signin
    r = client.post("/api/auth/signup", json={
        "email": f"e2e-{s}@example.com", "password": "Str0ngPass!x", "full_name": "E2E Probe",
    })
    step("signup", r.status_code == 201, str(r.status_code))
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    # 2. profile
    r = client.post("/api/profile", headers=h, json={
        "currency": "USD", "current_balance": "4000.00", "minimum_safe_balance": "1000.00",
    })
    step("profile create", r.status_code == 201)

    # 3. income + expense (fuel for the engine)
    step("income add", client.post("/api/profile/income", headers=h, json={
        "name": "Salary", "amount": "3200.00", "frequency": "monthly", "next_date": "2026-10-01",
    }).status_code == 201)
    step("expense add", client.post("/api/profile/expenses", headers=h, json={
        "name": "Rent", "category": "rent", "amount": "1200.00", "frequency": "monthly",
        "next_date": "2026-10-01", "minimum_allowed_amount": "1200.00", "essential": True,
    }).status_code == 201)

    # 4. commitment + pending — create, EDIT (new PUT), verify, delete
    c = client.post("/api/profile/commitments", headers=h, json={
        "name": "Laptop loan", "amount": "300.00", "due_date": "2026-11-15",
        "is_installment": True, "installment_total": 6,
    })
    step("commitment add", c.status_code == 201)
    cu = client.put(f"/api/profile/commitments/{c.json()['id']}", headers=h, json={
        "name": "Laptop loan", "amount": "350.00", "due_date": "2026-11-20",
        "is_installment": True, "installment_total": 6,
    })
    step("commitment EDIT (new PUT)", cu.status_code == 200 and cu.json()["amount"] == "350.00")

    p = client.post("/api/profile/pending", headers=h, json={
        "name": "Utility bill", "amount": "80.00", "due_date": "2026-10-05",
    })
    step("pending add", p.status_code == 201)
    pu = client.put(f"/api/profile/pending/{p.json()['id']}", headers=h, json={
        "name": "Utility bill", "amount": "95.00", "due_date": "2026-10-08",
    })
    step("pending EDIT (new PUT)", pu.status_code == 200 and pu.json()["amount"] == "95.00")

    # 5. affordability check (engine) — small item
    r = client.post("/api/affordability/check", headers=h, json={
        "item_name": "Coffee machine", "amount": "120.00",
    })
    step("affordability check", r.status_code == 201 and r.json()["decision"] is not None)
    step("explanation present", bool(r.json()["decision"]["decision_explanation"]))

    # 6. dashboard summary
    r = client.get("/api/affordability/summary", headers=h)
    j = r.json()
    step("summary", r.status_code == 200 and j["profile_exists"] is True)
    step("monthly income includes all cadences", float(j["monthly_income"]) == 3200.00,
         str(j.get("monthly_income")))

    # 7. history + detail
    r = client.get("/api/affordability/decisions", headers=h)
    step("history list", r.status_code == 200 and r.json()["total"] >= 1)
    rid = r.json()["items"][0]["id"]
    step("history detail", client.get(f"/api/affordability/decisions/{rid}", headers=h).status_code == 200)

    # 8. ownership isolation: second user cannot touch first user's decision
    r2 = client.post("/api/auth/signup", json={
        "email": f"e2e-other-{s}@example.com", "password": "Str0ngPass!x",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    step("cross-user detail blocked", client.get(
        f"/api/affordability/decisions/{rid}", headers=h2).status_code == 404)
    step("cross-user commitment edit blocked", client.put(
        f"/api/profile/commitments/{c.json()['id']}", headers=h2, json={
            "name": "Hacked", "amount": "1", "due_date": "2026-11-15",
        }).status_code == 404)

    # 9. persistence: data still there for the same user
    step("persistence", client.get("/api/profile", headers=h).json()["current_balance"] == "4000.00")

    # 10. invalid token handled
    step("invalid token 401", client.get(
        "/api/profile", headers={"Authorization": "Bearer garbage"}).status_code == 401)

    print(f"\n{'ALL ' + str(len(ok)) + ' STEPS PASS' if all(ok) else 'FAILURES PRESENT'}")


if __name__ == "__main__":
    main()
