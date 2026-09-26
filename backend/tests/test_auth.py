def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "X-Request-ID" in res.headers


def test_login_and_me(client):
    bad = client.post("/api/auth/login", json={"username": "manager", "password": "wrong"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"username": "manager", "password": "Manager-2026!"})
    assert ok.status_code == 200
    assert ok.json()["user"]["username"] == "manager"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "manager"


def test_lockout(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "viewer", "password": "nope"})
    locked = client.post("/api/auth/login", json={"username": "viewer", "password": "Viewer-2026!"})
    assert locked.status_code == 401
