import sys

from agent.loop import run_turn, chat, SYSTEM_PROMPT

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        chat()
    elif args[0] == "--resume":
        chat(resume=True)
    else:
        task = " ".join(args)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        print(run_turn(messages))