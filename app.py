"""Inventory and Stock Management System - application entry point.

Run with:  python app.py
"""
import secrets
import sys
from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request, session
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from models import Category, Product, StockTransaction, User, db
from routes import api, auth, categories, dashboard, products, reports, stock

ERROR_MESSAGES = {
    400: "Bad request. The form may have expired - please go back and try again.",
    403: "You do not have permission to access this resource.",
    404: "The page you are looking for could not be found.",
    405: "That method is not allowed for this URL.",
    500: "Something went wrong on our side. Please try again later.",
}


def seed_default_data():
    """Create demo data on an empty database (mirrors database.sql)."""
    if User.query.first() is not None:
        return

    admin = User(name="Admin User", email="admin@inventory.com", role="admin")
    admin.set_password("Admin@123")
    staff = User(name="Staff User", email="staff@inventory.com", role="staff")
    staff.set_password("Staff@123")
    db.session.add_all([admin, staff])

    cats = {
        name: Category(name=name, description=desc)
        for name, desc in [
            ("Electronics", "Computers, accessories and gadgets"),
            ("Stationery", "Office and school supplies"),
            ("Furniture", "Desks, chairs and storage"),
            ("Cleaning", "Cleaning and hygiene supplies"),
        ]
    }
    db.session.add_all(cats.values())
    db.session.flush()

    items = [
        ("Wireless Mouse", "Electronics", 15.99, 45, 15, "TechSource Ltd"),
        ("USB-C Cable", "Electronics", 7.50, 8, 20, "TechSource Ltd"),
        ("A4 Paper Ream", "Stationery", 4.25, 120, 40, "PaperWorld"),
        ("Ball Pen (Box of 50)", "Stationery", 9.00, 12, 15, "PaperWorld"),
        ("Office Chair", "Furniture", 89.00, 14, 5, "ComfortSeating"),
        ("Standing Desk", "Furniture", 249.00, 3, 4, "ComfortSeating"),
        ("Hand Sanitizer 500ml", "Cleaning", 3.80, 60, 25, "CleanCo"),
        ("Floor Cleaner 5L", "Cleaning", 12.40, 22, 10, "CleanCo"),
    ]
    product_objs = {}
    for name, cat, price, qty, minimum, supplier in items:
        p = Product(name=name, category_id=cats[cat].id, price=price, quantity=qty,
                    minimum_stock=minimum, supplier=supplier)
        db.session.add(p)
        product_objs[name] = p
    db.session.flush()

    today = date.today()
    txns = [
        ("Wireless Mouse", staff, "STOCK IN", 50, "TechSource Ltd", 11.50, 20, "Initial purchase"),
        ("Wireless Mouse", admin, "STOCK OUT", 5, "Sales Department", None, 12, "Team order"),
        ("A4 Paper Ream", staff, "STOCK IN", 150, "PaperWorld", 3.10, 18, "Quarterly refill"),
        ("A4 Paper Ream", staff, "STOCK OUT", 30, "Accounts Department", None, 9, None),
        ("USB-C Cable", admin, "STOCK IN", 30, "TechSource Ltd", 4.00, 25, None),
        ("USB-C Cable", staff, "STOCK OUT", 22, "IT Department", None, 6, "Laptop rollout"),
        ("Office Chair", admin, "STOCK IN", 20, "ComfortSeating", 62.00, 30, None),
        ("Office Chair", staff, "STOCK OUT", 6, "HR Department", None, 3, "New joiners"),
    ]
    for name, user, kind, qty, party, price, days_ago, notes in txns:
        db.session.add(StockTransaction(
            product_id=product_objs[name].id, user_id=user.id, transaction_type=kind,
            quantity=qty, supplier_customer=party, unit_price=price,
            transaction_date=today - timedelta(days=days_ago), notes=notes))
    db.session.commit()
    print("Seeded demo data (see README for credentials).")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    for module in (auth, dashboard, products, categories, stock, reports, api):
        app.register_blueprint(module.bp)

    # ---------------------------------------------------------- CSRF (forms)
    @app.before_request
    def csrf_protect():
        """Check the CSRF token on every HTML form POST (the JSON API is exempt)."""
        if request.method == "POST" and not request.path.startswith("/api/"):
            expected = session.get("_csrf_token")
            sent = request.form.get("csrf_token")
            if not expected or not sent or not secrets.compare_digest(expected, sent):
                return handle_error(400)

    @app.context_processor
    def inject_globals():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(16)
        return {
            "csrf_token": session["_csrf_token"],
            "current_user": auth.get_current_user(),
        }

    @app.template_filter("fmt_date")
    def fmt_date(value):
        return value.strftime("%d %b %Y") if value else "-"

    @app.template_filter("money")
    def money(value):
        return f"{float(value or 0):,.2f}"

    # ------------------------------------------------------ error handling
    def handle_error(error_or_code):
        code = error_or_code if isinstance(error_or_code, int) else getattr(
            error_or_code, "code", 500)
        if code not in ERROR_MESSAGES:
            code = 500
        if code == 500:
            db.session.rollback()
        message = ERROR_MESSAGES[code]
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), code
        return render_template("error.html", code=code, message=message), code

    for code in ERROR_MESSAGES:
        app.register_error_handler(code, handle_error)

    # ------------------------------------------------------------ database
    with app.app_context():
        try:
            db.create_all()
            seed_default_data()
        except SQLAlchemyError as exc:
            print("\nCould not connect to the database.")
            print("Check your .env settings and make sure MySQL is running.")
            print(f"Details: {exc.__class__.__name__}: {str(exc).splitlines()[0]}\n")
            sys.exit(1)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=app.config["PORT"], debug=app.config["DEBUG"])
