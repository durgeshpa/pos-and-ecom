from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION


class ExtendedManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            result = super().hashed_name(name, content, filename)
        except ValueError:
            # When the fille is missing, let's forgive and ignore that.
            result = name
        return result
