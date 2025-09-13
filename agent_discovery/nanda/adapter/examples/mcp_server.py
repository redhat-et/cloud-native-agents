#!/usr/bin/env python3

import argparse
import os
from dotenv import load_dotenv

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.responses import PlainTextResponse
import uvicorn

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
import json


# Minimal MCP server
mcp = FastMCP("nanda-mcp-server")


@mcp.tool()
async def ping(name: str = "world") -> str:
    """Return a friendly greeting. Useful for smoke tests."""
    return f"Hello, {name}! MCP is up."


@mcp.tool()
async def add(a: float, b: float) -> str:
    """
    Add two numbers and return the sum.
    Returns a JSON string like {"a": a, "b": b, "sum": a+b}.
    """
    result = a + b
    return json.dumps({"a": a, "b": b, "sum": result}, indent=2)

def create_app():
    # SSE transport publishes a /messages/ mount used for inbound posts from the client
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await mcp._mcp_server.run(read, write, mcp._mcp_server.create_initialization_options())
        return PlainTextResponse("ok")

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the minimal MCP server (SSE)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_SERVER_PORT", 6080)))
    args = parser.parse_args()

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
