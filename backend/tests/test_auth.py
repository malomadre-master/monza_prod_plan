from tests.conftest import login


def test_login_ok(client) -> None:
    token = login(client)
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert me.json()["role"] == "admin"


def test_login_wrong_password(client) -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_me_requires_token(client) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_admin_sets_constructor_efficiency(client) -> None:
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/users",
        json={
            "username": "kpd08",
            "display_name": "Конструктор КПД",
            "password": "pass",
            "role": "designer",
            "efficiency": "0.80",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["efficiency"] == "0.80"
    user_id = created.json()["id"]
    patched = client.patch(f"/api/users/{user_id}", json={"efficiency": "1.20"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["efficiency"] == "1.20"
