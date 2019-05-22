from tastypie.resources import ModelResource
from django.contrib.auth import get_user_model
from tastypie.authentication import (
	BasicAuthentication, ApiKeyAuthentication
)


User = get_user_model()

class MyModelResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        allowed_methods = ['get']
        authentication = BasicAuthentication()