from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Banner, BannerPosition
from .serializers import BannerSerializer
@api_view(['GET', 'POST'])
def banner_list(request):
    if request.method == 'GET':
        banners = Banner.objects.filter(Status=True)
        serializer = BannerSerializer(banners, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BannerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def banner_detail(request,pk):
    """
    Retrieve, update or delete a code banner.
    """
    try:
        banner = Banner.objects.get(pk=pk)
    except Banner.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = BannerSerializer(banner)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = BannerSerializer(banner, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        banner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
