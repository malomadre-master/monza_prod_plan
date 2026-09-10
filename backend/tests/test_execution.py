from tests.conftest import login
from tests.test_orders import SAMPLE


def _auth(client, username: str, password: str = "pass") -> dict[str, str]:
    token = login(client, username, password)
    return {"Authorization": f"Bearer {token}"}


def _item_ready(client, *, procurement: bool) -> tuple[int, int]:
    headers = {"Authorization": f"Bearer {login(client)}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    d1 = _auth(client, "designer1")
    claimed = client.post(f"/api/orders/{order_id}/claim", headers=d1)
    item_id = claimed.json()["items"][0]["id"]
    upload = client.post(
        f"/api/orders/{order_id}/items/{item_id}/attachments",
        data={"store": "production"},
        files={"file": ("plan.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers=d1,
    )
    assert upload.status_code == 201, upload.text
    done = client.post(
        f"/api/orders/{order_id}/items/{item_id}/complete",
        json={"procurement_needed": procurement},
        headers=d1,
    )
    assert done.status_code == 200, done.text
    return order_id, item_id


def test_saw_queue_after_construction_without_procurement(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    order_id, item_id = _item_ready(client, procurement=False)
    worker = _auth(client, "worker1")
    queue = client.get("/api/terminal/queue", headers=worker)
    assert queue.status_code == 200, queue.text
    assert queue.json()["center_code"] == "saw"
    ids = [row["item_id"] for row in queue.json()["cards"]]
    assert item_id in ids
    assert all(row["order_id"] != order_id or row["step_status"] == "waiting" for row in queue.json()["cards"] if row["item_id"] == item_id)


def test_procurement_blocks_saw_until_confirmed(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    order_id, item_id = _item_ready(client, procurement=True)
    worker = _auth(client, "worker1")
    empty = client.get("/api/terminal/queue", headers=worker)
    assert all(row["item_id"] != item_id for row in empty.json()["cards"])

    supply = _auth(client, "supply1")
    gate = client.get("/api/terminal/queue", headers=supply)
    assert gate.json()["center_code"] == "complectation"
    assert any(row["item_id"] == item_id for row in gate.json()["cards"])
    confirmed = client.post(
        "/api/terminal/events",
        json={"order_id": order_id, "item_id": item_id, "kind": "materials_confirmed"},
        headers=supply,
    )
    assert confirmed.status_code == 201, confirmed.text
    saw = client.get("/api/terminal/queue", headers=worker)
    assert any(row["item_id"] == item_id for row in saw.json()["cards"])


def test_take_done_and_wip_one(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    first_order, first_item = _item_ready(client, procurement=False)
    second_order, second_item = _item_ready(client, procurement=False)
    worker = _auth(client, "worker1")
    taken = client.post(
        "/api/terminal/events",
        json={"order_id": first_order, "item_id": first_item, "kind": "taken", "center_code": "saw"},
        headers=worker,
    )
    assert taken.status_code == 201, taken.text
    blocked = client.post(
        "/api/terminal/events",
        json={"order_id": second_order, "item_id": second_item, "kind": "taken"},
        headers=worker,
    )
    assert blocked.status_code == 409
    done = client.post(
        "/api/terminal/events",
        json={"order_id": first_order, "item_id": first_item, "kind": "done"},
        headers=worker,
    )
    assert done.status_code == 201, done.text
    edge = client.get("/api/terminal/queue?center=edgebanding", headers={"Authorization": f"Bearer {login(client)}"})
    assert any(row["item_id"] == first_item for row in edge.json()["cards"])
    again = client.post(
        "/api/terminal/events",
        json={"order_id": second_order, "item_id": second_item, "kind": "taken"},
        headers=worker,
    )
    assert again.status_code == 201, again.text


def test_worker_cannot_open_other_center(client) -> None:
    worker = _auth(client, "worker1")
    response = client.get("/api/terminal/queue?center=edgebanding", headers=worker)
    assert response.status_code == 403


def test_designer_cannot_use_terminal(client) -> None:
    designer = _auth(client, "designer1")
    response = client.get("/api/terminal/queue", headers=designer)
    assert response.status_code == 403
