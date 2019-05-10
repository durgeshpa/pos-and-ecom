import csv
import codecs
import datetime
import os
import logging

from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from shops.models import Shop, ShopType
from addresses.models import City, State, Address
from categories.models import Category
from brand.models import Brand
from .forms import (
    GFProductPriceForm, ProductPriceForm, ProductsFilterForm,
    ProductsPriceFilterForm, ProductsCSVUploadForm, ProductImageForm
    )
from products.models import (
    Product, ProductCategory, ProductOption,
    ProductTaxMapping, ProductVendorMapping,
    ProductImage, ProductHSN, ProductPrice
    )

logger = logging.getLogger(__name__)


def load_cities(request):
    """Return list of cities for specific state id

    :param request: state_id
    :return: list of cities
    """
    state_id = request.GET.get('state')
    if state_id:
        cities = City.objects.filter(state=state_id).order_by('city_name')
    else:
        cities = City.objects.none()

    return render(
        request, 'admin/products/city_dropdown_list_options.html',
        {'cities': cities}
    )


def load_sp_sr(request):
    """Return list of sp/sr for specific state and city

    :param request: state_id, city_id, sp/sr
    :return: list of sp/sr for specific state and city
    """
    state_id = request.GET.get('state_id')
    city_id = request.GET.get('city_id')
    sp_sr = request.GET.get('sp_sr')
    if sp_sr and city_id and state_id:
        shops_id = Address.objects.filter(
            city=city_id
        ).values_list('shop_name', flat=True)

        shops = Shop.objects.filter(
            pk__in=shops_id,
            shop_type=sp_sr
        ).order_by('shop_name')

        return render(
            request,
            'admin/products/shop_dropdown_list_options.html',
            {'shops': shops}
        )
    else:
        shops = Shop.objects.none()
        return render(
            request,
            'admin/products/shop_dropdown_list_options.html',
            {'shops': shops}
        )


def load_gf(request):
    """Returns list of GramFactories for specific state and city

    :param request: state_id, city_id
    :return: list of GramFactories for specific state and city
    """
    state_id = request.GET.get('state_id')
    city_id = request.GET.get('city_id')
    if city_id and state_id:
        shops_id = Address.objects.filter(
            city=city_id
        ).values_list('shop_name', flat=True)

        shoptype = ShopType.objects.filter(shop_type="gf")

        shops = Shop.objects.filter(
            pk__in=shops_id, shop_type__in=shoptype
        ).order_by('shop_name')

        return render(
            request,
            'admin/products/shop_dropdown_list_options.html',
            {'shops': shops}
        )
    else:
        shops = Shop.objects.none()
        return render(
            request,
            'admin/products/shop_dropdown_list_options.html',
            {'shops': shops}
        )


def load_brands(request):
    """Returns brands for specific category_id

    :param request: category_id
    :return: list of brands
    """
    id = request.GET.get('category_id')
    if id:
        from urllib.parse import unquote

        id = list(filter(None, [x.strip() for x in unquote(id).split(',')]))

        category_id = Category.objects.filter(id__in=id).values('id')

        product_id = ProductCategory.objects.filter(
            category__in=category_id
        ).values_list('product')

        product_brand = Product.objects.filter(
            id__in=product_id
        ).values_list('product_brand')

        brands = Brand.objects.filter(
            id__in=product_brand
        ).order_by('brand_name')

        return render(
            request,
            'admin/products/brand_dropdown_list_options.html',
            {'brands': brands}
        )
    else:
        brands = Brand.objects.none()
        return render(
            request,
            'admin/products/brand_dropdown_list_options.html',
            {'brands': brands}
        )


