"""Small parsing helpers shared by forms and the API."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def parse_int(value):
    """Return an int, or None if the value is not a whole number."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def parse_decimal(value):
    """Return a Decimal rounded to 2 places, or None if invalid."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite():
            return None
        return number.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_date(value):
    """Parse YYYY-MM-DD into a date, or None."""
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def today():
    return date.today()
