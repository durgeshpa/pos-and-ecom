import logging
import requests

from django.http.response import Http404, HttpResponseBadRequest, FileResponse
from django.shortcuts import render
from django.views import View
from dal import autocomplete
from django.db.models import Q
from django.shortcuts import get_object_or_404

from shops.models import Shop
from pos.models import RetailerProduct
from ecom.models import EcommerceOrderedProduct

# Create your views here.
class EcomShopAutoCompleteView(autocomplete.Select2QuerySetView):
    """
    shop filter for ecom tagged product
    """

    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type__in=['f'], status=True, approval_status=2, 
                                pos_enabled=True)
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs

class EcomProductAutoCompleteView(autocomplete.Select2QuerySetView):
    """
    product filter for ecom tagged product on basis of shop
    """
    
    def get_queryset(self, *args, **kwargs):
        qs = RetailerProduct.objects.none()
        shop = self.forwarded.get('shop', None)
        if shop:
            qs = RetailerProduct.objects.filter(~Q(sku_type=4), shop=shop, online_enabled = True).order_by('-created_at')
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs


class DownloadEcomOrderInvoiceView(View):

    def get(self, request, pk):
        try:
           order = get_object_or_404(EcomOrderedProduct, pk=pk)
           if order.invoice.invoice_pdf.url:
                with requests.Session() as s:
                    try:
                        import io
                        response = s.get(order.invoice.invoice_pdf.url)
                        response = FileResponse(io.BytesIO(response.content), content_type='application/pdf')
                        response['Content-Length'] = response['Content-Length']
                        response['Content-Disposition'] = 'attachment; filename="%s"' % order.invoice.pdf_name
                        return response
                    except Exception as err:
                        return HttpResponseBadRequest(err)
           else:
                return HttpResponseBadRequest("Invoice not generated")
        except EcomOrderedProduct.DoesNotExist:
            raise Http404("Resource not found on server")
        except Exception as err:
            logging.exception("Invoice download failed due to %s" % err)
            return HttpResponseBadRequest("Invoice download failed due to %s" % err)