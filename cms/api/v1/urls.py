from django.urls import path
from . import views
from .views import LandingPageView, PageFunctionView, LandingPageTypeList, LandingPageSubTypeList, CardTypeList, \
    ImageTypeList

urlpatterns = [
    path('apps/', views.ApplicationView.as_view(), name = 'apps'),
    path('apps/<id>/', views.ApplicationDetailView.as_view(), name = 'app_detail'),
	path("cards/", views.CardView.as_view(), name="cards" ),
	path("cards/<id>/", views.CardDetailView.as_view(), name="card_detail"),
    path("items/", views.ItemsView.as_view(), name="items"),
    path("pages/", views.PageView.as_view(), name = 'pages'),
    path("pages/<id>/", views.PageDetailView.as_view(), name = 'page_detail'),
    path('pages/<id>/latest/', views.PageVersionDetailView.as_view(), name = 'page_version_latest'),
    path('category/', views.CategoryListView.as_view(), name = 'cms-category-list'),
    path('subcategory-banner/', views.SubCategoryListView.as_view(), name = 'cms-subcategory-list'),
    path('brand/', views.BrandListView.as_view(), name = 'cms-brand-list'),
    path('subbrand-banner/', views.SubBrandListView.as_view(), name = 'cms-subbrand-list'),
    path("landing-pages/", LandingPageView.as_view(), name = 'landing-pages'),
    path("functions/", PageFunctionView.as_view(), name = 'functions'),
    path("choice-card-type/", CardTypeList.as_view()),
    path("choice-lp-type/", LandingPageTypeList.as_view()),
    path("choice-lp-subtype/", LandingPageSubTypeList.as_view()),
    path("choice-image-type/", ImageTypeList.as_view()),
    path("templates/", views.TemplateCRUDView.as_view(), name="templates" ),

]
