from django.shortcuts import render
from rest_framework.views import APIView
from rest_auth import authentication
from rest_framework import permissions
from rest_framework.response import Response


# Create your views here.
class TestAuthView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        return Response("Hello {0}!".format(request.user))
