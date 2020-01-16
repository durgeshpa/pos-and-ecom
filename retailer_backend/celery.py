from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

#from retailer_backend import common_function
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retailer_backend.settings')

app = Celery('retailer_backend_celery')
# app.conf.task_routes = {'retailer_backend.common_function.generate_invoice_number': {'queue': 'invoice'}}

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
