import sys

from agent.loop import run_turn, chat, SYSTEM_PROMPT

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        print(run_turn(messages))
    else:
        chat()