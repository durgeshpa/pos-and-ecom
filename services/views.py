import requests
from PIL import Image
import PIL

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse

# Create your views here.

class ResizeImage(APIView):
    permission_classes = (AllowAny,)
    def get(self,request, *args, **kwargs):
    	img_url = request.GET.get('image_url')
    	width = int(request.GET.get('width', '200'))
    	height = request.GET.get('height', None)
    	img_response = requests.get(img_url, stream=True)
    	img_response.raw.decode_content = True
    	image = Image.open(img_response.raw)

    	if not height:
    		height = int(image.height * width/image.width)
    	image = image.resize((width,height), PIL.Image.LANCZOS)
    	response = HttpResponse(content_type="image/jpeg")
    	image.save(response, "JPEG")
    	return response
