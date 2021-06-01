import codecs
import csv
import re
import datetime
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers

from products.models import Product, ParentProductTaxMapping, ParentProduct, ParentProductCategory, ParentProductImage, \
    ProductHSN, ProductCapping, ProductVendorMapping, ProductImage, ProductPrice, ProductHSN, Tax, ProductSourceMapping
from categories.models import Category
from brand.models import Brand, Vendor
from shops.models import Shop
from products.common_validators import get_validate_parent_brand, get_validate_product_hsn, get_validate_parent_product, \
    get_validate_images, get_validate_category, get_validate_tax, is_ptr_applicable_validation, get_validate_product, \
    get_validate_seller_shop, check_active_capping, validate_tax_type, get_validate_vendor
from products.common_function import ParentProductCls, ProductCls
from accounts.models import User


class BrandSerializers(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'brand_name', 'brand_code')


class VendorSerializers(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name')


class ProductHSNSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductHSN
        fields = ('id', 'product_hsn_code')


class CategorySerializers(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('category_name', )


class ParentProductCategorySerializers(serializers.ModelSerializer):
    category = CategorySerializers(read_only=True)

    class Meta:
        model = ParentProductCategory
        fields = ('id', 'category',)


class ParentProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ParentProductImage
        fields = ('id', 'image_name', 'image',)


class ProductImageSerializers(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None, use_url=True,
    )

    class Meta:
        model = ProductImage
        fields = ('id', 'image_name', 'image',)


class TaxSerializers(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = ('tax_name', 'tax_type', 'tax_percentage')


class ProductSourceMappingSerializers(serializers.ModelSerializer):
    class Meta:
        model = ProductSourceMapping
        fields = ('source_sku', 'status')


class ParentProductTaxMappingSerializers(serializers.ModelSerializer):
    tax = TaxSerializers(read_only=True)

    class Meta:
        model = ParentProductTaxMapping
        fields = ('id', 'tax')


class ProductSerializers(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'product_sku', 'status',)


class UserSerializers(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'first_name', 'phone_number',)


class ParentProductSerializers(serializers.ModelSerializer):
    """Handles creating, reading and updating parent product items."""
    parent_brand = BrandSerializers(read_only=True)
    updated_by = UserSerializers(read_only=True)
    product_hsn = ProductHSNSerializers(read_only=True)
    parent_product_pro_image = ParentProductImageSerializers(many=True)
    parent_product_pro_category = ParentProductCategorySerializers(many=True)
    parent_product_pro_tax = ParentProductTaxMappingSerializers(many=True)
    parent_id = serializers.CharField(read_only=True)
    product_parent_product = ProductSerializers(many=True, required=False)

    def validate(self, data):
        """
            is_ptr_applicable validation.
        """
        if not 'parent_brand' in self.initial_data or not self.initial_data['parent_brand']:
            raise serializers.ValidationError(_('parent_brand is required'))

        if not 'product_hsn' in self.initial_data or not self.initial_data['product_hsn']:
            raise serializers.ValidationError(_('product_hsn is required'))

        if len(self.initial_data.getlist('parent_product_pro_image')) == 0:
            raise serializers.ValidationError(_('parent_product_image is required'))

        if len(self.initial_data.getlist('parent_product_pro_category')) == 0:
            raise serializers.ValidationError(_('parent_product_category is required'))

        if len(self.initial_data.getlist('parent_product_pro_tax')) == 0:
            raise serializers.ValidationError(_('parent_product_pro_tax is required'))

        if data.get('is_ptr_applicable'):
            is_ptr_applicable = is_ptr_applicable_validation(data)
            if 'error' in is_ptr_applicable:
                raise serializers.ValidationError(is_ptr_applicable['error'])

        parent_brand_val = get_validate_parent_brand(self.initial_data['parent_brand'])
        if 'error' in parent_brand_val:
            raise serializers.ValidationError(parent_brand_val['error'])

        product_hsn_val = get_validate_product_hsn(self.initial_data['product_hsn'])
        if 'error' in product_hsn_val:
            raise serializers.ValidationError(_(f'{product_hsn_val["error"]}'))

        image_val = get_validate_images(self.initial_data.getlist('parent_product_pro_image'))
        if 'error' in image_val:
            raise serializers.ValidationError(_(image_val["error"]))

        category_val = get_validate_category(self.initial_data['parent_product_pro_category'])
        if 'error' in category_val:
            raise serializers.ValidationError(_(category_val["error"]))

        tax_val = get_validate_tax(self.initial_data['parent_product_pro_tax'])
        if 'error' in tax_val:
            raise serializers.ValidationError(_(tax_val["error"]))

        return data

    class Meta:
        model = ParentProduct
        fields = ('id', 'parent_id', 'name', 'inner_case_size', 'product_type', 'is_ptr_applicable',
                  'ptr_percent', 'ptr_type', 'status', 'product_hsn', 'parent_brand', 'parent_product_pro_image',
                  'parent_product_pro_category', 'parent_product_pro_tax', 'product_parent_product', 'updated_by')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        data = {
                "basic":
                    {
                        "id" : representation['id'],
                        "parent_id": representation['parent_id'],
                        "name": representation['name'],
                        "parent_id": representation['parent_id'],
                        "status": representation['status'],
                        "product_type": representation['product_type'],
                        "parent_product_pro_tax": representation['parent_product_pro_tax'],
                        "parent_product_pro_category": representation['parent_product_pro_category'],
                        "parent_brand": representation['parent_brand'],
                    },
                "additional":
                    {
                        "is_ptr_applicable": representation['is_ptr_applicable'],
                        "ptr_percent": representation['ptr_percent'],
                        "ptr_type": representation['ptr_type'],
                        "parent_product_pro_image": representation['parent_product_pro_image'],
                        "product_hsn": representation['product_hsn'],
                    },
                "detail_page_1":
                    {
                        "name": representation['name'],
                        "parent_brand": representation['parent_brand'],
                        "product_hsn": representation['product_hsn'],
                        "inner_case_size": representation['inner_case_size'],
                        "product_type": representation['product_type'],
                        "is_ptr_applicable": representation['is_ptr_applicable'],
                        "ptr_percent": representation['ptr_percent'],
                        "ptr_type": representation['ptr_type'],
                        "parent_product_pro_category": representation['parent_product_pro_category'],
                        "parent_product_pro_tax": representation['parent_product_pro_tax'],
                        "parent_product_pro_image": representation['parent_product_pro_image'],
                    },
                "detail_page_2":
                    {
                        "product_parent_product": representation['product_parent_product'],
                    },
                "detail_page_log":
                    {
                        "updated_by": representation['updated_by']
                    }
                }
        return data


    @transaction.atomic
    def create(self, validated_data):
        """create a new Parent Product with image category & tax"""

        validated_data.pop('parent_product_pro_image')
        validated_data.pop('parent_product_pro_category')
        validated_data.pop('parent_product_pro_tax')
        validated_data.pop('product_parent_product', None)

        try:
            parent_product = ParentProductCls.create_parent_product(self.initial_data['parent_brand'],
                                                                    self.initial_data['product_hsn'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)

        return parent_product

    @transaction.atomic
    def update(self, instance, validated_data):
        """ This method is used to update an instance of the Parent Product's attribute. """

        validated_data.pop('parent_product_pro_image', None)
        validated_data.pop('parent_product_pro_category', None)
        validated_data.pop('parent_product_pro_tax', None)
        validated_data.pop('product_parent_product', None)

        try:
            # call super to save modified instance along with the validated data
            parent_product_obj = super().update(instance, validated_data)
            parent_product = ParentProductCls.update_parent_product(self.initial_data['parent_brand'],
                                                                    self.initial_data['product_hsn'],
                                                                    parent_product_obj)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        self.create_parent_tax_image_cat(parent_product)

        return parent_product

    # crete parent product image, tax & category
    def create_parent_tax_image_cat(self, parent_product):
        ParentProductCls.upload_parent_product_images(parent_product,
                                                      self.initial_data.getlist('parent_product_pro_image'))
        ParentProductCls.create_parent_product_category(parent_product,
                                                        self.initial_data['parent_product_pro_category'])
        ParentProductCls.create_parent_product_tax(parent_product, self.initial_data['parent_product_pro_tax'])


class ParentProductBulkUploadSerializers(serializers.ModelSerializer):
    file = serializers.FileField(label='Upload Parent Product list')

    class Meta:
        model = ParentProduct
        fields = ('file',)

    def validate(self, data):
        if not data['file'].name[-4:] in '.csv':
            raise serializers.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(data['file'], 'utf-8', errors='ignore'))
        next(reader)
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                        row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                    continue
            if not row[0]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Parent Name' can not be empty."))
            elif not re.match("^[ \w\$\_\,\%\@\.\/\#\&\+\-\(\)\*\!\:]*$", row[0]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | {VALIDATION_ERROR_MESSAGES['INVALID_PRODUCT_NAME']}."))
            if not row[1]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand' can not be empty."))
            elif not Brand.objects.filter(brand_name=row[1].strip()).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand' doesn't exist in the system."))
            if not row[2]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Category' can not be empty."))
            else:
                if not Category.objects.filter(category_name=row[2].strip()).exists():
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        if not Category.objects.filter(category_name=cat).exists():
                            raise serializers.ValidationError(
                                _(f"Row {row_id + 2} | 'Category' {cat.strip()} doesn't exist in the system."))
            if not row[3]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'HSN' can not be empty."))
            elif not ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).exists():
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'HSN' doesn't exist in the system."))
            if not row[4]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'GST' can not be empty."))
            elif not re.match("^([0]|[5]|[1][2]|[1][8]|[2][8])(\s+)?(%)?$", row[4]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'GST' can only be 0, 5, 12, 18, 28."))
            if row[5] and not re.match("^([0]|[1][2])(\s+)?%?$", row[5]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'CESS' can only be 0, 12."))
            if row[6] and not re.match("^[0-9]\d*(\.\d{1,2})?(\s+)?%?$", row[6]):
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Surcharge' can only be a numeric value."))
            if not row[7]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Brand Case Size' can not be empty."))
            elif not re.match("^\d+$", row[7]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | 'Brand Case Size' can only be a numeric value."))
            if not row[8]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Inner Case Size' can not be empty."))
            elif not re.match("^\d+$", row[8]):
                raise serializers.ValidationError(
                    _(f"Row {row_id + 2} | 'Inner Case Size' can only be a numeric value."))
            if not row[9]:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can not be empty."))
            elif row[9].lower() not in ['b2b', 'b2c', 'both', 'both b2b and b2c']:
                raise serializers.ValidationError(_(f"Row {row_id + 2} | 'Product Type' can only be 'B2B', 'B2C', "
                                                    f"'Both B2B and B2C'."))

        return data

    def create(self, validated_data):
        reader = csv.reader(codecs.iterdecode(validated_data['file'], 'utf-8', errors='ignore'))
        next(reader)
        parent_product_list = []
        try:
            for row in reader:
                if len(row) == 0:
                    continue
                if '' in row:
                    if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                            row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == ''):
                        continue
                parent_product = ParentProduct.objects.create(
                    name=row[0].strip(),
                    parent_brand=Brand.objects.filter(brand_name=row[1].strip()).last(),
                    product_hsn=ProductHSN.objects.filter(product_hsn_code=row[3].replace("'", '')).last(),
                    brand_case_size=int(row[7]),
                    inner_case_size=int(row[8]),
                    product_type=row[9]
                )
                parent_product.save()

                parent_gst = int(row[4])
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='gst', tax_percentage=parent_gst).last()
                ).save()

                parent_cess = int(row[5]) if row[5] else 0
                ParentProductTaxMapping.objects.create(
                    parent_product=parent_product,
                    tax=Tax.objects.filter(tax_type='cess', tax_percentage=parent_cess).last()
                ).save()

                parent_surcharge = float(row[6]) if row[6] else 0
                if Tax.objects.filter(
                        tax_type='surcharge',
                        tax_percentage=parent_surcharge
                ).exists():
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=Tax.objects.filter(tax_type='surcharge', tax_percentage=parent_surcharge).last()
                    ).save()
                else:
                    new_surcharge_tax = Tax.objects.create(
                        tax_name='Surcharge - {}'.format(parent_surcharge),
                        tax_type='surcharge',
                        tax_percentage=parent_surcharge,
                        tax_start_at=datetime.datetime.now()
                    )
                    new_surcharge_tax.save()
                    ParentProductTaxMapping.objects.create(
                        parent_product=parent_product,
                        tax=new_surcharge_tax
                    ).save()
                if Category.objects.filter(category_name=row[2].strip()).exists():
                    parent_product_category = ParentProductCategory.objects.create(
                        parent_product=parent_product,
                        category=Category.objects.filter(category_name=row[2].strip()).last()
                    )
                    parent_product_category.save()
                else:
                    categories = row[2].split(',')
                    for cat in categories:
                        cat = cat.strip().replace("'", '')
                        parent_product_category = ParentProductCategory.objects.create(
                            parent_product=parent_product,
                            category=Category.objects.filter(category_name=cat).last()
                        )
                        parent_product_category.save()
                parent_product_list.append(parent_product)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return parent_product_list


class ParentProductExportAsCSVSerializers(serializers.ModelSerializer):
    parent_product_id_list = serializers.ListField(
        child=serializers.IntegerField()
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list',)

    def validate(self, data):

        if len(data.get('parent_product_id_list')) == 0:
            raise serializers.ValidationError(_('Atleast one parent_product id must be selected '))

        for id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {id}')

        return data

    def product_gst(self, obj):
        product_gst = validate_tax_type(obj, 'gst')
        return product_gst

    def product_cess(self, obj):
        product_cess = validate_tax_type(obj, 'cess')
        return product_cess

    def product_surcharge(self, obj):
        product_surcharge = validate_tax_type(obj, 'surcharge')
        return product_surcharge

    def product_category(self, obj):
        try:
            if obj.parent_product_pro_category.exists():
                cats = [str(c.category) for c in obj.parent_product_pro_category.filter(status=True)]
                return "\n".join(cats)
            return ''
        except:
            return ''

    def product_image(self, obj):
        if obj.parent_product_pro_image.exists():
            return "{}".format(obj.parent_product_pro_image.last().image.url)
        else:
            return '-'

    def create(self, validated_data):
        meta = ParentProduct._meta
        field_names = [
            'parent_id', 'name', 'parent_brand', 'product_category', 'product_hsn',
            'product_gst', 'product_cess', 'product_surcharge', 'product_image', 'status',
            'product_type', 'is_ptr_applicable', 'ptr_type', 'ptr_percent'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)

        writer = csv.writer(response)
        writer.writerow(field_names)
        for id in validated_data['parent_product_id_list']:
            obj = ParentProduct.objects.filter(id=id).last()
            row = []
            for field in field_names:
                try:
                    val = getattr(obj, field)
                    if field == 'ptr_type':
                        val = getattr(obj, 'ptr_type_text')
                except:
                    val = eval("self.{}(obj)".format(field))
                finally:
                    row.append(val)
            writer.writerow(row)
        return response


class ActiveDeactivateSelectedProductSerializers(serializers.ModelSerializer):
    is_active = serializers.BooleanField()
    parent_product_id_list = serializers.ListField(
        child=serializers.IntegerField()
    )

    class Meta:
        model = ParentProduct
        fields = ('parent_product_id_list', 'is_active',)

    def validate(self, data):

        if data.get('is_active') is None:
            raise serializers.ValidationError('This field is required')

        if len(data.get('parent_product_id_list')) == 0:
            raise serializers.ValidationError(_('atleast one parent_product id must be selected '))

        for id in data.get('parent_product_id_list'):
            try:
                ParentProduct.objects.get(id=id)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(f'parent_product not found for id {id}')

        return data

    def update(self, instance, validated_data):

        if validated_data['is_active']:
            parent_product_status = True
            product_status = "active"
        else:
            parent_product_status = False
            product_status = "deactivated"

        try:
            parent_products = ParentProduct.objects.filter(id__in=validated_data['parent_product_id_list'])
            parent_products.update(status=parent_product_status)
            for parent_product_obj in parent_products:
                Product.objects.filter(parent_product=parent_product_obj).update(status=product_status)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return validated_data


class ShopSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'shop_name',)


class ProductCappingSerializers(serializers.ModelSerializer):
    product = ProductSerializers(read_only=True)
    seller_shop = ShopSerializers(read_only=True)

    class Meta:
        model = ProductCapping
        fields = ('id', 'product', 'seller_shop', 'capping_type', 'capping_qty', 'start_date', 'end_date', 'status')

    def validate(self, data):

        if self.initial_data['product'] is None:
            raise serializers.ValidationError('product is required')

        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])

        if self.initial_data['seller_shop'] is None:
            raise serializers.ValidationError('seller_shop is required')

        seller_shop_val = get_validate_seller_shop(self.initial_data['seller_shop'])
        if 'error' in seller_shop_val:
            raise serializers.ValidationError(seller_shop_val['error'])

        """ check capping is active for the selected sku and warehouse """
        active_capping = check_active_capping(self.initial_data['seller_shop'], self.initial_data['product'])
        if 'error' in active_capping:
            raise serializers.ValidationError(active_capping['error'])

        # check capping quantity is zero or not
        if data.get('capping_qty') == 0:
            raise serializers.ValidationError("Capping qty should be greater than 0.")

        self.capping_duration_check(data)

        return data

    def capping_duration_check(self, data):
        """ Capping Duration check according to capping type """

        # if capping type is Daily, & check this condition for Weekly & Monthly as Well
        day_difference = data.get('end_date').date() - data.get('start_date').date()
        if day_difference.days == 0:
            raise serializers.ValidationError("Please enter valid Start Date and End Date.")

        # if capping type is Weekly
        if data.get('capping_type') == 1:
            if not day_difference.days % 7 == 0:
                raise serializers.ValidationError("Please enter valid Start Date and End Date.")

        # if capping type is Monthly
        elif data.get('capping_type') == 2:
            if not day_difference.days % 30 == 0:
                raise serializers.ValidationError("Please enter valid Start Date and End Date.")

    @transaction.atomic
    def create(self, validated_data):
        """ create product capping """
        try:
            product_capping = ProductCls.create_product_capping(self.initial_data['product'],
                                                                self.initial_data['seller_shop'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_capping

    @transaction.atomic
    def update(self, instance, validated_data):
        """update a Product Capping """
        try:
            product_capping = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_capping


class ProductVendorMappingSerializers(serializers.ModelSerializer):
    product = ProductSerializers(read_only=True)
    vendor = VendorSerializers(read_only=True)

    def validate(self, data):
        if data.get('product_price') is None and data.get('product_price_pack') is None:
            raise serializers.ValidationError("please enter one Brand to Gram Price")

        if data.get('case_size') is None:
            raise serializers.ValidationError("please enter case_size")

        if self.initial_data['vendor'] is None:
            raise serializers.ValidationError("please select vendor")

        if self.initial_data['product'] is None:
            raise serializers.ValidationError("please select product")

        if not (data.get('product_price') is None or data.get('product_price_pack') is None):
            raise serializers.ValidationError("please enter only one Brand to Gram Price")

        product_val = get_validate_product(self.initial_data['product'])
        if 'error' in product_val:
            raise serializers.ValidationError(product_val['error'])

        vendor_val = get_validate_vendor(self.initial_data['vendor'])
        if 'error' in vendor_val:
            raise serializers.ValidationError(vendor_val['error'])

        return data

    class Meta:
        model = ProductVendorMapping
        fields = ('id', 'product_price', 'product_price_pack', 'product_mrp', 'case_size', 'status', 'vendor',
                  'product')

    @transaction.atomic
    def create(self, validated_data):
        """ create vendor product mapping """
        try:
            product_vendor_map = ProductCls.create_product_vendor_mapping(self.initial_data['product'],
                                                                          self.initial_data['vendor'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_vendor_map

    @transaction.atomic
    def update(self, instance, validated_data):
        """update vendor product mapping """
        try:
            # call super to save modified instance along with the validated data
            product_vendor_map_obj = super().update(instance, validated_data)
            product_vendor_map = ProductCls.update_product_vendor_mapping(self.initial_data['product'],
                                                                          self.initial_data['vendor'],
                                                                          product_vendor_map_obj)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return product_vendor_map


class ChildProductSerializers(serializers.ModelSerializer):
    """ Handles creating, reading and updating child product items."""
    parent_product = ParentProductSerializers(read_only=True)
    product_vendor_mapping = ProductVendorMappingSerializers(many=True)
    product_sku = serializers.CharField(required=False)
    product_pro_image = ProductImageSerializers(many=True)

    class Meta:
        model = Product
        fields = ('id', 'product_sku', 'product_name', 'product_ean_code', 'status', 'product_mrp',
                  'weight_value', 'weight_unit', 'reason_for_child_sku', 'use_parent_image', 'repackaging_type',
                  'product_pro_image', 'parent_product', 'product_vendor_mapping')

    def validate(self, data):
        if not 'parent_product' in self.initial_data or self.initial_data['parent_product'] is None:
            raise serializers.ValidationError('parent_product is required')

        parent_product_val = get_validate_parent_product(self.initial_data['parent_product'])
        if 'error' in parent_product_val:
            raise serializers.ValidationError(parent_product_val['error'])

        if self.initial_data['use_parent_image']:
            if parent_product_val['parent_product'] and not parent_product_val['parent_product']. \
                    parent_product_pro_image.exists():
                raise serializers.ValidationError(
                    _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))
        elif len(self.initial_data.getlist('product_pro_image')) == 0:
            if parent_product_val['parent_product'] and parent_product_val['parent_product'].parent_product_pro_image. \
                    exists():
                data['use_parent_image'] = True
            else:
                raise serializers.ValidationError(
                    _(f"Parent Product Image Not Available. Please Upload Child Product Image(s)."))

        if len(self.initial_data.getlist('product_pro_image')) > 0:
            image_val = get_validate_images(self.initial_data.getlist('product_pro_image'))
            if 'error' in image_val:
                raise serializers.ValidationError(_(image_val["error"]))

        if 'status' in self.initial_data and self.initial_data['status'] == 'active':
            error = True
            if 'id' in self.initial_data and ProductPrice.objects.filter(approval_status=ProductPrice.APPROVED,
                                                                         product_id=self.initial_data['id']).exists():
                error = False
            if error:
                raise serializers.ValidationError("Product cannot be made active until an active Product Price exists")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """create a new Child Product with image category & tax"""
        validated_data.pop('product_pro_image', None)
        try:
            child_product = ProductCls.create_child_product(self.initial_data['parent_product'], **validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)
        if len(self.initial_data.getlist('product_pro_image')) > 0:
            ProductCls.upload_child_product_images(child_product, self.initial_data.getlist('child_product_pro_image'))

        return child_product

    @transaction.atomic
    def update(self, instance, validated_data):
        """
            This method is used to update an instance of the Child Product's attribute.
        """
        validated_data.pop('product_pro_image', None)
        try:
            # call super to save modified instance along with the validated data
            child_product_obj = super().update(instance, validated_data)
            child_product = ProductCls.update_child_product(self.initial_data['parent_product'],
                                                            child_product_obj)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        if len(self.initial_data.getlist('product_pro_image')) > 0:
            ProductCls.upload_child_product_images(child_product, self.initial_data.getlist('product_pro_image'))

        return child_product


def only_int(value):
    if value.isdigit() is False:
        raise serializers.ValidationError('HSN can only be a numeric value.')


class ProductHSNSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """
    product_hsn_code = serializers.CharField(max_length=8, min_length=6, validators=[only_int])

    class Meta:
        model = ProductHSN
        fields = ['id', 'product_hsn_code', ]


class TaxSerializers(serializers.ModelSerializer):
    """ Handles Get & creating """

    class Meta:
        model = Tax
