import requests
from PIL import Image
import PIL

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse, Http404
from django.conf import settings
# Create your views here.

class ResizeImage(APIView):
    permission_classes = (AllowAny,)
    def get(self,request, image_path, image_name, *args, **kwargs):
        path = "/".join(args)
        img_url = "https://{}/{}/{}".format(getattr(settings, 'AWS_S3_CUSTOM_DOMAIN_ORIG'), image_path,image_name, path)
        width = int(request.GET.get('width', '600'))
        height = request.GET.get('height', None)
        img_response = requests.get(img_url, stream=True)
        if img_response.status_code == 404:
            raise Http404("Image not found")
        content_type = img_response.headers.get('Content-Type')
        img_response.raw.decode_content = True
        image = Image.open(img_response.raw)

        if not height:
            height = int(image.height * width/image.width)
        image = image.resize((width,height), PIL.Image.LANCZOS)
        response = HttpResponse(content_type=content_type)
        image_type = {
            'image/png': 'PNG',
            'image/jpeg': 'JPEG',
            'image/jpg' : 'JPEG'
        }
        image.save(response, image_type[content_type])
        return response
