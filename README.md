# Groove Merchant Records — Buyback MCP Server

## Scope of this piece

The full lab asks for eight protocol concerns. **This piece implements
three: capability negotiation, defensive tool design, and progress
tracking.** Notifications, elicitation, resources, prompts, and the
remote (Streamable HTTP) transport are the rest of the team's pieces
and aren't built here — don't grade this folder against those.

## The company & problem

Groove Merchant Records is a small two-store used-record chain that
buys music back from customers for store credit ("trade-ins"). Today a
clerk eyeballs a record's condition and writes an offer on a paper
slip. The risk of handing an LLM this workflow directly: a model could
approve an inflated offer on a whim, or let a junior clerk sign off on
a buy that should need a manager, and there'd be no server-side check
stopping it — only whatever the model happened to do that time.

The server sits in front of a SQLite database and exposes exactly two
tools, not raw SQL access.

## Database / ERD

`db/schema.sql` — `stores`, `staff` (role: `clerk`/`buyer`),
`customers`, `inventory_items`, `trade_ins`, `trade_in_items`,
`store_credits`. See `db/erd.md` for the Mermaid ERD. Seed data
(`db/seed.py`) covers normal inventory plus an edge case (a zero-stock
item).

## How each concern shows up here

- **Capability negotiation** (`agent/agent.py`): the client calls
  `session.initialize()`, reads back the server's declared
  `capabilities`, and only proceeds to list/call tools if
  `capabilities.tools` is actually present — it doesn't assume the
  server supports everything.
  *Known limitation:* this version of the MCP SDK's `FastMCP` also
  reports `resources`/`prompts` capabilities as present by default,
  even though none are registered in this piece yet. That becomes
  accurate once the teammate responsible for resources/prompts adds
  them; the negotiation logic itself (the client checking before
  relying on a capability) is real and doesn't change.

- **Defensive tool design** (`mcp_server/server.py`,
  `process_trade_in`): real JSON Schema constraints (required fields,
  `additionalProperties: false` via Pydantic's `extra="forbid"`, enums
  for format/condition, bounds on price and item count) — plus two
  things the schema *can't* express: a server-side sanity ceiling on
  offer price per condition, and a handler-level authorization check
  that looks up the staff member's role from the database (never
  trusts a client-supplied role) before allowing any item over $75 to
  be approved.

- **Progress tracking** (`generate_inventory_valuation_report`): scans
  every inventory row for a store and reports `ctx.report_progress()`
  after each item instead of blocking silently until one final
  response — genuinely useful once a store's catalog is large.

## Read-only vs. write

| Tool | Type | Requires elevated role? |
|---|---|---|
| `process_trade_in` | write (inserts trade-in, items, and store credit) | only for items over $75 |
| `generate_inventory_valuation_report` | read-only | no |

If a client connects without declaring it can handle tool calls at
all, the agent here refuses to proceed rather than calling tools blind
(see the capability check above).

## Running it

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python db/seed.py            # builds db/groove_merchant.db
python agent/agent.py        # launches the server over stdio and runs the demo
```

The agent script walks through all three concerns in order: capability
check, four `process_trade_in` calls (clerk approved, clerk rejected,
buyer approved, implausible-price rejected), then a progress-reporting
valuation report.

## Transport

stdio, since this piece is still in development — the rest of the
team's remote/Streamable HTTP transition happens elsewhere in the repo
per the team's transport decision.
