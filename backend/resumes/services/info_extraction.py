import re

from .skill_extraction import extract_skills

# ----------------------------------------------------------------------
# Section headings
# ----------------------------------------------------------------------
SECTION_ALIASES = {
    "education": {
        "education", "academic background", "academic qualifications", "academics",
        "educational qualifications", "education & training", "qualifications",
    },
    "experience": {
        "experience", "work experience", "professional experience", "employment history",
        "work history", "internships", "internship experience", "experience & internships",
        "internship", "industrial training", "relevant experience",
    },
    "projects": {
        "projects", "academic projects", "personal projects", "key projects",
        "project work", "technical projects", "projects & research", "major projects",
    },
    "skills": {
        "skills", "technical skills", "key skills", "core competencies",
        "skills & tools", "technologies", "tech stack", "technical proficiency",
    },
    "certifications": {
        "certifications", "certificates", "licenses & certifications", "courses",
        "certifications & courses", "courses & certifications", "training & certifications",
        "certifications & achievements", "licenses",
    },
    # headings that only mark where the previous section ends
    "other": {
        "summary", "profile", "objective", "career objective", "professional summary",
        "about me", "achievements", "awards", "honors & awards", "extracurricular activities",
        "interests", "hobbies", "languages", "references", "publications",
        "positions of responsibility", "declaration", "volunteering", "co-curricular activities",
        "personal details", "personal information",
    },
}
HEADING_LOOKUP = {
    alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}


def _normalize_heading(line):
    text = line.lower().replace(" and ", " & ")
    text = re.sub(r"[^a-z& \-]", "", text)
    return re.sub(r"\s+", " ", text).strip(" -")


def split_sections(text):
    """Splits resume text into {"header": [...], "education": [...], ...} (lists of lines)."""
    sections = {"header": []}
    current = "header"
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and len(stripped) <= 45 and len(stripped.split()) <= 5:
            heading = HEADING_LOOKUP.get(_normalize_heading(stripped))
            if heading:
                current = heading
                sections.setdefault(current, [])
                continue
        sections.setdefault(current, []).append(line)
    return sections


# ----------------------------------------------------------------------
# Contact information
# ----------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PHONE_CANDIDATE_RE = re.compile(r"(?<![\w@])\(?\+?\d[\d\s().\-]{8,17}\d(?!\w)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_\-%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-]+", re.I)

NOT_A_NAME_WORDS = {
    "resume", "curriculum", "vitae", "cv", "profile", "summary", "objective", "contact",
    "engineer", "developer", "student", "analyst", "intern", "scientist", "manager",
    "email", "phone", "address", "mobile", "linkedin", "github", "portfolio",
    "education", "experience", "skills", "projects", "software", "data", "machine",
    "learning", "full", "stack", "web", "fresher", "graduate",
}


def _extract_email(text):
    match = EMAIL_RE.search(text)
    return match.group(0).lower() if match else None


def _extract_phone(text):
    top = text[:1500]  # contact details are at the top of a resume
    for chunk in (top, text):
        for match in PHONE_CANDIDATE_RE.finditer(chunk):
            candidate = match.group(0).strip()
            digits = re.sub(r"\D", "", candidate)
            if 10 <= len(digits) <= 13:
                return re.sub(r"\s+", " ", candidate)
    return None


def _extract_link(pattern, text):
    match = pattern.search(text)
    if not match:
        return None
    link = match.group(0)
    return link if link.lower().startswith("http") else "https://" + link


def _extract_name(header_lines):
    """Picks the first short, name-like line near the top of the resume."""
    checked = 0
    for line in header_lines:
        line = line.strip()
        if not line:
            continue
        checked += 1
        if checked > 8:
            break
        if "@" in line or "http" in line.lower() or sum(ch.isdigit() for ch in line) >= 3:
            continue
        words = line.replace(",", " ").split()
        if not 2 <= len(words) <= 4 or len(line) > 40:
            continue
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", word) for word in words):
            continue
        if any(word.lower().strip(".") in NOT_A_NAME_WORDS for word in words):
            continue
        return line.title() if line.isupper() else line
    return None


def extract_contact(text, header_lines):
    return {
        "name": _extract_name(header_lines),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "linkedin": _extract_link(LINKEDIN_RE, text),
        "github": _extract_link(GITHUB_RE, text),
    }


# ----------------------------------------------------------------------
# Education
# ----------------------------------------------------------------------
DEGREE_RE = re.compile(
    r"\b(?:b\.?\s?tech|bachelors?|bachelor's|b\.\s?e\.?|b\.?\s?sc|bca|b\.?\s?com|"
    r"m\.?\s?tech|masters?|master's|m\.\s?e\.?|m\.?\s?sc|mca|mba|ph\.?\s?d|diploma|"
    r"10th|12th|higher secondary|senior secondary|secondary school|intermediate|"
    r"high school|matriculation|cbse|icse)(?![A-Za-z])",
    re.I,
)
STRONG_DEGREE_RE = re.compile(
    r"\b(?:b\.?\s?tech|bachelors?|bachelor's|b\.?\s?sc|bca|m\.?\s?tech|masters?|master's|"
    r"m\.?\s?sc|mca|mba|ph\.?\s?d|diploma)(?![A-Za-z])",
    re.I,
)
INSTITUTION_RE = re.compile(
    r"\b(?:university|college|institute|school|academy|polytechnic|iit|nit|iiit|vidyalaya)\b", re.I
)
YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
CGPA_RE = re.compile(r"(?:cgpa|gpa)\s*[:\-]?\s*(\d+(?:\.\d+)?)(?:\s*/\s*(\d+(?:\.\d+)?))?", re.I)
PERCENT_RE = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*%")

SCHOOL_WORDS = {"higher secondary", "senior secondary", "secondary school", "high school", "intermediate"}


