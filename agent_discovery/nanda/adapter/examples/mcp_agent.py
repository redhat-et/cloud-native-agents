#!/usr/bin/env python3
import os, json, asyncio
from dotenv import load_dotenv
from nanda_adapter import NANDA

# --- MCP client imports ---
from mcp import ClientSession
from mcp.client.sse import sse_client  # connects to http(s)://.../sse

# Default MCP server (your SSE endpoint)
load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:6080/sse")

async def _mcp_call(url: str, tool: str, args: dict) -> str:
    """Connect to a remote MCP server via SSE and call a tool."""
    async with sse_client(url) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)

            # Extract plain text blocks when present; otherwise return JSON
            blocks = getattr(result, "content", []) or []
            texts = []
            for b in blocks:
                # handle both dict-like and object-like blocks
                if isinstance(b, dict) and b.get("type") == "text":
                    texts.append(b.get("text", ""))
                elif hasattr(b, "type") and getattr(b, "type") == "text":
                    texts.append(getattr(b, "text", ""))
            return "\n".join([t for t in texts if t]) or json.dumps(blocks, indent=2)

def mcp_formatter(message: str) -> str:
    """
    Minimal router without '#':
    - "ping <name>" -> MCP tool `ping(name)`
    - "add <a> <b>" or "add a=<a> b=<b>" -> MCP tool `add(a,b)`
    - "query <prompt>" -> MCP tool `query(prompt)`
    - anything else -> `query(prompt=<full message>)`
    """
    text = (message or "").strip()
    if not text:
        return ""

    # Split into command and remainder
    parts = text.split()
    cmd = parts[0].lower()
    rest = text[len(parts[0]):].strip() if len(parts) > 0 else ""

    try:
        if cmd == "ping":
            name = rest if rest else "world"
            return asyncio.run(_mcp_call(MCP_SERVER_URL, "ping", {"name": name}))

        if cmd == "add":
            a_val = None
            b_val = None

            # Try named args like: a=54 b=34
            tokens = rest.split()
            for tok in tokens:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    if k == "a":
                        try:
                            a_val = float(v)
                        except Exception:
                            pass
                    if k == "b":
                        try:
                            b_val = float(v)
                        except Exception:
                            pass

            # If not named, try positional like: 54 34
            if a_val is None or b_val is None:
                nums = []
                for tok in tokens:
                    try:
                        nums.append(float(tok))
                    except Exception:
                        continue
                if len(nums) >= 2:
                    a_val = nums[0] if a_val is None else a_val
                    b_val = nums[1] if b_val is None else b_val

            if a_val is None or b_val is None:
                return "Usage: add <a> <b>  or  add a=<a> b=<b>"

            return asyncio.run(_mcp_call(MCP_SERVER_URL, "add", {"a": a_val, "b": b_val}))

        if cmd == "query":
            prompt = rest
            return asyncio.run(_mcp_call(MCP_SERVER_URL, "query", {"prompt": prompt}))

        # Default: send whole text as prompt to `query`
        return asyncio.run(_mcp_call(MCP_SERVER_URL, "query", {"prompt": text}))

    except Exception as e:
        return f"[MCP call failed] {e}"

if __name__ == "__main__":
    nanda = NANDA(mcp_formatter)
    nanda.start_server_api(
        anthropic_key=os.getenv('ANTHROPIC_API_KEY', ''),
        domain='localhost',
        agent_id=os.getenv('MCP_AGENT_ID', 'mcp_agent'),
        port=int(os.getenv('MCP_AGENT_PORT', '6006')),
        api_port=int(os.getenv('MCP_AGENT_API_PORT', '6007')),
        public_url=os.getenv('MCP_AGENT_PUBLIC_URL', 'http://localhost:6006'),
        api_url=os.getenv('MCP_AGENT_API_URL', 'http://localhost:6007'),
        ssl=os.getenv('SSL', 'false').lower() == 'true'
        )
