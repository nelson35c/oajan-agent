_REGISTRY = {}


def tool(schema):
    """Register a function as an agent tool with its JSON schema."""
    def decorator(fn):
        _REGISTRY[schema["function"]["name"]] = (fn, schema)
        return fn
    return decorator

def schemas():
    return [schema for _, schema in _REGISTRY.values()]

def dispatch(name, args):
    entry = _REGISTRY.get(name)
    if entry is None:
        return f"Error: no tool named '{name}' "
    fn, _ = entry

    try: 
        return fn(**args)
    except Exception as exc:
        return f"Error running {name}: {exc}"

from agent.tools import calculator
from agent.tools import files
from agent.tools import web_search
from agent.tools import apple



