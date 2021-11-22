from django.db import models
from django.contrib.postgres.fields import JSONField


class GlobalConfig(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key
