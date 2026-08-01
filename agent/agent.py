import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "mcp_server", "server.py")


async def on_progress(progress: float, total: float | None, message: str | None) -> None:
    print(f"    ... {int(progress)}/{int(total) if total else '?'}  {message or ''}")


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            print("=== 1. Capability negotiation ===")
            init_result = await session.initialize()
            caps = init_result.capabilities
            print(f"Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
            print(
                f"Declared capabilities -> tools: {bool(caps.tools)}, "
                f"resources: {bool(caps.resources)}, prompts: {bool(caps.prompts)}"
            )

            if not caps.tools:
                print("Server did not declare tool support -- refusing to call any tools.")
                return

            tools = await session.list_tools()
            print(f"Tools available: {[t.name for t in tools.tools]}\n")

            print("=== 2. Defensive tool design: process_trade_in ===")

            print("-- Clerk processes a low-value item (should succeed) --")
            result = await session.call_tool(
                "process_trade_in",
                {
                    "customer_id": 1,
                    "staff_id": 1,  # Nadia, clerk
                    "store_id": 1,
                    "items": [{"title": "Random 7\" Single", "format": "vinyl", "condition": "good", "offer_price": 12.50}],
                },
            )
            print("Result:", result.content[0].text, "| error:", result.isError)

            print("\n-- Same clerk attempts a high-value item (should be rejected) --")
            result = await session.call_tool(
                "process_trade_in",
                {
                    "customer_id": 1,
                    "staff_id": 1,  # Nadia, clerk -- not authorized above $75
                    "store_id": 1,
                    "items": [{"title": "Rare First Pressing", "format": "vinyl", "condition": "mint", "offer_price": 120.00}],
                },
            )
            print("Result:", result.content[0].text, "| error:", result.isError)

            print("\n-- A buyer processes the same high-value item (should succeed) --")
            result = await session.call_tool(
                "process_trade_in",
                {
                    "customer_id": 1,
                    "staff_id": 2,  # Omar, buyer
                    "store_id": 1,
                    "items": [{"title": "Rare First Pressing", "format": "vinyl", "condition": "mint", "offer_price": 120.00}],
                },
            )
            print("Result:", result.content[0].text, "| error:", result.isError)

            print("\n-- Implausible offer price for the condition (should be rejected) --")
            result = await session.call_tool(
                "process_trade_in",
                {
                    "customer_id": 1,
                    "staff_id": 2,
                    "store_id": 1,
                    "items": [{"title": "Beat-up Comp", "format": "cd", "condition": "poor", "offer_price": 30.00}],
                },
            )
            print("Result:", result.content[0].text, "| error:", result.isError)

            print("\n=== 3. Progress tracking: generate_inventory_valuation_report ===")
            result = await session.call_tool(
                "generate_inventory_valuation_report",
                {"store_id": 1},
                progress_callback=on_progress,
            )
            print("Final report:", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
