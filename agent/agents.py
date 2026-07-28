"""Agent personas. Each agent is a folder `agents/<name>/AGENT.md` — YAML-ish
frontmatter (name, description) plus a body that IS the agent's soul: the
identity and behavior half of its system prompt. The shared operating rules
(tool mechanics) are added by the loop, so a persona only describes *who* it is.

This mirrors the skill system: file-based, self-hosting, no framework. An agent
also names a memory namespace, so different personas keep separate long-term
memory while sharing the same tools and harness.
"""

from dataclasses import dataclass
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
AGENTS_DIR.mkdir(exist_ok=True)

DEFAULT_AGENT = "oajan"


@dataclass
class Agent:
    name: str          # folder name; also the memory namespace
    description: str    # one-liner from frontmatter
    soul: str           # the identity/behavior body


def _agent_path(name):
    return AGENTS_DIR / name / "AGENT.md"


def _split_frontmatter(text):
    """Return (frontmatter_lines, body) for a `--- ... ---` header, else ([], text)."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], "\n".join(lines[i + 1:]).strip()
    return [], text.strip()


def _parse(path):
    fm, body = _split_frontmatter(path.read_text())
    description = ""
    for line in fm:
        if line.startswith("description:"):
            description = line.split("description:", 1)[1].strip()
    return Agent(name=path.parent.name, description=description, soul=body)


def list_agents():
    """All agents as (name, description) pairs."""
    return [(p.parent.name, _parse(p).description) for p in sorted(AGENTS_DIR.glob("*/AGENT.md"))]


def load_agent(name=None):
    """Load one agent by name (default if None), or None if it doesn't exist."""
    path = _agent_path(name or DEFAULT_AGENT)
    if not path.exists():
        return None
    return _parse(path)
