import asyncio
from dotenv import load_dotenv
from composio import Composio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from agent import tools as _tools

load_dotenv()

# Create one authenticated Composio session; reuse its URL + headers.
# No `toolkits` scope -> the session exposes the full meta-router across the
# entire Composio catalog (1000+ apps). The model discovers tools at runtime
# via COMPOSIO_SEARCH_TOOLS and runs them through the nested
# COMPOSIO_MULTI_EXECUTE_TOOL. manage_connections=True hands the agent
# COMPOSIO_MANAGE_CONNECTIONS so it can kick off OAuth for a new app on demand.
_composio = Composio()
_session = _composio.create(
    user_id="nelson",
    manage_connections=True,
)
_URL = _session.mcp.url
_HEADERS = _session.mcp.headers


async def _with_session(run):
    """Open an MCP connection, hand the live session to `run`, return its result."""
    async with streamablehttp_client(_URL, headers=_HEADERS) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            return await run(s)


def list_tools():
    async def run(s):
        return await s.list_tools()
    return asyncio.run(_with_session(run))


def call_tool(name, arguments):
    async def run(s):
        return await s.call_tool(name, arguments)
    result = asyncio.run(_with_session(run))
    parts = [getattr(item, "text", "") for item in result.content]
    return "\n".join(p for p in parts if p) or str(result)

def _make_caller(tool_name):
    """A dispatch fn that forwards the model's args to the MCP tool."""
    def _call(**kwargs):
        return call_tool(tool_name, kwargs)
    return _call


# Heavy meta-tools we don't need for app actions — their schemas alone eat
# ~2,800 tokens, which busts small free-tier per-request limits.
_SKIP = {"COMPOSIO_REMOTE_WORKBENCH", "COMPOSIO_REMOTE_BASH_TOOL"}


def register_composio_tools():
    result = list_tools()
    registered = []
    for t in result.tools:
        if t.name in _SKIP:
            continue
        schema = {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        _tools.register(t.name, _make_caller(t.name), schema)
        registered.append(t.name)
    return registered