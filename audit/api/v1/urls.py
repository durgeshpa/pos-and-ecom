from django.conf.urls import url

from audit.api.v1.views import AuditListView, AuditStartView

urlpatterns = [
    url(r'^audits/$', AuditListView.as_view(), name='audits'),
    url(r'^audit-start/$', AuditStartView.as_view(), name='audits'),

]