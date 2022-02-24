# -*- coding: utf-8 -*-

from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from report.api.views import (ReportChoiceListView, ReportCreateUpdateView, 
                              DownloadPrivateFileAws, 
                              ReportListRetrieveView)


router = DefaultRouter()

router.register('report-choices', ReportChoiceListView, base_name='report-choices')
router.register('reports', ReportListRetrieveView, base_name='reports')
router.register('create-update-reports', ReportCreateUpdateView, base_name='create-update-reports')

urlpatterns = [
    url(r'^get-file-aws/$', DownloadPrivateFileAws.as_view(), name='get-file-aws')
]

urlpatterns += router.urls