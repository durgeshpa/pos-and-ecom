from django.urls import path
from . import views

urlpatterns = [
	path("cards/", views.CardView.as_view(), name="cards" ),
	path("cards/<id>", views.CardDetailView.as_view(), name="card_detail")
]
