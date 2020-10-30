"""
Django settings for retailer_backend project.

Generated by 'django-admin startproject' using Django 2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import logging.config
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Decouple used to get values from .env file
from decouple import config, Csv

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

AUTH_USER_MODEL = 'accounts.user'

ENVIRONMENT = config('ENVIRONMENT')

# Application definition

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'dal_admin_filters',
    'nested_admin',
    # 'jet.dashboard',
    # 'jet',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'rest_auth.registration',
    'accounts',
    'otp',
    'api',
    'rest_framework_swagger',
    'categories',
    'adminsortable',
    'mptt',
    'addresses',
    'products',
    'shops',
    'import_export',
    'base',
    'brand',
    'banner',
    'storages',
    #'order',
    'django.contrib.humanize',
    'gram_to_brand',
    'sp_to_gram',
    #'autocomplete_light',
    'retailer_to_sp',
    'wkhtmltopdf',
    'django_crontab',
    'tempus_dominus',
    'daterange_filter',
    'retailer_to_gram',
    'admin_auto_filters',
    'notification_center',
    'payments',
    'django_ses',
    'services',
    'rangefilter',
    'admin_numeric_filter',
    'django_admin_listfilter_dropdown',
    'debug_toolbar',
    # used for installing shell_plus
    'fcm',
    'django_celery_beat',
    'django_celery_results',
    'coupon',
    'offer',
    'celerybeat_status',
    'django_elasticsearch_dsl',
    'mathfilters',
    'wms',
    'audit'
]

# if ENVIRONMENT.lower() in ["production","qa"]:
#     INSTALLED_APPS +=[
#         'elasticapm.contrib.django',
# ]
#     service_name = "gramfactory-{}".format(ENVIRONMENT.lower())
#     ELASTIC_APM = {
#       # Set required service name. Allowed characters:
#       # a-z, A-Z, 0-9, -, _, and space
#       'SERVICE_NAME': service_name,

#       # Use if APM Server requires a token
#       'SECRET_TOKEN': '',

#       # Set custom APM Server URL (default: http://localhost:8200)
#       'SERVER_URL': 'http://13.234.240.93:8001',
#     }

FCM_APIKEY = config('FCM_APIKEY')

FCM_DEVICE_MODEL = 'notification_center.FCMDevice'
IMPORT_EXPORT_USE_TRANSACTIONS = True
SITE_ID = 1
if DEBUG:
    MIDDLEWARE = [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]
else:
    MIDDLEWARE = []
MIDDLEWARE += [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middlewares.RequestMiddleware',
]
# if ENVIRONMENT.lower() in ["production", "qa"]:
#     MIDDLEWARE += [
#             'elasticapm.contrib.django.middleware.TracingMiddleware'
#     ]

ROOT_URLCONF = 'retailer_backend.urls'
# STATICFILES_STORAGE = "retailer_backend.storage.ExtendedManifestStaticFilesStorage"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'retailer_backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
	},
    'readonly': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    },
    'dataanalytics': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        (
            'rest_framework.parsers.JSONParser',
            'rest_framework.parsers.FormParser',
            'rest_framework.parsers.MultiPartParser'
        )
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication'
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),

    'DATETIME_FORMAT': "%d-%m-%Y %H:%M:%S",
}

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE =  'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = False

ACCOUNT_AUTHENTICATION_METHOD = 'username'
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'phone_number'
ACCOUNT_USERNAME_MIN_LENGTH = 10
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
#STATIC_ROOT = os.path.join(BASE_DIR, "static/")
STATIC_ROOT = os.path.join(BASE_DIR, "static_root")
STATICFILES_DIRS = ( os.path.join(BASE_DIR, "static"),)

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = '/media/'

OTP_LENGTH = 6
OTP_CHARS = '0123456789'
OTP_ATTEMPTS = 5
OTP_RESEND_IN = 30

DEFAULT_CITY_CODE = '07'
PO_STARTS_WITH = 'ADT/PO'
CN_STARTS_WITH = 'ADT/CN'
INVOICE_STARTS_WITH = 'ORD'

EMAIL_BACKEND = 'django_ses.SESBackend' #"smtp.sendgrid.net" #
EMAIL_USE_TLS = True
EMAIL_PORT = 587
# EMAIL_HOST_USER = config('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
# FROM_EMAIL = config('FROM_EMAIL')


MIME_TYPE = 'html'

AWS_SES_ACCESS_KEY_ID = config('AWS_SES_ACCESS_KEY_ID')
AWS_SES_SECRET_ACCESS_KEY = config('AWS_SES_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = 'us-east-1'
AWS_SES_CONFIGURATION_SET = 'gramfactory_basic_emails'

OLD_PASSWORD_FIELD_ENABLED = True
LOGOUT_ON_PASSWORD_CHANGE = True

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
#AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN')
AWS_S3_CUSTOM_DOMAIN_ORIG = config('AWS_S3_CUSTOM_DOMAIN_ORIG')
AWS_S3_OBJECT_PARAMETERS = {
  'CacheControl': 'max-age=86400',
}
MEDIAFILES_LOCATION = 'media'
DEFAULT_FILE_STORAGE = 'retailer_backend.storage.MediaStorage'

order_gram_to_brand_group = 'gram_to_brand_order_group'
grn_gram_to_brand_group = 'grn_brand_to_gram_group'
BLOCKING_TIME_IN_MINUTS = config('BLOCKING_TIME_IN_MINUTS')

WKHTMLTOPDF_CMD = '/usr/local/bin/wkhtmltopdf'
WKHTMLTOPDF_CMD_OPTIONS = {
    'quiet': True,
}

TEMPUS_DOMINUS_INCLUDE_ASSETS=False

CRONJOBS = [
    ('* * * * *', 'retailer_backend.cron.discounted_order_cancellation', '>> /tmp/discounted_cancellation.log'),
    ('* * * * *', 'retailer_backend.cron.delete_ordered_reserved_products'),
    ('2 0 * * *', 'analytics.api.v1.views.getStock'),
    ('*/10 * * * *', 'retailer_backend.cron.po_status_change_exceeds_validity_date'),
    ('* */6 * * *', 'retailer_backend.cron.sync_es_products'),
    ('30 21 * * *', 'shops.api.v1.views.set_shop_map_cron', '>>/tmp/shops'),

    ('*/1 * * * *', 'wms.views.release_blocking_with_cron', '>>/tmp/release.log'),
    ('*/5 * * * *', 'wms.views.pickup_entry_creation_with_cron', '>>/tmp/picking'),
    ('* */6 * * *', 'retailer_backend.cron.sync_es_products'),
    ('0 2 * * *', 'wms.views.archive_inventory_cron'),
    ('0 1 * * *', 'audit.views.start_automated_inventory_audit'),
    ('0 3 * * *', 'wms.views.move_expired_inventory_cron'),
    ('*/5 * * * *', 'audit.views.update_audit_status'),
    ('*/10 * * * *', 'audit.views.create_audit_tickets')
]

INTERNAL_IPS = ['127.0.0.1','localhost']

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda x: True
}

DEBUG_TOOLBAR_PATCH_SETTINGS = False

# Initiate Sentry SDK
if ENVIRONMENT.lower() in ["production","stage", "qa", "qa1","qa3"]:
    from sentry_sdk.integrations.celery import CeleryIntegration
    sentry_sdk.init(
        dsn="https://2f8d192414f94cd6a0ba5b26d6461684@sentry.io/1407300",
        integrations=[DjangoIntegration(),CeleryIntegration()],
        environment=ENVIRONMENT.lower()
    )

DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000

REDIS_DB_CHOICE = {
    'production': '1',
    'stage': '2',
    'qa': '7',
    'qa1': '9',
    'local-raj':'5',
    'qa3':'6',
    'qa2':'8',
    'local':'10',
}

# JET_THEMES = [
#     {
#         'theme': 'default', # theme folder name
#         'color': '#47bac1', # color of the theme's button in user menu
#         'title': 'Default' # theme title
#     },
#     {
#         'theme': 'green',
#         'color': '#44b78b',
#         'title': 'Green'
#     },
#     {
#         'theme': 'light-green',
#         'color': '#2faa60',
#         'title': 'Light Green'
#     },
#     {
#         'theme': 'light-violet',
#         'color': '#a464c4',
#         'title': 'Light Violet'
#     },
#     {
#         'theme': 'light-blue',
#         'color': '#5EADDE',
#         'title': 'Light Blue'
#     },
#     {
#         'theme': 'light-gray',
#         'color': '#222',
#         'title': 'Light Gray'
#     }
# ]
# JET_SIDE_MENU_COMPACT = True

FCM_MAX_RECIPIENTS = 1000
REDIS_URL = "{}/{}".format(config('CACHE_HOST'), REDIS_DB_CHOICE[ENVIRONMENT.lower()])
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


CELERY_ROUTES = {
    'analytics.api.v1.views': {'queue': 'analytics_tasks'},
}

# ElasticSearch
ELASTICSEARCH_PREFIX = config('ELASTICSEARCH_PREFIX')
ELASTICSEARCH_DSL={
    'default': {
        'hosts': '35.154.13.198:9200'
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "gfcache"
    }
}
#DataFlair #Logging Information
LOGGING = {
   'version': 1,
   'disable_existing_loggers': False,
   'loggers': {
       'django': {
           'handlers': ['file-info','file-error'],
           'level': 'INFO',
           'propagate': True,
       },
        'file-info': {
                   'handlers': ['file-info'],
                   'level': 'INFO',
                   'propagate': True,
               },
        'file-error': {
           'handlers': ['file-error'],
           'level': 'INFO',
           'propagate': True,
       },
       'cron_log': {
            'handlers': ['cron_log_file'],
            'level': 'INFO',
            'propagate': True,
        },
   },
   'handlers': {
       # 'file-debug': {
       #     'level': 'DEBUG',
       #     'class': 'logging.FileHandler',
       #     'filename': '/var/log/retailer-backend/debug.log',
       #     'formatter': 'verbose',
       # },
       'file-info': {
           'level': 'INFO',
           'class': 'logging.FileHandler',
           'filename': '/var/log/retailer-backend/info.log',
           'formatter': 'verbose',
       },
       'file-error': {
           'level': 'ERROR',
           'class': 'logging.FileHandler',
           'filename': '/var/log/retailer-backend/error.log',
           'formatter': 'verbose',
       },
       # 'console': {
       #     'class': 'logging.StreamHandler',
       #     'formatter': 'simple',
       # },
        'cron_log_file': {
             'level': 'INFO',
             'class': 'logging.FileHandler',
             'filename': '/var/log/retailer-backend/scheduled_jobs.log',
             'formatter': 'verbose'
         },

   },
   'formatters': {
       'verbose': {
           'format': '%(levelname)s|%(asctime)s|%(module)s|%(process)d|%(thread)d|%(message)s',
           'datefmt' : "%d/%b/%Y %H:%M:%S"
       },
       'simple': {
           'format': '%(levelname)s|%(message)s'
       },
   },
}
