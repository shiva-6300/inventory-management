"""Dashboard page."""
from flask import Blueprint, render_template
from sqlalchemy import func

from models import Category, Product, StockTransaction, db
from models.transaction import STOCK_IN, STOCK_OUT
from routes.auth import login_required

bp = Blueprint("dashboard", __name__)


def _total_quantity(transaction_type):
    total = (
        db.session.query(func.coalesce(func.sum(StockTransaction.quantity), 0))
        .filter(StockTransaction.transaction_type == transaction_type)
        .scalar()
    )
    return int(total or 0)


@bp.route("/dashboard")
@login_required
def dashboard():
    total_stock = db.session.query(func.coalesce(func.sum(Product.quantity), 0)).scalar()
    low_stock = (
        Product.query.filter(Product.quantity <= Product.minimum_stock)
        .order_by(Product.quantity.asc())
        .all()
    )
    stats = {
        "products": Product.query.count(),
        "categories": Category.query.count(),
        "total_stock": int(total_stock or 0),
        "low_stock": len(low_stock),
        "stock_in": _total_quantity(STOCK_IN),
        "stock_out": _total_quantity(STOCK_OUT),
    }
    recent = (
        StockTransaction.query.order_by(
            StockTransaction.transaction_date.desc(), StockTransaction.id.desc()
        )
        .limit(5)
        .all()
    )
    return render_template(
        "dashboard.html", stats=stats, low_stock=low_stock[:8], recent=recent
    )
