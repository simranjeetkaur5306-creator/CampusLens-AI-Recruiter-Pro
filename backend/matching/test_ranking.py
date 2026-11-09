from django.test import TestCase

from applications.models import Application
from jobs.models import Job
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import make_candidate, make_job, make_recruiter, make_resume, set_embedding, vector
from .services import ranking, search
from .services.similarity import rank_vectors


class SkillOverlapTests(TestCase):
    def test_compares_names_ignoring_case_and_sorts(self):
        matching, missing = ranking.skill_overlap(["python", "Docker"], ["SQL", "Python", "Machine Learning"])
        self.assertEqual(matching, ["Python"])
        self.assertEqual(missing, ["Machine Learning", "SQL"])

    def test_nothing_is_guessed(self):
        # "MySQL" is not treated as SQL: only literal skill names are compared
        self.assertEqual(ranking.skill_overlap(["MySQL"], ["SQL"]), ([], ["SQL"]))

    def test_empty_inputs(self):
        self.assertEqual(ranking.skill_overlap([], []), ([], []))
        self.assertEqual(ranking.skill_overlap([], ["Python"]), ([], ["Python"]))
        self.assertEqual(ranking.skill_overlap(["Python"], []), ([], []))


class RankApplicantsTests(TestCase):
    def setUp(self):
        self.recruiter = make_recruiter()
        self.job = make_job(self.recruiter, title="ML Engineer", skills=("Python", "Machine Learning", "SQL"))
        set_embedding(self.job, vector(1, 0))
        self.n = 0

    def apply(self, vec, skills=("Python",), job=None):
        self.n += 1
        candidate = make_candidate(f"cand{self.n}@example.com")
        resume = make_resume(candidate, skills=skills)
        if vec is not None:
            set_embedding(resume, vec)
        return Application.objects.create(candidate=candidate, job=job or self.job, resume=resume)

    def test_ranked_by_similarity_with_consecutive_ranks(self):
        far = self.apply(vector(0, 1))
        best = self.apply(vector(1, 0.05))
        middle = self.apply(vector(1, 1))
        rows, total, scored = ranking.rank_applicants(self.job)
        self.assertEqual([r.application.pk for r in rows], [best.pk, middle.pk, far.pk])
        self.assertEqual([r.rank for r in rows], [1, 2, 3])
        self.assertEqual((total, scored), (3, 3))

    def test_database_ranking_equals_the_python_reference(self):
        for vec in (vector(0, 1), vector(1, 0.05), vector(1, 1), vector(-1, 0.3), vector(2, 1, 1)):
            self.apply(vec)
        rows, _total, _scored = ranking.rank_applicants(self.job)
        reference = rank_vectors(
            self.job.embedding, {r.application.pk: r.application.resume.embedding for r in rows}
        )
        self.assertEqual([r.application.pk for r in rows], [item[0] for item in reference])
        for row, (_pk, similarity, score) in zip(rows, reference):
            self.assertAlmostEqual(row.similarity, similarity, places=5)
            self.assertAlmostEqual(row.score, score, delta=0.01)

    def test_matching_and_missing_skills_come_from_the_resume_the_candidate_applied_with(self):
        self.apply(vector(1, 0), skills=("python", "Docker"))
        row = ranking.rank_applicants(self.job)[0][0]
        self.assertEqual(row.matching_skills, ["Python"])
        self.assertEqual(row.missing_skills, ["Machine Learning", "SQL"])

    def test_applicants_that_cannot_be_scored_come_last_and_are_not_hidden(self):
        scored = self.apply(vector(1, 0.1))
        not_embedded = self.apply(None)
        deleted = self.apply(vector(0, 1))
        Resume.objects.filter(pk=deleted.resume_id).delete()
        rows, total, scored_count = ranking.rank_applicants(self.job)
        self.assertEqual((total, scored_count), (3, 1))
        self.assertEqual([r.application.pk for r in rows], [scored.pk, not_embedded.pk, deleted.pk])
        self.assertEqual([r.rank for r in rows], [1, None, None])
        self.assertEqual([r.score for r in rows[1:]], [None, None])
        self.assertEqual(rows[2].matching_skills, [])           # no resume left
        self.assertEqual(rows[2].missing_skills, ["Machine Learning", "Python", "SQL"])

    def test_limit_keeps_the_best_and_totals_stay_complete(self):
        for vec in (vector(0, 1), vector(1, 0.05), vector(1, 1), vector(0.2, 1)):
            self.apply(vec)
        rows, total, scored = ranking.rank_applicants(self.job, limit=2)
        self.assertEqual([r.rank for r in rows], [1, 2])
        self.assertEqual((total, scored), (4, 4))

    def test_invalid_limits(self):
        for bad in (0, -1, 201, "5", 1.5, None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                ranking.rank_applicants(self.job, limit=bad)

    def test_only_applicants_of_this_job(self):
        other = make_job(self.recruiter, title="Other job")
        mine = self.apply(vector(1, 0))
        self.apply(vector(1, 0), job=other)
        rows, total, _ = ranking.rank_applicants(self.job)
        self.assertEqual([r.application.pk for r in rows], [mine.pk])
        self.assertEqual(total, 1)

    def test_equal_scores_keep_the_order_of_application(self):
        first = self.apply(vector(1, 1))
        second = self.apply(vector(1, 1))
        rows, _t, _s = ranking.rank_applicants(self.job)
        self.assertEqual([r.application.pk for r in rows], [first.pk, second.pk])

    def test_the_resume_used_is_the_one_applied_with_not_a_newer_one(self):
        old = self.apply(vector(0, 1))                     # applied with a poor match
        newer = make_resume(old.candidate)                 # uploads a perfect resume afterwards
        set_embedding(newer, vector(1, 0))
        rows, _t, _s = ranking.rank_applicants(self.job)
        self.assertLess(rows[0].similarity, 0.1)

    def test_no_applicants(self):
        self.assertEqual(ranking.rank_applicants(self.job), ([], 0, 0))

    def test_job_without_embedding_is_reported(self):
        fresh = make_job(self.recruiter, title="Fresh")
        with self.assertRaises(EmbeddingError):
            ranking.rank_applicants(fresh)


class RecommendJobsTests(TestCase):
    def setUp(self):
        recruiter = make_recruiter()
        self.candidate = make_candidate("c@example.com")
        self.resume = make_resume(self.candidate, skills=("Python", "Docker"))
        set_embedding(self.resume, vector(1, 0))
        self.best = make_job(recruiter, title="Best", skills=("Python", "SQL"))
        self.middle = make_job(recruiter, title="Middle", skills=("Docker",))
        self.weak = make_job(recruiter, title="Weak", skills=("Cooking",))
        for job, vec in ((self.best, vector(1, 0.05)), (self.middle, vector(1, 1)), (self.weak, vector(0, 1))):
            set_embedding(job, vec)

    def recommend(self, **kwargs):
        return ranking.recommend_jobs(self.resume, self.candidate, Job.objects.filter(is_active=True), **kwargs)

    def test_best_first_with_skills(self):
        results = self.recommend()
        self.assertEqual([r.job.job_title for r in results], ["Best", "Middle", "Weak"])
        self.assertEqual((results[0].matching_skills, results[0].missing_skills), (["Python"], ["SQL"]))
        self.assertEqual((results[1].matching_skills, results[1].missing_skills), (["Docker"], []))

    def test_same_order_as_the_plain_search(self):
        plain = search.search_jobs_for_resume(self.resume)
        self.assertEqual([r.job.pk for r in self.recommend()], [r.item.pk for r in plain])

    def test_applied_jobs_are_left_out_unless_requested(self):
        Application.objects.create(candidate=self.candidate, job=self.best, resume=self.resume)
        self.assertEqual([r.job.job_title for r in self.recommend()], ["Middle", "Weak"])
        shown = self.recommend(include_applied=True)
        self.assertEqual([(r.job.job_title, r.already_applied) for r in shown],
                         [("Best", True), ("Middle", False), ("Weak", False)])

    def test_other_candidates_applications_do_not_hide_jobs(self):
        other = make_candidate("o@example.com")
        Application.objects.create(candidate=other, job=self.best, resume=make_resume(other))
        self.assertEqual(len(self.recommend()), 3)

    def test_min_percent_and_limit(self):
        self.assertEqual([r.job.job_title for r in self.recommend(min_percent=50)], ["Best", "Middle"])
        self.assertEqual([r.job.job_title for r in self.recommend(limit=1)], ["Best"])
        self.assertEqual(self.recommend(min_percent=100), [])