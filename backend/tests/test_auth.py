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
