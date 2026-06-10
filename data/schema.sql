-- A small e-commerce schema. Deliberately normalized so that interesting
-- questions require joins, aggregates, and subqueries — the cases where a
-- naive one-shot prompt tends to hallucinate columns or miss a join.

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL,
    country     TEXT    NOT NULL,
    signup_date TEXT    NOT NULL          -- ISO date 'YYYY-MM-DD'
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    category   TEXT    NOT NULL,
    price      REAL    NOT NULL,          -- list price
    cost       REAL    NOT NULL           -- unit cost (for profit questions)
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date  TEXT    NOT NULL,         -- ISO date 'YYYY-MM-DD'
    status      TEXT    NOT NULL          -- completed | pending | cancelled | refunded
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL,
    unit_price    REAL    NOT NULL         -- price actually charged (may differ from list)
);

CREATE TABLE reviews (
    review_id   INTEGER PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    rating      INTEGER NOT NULL,          -- 1..5
    created_at  TEXT    NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_order      ON order_items(order_id);
CREATE INDEX idx_items_product    ON order_items(product_id);
CREATE INDEX idx_reviews_product  ON reviews(product_id);
