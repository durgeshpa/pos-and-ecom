import csv
import codecs
import datetime
import os
import logging
import re
import openpyxl

from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required

from decimal import Decimal

from shops.models import Shop, ShopType
from addresses.models import City, State, Address, Pincode
from categories.models import Category
from brand.models import Brand
from .forms import (
    GFProductPriceForm, ProductPriceForm, ProductsFilterForm,
    ProductsPriceFilterForm, ProductsCSVUploadForm, ProductImageForm,
    ProductCategoryMappingForm, NewProductPriceUpload
    )
from products.models import (
    Product, ProductCategory, ProductOption,
    ProductTaxMapping, ProductVendorMapping,
    ProductImage, ProductHSN, ProductPrice
    )

logger = logging.getLogger(__name__)
from dal import autocomplete
from django.db.models import Q
from .utils import products_price_excel


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


class SpSrProductPrice(View):

    def validate_row(self, first_row, row):
        if not re.match("^\d{0,8}(\.\d{1,4})?$", row[4]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[4], first_row[4]))
        if not re.match("^\d{0,8}(\.\d{1,4})?$", row[5]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[5], first_row[5]))
        if not re.match("^\d{0,8}(\.\d{1,4})?$", row[6]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[6], first_row[6]))
        if not re.match("^\d{0,8}(\.\d{1,4})?$", row[7]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[7], first_row[7]))
        if row[8] and not re.match("^\d{0,8}(\.\d{1,4})?$", row[8]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[8], first_row[8]))
        if row[9] and not re.match("^\d{0,8}(\.\d{1,4})?$", row[9]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[9], first_row[9]))
        if (row[0] and not re.match("^[\d]*$", row[0])) or not row[0]:
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[0], first_row[0]))

    def create_product_price(self, request, file, shops, city, start_date,
                             end_date, sp_sr):
        try:
            with transaction.atomic():
                reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
                first_row = next(reader)
                for row_id, row in enumerate(reader):

                    if (row[4] and row[5] and row[6] and row[7]):
                        self.validate_row(first_row, row)
                        for shop in shops:
                            ProductPrice.objects.create(
                                product_id=row[0], city_id=city,
                                mrp=float(row[4]), shop_id=shop.id,
                                price_to_retailer=float(row[7]),
                                price_to_service_partner=float(row[5]),
                                price_to_super_retailer=float(row[6]),
                                cash_discount=float(row[8]) if row[8] else 0,
                                loyalty_incentive=float(row[9]) if row[9] else 0,
                                start_date=start_date, end_date=end_date,
                                approval_status=ProductPrice.APPROVAL_PENDING)

                    elif (row[4] or row[5] or row[6] or row[7]):
                        raise Exception("Please enter all the prices")
                    else:
                        continue

                messages.success(request, 'Price uploaded successfully')

        except Exception as e:
            messages.error(request, "{} at Row[{}] for {}"
                                    "".format(e, row_id + 2, row[1]))

    def get(self, request):
        form = ProductPriceForm(initial={'sp_sr_list': Shop.objects.none()})
        return render(request, 'admin/products/productpriceupload.html',
                      {'form': form})

    def post(self, request):
        form = ProductPriceForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.cleaned_data.get('file')
            city = form.cleaned_data.get('city').id
            start_date = form.cleaned_data.get('start_date_time')
            end_date = form.cleaned_data.get('end_date_time')
            sp_sr = form.cleaned_data.get('sp_sr_choice').shop_type
            shops = form.cleaned_data.get('sp_sr_list')

            self.create_product_price(request, file, shops, city,
                                      start_date, end_date, sp_sr)

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
                            cash_discount=row[8],
                            loyalty_incentive=row[9],
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
                    'mrp', 'ptsp', 'ptr', 'cash_discount', 'loyalty_incentive', 'price_start_date',
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
                            product.price_to_retailer, product.cash_discount,
                            product.loyalty_incentive, product.start_date,
                            product.end_date, product.shop.shop_name
                        ])

            if sp_sr == "sr":
                writer.writerow([
                    'product_id', 'product_name', 'gf_code', 'product_hsn',
                    'mrp', 'ptr', 'cash_discount', 'loyalty_incentive', 'price_start_date', 'price_end_date',
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
                            product.cash_discount, product.loyalty_incentive,
                            product.start_date, product.end_date,
                            product.shop.shop_name
                        ])
            if sp_sr == "gf":
                writer.writerow([
                    'product_id', 'product_name',  'gf_code', 'product_hsn',
                    'mrp', 'ptsp', 'ptsr', 'ptr', 'cash_discount', 'loyalty_incentive', 'price_start_date',
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
                            product.price_to_retailer, product.cash_discount,
                            product.loyalty_incentive, product.start_date,
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
    writer.writerow(['id','product_name','product_gf_code','product_sku', 'mrp', 'brand_to_gram_price','case_size'])
    products = Product.objects.values_list('id','product_name','product_gf_code','product_sku','product_case_size')
    for product in products:
        writer.writerow([product[0],product[1],product[2],product[3],'','',product[4]])
    return response

def products_vendor_mapping(request,pk=None):
    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt)+"vendor_product_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    try:
        writer.writerow(['id','product_name','sku','case_size','number_of_cases','mrp','brand_to_gram_price'])
        vendor_products = ProductVendorMapping.objects.filter(vendor_id=int(pk),case_size__gt=0,status=True)
        for p in vendor_products:
            writer.writerow([p.product_id,p.product.product_name,p.product.product_sku,p.case_size,'',p.product_mrp,p.product_price])
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


class ProductPriceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = Product.objects.none()
        if self.q:
            qs = Product.objects.filter(
                Q(product_name__icontains=self.q) |
                Q(product_sku__iexact=self.q)
            )
        return qs

class ProductCategoryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self, *args, **kwargs):
        qs = None
        if self.q:
            qs = Category.objects.filter(category_name__icontains=self.q),
            #qs = Product.objects.filter(product_name__icontains=self.q)
        return qs


