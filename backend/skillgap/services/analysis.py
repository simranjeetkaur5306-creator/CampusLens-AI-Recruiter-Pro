import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from jobs.services import canonical_skill

from .learning import guidance_for

GRAPH_FILE = Path(__file__).resolve().parent.parent / "data" / "skill_graph.json"

MATCHED, PARTIAL, MISSING = "matched", "partial", "missing"
PARTIAL_WEIGHT = 0.5
COVERAGE_RULE = "matched skill = 1 point, partially matched skill = 0.5 point, missing skill = 0"
DISCLAIMER = (
    "Based only on the skills found in the resume text. A skill you have but did not write on your "
    "resume is not counted. The learning suggestions are general guidance, not a promise of a result."
)


@lru_cache(maxsize=1)
def load_graph():
    """Returns (builds_on, related), both keyed by lower-case skill name.

    builds_on["django"] = ["Python"]            Django normally requires knowing Python
    related["pytorch"]  = {"TensorFlow", ...}   skills from the same family
    """
    with open(GRAPH_FILE, encoding="utf-8") as handle:
        data = json.load(handle)
    builds_on = {name.lower(): list(parents) for name, parents in data["builds_on"].items()}
    related = defaultdict(set)
    for family in data["related"]:
        for skill in family:
            related[skill.lower()].update(other for other in family if other != skill)
    return builds_on, dict(related)


def _mentioned_in_text(skill_name, text):
    """True if the skill name literally appears in the text (whole word, any case)."""
    escaped = re.sub(r"(?:\\ )+", r"[\\s\\-]+", re.escape(skill_name))
    return re.search(rf"(?<![\w+#]){escaped}(?![\w+#])", text, re.IGNORECASE) is not None


def _evidence(kind, note, skills=()):
    return {"type": kind, "skills": sorted(skills), "note": note}


def _assess(name, category, have, text):
    key = name.lower()
    builds_on, related = load_graph()

    if key in have:
        return MATCHED, _evidence("listed", "Listed on your resume.", [have[key]])

    # Skills that are not in our skills dictionary could not be detected when the resume was parsed,
    # so look for the name in the resume text itself.
    if canonical_skill(name)[1] == "" and text and _mentioned_in_text(name, text):
        return MATCHED, _evidence("mentioned_in_text", "Mentioned in your resume text.")

    implied_by = sorted(have[other] for other in have if key in {p.lower() for p in builds_on.get(other, [])})
    related_to = sorted(have[other.lower()] for other in related.get(key, ()) if other.lower() in have)
    related_only = [skill for skill in related_to if skill not in implied_by]
    if implied_by:
        note = (
            f"Your resume lists {', '.join(implied_by)}, which normally builds on {name}, "
            f"but {name} itself is not listed."
        )
        return PARTIAL, _evidence("implied", note, implied_by + related_only)
    if related_only:
        note = f"Your resume lists {', '.join(related_only)}, a related skill, but not {name} itself."
        return PARTIAL, _evidence("related", note, related_only)

    return MISSING, _evidence("not_found", "Not found on your resume.")


def _depth(name, gap_keys, builds_on, seen=()):
    """How many unmet prerequisites (that are also gaps) stand in front of this skill."""
    prerequisites = [p for p in builds_on.get(name.lower(), []) if p.lower() in gap_keys and p.lower() not in seen]
    if not prerequisites:
        return 0
    return 1 + max(_depth(p, gap_keys, builds_on, seen + (name.lower(),)) for p in prerequisites)


def _summary(total, matched, partial, missing):
    if total == 0:
        return "This job does not list any required skills, so there is nothing to compare."
    if matched == total:
        return f"Your resume lists all {total} required skills."
    text = f"Your resume covers {matched} of {total} required skills"
    if partial:
        text += f", partly covers {partial}"
    if missing:
        text += f", and {missing} could not be found" if partial else f" and {missing} could not be found"
    return text + "."


def analyze(resume_skills, resume_text, job_skills):
    """Compares a resume with the skills a job requires.

    resume_skills : skill names found in the resume (list of str)
    resume_text   : the resume's extracted text (str)
    job_skills    : the job's required skills (list of {"name": ..., "category": ...})

    Every status is based on what is written in the resume. Nothing is guessed:
      matched : the skill is listed (or, for skills outside our dictionary, mentioned in the text)
      partial : the skill itself is not there, but a skill that builds on it or a related one is
      missing : no evidence at all
    """
    have = {name.lower(): name for name in resume_skills}
    builds_on, _related = load_graph()

    items, seen = [], set()
    for skill in job_skills:
        name, category = skill["name"], skill.get("category", "")
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        status, evidence = _assess(name, category, have, resume_text or "")
        items.append({"skill": name, "category": category, "status": status, "evidence": evidence})

    by_status = {status: [i for i in items if i["status"] == status] for status in (MATCHED, PARTIAL, MISSING)}
    for rows in by_status.values():
        rows.sort(key=lambda row: row["skill"].lower())

    total = len(items)
    matched, partial, missing = (len(by_status[s]) for s in (MATCHED, PARTIAL, MISSING))
    coverage = None if total == 0 else round((matched + PARTIAL_WEIGHT * partial) / total * 100, 1)

    # Learning plan: prerequisites first, and missing skills before partially covered ones
    gaps = by_status[PARTIAL] + by_status[MISSING]
    gap_keys = {row["skill"].lower() for row in gaps}
    ordered = sorted(
        gaps,
        key=lambda row: (_depth(row["skill"], gap_keys, builds_on), row["status"] != MISSING, row["skill"].lower()),
    )
    plan = []
    for priority, row in enumerate(ordered, start=1):
        learn_after = sorted(
            p for p in builds_on.get(row["skill"].lower(), []) if p.lower() in gap_keys
        )
        plan.append(
            {
                "priority": priority,
                "skill": row["skill"],
                "status": row["status"],
                "learn_after": learn_after,
                **guidance_for(row["skill"], row["category"]),
            }
        )

    return {
        "summary": _summary(total, matched, partial, missing),
        "total_required": total,
        "matched_count": matched,
        "partial_count": partial,
        "missing_count": missing,
        "coverage_percent": coverage,
        "coverage_rule": COVERAGE_RULE,
        "matched": by_status[MATCHED],
        "partial": by_status[PARTIAL],
        "missing": by_status[MISSING],
        "learning_plan": plan,
        "disclaimer": DISCLAIMER,
    }