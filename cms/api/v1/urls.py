from django.urls import path
from . import views

urlpatterns = [
    path('apps/', views.ApplicationView.as_view(), name = 'apps'),
    path('apps/<id>/', views.ApplicationDetailView.as_view(), name = 'app_detail'),
	path("cards/", views.CardView.as_view(), name="cards" ),
	path("cards/<id>/", views.CardDetailView.as_view(), name="card_detail"),
    path("items/", views.ItemsView.as_view(), name="items"),
    path("pages/", views.PageView.as_view(), name = 'pages'),
    path("pages/<id>/", views.PageDetailView.as_view(), name = 'page_detail'),
    path('pages/<id>/latest/', views.PageVersionDetailView.as_view(), name = 'page_version_latest')
]
