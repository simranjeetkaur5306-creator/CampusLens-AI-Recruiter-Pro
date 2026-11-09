import numpy as np
from django.core.management.base import BaseCommand, CommandError

from jobs.models import Job
from matching.exceptions import EmbeddingError
from matching.services import embeddings, search
from matching.services.similarity import rank_vectors
from resumes.models import Resume


class Command(BaseCommand):
    help = (
        "Finds the active jobs nearest to a resume (--resume-id) or to a free-text query (--query) "
        "using pgvector. Add --verify to compare the database ranking with a pure-Python calculation."
    )

    def add_arguments(self, parser):
        parser.add_argument("--resume-id", type=int)
        parser.add_argument("--query")
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--verify", action="store_true")

    def handle(self, *args, **options):
        resume_id, query, limit = options["resume_id"], options["query"], options["limit"]
        if bool(resume_id) == bool(query):
            raise CommandError("Give exactly one of --resume-id or --query.")
        try:
            if resume_id:
                resume = Resume.objects.filter(pk=resume_id).first()
                if resume is None:
                    raise CommandError(f"Resume {resume_id} does not exist.")
                vector = resume.embedding
                if vector is None:
                    raise CommandError(f"Resume {resume_id} has no embedding yet. Run: python manage.py embed_all")
                self.stdout.write(f"Resume {resume.pk}: {resume.original_filename}")
            else:
                vector = embeddings.embed_text(query)
                self.stdout.write(f"Query: {query}")
            results = search.search_jobs(vector, queryset=Job.objects.filter(is_active=True), limit=limit)
        except EmbeddingError as exc:
            raise CommandError(str(exc))
        except ValueError as exc:
            raise CommandError(str(exc))

        if not results:
            self.stdout.write("No active jobs with an embedding were found. Run: python manage.py embed_all")
        for rank, row in enumerate(results, start=1):
            self.stdout.write(
                f"{rank}. [{row.item.pk}] {row.item.job_title} at {row.item.company_name}   "
                f"cosine {row.similarity:.4f}   score {row.score}%"
            )
        if options["verify"]:
            self._verify(vector, results, limit)

    def _verify(self, vector, results, limit):
        items = {
            job.pk: np.asarray(job.embedding)
            for job in Job.objects.filter(is_active=True, embedding__isnull=False)
        }
        reference = rank_vectors(vector, items)[:limit]
        if len(reference) != len(results):
            raise CommandError("VERIFY FAILED: the database and the Python reference returned different numbers of rows.")
        biggest = 0.0
        for db_row, (job_id, similarity, _score) in zip(results, reference):
            difference = abs(db_row.similarity - similarity)
            if db_row.item.pk != job_id and difference > 1e-6:  # a swap between exact ties is fine
                raise CommandError(
                    f"VERIFY FAILED: the database ranked job {db_row.item.pk} where the reference has job {job_id}."
                )
            biggest = max(biggest, difference)
        if biggest > 1e-4:
            raise CommandError(f"VERIFY FAILED: similarities differ by up to {biggest:.6f}.")
        self.stdout.write(self.style.SUCCESS(
            f"VERIFY OK: pgvector matches the Python calculation (largest difference {biggest:.2e})."
        ))