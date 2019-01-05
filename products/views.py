from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from .models import ProductImage, Product, ProductPrice
from shops.models import Shop, ShopType
from .forms import GFProductPriceForm,ProductPriceForm, ProductsFilterForm, ProductsPriceFilterForm, ProductsCSVUploadForm
from addresses.models import City, State, Address
from django.contrib import messages
import csv, codecs, datetime
from django.http import HttpResponse
from brand.models import Brand
from categories.models import Category
from products.models import Product, ProductCategory, ProductOption, ProductTaxMapping, ProductVendorMapping
from django.core.exceptions import ValidationError
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

def load_gf(request):
    state_id = request.GET.get('state_id')
    city_id = request.GET.get('city_id')
    if city_id and state_id:
        shops_id = Address.objects.filter(city=city_id).values_list('shop_name', flat=True)
        shoptype = ShopType.objects.filter(shop_type="gf")
        shops = Shop.objects.filter(pk__in=shops_id, shop_type__in=shoptype).order_by('shop_name')
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
            try:
                for row in reader:
                    for shop in shops:
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

            except:
                messages.error("Something went wrong!")
            return redirect('admin:sp_sr_productprice')


    else:
        form = ProductPriceForm(initial = {'sp_sr_list': Shop.objects.none()})
    return render(request, 'admin/products/productpriceupload.html', {
                                            'form':form,
                                            }
                )

def GFProductPrice(request):
    if request.method == 'POST':
        form = GFProductPriceForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/gfproductpriceupload.html', {'form':form})
        if form.is_valid():
            file = form.cleaned_data['file']
            city = form.cleaned_data['city'].id
            start_date = form.cleaned_data['start_date_time']
            end_date = form.cleaned_data['end_date_time']
            shops = form.cleaned_data['gf_list']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            try:
                for row in reader:
                    for shop in shops:
                        product_price = ProductPrice.objects.create(
                        product_id=row[0],
                        city_id = city,
                        mrp = row[2],
                        shop_id = shop.id,
                        price_to_retailer=row[5],
                        price_to_service_partner=row[3],
                        price_to_super_retailer=row[4],
                        start_date=start_date,
                        end_date=end_date)

                messages.success(request, 'Price uploaded successfully')

            except:
                messages.error("Something went wrong!")
            return redirect('admin:gf_productprice')


    else:
        form = GFProductPriceForm(initial = {'gf_list': Shop.objects.none()})
    return render(request, 'admin/products/gfproductpriceupload.html', {
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
            if sp_sr == "gf":
                writer.writerow(['product_id','product_name', 'mrp', 'ptsp','ptsr','ptr', 'price_start_date', 'price_end_date', 'sr_name'])
                for shop in shops:
                    products = ProductPrice.objects.filter(shop=shop).order_by('product','-created_at').distinct('product')
                    for product in products:
                        writer.writerow([product.product.id,product.product.product_name,product.mrp,product.price_to_service_partner,product.price_to_super_retailer,product.price_to_retailer,product.start_date,product.end_date,product.shop.shop_name])
            return response




    else:
        form = ProductsPriceFilterForm()
    return render(request, 'admin/products/productpricefilter.html', {
                                            'form':form,
                                            }
                )

def ProductsCSVUploadView(request):

    if request.method == 'POST':
        form = ProductsCSVUploadForm(request.POST, request.FILES)
        if form.errors:
            return render(request, 'admin/products/productscsvupload.html', {'form':form})
        if form.is_valid():
            file = form.cleaned_data['file']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            try:
                for row in reader:
                    product = Product.objects.create(product_name=row[0],\
                              product_short_description=row[1],\
                              product_long_description = row[2],\
                              product_gf_code = row[3],\
                              product_ean_code = row[4],\
                              product_brand_id=row[5],\
                              product_inner_case_size=row[14],\
                              product_case_size=row[15])

                    for c in row[6].split(','):
                        if c is not '':
                            ProductCategory.objects.create(product=product,\
                                      category_id=c.strip())

                    # product_category = ProductCategory.objects.bulk_create([ProductCategory(product=product,\
                    #           category_id=c.strip()) for c in row[6].split(',') if c is not ''])

                    productoptions = ProductOption.objects.create(product=product,size_id=row[8] if row[8] else None,\
                            color_id=row[9] if row[9] else None,fragrance_id=row[10] if row[10] else None,\
                            flavor_id=row[11] if row[11] else None,weight_id=row[12] if row[12] else None,\
                            package_size_id=row[13] if row[13] else None)

                    producttax = ProductTaxMapping.objects.bulk_create([ProductTaxMapping(product=product,\
                                tax_id=t.strip()) for t in row[7].split(',') if t is not ''])
                messages.success(request, 'Products uploaded successfully')
            except:
                messages.error(request,"Something went wrong!")
            return redirect('admin:productscsvupload')
    else:
        form = ProductsCSVUploadForm()
    return render(request, 'admin/products/productscsvupload.html', {
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

def products_export_for_vendor(request):
    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt)+"product_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['id','product_name', 'brand_to_gram_price'])
    products = Product.objects.values_list('id','product_name')
    for product in products:
        writer.writerow([product[0],product[1],''])
    return response

def products_vendor_mapping(request,pk=None):
    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt)+"vendor_product_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    try:
        writer.writerow(['id','product_name','case_size','number_of_cases','scheme','brand_to_gram_price'])
        vendor_products = ProductVendorMapping.objects.filter(vendor_id=int(pk)).order_by('product','-created_at').distinct('product')
        for p in vendor_products:
            writer.writerow([p.product_id,p.product.product_name,p.product.product_case_size,'','',p.product_price])
    except:
        writer.writerow(["Make sure you have selected vendor before downloading CSV file"])
    return response

def ProductsUploadSample(request):
    filename = "products_upload_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_name','product_short_description','product_long_description','product_gf_code','product_ean_code','p_brand_id','p_cat_id','p_tax_id','p_size_id','p_color_id','p_fragrance_id','p_flavor_id','p_weight_id','p_package_size_id','p_inner_case_size','p_case_size'])
    writer.writerow(['fortune sunflowers oil','Fortune Sun Lite Refined Sunflower Oil is a healthy','Fortune Sun Lite Refined Sunflower Oil is a healthy, light and nutritious oil that is simple to digest. Rich in natural vitamins, it consists mostly of poly-unsaturated fatty acids (PUFA) and is low in soaked fats. It is strong and makes you feel light and active level after heavy food.','12BBPRG00000121','1234567890123','1','1','1','1','1','1','1','1','1','4','2'])
    return response

def NameIDCSV(request):
    filename = "name_id.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['BRAND NAME','BRAND ID','CATEGORY NAME','CATEGORY ID','TAX NAME','TAX ID','SIZE NAME','SIZE ID','COLOR NAME','COLOR ID','FRAGRANCE NAME','FRAGRANCE ID','FLAVOR NAME','FLAVOR ID','WEIGHT NAME','WEIGHT ID','PACKSIZE NAME','PACKSIZE ID'])
    return response