def sp_sr_productprice(request):
    """CSV to product prices for sp/sr

    :param request: Form
    :return: product prices for sp/sr
    """
    if request.method == 'POST':
        form = ProductPriceForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/products/productpriceupload.html',
                {'form': form}
            )

        if form.is_valid():
            file = form.cleaned_data.get('file')
            city = form.cleaned_data.get('city').id
            start_date = form.cleaned_data.get('start_date_time')
            end_date = form.cleaned_data.get('end_date_time')
            sp_sr = form.cleaned_data.get('sp_sr_choice').shop_type
            shops = form.cleaned_data.get('sp_sr_list')
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            try:
                for row in reader:
                    for shop in shops:
                        if sp_sr == "sp":
                            product_price = ProductPrice.objects.create(
                                product_id=row[0],
                                city_id=city,
                                mrp=row[4],
                                shop_id=shop.id,
                                price_to_retailer=row[7],
                                price_to_service_partner=row[5],
                                start_date=start_date,
                                end_date=end_date
                            )

                        elif sp_sr == "sr":
                            product_price = ProductPrice.objects.create(
                                product_id=row[0],
                                city_id=city,
                                mrp=row[4],
                                shop_id=shop.id,
                                price_to_super_retailer=row[6],
                                start_date=start_date,
                                end_date=end_date
                            )
                messages.success(request, 'Price uploaded successfully')

            except:
                messages.error(request, "Something went wrong!")
            return redirect('admin:sp_sr_productprice')

    else:
        form = ProductPriceForm(
            initial={'sp_sr_list': Shop.objects.none()}
        )
    return render(
        request,
        'admin/products/productpriceupload.html',
        {'form': form}
    )


def gf_product_price(request):
    """CSV to product prices for GramFactory

    :param request: Form
    :return: product prices for GramFactory
    """
    if request.method == 'POST':
        form = GFProductPriceForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/products/gfproductpriceupload.html',
                {'form': form}
            )

        if form.is_valid():
            file = form.cleaned_data.get('file')
            city = form.cleaned_data.get('city').id
            start_date = form.cleaned_data.get('start_date_time')
            end_date = form.cleaned_data.get('end_date_time')
            shops = form.cleaned_data.get('gf_list')
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            try:
                for row in reader:
                    for shop in shops:
                        product_price = ProductPrice.objects.create(
                            product_id=row[0],
                            city_id=city,
                            mrp=row[4],
                            shop_id=shop.id,
                            price_to_retailer=row[7],
                            price_to_service_partner=row[5],
                            price_to_super_retailer=row[6],
                            start_date=start_date,
                            end_date=end_date
                        )

                messages.success(request, 'Price uploaded successfully')

            except:
                messages.error("Something went wrong!")
            return redirect('admin:gf_productprice')

    else:
        form = GFProductPriceForm(
            initial={'gf_list': Shop.objects.none()}
        )
    return render(
        request,
        'admin/products/gfproductpriceupload.html',
        {'form': form}
    )


def products_filter_view(request):
    """Returns CSV includes products of specific category and brand

    :param request: Form
    :return: Products CSV for selected Category and Brands
    """
    if request.method == 'POST':
        form = ProductsFilterForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/products/productsfilter.html',
                {'filter_form': form}
            )
        if form.is_valid():
            dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
            filename = str(dt)+"product_list.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)
            writer.writerow([
                'id', 'product_name',
                'gf_code', 'product_hsn',
                'mrp', 'ptsp', 'ptsr', 'ptr', 'cash_discount', 'loyalty_incentive'
            ])
            brands = form.cleaned_data.get('brand')
            products = Product.objects.select_related(
                'product_hsn'
                ).filter(
                product_brand__in=brands
            )
            for product in products:
                writer.writerow([
                    product.id, product.product_name,
                    product.product_gf_code, product.product_hsn,
                    '', '', '', ''
                ])
            return response
    else:
        form = ProductsFilterForm()
    return render(
        request,
        'admin/products/productsfilter.html',
        {'filter_form': form}
    )


