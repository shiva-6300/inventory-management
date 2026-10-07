"""Database object and model imports."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """Current UTC time as a naive datetime (works with MySQL DATETIME)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Imported after `db` is defined to avoid circular-import problems.
from models.user import User  # noqa: E402,F401
from models.category import Category  # noqa: E402,F401
from models.product import Product  # noqa: E402,F401
from models.transaction import StockTransaction  # noqa: E402,F401
