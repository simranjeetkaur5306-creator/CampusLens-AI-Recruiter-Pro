import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from matching.exceptions import EmbeddingError
from matching.services import embeddings
from matching.services.similarity import cosine_similarity, similarity_to_score

# SAMPLE DATA, written only to demonstrate and test the embedding pipeline.
SAMPLE_RESUMES = {
    "ML student": (
        "Built predictive models for customer churn using Python, scikit-learn and pandas. "
        "Trained classification and regression models, evaluated them with cross-validation and "
        "improved accuracy through feature engineering. Coursework in statistics and deep learning."
    ),
    "Web developer": (
        "Developed responsive web applications with React, JavaScript and CSS. Built reusable user "
        "interface components, integrated REST APIs and improved page load speed for a college portal."
    ),
    "Restaurant cook": (
        "Experienced restaurant cook who prepared Italian dishes, managed kitchen inventory and trained "
        "junior staff. Skilled in menu planning, food safety and fast-paced service."
    ),
}
SAMPLE_JOBS = {
    "ML Engineer": (
        "Machine Learning Engineer. Develop and deploy machine learning models in Python. Experience with "
        "scikit-learn, pandas, model evaluation and feature engineering is required."
    ),
    "Frontend Developer": (
        "Frontend Developer. Build responsive user interfaces using React, JavaScript and CSS. Work with "
        "REST APIs and optimise web performance."
    ),
    "Restaurant Chef": (
        "Restaurant Chef. Lead the kitchen team, plan menus, manage food inventory and ensure food "
        "safety standards."
    ),
}
EXPECTED_BEST_JOB = {
    "ML student": "ML Engineer",
    "Web developer": "Frontend Developer",
    "Restaurant cook": "Restaurant Chef",
}


class Command(BaseCommand):
    help = (
        "Loads the embedding model and shows how similarity scores behave. "
        "Use --text-a and --text-b to compare two texts of your own."
    )

    def add_arguments(self, parser):
        parser.add_argument("--text-a", help="First text to compare")
        parser.add_argument("--text-b", help="Second text to compare")

    def handle(self, *args, **options):
        text_a, text_b = options.get("text_a"), options.get("text_b")
        if bool(text_a) != bool(text_b):
            raise CommandError("Give both --text-a and --text-b, or neither.")
        try:
            started = time.perf_counter()
            embeddings.get_model()
            self.stdout.write(
                f"Model: {settings.EMBEDDING_MODEL_NAME} ({settings.EMBEDDING_DIMENSIONS} dimensions), "
                f"loaded in {time.perf_counter() - started:.1f}s"
            )
            if text_a:
                self._compare_two(text_a, text_b)
            else:
                self._run_samples()
        except EmbeddingError as exc:
            raise CommandError(str(exc))

    def _compare_two(self, text_a, text_b):
        similarity = cosine_similarity(embeddings.embed_text(text_a), embeddings.embed_text(text_b))
        self.stdout.write(f"Cosine similarity: {similarity:.4f}   Matching score: {similarity_to_score(similarity)}%")

    def _run_samples(self):
        self.stdout.write("SAMPLE DATA (written for this demo only)\n")
        started = time.perf_counter()
        resume_vectors = {name: embeddings.embed_text(text) for name, text in SAMPLE_RESUMES.items()}
        job_vectors = {name: embeddings.embed_text(text) for name, text in SAMPLE_JOBS.items()}
        seconds = time.perf_counter() - started
        self.stdout.write(f"Embedded {len(resume_vectors) + len(job_vectors)} texts in {seconds:.2f}s\n")

        failures = 0
        for resume_name, resume_vector in resume_vectors.items():
            self.stdout.write(f"Resume: {resume_name}")
            scores = {
                job: cosine_similarity(resume_vector, vector) for job, vector in job_vectors.items()
            }
            best = max(scores, key=scores.get)
            for job, similarity in sorted(scores.items(), key=lambda row: row[1], reverse=True):
                self.stdout.write(f"   {job:<20} cosine {similarity:.4f}   score {similarity_to_score(similarity)}%")
            ok = best == EXPECTED_BEST_JOB[resume_name]
            failures += 0 if ok else 1
            self.stdout.write(
                f"   -> best match: {best}  [{'PASS' if ok else 'FAIL, expected ' + EXPECTED_BEST_JOB[resume_name]}]\n"
            )
        if failures:
            raise CommandError(f"{failures} of {len(resume_vectors)} checks failed.")
        self.stdout.write(self.style.SUCCESS("All sanity checks passed."))