"""JSON REST API under ``/api``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import Order, User
from app.schemas import LoginIn, OrderIn, OrderOut, OrderPage, OrderPatch, UserIn, UserOut
from app.security import authenticate, require_admin, require_user

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=UserOut, tags=["auth"])
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> User:
    """Start a session (sets the signed session cookie)."""
    user = authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    request.session["user_id"] = user.id
    return user


@router.post("/auth/logout", status_code=204, tags=["auth"])
def logout(request: Request) -> Response:
    """End the session."""
    request.session.clear()
    return Response(status_code=204)


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(require_user)) -> User:
    """Return the logged-in user."""
    return user


@router.post("/orders", response_model=OrderOut, status_code=201, tags=["orders"])
def create_order(
    body: OrderIn,
    response: Response,
    idempotency_key: Annotated[str | None, Header(max_length=64)] = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Order:
    """Create an order. A repeated ``Idempotency-Key`` returns the original (200)."""
    try:
        order, created = services.create_order(db, user, body, idempotency_key)
    except services.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not created:
        response.status_code = 200
    return order


@router.get("/orders", response_model=OrderPage, tags=["orders"])
def list_orders(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[str | None, Query(pattern="^(new|paid|shipped|cancelled)$")] = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> OrderPage:
    """List the caller's orders (all orders for admins), newest first."""
    rows, total = services.list_orders(db, user, page, page_size, status)
    return OrderPage(items=[OrderOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def get_order(order_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)) -> Order:
    """Fetch one order; other users' orders look like 404."""
    order = services.get_visible_order(db, user, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def patch_order(
    order_id: int, body: OrderPatch, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> Order:
    """Change status (state machine enforced) or quantity (only while 'new')."""
    order = services.get_visible_order(db, user, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        return services.update_order(db, order, body)
    except services.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/admin/users", response_model=UserOut, status_code=201, tags=["admin"])
def create_user(body: UserIn, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> User:
    """Admin: create a user (used by tests to provision isolated accounts)."""
    try:
        return services.create_user(db, body.username, body.password, body.role)
    except services.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/admin/stats", tags=["admin"])
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, int]:
    """Admin: order counts per status."""
    rows = db.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    return {status: count for status, count in rows}


@router.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe used by Docker and the test harness."""
    return {"status": "ok"}
