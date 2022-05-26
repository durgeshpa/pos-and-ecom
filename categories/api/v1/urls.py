from django.conf.urls import include, url

from .views import (GetAllSubCategoryListView, GetCategoryListBySlot, GetcategoryBrandListView,
                    GetSubCategoriesListView, GetAllCategoryListView, CategoryView, CategoryExportAsCSVView,
                    GetAllB2cSubCategoryListView, GetB2cCategoryListBySlot, GetAllB2cCategoryListView, B2cCategoryView, 
                    B2cCategoryExportAsCSVView, ActivateDeactivateCategories)

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^get-all-category/$', GetAllSubCategoryListView.as_view({'get': 'list'}), name='get_all_category'),
    url(r'^get-category-list-by-slot/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
    url(r'^get-category-list-by-slot/(?P<slot_name>[\w\-]+)/$', GetCategoryListBySlot.as_view(), name='get_all_category'),
    url(r'^get-category-brand/(?P<category>[-\w]+)/$', GetcategoryBrandListView.as_view(), name='get_category_brand'),
    url(r'^get-sub-categories/(?P<category>[-\w]+)/$', GetSubCategoriesListView.as_view(), name='get_subcategories'),
    url(r'^get-all-categories/$', GetAllCategoryListView.as_view(), name='get_all_category_subcategory'),
    url(r'^category/$', CategoryView.as_view(), name='category'),
    url(r'^export-csv-category/$', CategoryExportAsCSVView.as_view(), name='export-csv-category'),
    url(r'^get-all-b2c-category/$', GetAllB2cSubCategoryListView.as_view({'get': 'list'}), name='get_all_b2c_category'),
    url(r'^get-b2c-category-list-by-slot/$', GetB2cCategoryListBySlot.as_view(), name='get_b2c_category_all_slot'),
    url(r'^get-b2c-category-list-by-slot/(?P<slot_name>[\w\-]+)/$', GetB2cCategoryListBySlot.as_view(), name='get_b2c_category_by_slot'),
    url(r'^get-all-b2c-categories/$', GetAllB2cCategoryListView.as_view(), name='get_all_b2c_category_subcategory'),
    url(r'^b2c-category/$', B2cCategoryView.as_view(), name='b2c_category'),
    url(r'^export-csv-b2c-category/$', B2cCategoryExportAsCSVView.as_view(), name='export_csv_b2c_category'),
    url(r'^category-activate-deactivate/$', ActivateDeactivateCategories.as_view(), name='category-activate-deactivate')
]