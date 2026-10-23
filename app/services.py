"""Business logic shared by the REST API and the HTML views."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import TRANSITIONS, Order, User
from app.schemas import OrderIn, OrderPatch
from app.security import hash_password


class ConflictError(Exception):
    """Raised for state conflicts (duplicate user, illegal transition, key reuse)."""


def create_user(db: Session, username: str, password: str, role: str = "user") -> User:
    """Create a user or raise :class:`ConflictError` if the name is taken."""
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"User '{username}' already exists") from exc
    return user


def ensure_admin(db: Session, username: str, password: str) -> None:
    """Bootstrap the admin account on startup if it does not exist yet."""
    if db.scalar(select(User).where(User.username == username)) is None:
        create_user(db, username, password, role="admin")


def create_order(db: Session, owner: User, data: OrderIn, idempotency_key: str | None = None) -> tuple[Order, bool]:
    """Create an order. Returns ``(order, created)``.

    With an ``idempotency_key`` a retry returns the original order
    (``created=False``). Reusing a key with a different payload is a conflict.
    """
    if idempotency_key:
        existing = db.scalar(
            select(Order).where(Order.owner_id == owner.id, Order.idempotency_key == idempotency_key)
        )
        if existing:
            same = (existing.customer, existing.item, existing.quantity) == (data.customer, data.item, data.quantity)
            if not same:
                raise ConflictError("Idempotency-Key was already used with a different payload")
            return existing, False
    order = Order(
        customer=data.customer,
        item=data.item,
        quantity=data.quantity,
        owner_id=owner.id,
        idempotency_key=idempotency_key or None,
    )
    db.add(order)
    db.flush()
    order.reference = f"ORD-{order.id:06d}"
    db.commit()
    return order, True


def visible_orders_query(user: User):  # noqa: ANN201
    """Admins see everything, users only their own orders."""
    query = select(Order)
    if user.role != "admin":
        query = query.where(Order.owner_id == user.id)
    return query


def list_orders(db: Session, user: User, page: int, page_size: int, status: str | None) -> tuple[list[Order], int]:
    """Paginated, newest-first listing with an optional status filter."""
    base = visible_orders_query(user)
    if status:
        base = base.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def get_visible_order(db: Session, user: User, order_id: int) -> Order | None:
    """Fetch an order the user may see; ``None`` hides other users' orders."""
    order = db.get(Order, order_id)
    if order is None or (user.role != "admin" and order.owner_id != user.id):
        return None
    return order


def update_order(db: Session, order: Order, patch: OrderPatch) -> Order:
    """Apply a partial update, enforcing the status state machine."""
    if patch.status and patch.status != order.status:
        if patch.status not in TRANSITIONS[order.status]:
            raise ConflictError(f"Cannot move order from '{order.status}' to '{patch.status}'")
        order.status = patch.status
    if patch.quantity is not None:
        if order.status != "new":
            raise ConflictError("Quantity can only change while the order is 'new'")
        order.quantity = patch.quantity
    db.commit()
    return order
