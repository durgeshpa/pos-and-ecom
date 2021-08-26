from re import I
from django.shortcuts import render
from django.http import HttpResponse
from .cron import bestseller_product

# Create your views here.
def test(req):
    bestseller_product()
    return HttpResponse('True')
