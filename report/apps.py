# -*- coding: utf-8 -*-

from django.apps import AppConfig


class ReportConfig(AppConfig):
    name = 'report'
    verbose_name = 'Report Centre'

    def ready(self, *args, **kwargs):
        from django.db.models.signals import post_save
        from report.models import AsyncReportRequest
        from report.signal_handlers import (async_report_post_save,)

        post_save.connect(async_report_post_save, sender=AsyncReportRequest)
