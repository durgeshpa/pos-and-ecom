from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth.management import _get_all_permissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):

    def handle(self, *args, **options):
        for model in apps.get_models():
            opts = model._meta
            if opts.app_label == 'franchise':
                ctype, created = ContentType.objects.get_or_create(
                    app_label=opts.app_label,
                    model=opts.object_name.lower())

                for code_tupel in _get_all_permissions(opts):
                    codename = code_tupel[0]
                    name = code_tupel[1]
                    Permission.objects.get_or_create(
                        codename=codename,
                        content_type=ctype,
                        defaults={'name': name})