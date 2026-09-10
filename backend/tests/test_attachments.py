from tests.conftest import login
from tests.test_orders import SAMPLE


def _auth(client, username: str, password: str = "pass") -> dict[str, str]:
    token = login(client, username, password)
    return {"Authorization": f"Bearer {token}"}


def _queued(client) -> int:
    headers = {"Authorization": f"Bearer {login(client)}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_designer_claims_and_second_cannot_see(client) -> None:
    order_id = _queued(client)
    d1 = _auth(client, "designer1")
    claimed = client.post(f"/api/orders/{order_id}/claim", headers=d1)
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["status"] == "in_design"
    assert claimed.json()["claimed_by_name"] == "Конструктор Один"

    d2 = _auth(client, "designer2")
    hidden = client.get("/api/orders", headers=d2)
    assert hidden.status_code == 200
    assert all(row["id"] != order_id for row in hidden.json())
    assert client.get(f"/api/orders/{order_id}", headers=d2).status_code == 404

    mine = client.get("/api/orders", headers=d1)
    assert any(row["id"] == order_id for row in mine.json())


def test_designer_wip_limit_one(client) -> None:
    first = _queued(client)
    second = _queued(client)
    d1 = _auth(client, "designer1")
    assert client.post(f"/api/orders/{first}/claim", headers=d1).status_code == 200
    blocked = client.post(f"/api/orders/{second}/claim", headers=d1)
    assert blocked.status_code == 409


def test_worker_cannot_claim(client) -> None:
    order_id = _queued(client)
    worker = _auth(client, "worker1")
    response = client.post(f"/api/orders/{order_id}/claim", headers=worker)
    assert response.status_code == 403


def test_upload_complete_frees_wip(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    order_id = _queued(client)
    d1 = _auth(client, "designer1")
    claimed = client.post(f"/api/orders/{order_id}/claim", headers=d1)
    item_id = claimed.json()["items"][0]["id"]

    too_early = client.post(
        f"/api/orders/{order_id}/items/{item_id}/complete",
        json={"procurement_needed": False},
        headers=d1,
    )
    assert too_early.status_code == 400

    upload = client.post(
        f"/api/orders/{order_id}/items/{item_id}/attachments",
        data={"store": "production"},
        files={"file": ("plan.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers=d1,
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    listed = client.get(f"/api/orders/{order_id}/items/{item_id}/attachments", headers=d1)
    assert listed.status_code == 200
    assert listed.json()[0]["original_name"] == "plan.pdf"

    downloaded = client.get(f"/api/attachments/{attachment_id}", headers=d1)
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF")

    forbidden = client.post(
        f"/api/orders/{order_id}/items/{item_id}/attachments",
        data={"store": "production"},
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
        headers=d1,
    )
    assert forbidden.status_code == 400

    done = client.post(
        f"/api/orders/{order_id}/items/{item_id}/complete",
        json={"procurement_needed": False},
        headers=d1,
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "in_production"
    assert done.json()["items"][0]["construction_done_at"]
    assert done.json()["items"][0]["procurement_needed"] is False

    next_order = _queued(client)
    again = client.post(f"/api/orders/{next_order}/claim", headers=d1)
    assert again.status_code == 200, again.text


def test_unclaimed_designer_cannot_upload(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.files.settings.attachments_dir", str(tmp_path))
    order_id = _queued(client)
    headers = {"Authorization": f"Bearer {login(client)}"}
    order = client.get(f"/api/orders/{order_id}", headers=headers).json()
    item_id = order["items"][0]["id"]
    d2 = _auth(client, "designer2")
    response = client.post(
        f"/api/orders/{order_id}/items/{item_id}/attachments",
        data={"store": "production"},
        files={"file": ("plan.pdf", b"%PDF-1.4", "application/pdf")},
        headers=d2,
    )
    assert response.status_code == 403
