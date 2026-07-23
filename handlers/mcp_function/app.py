"""McpFunction: FastMCP tools exposed over Streamable HTTP, adapted to Lambda via Mangum.

See docs/基本設計.md §6, §7.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from mangum import Mangum

from health_mcp import queries

mcp = FastMCP("apple-watch-vitalpipe")


@mcp.tool()
def get_metric_summary(metric_name: str, start_date: str, end_date: str) -> dict[str, Any]:
    """Get the average/sum/max/min of a metric over a date range."""
    return queries.get_metric_summary(metric_name, start_date, end_date)


@mcp.tool()
def get_workouts(start_date: str, end_date: str) -> dict[str, Any]:
    """List workouts recorded within a date range."""
    return queries.get_workouts(start_date, end_date)


@mcp.tool()
def get_sleep_summary(start_date: str, end_date: str) -> dict[str, Any]:
    """Summarize sleep (time asleep/in bed/stage breakdown) over a date range."""
    return queries.get_sleep_summary(start_date, end_date)


@mcp.tool()
def get_trend(metric_name: str, days: int) -> dict[str, Any]:
    """Compute the trend (least-squares slope and change rate) of a metric over the last N days."""
    return queries.get_trend(metric_name, days)


# stateless_http=True: a Lambda invocation may land on any warm execution
# environment, so the MCP session can't rely on in-memory state surviving
# between requests the way a long-running server would.
_asgi_app = mcp.http_app(transport="streamable-http", stateless_http=True)

handler = Mangum(_asgi_app)
