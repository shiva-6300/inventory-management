# Inventory and Stock Management System

A Flask web application for managing products, categories and stock movements, with
role-based access (Admin / Staff), low-stock alerts, Pandas-powered reports and a JSON REST API.

**Tech stack:** Python 3, Flask, MySQL, SQLAlchemy, Pandas (reports), HTML, CSS, Jinja2.

## Features

- **Login / logout** with hashed passwords (Werkzeug) and Flask sessions
- **Roles:** Admin (full access) and Staff (stock in/out, history, reports, read-only products/categories)
- **Dashboard:** total products, categories, total stock, low-stock count, total stock-in and stock-out, low-stock list, recent transactions
- **Products (admin):** add, edit, delete, view, search by name, filter by category
- **Categories (admin):** add, edit, delete, view
- **Stock In:** product, quantity, supplier, purchase price, date, notes - quantity increases automatically
- **Stock Out:** product, quantity, customer/department, date, notes - quantity decreases automatically; cannot exceed available stock
- **Low-stock alerts:** products where `quantity <= minimum_stock`
- **Stock history:** filter by date range, transaction type and product; CSV download
- **Reports:** totals, inventory value, stock-in / stock-out summaries, stock by category, monthly movement, low-stock list (Pandas)
- **REST API** with JSON responses and proper HTTP status codes

## Project Structure

```
inventory-management/
├── app.py            # App factory, CSRF, error handlers, demo-data seeding
├── config.py         # Settings from environment variables
├── utils.py          # Parsing helpers (int, decimal, date)
├── requirements.txt
├── .env.example
├── database.sql      # MySQL schema + sample data
├── models/           # user, category, product, transaction
├── routes/           # auth, dashboard, products, categories, stock, reports, api
├── templates/        # Jinja2 pages (+ base.html, _product_form.html, error.html)
└── static/css/style.css
```

## Installation

Requirements: Python 3.9+ and MySQL 8 (or MariaDB).

```bash
cd inventory-management
python -m venv venv
# Windows (cmd/PowerShell): venv\Scripts\activate
# Git Bash:                 source venv/Scripts/activate
# macOS/Linux:              source venv/bin/activate
python -m pip install -r requirements.txt
```

### Database setup

Option A - schema and sample data (recommended):
```bash
mysql -u root -p < database.sql
```
Option B - create an empty database only; the app creates the tables and demo data on first start:
```sql
CREATE DATABASE inventory_management CHARACTER SET utf8mb4;
```

### Environment variables

```bash
cp .env.example .env      # Windows cmd: copy .env.example .env
```
Edit `.env`:

| Variable      | Description                          |
|---------------|--------------------------------------|
| `SECRET_KEY`  | Long random string for sessions      |
| `DB_HOST`     | MySQL host (default `localhost`)     |
| `DB_PORT`     | MySQL port (default `3306`)          |
| `DB_USER`     | MySQL user                           |
| `DB_PASSWORD` | MySQL password                       |
| `DB_NAME`     | Database name (`inventory_management`) |

## Run

```bash
python app.py
```
Open <http://127.0.0.1:5000>.

## Sample Logins

| Role  | Email                | Password   |
|-------|----------------------|------------|
| Admin | admin@inventory.com  | Admin@123  |
| Staff | staff@inventory.com  | Staff@123  |

## Business Rules

- Quantities must be whole numbers; negative quantities are rejected everywhere.
- Stock-in / stock-out quantity must be greater than zero; dates cannot be in the future.
- Stock-out is refused if it exceeds available stock (the product row is locked during the update).
- Product and category names must be unique (case-insensitive).
- A category with products cannot be deleted; a product with stock history cannot be deleted
  (set its quantity to 0 instead) so the audit trail is never lost.

## REST API

Base URL `http://127.0.0.1:5000/api`. The API uses the same session cookie as the website:
call `POST /api/login` first and send the cookie afterwards. Bodies must be JSON
(`Content-Type: application/json`). Errors look like `{"error": "message", "details": [...]}`.

