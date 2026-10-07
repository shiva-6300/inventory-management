"""Product management pages."""
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from sqlalchemy.exc import IntegrityError

from models import Category, Product, db
from models.product import validate_product_data
from routes.auth import admin_required, login_required

bp = Blueprint("products", __name__, url_prefix="/products")

FORM_FIELDS = ("name", "category_id", "price", "quantity", "minimum_stock", "supplier")


def _form_data():
    return {field: request.form.get(field, "") for field in FORM_FIELDS}


@bp.route("/")
@login_required
def list_products():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)

    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)
    products = query.order_by(Product.name).all()

    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "products.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
    )


@bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_product():
    categories = Category.query.order_by(Category.name).all()
    form = {"name": "", "category_id": "", "price": "", "quantity": "0",
            "minimum_stock": "10", "supplier": ""}

    if request.method == "POST":
        form = _form_data()
        cleaned, errors = validate_product_data(form)
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("add_product.html", form=form, categories=categories), 400
        db.session.add(Product(**cleaned))
        db.session.commit()
        flash(f"Product '{cleaned['name']}' added.", "success")
        return redirect(url_for("products.list_products"))

    return render_template("add_product.html", form=form, categories=categories)


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    categories = Category.query.order_by(Category.name).all()
    form = {
        "name": product.name,
        "category_id": str(product.category_id),
        "price": f"{product.price:.2f}",
        "quantity": str(product.quantity),
        "minimum_stock": str(product.minimum_stock),
        "supplier": product.supplier or "",
    }

    if request.method == "POST":
        form = _form_data()
        cleaned, errors = validate_product_data(form, exclude_id=product.id)
        if errors:
            for message in errors:
                flash(message, "danger")
            return (
                render_template("edit_product.html", product=product, form=form,
                                categories=categories),
                400,
            )
        for key, value in cleaned.items():
            setattr(product, key, value)
        db.session.commit()
        flash(f"Product '{product.name}' updated.", "success")
        return redirect(url_for("products.list_products"))

    return render_template("edit_product.html", product=product, form=form,
                           categories=categories)


@bp.route("/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    if product.transactions:
        flash(
            f"'{product.name}' has stock history and cannot be deleted. "
            "Set its quantity to 0 instead.",
            "danger",
        )
        return redirect(url_for("products.list_products"))
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product.name}' deleted.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("This product could not be deleted because it is in use.", "danger")
    return redirect(url_for("products.list_products"))
