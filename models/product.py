from decimal import Decimal

from sqlalchemy import func

from models import db, utcnow
from models.category import Category
from utils import parse_decimal, parse_int

MAX_PRICE = Decimal("9999999.99")
MAX_QUANTITY = 1_000_000


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=10)
    supplier = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    category = db.relationship("Category", back_populates="products")
    transactions = db.relationship("StockTransaction", back_populates="product")

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock

    @property
    def stock_value(self):
        return self.price * self.quantity

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "price": float(self.price),
            "quantity": self.quantity,
            "minimum_stock": self.minimum_stock,
            "supplier": self.supplier,
            "is_low_stock": self.is_low_stock,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Product {self.id} {self.name}>"


def validate_product_data(data, exclude_id=None):
    """Return (cleaned, errors) for a product form / JSON payload."""
    errors = []
    name = str(data.get("name") or "").strip()
    supplier = str(data.get("supplier") or "").strip()

    if not name:
        errors.append("Product name is required.")
    elif len(name) < 2 or len(name) > 150:
        errors.append("Product name must be between 2 and 150 characters.")
    else:
        query = Product.query.filter(func.lower(Product.name) == name.lower())
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        if query.first():
            errors.append("A product with this name already exists.")

    category_id = parse_int(data.get("category_id"))
    if category_id is None or db.session.get(Category, category_id) is None:
        errors.append("Please select a valid category.")

    price = parse_decimal(data.get("price"))
    if price is None:
        errors.append("Price is required and must be a valid number.")
    elif price < 0:
        errors.append("Price cannot be negative.")
    elif price > MAX_PRICE:
        errors.append("Price is too large.")

    quantity = parse_int(data.get("quantity"))
    if quantity is None:
        errors.append("Quantity is required and must be a whole number.")
    elif quantity < 0:
        errors.append("Quantity cannot be negative.")
    elif quantity > MAX_QUANTITY:
        errors.append(f"Quantity cannot exceed {MAX_QUANTITY:,}.")

    minimum_stock = parse_int(data.get("minimum_stock"))
    if minimum_stock is None:
        errors.append("Minimum stock level is required and must be a whole number.")
    elif minimum_stock < 0:
        errors.append("Minimum stock level cannot be negative.")
    elif minimum_stock > MAX_QUANTITY:
        errors.append(f"Minimum stock level cannot exceed {MAX_QUANTITY:,}.")

    if len(supplier) > 150:
        errors.append("Supplier name must not exceed 150 characters.")

    cleaned = {
        "name": name,
        "category_id": category_id,
        "price": price,
        "quantity": quantity,
        "minimum_stock": minimum_stock,
        "supplier": supplier or None,
    }
    return cleaned, errors
