from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

import codecs
import re
import decimal
from dal import autocomplete
from django import forms
import csv
from tempus_dominus.widgets import DateTimePicker

from pos.models import RetailerProduct, RetailerProductImage, DiscountedRetailerProduct, MeasurementCategory, \
    MeasurementUnit
from products.models import Product
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState


class RetailerProductsForm(forms.ModelForm):
    linked_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(
            url='admin:product-price-autocomplete', ),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['measurement_category'].required = False

    def clean(self):
        data = self.cleaned_data
        if data["product_pack_type"] == 'loose' and not data["measurement_category"]:
            raise ValidationError(_('Measurement Category is required'))
        return data


class DiscountedRetailerProductsForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['f']),
        widget=autocomplete.ModelSelect2(
            url='retailer-product-autocomplete'
        )
    )
    product_ref = forms.ModelChoiceField(
        queryset=RetailerProduct.objects.filter(~Q(sku_type=4)),
        widget=autocomplete.ModelSelect2(
            url='discounted-product-autocomplete',
            forward=('shop',),
            attrs={"onChange": 'getProductDetails()'},
        )
    )
    product_ean_code = forms.CharField(required=False)
    mrp = forms.DecimalField(required=False)
    selling_price = forms.DecimalField(min_value=0, decimal_places=2, required=False)
    discounted_selling_price = forms.DecimalField(min_value=0, decimal_places=2)
    discounted_stock = forms.IntegerField(initial=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            discounted_stock = PosInventory.objects.filter(product=self.instance,
                                                           inventory_state__inventory_state=PosInventoryState.AVAILABLE).last().quantity

            initial_arguments = {'discounted_stock': discounted_stock,
                                 'discounted_selling_price': self.instance.selling_price}
            kwargs.update(initial=initial_arguments)
            super().__init__(*args, **kwargs)
            self.fields['shop'].disabled = True
            self.fields['product_ref'].disabled = True
        self.fields['mrp'].disabled = True
        self.fields['selling_price'].disabled = True
        self.fields['product_ean_code'].disabled = True

    def clean(self):
        data = self.cleaned_data
        if not data.get('product_ref'):
            raise ValidationError(_('Invalid Product.'))
        product_ref = data.get('product_ref')
        if data.get('discounted_selling_price') is None or data.get('discounted_selling_price') <= 0 \
                or data.get('discounted_selling_price') >= product_ref.selling_price:
            raise ValidationError(_('Invalid discounted price.'))
        if self.instance.id is None and \
                DiscountedRetailerProduct.objects.filter(product_ref=data['product_ref']).exists():
            raise ValidationError(_('Discounted product already exists for this product'))
        return data


class RetailerProductsCSVDownloadForm(forms.Form):
    """
        Select shop for downloading Retailer Products
    """
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', )
    )


