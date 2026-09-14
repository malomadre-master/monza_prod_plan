from tests.conftest import login
from tests.test_execution import _item_ready
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
    assert first["pinned"] is False


def test_board_queued_item_sits_on_construction(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    board = client.get("/api/plan/board", headers=headers)
    assert board.status_code == 200, board.text
    card = board.json()[0]
    assert card["center_code"] == "construction"
    assert card["board_status"] == "waiting"
    assert card["item_type"] == "kitchen"
    assert card["start"]


def test_board_moves_with_shop_events(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    order_id, item_id = _item_ready(client, procurement=False)
    headers = {"Authorization": f"Bearer {login(client)}"}
    board = client.get("/api/plan/board", headers=headers)
    card = next(row for row in board.json() if row["item_id"] == item_id)
    assert card["center_code"] == "saw"
    assert card["board_status"] == "waiting"
    worker = client.post(
        "/api/auth/login",
        json={"username": "worker1", "password": "pass"},
    )
    worker_headers = {"Authorization": f"Bearer {worker.json()['access_token']}"}
    taken = client.post(
        "/api/terminal/events",
        json={"order_id": order_id, "item_id": item_id, "kind": "taken", "center_code": "saw"},
        headers=worker_headers,
    )
    assert taken.status_code == 201, taken.text
    board = client.get("/api/plan/board", headers=headers)
    card = next(row for row in board.json() if row["item_id"] == item_id)
    assert card["center_code"] == "saw"
    assert card["board_status"] == "in_progress"
    assert card["taken_by_name"] == "Станочник"


def test_board_procurement_gate(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    _order_id, item_id = _item_ready(client, procurement=True)
    headers = {"Authorization": f"Bearer {login(client)}"}
    board = client.get("/api/plan/board", headers=headers)
    card = next(row for row in board.json() if row["item_id"] == item_id)
    assert card["center_code"] == "complectation"
    assert card["board_status"] == "waiting"


def test_pin_preview_and_apply_moves_other_slot(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    kitchen = {**SAMPLE["items"][0], "area_m2": "100"}
    first = client.post("/api/orders", json={**SAMPLE, "items": [kitchen]}, headers=headers)
    second = client.post(
        "/api/orders",
        json={**SAMPLE, "customer": "Petrov", "priority": 2, "contract_number": "D-13", "items": [kitchen]},
        headers=headers,
    )
    assert first.status_code == 201 and second.status_code == 201
    plan = client.get("/api/plan", headers=headers).json()
    saw_first = next(row for row in plan if row["order_id"] == first.json()["id"] and row["center_code"] == "saw")
    item_b = second.json()["items"][0]["id"]
    payload = {
        "item_id": item_b,
        "center_code": "saw",
        "start": saw_first["start"],
        "finish": saw_first["finish"],
    }
    preview = client.post("/api/plan/pins/preview", json=payload, headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["changes"]
    applied = client.put("/api/plan/pins", json=payload, headers=headers)
    assert applied.status_code == 200, applied.text
    plan = client.get("/api/plan", headers=headers).json()
    saw_b = next(row for row in plan if row["item_id"] == item_b and row["center_code"] == "saw")
    saw_a = next(row for row in plan if row["order_id"] == first.json()["id"] and row["center_code"] == "saw")
    assert saw_b["pinned"] is True
    assert saw_b["start"] == saw_first["start"]
    assert saw_a["start"] != saw_b["start"]
    worker = client.post("/api/auth/login", json={"username": "worker1", "password": "pass"})
    forbidden = client.put(
        "/api/plan/pins",
        json=payload,
        headers={"Authorization": f"Bearer {worker.json()['access_token']}"},
    )
    assert forbidden.status_code == 403
    cleared = client.put("/api/plan/pins", json={**payload, "remove": True}, headers=headers)
    assert cleared.status_code == 200
    plan = client.get("/api/plan", headers=headers).json()
    saw_b = next(row for row in plan if row["item_id"] == item_b and row["center_code"] == "saw")
    assert saw_b["pinned"] is False


def test_queue_reorder_preview_and_apply(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    kitchen = {**SAMPLE["items"][0], "area_m2": "100"}
    first = client.post("/api/orders", json={**SAMPLE, "items": [kitchen]}, headers=headers)
    second = client.post(
        "/api/orders",
        json={**SAMPLE, "customer": "Petrov", "priority": 2, "contract_number": "D-13", "items": [kitchen]},
        headers=headers,
    )
    assert first.status_code == 201 and second.status_code == 201
    item_a = first.json()["items"][0]["id"]
    item_b = second.json()["items"][0]["id"]
    plan = client.get("/api/plan", headers=headers).json()
    saw_a_before = next(row for row in plan if row["item_id"] == item_a and row["center_code"] == "saw")
    saw_b_before = next(row for row in plan if row["item_id"] == item_b and row["center_code"] == "saw")
    assert saw_a_before["start"] < saw_b_before["start"]
    payload = {"center_code": "construction", "item_ids": [item_b, item_a]}
    preview = client.post("/api/plan/queue/preview", json=payload, headers=headers)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["changes"]
    saw_a_preview = next(row for row in body["slots"] if row["item_id"] == item_a and row["center_code"] == "saw")
    saw_b_preview = next(row for row in body["slots"] if row["item_id"] == item_b and row["center_code"] == "saw")
    assert saw_b_preview["start"] < saw_a_preview["start"]
    plan = client.get("/api/plan", headers=headers).json()
    saw_a = next(row for row in plan if row["item_id"] == item_a and row["center_code"] == "saw")
    assert saw_a["start"] == saw_a_before["start"]
    incomplete = client.post("/api/plan/queue/preview", json={"center_code": "construction", "item_ids": [item_a]}, headers=headers)
    assert incomplete.status_code == 409
    applied = client.put("/api/plan/queue", json=payload, headers=headers)
    assert applied.status_code == 200, applied.text
    plan = client.get("/api/plan", headers=headers).json()
    saw_a = next(row for row in plan if row["item_id"] == item_a and row["center_code"] == "saw")
    saw_b = next(row for row in plan if row["item_id"] == item_b and row["center_code"] == "saw")
    assert saw_b["start"] < saw_a["start"]
    board = client.get("/api/plan/board", headers=headers).json()
    waiting = [row for row in board if row["center_code"] == "construction" and row["board_status"] == "waiting"]
    assert [row["item_id"] for row in waiting] == [item_b, item_a]
    worker = client.post("/api/auth/login", json={"username": "worker1", "password": "pass"})
    forbidden = client.put(
        "/api/plan/queue",
        json=payload,
        headers={"Authorization": f"Bearer {worker.json()['access_token']}"},
    )
    assert forbidden.status_code == 403
