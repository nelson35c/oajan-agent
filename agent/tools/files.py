from agent.tools import tool
import os

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
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: no file found at '{path}'"

@tool(WRITE_FILE_SCHEMA)
def write_file(path, content):
    if os.path.splitext(path)[1] == "":
        path = path + ".md"
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} characters to '{path}'"

