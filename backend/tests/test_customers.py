from app.config import settings
from app.iin import generate_iin


def _login(client, username="manager", password="Manager-2026!"):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200


def test_create_list_export(client):
    _login(client)
    iin = generate_iin(second_weights=False)
    created = client.post(
        "/api/customers",
        json={"name": "O'Brien", "iin": iin, "phone": "+77001112233", "email": "ob@example.com"},
    )
    assert created.status_code == 201, created.text
    listed = client.get("/api/customers", params={"q": "Brien"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    export = client.get("/api/customers/export", params={"fmt": "csv"})
    assert export.status_code == 200
    assert b"O'Brien" in export.content


def test_search_apostrophe_clean(client):
    _login(client)
    iin = generate_iin()
    client.post("/api/customers", json={"name": "O'Brien", "iin": iin})
    found = client.get("/api/customers/search", params={"name": "O'Brien"})
    assert found.status_code == 200
    assert len(found.json()) == 1


def test_viewer_cannot_create(client):
    _login(client, "viewer", "Viewer-2026!")
    res = client.post("/api/customers", json={"name": "X", "iin": generate_iin()})
    assert res.status_code == 403


def test_iin_fault_via_api(client):
    settings.CRM_MODE = "experiment"
    settings.FAULT_IIN_SECOND_WEIGHTS = True
    try:
        _login(client)
        iin = generate_iin(second_weights=True)
        res = client.post("/api/customers", json={"name": "Faulty", "iin": iin})
        assert res.status_code == 422
    finally:
        settings.CRM_MODE = "clean"
        settings.FAULT_IIN_SECOND_WEIGHTS = False
