import os
from agent.tools import tool
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent/ "workspace"
WORKSPACE.mkdir(exist_ok=True)

def _safe_path(path):
    candidate = (WORKSPACE / path.lstrip("/\\")).resolve()
    if not candidate.is_relative_to(WORKSPACE):
        return None
    return candidate

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read and return the full text contents of a file at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write text to a file at the given path, overwriting any existing contents. If no file extension is give, the file is saved as a Markdown (.md).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Text to write into the file"},
            },
            "required": ["path", "content"],
        },
    },
}

@tool(READ_FILE_SCHEMA)
def read_file(path):
    safe = _safe_path(path)
    if safe is None:
        return f"Error: '{path}' is outside of Oajan's worksapce and cannot be accessed"
    try:
       return safe.read_text()
    except FileNotFoundError:
        return f"Error: no file found at '{path}'"

@tool(WRITE_FILE_SCHEMA)
def write_file(path, content):
    if os.path.splitext(path)[1] == "":
        path = path + ".md"
    safe = _safe_path(path)
    if safe is None:
        return f"Error: '{path}' is outside of Oajan's workspace and cannot be written"
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content)
    return f"Wrote {len(content)} characters to '{safe.name}'"