class RetailerProductsCSVUploadForm(forms.Form):
    """
        Select shop for create or update Products
    """
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', ),
    )
    file = forms.FileField(label='Upload Products')

    def __init__(self, *args, **kwargs):

        try:
            self.shop_id = kwargs.pop('shop_id')
        except:
            self.shop_id = ''

        super().__init__(*args, **kwargs)

    def check_mandatory_data(self, row, key_string, row_num):
        """
            Check Mandatory Fields from uploaded CSV for creating or updating Retailer Products
        """
        if key_string not in row.keys():
            raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

        if key_string in row.keys():
            if row[key_string] == '':
                raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

    def validate_data(self, uploaded_data_by_user_list):
        """
            Validation for create Products Catalogue
        """
        row_num = 1
        for row in uploaded_data_by_user_list:
            row_num += 1
            self.check_mandatory_data(row, 'shop_id', row_num)
            self.check_mandatory_data(row, 'product_name', row_num)
            self.check_mandatory_data(row, 'mrp', row_num)
            self.check_mandatory_data(row, 'selling_price', row_num)
            self.check_mandatory_data(row, 'product_pack_type', row_num)
            self.check_mandatory_data(row, 'available_for_online_orders', row_num)
            self.check_mandatory_data(row, 'is_visible', row_num)
            self.check_mandatory_data(row, 'initial_purchase_value', row_num)

            if row["shop_id"] != self.shop_id:
                raise ValidationError(_(f"Row {row_num} | {row['shop_id']} | "
                                        f"Check the shop id, you might be uploading to wrong shop!"))

            if row["product_id"] != '':
                if not RetailerProduct.objects.filter(id=row["product_id"]).exists():
                    raise ValidationError(_(f"Row {row_num} | {row['product_id']} | doesn't exist"))

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['mrp'])):
                raise ValidationError(_(f"Row {row_num} | 'Product MRP' can only be a numeric value."))

            if not re.match("^\d+[.]?[\d]{0,2}$", str(row['selling_price'])):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' can only be a numeric value."))

            if decimal.Decimal(row['selling_price']) > decimal.Decimal(row['mrp']):
                raise ValidationError(_(f"Row {row_num} | 'Selling Price' cannot be greater than 'Product Mrp'"))

            if 'linked_product_sku' in row.keys():
                if row['linked_product_sku'] != '':
                    if not Product.objects.filter(product_sku=row['linked_product_sku']).exists():
                        raise ValidationError(
                            _(f"Row {row_num} | {row['linked_product_sku']} | 'SKU ID' doesn't exist."))

            #Check for discounted product
            if row.get('product_id') == '' and 'discounted_price' in row.keys() and not row.get('discounted_price')=='':
                raise ValidationError(_(f"Row {row_num} | 'Discounted Product' cannot be created for new product | Provide product Id"))

            if row.get('product_id') != '' and 'discounted_price' in row.keys() and row.get('discounted_price'):
                product = RetailerProduct.objects.filter(id=row["product_id"]).last()
                if product.sku_type == 4:
                    raise ValidationError("This product is already discounted. Further discounted product"
                                                      " cannot be created.")
                elif 'discounted_stock' not in row.keys() or not row['discounted_stock']:
                    raise ValidationError("Discounted stock is required to create discounted product")
                elif decimal.Decimal(row['discounted_price']) <= 0:
                    raise ValidationError("Discounted Price should be greater than 0")
                elif decimal.Decimal(row['discounted_price']) >= decimal.Decimal(row['selling_price']):
                    raise ValidationError("Discounted Price should be less than selling price")
                elif int(row['discounted_stock']) < 0:
                    raise ValidationError("Invalid discounted stock")

            if 'available_for_online_orders' in row.keys() and str(row['available_for_online_orders']).lower() not in \
                    ['yes', 'no']:
                raise ValidationError("Available for Online Orders should be Yes OR No")
            if 'available_for_online_orders' and str(row['available_for_online_orders']).lower() == 'yes':
                row['online_enabled'] = True
            else:
                row['online_enabled'] = False

            if 'is_visible' in row.keys() and str(row['is_visible']).lower() == 'yes':
                row['is_deleted'] = False
            else:
                row['is_deleted'] = True

            if 'online_order_price' in row.keys() and row['online_order_price'] and \
                    decimal.Decimal(row['online_order_price']) > decimal.Decimal(row['mrp']):
                raise ValidationError("Online Order Price should be equal to OR less than MRP")

            if 'initial_purchase_value' in row.keys() and row['initial_purchase_value'] and \
                    decimal.Decimal(row['initial_purchase_value']) > decimal.Decimal(row['selling_price']):
                raise ValidationError("Initial Purchase Value should be equal to OR less than Selling Price")

            # Validate packaging type and measurement category
            if row['product_pack_type'].lower() not in ['loose', 'packet']:
                raise ValidationError(_(f"Row {row_num} | Invalid product_pack_type. Options are 'packet' or 'loose'"))
            if row['product_pack_type'].lower() == 'loose':
                self.check_mandatory_data(row, 'measurement_category', row_num)
                try:
                    measure_cat = MeasurementCategory.objects.get(category=row['measurement_category'])
                    MeasurementUnit.objects.filter(category=measure_cat).last()
                except:
                    raise ValidationError(_(f"Row {row_num} | Invalid measurement_category."))
                row['purchase_pack_size'] = 1

            if not str(row['purchase_pack_size']).isdigit():
                raise ValidationError(_(f"Row {row_num} | Invalid purchase_pack_size."))

            # check for offer price
            if 'offer_price' in row.keys() and row['offer_price']:
                if decimal.Decimal(row['offer_price']) > decimal.Decimal(row['mrp']):
                    raise ValidationError("Offer Price should be equal to OR less than MRP")
                if not 'offer_start_date' in row.keys() or not row['offer_start_date']:
                    raise ValidationError("Offer Start Date is missing")
                if not 'offer_end_date' in row.keys() or not row['offer_end_date']:
                    raise ValidationError("Offer End Date is missing")
                if row['offer_start_date'] > row['offer_end_date']:
                    raise ValidationError("Offer start date should be less than offer end date")

            # Check if product with this ean code and mrp already exists
            if row.get('product_id') == '' and RetailerProduct.objects.filter(shop_id=row.get('shop_id'),
                                              product_ean_code=row.get('product_ean_code'),
                                              mrp=row.get('mrp'), is_deleted=False).exists():
                raise ValidationError(_(f"Row {row_num} | "
                                 f"product with ean code {row.get('product_ean_code')} "
                                 f"and mrp {row.get('mrp')} already exists"))
                continue

    def read_file(self, headers, reader):
        """
            Reading & validating File Uploaded by user
        """
        uploaded_data_by_user_list = []
        csv_dict = {}
        count = 0
        for id, row in enumerate(reader):
            for ele in row:
                csv_dict[headers[count]] = ele
                count += 1
            uploaded_data_by_user_list.append(csv_dict)
            csv_dict = {}
            count = 0
        self.validate_data(uploaded_data_by_user_list)

    def clean_file(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))

                headers = next(reader, None)
                self.read_file(headers, reader)
        return self.cleaned_data['file']


