import pgvector.django.indexes
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_enable_pgvector"),  # the vector extension must exist before a vector column
        ("candidates", "0001_initial"),
        ("resumes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resume",
            name="embedded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resume",
            name="embedding",
            field=pgvector.django.vector.VectorField(blank=True, dimensions=384, null=True),
        ),
        migrations.AddField(
            model_name="resume",
            name="embedding_model",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddIndex(
            model_name="resume",
            index=pgvector.django.indexes.HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="resume_embedding_hnsw",
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]