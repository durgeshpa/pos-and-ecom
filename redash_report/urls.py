from django.urls import path

from .views import scheduled_report

urlpatterns = [
	path('', scheduled_report),
]
