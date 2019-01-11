from django.shortcuts import render
from products.models import Product, ProductPrice
from categories.models import Category
from django.shortcuts import render, get_object_or_404
from gram_to_brand.models import GRNOrderProductMapping
from dal import autocomplete
from shops.models import Shop,ParentRetailerMapping
from addresses.models import Address
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from wkhtmltopdf.views import PDFTemplateResponse
from sp_to_gram.models import Cart


# Create your views here.
def abc():
    pass

class GfShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self,*args,**kwargs):
        # if not self.request.is_authenticated():

        qs = Shop.objects.all()

        state = self.forwarded.get('state', None)
        if state:
            shop_id = Address.objects.filter(state__id=state).values('shop_name')
            qs = qs.filter(id__in=[shop_id])

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)

        return qs

class GfProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        my_shop = self.forwarded.get('shop', None)

        if my_shop:
            parent_mapping = ParentRetailerMapping.objects.get(retailer__id=my_shop)
            grn_pro = GRNOrderProductMapping.objects.filter(grn_order__order__ordered_cart__gf_shipping_address__shop_name=parent_mapping.parent).annotate(Sum('available_qty'))
            product = grn_pro.values('product')
            qs = Product.objects.filter(id__in=[product])

        if self.q:
            qs = Product.objects.filter(shop_name__startswith=self.q)

        return qs


class MyShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Shop.objects.filter(shop_type__shop_type='sp',shop_owner=self.request.user)

        if self.q:
            qs = qs.filter(shop_name__startswith=self.q)
            print(qs)
        return qs


class SpProductPrice(APIView):
    permission_classes = (AllowAny,)
    def get(self,*args,**kwargs):
        shop_id =self.request.GET.get('shop_id')
        product_id =self.request.GET.get('product_id')

        parent_mapping = ParentRetailerMapping.objects.get(retailer=shop_id,status=True)
        pro_price = ProductPrice.objects.filter(product__id=product_id,shop=parent_mapping.parent)
        if pro_price.exists():
            pro_price = pro_price.last()
            service_partner_price = pro_price.price_to_service_partner
            product_case_size = pro_price.product.product_case_size
        else:
            service_partner_price = ""
            product_case_size = ""
        return Response({"service_partner_price": service_partner_price, "product_case_size": product_case_size,"success": True})

class DownloadPurchaseOrderSP(APIView):
    permission_classes = (AllowAny,)
    """
    PDF Download object
    """
    filename = 'purchase_order_sp.pdf'
    template_name = 'admin/purchase_order/sp_purchase_order.html'

    def get(self, request, *args, **kwargs):
        order_obj = get_object_or_404(Cart, pk=self.kwargs.get('pk'))
        #shop =order_obj
        products = order_obj.sp_cart_list.all()
        order= order_obj.sp_order_cart_mapping.last()
        order_id= order.order_no
        sum_qty = 0
        sum_amount=0
        tax_inline=0
        taxes_list = []
        gst_tax_list= []
        cess_tax_list= []
        surcharge_tax_list=[]
        for m in products:

            sum_qty = sum_qty + m.qty
            sum_amount = sum_amount + (m.qty * m.price)
            inline_sum_amount = (m.qty * m.price)
            for n in m.cart_product.product_pro_tax.all():

                divisor= (1+(n.tax.tax_percentage/100))
                original_amount= (inline_sum_amount/divisor)
                tax_amount = inline_sum_amount - original_amount
                if n.tax.tax_type=='gst':
                    gst_tax_list.append(tax_amount)
                if n.tax.tax_type=='cess':
                    cess_tax_list.append(tax_amount)
                if n.tax.tax_type=='surcharge':
                    surcharge_tax_list.append(tax_amount)

                taxes_list.append(tax_amount)
                igst= sum(gst_tax_list)
                cgst= (sum(gst_tax_list))/2
                sgst= (sum(gst_tax_list))/2
                cess= sum(cess_tax_list)
                surcharge= sum(surcharge_tax_list)

            print(surcharge_tax_list)
            print(gst_tax_list)
            print(cess_tax_list)
            print(taxes_list)

        total_amount = sum_amount
        print(sum_amount)

        data = {"object": order_obj,"products":products, "shop":order_obj, "sum_qty": sum_qty, "sum_amount":sum_amount,
                "url":request.get_host(), "scheme": request.is_secure() and "https" or "http" , "igst":igst, "cgst":cgst,
                "sgst":sgst,"cess":cess,"surcharge":surcharge, "total_amount":total_amount,"order_id":order_id}
        for m in products:
            data = {"object": order_obj,"products":products,"amount_inline": m.qty * m.price }
        cmd_option = {"margin-top": 10, "zoom": 1, "javascript-delay": 1000, "footer-center": "[page]/[topage]",
                      "no-stop-slow-scripts": True, "quiet": True}
        response = PDFTemplateResponse(request=request, template=self.template_name, filename=self.filename,context=data, show_content_in_browser=False, cmd_options=cmd_option)
        return response

