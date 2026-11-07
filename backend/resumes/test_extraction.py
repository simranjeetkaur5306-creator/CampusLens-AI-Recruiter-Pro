from django.test import SimpleTestCase

from .services.info_extraction import extract_info, split_sections
from .services.skill_extraction import extract_skills

SAMPLE_RESUME = """SIMRAN KAUR
simran.kaur@example.com | +91 98765 43210
linkedin.com/in/simran-kaur | github.com/simran-dev

EDUCATION
Kurukshetra University
B.Tech in Computer Science (AI & ML)  2023 - 2027
CGPA: 8.4/10
Government Senior Secondary School
12th (CBSE), 2022, 91%

SKILLS
Python, SQL, Machine Learning, Django, React, Docker, Git

EXPERIENCE
AI & ML Intern
Isekai Tech Pvt. Ltd.  Jun 2025 - Aug 2025
- Built an NLP pipeline using spaCy and scikit-learn for text classification
- Created REST APIs with Django REST Framework

PROJECTS
PulseIQ | Python, Pandas, Power BI
- Built a product analytics dashboard with SQL and Python
- Tracked retention using A/B testing

CampusLens AI - Recruitment platform
- Semantic resume matching with embeddings and PostgreSQL

CERTIFICATIONS
- Machine Learning Specialization, Coursera
- AWS Cloud Practitioner Essentials

ACHIEVEMENTS
- Winner of a college hackathon
"""


def names(skills):
    return {skill["name"] for skill in skills}


class SkillExtractionTests(SimpleTestCase):
    def test_finds_listed_skills(self):
        found = names(extract_skills("Skills: Python, SQL, Machine Learning, Django, Docker"))
        self.assertEqual(found, {"Python", "SQL", "Machine Learning", "Django", "Docker"})

    def test_case_insensitive_and_aliases(self):
        found = names(extract_skills("python, nlp, sklearn, nodejs, powerbi, postgres"))
        self.assertEqual(
            found,
            {"Python", "Natural Language Processing", "Scikit-learn", "Node.js", "Power BI", "PostgreSQL"},
        )

    def test_java_is_not_found_inside_javascript(self):
        found = names(extract_skills("I know JavaScript and TypeScript"))
        self.assertIn("JavaScript", found)
        self.assertNotIn("Java", found)

    def test_sql_is_not_found_inside_mysql_or_nosql(self):
        found = names(extract_skills("MySQL and NoSQL"))
        self.assertEqual(found, {"MySQL", "NoSQL"})

    def test_git_is_not_found_inside_github(self):
        found = names(extract_skills("Projects hosted on GitHub"))
        self.assertEqual(found, {"GitHub"})

    def test_special_characters_cpp_csharp(self):
        found = names(extract_skills("Languages: C++, C#, Python."))
        self.assertEqual(found, {"C++", "C#", "Python"})

    def test_skill_at_end_of_sentence(self):
        self.assertEqual(names(extract_skills("I love working with Python.")), {"Python"})

    def test_hyphen_and_space_variants(self):
        self.assertEqual(names(extract_skills("scikit learn and machine-learning")), {"Scikit-learn", "Machine Learning"})

    def test_case_sensitive_abbreviations(self):
        self.assertIn("Machine Learning", names(extract_skills("Worked on ML models")))
        self.assertNotIn("Machine Learning", names(extract_skills("the ml file")))
        self.assertIn("Microsoft Excel", names(extract_skills("Advanced Excel formulas")))
        self.assertNotIn("Microsoft Excel", names(extract_skills("I excel in teamwork")))
        self.assertIn("React", names(extract_skills("Frontend: React, Redux")))
        self.assertNotIn("React", names(extract_skills("I react quickly to change")))

    def test_no_skills_in_unrelated_text(self):
        self.assertEqual(extract_skills("I enjoy painting and long walks."), [])

    def test_empty_text(self):
        self.assertEqual(extract_skills(""), [])
        self.assertEqual(extract_skills(None), [])

    def test_result_has_category(self):
        skill = extract_skills("Docker")[0]
        self.assertEqual(skill, {"name": "Docker", "category": "Cloud & DevOps"})


