"""Natural-language skill-gap summary written by the LLM (Phase 11, Module 9).

The skill comparison itself stays grounded: analysis.analyze() decides which skills are matched,
partial or missing from the resume data. The LLM only explains that result in friendly words and
suggests next steps. Its answer is checked: a next step that names a skill which is not in the
analysis is dropped, so the summary cannot invent requirements.
"""
import json
import re

from core import llm

NOTE = (
    "Written by AI from the skill-gap analysis above. The matched, partial and missing lists come "
    "from your resume data; the wording and advice are AI-generated and should be read as guidance."
)
MAX_SUMMARY_CHARS = 700
MAX_STEP_CHARS = 250
MAX_STEPS = 4


def _facts(job_title, result):
    """Only the analysis numbers and skill names: no resume text and no contact details."""
    return {
        "job_title": job_title,
        "coverage_percent": result["coverage_percent"],
        "total_required": result["total_required"],
        "matched": [row["skill"] for row in result["matched"]],
        "partially_covered": [
            {"skill": row["skill"], "why": row["evidence"]["note"]} for row in result["partial"]
        ],
        "missing": [row["skill"] for row in result["missing"]],
        "learning_plan_order": [row["skill"] for row in result["learning_plan"]],
    }


def build_messages(job_title, result):
    system = (
        "You are a friendly career advisor for students. Explain a skill-gap analysis in plain, "
        "encouraging English. Use only the skills in the data; never add new required skills or "
        "claim the student has a skill that is not listed as matched. Reply with JSON only."
    )
    user = (
        f"ANALYSIS DATA:\n{json.dumps(_facts(job_title, result), ensure_ascii=False)}\n\n"
        "Return {\"summary\": \"...\", \"next_steps\": [\"...\"]} where:\n"
        "- summary: 3 to 5 sentences on how well the resume fits this job, naming the strongest "
        "matched skills and the most important gaps\n"
        f"- next_steps: up to {MAX_STEPS} concrete actions, in the learning-plan order, each about "
        "one partially covered or missing skill from the data"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _mentions(text, skill):
    return re.search(rf"(?<![\w+#]){re.escape(skill)}(?![\w+#])", text, re.IGNORECASE) is not None


def clean_summary(data, result):
    summary = llm.clean_text(data.get("summary"), MAX_SUMMARY_CHARS)
    if len(summary) < 20:
        raise llm.LLMError("The AI did not return a usable summary. Please try again.", 502, "ai_bad_output")

    gaps = [row["skill"] for row in result["partial"] + result["missing"]]
    steps = []
    raw_steps = data.get("next_steps")
    for step in raw_steps if isinstance(raw_steps, list) else []:
        text = llm.clean_text(step, MAX_STEP_CHARS)
        # keep a step only if it is about one of the real gaps (when there are any)
        if text and (not gaps or any(_mentions(text, skill) for skill in gaps)):
            steps.append(text)
        if len(steps) == MAX_STEPS:
            break
    return {"summary": summary, "next_steps": steps}


def summarise(job_title, result):
    """Returns ({"summary", "next_steps"}, LLMResult). Raises core.llm.LLMError on failure."""
    if result["total_required"] == 0:
        return {"summary": result["summary"], "next_steps": []}, llm.LLMResult(data={}, model="none")
    llm_result = llm.chat_json(build_messages(job_title, result), max_tokens=800)
    return clean_summary(llm_result.data, result), llm_result
