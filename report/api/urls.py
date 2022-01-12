# -*- coding: utf-8 -*-

from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from report.api.views import (AsyncReportCreateUpdateView, 
                              AsyncReportFileView, 
                              AsyncReportListRetrieveView)


router = DefaultRouter()

router.register('reports', AsyncReportListRetrieveView, base_name='reports')
router.register('create-update-reports', AsyncReportCreateUpdateView, base_name='create-update-reports')

urlpatterns = [
    url(r'^report-file/(?P<id>\d+)/$', AsyncReportFileView.as_view())
]

urlpatterns += router.urls