class InfoExtractionTests(SimpleTestCase):
    def setUp(self):
        self.info = extract_info(SAMPLE_RESUME)

    def test_sections_split(self):
        sections = split_sections(SAMPLE_RESUME)
        for key in ("header", "education", "skills", "experience", "projects", "certifications", "other"):
            self.assertIn(key, sections)

    def test_contact(self):
        contact = self.info["contact"]
        self.assertEqual(contact["name"], "Simran Kaur")
        self.assertEqual(contact["email"], "simran.kaur@example.com")
        self.assertEqual(contact["phone"], "+91 98765 43210")
        self.assertEqual(contact["linkedin"], "https://linkedin.com/in/simran-kaur")
        self.assertEqual(contact["github"], "https://github.com/simran-dev")

    def test_education(self):
        education = self.info["education"]
        self.assertEqual(len(education), 2)
        btech = education[0]
        self.assertIn("B.Tech", btech["degree"])
        self.assertEqual(btech["institution"], "Kurukshetra University")
        self.assertEqual(btech["years"], [2023, 2027])
        self.assertIn("8.4", btech["grade"])
        school = education[1]
        self.assertIn("12th", school["degree"])
        self.assertIn("School", school["institution"])
        self.assertEqual(school["years"], [2022])
        self.assertEqual(school["grade"], "91%")

    def test_experience(self):
        experience = self.info["experience"]
        self.assertEqual(len(experience), 1)
        job = experience[0]
        self.assertEqual(job["title"], "AI & ML Intern")
        self.assertEqual(job["organization"], "Isekai Tech Pvt. Ltd.")
        self.assertEqual(job["duration"], "Jun 2025 - Aug 2025")
        self.assertEqual(len(job["description"]), 2)

    def test_projects(self):
        projects = self.info["projects"]
        self.assertEqual([p["title"] for p in projects], ["PulseIQ", "CampusLens AI"])
        self.assertIn("Power BI", projects[0]["technologies"])
        self.assertIn("Pandas", projects[0]["technologies"])
        self.assertIn("A/B Testing", projects[0]["technologies"])
        self.assertIn("PostgreSQL", projects[1]["technologies"])
        self.assertIn("Embeddings", projects[1]["technologies"])

    def test_certifications(self):
        self.assertEqual(
            self.info["certifications"],
            ["Machine Learning Specialization, Coursera", "AWS Cloud Practitioner Essentials"],
        )

    def test_achievements_section_does_not_leak_into_certifications(self):
        self.assertNotIn("Winner of a college hackathon", self.info["certifications"])

    def test_missing_information_is_not_invented(self):
        info = extract_info("Some random text without any structure at all, just words and more words.")
        self.assertEqual(
            info["contact"],
            {"name": None, "email": None, "phone": None, "linkedin": None, "github": None},
        )
        self.assertEqual(info["education"], [])
        self.assertEqual(info["experience"], [])
        self.assertEqual(info["projects"], [])
        self.assertEqual(info["certifications"], [])

    def test_year_ranges_are_not_mistaken_for_phone_numbers(self):
        info = extract_info("Jane Doe\nB.Tech 2023 - 2027\nEDUCATION\nB.Tech 2023 - 2027")
        self.assertIsNone(info["contact"]["phone"])

    def test_education_fallback_without_heading(self):
        info = extract_info("Amit Verma\nBachelor of Technology, XYZ Institute, 2024\nLoves coding")
        self.assertEqual(len(info["education"]), 1)
        self.assertEqual(info["education"][0]["years"], [2024])

    def test_job_title_line_is_not_taken_as_name(self):
        info = extract_info("Machine Learning Engineer\nRiya Sharma\nriya@example.com")
        self.assertEqual(info["contact"]["name"], "Riya Sharma")