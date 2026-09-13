from tests.conftest import login
from tests.test_orders import SAMPLE


def test_plan_has_linear_route(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    plan = client.get("/api/plan", headers=headers)
    assert plan.status_code == 200, plan.text
    codes = [row["center_code"] for row in plan.json()]
    assert codes[0] == "construction"
    assert "complectation" in codes
    assert codes[-1] == "qc"
    first = plan.json()[0]
    assert first["customer"] == "Иванов"
    assert first["start"] == "2026-09-10"
    assert first["item_type"] == "kitchen"
    assert first["qty"] == 1
    assert first["order_priority"] == 1
    assert first["item_priority"] == 1
    assert first["launch_date"] == "2026-09-10"
