from agent.tools import tool

CALCULATOR_SCHEMA = {
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


@tool(CALCULATOR_SCHEMA)
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