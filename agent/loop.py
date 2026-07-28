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

# The "soul" is the identity half of the prompt — swappable per agent (see
# agents/<name>/AGENT.md). This one is the fallback when no agent file is loaded.
_DEFAULT_SOUL = (
    "You are Oajan, a pragmatic, general-purpose task-solving assistant. "
    "Work through tasks step by step using the tools available."
)

# The operating rules are shared by every agent — they describe how the harness
# and its tools work, not who the agent is, so they are appended to any soul.
_OPERATING_RULES = (
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


def _build_system_prompt(soul=None):
    """Compose a full system prompt: an agent's soul + shared operating rules +
    the skill index. Passing no soul yields the default Oajan identity."""
    prompt = (soul or _DEFAULT_SOUL) + "\n\n" + _OPERATING_RULES
    skills = list_skills()
    if skills:
        index = "\n".join(f"- {name}: {desc}" for name, desc in skills)
        prompt += (
            "\n\nAvailable skills (reusable procedures). When a task matches one, "
            "call read_skill with its name to load the full steps, then follow them:\n"
            + index
        )
    return prompt

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


def _capture_voice():
    """Record from the mic and transcribe it. Returns the text (or None)."""
    from agent import stt
    if not stt.available():
        console.print("[yellow]Voice needs GROQ_API_KEY set in .env.[/]")
        return None
    try:
        from agent.voice_input import record_until_enter
    except Exception as exc:
        console.print(f"[yellow]Voice needs the 'sounddevice' package ({exc}).[/]")
        return None

    console.print("[dim]🎙️  Recording… press Enter to stop.[/]")
    try:
        audio = record_until_enter()
    except Exception as exc:
        console.print(f"[yellow]Couldn't access the microphone: {exc}[/]")
        return None
    if not audio:
        console.print("[dim]No audio captured.[/]")
        return None

    with console.status("[dim]Transcribing…[/]", spinner="dots"):
        try:
            return stt.transcribe(audio, "audio.wav")
        except Exception as exc:
            console.print(f"[yellow]Transcription failed: {exc}[/]")
            return None


def _activate_agent(agent, resume=False):
    """Resolve an agent and set up its thread. Returns (name, session_id, messages)."""
    from agent.agents import load_agent, DEFAULT_AGENT

    active = load_agent(agent)
    if agent and active is None:
        console.print(f"[yellow]No agent '{agent}' — using '{DEFAULT_AGENT}'.[/]")
        active = load_agent(DEFAULT_AGENT)
    name = active.name if active else DEFAULT_AGENT
    system_prompt = _build_system_prompt(active.soul if active else None)

    # Each agent namespaces its own saved threads and long-term memory.
    prefix = f"{name}-"
    threads = [s[0] for s in list_sessions() if s[0].startswith(prefix)]
    if resume and threads:
        session_id = threads[0]
        prior = load_session(session_id) or []
        console.print(f"[dim]Resuming {session_id} — {len(prior)} messages restored.[/]")
    else:
        session_id = prefix + str(uuid.uuid4())
        prior = []

    messages = [{"role": "system", "content": system_prompt}] + prior
    return name, session_id, messages


def chat(resume=False, agent=None):
    from agent.agents import list_agents

    name, session_id, messages = _activate_agent(agent, resume=resume)

    banner = Group(
        _gradient_logo(OAJAN_LOGO),
        Text(
            f"{name}  ·  {MODEL}  ·  {len(tools.schemas())} tools  ·  "
            f"{len(list_skills())} skills  ·  /voice to speak  ·  Ctrl+C to stop  ·  "
            f"type 'exit' to leave",
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
        low = user_input.lower()
        if low in {"exit", "quit"}:
            save_session(session_id, messages)
            console.print("[dim]Session saved. Goodbye.[/]")
            break
        if low == "/agents":
            for n, desc in list_agents():
                mark = "[cyan]→[/]" if n == name else " "
                console.print(f"{mark} [bold]{n}[/] — {desc}")
            continue
        if low == "/agent" or low.startswith("/agent "):
            from agent.agents import load_agent
            target = user_input.split(maxsplit=1)[1].strip() if " " in user_input else ""
            if not target:
                console.print(f"[dim]Current agent: [cyan]{name}[/]. Usage: /agent <name>[/]")
            elif load_agent(target) is None:
                console.print(f"[yellow]No agent '{target}'. Try /agents.[/]")
            else:
                save_session(session_id, messages)
                name, session_id, messages = _activate_agent(target)
                console.print(f"[dim]Switched to [cyan]{name}[/].[/]")
            continue
        if low in {"/voice", "/v"}:
            spoken = _capture_voice()
            if not spoken:
                continue
            console.print(f"[dim]🎙️  heard:[/] {spoken}")
            user_input = spoken
        if not user_input:
            continue
        console.rule(style="grey37")
        console.print()

        memories = recall_memories(user_input, session_id=name)
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
            with console.status(f"[dim]{name} is thinking…[/]", spinner="dots"):
                answer = run_turn(messages, session_id=session_id)

        console.print(f"\n[bold cyan]{name} ›[/]")
        console.print(Markdown(answer))

        if answer != STOP_MESSAGE:
            save_memory(name, f"User: {user_input}\nAssistant: {answer}")