def products_price_filter_view(request):
    """Returns CSV includes product price of selected SP/SR/GF

    :param request: Form
    :return: Products CSV for selected Category and Brands
    """
    if request.method == 'POST':
        form = ProductsPriceFilterForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/products/productpricefilter.html',
                {'form': form}
            )
        if form.is_valid():
            city = form.cleaned_data.get('city').id
            sp_sr = form.cleaned_data.get('sp_sr_choice').shop_type
            shops = form.cleaned_data.get('sp_sr_list')
            dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
            filename = str(dt)+"product_price_list.csv"
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            writer = csv.writer(response)

            if sp_sr == "sp":
                writer.writerow([
                    'product_id', 'product_name', 'gf_code', 'product_hsn',
                    'mrp', 'ptsp', 'ptr', 'price_start_date',
                    'price_end_date', 'sp_name'
                ])
                for shop in shops:
                    products = ProductPrice.objects.select_related(
                        'product'
                    ).filter(
                        shop=shop,
                        status=True
                    ).order_by('product__product_name')
                    for product in products:
                        writer.writerow([
                            product.product_id, product.product.product_name,
                            product.product.product_gf_code,
                            product.product.product_hsn,
                            product.mrp, product.price_to_service_partner,
                            product.price_to_retailer, product.start_date,
                            product.end_date, product.shop.shop_name
                        ])

            if sp_sr == "sr":
                writer.writerow([
                    'product_id', 'product_name', 'gf_code', 'product_hsn',
                    'mrp', 'ptr', 'price_start_date', 'price_end_date',
                    'sr_name'
                ])
                for shop in shops:
                    products = ProductPrice.objects.select_related(
                        'product'
                    ).filter(
                        shop=shop,
                        status=True
                    ).order_by('product__product_name')
                    for product in products:
                        writer.writerow([
                            product.product_id,
                            product.product.product_name,
                            product.product.product_gf_code,
                            product.product.product_hsn,
                            product.mrp, product.price_to_retailer,
                            product.start_date, product.end_date,
                            product.shop.shop_name
                        ])
            if sp_sr == "gf":
                writer.writerow([
                    'product_id', 'product_name',  'gf_code', 'product_hsn',
                    'mrp', 'ptsp', 'ptsr', 'ptr', 'price_start_date',
                    'price_end_date', 'sr_name'
                ])
                for shop in shops:
                    products = ProductPrice.objects.select_related(
                        'product'
                    ).filter(
                        shop=shop,
                        status=True
                    ).order_by('product__product_name')
                    for product in products:
                        writer.writerow([
                            product.product_id,
                            product.product.product_name,
                            product.product.product_gf_code,
                            product.product.product_hsn,
                            product.mrp, product.price_to_service_partner,
                            product.price_to_super_retailer,
                            product.price_to_retailer, product.start_date,
                            product.end_date, product.shop.shop_name
                        ])
            return response

    else:
        form = ProductsPriceFilterForm()
    return render(
        request,
        'admin/products/productpricefilter.html',
        {'form': form}
    )


def products_csv_upload_view(request):
    """CSV to Product Price

    :param request: form
    :return: creates product prices
    """
    if request.method == 'POST':
        form = ProductsCSVUploadForm(request.POST, request.FILES)

        if form.errors:
            return render(
                request,
                'admin/products/productscsvupload.html',
                {'form': form}
            )

        if form.is_valid():
            file = form.cleaned_data['file']
            reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
            first_row = next(reader)
            for row in reader:
                try:
                    product_hsn_dt, _ = ProductHSN.objects.get_or_create(
                        product_hsn_code=row[16]
                    )
                except Exception as e:
                    logger.exception("Unable to create product HSN")
                    messages.error(request, "Unable to create product HSN")
                    return render(
                        request,
                        'admin/products/productscsvupload.html',
                        {'form': form}
                    )
                try:
                    brand = Brand.objects.get(pk=row[5])
                except Exception as e:
                    logger.exception("Brand Does not exist")
                    message.error(request, "Brand doesn't exist for  {}".format(row[1]))
                    return render(request, 'admin/products/productscsvupload.html',{'form': form})

                try:
                    product = Product.objects.get(product_gf_code=row[3])
                except:
                    product = Product.objects.create(product_gf_code=row[3], product_brand_id=row[5])
                else:
                    product.product_brand = brand
                finally:
                    product.product_name = row[0]
                    product.product_short_description = row[1]
                    product.product_long_description = row[2]
                    product.product_ean_code = row[4]
                    product.product_inner_case_size = row[14]
                    product.product_hsn = product_hsn_dt
                    product.product_case_size = row[15]
                try:
                    product.save()
                except Exception as e:
                    logger.exception("Unable to save product")
                    messages.error(
                        request,
                        "unable to save product details for {}".format(row[1]))
                    return render(
                        request,
                        'admin/products/productscsvupload.html',
                        {'form': form}
                    )

                for c in row[6].split(','):
                    if c is not '':
                        try:
                            product_category, _ = ProductCategory.objects.\
                                get_or_create(
                                            product=product,
                                            category_id=c.strip()
                                )
                        except Exception as e:
                            logger.exception(
                                "unable to get or create product "
                                "category for category {}".format(c)
                            )
                            messages.error(
                                request, "unable to create product category "
                                         "for {}, {}".format(row[1], c)
                            )
                            return render(
                                request,
                                'admin/products/productscsvupload.html',
                                {'form': form}
                            )
                try:
                    productoptions, _ = ProductOption.objects.get_or_create(
                        product=product
                    )
                    productoptions.size_id = row[8] if row[8] else None
                    productoptions.color_id = row[9] if row[9] else None
                    productoptions.fragrance_id = row[10] if row[10] else None
                    productoptions.flavor_id = row[11] if row[11] else None
                    productoptions.weight_id = row[12] if row[12] else None
                    productoptions.package_size_id = row[13] if row[13] else None
                    productoptions.save()
                except Exception as e:
                    logger.exception("Unable to create Product Options")
                    messages.error(
                        request,
                        "Unable to create Product options "
                        "for {}".format(row[1])
                    )
                    return render(
                        request,
                        'admin/products/productscsvupload.html',
                        {'form': form}
                    )
                for t in row[7].split(','):
                    if t is not '':
                        try:
                            product_tax, _ = ProductTaxMapping.objects\
                                .get_or_create(
                                                product=product,
                                                tax_id=t.strip()
                                )
                        except Exception as e:
                            logger.error(e)
                            messages.error(
                                request,
                                "Unable to create product tax"
                                " for {}--{}".format(row[1], t)
                            )
                            return render(
                                request,
                                'admin/products/productscsvupload.html',
                                {'form': form}
                            )
            messages.success(request, 'Products uploaded successfully')
            return redirect('admin:productscsvupload')
    else:
        form = ProductsCSVUploadForm()
    return render(
        request,
        'admin/products/productscsvupload.html',
        {'form': form}
    )


