from tests.conftest import login
from tests.test_orders import SAMPLE


def test_holiday_shifts_plan_start(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/orders", json=SAMPLE, headers=headers)
    assert created.status_code == 201, created.text
    before = client.get("/api/plan", headers=headers).json()
    assert before[0]["start"] == "2026-09-10"

    added = client.post(
        "/api/calendar/days",
        json={"day": "2026-09-10", "kind": "holiday", "title": "выходной"},
        headers=headers,
    )
    assert added.status_code == 201, added.text
    after = client.get("/api/plan", headers=headers).json()
    assert after[0]["start"] == "2026-09-11"


def test_attendance_absence_for_designer(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    staff = client.get("/api/calendar/staff", headers=headers)
    assert staff.status_code == 200, staff.text
    designer = next(row for row in staff.json() if row["role"] == "designer")
    marked = client.put(
        "/api/calendar/attendance",
        json={"user_id": designer["id"], "day": "2026-09-10", "present": False},
        headers=headers,
    )
    assert marked.status_code == 200
    assert marked.json()["present"] is False
    month = client.get(
        "/api/calendar/attendance",
        params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
        headers=headers,
    )
    assert month.status_code == 200
    assert any(row["user_id"] == designer["id"] and row["day"] == "2026-09-10" for row in month.json()["absences"])


def test_worker_cannot_edit_calendar(client) -> None:
    token = login(client, "worker1", "pass")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/calendar/days",
        json={"day": "2026-09-10", "kind": "holiday", "title": ""},
        headers=headers,
    )
    assert response.status_code == 403
