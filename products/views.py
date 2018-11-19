from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from .models import ProductImage, Product, ProductPrice
from shops.models import Shop, ShopType
from .forms import ProductPriceForm
from addresses.models import City, State, Address
from django.contrib import messages
import csv, codecs

def load_cities(request):
    state_id = request.GET.get('state')
    if state_id:
        cities = City.objects.filter(state=state_id).order_by('city_name')
    else:
        cities = City.objects.none()
    return render(request, 'admin/products/city_dropdown_list_options.html', {'cities': cities})

def load_sp_sr(request):
    state_id = request.GET.get('state_id')
    city_id = request.GET.get('city_id')
    sp_sr = request.GET.get('sp_sr')
    if sp_sr and city_id and state_id:
        shops_id = Address.objects.filter(city=city_id).values_list('shop_name', flat=True)
        shops = Shop.objects.filter(pk__in=shops_id, shop_type=sp_sr).order_by('shop_name')
        return render(request, 'admin/products/shop_dropdown_list_options.html', {'shops': shops})
    else:
        shops = Shop.objects.none()
        return render(request, 'admin/products/shop_dropdown_list_options.html', {'shops': shops})

def sp_sr_productprice(request):
    if request.method == 'POST':
        form = ProductPriceForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/index.html', {'form':form})
        if form.is_valid():
            file = form.cleaned_data['file']
            city = form.cleaned_data['city'].id
            start_date = form.cleaned_data['start_date_time']
            end_date = form.cleaned_data['end_date_time']
            sp_sr = form.cleaned_data['sp_sr_choice'].shop_type
            shops = form.cleaned_data['sp_sr_list']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            for row in reader:
                for shop in shops:
                    try:
                        if sp_sr == "sp":
                            product_price = ProductPrice.objects.create(
                            product_id=row[0],
                            city_id = city,
                            mrp = row[2],
                            shop_id = shop.id,
                            price_to_retailer=row[5],
                            price_to_service_partner=row[3],
                            start_date=start_date,
                            end_date=end_date)

                        elif sp_sr == "sr":
                            product_price = ProductPrice.objects.create(
                            product_id=row[0],
                            city_id = city,
                            mrp = row[2],
                            shop_id = shop.id,
                            price_to_super_retailer=row[4],
                            start_date=start_date,
                            end_date=end_date)
                            messages.success(request, 'Price uploaded successfully')
                            return redirect('admin:sp_sr_productprice')

                    except:
                        raise ValidationError("Something went wrong!")
            #return render(request, 'admin/products/index.html', {'form':form})

    else:
        form = ProductPriceForm(initial = {'sp_sr_list': Shop.objects.none()})
    return render(request, 'admin/products/index.html', {'form':form})

def create_product_price(self, **kwargs):
    product = Product.objects.get(id=kwargs.get('product_id'),\
              product_name=kwargs.get('product_name'))
    try:
        product_price = ProductPrice.objects.get(product=product)
        product_price.price_to_retailer=kwargs.get('retailer_price')
        product_price.price_to_super_retailer=kwargs.get('super_retailer_price')
        product_price.price_to_service_partner=kwargs.get('service_partner_price')
        product_price.save()
    except:
        ProductPrice.objects.create(product=product,\
                 price_to_retailer=kwargs.get('retailer_price'),\
                 price_to_super_retailer=kwargs.get('super_retailer_price'),\
                 price_to_service_partner=kwargs.get('service_partner_price'))

import csv, datetime
from django.http import HttpResponse
def export(request):
    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt)+"product_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['id','product_name', 'mrp', 'ptsp', 'ptsr', 'ptr'])
    products = Product.objects.values_list('id','product_name')
    for product in products:
        writer.writerow([product[0],product[1],'','','',''])
    return response
