import sys

from agent.loop import run_agent

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "What is 847 times 23, then subtract 1000?"
    print(run_agent(task))