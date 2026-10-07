"""Stock in, stock out, stock history and low-stock pages."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Product, StockTransaction
from models.transaction import (STOCK_IN, STOCK_OUT, TRANSACTION_TYPES,
                                record_transaction)
from routes.auth import get_current_user, login_required
from utils import parse_date, today

bp = Blueprint("stock", __name__)


def _products():
    return Product.query.order_by(Product.name).all()


def _transaction_page(transaction_type, template):
    form = {
        "product_id": request.args.get("product", ""),
        "quantity": "",
        "party": "",
        "purchase_price": "",
        "date": today().isoformat(),
        "notes": "",
    }
    if request.method == "POST":
        form = {key: request.form.get(key, "") for key in form}
        txn, errors = record_transaction(get_current_user(), transaction_type, form)
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template(template, form=form, products=_products(),
                                   today=today().isoformat()), 400
        verb = "added to" if transaction_type == STOCK_IN else "removed from"
        flash(f"{txn.quantity} unit(s) {verb} '{txn.product.name}'. "
              f"New quantity: {txn.product.quantity}.", "success")
        return redirect(url_for("stock.stock_history"))
    return render_template(template, form=form, products=_products(),
                           today=today().isoformat())


@bp.route("/stock-in", methods=["GET", "POST"])
@login_required
def stock_in():
    return _transaction_page(STOCK_IN, "stock_in.html")


@bp.route("/stock-out", methods=["GET", "POST"])
@login_required
def stock_out():
    return _transaction_page(STOCK_OUT, "stock_out.html")


def filtered_transactions(args):
    """Apply history filters (also reused by the CSV export). Returns (query, filters)."""
    txn_type = args.get("type", "")
    product_id = args.get("product", type=int)
    date_from = args.get("date_from", "")
    date_to = args.get("date_to", "")

    query = StockTransaction.query
    if txn_type in TRANSACTION_TYPES:
        query = query.filter_by(transaction_type=txn_type)
    else:
        txn_type = ""
    if product_id:
        query = query.filter_by(product_id=product_id)
    start, end = parse_date(date_from), parse_date(date_to)
    if start:
        query = query.filter(StockTransaction.transaction_date >= start)
    else:
        date_from = ""
    if end:
        query = query.filter(StockTransaction.transaction_date <= end)
    else:
        date_to = ""
    query = query.order_by(StockTransaction.transaction_date.desc(),
                           StockTransaction.id.desc())
    filters = {"type": txn_type, "product": product_id,
               "date_from": date_from, "date_to": date_to}
    return query, filters


@bp.route("/stock-history")
@login_required
def stock_history():
    query, filters = filtered_transactions(request.args)
    return render_template(
        "stock_history.html",
        transactions=query.all(),
        products=_products(),
        types=TRANSACTION_TYPES,
        filters=filters,
    )


@bp.route("/low-stock")
@login_required
def low_stock():
    products = (
        Product.query.filter(Product.quantity <= Product.minimum_stock)
        .order_by((Product.quantity - Product.minimum_stock).asc(), Product.name)
        .all()
    )
    return render_template("low_stock.html", products=products)
