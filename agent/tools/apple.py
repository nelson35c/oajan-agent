import subprocess
import sys

from agent.tools import tool

def _osa(script, timeout=30):
    """Run an AppleScript via osascript"""
    if sys.platform != "darwin":
        return "Error: Apple tools only works on macOS"
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "Error: the apple app took to long to respond"
    if result.returncode != 0:
        return f"Error from AppleScript: {result.stderr.strip()}"
    return result.stdout.strip() or "Done"

CREATE_NOTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_note",
        "description": "Create a new note in the macOS Notes app.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The notes title (first line)"},
                "body": {"type": "string", "description": "The notes body text"},

            },
            "required": ["title", "body"],
        },
    },
}

@tool(CREATE_NOTE_SCHEMA)
def create_note(title, body):
    script = f'tell application "Notes" to make new note with properties {{body:"{title}" & return & "{body}"}}'
    return _osa(script)
