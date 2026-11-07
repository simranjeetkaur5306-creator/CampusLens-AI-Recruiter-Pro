from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Resume


@receiver(post_delete, sender=Resume)
def delete_resume_file(sender, instance, **kwargs):
    """Removes the file from disk when a Resume row is deleted (also on cascade deletes).

    Runs after the database transaction commits, so a rolled-back delete never loses a file.
    """
    name = instance.file.name
    if not name:
        return
    storage = instance.file.storage
    transaction.on_commit(lambda: storage.delete(name))