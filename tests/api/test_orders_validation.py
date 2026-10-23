"""Input validation: every bad payload must fail with 422 and create nothing."""

import pytest

from tests.data.factories import order_payload


@pytest.mark.regression
@pytest.mark.parametrize(
    "overrides",
    [
        {"customer": ""},
        {"customer": "   "},
        {"customer": "x" * 81},
        {"item": ""},
        {"quantity": 0},
        {"quantity": -3},
        {"quantity": 1001},
        {"quantity": "many"},
        {"quantity": 2.5},
    ],
    ids=["empty-customer", "blank-customer", "long-customer", "empty-item", "qty-zero", "qty-negative",
         "qty-too-large", "qty-string", "qty-float"],
)
def test_invalid_payload_is_rejected_and_nothing_is_created(api, overrides):
    resp = api.post("/api/orders", json=order_payload(**overrides))
    assert resp.status_code == 422
    assert api.get("/api/orders").json()["total"] == 0


@pytest.mark.regression
@pytest.mark.parametrize("missing", ["customer", "item", "quantity"])
def test_missing_required_field(api, missing):
    payload = order_payload()
    del payload[missing]
    resp = api.post("/api/orders", json=payload)
    assert resp.status_code == 422
    assert any(missing in err["loc"] for err in resp.json()["detail"])


@pytest.mark.regression
def test_boundary_quantities_are_accepted(api):
    assert api.post("/api/orders", json=order_payload(quantity=1)).status_code == 201
    assert api.post("/api/orders", json=order_payload(quantity=1000)).status_code == 201


@pytest.mark.regression
def test_invalid_status_value_in_patch(api):
    oid = api.post("/api/orders", json=order_payload()).json()["id"]
    assert api.patch(f"/api/orders/{oid}", json={"status": "teleported"}).status_code == 422


@pytest.mark.regression
def test_malformed_json_is_422(api):
    resp = api.post("/api/orders", content=b"{not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422
