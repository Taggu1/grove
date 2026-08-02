import sqlite3
import os

HERE = os.path.dirname(__file__)
DB_PATH = os.path.join(HERE, "groove_merchant.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    conn.executemany(
        "INSERT INTO stores (id, name, city) VALUES (?,?,?)",
        [(1, "Groove Merchant - Downtown", "Cairo"), (2, "Groove Merchant - Maadi", "Cairo")],
    )

    conn.executemany(
        "INSERT INTO staff (id, store_id, name, role) VALUES (?,?,?,?)",
        [
            (1, 1, "Nadia (clerk)", "clerk"),
            (2, 1, "Omar (buyer)", "buyer"),
            (3, 2, "Farah (clerk)", "clerk"),
        ],
    )

    conn.executemany(
        "INSERT INTO customers (id, name, email) VALUES (?,?,?)",
        [
            (1, "Karim Adel", "karim@example.com"),
            (2, "Salma Fathy", "salma@example.com"),
        ],
    )

    # normal + edge case inventory: mix of formats, conditions, one zero-quantity edge case
    conn.executemany(
        "INSERT INTO inventory_items (store_id, title, format, condition, price, quantity) VALUES (?,?,?,?,?,?)",
        [
            (1, "Kind of Blue", "vinyl", "mint", 45.00, 3),
            (1, "Abbey Road", "vinyl", "vg", 38.00, 2),
            (1, "Thriller", "cd", "good", 8.00, 5),
            (1, "Rumours", "vinyl", "mint", 42.00, 1),
            (1, "Unknown Pleasures", "cassette", "fair", 15.00, 4),
            (1, "Discontinued Bootleg", "vinyl", "poor", 5.00, 0),  # edge case: zero stock
            (2, "The Wall", "vinyl", "good", 30.00, 2),
            (2, "Legend", "cd", "vg", 10.00, 6),
        ],
    )

    conn.commit()
    conn.close()
    print(f"Seeded database at {DB_PATH}")


if __name__ == "__main__":
    main()
