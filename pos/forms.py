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
    MeasurementUnit, BulkRetailerProduct
from products.models import Product
from shops.models import Shop
from wms.models import PosInventory, PosInventoryState
#from .models import PosStoreRewardMapping, ShopRewardConfig

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


class RetailerProductsCSVUploadForm(forms.ModelForm):
    """
        Select shop for create or update Products
    """
    seller_shop = forms.ModelChoiceField(
        label='Select Shop',
        queryset=Shop.objects.filter(shop_type__shop_type__in=['f']),
        widget=autocomplete.ModelSelect2(url='retailer-product-autocomplete', ),
    )

    class Meta:
        model = BulkRetailerProduct
        fields = ('seller_shop', 'products_csv', 'uploaded_by',)

    def __init__(self, *args, **kwargs):

        try:
            self.shop_id = kwargs.pop('shop_id')
        except:
            self.shop_id = ''

        try:
            self.uploaded_by = kwargs.pop('user')
        except:
            self.uploaded_by = ''
        super().__init__(*args, **kwargs)
        self.fields['uploaded_by'].required = False
        self.fields['uploaded_by'].widget = forms.HiddenInput()

    def clean(self):
        if 'products_csv' in self.cleaned_data:
            if self.cleaned_data['products_csv']:
                if not self.cleaned_data['products_csv'].name[-4:] in ('.csv'):
                    raise forms.ValidationError("Sorry! Only csv file accepted")
        self.cleaned_data['uploaded_by'] = self.uploaded_by


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



class ShopRewardUploadForm(forms.Form):
    """
        Select shop for create or update reward configration django
    """
    file = forms.FileField()

    def clean_file(self):
        """
            FileField validation Check if file ends with only .csv
        """
        if self.cleaned_data.get('file'):

            if not self.cleaned_data['file'].name[-4:] in '.csv':
                raise forms.ValidationError("Please upload only CSV File")
        file = self.cleaned_data['file']
        reader = csv.DictReader(codecs.iterdecode(file, 'utf-8'))
        error = []
        row_num = 1
        count = 0
        lis = []
        for row in reader:
            shop = Shop.objects.filter(id=row.get('shop_id'))
            row_num +=1
            for key in row:
                if key == "shop_id" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                    
                if key == "Minimum_Order_Value" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                elif key == "Minimum_Order_Value" and  int(row[key]) <199:
                    lis.append(f"{key} should be greater than 199 |error at row no {row_num}")

                if key == "Is_Enable_Point_Redeemed_Ecom" and row[key] == True and not row['Max_Point_Redeemed_Ecom']:
                    lis.append(f"'Max_Point_Redeemed_Ecom is required fields|error at row no {row_num}")
                if key == "Is_Enable_Point_Redeemed_Pos" and row[key] == True and not row['Max_Point_Redeemed_Pos']:
                    lis.append(f"Max_Point_Redeemed_Pos is required fields|error at row no {row_num}")
                if key == "Is_Enable_Point_Added_Pos_Order" and row[key] == True and not row['Percentage_Point_Added_Pos_Order_Amount']:
                    lis.append(f"Percentage_Point_Added_Pos_Order_Amount is required fields|error at row no {row_num}")
                if key == "Is_Enable_Point_Added_Ecom_Order" and row[key] == True and not row['Percentage_Point_Added_Ecom_Order_Amount']:
                    lis.append(f"Percentage_Point_Added_Ecom_Order_Amount is required fields|error at row no {row_num}")
                if key == "Max_Monthly_Points_Redeemed" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                if key == "Point_Redeemed_Second_Order" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                if key == "Point_Redeemed_First_Order" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                if key == "Percentage_Value_Of_Each_Point" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")
                if key == "enable_loyalty_points" and not row[key]:
                    lis.append(f"{key} is required fields |error at row no {row_num}")

                
            if len(lis) >= 1:
                raise forms.ValidationError(lis)





        return self.cleaned_data['file']
    
