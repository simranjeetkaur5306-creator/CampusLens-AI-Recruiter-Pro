import json

from django.test import SimpleTestCase

from resumes.services.skill_extraction import SKILLS_FILE

from .services import analysis, learning
from .services.analysis import MATCHED, MISSING, PARTIAL, analyze

PY = {"name": "Python", "category": "Programming Languages"}
SQL = {"name": "SQL", "category": "Programming Languages"}
DJANGO = {"name": "Django", "category": "Backend"}
DOCKER = {"name": "Docker", "category": "Cloud & DevOps"}
TF = {"name": "TensorFlow", "category": "AI/ML"}


def statuses(result):
    return {row["skill"]: row["status"] for key in ("matched", "partial", "missing") for row in result[key]}


class DataFileTests(SimpleTestCase):
    """The data files are typed by hand, so these tests catch typos and broken rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(SKILLS_FILE, encoding="utf-8") as handle:
            entries = json.load(handle)
        cls.names = {entry["name"] for entry in entries}
        cls.categories = {entry["category"] for entry in entries}
        with open(analysis.GRAPH_FILE, encoding="utf-8") as handle:
            cls.graph = json.load(handle)
        with open(learning.LEARNING_FILE, encoding="utf-8") as handle:
            cls.learning = json.load(handle)

    def test_every_skill_in_the_graph_exists_in_the_dictionary(self):
        used = set(self.graph["builds_on"]) | {p for parents in self.graph["builds_on"].values() for p in parents}
        used |= {skill for family in self.graph["related"] for skill in family}
        self.assertEqual(sorted(used - self.names), [])

    def test_builds_on_has_no_self_references_duplicates_or_cycles(self):
        builds_on = self.graph["builds_on"]
        for skill, parents in builds_on.items():
            self.assertNotIn(skill, parents, skill)
            self.assertEqual(len(parents), len(set(parents)), skill)

        def walk(skill, path):
            self.assertNotIn(skill, path, f"cycle: {path + [skill]}")
            for parent in builds_on.get(skill, []):
                walk(parent, path + [skill])

        for skill in builds_on:
            walk(skill, [])

    def test_related_families_are_sensible(self):
        for family in self.graph["related"]:
            self.assertGreaterEqual(len(family), 2, family)
            self.assertEqual(len(family), len(set(family)), family)

    def test_curated_learning_entries_are_complete_and_use_real_skills(self):
        self.assertEqual(sorted(set(self.learning["skills"]) - self.names), [])
        for name, entry in self.learning["skills"].items():
            self.assertTrue(3 <= len(entry["topics"]) <= 6, name)
            self.assertTrue(all(isinstance(t, str) and t.strip() for t in entry["topics"]), name)
            self.assertTrue(entry["project"].strip().endswith("."), name)

    def test_category_defaults_cover_real_categories_and_format_cleanly(self):
        self.assertEqual(sorted(set(self.learning["category_defaults"]) - self.categories), [])
        self.assertEqual(sorted(self.categories - set(self.learning["category_defaults"])), [])
        for entry in [*self.learning["category_defaults"].values(), self.learning["default"]]:
            for topic in entry["topics"]:
                self.assertNotIn("{", topic.format(skill="X"))
            self.assertNotIn("{", entry["project"].format(skill="X"))


class AssessmentTests(SimpleTestCase):
    def one(self, resume_skills, job_skill, text=""):
        result = analyze(resume_skills, text, [job_skill])
        for key in ("matched", "partial", "missing"):
            if result[key]:
                return key, result[key][0]

    def test_listed_skill_is_matched_ignoring_case(self):
        status, row = self.one(["python"], PY)
        self.assertEqual((status, row["evidence"]["type"]), ("matched", "listed"))

    def test_skill_outside_the_dictionary_is_found_in_the_resume_text(self):
        custom = {"name": "Basket Weaving", "category": ""}
        status, row = self.one([], custom, text="Won a prize for basket weaving in 2024.")
        self.assertEqual((status, row["evidence"]["type"]), ("matched", "mentioned_in_text"))
        self.assertEqual(self.one([], custom, text="Likes pottery.")[0], "missing")

    def test_text_search_needs_the_whole_word(self):
        custom = {"name": "Basket Weaving", "category": ""}
        self.assertEqual(self.one([], custom, text="Enjoys basket weavings and more.")[0], "missing")

    def test_dictionary_skills_rely_on_the_skills_found_when_parsing_not_on_raw_text(self):
        self.assertEqual(self.one([], SQL, text="I know SQL very well")[0], "missing")

    def test_a_skill_that_builds_on_the_required_one_gives_partial_credit(self):
        status, row = self.one(["PostgreSQL"], SQL)
        self.assertEqual(status, "partial")
        self.assertEqual(row["evidence"]["type"], "implied")
        self.assertEqual(row["evidence"]["skills"], ["PostgreSQL"])
        self.assertIn("PostgreSQL", row["evidence"]["note"])
        self.assertIn("SQL itself is not listed", row["evidence"]["note"])

    def test_a_related_skill_gives_partial_credit(self):
        status, row = self.one(["PyTorch"], TF)
        self.assertEqual((status, row["evidence"]["type"], row["evidence"]["skills"]), ("partial", "related", ["PyTorch"]))

    def test_implied_and_related_evidence_are_combined(self):
        status, row = self.one(["Django REST Framework", "Flask"], DJANGO)
        self.assertEqual(status, "partial")
        self.assertEqual(row["evidence"]["type"], "implied")
        self.assertEqual(row["evidence"]["skills"], ["Django REST Framework", "Flask"])

    def test_a_direct_match_beats_partial_evidence(self):
        self.assertEqual(self.one(["SQL", "PostgreSQL"], SQL)[0], "matched")

    def test_a_basic_skill_does_not_prove_an_advanced_one(self):
        self.assertEqual(self.one(["Python"], DJANGO)[0], "missing")
        self.assertEqual(self.one(["SQL"], {"name": "PostgreSQL", "category": "Databases"})[0], "missing")
        self.assertEqual(self.one(["Git"], DOCKER)[0], "missing")

    def test_skills_of_the_same_family_are_partial(self):
        self.assertEqual(self.one(["MySQL"], {"name": "PostgreSQL", "category": "Databases"})[0], "partial")
        self.assertEqual(self.one(["Azure"], {"name": "AWS", "category": "Cloud & DevOps"})[0], "missing")  # "Azure" is not the canonical name
        self.assertEqual(self.one(["Microsoft Azure"], {"name": "AWS", "category": "Cloud & DevOps"})[0], "partial")

    def test_related_skills_work_in_both_directions(self):
        self.assertEqual(self.one(["JavaScript"], {"name": "TypeScript", "category": ""})[0], "partial")
        self.assertEqual(self.one(["TypeScript"], {"name": "JavaScript", "category": ""})[0], "partial")

    def test_missing_skill_has_a_clear_note(self):
        status, row = self.one([], DOCKER)
        self.assertEqual((status, row["evidence"]["type"], row["evidence"]["note"]), ("missing", "not_found", "Not found on your resume."))


class AnalyzeTests(SimpleTestCase):
    def test_counts_lists_and_coverage(self):
        job = [PY, SQL, DJANGO, DOCKER, TF]
        result = analyze(["Python", "PostgreSQL", "PyTorch", "Docker"], "", job)
        self.assertEqual(statuses(result), {"Python": MATCHED, "Docker": MATCHED, "SQL": PARTIAL, "TensorFlow": PARTIAL, "Django": MISSING})
        self.assertEqual((result["total_required"], result["matched_count"], result["partial_count"], result["missing_count"]), (5, 2, 2, 1))
        self.assertEqual(result["coverage_percent"], 60.0)  # (2 + 0.5 * 2) / 5
        self.assertIn("0.5", result["coverage_rule"])

    def test_every_list_is_sorted_by_skill_name(self):
        result = analyze([], "", [PY, DJANGO, DOCKER, SQL])
        self.assertEqual([r["skill"] for r in result["missing"]], ["Django", "Docker", "Python", "SQL"])

    def test_duplicate_job_skills_are_counted_once(self):
        result = analyze(["python"], "", [PY, {"name": "python", "category": ""}, PY])
        self.assertEqual(result["total_required"], 1)

    def test_summary_sentences(self):
        self.assertEqual(analyze(["Python"], "", [PY])["summary"], "Your resume lists all 1 required skills.")
        self.assertEqual(analyze(["Python"], "", [PY, DJANGO])["summary"], "Your resume covers 1 of 2 required skills and 1 could not be found.")
        self.assertEqual(
            analyze(["PostgreSQL"], "", [SQL, DJANGO])["summary"],
            "Your resume covers 0 of 2 required skills, partly covers 1, and 1 could not be found.",
        )
        self.assertEqual(
            analyze(["PostgreSQL"], "", [SQL])["summary"], "Your resume covers 0 of 1 required skills, partly covers 1."
        )

    def test_job_without_required_skills(self):
        result = analyze(["Python"], "text", [])
        self.assertEqual((result["total_required"], result["coverage_percent"], result["learning_plan"]), (0, None, []))
        self.assertIn("nothing to compare", result["summary"])

    def test_everything_matched_gives_full_coverage_and_no_plan(self):
        result = analyze(["Python", "SQL"], "", [PY, SQL])
        self.assertEqual((result["coverage_percent"], result["learning_plan"]), (100.0, []))

    def test_nothing_matched_gives_zero_coverage(self):
        self.assertEqual(analyze([], "", [PY, SQL])["coverage_percent"], 0.0)

    def test_empty_inputs_do_not_crash(self):
        self.assertEqual(analyze([], None, [PY])["missing_count"], 1)
        self.assertEqual(analyze([], "", [])["total_required"], 0)

    def test_result_can_be_sent_as_json(self):
        json.dumps(analyze(["Python"], "text", [PY, SQL, DJANGO]))

    def test_disclaimer_is_always_present(self):
        self.assertIn("did not write on your resume", analyze([], "", [PY])["disclaimer"])


class LearningPlanTests(SimpleTestCase):
    def test_prerequisites_come_first_and_are_named(self):
        plan = analyze([], "", [DJANGO, PY, DOCKER])["learning_plan"]
        self.assertEqual([p["skill"] for p in plan], ["Docker", "Python", "Django"])
        self.assertEqual([p["priority"] for p in plan], [1, 2, 3])
        self.assertEqual(plan[2]["learn_after"], ["Python"])
        self.assertEqual(plan[0]["learn_after"], [])

    def test_a_prerequisite_the_candidate_already_has_is_not_mentioned(self):
        plan = analyze(["Python"], "", [DJANGO])["learning_plan"]
        self.assertEqual(plan[0]["learn_after"], [])

    def test_chains_of_prerequisites_are_ordered(self):
        job = [{"name": "Django REST Framework", "category": "Backend"}, DJANGO, PY]
        plan = analyze([], "", job)["learning_plan"]
        self.assertEqual([p["skill"] for p in plan], ["Python", "Django", "Django REST Framework"])
        self.assertEqual(plan[2]["learn_after"], ["Django", "Python"])

    def test_missing_skills_come_before_partially_covered_ones_at_the_same_level(self):
        plan = analyze(["PyTorch"], "", [TF, DOCKER])["learning_plan"]
        self.assertEqual([(p["skill"], p["status"]) for p in plan], [("Docker", "missing"), ("TensorFlow", "partial")])

    def test_curated_guidance(self):
        python = analyze([], "", [PY])["learning_plan"][0]
        self.assertEqual(python["source"], "curated")
        self.assertTrue(len(python["topics"]) >= 3)
        self.assertIn("command-line", python["project_idea"])

    def test_generic_guidance_uses_the_category_and_names_the_skill(self):
        terraform = analyze([], "", [{"name": "Terraform", "category": "Cloud & DevOps"}])["learning_plan"][0]
        self.assertEqual(terraform["source"], "generic")
        self.assertTrue(any("Terraform" in topic for topic in terraform["topics"]))
        self.assertIn("Terraform", terraform["project_idea"])
        self.assertNotIn("{", terraform["project_idea"])

    def test_unknown_skill_gets_default_guidance(self):
        plan = analyze([], "", [{"name": "Quantum Basket Weaving", "category": ""}])["learning_plan"][0]
        self.assertEqual(plan["source"], "generic")
        self.assertIn("Quantum Basket Weaving", plan["project_idea"])

    def test_returned_guidance_cannot_change_the_stored_data(self):
        first = learning.guidance_for("Python")
        first["topics"].append("hacked")
        self.assertNotIn("hacked", learning.guidance_for("Python")["topics"])