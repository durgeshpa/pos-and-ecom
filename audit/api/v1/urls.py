from django.conf.urls import url

from audit.api.v1.views import AuditListView, AuditStartView, AuditBinList, AuditInventory, AuditBinsBySKUList, \
    AuditEndView, AuditSKUsByBinList

urlpatterns = [
    url(r'^audits/$', AuditListView.as_view(), name='audits'),
    url(r'^audit-start/$', AuditStartView.as_view(), name='start-audit'),
    url(r'^audit-end/$', AuditEndView.as_view(), name='start-end'),
    url(r'^audit-bin/$', AuditBinList.as_view(), name='audit-bin'),
    url(r'^audit-sku-bin/$', AuditBinsBySKUList.as_view(), name='audit-sku-bin'),
    url(r'^audit-bin-sku/$', AuditSKUsByBinList.as_view(), name='audit-bin-sku'),
    url(r'^audit-inventory/$', AuditInventory.as_view(), name='audit-inventory'),
]