class MultiPhotoUploadView(View):
    """
    Bulk images upload with GFcode as photo name
    """
    def get(self, request):
        photos_list = ProductImage.objects.all()
        return render(
            self.request,
            'admin/products/multiphotoupload.html',
            {'photos': photos_list}
        )

    def post(self, request):
        form = ProductImageForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            file_name = (
                os.path.splitext(form.cleaned_data['image'].name)[0])
            try:
                product = Product.objects.get(product_gf_code=file_name)
            except:
                data = {
                    'is_valid': False,
                    'error': True,
                    'name': 'No Product found with GF code <b>' + file_name
                            + '</b>', 'url': '#'
                }

            else:
                form_instance = form.save(commit=False)
                form_instance.product = product
                form_instance.image_name = file_name
                form_instance.save()
                data = {
                    'is_valid': True,
                    'name': form_instance.image.name,
                    'url': form_instance.image.url
                }
        else:
            data = {'is_valid': False}
        return JsonResponse(data)


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
    writer.writerow(['id','product_name','product_gf_code', 'mrp', 'brand_to_gram_price','case_size'])
    products = Product.objects.values_list('id','product_name','product_gf_code','product_case_size')
    for product in products:
        writer.writerow([product[0],product[1],product[2],'','',product[3]])
    return response

def products_vendor_mapping(request,pk=None):
    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt)+"vendor_product_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    try:
        writer.writerow(['id','product_name','case_size','number_of_cases','mrp','brand_to_gram_price'])
        vendor_products = ProductVendorMapping.objects.filter(vendor_id=int(pk),case_size__gt=0,status=True)
        for p in vendor_products:
            writer.writerow([p.product_id,p.product.product_name,p.case_size,'',p.product_mrp,p.product_price])
    except:
        writer.writerow(["Make sure you have selected vendor before downloading CSV file"])
    return response

def ProductsUploadSample(request):
    filename = "products_upload_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['product_name','product_short_description','product_long_description','product_gf_code','product_ean_code','p_brand_id','p_cat_id','p_tax_id','p_size_id','p_color_id','p_fragrance_id','p_flavor_id','p_weight_id','p_package_size_id','p_inner_case_size','p_case_size','product_hsn_code'])
    writer.writerow(['fortune sunflowers oil','Fortune Sun Lite Refined Sunflower Oil is a healthy','Fortune Sun Lite Refined Sunflower Oil is a healthy, light and nutritious oil that is simple to digest. Rich in natural vitamins, it consists mostly of poly-unsaturated fatty acids (PUFA) and is low in soaked fats. It is strong and makes you feel light and active level after heavy food.','12BBPRG00000121','1234567890123','1','1','1','1','1','1','1','1','1','4','2','HSN Code'])
    return response

def NameIDCSV(request):
    filename = "name_id.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['BRAND NAME','BRAND ID','CATEGORY NAME','CATEGORY ID','TAX NAME','TAX ID','SIZE NAME','SIZE ID','COLOR NAME','COLOR ID','FRAGRANCE NAME','FRAGRANCE ID','FLAVOR NAME','FLAVOR ID','WEIGHT NAME','WEIGHT ID','PACKSIZE NAME','PACKSIZE ID'])
    return response
