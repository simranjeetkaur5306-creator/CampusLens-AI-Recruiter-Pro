
from django.db import migrations


def repair_interview_table(apps, schema_editor):
    """
    Reconcile the legacy interview question table with the current
    InterviewQuestionSet model.

    Existing records are preserved. Legacy columns are retained.
    """
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        # Add fields that are missing from the legacy table.
        cursor.execute("""
            ALTER TABLE interviews_interviewquestionset
            ADD COLUMN IF NOT EXISTS candidate_id bigint NULL,
            ADD COLUMN IF NOT EXISTS application_id bigint NULL,
            ADD COLUMN IF NOT EXISTS audience varchar(20) NOT NULL DEFAULT 'candidate',
            ADD COLUMN IF NOT EXISTS used_resume boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS question_count smallint NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS prompt_version varchar(20) NOT NULL DEFAULT 'v1',
            ADD COLUMN IF NOT EXISTS prompt_tokens integer NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS completion_tokens integer NOT NULL DEFAULT 0
        """)

        # Add foreign-key constraints only when they do not already exist.
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'interviews_iqs_candidate_fk'
                ) THEN
                    ALTER TABLE interviews_interviewquestionset
                    ADD CONSTRAINT interviews_iqs_candidate_fk
                    FOREIGN KEY (candidate_id)
                    REFERENCES candidates_candidate(id)
                    DEFERRABLE INITIALLY DEFERRED;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'interviews_iqs_application_fk'
                ) THEN
                    ALTER TABLE interviews_interviewquestionset
                    ADD CONSTRAINT interviews_iqs_application_fk
                    FOREIGN KEY (application_id)
                    REFERENCES applications_application(id)
                    DEFERRABLE INITIALLY DEFERRED;
                END IF;
            END
            $$;
        """)

        # Add the index expected by the current model.
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS interviews__request_ae0b8e_idx
            ON interviews_interviewquestionset
            (requested_by_id, created_at DESC)
        """)


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            repair_interview_table,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
