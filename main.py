import sys

from agent.loop import run_turn, chat, SYSTEM_PROMPT
from agent import trace

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--verbose" in args:
        trace.set_verbose(True)
        args = [a for a in args if a != "--verbose"]

    if not args:
        from agent.mcp_client import register_composio_tools
        register_composio_tools()
        chat()
    elif args[0] == "--resume":
        from agent.mcp_client import register_composio_tools
        register_composio_tools()
        chat(resume=True)
    else:
        from agent.mcp_client import register_composio_tools
        register_composio_tools()
        task = " ".join(args)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        print(run_turn(messages))