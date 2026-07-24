import json
import uuid
from datetime import date
from agent import tools, trace
from agent.llm import complete
from agent.memory.store import save_memory, recall_memories
from agent.memory.session_store import save_session, load_session, list_sessions
from agent.skills import list_skills

MAX_STEPS = 8

_BASE_PROMPT = (
    "You are Oajan, a task-solving agent. Work through tasks step by step "
    "using the tools available.\n"
    f"Today's date is {date.today().isoformat()}.\n"
    "Your training data may be out of date. For anything about current events, "
    "recent facts, prices, or information you are not certain is current, use the "
    "web_search tool instead of answering from memory. Do not refuse a question "
    "as 'in the future' — check with web_search first.\n"
    "Always use the calculator for arithmetic — never compute it yourself."
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

def run_turn(messages, max_steps=MAX_STEPS):
    for step in range(1, max_steps + 1):
        message = complete(messages, tools=tools.schemas())
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            trace.tool_call(step, call.function.name, args)

            result = tools.dispatch(call.function.name, args)
            trace.tool_result(step, result)

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return f"Stopped: hit max_steps ({max_steps}) without a final answer."


def chat(resume=False):
    if resume and list_sessions():
        session_id = list_sessions()[0][0]         
        prior = load_session(session_id) or []
        print(f"Resuming session {session_id} — {len(prior)} messages restored.\n")
    else:
        session_id = str(uuid.uuid4())
        prior = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + prior
    print("Oajan ready. Type 'exit' or 'quit' to leave.\n")

    while True:
        user_input = input("you > ").strip()
        if user_input.lower() in {"exit", "quit"}:
            path = save_session(session_id, messages)
            print(f"Session saved to {path}")
            print("Goodbye.")
            break
        if not user_input:
            continue

        memories = recall_memories(user_input)
        trace.memory_recall(memories)
        if memories:
            block = "Relevant memories from past conversations:\n" + "\n".join(
                f"- {m['content']}" for m in memories
            )
            messages.append({"role": "system", "content": block})

        messages.append({"role": "user", "content": user_input})
        answer = run_turn(messages)
        print(f"\noajan > {answer}\n")

        save_memory(session_id, f"User: {user_input}\nAssistant: {answer}")