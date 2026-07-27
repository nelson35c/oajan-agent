"""Direct Composio SDK tools (top-level args) — bypasses the MCP meta-router.

The MCP tool-router only exposes 7 meta-tools and requires the model to nest
arguments inside COMPOSIO_MULTI_EXECUTE_TOOL, which weaker models can't do.
Here we fetch specific app tools as first-class OpenAI schemas and execute them
directly, so the model fills top-level args the same way it does for local tools.
"""

from dotenv import load_dotenv
from composio import Composio

from agent import tools as _tools

load_dotenv()

_composio = Composio()
_USER_ID = "nelson"

# Specific app tools to expose directly. Add more slugs / toolkits as needed.
_APP_TOOLS = [
    "GMAIL_CREATE_EMAIL_DRAFT",
    "GMAIL_SEND_EMAIL",
    "GMAIL_FETCH_EMAILS",
]


def _make_caller(slug):
    def _call(**kwargs):
        return _composio.tools.execute(
            slug,
            arguments=kwargs,
            user_id=_USER_ID,
            dangerously_skip_version_check=True,
        )
    return _call


def register_composio_tools():
    schemas = _composio.tools.get(user_id=_USER_ID, tools=_APP_TOOLS)
    registered = []
    for schema in schemas:
        if "type" not in schema:
            schema = {"type": "function", **schema}
        name = schema["function"]["name"]
        _tools.register(name, _make_caller(name), schema)
        registered.append(name)
    return registered
