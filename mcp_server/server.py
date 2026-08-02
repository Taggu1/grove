import asyncio
import os
import sqlite3
from typing import Literal

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, ConfigDict, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "groove_merchant.db")

# Any trade-in containing an item offered above this line requires a
# staff member with the "buyer" role -- clerks can't self-approve high
# value buys. This is the real risk in the domain: an ungated tool here
# would let anyone drain the store's buy budget on inflated offers.
BUYER_APPROVAL_THRESHOLD = 75.00

# condition -> fraction of a $40 baseline catalog value; used as a
# sanity ceiling independent of whatever the client claims the offer is.
CONDITION_MULTIPLIERS = {"mint": 1.0, "vg": 0.75, "good": 0.5, "fair": 0.3, "poor": 0.1}

mcp = FastMCP(
    name="groove-merchant-buyback",
    instructions=(
        "Tools for processing customer trade-ins and valuing store inventory "
        "at Groove Merchant Records."
    ),
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class TradeInItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200, description="Title of the record being traded in")
    format: Literal["vinyl", "cd", "cassette"] = Field(..., description="Physical format of the item")
    condition: Literal["mint", "vg", "good", "fair", "poor"] = Field(..., description="Graded condition")
    offer_price: float = Field(..., gt=0, le=500, description="Offer price in USD for this single item")


@mcp.tool()
def process_trade_in(
    customer_id: int = Field(..., description="ID of the customer trading items in"),
    staff_id: int = Field(..., description="ID of the staff member processing this trade-in"),
    store_id: int = Field(..., description="Store where the trade-in is happening"),
    items: list[TradeInItem] = Field(..., min_length=1, max_length=25, description="Items being traded in"),
) -> dict:
    """
    Process a customer trade-in and issue store credit.

    Write tool with real stakes: it moves money (store credit) and stock.
    Any item offered above $75 requires a staff member with the 'buyer'
    role -- this is checked server-side against the staff table, never
    trusted from the client. Offer prices are also sanity-checked against
    a condition-adjusted ceiling independent of the JSON Schema bounds.
    """
    conn = get_db()
    try:
        staff = conn.execute(
            "SELECT * FROM staff WHERE id = ? AND store_id = ?", (staff_id, store_id)
        ).fetchone()
        if staff is None:
            raise ValueError(f"No staff member {staff_id} at store {store_id}; cannot authorize this trade-in.")

        customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if customer is None:
            raise ValueError(f"Customer {customer_id} does not exist.")

        # --- handler-level authorization (independent of the schema) ---
        high_value = [i for i in items if i.offer_price > BUYER_APPROVAL_THRESHOLD]
        if high_value and staff["role"] != "buyer":
            titles = ", ".join(i.title for i in high_value)
            raise PermissionError(
                f"{staff['name']} has role '{staff['role']}' and cannot approve items over "
                f"${BUYER_APPROVAL_THRESHOLD:.2f} ({titles}). A staff member with role 'buyer' "
                f"must process this trade-in."
            )

        # --- server-side validation independent of the JSON Schema ---
        for item in items:
            ceiling = 40.0 * CONDITION_MULTIPLIERS[item.condition] * 3
            if item.offer_price > ceiling:
                raise ValueError(
                    f"Offer price ${item.offer_price:.2f} for '{item.title}' ({item.condition}) "
                    f"exceeds the plausible ceiling of ${ceiling:.2f} for that condition."
                )

        total_credit = round(sum(i.offer_price for i in items), 2)

        cur = conn.execute(
            "INSERT INTO trade_ins (store_id, customer_id, staff_id, status, total_credit, created_at) "
            "VALUES (?, ?, ?, 'approved', ?, datetime('now'))",
            (store_id, customer_id, staff_id, total_credit),
        )
        trade_in_id = cur.lastrowid
        for item in items:
            conn.execute(
                "INSERT INTO trade_in_items (trade_in_id, title, format, condition, offer_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (trade_in_id, item.title, item.format, item.condition, item.offer_price),
            )
        conn.execute(
            "INSERT INTO store_credits (customer_id, amount, trade_in_id, issued_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (customer_id, total_credit, trade_in_id),
        )
        conn.commit()

        return {
            "trade_in_id": trade_in_id,
            "status": "approved",
            "total_credit_issued": total_credit,
            "approved_by": staff["name"],
            "approver_role": staff["role"],
        }
    finally:
        conn.close()


@mcp.tool()
async def generate_inventory_valuation_report(
    store_id: int = Field(..., description="Store to generate the valuation report for"),
    ctx: Context = None,
) -> dict:
    """
    Scan every inventory row for a store and compute its total valuation.

    This genuinely takes a while at real inventory sizes, so it reports
    progress per item scanned instead of leaving the client blocked with
    no feedback until a single final response.
    """
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM inventory_items WHERE store_id = ?", (store_id,)).fetchall()
        if not rows:
            raise ValueError(f"No inventory found for store {store_id}.")

        total = 0.0
        by_format: dict[str, float] = {}
        n = len(rows)

        for idx, row in enumerate(rows, start=1):
            await asyncio.sleep(0.15)  # stand-in for real per-item valuation work
            value = row["price"] * row["quantity"]
            total += value
            by_format[row["format"]] = by_format.get(row["format"], 0.0) + value
            if ctx is not None:
                await ctx.report_progress(progress=idx, total=n, message=f"Valued {idx}/{n} SKUs")

        return {
            "store_id": store_id,
            "items_scanned": n,
            "total_valuation": round(total, 2),
            "by_format": {k: round(v, 2) for k, v in by_format.items()},
        }
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
