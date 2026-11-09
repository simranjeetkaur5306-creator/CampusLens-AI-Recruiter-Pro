from django.core.management.base import BaseCommand, CommandError

from jobs.models import Job
from matching.exceptions import EmbeddingError
from matching.services import embeddings, storage
from resumes.models import Resume


class Command(BaseCommand):
    help = (
        "Creates embeddings (pgvector columns) for resumes and jobs that do not have one yet. "
        "Use --force to rebuild every embedding, for example after changing the model."
    )

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=["resumes", "jobs"], help="Embed only resumes or only jobs")
        parser.add_argument("--force", action="store_true", help="Rebuild embeddings that already exist")

    def handle(self, *args, **options):
        try:
            embeddings.get_model()  # fail early, with one clear message, if the model is unavailable
        except EmbeddingError as exc:
            raise CommandError(str(exc))

        force, only = options["force"], options["only"]
        failed = 0
        if only in (None, "resumes"):
            resumes = Resume.objects.filter(parsing_status=Resume.ParsingStatus.SUCCESS).prefetch_related("skills")
            failed += self._run("resume", resumes, storage.embed_resume, force)
        if only in (None, "jobs"):
            jobs = Job.objects.prefetch_related("required_skills")
            failed += self._run("job", jobs, storage.embed_job, force)
        if failed:
            raise CommandError(f"{failed} item(s) could not be embedded. See the messages above.")

    def _run(self, label, queryset, embed, force):
        if not force:
            queryset = queryset.filter(embedding__isnull=True)
        done = failed = 0
        for obj in queryset:
            try:
                embed(obj)
                done += 1
            except Exception as exc:  # keep going; report at the end
                failed += 1
                self.stderr.write(f"Could not embed {label} {obj.pk}: {exc}")
        self.stdout.write(f"{label}s embedded: {done}, failed: {failed}")
        return failed