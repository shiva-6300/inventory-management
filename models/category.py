from sqlalchemy import func

from models import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    products = db.relationship("Product", back_populates="category")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "product_count": len(self.products),
        }

    def __repr__(self):
        return f"<Category {self.name}>"


def validate_category_data(data, exclude_id=None):
    """Return (cleaned, errors) for a category form / JSON payload."""
    errors = []
    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip()

    if not name:
        errors.append("Category name is required.")
    elif len(name) < 2 or len(name) > 100:
        errors.append("Category name must be between 2 and 100 characters.")
    else:
        query = Category.query.filter(func.lower(Category.name) == name.lower())
        if exclude_id:
            query = query.filter(Category.id != exclude_id)
        if query.first():
            errors.append("A category with this name already exists.")

    if len(description) > 255:
        errors.append("Description must not exceed 255 characters.")

    return {"name": name, "description": description or None}, errors
