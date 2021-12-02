import sys
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'retailer_backend.settings')
django.setup()

from django.apps.registry import apps



app_config = apps.get_app_config('ecom')

# To create Content Types
from django.contrib.contenttypes.management import create_contenttypes
create_contenttypes(app_config)

# To create Permissions
from django.contrib.auth.management import create_permissions
create_permissions(app_config)