| Method | Endpoint                 | Access        | Description                             |
|--------|--------------------------|---------------|-----------------------------------------|
| POST   | `/api/login`             | Public        | Log in                                  |
| POST   | `/api/logout`            | Logged in     | Log out                                 |
| GET    | `/api/products`          | Logged in     | List products (`?search=`, `?category_id=`) |
| POST   | `/api/products`          | Admin         | Create product                          |
| GET    | `/api/products/<id>`     | Logged in     | Get one product                         |
| PUT    | `/api/products/<id>`     | Admin         | Update product (send only changed fields) |
| DELETE | `/api/products/<id>`     | Admin         | Delete product (409 if it has history)  |
| GET    | `/api/categories`        | Logged in     | List categories                         |
| POST   | `/api/categories`        | Admin         | Create category                         |
| POST   | `/api/stock-in`          | Logged in     | Record incoming stock                   |
| POST   | `/api/stock-out`         | Logged in     | Record outgoing stock                   |
| GET    | `/api/stock-history`     | Logged in     | History (`?type=`, `?product=`, `?date_from=`, `?date_to=`) |
| GET    | `/api/low-stock`         | Logged in     | Products at or below minimum stock      |

Status codes: `200` OK, `201` created, `400` invalid input, `401` not logged in, `403` wrong role,
`404` not found, `409` conflict (insufficient stock, product has history).

### Example requests

```bash
# Login as admin (saves cookie)
curl -c c.txt -X POST http://127.0.0.1:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@inventory.com", "password": "Admin@123"}'

# Create a category and a product (admin)
curl -b c.txt -X POST http://127.0.0.1:5000/api/categories \
  -H "Content-Type: application/json" -d '{"name": "Tools", "description": "Hand tools"}'

curl -b c.txt -X POST http://127.0.0.1:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Hammer", "category_id": 5, "price": 12.5, "quantity": 20, "minimum_stock": 5, "supplier": "ToolCo"}'

# Update only the price
curl -b c.txt -X PUT http://127.0.0.1:5000/api/products/9 \
  -H "Content-Type: application/json" -d '{"price": 14.0}'

# Stock in
curl -b c.txt -X POST http://127.0.0.1:5000/api/stock-in \
  -H "Content-Type: application/json" \
  -d '{"product_id": 9, "quantity": 10, "supplier": "ToolCo", "purchase_price": 9.5, "notes": "Restock"}'

# Stock out (returns 409 if more than available)
curl -b c.txt -X POST http://127.0.0.1:5000/api/stock-out \
  -H "Content-Type: application/json" \
  -d '{"product_id": 9, "quantity": 3, "customer": "Maintenance Dept"}'

# Reads
curl -b c.txt "http://127.0.0.1:5000/api/products?search=mouse"
curl -b c.txt "http://127.0.0.1:5000/api/stock-history?type=STOCK%20OUT&date_from=2026-01-01"
curl -b c.txt http://127.0.0.1:5000/api/low-stock
```

Stock-out success response (`201`):
```json
{
  "message": "Stock Out recorded.",
  "new_quantity": 27,
  "transaction": {"id": 12, "product": "Hammer", "transaction_type": "STOCK OUT", "quantity": 3,
                  "supplier_customer": "Maintenance Dept", "transaction_date": "2026-10-06", "...": "..."}
}
```

## Database

- `users` (id, name, email, password, role, created_at)
- `categories` (id, name, description)
- `products` (id, name, category_id -> categories.id, price, quantity, minimum_stock, supplier, created_at, updated_at)
- `stock_transactions` (id, product_id -> products.id, user_id -> users.id, transaction_type, quantity,
  supplier_customer, unit_price, transaction_date, notes)

`unit_price` stores the purchase price for stock-in transactions.

## Troubleshooting

- **Could not connect to the database** - MySQL must be running and `.env` must have the right credentials
  (`using password: NO` in the error means `.env` is missing or `DB_PASSWORD` is empty).
- **Unknown database** - run `database.sql` or create `inventory_management` manually.
- **`ModuleNotFoundError`** - activate your virtual environment and run `python -m pip install -r requirements.txt`.
