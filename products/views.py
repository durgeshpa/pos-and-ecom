from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from .models import ProductImage, Product, ProductPrice
from shops.models import Shop, ShopType
from .forms import ProductPriceForm, ProductsFilterForm, ProductsPriceFilterForm
from addresses.models import City, State, Address
from django.contrib import messages
import csv, codecs, datetime
from django.http import HttpResponse
from brand.models import Brand
from categories.models import Category
from products.models import Product, ProductCategory

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

def load_brands(request):
    id = request.GET.get('category_id')
    if id:
        from urllib.parse import unquote
        id = list(filter(None, [x.strip() for x in unquote(id).split(',')]))
        category_id = Category.objects.filter(id__in=id).values('id')
        product_id = ProductCategory.objects.filter(category__in=category_id).values_list('product')
        product_brand = Product.objects.filter(id__in=product_id).values_list('product_brand')
        brands = Brand.objects.filter(id__in=product_brand).order_by('brand_name')
        return render(request, 'admin/products/brand_dropdown_list_options.html', {'brands': brands})
    else:
        brands = Brand.objects.none()
        return render(request, 'admin/products/brand_dropdown_list_options.html', {'brands': brands})

def sp_sr_productprice(request):
    if request.method == 'POST':
        form = ProductPriceForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/productpriceupload.html', {'form':form})
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

    else:
        form = ProductPriceForm(initial = {'sp_sr_list': Shop.objects.none()})
    return render(request, 'admin/products/productpriceupload.html', {
                                            'form':form,
                                            }
                )


def ProductsFilterView(request):
    if request.method == 'POST':
        form = ProductsFilterForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/productsfilter.html', {'filter_form':filter_form})
        if form.is_valid():
            dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
            filename = str(dt)+"product_list.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            writer.writerow(['id','product_name', 'mrp', 'ptsp', 'ptsr', 'ptr'])
            brands = form.cleaned_data['brand']
            products = Product.objects.filter(product_brand__in=brands)
            for product in products:
                writer.writerow([product.id,product.product_name,'','','',''])
            return response
    else:
        filter_form = ProductsFilterForm()
    return render(request, 'admin/products/productsfilter.html', {
                                            'filter_form':filter_form}
                )

def ProductsPriceFilterView(request):
    if request.method == 'POST':
        form = ProductsPriceFilterForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/productpricefilter.html', {'form':form})
        if form.is_valid():
            city = form.cleaned_data['city'].id
            sp_sr = form.cleaned_data['sp_sr_choice'].shop_type
            shops = form.cleaned_data['sp_sr_list']
            dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
            filename = str(dt)+"product_price_list.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            if sp_sr == "sp":
                writer.writerow(['product_id','product_name', 'mrp', 'ptsp', 'ptr', 'price_start_date', 'price_end_date', 'sp_name'])
                for shop in shops:
                    products = ProductPrice.objects.filter(shop=shop).order_by('product','-created_at').distinct('product')
                    for product in products:
                        writer.writerow([product.product.id,product.product.product_name,product.mrp,product.price_to_service_partner,product.price_to_retailer,product.start_date,product.end_date,product.shop.shop_name])
            if sp_sr == "sr":
                writer.writerow(['product_id','product_name', 'mrp', 'ptr', 'price_start_date', 'price_end_date', 'sr_name'])
                for shop in shops:
                    products = ProductPrice.objects.filter(shop=shop).order_by('product','-created_at').distinct('product')
                    for product in products:
                        writer.writerow([product.product.id,product.product.product_name,product.mrp,product.price_to_retailer,product.start_date,product.end_date,product.shop.shop_name])
            return response




    else:
        form = ProductsPriceFilterForm()
    return render(request, 'admin/products/productpricefilter.html', {
                                            'form':form,
                                            }
                )

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

def ProductsUploadSample(request):
    filename = "products_upload_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_name','product_slug','product_short_description','product_long_description','product_sku','product_ean_code','product_status','p_cat_id','p_cat_status','p_size_id','p_color_id','p_fragrance_id','p_flavor_id','p_weight_id','p_package_size_id','p_tax_id','p_tax_status','p_surcharge_name','p_surcharge_percentage','p_surcharge_start_at','p_surcharge_end_at','p_surcharge_status'])
    writer.writerow(['fortune sunflowers oil','fortune-sunflower-refined-oil','Fortune Sun Lite Refined Sunflower Oil is a healthy','Fortune Sun Lite Refined Sunflower Oil is a healthy, light and nutritious oil that is simple to digest. Rich in natural vitamins, it consists mostly of poly-unsaturated fatty acids (PUFA) and is low in soaked fats. It is strong and makes you feel light and active level after heavy food.','12BBPRG00000121','1234567890123','1','1','1','1','1','1','1','1','1','1','1','oilsubcharge','1','2012-09-04 06:00:00','2012-09-04 06:00:00','0'])
    return response
