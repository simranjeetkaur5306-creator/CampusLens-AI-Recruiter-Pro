from django.test import TestCase

from resumes.models import Skill

from .services import canonical_skill, resolve_skills


class CanonicalSkillTests(TestCase):
    def test_aliases_map_to_the_resume_parser_names(self):
        self.assertEqual(canonical_skill("ML")[0], "Machine Learning")
        self.assertEqual(canonical_skill("sklearn")[0], "Scikit-learn")
        self.assertEqual(canonical_skill("nodejs")[0], "Node.js")
        self.assertEqual(canonical_skill("sql")[0], "SQL")
        self.assertEqual(canonical_skill("  machine   learning ")[0], "Machine Learning")
        self.assertEqual(canonical_skill("ml")[0], "Machine Learning")
        self.assertEqual(canonical_skill("Machine-Learning")[0], "Machine Learning")
        self.assertEqual(canonical_skill("react")[0], "React")

    def test_unknown_skill_is_kept_as_typed(self):
        self.assertEqual(canonical_skill("Quantum Basket Weaving"), ("Quantum Basket Weaving", ""))

    def test_text_with_several_known_skills_is_not_collapsed(self):
        self.assertEqual(canonical_skill("Python and Java")[0], "Python and Java")


class ResolveSkillsTests(TestCase):
    def test_creates_skills_and_removes_duplicates(self):
        skills = resolve_skills(["Python", "python", "ML", "Machine Learning", "Custom Tool"])
        self.assertEqual([s.name for s in skills], ["Python", "Machine Learning", "Custom Tool"])
        self.assertEqual(Skill.objects.count(), 3)

    def test_reuses_existing_skill_rows(self):
        existing = Skill.objects.create(name="Python", category="Programming Languages")
        skills = resolve_skills(["PYTHON"])
        self.assertEqual(skills[0].pk, existing.pk)
        self.assertEqual(Skill.objects.filter(name__iexact="python").count(), 1)

    def test_category_comes_from_the_dictionary(self):
        skill = resolve_skills(["docker"])[0]
        self.assertEqual((skill.name, skill.category), ("Docker", "Cloud & DevOps"))