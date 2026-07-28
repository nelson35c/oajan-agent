import sys

from agent.loop import run_turn, chat, _build_system_prompt
from agent import trace

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--verbose" in args:
        trace.set_verbose(True)
        args = [a for a in args if a != "--verbose"]

    # --agent <name> picks a persona (agents/<name>/AGENT.md); default otherwise.
    agent_name = None
    if "--agent" in args:
        i = args.index("--agent")
        if i + 1 < len(args):
            agent_name = args[i + 1]
            del args[i:i + 2]
        else:
            del args[i]

    from agent.mcp_client import register_composio_tools
    register_composio_tools()

    if args and args[0] == "--telegram":
        from agent.gateway.telegram import run as run_telegram
        run_telegram()
    elif not args:
        chat(agent=agent_name)
    elif args[0] == "--resume":
        chat(resume=True, agent=agent_name)
    else:
        from agent.agents import load_agent
        active = load_agent(agent_name)
        task = " ".join(args)
        messages = [
            {"role": "system", "content": _build_system_prompt(active.soul if active else None)},
            {"role": "user", "content": task},
        ]
        print(run_turn(messages))
