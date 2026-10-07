from werkzeug.security import check_password_hash, generate_password_hash

from models import db, utcnow


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # hashed, never plain text
    role = db.Column(
        db.Enum("admin", "staff", name="user_role"), nullable=False, default="staff"
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    transactions = db.relationship("StockTransaction", back_populates="user")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
