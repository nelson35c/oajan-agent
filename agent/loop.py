import json
import uuid
from datetime import date
from agent import tools, trace
from agent.llm import complete, MODEL
from agent.memory.store import save_memory, recall_memories
from agent.memory.session_store import save_session, load_session, list_sessions
from agent.skills import list_skills
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

OAJAN_LOGO = r"""
 ██████╗  █████╗      ██╗ █████╗ ███╗   ██╗
██╔═══██╗██╔══██╗     ██║██╔══██╗████╗  ██║
██║   ██║███████║     ██║███████║██╔██╗ ██║
██║   ██║██╔══██║██   ██║██╔══██║██║╚██╗██║
╚██████╔╝██║  ██║╚█████╔╝██║  ██║██║ ╚████║
 ╚═════╝ ╚═╝  ╚═╝ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝

 █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
"""

console = Console()

MAX_STEPS = 8
MAX_TOOL_RESULT_CHARS = 50000   # generous cap (Perplexity has a large context); keeps Composio schemas intact
STOP_MESSAGE = "⏹  Stopped."    # returned when the user interrupts a running turn with Ctrl+C

_BASE_PROMPT = (
    "You are Oajan, a task-solving agent. Work through tasks step by step "
    "using the tools available.\n"
    f"Today's date is {date.today().isoformat()}.\n"
    "Your training data may be out of date. For anything about current events, "
    "recent facts, prices, or information you are not certain is current, use the "
    "web_search tool instead of answering from memory. Do not refuse a question "
    "as 'in the future' — check with web_search first.\n"
    "Always use the calculator for arithmetic — never compute it yourself.\n"
    "You reach external apps (Gmail, Slack, GitHub, Notion, and 1000+ more) "
    "through the Composio meta-router. The flow is: (1) call COMPOSIO_SEARCH_TOOLS "
    "with a plain-language query (e.g. 'create a gmail draft') to find the exact "
    "tool slug; (2) if unsure of a tool's parameters, call COMPOSIO_GET_TOOL_SCHEMAS "
    "for that slug; (3) call COMPOSIO_MULTI_EXECUTE_TOOL to run it. "
    "When calling COMPOSIO_MULTI_EXECUTE_TOOL, you MUST fill each tool's "
    "'arguments' object with the actual parameter values (for example "
    "recipient_email, subject, body for a Gmail draft). NEVER send an empty "
    "'arguments': {} — that produces a blank, invalid result. Only include the "
    "specific tool you need; do not batch unrelated read tools. "
    "If a tool fails because the app is not connected, call "
    "COMPOSIO_MANAGE_CONNECTIONS to start the OAuth flow and give the user the link."
)

def _build_system_prompt():
    skills = list_skills()
    if not skills:
        return _BASE_PROMPT
    index = "\n".join(f"- {name}: {desc}" for name, desc in skills)
    return (
        _BASE_PROMPT
        + "\n\nAvailable skills (reusable procedures). When a task matches one, "
          "call read_skill with its name to load the full steps, then follow them:\n"
        + index
    )

SYSTEM_PROMPT = _build_system_prompt()

def _msg_field(m, key):
    """Read a field from a message that may be a dict or an SDK object."""
    return m.get(key) if isinstance(m, dict) else getattr(m, key, None)


def _seal_pending_tool_calls(messages):
    """After an interrupt, add a placeholder result for every tool_call that
    never got one. The chat APIs require each tool_call to be followed by a
    matching tool result, so this keeps the history valid for the next turn."""
    answered = {
        _msg_field(m, "tool_call_id")
        for m in messages
        if _msg_field(m, "role") == "tool"
    }
    for m in messages:
        for call in _msg_field(m, "tool_calls") or []:
            if call.id not in answered:
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": "[Interrupted by user before this tool ran.]",
                })
                answered.add(call.id)


def run_turn(messages, max_steps=MAX_STEPS, session_id=None):
    with trace.turn(messages, session_id=session_id) as span:
        answer = None
        try:
            for step in range(1, max_steps + 1):
                message = complete(messages, tools=tools.schemas())
                messages.append(message)

                if not message.tool_calls:
                    answer = message.content
                    break

                for call in message.tool_calls:
                    args = json.loads(call.function.arguments)
                    with trace.tool_span(step, call.function.name, args) as obs:
                        result = tools.dispatch(call.function.name, args)
                        obs.set(result)

                    content = str(result)
                    if len(content) > MAX_TOOL_RESULT_CHARS:
                        content = content[:MAX_TOOL_RESULT_CHARS] + "\n...[truncated]"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": content,
                    })
            else:
                answer = f"Stopped: hit max_steps ({max_steps}) without a final answer."
        except KeyboardInterrupt:
            _seal_pending_tool_calls(messages)
            answer = STOP_MESSAGE

        trace.set_turn_output(span, answer)
    return answer

def _gradient_logo(art, start=(45, 212, 191), end=(59, 130, 246)):
    """Render the logo with a vertical color fade from `start` to `end` RGB."""
    lines = art.strip("\n").splitlines()
    n = len(lines)
    out = Text()
    for i, line in enumerate(lines):
        t = i / max(n - 1, 1)                      
        r = int(start[0] + (end[0] - start[0]) * t)
        g = int(start[1] + (end[1] - start[1]) * t)
        b = int(start[2] + (end[2] - start[2]) * t)
        out.append(line + "\n", style=f"bold #{r:02x}{g:02x}{b:02x}")
    return out


def chat(resume=False):
    if resume and list_sessions():
        session_id = list_sessions()[0][0]
        prior = load_session(session_id) or []
        console.print(f"[dim]Resuming session {session_id} — {len(prior)} messages restored.[/]")
    else:
        session_id = str(uuid.uuid4())
        prior = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + prior

    banner = Group(
        _gradient_logo(OAJAN_LOGO),
        Text(
            f"{MODEL}  ·  {len(tools.schemas())} tools  ·  "
            f"{len(list_skills())} skills  ·  Ctrl+C to stop  ·  type 'exit' to leave",
            style="dim",
        ),
    )
    console.print(Panel.fit(banner, border_style="#2dd4bf", padding=(1, 4)))

    while True:
        console.rule(style="grey37")
        try:
            user_input = console.input("[bold green]you ›[/] ").strip()
        except KeyboardInterrupt:
            # Ctrl+C at an idle prompt cancels the line rather than quitting.
            console.print("[dim](type 'exit' to leave)[/]")
            continue
        except EOFError:
            # Ctrl+D quits cleanly, like 'exit'.
            save_session(session_id, messages)
            console.print("\n[dim]Session saved. Goodbye.[/]")
            break
        if user_input.lower() in {"exit", "quit"}:
            save_session(session_id, messages)
            console.print("[dim]Session saved. Goodbye.[/]")
            break
        if not user_input:
            continue
        console.rule(style="grey37")
        console.print()

        memories = recall_memories(user_input)
        trace.memory_recall(memories)
        if memories:
            block = "Relevant memories from past conversations:\n" + "\n".join(
                f"- {m['content']}" for m in memories
            )
            messages.append({"role": "system", "content": block})

        messages.append({"role": "user", "content": user_input})

        if trace.is_verbose():
            answer = run_turn(messages, session_id=session_id)
        else:
            with console.status("[dim]Oajan is thinking…[/]", spinner="dots"):
                answer = run_turn(messages, session_id=session_id)

        console.print("\n[bold cyan]oajan ›[/]")
        console.print(Markdown(answer))

        if answer != STOP_MESSAGE:
            save_memory(session_id, f"User: {user_input}\nAssistant: {answer}")