import pytest


@pytest.mark.smoke
def test_health(anon_api):
    resp = anon_api.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.regression
def test_openapi_schema_lists_order_endpoints(anon_api):
    paths = anon_api.get("/openapi.json").json()["paths"]
    assert {"/api/orders", "/api/orders/{order_id}", "/api/auth/login"} <= set(paths)
