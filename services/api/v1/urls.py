# from django.conf.urls import url
# from django.urls import path
# from rest_framework.authtoken.views import obtain_auth_token
# from services.api.v1.views import (OrderDetailView, OrderReportsView, OrderReportView, GRNReportsView, GRNReportView, MasterReportsView, MasterReportView,
#                                    OrderGrnReportsView, RetailerReportsView, CategoryProductReportsView)
#
# urlpatterns = [
#     path('detail-type/', OrderDetailView.as_view(), name='detail-type', ),
#     path('orderReport-type/', OrderReportsView.as_view(), name='orderReport-type',),
#     path('orderReport-type/<int:pk>/', OrderReportView.as_view(), name="orderReport-detail",),
#     path('grnReports-type/', GRNReportsView.as_view(), name='grnReports-type',),
#     path('grnReports-type/<int:pk>/', GRNReportView.as_view(), name='grnReport-detail',),
#     path('masterReports-type/', MasterReportsView.as_view(), name='masterReports-type',),
#     path('masterReports-type/<int:pk>/', MasterReportView.as_view(), name='masterReport-detail',),
#     path('orderGrn-type/', OrderGrnReportsView.as_view(), name='orderGrn-type', ),
#     path('retailer-report/', RetailerReportsView.as_view(), name='retailer-report',),
#     path('category-report/', CategoryProductReportsView.as_view(), name='category-report',),
#     path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
#
#
# ]