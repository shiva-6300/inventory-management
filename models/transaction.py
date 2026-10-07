from sqlalchemy import select

from models import db
from models.product import MAX_PRICE, MAX_QUANTITY, Product
from utils import parse_date, parse_decimal, parse_int, today

STOCK_IN = "STOCK IN"
STOCK_OUT = "STOCK OUT"
TRANSACTION_TYPES = (STOCK_IN, STOCK_OUT)


class StockTransaction(db.Model):
    __tablename__ = "stock_transactions"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type = db.Column(
        db.Enum(*TRANSACTION_TYPES, name="transaction_type"), nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    supplier_customer = db.Column(db.String(150), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=True)  # purchase price (stock in)
    transaction_date = db.Column(db.Date, nullable=False, default=today)
    notes = db.Column(db.String(500), nullable=True)

    product = db.relationship("Product", back_populates="transactions")
    user = db.relationship("User", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product": self.product.name,
            "user_id": self.user_id,
            "user": self.user.name,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "supplier_customer": self.supplier_customer,
            "purchase_price": float(self.unit_price) if self.unit_price is not None else None,
            "transaction_date": self.transaction_date.isoformat(),
            "notes": self.notes,
        }

    def __repr__(self):
        return f"<StockTransaction {self.id} {self.transaction_type} x{self.quantity}>"


def record_transaction(user, transaction_type, data):
    """Validate and record a stock-in / stock-out transaction.

    `data` needs: product_id, quantity, party (supplier/customer), date, notes
    and (for stock in) purchase_price.
    Returns (transaction_or_None, errors). Stock quantity is updated and
    committed here, so web routes and the API behave identically.
    """
    errors = []
    is_in = transaction_type == STOCK_IN
    party_label = "Supplier" if is_in else "Customer / Department"

    product_id = parse_int(data.get("product_id"))
    quantity = parse_int(data.get("quantity"))
    party = str(data.get("party") or "").strip()
    notes = str(data.get("notes") or "").strip()
    date_value = str(data.get("date") or "").strip() or today().isoformat()
    txn_date = parse_date(date_value)
    unit_price = None

    if product_id is None:
        errors.append("Please select a product.")
    if quantity is None:
        errors.append("Quantity is required and must be a whole number.")
    elif quantity <= 0:
        errors.append("Quantity must be greater than zero.")
    elif quantity > MAX_QUANTITY:
        errors.append(f"Quantity cannot exceed {MAX_QUANTITY:,}.")

    if not party:
        errors.append(f"{party_label} is required.")
    elif len(party) > 150:
        errors.append(f"{party_label} must not exceed 150 characters.")

    if txn_date is None:
        errors.append("Date must be a valid date (YYYY-MM-DD).")
    elif txn_date > today():
        errors.append("Date cannot be in the future.")

    if len(notes) > 500:
        errors.append("Notes must not exceed 500 characters.")

    if is_in:
        unit_price = parse_decimal(data.get("purchase_price"))
        if unit_price is None:
            errors.append("Purchase price is required and must be a valid number.")
        elif unit_price < 0:
            errors.append("Purchase price cannot be negative.")
        elif unit_price > MAX_PRICE:
            errors.append("Purchase price is too large.")

    if errors:
        return None, errors

    # Lock the product row so two simultaneous stock-outs cannot oversell.
    product = db.session.execute(
        select(Product).where(Product.id == product_id).with_for_update()
    ).scalar_one_or_none()
    if product is None:
        return None, ["Selected product does not exist."]

    if is_in:
        product.quantity += quantity
    else:
        if quantity > product.quantity:
            db.session.rollback()
            return None, [
                f"Insufficient stock for '{product.name}': "
                f"requested {quantity}, only {product.quantity} available."
            ]
        product.quantity -= quantity

    txn = StockTransaction(
        product_id=product.id,
        user_id=user.id,
        transaction_type=transaction_type,
        quantity=quantity,
        supplier_customer=party,
        unit_price=unit_price,
        transaction_date=txn_date,
        notes=notes or None,
    )
    db.session.add(txn)
    db.session.commit()
    return txn, []
