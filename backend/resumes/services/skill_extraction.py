import json
import re
from functools import lru_cache
from pathlib import Path

SKILLS_FILE = Path(__file__).resolve().parent.parent / "data" / "skills.json"

# A skill must not be glued to other letters/digits/+/#  ("Java" must not match
# inside "JavaScript", "SQL" must not match inside "MySQL") and must not be the
# start of a dotted word ("Node" in "Node.js" is handled by the alias "nodejs").
_LEFT = r"(?<![\w+#])"
_RIGHT = r"(?![\w+#])(?!\.\w)"


def _alias_pattern(alias):
    escaped = re.escape(alias.strip())
    escaped = re.sub(r"(?:\\ )+", r"[\\s\\-]+", escaped)  # "machine learning" also matches "machine-learning"
    return f"{_LEFT}{escaped}{_RIGHT}"


@lru_cache(maxsize=1)
def load_skill_catalog():
    """Reads skills.json once and compiles one regex per skill."""
    with open(SKILLS_FILE, encoding="utf-8") as handle:
        entries = json.load(handle)

    catalog = []
    for entry in entries:
        insensitive = list(entry.get("aliases", []))
        if entry.get("match_name", True):
            insensitive.append(entry["name"])
        sensitive = list(entry.get("cs", []))  # e.g. "ML", "AI": only matched in this exact case

        patterns = []
        if insensitive:
            patterns.append(
                re.compile("|".join(_alias_pattern(a) for a in insensitive), re.IGNORECASE)
            )
        if sensitive:
            patterns.append(re.compile("|".join(_alias_pattern(a) for a in sensitive)))
        catalog.append(
            {"name": entry["name"], "category": entry.get("category", ""), "patterns": patterns}
        )
    return catalog


def extract_skills(text):
    """Returns the skills found in the text as [{"name": ..., "category": ...}].

    Only skills that are present in skills.json AND literally written in the
    resume are returned. Nothing is guessed or added.
    """
    if not text:
        return []
    found = []
    for skill in load_skill_catalog():
        if any(pattern.search(text) for pattern in skill["patterns"]):
            found.append({"name": skill["name"], "category": skill["category"]})
    return sorted(found, key=lambda item: item["name"].lower())