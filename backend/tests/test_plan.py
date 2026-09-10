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
    assert plan.json()[0]["customer"] == "Иванов"
    assert plan.json()[0]["start"] == "2026-09-10"
