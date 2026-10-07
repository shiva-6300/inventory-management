"""JSON REST API (session based - log in with POST /api/login first)."""
from functools import wraps

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from models import Category, Product, StockTransaction, User, db
from models.category import validate_category_data
from models.product import validate_product_data
from models.transaction import (STOCK_IN, STOCK_OUT, TRANSACTION_TYPES,
                                record_transaction)
from routes.auth import EMAIL_RE, get_current_user
from routes.stock import filtered_transactions

bp = Blueprint("api", __name__, url_prefix="/api")


def error(message, status, **extra):
    return jsonify({"error": message, **extra}), status


def api_auth(admin_only=False):
    """Require a logged-in session (and optionally the admin role)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return error("Authentication required. Log in with POST /api/login.", 401)
            if admin_only and user.role != "admin":
                return error("This action requires the 'admin' role.", 403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def json_body():
    if not request.is_json:
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


BAD_BODY = "Request body must be a JSON object (Content-Type: application/json)."


# ---------------------------------------------------------------------- auth
@bp.route("/login", methods=["POST"])
def login():
    data = json_body()
    if data is None:
        return error(BAD_BODY, 400)
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not email or not isinstance(password, str) or not password:
        return error("Both 'email' and 'password' are required.", 400)
    if len(email) > 120 or not EMAIL_RE.match(email):
        return error("Please provide a valid email address.", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return error("Invalid email or password.", 401)

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["role"] = user.role
    return jsonify({"message": "Login successful.", "user": user.to_dict()}), 200


@bp.route("/logout", methods=["POST"])
@api_auth()
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


# ------------------------------------------------------------------ products
@bp.route("/products", methods=["GET"])
@api_auth()
def list_products():
    query = Product.query
    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    products = query.order_by(Product.name).all()
    return jsonify({"count": len(products), "products": [p.to_dict() for p in products]}), 200


@bp.route("/products", methods=["POST"])
@api_auth(admin_only=True)
def create_product():
    data = json_body()
    if data is None:
        return error(BAD_BODY, 400)
    cleaned, errors = validate_product_data(data)
    if errors:
        return error("Validation failed.", 400, details=errors)
    product = Product(**cleaned)
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product created.", "product": product.to_dict()}), 201


@bp.route("/products/<int:product_id>", methods=["GET"])
@api_auth()
def get_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        return error("Product not found.", 404)
    return jsonify({"product": product.to_dict()}), 200


@bp.route("/products/<int:product_id>", methods=["PUT"])
@api_auth(admin_only=True)
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        return error("Product not found.", 404)
    data = json_body()
    if data is None:
        return error(BAD_BODY, 400)

    # Fields that are not sent keep their current value.
    merged = {
        "name": product.name,
        "category_id": product.category_id,
        "price": product.price,
        "quantity": product.quantity,
        "minimum_stock": product.minimum_stock,
        "supplier": product.supplier,
    }
    merged.update({k: v for k, v in data.items() if k in merged})
    cleaned, errors = validate_product_data(merged, exclude_id=product.id)
    if errors:
        return error("Validation failed.", 400, details=errors)
    for key, value in cleaned.items():
        setattr(product, key, value)
    db.session.commit()
    return jsonify({"message": "Product updated.", "product": product.to_dict()}), 200


@bp.route("/products/<int:product_id>", methods=["DELETE"])
@api_auth(admin_only=True)
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        return error("Product not found.", 404)
    if product.transactions:
        return error("Product has stock history and cannot be deleted.", 409)
    try:
        db.session.delete(product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("Product is in use and cannot be deleted.", 409)
    return jsonify({"message": "Product deleted."}), 200


# ---------------------------------------------------------------- categories
@bp.route("/categories", methods=["GET"])
@api_auth()
def list_categories():
    categories = Category.query.order_by(Category.name).all()
    return jsonify({"count": len(categories), "categories": [c.to_dict() for c in categories]}), 200


@bp.route("/categories", methods=["POST"])
@api_auth(admin_only=True)
def create_category():
    data = json_body()
    if data is None:
        return error(BAD_BODY, 400)
    cleaned, errors = validate_category_data(data)
    if errors:
        return error("Validation failed.", 400, details=errors)
    category = Category(**cleaned)
    db.session.add(category)
    db.session.commit()
    return jsonify({"message": "Category created.", "category": category.to_dict()}), 201


# --------------------------------------------------------------------- stock
def _stock_endpoint(transaction_type):
    data = json_body()
    if data is None:
        return error(BAD_BODY, 400)
    if transaction_type == STOCK_IN:
        party = data.get("supplier", data.get("supplier_customer"))
    else:
        party = data.get("customer", data.get("supplier_customer"))
    payload = {
        "product_id": data.get("product_id"),
        "quantity": data.get("quantity"),
        "party": party,
        "purchase_price": data.get("purchase_price"),
        "date": data.get("date"),
        "notes": data.get("notes"),
    }
    txn, errors = record_transaction(get_current_user(), transaction_type, payload)
    if errors:
        insufficient = any(e.startswith("Insufficient stock") for e in errors)
        return error("Validation failed.", 409 if insufficient else 400, details=errors)
    return jsonify(
        {
            "message": f"{transaction_type.title()} recorded.",
            "transaction": txn.to_dict(),
            "new_quantity": txn.product.quantity,
        }
    ), 201


@bp.route("/stock-in", methods=["POST"])
@api_auth()
def stock_in():
    return _stock_endpoint(STOCK_IN)


@bp.route("/stock-out", methods=["POST"])
@api_auth()
def stock_out():
    return _stock_endpoint(STOCK_OUT)


@bp.route("/stock-history", methods=["GET"])
@api_auth()
def stock_history():
    txn_type = request.args.get("type")
    if txn_type and txn_type not in TRANSACTION_TYPES:
        return error("Invalid type. Use 'STOCK IN' or 'STOCK OUT'.", 400)
    query, _ = filtered_transactions(request.args)
    transactions = query.all()
    return jsonify(
        {"count": len(transactions), "transactions": [t.to_dict() for t in transactions]}
    ), 200


@bp.route("/low-stock", methods=["GET"])
@api_auth()
def low_stock():
    products = (
        Product.query.filter(Product.quantity <= Product.minimum_stock)
        .order_by(Product.quantity.asc())
        .all()
    )
    return jsonify({"count": len(products), "products": [p.to_dict() for p in products]}), 200
