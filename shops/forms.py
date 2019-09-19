from django import forms
from .models import ParentRetailerMapping, Shop, ShopType, ShopUserMapping, ShopTiming
from addresses.models import Address
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from dal import autocomplete
import csv
import codecs
from products.models import Product, ProductPrice
import re
from .models import Shop
from addresses.models import State
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from django.core.exceptions import ObjectDoesNotExist

class ParentRetailerMappingForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp','gf']),
        widget=autocomplete.ModelSelect2(url='shop-parent-autocomplete', )
    )
    retailer = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp', 'r']),
        widget=autocomplete.ModelSelect2(url='shop-retailer-autocomplete', )
    )

    class Meta:
        Model = ParentRetailerMapping
        fields = ('parent','retailer','status')

    def clean(self):
        cleaned_data = super().clean()
        retailer = cleaned_data.get("retailer")
        parent_mapping = ParentRetailerMapping.objects.filter(retailer=retailer, status=True)
        if parent_mapping.exists():
            for parent in parent_mapping:
                parent.status=False
                parent.save()
        return cleaned_data


class ShopParentRetailerMappingForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp','gf']),
        widget=autocomplete.ModelSelect2(url='shop-parent-autocomplete',forward=('shop_type',))
    )

    class Meta:
        Model = ParentRetailerMapping


class StockAdjustmentUploadForm(forms.Form):
    shop = forms.ModelChoiceField(
            queryset=Shop.objects.filter(shop_type__shop_type__in=['sp']),
        )
    upload_file = forms.FileField()

    def clean_upload_file(self):
        if self.cleaned_data['upload_file'].name[-4:] != ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['upload_file'], 'utf-8'))
        first_row = next(reader)
        for id, row in enumerate(reader):
            if not row[0]:
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[0] + ":" + row[0] + " | Product Id required")
            else:
                try:
                    Product.objects.get(product_gf_code=row[0])
                except:
                    raise ValidationError(_('INVALID_PRODUCT_ID at Row[%(value)s]'), params={'value': id+1},)

            if not row[2]:
                raise ValidationError("Row[" + str(id + 1) + "] | " + first_row[2] + ":" + row[1] + " | Product SKU required")
            else:
                try:
                    Product.objects.get(product_sku=row[2])
                except:
                    raise ValidationError(_('INVALID_PRODUCT_SKU at Row[%(value)s]'), params={'value': id+1},)



            if not row[3] or not re.match("^[\d]*$", row[3]):
                raise ValidationError(_('INVALID_AVAILABLE_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

            if not row[4] or not re.match("^[\d]*$", row[4]):
                raise ValidationError(_('INVALID_DAMAGED_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

            if not row[5] or not re.match("^[\d]*$", row[5]):
                raise ValidationError(_('INVALID_EXPIRED_QTY at Row[%(value)s]. It should be numeric'),params={'value': id + 1}, )

        return self.cleaned_data['upload_file']


class ShopForm(forms.ModelForm):
    shop_code = forms.CharField(
                        max_length=1, min_length=1,
                        required=False, validators=[
                            RegexValidator(
                                regex='^[a-zA-Z0-9]*$',
                                message='Shop Code must be Alphanumeric',
                                code='invalid_code_code'
                            ),
                        ])
    warehouse_code = forms.CharField(
                        max_length=2, min_length=2,
                        required=False, validators=[
                            RegexValidator(
                                regex='^[a-zA-Z0-9]*$',
                                message='Warehouse Code must be Alphanumeric',
                                code='invalid_warehouse_code'
                            ),
                        ])

    shop_owner = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:user-autocomplete', )
    )

    class Meta:
        Model = Shop
        fields = (
            'shop_name', 'shop_owner', 'shop_type',
            'shop_code', 'warehouse_code','created_by', 'status')

    @classmethod
    def get_shop_type(cls, data):
        shop_type = data.cleaned_data.get('shop_type')
        return shop_type

    @classmethod
    def shop_type_retailer(cls, data):
        shop_type = cls.get_shop_type(data)
        if shop_type.shop_type != 'r':
            return False
        return True

    def clean_shop_code(self):
        shop_code = self.cleaned_data.get('shop_code', None)
        if not self.shop_type_retailer(self) and not shop_code:
            raise ValidationError(_("This field is required"))
        return shop_code

    def clean_warehouse_code(self):
        warehouse_code = self.cleaned_data.get('warehouse_code', None)
        if not self.shop_type_retailer(self) and not warehouse_code:
            raise ValidationError(_("This field is required"))
        return warehouse_code


class AddressForm(forms.ModelForm):
    nick_name = forms.CharField(required=True)
    address_contact_name = forms.CharField(required=True)
    address_contact_number = forms.CharField(required=True)
    state = forms.ModelChoiceField(queryset=State.objects.all())
    pincode = forms.CharField(max_length=6, required=True)

    class Meta:
        Model = Address

from django.forms.models import BaseInlineFormSet

class RequiredInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super(RequiredInlineFormSet, self)._construct_form(i, **kwargs)
        if i < 1:
            form.empty_permitted = False
        return form

class AddressInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(AddressInlineFormSet, self).clean()
        flag = 0
        delete = False
        address_form = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['address_type'] == 'shipping':
                address_form.append(form.cleaned_data.get('DELETE'))
                flag = 1

        if address_form and all(address_form):
            raise forms.ValidationError('You cant delete all shipping address')
        elif flag==0:
            raise forms.ValidationError('Please add at least one shipping address')

class ShopTimingForm(forms.ModelForm):
    SUN = 'SUN'
    MON = 'MON'
    TUE = 'TUE'
    WED = 'WED'
    THU = 'THU'
    FRI = 'FRI'
    SAT = 'SAT'

    off_day_choices = (
        (SUN, 'Sunday'),
        (MON, 'Monday'),
        (TUE, 'Tuesday'),
        (WED, 'Wednesday'),
        (THU, 'Thuresday'),
        (FRI, 'Friday'),
        (SAT, 'Saturday'),
    )
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r']),
        widget=autocomplete.ModelSelect2(url='admin:shop-timing-autocomplete', )
    )
    off_day = forms.MultipleChoiceField(
        required=False,
        choices=off_day_choices,
        widget=forms.SelectMultiple(),
    )

    class Meta:
        model = ShopTiming
        fields = ('shop','open_timing','closing_timing','break_start_time','break_end_time','off_day')

class BulkShopUpdation(forms.Form):
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name[-5:] == '.xlsx':
            raise forms.ValidationError("Sorry! Only Excel file accepted")
        return file

class ShopUserMappingForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:shop-autocomplete',)
    )
    employee = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:user-autocomplete', )
    )

    class Meta:
        model = ShopUserMapping
        fields = ('shop', 'manager', 'employee','employee_group','status')

    # def clean(self):
    #     cleaned_data = super().clean()
    #     if self.cleaned_data.get('shop') and self.cleaned_data.get('employee') and self.cleaned_data.get('employee_group'):
    #         group = Permission.objects.get(codename='can_sales_person_add_shop').group_set.last()
    #         shop_user_obj =ShopUserMapping.objects.filter(shop=self.cleaned_data.get('shop'), employee_group=group)
    #         if shop_user_obj.exists() and shop_user_obj.last().employee != self.cleaned_data.get('employee'):
    #             raise ValidationError(_(VALIDATION_ERROR_MESSAGES['ALREADY_ADDED_SHOP']))
    #     return cleaned_data

class ShopUserMappingCsvViewForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        uploaded_employee_list = []
        for id, row in enumerate(reader):
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError(_('INVALID_SHOP_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)

            if not Shop.objects.filter(pk=row[0]).exists():
                raise ValidationError(_('INVALID_SHOP_ID at Row[%(value)s]. Shop Id not exists'), params={'value': id+1},)

            if not row[2] or not re.match("^[\d]*$", row[2]):
                raise ValidationError(_('INVALID_EMPLOYEE_NO at Row[%(value)s]. It should be numeric'), params={'value': id+1},)

            if not get_user_model().objects.filter(phone_number=row[2]).exists():
                raise ValidationError(_('INVALID_EMPLOYEE_NO at Row[%(value)s]. Employee no not exists'), params={'value': id+1},)

            if row[1] and not re.match("^[\d]*$", row[1]) and not get_user_model().objects.filter(phone_number=row[1]).exists():
                raise ValidationError(_('INVALID_MANAGER_NO at Row[%(value)s]. It should be numeric'), params={'value': id+1},)

            if row[1] and not any([row[1] in uploaded_employee_list, ShopUserMapping.objects.filter(employee__phone_number=row[1], employee_group__permissions__codename='can_sales_manager_add_shop',status=True).exists()]):
                raise ValidationError(_('INVALID_MANAGER_NO at Row[%(value)s]. Please create employee first, then manager'),
                                      params={'value': id + 1}, )

            if not row[3] or not re.match("^[\d]*$", row[3]) or not Group.objects.filter(pk=row[3]):
                raise ValidationError(_('INVALID_GROUP_ID at Row[%(value)s]. It should be numeric'), params={'value': id+1},)

            uploaded_employee_list.append(row[2])



