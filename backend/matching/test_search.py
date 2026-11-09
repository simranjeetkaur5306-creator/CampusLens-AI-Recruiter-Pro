from django.test import TestCase

from jobs.models import Job
from resumes.models import Resume

from .exceptions import EmbeddingError
from .factories import make_candidate, make_job, make_recruiter, make_resume, set_embedding, vector
from .services import search, storage
from .services.similarity import cosine_similarity, rank_vectors, similarity_to_score


class SearchJobsTests(TestCase):
    def setUp(self):
        recruiter = make_recruiter()
        self.query = vector(1, 0)
        self.best = make_job(recruiter, title="Best match")
        self.good = make_job(recruiter, title="Good match")
        self.weak = make_job(recruiter, title="Weak match")
        self.opposite = make_job(recruiter, title="Opposite")
        for job, values in ((self.best, vector(1, 0.05)), (self.good, vector(1, 1)),
                            (self.weak, vector(0.1, 1)), (self.opposite, vector(-1, 0))):
            set_embedding(job, values)

    def test_results_are_ordered_best_first(self):
        results = search.search_jobs(self.query)
        self.assertEqual([r.item.job_title for r in results], ["Best match", "Good match", "Weak match", "Opposite"])

    def test_database_ranking_equals_the_python_reference(self):
        results = search.search_jobs(self.query)
        reference = rank_vectors(self.query, {job.pk: job.embedding for job in Job.objects.all()})
        self.assertEqual([r.item.pk for r in results], [row[0] for row in reference])
        for result, (_pk, similarity, score) in zip(results, reference):
            self.assertAlmostEqual(result.similarity, similarity, places=5)
            self.assertEqual(result.score, similarity_to_score(result.similarity))
            self.assertAlmostEqual(result.score, score, delta=0.01)

    def test_similarity_values(self):
        results = {r.item.job_title: r for r in search.search_jobs(self.query)}
        self.assertAlmostEqual(results["Good match"].similarity, cosine_similarity(self.query, vector(1, 1)), places=5)
        self.assertLess(results["Opposite"].similarity, 0)
        self.assertEqual(results["Opposite"].score, 0.0)  # negative similarity is shown as 0 %

    def test_only_active_jobs_with_an_embedding_are_found(self):
        make_job(make_recruiter("r2@example.com"), title="Closed job", active=False)
        closed = Job.objects.get(job_title="Closed job")
        set_embedding(closed, self.query)  # perfect match, but unpublished
        make_job(make_recruiter("r3@example.com"), title="Not embedded yet")  # no vector
        titles = [r.item.job_title for r in search.search_jobs(self.query, limit=50)]
        self.assertNotIn("Closed job", titles)
        self.assertNotIn("Not embedded yet", titles)
        self.assertEqual(len(titles), 4)

    def test_limit(self):
        self.assertEqual(len(search.search_jobs(self.query, limit=2)), 2)
        self.assertEqual([r.item.job_title for r in search.search_jobs(self.query, limit=1)], ["Best match"])

    def test_invalid_limits(self):
        for bad in (0, -1, 101, "5", 2.5, None, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                search.search_jobs(self.query, limit=bad)

    def test_queryset_restricts_the_candidates(self):
        Job.objects.filter(pk=self.good.pk).update(location="Delhi")
        results = search.search_jobs(self.query, queryset=Job.objects.filter(is_active=True, location="Delhi"))
        self.assertEqual([r.item.job_title for r in results], ["Good match"])

    def test_empty_result_when_nothing_matches_the_filter(self):
        self.assertEqual(search.search_jobs(self.query, queryset=Job.objects.filter(location="Mars")), [])

    def test_equal_similarity_is_ordered_by_id(self):
        twin = make_job(make_recruiter("r4@example.com"), title="Twin of best")
        set_embedding(twin, vector(1, 0.05))
        titles = [r.item.job_title for r in search.search_jobs(self.query, limit=2)]
        self.assertEqual(titles, ["Best match", "Twin of best"])

    def test_search_for_a_stored_resume(self):
        resume = make_resume(make_candidate())
        set_embedding(resume, vector(0.1, 1))
        results = search.search_jobs_for_resume(resume, limit=1)
        self.assertEqual(results[0].item.job_title, "Weak match")

    def test_resume_without_embedding_is_reported(self):
        resume = make_resume(make_candidate())
        with self.assertRaises(EmbeddingError):
            search.search_jobs_for_resume(resume)


class SearchByTextTests(TestCase):
    def test_related_job_ranks_first_using_the_fake_model(self):
        recruiter = make_recruiter()
        cook = make_job(recruiter, title="Restaurant Chef", skills=("Custom Cooking",),
                        description="Lead the kitchen team, plan menus and manage food inventory.")
        dev = make_job(recruiter, title="Backend Developer", skills=("Python", "Django"),
                       description="Build REST APIs with Python and Django for our hiring platform.")
        storage.embed_job(cook)
        storage.embed_job(dev)
        results = search.search_jobs_for_text("python django REST APIs developer")
        self.assertEqual(results[0].item.pk, dev.pk)
        self.assertGreater(results[0].similarity, results[1].similarity)

    def test_invalid_text_raises(self):
        with self.assertRaises(EmbeddingError):
            search.search_jobs_for_text("   ")


class SearchResumesTests(TestCase):
    def setUp(self):
        self.job = make_job(make_recruiter())
        set_embedding(self.job, vector(1, 0))
        self.near = make_resume(make_candidate("a@example.com"))
        self.far = make_resume(make_candidate("b@example.com"))
        set_embedding(self.near, vector(1, 0.1))
        set_embedding(self.far, vector(0, 1))

    def test_ranked_best_first(self):
        results = search.search_resumes_for_job(self.job)
        self.assertEqual([r.item.pk for r in results], [self.near.pk, self.far.pk])

    def test_only_active_parsed_resumes_with_a_vector(self):
        inactive = make_resume(make_candidate("c@example.com"), active=False)
        failed = make_resume(make_candidate("d@example.com"), status="failed")
        unembedded = make_resume(make_candidate("e@example.com"))
        for resume in (inactive, failed):
            set_embedding(resume, vector(1, 0))  # perfect vectors that must still be ignored
        ids = {r.item.pk for r in search.search_resumes_for_job(self.job, limit=50)}
        self.assertEqual(ids, {self.near.pk, self.far.pk})
        self.assertNotIn(unembedded.pk, ids)

    def test_queryset_restricts_to_given_candidates(self):
        only_far = Resume.objects.filter(pk=self.far.pk)
        self.assertEqual([r.item.pk for r in search.search_resumes_for_job(self.job, queryset=only_far)], [self.far.pk])

    def test_job_without_embedding_is_reported(self):
        job = make_job(make_recruiter("r2@example.com"), title="Fresh")
        with self.assertRaises(EmbeddingError):
            search.search_resumes_for_job(job)