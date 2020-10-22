from django.conf.urls import url

from audit.api.v1.views import AuditListView, AuditStartView, AuditBinList, AuditInventory

urlpatterns = [
    url(r'^audits/$', AuditListView.as_view(), name='audits'),
    url(r'^audit-start/$', AuditStartView.as_view(), name='start-audit'),
    url(r'^audit-bin/$', AuditBinList.as_view(), name='audit-bin'),
    url(r'^audit-inventory/$', AuditInventory.as_view(), name='audit-inventory'),
]