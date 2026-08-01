-- Groove Merchant Records: trade-in / buyback schema
-- Engine: SQLite

CREATE TABLE stores (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    city    TEXT NOT NULL
);

CREATE TABLE staff (
    id          INTEGER PRIMARY KEY,
    store_id    INTEGER NOT NULL REFERENCES stores(id),
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('clerk', 'buyer'))
);

CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    email   TEXT NOT NULL
);

CREATE TABLE inventory_items (
    id          INTEGER PRIMARY KEY,
    store_id    INTEGER NOT NULL REFERENCES stores(id),
    title       TEXT NOT NULL,
    format      TEXT NOT NULL CHECK (format IN ('vinyl', 'cd', 'cassette')),
    condition   TEXT NOT NULL CHECK (condition IN ('mint','vg','good','fair','poor')),
    price       REAL NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE trade_ins (
    id              INTEGER PRIMARY KEY,
    store_id        INTEGER NOT NULL REFERENCES stores(id),
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    staff_id        INTEGER NOT NULL REFERENCES staff(id),
    status          TEXT NOT NULL CHECK (status IN ('approved','rejected')),
    total_credit    REAL NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE trade_in_items (
    id              INTEGER PRIMARY KEY,
    trade_in_id     INTEGER NOT NULL REFERENCES trade_ins(id),
    title           TEXT NOT NULL,
    format          TEXT NOT NULL,
    condition       TEXT NOT NULL,
    offer_price     REAL NOT NULL
);

CREATE TABLE store_credits (
    id              INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    amount          REAL NOT NULL,
    trade_in_id     INTEGER NOT NULL REFERENCES trade_ins(id),
    issued_at       TEXT NOT NULL
);