class RetailerProductMultiImageForm(forms.ModelForm):
    """
       Bulk Retailer Products Image Form
    """

    class Meta:
        model = RetailerProductImage
        fields = ('image',)


class PosInventoryChangeCSVDownloadForm(forms.Form):
    """
        Select sku for downloading PosInventory changes
    """
    sku = forms.ModelChoiceField(
        label='Select Product SKU',
        queryset=RetailerProduct.objects.filter(~Q(sku_type=4)),
        widget=autocomplete.ModelSelect2(url='inventory-product-autocomplete', )
    )


class MeasurementUnitFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        super(MeasurementUnitFormSet, self).clean()
        count = 0
        valid = True
        default_count = 0
        for form in self:
            if form.is_valid():
                if form.cleaned_data:
                    count += 1
                if form.instance.default:
                    default_count += 1
            else:
                valid = False

        if count < 1:
            raise ValidationError("At least one Measurement Unit is required")

        if default_count > 1:
            raise ValidationError("Only one Measurement Unit can be set as default")

        if default_count < 1:
            raise ValidationError("Please set one Measurement Unit as default")

        if valid:
            return self.cleaned_data

    class Meta:
        model = MeasurementUnit


class RetailerProductsStockUpdateForm(forms.Form):
    """
        Select shop for stock update
    """
    shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', ),
    )
    file = forms.FileField(label='Upload Product Stock')

    def __init__(self, *args, **kwargs):

        try:
            self.shop_id = kwargs.pop('shop_id')
        except:
            self.shop_id = ''

        super().__init__(*args, **kwargs)

    def check_mandatory_data(self, row, key_string, row_num):
        """
            Check Mandatory Fields from uploaded CSV for creating or updating Retailer Products
        """
        if key_string not in row.keys():
            raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

        if key_string in row.keys():
            if row[key_string] == '':
                raise ValidationError(_(f"Row {row_num} | Please provide {key_string}"))

    def validate_data(self, uploaded_data_list):
        """
            Validation for create Products Catalogue
        """
        row_num = 1
        for row in uploaded_data_list:
            row_num += 1
            self.check_mandatory_data(row, 'shop_id', row_num)
            self.check_mandatory_data(row, 'product_id', row_num)
            self.check_mandatory_data(row, 'current_inventory', row_num)
            self.check_mandatory_data(row, 'updated_inventory', row_num)

            if row["shop_id"] != self.shop_id:
                raise ValidationError(_(f"Row {row_num} | {row['shop_id']} | "
                                        f"Check the shop id, you might be uploading to wrong shop!"))

            if not RetailerProduct.objects.filter(id=row["product_id"]).exists():
                raise ValidationError(_(f"Row {row_num} | {row['product_id']} | doesn't exist"))

            if row["current_inventory"] == '':
                raise ValidationError(_(f"Row {row_num} | {row['current_inventory']} | "
                                        f"Current Inventory is not valid!"))

            if row["updated_inventory"] == '' or int(row["updated_inventory"]) < 0 :
                raise ValidationError(_(f"Row {row_num} | {row['updated_inventory']} | "
                                        f"Update Inventory is not valid!"))
            if row["current_inventory"] != row["updated_inventory"] \
                    and ('reason_for_update' not in row or row["reason_for_update"] == ''):

                raise ValidationError(_(f"Row {row_num} | {row['reason_for_update']} | "
                                        f"Reason for update is required!"))

            #validation for discounted product
            if row.get('product_id') != '' and 'discounted_price' in row.keys() and not row.get('discounted_price') == '':
                product = RetailerProduct.objects.filter(id=row["product_id"]).last()
                if product.sku_type == 4:
                    raise ValidationError("This product is already discounted. Further discounted product"
                                                      " cannot be created.")
                elif 'discounted_inventory' not in row.keys() or not row['discounted_inventory']:
                    raise ValidationError("Discounted qty is required to create discounted product")
                elif decimal.Decimal(row['discounted_price']) <= 0:
                    raise ValidationError("Discounted Price should be greater than 0")
                elif decimal.Decimal(row['discounted_price']) >= product.selling_price:
                    raise ValidationError("Discounted Price should be less than selling price")
                elif int(row['discounted_inventory']) < 0:
                    raise ValidationError("Invalid discounted qty")



    def read_file(self, headers, reader):
        """
            Reading & validating File Uploaded by user
        """
        uploaded_data_by_user_list = []
        csv_dict = {}
        count = 0
        for id, row in enumerate(reader):
            for ele in row:
                csv_dict[headers[count]] = ele
                count += 1
            uploaded_data_by_user_list.append(csv_dict)
            csv_dict = {}
            count = 0
        self.validate_data(uploaded_data_by_user_list)

    def clean_file(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in ('.csv'):
                raise forms.ValidationError("Please upload only CSV File")
            else:
                reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))

                headers = next(reader, None)
                self.read_file(headers, reader)
        return self.cleaned_data['file']


class RetailerOrderedReportForm(forms.Form):
    start_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD',
            },
            attrs={
                'autocomplete': 'off'
            }
        ),
    )
    end_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD',
            },
            attrs={
                'autocomplete': 'off'
            }
        ),
    )
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2,
                                     pos_enabled=True, pos_shop__status=True),
        widget=autocomplete.ModelSelect2(url='pos-shop-autocomplete', ),
    )


class RetailerPurchaseReportForm(forms.Form):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='f', status=True, approval_status=2,
                                     pos_enabled=True, pos_shop__status=True),
        widget=autocomplete.ModelSelect2(url='pos-shop-autocomplete', ),
    )
