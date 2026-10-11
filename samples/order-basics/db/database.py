"""Load and check the small locked fixture in this sample's MariaDB database."""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from decimal import Decimal


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "order-basics"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fixture():
    lock = json.loads((ROOT / "dataset.lock").read_text())
    require(set(lock["files"]) == {"products.csv", "orders.csv"}, "invalid data inventory")
    rows = {}
    for name, digest in lock["files"].items():
        path = ROOT / "data" / name
        require("sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() == digest, "data digest mismatch")
        with path.open() as source:
            rows[name] = list(csv.DictReader(source))
    return rows, hashlib.sha256((ROOT / "dataset.lock").read_bytes()).hexdigest()


def connection():
    import pymysql

    require(os.environ["MYSQL_DATABASE"] == "order_basics", "unexpected database")
    require(os.environ.get("BKN_SAMPLE_ID", SAMPLE) == SAMPLE, "unexpected sample")
    options = dict(user=os.environ["MYSQL_USER"], password=os.environ.get("MYSQL_PASSWORD", ""),
                   database="order_basics", charset="utf8mb4")
    if os.environ.get("MYSQL_UNIX_SOCKET"):
        options["unix_socket"] = os.environ["MYSQL_UNIX_SOCKET"]
    else:
        options.update(host=os.environ["MYSQL_HOST"], port=int(os.environ.get("MYSQL_PORT", "3306")))
    return pymysql.connect(**options)


def verify(conn, digest):
    with conn.cursor() as q:
        q.execute("SELECT sample_version,status,data_digest FROM bkn_sample_meta WHERE sample_id=%s", (SAMPLE,))
        require(q.fetchone() == (os.environ["BKN_SAMPLE_VERSION"], "ready", digest), "database identity is not ready")
        q.execute("SELECT COUNT(*) FROM products")
        require(q.fetchone()[0] == 3, "product count differs")
        q.execute("SELECT COUNT(*),SUM(quantity) FROM orders")
        require(q.fetchone() == (4, Decimal(8)), "order count or quantity differs")
        q.execute("SELECT COUNT(*),SUM(o.quantity*p.unit_price) FROM orders o JOIN products p ON o.product_id=p.product_id")
        require(q.fetchone() == (4, Decimal(750)), "joined amount differs")
    print(json.dumps({"ok": True, "products": 3, "orders": 4, "quantity": 8, "amount": 750}))


def main():
    rows, digest = fixture()
    with connection() as conn:
        if sys.argv[1] == "init":
            with conn.cursor() as q:
                q.execute("SHOW TABLES")
                existing = q.fetchall()
                if not existing:
                    q.execute("CREATE TABLE bkn_sample_meta (sample_id VARCHAR(32) PRIMARY KEY, sample_version VARCHAR(32), status VARCHAR(16), data_digest VARCHAR(64))")
                    q.execute("CREATE TABLE products (product_id VARCHAR(32) PRIMARY KEY, product_name VARCHAR(64), unit_price DECIMAL(12,2))")
                    q.execute("CREATE TABLE orders (order_id VARCHAR(32) PRIMARY KEY, product_id VARCHAR(32), quantity INT)")
                    q.executemany("INSERT INTO products VALUES (%s,%s,%s)", [(r['product_id'], r['product_name'], r['unit_price']) for r in rows['products.csv']])
                    q.executemany("INSERT INTO orders VALUES (%s,%s,%s)", [(r['order_id'], r['product_id'], r['quantity']) for r in rows['orders.csv']])
                    q.execute("INSERT INTO bkn_sample_meta VALUES (%s,%s,'ready',%s)", (SAMPLE, os.environ["BKN_SAMPLE_VERSION"], digest))
                    conn.commit()
                # An existing database is only read and verified, never cleared or overwritten.
        elif sys.argv[1] != "verify":
            raise ValueError("expected init or verify")
        verify(conn, digest)


if __name__ == "__main__":
    main()
