
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("interviews", "0002_repair_legacy_table"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE interviews_interviewquestionset
                    ALTER COLUMN source DROP NOT NULL,
                    ALTER COLUMN fallback_reason DROP NOT NULL,
                    ALTER COLUMN notice DROP NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
