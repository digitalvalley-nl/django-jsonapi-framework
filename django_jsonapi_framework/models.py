# Python Standard Library
import uuid

# Django
from django.db.models import (
    Model,
    UUIDField
)


"""Abstract model class that can be extended to use a UUID field as the primary
key.
"""
class UUIDModel(Model):
    id = UUIDField(
        blank=False,
        null=False,
        default=uuid.uuid4,
        primary_key=True,
        editable=False
    )

    class Meta:
        abstract = True
