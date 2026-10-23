"""Authentication and authorisation."""

import httpx
import pytest

from tests.data import seed
from tests.data.factories import unique_suffix as seed_suffix


@pytest.mark.smoke
def test_login_sets_session_and_me_returns_user(live_server, account):
    with httpx.Client(base_url=live_server) as client:
        resp = client.post("/api/auth/login", json={"username": account.username, "password": account.password})
        assert resp.status_code == 200
        assert "orderdesk_session" in client.cookies
        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == account.username
        assert me.json()["role"] == "user"


@pytest.mark.regression
@pytest.mark.parametrize(
    ("username", "password"),
    [("nobody", "whatever-123"), ("", ""), ("admin", "wrong-password")],
    ids=["unknown-user", "empty", "bad-password"],
)
def test_login_rejects_bad_credentials(anon_api, username, password):
    resp = anon_api.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 401
    assert "orderdesk_session" not in anon_api.cookies


@pytest.mark.regression
def test_login_with_missing_field_is_422(anon_api):
    assert anon_api.post("/api/auth/login", json={"username": "x"}).status_code == 422


@pytest.mark.smoke
def test_protected_endpoints_require_login(anon_api):
    for method, path in [("get", "/api/orders"), ("get", "/api/auth/me"), ("get", "/api/admin/stats")]:
        assert getattr(anon_api, method)(path).status_code == 401, path


@pytest.mark.regression
def test_logout_invalidates_session(api):
    assert api.get("/api/auth/me").status_code == 200
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/auth/me").status_code == 401


@pytest.mark.regression
def test_tampered_cookie_is_rejected(api):
    api.cookies.set("orderdesk_session", "garbage.value.here", domain="127.0.0.1")
    assert api.get("/api/auth/me").status_code == 401


@pytest.mark.regression
def test_regular_user_cannot_use_admin_endpoints(api):
    assert api.get("/api/admin/stats").status_code == 403
    assert api.post("/api/admin/users", json={"username": "sneaky1", "password": "password-123"}).status_code == 403


@pytest.mark.regression
def test_admin_can_create_user_and_duplicates_conflict(admin_api):
    account = seed.create_account(admin_api)
    dup = admin_api.post("/api/admin/users", json={"username": account.username, "password": "password-123"})
    assert dup.status_code == 409


@pytest.mark.regression
@pytest.mark.parametrize(
    "body",
    [
        {"username": "ab", "password": "password-123"},
        {"username": "bad name!", "password": "password-123"},
        {"username": "valid_name", "password": "short"},
        {"username": "valid_name", "password": "password-123", "role": "superuser"},
    ],
    ids=["short-name", "bad-chars", "short-password", "bad-role"],
)
def test_admin_user_creation_validates_input(admin_api, body):
    assert admin_api.post("/api/admin/users", json=body).status_code == 422


@pytest.mark.regression
def test_password_material_is_never_returned(admin_api, api):
    created = admin_api.post("/api/admin/users", json={"username": "leakcheck_" + seed_suffix(), "password": "password-123"})
    for body in (created.text, api.get("/api/auth/me").text):
        assert "password" not in body.lower()
        assert "$" not in body  # stored hashes use salt$digest
