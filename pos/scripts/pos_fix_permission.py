from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth.management import _get_all_permissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import logging

info_logger = logging.getLogger('file-info')


def run(*args):
    for model in apps.get_models():
        opts = model._meta
        if opts.app_label == 'pos':
            ctype, created = ContentType.objects.get_or_create(
                app_label=opts.app_label,
                model=opts.object_name.lower())

            if created:
                print('Content Type Created {}, {}, {}'.format(ctype.id, ctype.app_label, model))

            for code_tupel in _get_all_permissions(opts):
                codename = code_tupel[0]
                name = code_tupel[1]
                pe, pe_created = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=ctype,
                    defaults={'name': name})

                if pe_created:
                    print('Permission Created {}, {}, {}'.format(pe.id, pe.codename, ctype))
