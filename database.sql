-- ============================================================
-- Inventory and Stock Management System - MySQL schema + sample data
-- Usage:  mysql -u root -p < database.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventory_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE inventory_management;

DROP TABLE IF EXISTS stock_transactions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id          INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(120) NOT NULL,
    password    VARCHAR(255) NOT NULL,                 -- Werkzeug password hash
    role        ENUM('admin', 'staff') NOT NULL DEFAULT 'staff',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE categories (
    id           INT          NOT NULL AUTO_INCREMENT,
    name         VARCHAR(100) NOT NULL,
    description  VARCHAR(255) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE products (
    id             INT           NOT NULL AUTO_INCREMENT,
    name           VARCHAR(150)  NOT NULL,
    category_id    INT           NOT NULL,
    price          DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    quantity       INT           NOT NULL DEFAULT 0,
    minimum_stock  INT           NOT NULL DEFAULT 10,
    supplier       VARCHAR(150)  NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_products_name (name),
    KEY ix_products_category (category_id),
    CONSTRAINT chk_products_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_products_minimum CHECK (minimum_stock >= 0),
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_transactions (
    id                 INT          NOT NULL AUTO_INCREMENT,
    product_id         INT          NOT NULL,
    user_id            INT          NOT NULL,
    transaction_type   ENUM('STOCK IN', 'STOCK OUT') NOT NULL,
    quantity           INT          NOT NULL,
    supplier_customer  VARCHAR(150) NOT NULL,
    unit_price         DECIMAL(10,2) NULL,              -- purchase price (stock in)
    transaction_date   DATE         NOT NULL,
    notes              VARCHAR(500) NULL,
    PRIMARY KEY (id),
    KEY ix_transactions_product (product_id),
    KEY ix_transactions_user (user_id),
    KEY ix_transactions_date (transaction_date),
    CONSTRAINT chk_transactions_quantity CHECK (quantity > 0),
    CONSTRAINT fk_transactions_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
    CONSTRAINT fk_transactions_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Sample data
--   Admin: admin@inventory.com / Admin@123
--   Staff: staff@inventory.com / Staff@123
-- Passwords below are Werkzeug hashes (never plain text).
-- ------------------------------------------------------------
INSERT INTO users (id, name, email, password, role) VALUES
(1, 'Admin User', 'admin@inventory.com', 'scrypt:32768:8:1$CWAuVXRIHHKUPmcI$a32848ba1efd30d982314dc4fa973938f942ef06e5594e85e1fba4cb38a777369df579294252473edd53a81c53bcac4f98606cb4d688438cecf765a5d1dfc105', 'admin'),
(2, 'Staff User', 'staff@inventory.com', 'scrypt:32768:8:1$ebZNcW9wbrGUqwb0$65dccfbb29a7a493860337ae576cb6dc6dc5cec7e8e378de7016fddaaa1acbf4845262850a45d5003ca59a1ac8dc5a73f70a352a750b027e153d9db61397813b', 'staff');

INSERT INTO categories (id, name, description) VALUES
(1, 'Electronics', 'Computers, accessories and gadgets'),
(2, 'Stationery',  'Office and school supplies'),
(3, 'Furniture',   'Desks, chairs and storage'),
(4, 'Cleaning',    'Cleaning and hygiene supplies');

INSERT INTO products (id, name, category_id, price, quantity, minimum_stock, supplier) VALUES
(1, 'Wireless Mouse',       1,  15.99,  45, 15, 'TechSource Ltd'),
(2, 'USB-C Cable',          1,   7.50,   8, 20, 'TechSource Ltd'),
(3, 'A4 Paper Ream',        2,   4.25, 120, 40, 'PaperWorld'),
(4, 'Ball Pen (Box of 50)', 2,   9.00,  12, 15, 'PaperWorld'),
(5, 'Office Chair',         3,  89.00,  14,  5, 'ComfortSeating'),
(6, 'Standing Desk',        3, 249.00,   3,  4, 'ComfortSeating'),
(7, 'Hand Sanitizer 500ml', 4,   3.80,  60, 25, 'CleanCo'),
(8, 'Floor Cleaner 5L',     4,  12.40,  22, 10, 'CleanCo');

INSERT INTO stock_transactions
    (product_id, user_id, transaction_type, quantity, supplier_customer, unit_price, transaction_date, notes) VALUES
(1, 2, 'STOCK IN',  50, 'TechSource Ltd',      11.50, DATE_SUB(CURDATE(), INTERVAL 20 DAY), 'Initial purchase'),
(1, 1, 'STOCK OUT',  5, 'Sales Department',    NULL,  DATE_SUB(CURDATE(), INTERVAL 12 DAY), 'Team order'),
(3, 2, 'STOCK IN', 150, 'PaperWorld',           3.10, DATE_SUB(CURDATE(), INTERVAL 18 DAY), 'Quarterly refill'),
(3, 2, 'STOCK OUT', 30, 'Accounts Department', NULL,  DATE_SUB(CURDATE(), INTERVAL 9 DAY),  NULL),
(2, 1, 'STOCK IN',  30, 'TechSource Ltd',       4.00, DATE_SUB(CURDATE(), INTERVAL 25 DAY), NULL),
(2, 2, 'STOCK OUT', 22, 'IT Department',       NULL,  DATE_SUB(CURDATE(), INTERVAL 6 DAY),  'Laptop rollout'),
(5, 1, 'STOCK IN',  20, 'ComfortSeating',      62.00, DATE_SUB(CURDATE(), INTERVAL 30 DAY), NULL),
(5, 2, 'STOCK OUT',  6, 'HR Department',       NULL,  DATE_SUB(CURDATE(), INTERVAL 3 DAY),  'New joiners');
