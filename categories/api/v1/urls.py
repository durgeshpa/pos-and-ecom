from django.conf.urls import include, url

from .views import (GetAllSubCategoryListView, GetCategoryListBySlot, GetcategoryBrandListView,
                    GetSubCategoriesListView, GetAllCategoryListView, CategoryView, GetSubCategoryById)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^get-all-category/$', GetAllSubCategoryListView.as_view({'get': 'list'}), name='get_all_category'),
    url(r'^get-category-list-by-slot/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
    url(r'^get-category-list-by-slot/(?P<slot_name>[\w\-]+)/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
    url(r'^get-category-brand/(?P<category>[-\w]+)/$', GetcategoryBrandListView.as_view(), name='get_category_brand'),
    url(r'^get-sub-categories/(?P<category>[-\w]+)/$', GetSubCategoriesListView.as_view(), name='get_subcategories'),
    url(r'^get-all-categories/$', GetAllCategoryListView.as_view(), name='get_all_category_subcategory'),
    url(r'^category/$', CategoryView.as_view(), name='category'),
    url(r'^get-sub-category/$', GetSubCategoryById.as_view(), name='get-sub-category'),
]
