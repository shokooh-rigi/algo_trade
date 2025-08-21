from django.db import models


class SoftDeleteManager(models.Manager):
    """Custom manager to handle soft-deleted objects."""

    def get_queryset(self):
        """Return only non-deleted objects by default."""
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all objects, including soft-deleted ones."""
        return super().get_queryset()

    def only_deleted(self):
        """Return only soft-deleted objects."""
        return super().get_queryset().filter(is_deleted=True)
