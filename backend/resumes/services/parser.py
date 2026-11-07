from .info_extraction import extract_info
from .skill_extraction import extract_skills
from .text_extraction import extract_text


def parse_resume(data, file_type):
    """Runs the whole pipeline on file bytes and returns a plain dict.

    Raises ResumeParseError / NoTextFoundError if no text can be extracted.
    Keys: text, contact, education, experience, projects, certifications, skills.
    """
    text = extract_text(data, file_type)
    result = extract_info(text)
    result["text"] = text
    result["skills"] = extract_skills(text)
    return result