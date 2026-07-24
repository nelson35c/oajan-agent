import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.loop import run_turn, SYSTEM_PROMPT
from agent.tools.files import WORKSPACE
from agent.skills import SKILLS_DIR


def run_task(task):
    """Run one task through the agent, return the final answer text."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    return run_turn(messages) or ""


def _cleanup():
    """Remove artifacts so eval runs are repeatable and don't false-pass."""
    (WORKSPACE / "eval-test.md").unlink(missing_ok=True)
    skill_dir = SKILLS_DIR / "eval-greeting"
    if skill_dir.exists():
        shutil.rmtree(skill_dir)


# Each case: (name, task, check(answer) -> bool).
# Checks assert on substance or observable side effects, never exact text —
# the model's phrasing varies every run.
CASES = [
    (
        "calculator",
        "What is 47 times 89?",
        lambda a: "4183" in a.replace(",", ""),   # tolerate "4,183"
    ),
    (
        "multi_step_math",
        "What is 8 times 7, then add 6 to the result?",
        lambda a: "62" in a.replace(",", ""),
    ),
    (
        "web_search_factual",
        "Who won the 2022 FIFA World Cup? Answer with just the country.",
        lambda a: "argentina" in a.lower(),
    ),
    (
        "file_write_sandboxed",
        "Write the text 'hello evals' to a file called eval-test",
        lambda a: (WORKSPACE / "eval-test.md").exists(),
    ),
    (
        "skill_authoring",
        "Create a skill named eval-greeting that greets a user by their name.",
        lambda a: (SKILLS_DIR / "eval-greeting" / "SKILL.md").exists(),
    ),
]


def main():
    _cleanup()
    passed = 0
    for name, task, check in CASES:
        try:
            answer = run_task(task)
            ok = check(answer)
        except Exception as exc:
            ok = False
            answer = f"ERROR: {exc}"
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            print(f"       task:   {task}")
            print(f"       answer: {answer[:120]}")
    print(f"\n{passed}/{len(CASES)} passed")
    _cleanup()


if __name__ == "__main__":
    main()
