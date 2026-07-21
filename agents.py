import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

MODEL = os.getenv("GEMINI_CHAT_MODEL")
MAX_STEPS = 8

SYSTEM_PROMPT = (
    """You are Oajan, a task-solving agent. Work through tasks step by step 
    using the tools available. Always use the calculator for arithmetic  
    never compute it yourself."""
)

def calculator(a, b, operation):
    if operation == "add":
        return a + b
    if operation == "subtract":
        return a - b
    if operation == "multiply":
        return a * b
    if operation == "divide":
        return a / b if b != 0 else "Error: cannot divide by zero"
    return f"Error: unknown operation '{operation}'"

calculator_schema = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Perform arithmetic on two numbers. Use this for any calculation instead of computing it yourself.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "The first number"},
                "b": {"type": "number", "description": "The second number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The arithmetic operation to perform",
                },
            },
            "required": ["a", "b", "operation"],
        },
    },
}

TOOLS = {"calculator": calculator}
TOOL_SCHEMAS = [calculator_schema]

def run_agent(task, max_steps=MAX_STEPS):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            print(f"[{step}] → {name}({args})")

            fn = TOOLS.get(name)
            if fn is None:
                result = f"Error: no tool named '{name}'"
            else:
                try:
                    result = fn(**args)
                except Exception as exc:
                    result = f"Error running {name}: {exc}"

            print(f"[{step}] ← {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return f"Stopped: hit max_steps ({max_steps}) without a final answer."


if __name__ == "__main__":
    task = "What is 847 times 23, and then subtract 1000 from that result?"
    print(run_agent(task))

