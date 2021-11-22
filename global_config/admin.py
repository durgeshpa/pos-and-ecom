from django.contrib import admin

# Register your models here.
from global_config.models import GlobalConfig


@admin.register(GlobalConfig)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value")

