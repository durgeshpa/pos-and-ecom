from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from .serializers import UserIDSerializer

class UserID(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    allowed_methods = ('GET')

    def get(self, request, format=None):
        return Response("Hello {0}!".format(request.user.pk))
