"""Deterministic test-data factories.

All values derive from a seeded ``random.Random`` plus a per-process counter,
so a failing run can be reproduced exactly (``TEST_SEED=...``) while names stay
unique enough not to collide on a shared stage environment.
"""

from __future__ import annotations

import itertools
import os
import random
import uuid
from typing import Any

SEED = int(os.environ.get("TEST_SEED", "1234"))
_rng = random.Random(SEED)
_counter = itertools.count(1)

ITEMS = ["Steel bracket", "Copper pipe", "Pressure valve", "Control panel", "Filter unit", "Fan module"]
CUSTOMERS = ["Alder GmbH", "Birch AG", "Cedar KG", "Dahlia SE", "Elm GmbH & Co. KG"]


def unique_suffix() -> str:
    """Short unique token, safe across parallel workers and repeated stage runs."""
    return uuid.uuid4().hex[:8]


def order_payload(**overrides: Any) -> dict[str, Any]:
    """A valid order body; pass keyword overrides to build invalid variants."""
    next(_counter)
    payload: dict[str, Any] = {
        "customer": _rng.choice(CUSTOMERS),
        "item": _rng.choice(ITEMS),
        "quantity": _rng.randint(1, 50),
    }
    payload.update(overrides)
    return payload


def user_payload(prefix: str = "qa", role: str = "user", **overrides: Any) -> dict[str, Any]:
    """A valid user-creation body with a unique username."""
    payload: dict[str, Any] = {
        "username": f"{prefix}_{unique_suffix()}",
        "password": "Passw0rd-" + unique_suffix(),
        "role": role,
    }
    payload.update(overrides)
    return payload
