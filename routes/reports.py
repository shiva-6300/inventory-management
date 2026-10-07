"""Reports page (Pandas is used for the summaries) and CSV export."""
import pandas as pd
from flask import Blueprint, Response, render_template, request

from models import Product, StockTransaction
from models.transaction import STOCK_IN, STOCK_OUT
from routes.auth import login_required
from routes.stock import filtered_transactions

bp = Blueprint("reports", __name__, url_prefix="/reports")


def build_report():
    """Build report numbers with Pandas. Returns a dict for the template."""
    products = Product.query.all()
    product_df = pd.DataFrame(
        [
            {
                "name": p.name,
                "category": p.category.name,
                "quantity": p.quantity,
                "price": float(p.price),
                "low": p.is_low_stock,
            }
            for p in products
        ],
        columns=["name", "category", "quantity", "price", "low"],
    )
    product_df["value"] = product_df["quantity"] * product_df["price"]

    txn_df = pd.DataFrame(
        [
            {
                "product": t.product.name,
                "type": t.transaction_type,
                "quantity": t.quantity,
                "price": float(t.unit_price) if t.unit_price is not None else 0.0,
                "month": t.transaction_date.strftime("%Y-%m"),
            }
            for t in StockTransaction.query.all()
        ],
        columns=["product", "type", "quantity", "price", "month"],
    )
    txn_df["amount"] = txn_df["quantity"] * txn_df["price"]

    def summary(kind):
        subset = txn_df[txn_df["type"] == kind]
        by_product = (
            subset.groupby("product")["quantity"].sum().sort_values(ascending=False).head(5)
        )
        return {
            "transactions": int(len(subset)),
            "units": int(subset["quantity"].sum()),
            "value": float(subset["amount"].sum()),
            "top_products": [
                {"product": name, "quantity": int(qty)} for name, qty in by_product.items()
            ],
        }

    by_category = (
        product_df.groupby("category")
        .agg(products=("name", "count"), quantity=("quantity", "sum"), value=("value", "sum"))
        .reset_index()
        .sort_values("quantity", ascending=False)
    )

    monthly = (
        txn_df.groupby(["month", "type"])["quantity"].sum().unstack(fill_value=0)
        .reindex(columns=[STOCK_IN, STOCK_OUT], fill_value=0)
        .sort_index(ascending=False)
        .head(12)
    )

    return {
        "total_products": int(len(product_df)),
        "total_quantity": int(product_df["quantity"].sum()),
        "inventory_value": float(product_df["value"].sum()),
        "stock_in": summary(STOCK_IN),
        "stock_out": summary(STOCK_OUT),
        "low_stock": product_df[product_df["low"]].to_dict("records"),
        "by_category": by_category.to_dict("records"),
        "monthly": [
            {"month": month, "stock_in": int(row[STOCK_IN]), "stock_out": int(row[STOCK_OUT])}
            for month, row in monthly.iterrows()
        ],
    }


@bp.route("/")
@login_required
def reports():
    return render_template("reports.html", report=build_report())


@bp.route("/export/stock-history.csv")
@login_required
def export_history():
    query, _ = filtered_transactions(request.args)
    rows = [
        {
            "Date": t.transaction_date.isoformat(),
            "Product": t.product.name,
            "Type": t.transaction_type,
            "Quantity": t.quantity,
            "Supplier/Customer": t.supplier_customer,
            "Purchase Price": float(t.unit_price) if t.unit_price is not None else "",
            "User": t.user.name,
            "Notes": t.notes or "",
        }
        for t in query.all()
    ]
    df = pd.DataFrame(rows, columns=["Date", "Product", "Type", "Quantity",
                                     "Supplier/Customer", "Purchase Price", "User", "Notes"])
    return Response(
        df.to_csv(index=False),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_history.csv"},
    )
