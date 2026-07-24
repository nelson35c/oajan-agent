from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILLS_DIR.mkdir(exist_ok=True)


def _skill_path(name):
    return SKILLS_DIR / name / "SKILL.md"


def _parse(path):
    """Return (name, description) from a SKILL.md's frontmatter."""
    name = path.parent.name          # folder name, e.g. "create-skill"
    description = ""
    for line in path.read_text().splitlines():
        if line.startswith("description:"):
            description = line.split("description:", 1)[1].strip()
            break
    return name, description


def list_skills():
    """All skills as (name, description) pairs."""
    return [_parse(p) for p in sorted(SKILLS_DIR.glob("*/SKILL.md"))]


def read_skill(name):
    """Full markdown body of one skill, or an error string."""
    path = _skill_path(name)
    if not path.exists():
        return f"Error: no skill named '{name}'"
    return path.read_text()

def save_skill(name, description, steps):
    path = _skill_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n{steps}\n"
    path.write_text(content)
    return f"Saved skill '{name}' to {path}"