def _is_degree_line(line):
    """A degree line names a degree/exam. A school NAME alone ("... Senior Secondary School") is not one."""
    if not line:
        return False
    matches = [m.group(0).lower() for m in DEGREE_RE.finditer(line)]
    if not matches:
        return False
    if INSTITUTION_RE.search(line) and all(m in SCHOOL_WORDS for m in matches):
        return False
    return True


def _clean_institution(line):
    line = re.split(r"[\s,|\-–—(]*(?:19|20)\d{2}", line)[0]
    return line.strip(" ,|-–—:") or None


def _parse_education(lines):
    lines = [line.strip() for line in lines]
    degree_idx = [i for i, line in enumerate(lines) if _is_degree_line(line)]

    def is_institution_line(j):
        return bool(lines[j]) and bool(INSTITUTION_RE.search(lines[j])) and j not in degree_idx

    entries = []
    for pos, i in enumerate(degree_idx):
        low = degree_idx[pos - 1] + 1 if pos else 0
        high = degree_idx[pos + 1] if pos + 1 < len(degree_idx) else len(lines)
        if high - 1 > i and is_institution_line(high - 1):
            high -= 1  # that line is the NEXT entry's institution name
        after = list(range(i, min(i + 4, high)))
        before = [j for j in (i - 1, i - 2) if j >= low and is_institution_line(j)]

        institution = None
        if INSTITUTION_RE.search(lines[i]):
            institution = _clean_institution(lines[i])
        elif before:
            institution = _clean_institution(lines[before[0]])
        else:
            for j in after[1:]:
                if lines[j] and INSTITUTION_RE.search(lines[j]):
                    institution = _clean_institution(lines[j])
                    break

        window_text = " ".join(lines[j] for j in before + after)
        years = sorted({int(y) for y in YEAR_RE.findall(window_text)})
        cgpa = CGPA_RE.search(window_text)
        percent = PERCENT_RE.search(window_text)
        grade = None
        if cgpa:
            grade = cgpa.group(0).strip()
        elif percent:
            grade = percent.group(0).strip()

        entries.append(
            {
                "degree": _clean_institution(lines[i]) or lines[i],
                "institution": institution,
                "years": years if len(years) <= 2 else [years[0], years[-1]],
                "grade": grade,
            }
        )
    return entries[:6]


# ----------------------------------------------------------------------
# Experience and projects (heading + bullet points)
# ----------------------------------------------------------------------
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_POINT = rf"(?:(?:{_MONTH}\s+|\d{{1,2}}/)?(?:19|20)\d{{2}})"
DATE_RANGE_RE = re.compile(
    rf"{_POINT}\s*(?:-|–|—|to)\s*(?:{_POINT}|present|current|ongoing|now)", re.I
)
BULLET_RE = re.compile(r"^[-*]\s+")


def _split_entries(lines):
    """Groups section lines into entries: heading line(s) followed by bullet/detail lines."""
    entries = []
    current = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        is_bullet = bool(BULLET_RE.match(line))
        text = BULLET_RE.sub("", line)
        long_text = len(text) > 90 and not is_bullet

        if current is None:
            current = {"head": [text], "details": []}
            entries.append(current)
        elif is_bullet or long_text:
            current["details"].append(text)
        elif current["details"]:
            current = {"head": [text], "details": []}  # a new heading after bullets = new entry
            entries.append(current)
        else:
            current["head"].append(text)  # still in the heading block (title / company / dates)
    return entries


def _remove_dates(text):
    text = DATE_RANGE_RE.sub("", text)
    return re.sub(r"\s*[|,\-–—]+\s*$", "", text).strip(" |,-–—()")


def _parse_experience(lines):
    results = []
    for entry in _split_entries(lines):
        head_text = " ".join(entry["head"])
        duration = DATE_RANGE_RE.search(head_text)
        heading_lines = [h for h in (_remove_dates(h) for h in entry["head"]) if h]
        if not heading_lines:
            continue
        results.append(
            {
                "title": heading_lines[0],
                "organization": heading_lines[1] if len(heading_lines) > 1 else None,
                "duration": duration.group(0) if duration else None,
                "description": entry["details"][:12],
            }
        )
    return results[:10]


def _parse_projects(lines):
    results = []
    for entry in _split_entries(lines):
        title_line = _remove_dates(entry["head"][0])
        title = re.split(r"\s+[|–—]\s+|\s+-\s+|:\s+", title_line)[0].strip()
        if not title:
            continue
        entry_text = " ".join(entry["head"] + entry["details"])
        results.append(
            {
                "title": title,
                "technologies": [skill["name"] for skill in extract_skills(entry_text)],
                "description": (entry["head"][1:] + entry["details"])[:10],
            }
        )
    return results[:10]


def _parse_certifications(lines):
    items = []
    for raw in lines:
        text = BULLET_RE.sub("", raw.strip())
        if 4 <= len(text) <= 200:
            items.append(text)
    return items[:20]


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def extract_info(text):
    """Extracts contact info, education, experience, projects and certifications.

    Everything comes only from what is written in the resume; fields that cannot
    be found are None or an empty list.
    """
    sections = split_sections(text)

    education_lines = sections.get("education")
    if education_lines is not None:
        education = _parse_education(education_lines)
    else:  # no "Education" heading found: look for clear degree names in the whole text
        lines = text.split("\n")
        strong = [line for line in lines if STRONG_DEGREE_RE.search(line)]
        education = _parse_education(strong) if strong else []

    return {
        "contact": extract_contact(text, sections["header"]),
        "education": education,
        "experience": _parse_experience(sections.get("experience", [])),
        "projects": _parse_projects(sections.get("projects", [])),
        "certifications": _parse_certifications(sections.get("certifications", [])),
    }
