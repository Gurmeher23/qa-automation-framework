"""Server-rendered HTML views."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import Order, User
from app.schemas import OrderIn
from app.security import authenticate, current_user_or_none

router = APIRouter()


def _render(request: Request, name: str, user: User | None, status_code: int = 200, **ctx: object) -> Response:
    return request.app.state.templates.TemplateResponse(
        request, name, {"user": user, **ctx}, status_code=status_code
    )


@router.get("/", include_in_schema=False)
def index(user: User | None = Depends(current_user_or_none)) -> RedirectResponse:
    return RedirectResponse("/orders" if user else "/login", status_code=303)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request, user: User | None = Depends(current_user_or_none)) -> Response:
    return _render(request, "login.html", user, error=None)


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    user = authenticate(db, username, password)
    if user is None:
        return _render(request, "login.html", None, status_code=401, error="Invalid username or password")
    request.session["user_id"] = user.id
    return RedirectResponse("/orders", status_code=303)


@router.post("/logout", include_in_schema=False)
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/orders", response_class=HTMLResponse, include_in_schema=False)
def orders_page(request: Request, user: User | None = Depends(current_user_or_none), db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    rows, total = services.list_orders(db, user, page=1, page_size=100, status=None)
    return _render(request, "orders.html", user, orders=rows, total=total)


@router.get("/orders/new", response_class=HTMLResponse, include_in_schema=False)
def new_order_page(request: Request, user: User | None = Depends(current_user_or_none)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return _render(request, "order_new.html", user, errors=[], form={})


@router.post("/orders/new", include_in_schema=False)
def new_order_submit(
    request: Request,
    customer: str = Form(""),
    item: str = Form(""),
    quantity: str = Form(""),
    user: User | None = Depends(current_user_or_none),
    db: Session = Depends(get_db),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    form = {"customer": customer, "item": item, "quantity": quantity}
    try:
        data = OrderIn(customer=customer, item=item, quantity=quantity)  # type: ignore[arg-type]
    except ValidationError as exc:
        errors = [f"{'.'.join(map(str, e['loc'])).capitalize()}: {e['msg']}" for e in exc.errors()]
        return _render(request, "order_new.html", user, status_code=422, errors=errors, form=form)
    order, _ = services.create_order(db, user, data)
    return RedirectResponse(f"/orders?created={order.reference}", status_code=303)


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page(request: Request, user: User | None = Depends(current_user_or_none), db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role != "admin":
        return _render(request, "forbidden.html", user, status_code=403)
    orders = db.scalars(select(Order).order_by(Order.id.desc()).limit(500)).all()
    return _render(request, "admin.html", user, orders=orders)
