"""Deterministically build data/shop.db from schema.sql + a fixed RNG seed.

`python -m data.seed` (re)creates the database. Same seed -> byte-identical data,
so eval results are reproducible by anyone who clones the repo.
"""
from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema.sql")
DB_PATH = os.path.join(HERE, "shop.db")

SEED = 42

CATEGORIES = ["Electronics", "Books", "Home", "Toys", "Clothing"]
COUNTRIES = ["US", "UK", "DE", "FR", "CA", "AU"]
STATUSES = ["completed", "completed", "completed", "pending", "cancelled", "refunded"]

FIRST = ["Ava", "Liam", "Noah", "Emma", "Olivia", "Mateo", "Sofia", "Jack",
         "Mia", "Lucas", "Aria", "Leo", "Zoe", "Ethan", "Nora", "Kai",
         "Maya", "Owen", "Ivy", "Hugo"]
LAST = ["Smith", "Garcia", "Muller", "Dubois", "Brown", "Lee", "Rossi",
        "Nguyen", "Kim", "Patel", "Walker", "Khan", "Silva", "Cohen"]

START = date(2024, 1, 1)
END = date(2025, 5, 31)


def _rand_date(rng: random.Random) -> str:
    span = (END - START).days
    return (START + timedelta(days=rng.randint(0, span))).isoformat()


def build_database(db_path: str = DB_PATH) -> str:
    rng = random.Random(SEED)

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # --- customers ---------------------------------------------------------
    customers = []
    for cid in range(1, 61):  # 60 customers
        first = rng.choice(FIRST)
        last = rng.choice(LAST)
        customers.append((
            cid,
            f"{first} {last}",
            f"{first.lower()}.{last.lower()}{cid}@example.com",
            rng.choice(COUNTRIES),
            _rand_date(rng),
        ))
    conn.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    # --- products ----------------------------------------------------------
    products = []
    for pid in range(1, 41):  # 40 products
        category = CATEGORIES[(pid - 1) % len(CATEGORIES)]
        cost = round(rng.uniform(5, 400), 2)
        price = round(cost * rng.uniform(1.2, 2.2), 2)
        products.append((pid, f"{category} Item {pid}", category, price, cost))
    conn.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    # --- orders + order_items ---------------------------------------------
    orders = []
    items = []
    item_id = 1
    for oid in range(1, 501):  # 500 orders
        cust = rng.randint(1, 60)
        orders.append((oid, cust, _rand_date(rng), rng.choice(STATUSES)))
        for _ in range(rng.randint(1, 4)):  # 1..4 line items
            pid = rng.randint(1, 40)
            list_price = products[pid - 1][3]
            # charged price wiggles a little around list price
            unit_price = round(list_price * rng.uniform(0.9, 1.05), 2)
            items.append((item_id, oid, pid, rng.randint(1, 5), unit_price))
            item_id += 1
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    conn.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)

    # --- reviews -----------------------------------------------------------
    reviews = []
    for rid in range(1, 301):  # 300 reviews
        pid = rng.randint(1, 40)
        cust = rng.randint(1, 60)
        # ratings skew positive, like real review data
        rating = rng.choices([1, 2, 3, 4, 5], weights=[1, 1, 2, 3, 4])[0]
        reviews.append((rid, pid, cust, rating, _rand_date(rng)))
    conn.executemany("INSERT INTO reviews VALUES (?,?,?,?,?)", reviews)

    conn.commit()
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customers", "products", "orders", "order_items", "reviews")
    }
    conn.close()
    print(f"Built {db_path}")
    for t, n in counts.items():
        print(f"  {t:12} {n}")
    return db_path


if __name__ == "__main__":
    build_database()
