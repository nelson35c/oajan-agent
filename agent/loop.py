import json

from agent import tools
from agent.llm import complete

MAX_STEPS = 8

SYSTEM_PROMPT = (
    "You are Oajan, a task-solving agent. Work through tasks step by step "
    "using the tools available. Always use the calculator for arithmetic — "
    "never compute it yourself."
)


def run_agent(task, max_steps=MAX_STEPS):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        message = complete(messages, tools=tools.schemas())
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"[{step}] → {call.function.name}({args})")

            result = tools.dispatch(call.function.name, args)
            print(f"[{step}] ← {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return f"Stopped: hit max_steps ({max_steps}) without a final answer."