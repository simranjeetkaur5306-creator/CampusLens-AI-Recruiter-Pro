import json
from functools import lru_cache
from pathlib import Path

LEARNING_FILE = Path(__file__).resolve().parent.parent / "data" / "learning.json"


@lru_cache(maxsize=1)
def load_learning():
    with open(LEARNING_FILE, encoding="utf-8") as handle:
        data = json.load(handle)
    curated = {name.lower(): entry for name, entry in data["skills"].items()}
    return curated, data["category_defaults"], data["default"]


def guidance_for(skill_name, category=""):
    """What to study and what to build for a skill.

    Skills with an entry in learning.json get hand-written ("curated") guidance. All other skills
    get generic guidance for their category, or a default for skills we know nothing about.
    Nothing here is generated at run time, so it can never invent facts about a skill.
    """
    curated, category_defaults, default = load_learning()
    entry = curated.get(skill_name.lower())
    if entry is not None:
        return {"topics": list(entry["topics"]), "project_idea": entry["project"], "source": "curated"}
    entry = category_defaults.get(category, default)
    return {
        "topics": [topic.format(skill=skill_name) for topic in entry["topics"]],
        "project_idea": entry["project"].format(skill=skill_name),
        "source": "generic",
    }