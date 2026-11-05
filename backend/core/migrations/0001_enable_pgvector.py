from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """Runs CREATE EXTENSION IF NOT EXISTS vector, so any new database
    (including Django's test database) gets pgvector automatically."""

    dependencies = []

    operations = [VectorExtension()]