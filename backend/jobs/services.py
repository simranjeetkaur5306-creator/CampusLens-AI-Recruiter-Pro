import json
import re
from functools import lru_cache

from resumes.models import Skill
from resumes.services.skill_extraction import SKILLS_FILE


def _key(text):
    """Lower-case and treat spaces/hyphens alike: "Machine-Learning" == "machine learning"."""
    return re.sub(r"[\s\-]+", " ", text.strip().lower())


@lru_cache(maxsize=1)
def _alias_lookup():
    """Maps every name/alias in skills.json (any case) to (canonical name, category)."""
    with open(SKILLS_FILE, encoding="utf-8") as handle:
        entries = json.load(handle)
    lookup = {}
    for entry in entries:
        value = (entry["name"], entry.get("category", ""))
        for alias in [entry["name"], *entry.get("aliases", []), *entry.get("cs", [])]:
            lookup.setdefault(_key(alias), value)
    return lookup


def canonical_skill(name):
    """Returns (canonical_name, category) for a skill typed by a recruiter.

    The WHOLE typed text must match a known name or alias ("ml", "ML", "sklearn", "nodejs"
    become Machine Learning, Machine Learning, Scikit-learn, Node.js). Anything else is kept
    exactly as typed. Using the same names as the resume parser keeps resume skills and job
    skills comparable, which later phases need for matching and skill-gap analysis.
    """
    cleaned = " ".join(name.split())
    return _alias_lookup().get(_key(cleaned), (cleaned, ""))


def resolve_skills(names):
    """Turns a list of typed skill names into unique Skill rows (created if new)."""
    skills, seen = [], set()
    for raw in names:
        canonical, category = canonical_skill(raw)
        key = canonical.lower()
        if key in seen:
            continue
        seen.add(key)
        skill = Skill.objects.filter(name__iexact=canonical).first()
        if skill is None:
            skill = Skill.objects.create(name=canonical, category=category)
        skills.append(skill)
    return skills