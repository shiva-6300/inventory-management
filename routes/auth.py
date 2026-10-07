"""Authentication routes and access-control decorators."""
import re
from functools import wraps

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)

from models import User, db

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_current_user():
    """Return the logged-in User (cached per request) or None."""
    if "current_user" not in g:
        user_id = session.get("user_id")
        g.current_user = db.session.get(User, user_id) if user_id else None
    return g.current_user


def login_required(view):
    """Any logged-in user (admin or staff)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_current_user() is None:
            session.clear()
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Admins only."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            session.clear()
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if user.role != "admin":
            flash("Only administrators can access that page.", "danger")
            return redirect(url_for("dashboard.dashboard"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/")
def index():
    if get_current_user() is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("dashboard.dashboard"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user() is not None:
        return redirect(url_for("dashboard.dashboard"))

    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []

        if not email:
            errors.append("Email is required.")
        elif len(email) > 120 or not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")
        if not password:
            errors.append("Password is required.")

        if not errors:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session.clear()
                session.permanent = True
                session["user_id"] = user.id
                session["role"] = user.role
                flash(f"Welcome back, {user.name}!", "success")
                return redirect(url_for("dashboard.dashboard"))
            errors.append("Invalid email or password.")
            status = 401
        else:
            status = 400

        for message in errors:
            flash(message, "danger")
        return render_template("login.html", email=email), status

    return render_template("login.html", email=email)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
