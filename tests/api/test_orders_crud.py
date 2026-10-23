"""Order create / read / update and ownership rules."""

import pytest

from tests.data import seed
from tests.data.factories import order_payload


@pytest.mark.smoke
def test_create_and_fetch_order(api):
    payload = order_payload(customer="Fetch GmbH", quantity=7)
    created = api.post("/api/orders", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "new"
    assert body["customer"] == "Fetch GmbH"
    assert body["quantity"] == 7
    assert body["reference"] == f"ORD-{body['id']:06d}"

    fetched = api.get(f"/api/orders/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


@pytest.mark.regression
def test_customer_is_trimmed(api):
    resp = api.post("/api/orders", json=order_payload(customer="  Padded AG  "))
    assert resp.json()["customer"] == "Padded AG"


@pytest.mark.regression
def test_unknown_order_is_404(api):
    assert api.get("/api/orders/999999999").status_code == 404
    assert api.patch("/api/orders/999999999", json={"status": "paid"}).status_code == 404


@pytest.mark.regression
def test_users_cannot_see_each_others_orders(api, live_server, admin_api):
    order = api.post("/api/orders", json=order_payload()).json()
    with seed.login_client(live_server, seed.create_account(admin_api)) as other:
        assert other.get(f"/api/orders/{order['id']}").status_code == 404
        assert other.patch(f"/api/orders/{order['id']}", json={"status": "paid"}).status_code == 404
        assert other.get("/api/orders").json()["total"] == 0


@pytest.mark.regression
def test_admin_sees_every_users_orders(api, admin_api):
    order = api.post("/api/orders", json=order_payload()).json()
    assert admin_api.get(f"/api/orders/{order['id']}").status_code == 200


@pytest.mark.smoke
def test_status_happy_path(api):
    oid = api.post("/api/orders", json=order_payload()).json()["id"]
    for status in ("paid", "shipped"):
        resp = api.patch(f"/api/orders/{oid}", json={"status": status})
        assert resp.status_code == 200
        assert resp.json()["status"] == status


@pytest.mark.regression
@pytest.mark.parametrize(
    ("path", "illegal"),
    [
        ([], "shipped"),
        (["cancelled"], "paid"),
        (["paid", "shipped"], "cancelled"),
        (["paid", "shipped"], "new"),
    ],
    ids=["new-to-shipped", "cancelled-is-final", "shipped-is-final", "no-way-back-to-new"],
)
def test_illegal_status_transitions_conflict(api, path, illegal):
    oid = api.post("/api/orders", json=order_payload()).json()["id"]
    for status in path:
        api.patch(f"/api/orders/{oid}", json={"status": status}).raise_for_status()
    resp = api.patch(f"/api/orders/{oid}", json={"status": illegal})
    assert resp.status_code == 409
    expected = path[-1] if path else "new"
    assert api.get(f"/api/orders/{oid}").json()["status"] == expected


@pytest.mark.regression
def test_quantity_editable_only_while_new(api):
    oid = api.post("/api/orders", json=order_payload(quantity=1)).json()["id"]
    assert api.patch(f"/api/orders/{oid}", json={"quantity": 5}).json()["quantity"] == 5
    api.patch(f"/api/orders/{oid}", json={"status": "paid"}).raise_for_status()
    assert api.patch(f"/api/orders/{oid}", json={"quantity": 9}).status_code == 409


@pytest.mark.regression
def test_patch_cannot_change_immutable_fields(api):
    order = api.post("/api/orders", json=order_payload(customer="Fixed AG")).json()
    api.patch(f"/api/orders/{order['id']}", json={"customer": "Hacked", "owner_id": 1}).raise_for_status()
    assert api.get(f"/api/orders/{order['id']}").json()["customer"] == "Fixed AG"
