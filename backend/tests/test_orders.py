from tests.conftest import login


SAMPLE = {
    "customer": "Иванов",
    "contract_number": "Д-12",
    "contract_date": "2026-09-01",
    "launch_date": "2026-09-10",
    "priority": 1,
    "status": "queued",
    "notes": "",
    "items": [
        {
            "item_type": "kitchen",
            "comment": "верхние шкафы",
            "qty": 1,
            "priority": 1,
            "constructor_coeff": "1.0",
            "area_m2": "12.5",
        }
    ],
}


def test_create_and_list_order(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["customer"] == "Иванов"
    assert body["items"][0]["linear_m"] == "125.00"
    assert body["total_area_m2"] == "12.50"

    listed = client.get("/api/orders", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["item_count"] == 1


def test_worker_cannot_create_order(client) -> None:
    token = login(client, "worker1", "pass")
    response = client.post("/api/orders", json=SAMPLE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_cannot_edit_queued_order(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    order_id = created.json()["id"]
    payload = {**SAMPLE, "customer": "Петров"}
    updated = client.put(f"/api/orders/{order_id}", json=payload, headers=headers)
    assert updated.status_code == 409
