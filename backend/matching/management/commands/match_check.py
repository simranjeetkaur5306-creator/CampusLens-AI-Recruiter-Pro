from django.core.management.base import BaseCommand, CommandError

from jobs.models import Job
from matching.exceptions import EmbeddingError
from matching.services import embeddings
from matching.services.similarity import cosine_similarity, similarity_to_score
from resumes.models import Resume


class Command(BaseCommand):
    help = "Compares ONE stored resume with ONE stored job using the embedding model."

    def add_arguments(self, parser):
        parser.add_argument("--resume-id", type=int, required=True)
        parser.add_argument("--job-id", type=int, required=True)

    def handle(self, *args, **options):
        resume = Resume.objects.prefetch_related("skills").filter(pk=options["resume_id"]).first()
        if resume is None:
            raise CommandError(f"Resume {options['resume_id']} does not exist.")
        if resume.parsing_status != Resume.ParsingStatus.SUCCESS:
            raise CommandError(f"Resume {resume.pk} was not parsed successfully, so it has no text to compare.")
        job = Job.objects.prefetch_related("required_skills").filter(pk=options["job_id"]).first()
        if job is None:
            raise CommandError(f"Job {options['job_id']} does not exist.")

        try:
            resume_vector = embeddings.embed_text(embeddings.resume_document(resume))
            job_vector = embeddings.embed_text(embeddings.job_document(job))
        except EmbeddingError as exc:
            raise CommandError(str(exc))

        similarity = cosine_similarity(resume_vector, job_vector)
        self.stdout.write(f"Resume {resume.pk}: {resume.original_filename}")
        self.stdout.write(f"Job {job.pk}: {job.job_title} at {job.company_name}")
        self.stdout.write(f"Cosine similarity: {similarity:.4f}   Matching score: {similarity_to_score(similarity)}%")

        # Quick look at the literal skill overlap (the full skill-gap analysis comes in Phase 10)
        resume_skills = {skill.name for skill in resume.skills.all()}
        job_skills = {skill.name for skill in job.required_skills.all()}
        self.stdout.write(f"Job skills found in the resume: {', '.join(sorted(job_skills & resume_skills)) or 'none'}")
        self.stdout.write(f"Job skills not found in the resume: {', '.join(sorted(job_skills - resume_skills)) or 'none'}")