def download_all_products(request):
    """Returns CSV includes products

    :param request: Form
    :return: Products CSV
    """
    products_list = Product.objects.values(
        'id', 'product_name', 'product_gf_code', 'product_hsn').all()

    dt = datetime.datetime.now().strftime("%d_%b_%y_%I_%M")
    filename = str(dt) + "all_products_list.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow([
        'id', 'product_name',
        'gf_code', 'product_hsn',
        'mrp', 'ptsp', 'ptsr', 'ptr', 'cash_discount', 'loyalty_incentive'
    ])
    writer.writerows([[i['id'], i['product_name'], i['product_gf_code'],
                      i['product_hsn'], '', '', '', '']
                      for i in products_list])
    return response


class ProductCategoryMapping(View):

    def validate_row(self, first_row, row):
        if not row[0]:
            raise Exception("{} is requied".format(first_row[0]))
        if not row[1]:
            raise Exception("{} is requied".format(first_row[1]))

    def update_mapping(self, request, file):
        try:
            with transaction.atomic():
                reader = csv.reader(codecs.iterdecode(file, 'utf-8'))
                first_row = next(reader)
                for row_id, row in enumerate(reader):
                    self.validate_row(first_row, row)
                    ProductCategory.objects.filter(
                        product=Product.objects.get(product_gf_code=row[0])
                    ).update(category=Category.objects.get(id=row[1]))

                messages.success(request, 'Category Mapping updated successfully')

        except Exception as e:
            messages.error(request, "{} at Row[{}]".format(e, row_id + 2))

    @method_decorator(permission_required('products.change_product'))
    def get(self, request):
        form = ProductCategoryMappingForm()
        return render(request, 'admin/products/productcategorymapping.html',
                      {'form': form})

    @method_decorator(permission_required('products.change_product'))
    def post(self, request):
        form = ProductCategoryMappingForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data.get('file')
            self.update_mapping(request, file)

        return render(request, 'admin/products/productcategorymapping.html',
                      {'form': form})


def product_category_mapping_sample(self):
    filename = "product_category_mapping_sample.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerows([['gf_code', 'category_id'], ['GF01641', '161']])
    return response


class CityAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        buyer_shop = self.forwarded.get('buyer_shop', None)
        qs = City.objects.all()
        if buyer_shop:
            qs = qs.filter(city_address__shop_name_id=buyer_shop,
                           city_address__address_type='shipping')
            return qs
        if self.q:
            qs = qs.filter(city_name__icontains=self.q)
        return qs


class RetailerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Shop.objects.filter(shop_type__shop_type='r')
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class SellerShopAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Shop.objects.filter(shop_type__shop_type='sp')
        if self.q:
            qs = qs.filter(shop_name__icontains=self.q)
        return qs


class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Product.objects.all()
        if self.q:
            qs = qs.filter(Q(product_name=self.q) |
                           Q(product_gf_code=self.q) |
                           Q(product_sku=self.q))
        return qs


class PincodeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        city = self.forwarded.get('city', None)
        buyer_shop = self.forwarded.get('buyer_shop', None)
        qs = Pincode.objects.all()
        if buyer_shop:
            qs = qs.filter(pincode_address__shop_name_id=buyer_shop,
                           pincode_address__address_type='shipping')
            return qs
        if city:
            qs = qs.filter(city_id=city)
        return qs


class ProductPriceUpload(View):
    form_class = NewProductPriceUpload
    template_name = 'admin/products/NewProductPriceUpload.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def products_price_qs(self, data):
        qs = ProductPrice.objects.filter(seller_shop=data['seller_shop'])
        if data['city']:
            qs = qs.filter(city=data['city'])
        if data['pincode_from'] and data['pincode_to']:
            pincode_range = [i for i in range(int(data['pincode_from']),
                             int(data['pincode_to']))]
            qs = qs.filter(pincode__in=pincode_range)
        if data['buyer_shop']:
            qs = qs.filter(buyer_shop=data['buyer_shop'])
        if data['product']:
            qs = qs.filter(product=data['product'])
        return qs.values_list(
            'product_id', 'product__product_name', 'product__product_gf_code',
            'seller_shop__shop_name', 'mrp', 'selling_price',
            'city_id', 'city__city_name', 'pincode', 'buyer_shop_id',
            'buyer_shop__shop_name', 'start_date', 'end_date',
            'approval_status')

    def validate_row(self, first_row, row):
        if (row[0] and not re.match("^[\d]*$", str(row[0]))) or not row[0]:
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[0], first_row[0]))
        if ((row[4] and not re.match("^\d{0,8}(\.\d{1,2})?$", str(row[4]))) or
                not row[4]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[4], first_row[4]))
        if ((row[5] and not re.match("^\d{0,8}(\.\d{1,2})?$", str(row[5]))) or
                not row[5]):
            raise Exception("{} - Please enter a valid {}"
                            "".format(row[5], first_row[5]))

    def create_product_price(self, request, data):
        try:
            with transaction.atomic():
                wb_obj = openpyxl.load_workbook(data.get('csv_file'))
                sheet_obj = wb_obj.active
                first_row = next(sheet_obj.iter_rows(values_only=True))
                for row_id, row in enumerate(sheet_obj.iter_rows(
                    min_row=2, max_row=None, min_col=None, max_col=None,
                    values_only=True
                )):
                    self.validate_row(first_row, row)
                    ProductPrice.objects.create(
                        product_id=int(row[0]), mrp=Decimal(row[4]),
                        selling_price=Decimal(row[5]),
                        seller_shop_id=int(data['seller_shop'].id),
                        buyer_shop_id=int(row[9]) if row[9] else None,
                        city_id=int(row[6]) if row[6] else None,
                        pincode=row[8] if row[8] else None,
                        start_date=row[11], end_date=row[12],
                        approval_status=ProductPrice.APPROVAL_PENDING)

                messages.success(request, 'Prices uploaded successfully')

        except Exception as e:
            messages.error(request, "{} at Row[{}] for {}"
                                    "".format(e, row_id + 2, row[1]))

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            # if action is upload
            if data['action'] == '1':
                self.create_product_price(request, data)
            # if action is download
            elif data['action'] == '2':
                return products_price_excel(self.products_price_qs(data))

        return render(request, self.template_name, {'form': form})
