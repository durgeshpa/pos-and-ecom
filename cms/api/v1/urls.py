from django.urls import path

from .views import ApplicationDetailView, ApplicationView
urlpatterns = [
    path('apps/', ApplicationView.as_view(), name = 'apps'),
    path('apps/<id>', ApplicationDetailView.as_view(), name = 'app_detail')
]
