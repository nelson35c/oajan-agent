from agent.tools import tool
from agent import skills

READ_SKILL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_skill",
        "description": "Load the full step-by-step instructions of a skill by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The skill name (its folder name)"},
            },
            "required": ["name"],
        },
    },
}

@tool(READ_SKILL_SCHEMA)
def read_skill(name):
    return skills.read_skill(name)



SAVE_SKILL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_skill",
        "description": "Create a new reusable skill: writes a SKILL.md with the given name, description, and step-by-step body.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Lowercase-hyphenated skill name"},
                "description": {"type": "string", "description": "One sentence, 60 chars or fewer, stating what the skill does"},
                "steps": {"type": "string", "description": "The full markdown body: numbered, executable steps"},
            },
            "required": ["name", "description", "steps"],
        },
    },
}

@tool(SAVE_SKILL_SCHEMA)
def save_skill(name, description, steps):
    return skills.save_skill(name, description, steps)