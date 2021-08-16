from django.conf.urls import url,include

urlpatterns = [
    # URLs that do not require a session or valid token
    url(r'^api/', include('categories.api.urls')),

]
