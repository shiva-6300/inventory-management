"""Category management pages (viewing: everyone, changes: admin only)."""
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)

from models import Category, db
from models.category import validate_category_data
from routes.auth import admin_required, login_required

bp = Blueprint("categories", __name__, url_prefix="/categories")


def _render(edit_category=None, form=None, status=200):
    categories = Category.query.order_by(Category.name).all()
    if form is None:
        form = {
            "name": edit_category.name if edit_category else "",
            "description": (edit_category.description or "") if edit_category else "",
        }
    return (
        render_template("categories.html", categories=categories,
                        edit_category=edit_category, form=form),
        status,
    )


@bp.route("/")
@login_required
def list_categories():
    return _render()


@bp.route("/add", methods=["POST"])
@admin_required
def add_category():
    form = {"name": request.form.get("name", ""),
            "description": request.form.get("description", "")}
    cleaned, errors = validate_category_data(form)
    if errors:
        for message in errors:
            flash(message, "danger")
        return _render(form=form, status=400)
    db.session.add(Category(**cleaned))
    db.session.commit()
    flash(f"Category '{cleaned['name']}' added.", "success")
    return redirect(url_for("categories.list_categories"))


@bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    if request.method == "POST":
        form = {"name": request.form.get("name", ""),
                "description": request.form.get("description", "")}
        cleaned, errors = validate_category_data(form, exclude_id=category.id)
        if errors:
            for message in errors:
                flash(message, "danger")
            return _render(edit_category=category, form=form, status=400)
        category.name = cleaned["name"]
        category.description = cleaned["description"]
        db.session.commit()
        flash(f"Category '{category.name}' updated.", "success")
        return redirect(url_for("categories.list_categories"))
    return _render(edit_category=category)


@bp.route("/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    if category.products:
        flash(
            f"'{category.name}' still has {len(category.products)} product(s). "
            "Move or delete them first.",
            "danger",
        )
        return redirect(url_for("categories.list_categories"))
    db.session.delete(category)
    db.session.commit()
    flash(f"Category '{category.name}' deleted.", "success")
    return redirect(url_for("categories.list_categories"))
