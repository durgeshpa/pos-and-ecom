import datetime
from datetime import datetime, timedelta
from django import forms

from .common_validators import get_validate_approval_status_change_reason
from .models import ParentRetailerMapping, PosShopUserMapping, Shop, ShopType, ShopUserMapping, ShopTiming, \
    BeatPlanning, ShopStatusLog, FOFOConfigurations, FOFOConfig
from addresses.models import Address, State, City, DispatchCenterCityMapping, DispatchCenterPincodeMapping, Pincode
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from dal import autocomplete
import csv
import codecs
from products.models import Product, ProductPrice
import re
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from retailer_backend.messages import VALIDATION_ERROR_MESSAGES
from django.core.exceptions import ObjectDoesNotExist
from accounts.middlewares import get_current_user
from django.utils.translation import ugettext_lazy as __


class ParentRetailerMappingForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp','gf']),
        widget=autocomplete.ModelSelect2(url='shop-parent-autocomplete', )
    )
    retailer = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type__in=['sp', 'r', 'f']),
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
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['upload_file'], 'utf-8', errors='ignore'))
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

    shop_code_bulk = forms.CharField(
                        max_length=1, min_length=1,
                        required=False, validators=[
                            RegexValidator(
                                regex='^[a-zA-Z0-9]*$',
                                message='Shop Code must be Alphanumeric',
                                code='invalid_code_code'
                            ),
                        ])

    shop_code_discounted = forms.CharField(
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

    shop_code_super_store = forms.CharField(
                        max_length=1, min_length=1,
                        required=False, validators=[
                            RegexValidator(
                                regex='^[a-zA-Z0-9]*$',
                                message='Shop Code must be Alphanumeric',
                                code='invalid_code_code'
                            ),
                        ])
    shop_owner = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:user-autocomplete', )
    )

    # approval_status_reason = forms.ChoiceField(
    #     choices=Shop.APPROVAL_STATUS_REASON_CHOICES,
    #     widget=autocomplete.ModelSelect2(url='admin:approval-status-reason-autocomplete', forward=('approval_status',))
    # )

    shop_location = forms.CharField(
        max_length=125, min_length=3, required=False,  widget=forms.TextInput(attrs={'size':50,'placeholder': 'Enter Location to Search'})
    )

    class Meta:
        Model = Shop
        fields = (
            'shop_name', 'shop_owner', 'shop_type', 'approval_status', 'disapproval_status_reason',
            'shop_code', 'shop_code_bulk', 'shop_code_discounted', 'warehouse_code', 'shop_code_super_store',
            'created_by', 'status', 'pos_enabled', 'online_inventory_enabled', 'shop_location', 'latitude', 'longitude',
            'cutoff_time')

    def clean(self):
        data = self.cleaned_data
        if data.get('approval_status') == Shop.DISAPPROVED and data.get('disapproval_status_reason') is None:
            raise ValidationError('Disapproval status reason is required.')

        return data

    def clean(self):
        data = self.cleaned_data
        if data.get('approval_status') == Shop.DISAPPROVED and data.get('disapproval_status_reason') is None:
            raise ValidationError('Disapproval status reason is required.')

        return data

    @classmethod
    def get_shop_type(cls, data):
        shop_type = data.cleaned_data.get('shop_type')
        return shop_type

    @classmethod
    def shop_type_retailer(cls, data):
        shop_type = cls.get_shop_type(data)
        if shop_type and shop_type.shop_type not in ['r', 'f']:
            return False
        return True

    @classmethod
    def shop_type_dispatch_center(cls, data):
        shop_type = cls.get_shop_type(data)
        if shop_type.shop_type != 'dc':
            return False
        return True

    def clean_shop_code(self):
        shop_code = self.cleaned_data.get('shop_code', None)
        if not self.shop_type_retailer(self) and not shop_code:
            raise ValidationError(_("This field is required"))
        return shop_code

    def clean_shop_code_bulk(self):
        shop_code_bulk = self.cleaned_data.get('shop_code_bulk', None)
        if not self.shop_type_retailer(self) and not shop_code_bulk:
            raise ValidationError(_("This field is required"))
        return shop_code_bulk

    def clean_shop_code_discounted(self):
        shop_code_discounted = self.cleaned_data.get('shop_code_discounted', None)
        if not self.shop_type_retailer(self) and not shop_code_discounted:
            raise ValidationError(_("This field is required"))
        return shop_code_discounted

    def clean_warehouse_code(self):
        warehouse_code = self.cleaned_data.get('warehouse_code', None)
        if not self.shop_type_retailer(self) and not warehouse_code:
            raise ValidationError(_("This field is required"))
        return warehouse_code

    def clean_cutoff_time(self):
        cutoff_time = self.cleaned_data.get('cutoff_time', None)
        if self.shop_type_dispatch_center(self) and not cutoff_time:
            raise ValidationError(_("This field is required"))
        return cutoff_time

    def clean_disapproval_status_reason(self):
        disapproval_status_reason = self.cleaned_data.get('disapproval_status_reason', None)
        if int(self.data['approval_status']) != Shop.DISAPPROVED:
            return None
        return disapproval_status_reason

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
        flag_bill = 0
        delete = False
        address_form = []
        address_form_bill = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['address_type'] == 'shipping':
                address_form.append(form.cleaned_data.get('DELETE'))
                flag = 1
            if form.cleaned_data and form.cleaned_data['address_type'] == 'billing':
                address_form_bill.append(form.cleaned_data.get('DELETE'))
                flag_bill = 1

        if address_form and all(address_form):
            raise forms.ValidationError('You cant delete all shipping address')
        elif flag==0:
            raise forms.ValidationError('Please add at least one shipping address')
        if self.instance.shop_type and self.instance.shop_type.shop_type == 'f':
            if address_form_bill and all(address_form_bill):
                raise forms.ValidationError('You cant delete all billing address')
            elif flag_bill == 0:
                raise forms.ValidationError('Please add at least one billing address')
from django.contrib.admin import widgets as wi
class FOFOConfigInlineForm(forms.ModelForm):
    # SUN = 'SUN'
    # MON = 'MON'
    # TUE = 'TUE'
    # WED = 'WED'
    # THU = 'THU'
    # FRI = 'FRI'
    # SAT = 'SAT'
    #
    # off_day_choices = (
    #     (SUN, 'Sunday'),
    #     (MON, 'Monday'),
    #     (TUE, 'Tuesday'),
    #     (WED, 'Wednesday'),
    #     (THU, 'Thuresday'),
    #     (FRI, 'Friday'),
    #     (SAT, 'Saturday'),
    # )
    #days = forms.CharField(widget=forms.TextInput)
    class Meta:
        model = FOFOConfig
        fields = ('shop_opening_timing','shop_closing_timing','working_off_start_date','working_off_end_date','delivery_time', 'delivery_redius','min_order_value')
        help_texts = {
            'redius': 'Insert value in meters',
            'delivery_time':'Insert value in minutes',
        }
        widgets = {'delivery_time':forms.TextInput(attrs={'placeholder': 'Enter Value In Minutes'}),
                    'delivery_redius': forms.TextInput(attrs={'placeholder': 'Enter Value In Meter'})}
        labels = {
            'delivery_time': __('Delivery Time (Minutes)'),
            'delivery_redius': __('Delivery Radius (Meter)')
            }

    def clean(self):
        start_date = self.cleaned_data.get('working_off_start_date')
        end_date = self.cleaned_data.get('working_off_end_date')
        if start_date and start_date < datetime.today().date():
            self._errors['working_off_start_date'] = self.error_class(["Only Current Or Future Date Allowed"])
        if end_date and end_date < datetime.today().date():
            self._errors['working_off_end_date'] = self.error_class(["Only Current Or Future Date Allowed"])
        if start_date and not end_date:
            self._errors['working_off_end_date'] = self.error_class(["Date Required"])
        if end_date and not start_date:
            self._errors['working_off_start_date'] = self.error_class(["Date Required"])
        if (start_date and end_date ) and start_date > end_date:
            self._errors['working_off_start_date'] = self.error_class(["Start Date Should Be Less Than Or Eqal To End Date"])
            self._errors['working_off_end_date'] = self.error_class(["End Date Should Be Greater Than or Eqal to Start Date"])
        time = self.cleaned_data.get('delivery_time')
        if time and time<0:
            self._errors['delivery_time'] = self.error_class(["Delivery Time Should Be Positive Number"])
        delivery_redius = self.cleaned_data.get('delivery_redius')
        if delivery_redius and delivery_redius<0:
            self._errors['delivery_redius'] = self.error_class(["Delivery Radius Should Be Positive Number"])

        return self.cleaned_data


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
        queryset=Shop.objects.filter(shop_type__shop_type__in=['r', 'f']),
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


class BulkShopStatusChange(forms.Form):
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name[-4:] == '.csv':
            raise forms.ValidationError("Sorry! Only CSV file accepted")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        form_data_list = []
        for row_id, row in enumerate(reader):
            if not row[0]:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " + "Shop Id must not be empty."))
            if not Shop.objects.filter(pk=int(row[0])).exists():
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " +
                                        "shop id does not exist in the system."))
            if not row[2]:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " +
                                        "Shop Approval Status must not be empty."))
            if not str(row[2]).lower() in ['awaiting approval', 'approved', 'disapproved']:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " +
                                        "Incorrect Shop Approval Status."))
            if str(row[2]).lower() == 'awaiting approval':
                row[2] = 1
            if str(row[2]).lower() == 'approved':
                row[2] = 2
            else:
                row[2] = 0
            if row[2] == 0 and not row[3]:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " +
                                        "Disapproval Status Reason must not be empty."))
            if row[2] == 0 and row[3]:
                disapproval_status_reason = get_validate_approval_status_change_reason(str(row[3]), row[2])
                if 'error' in disapproval_status_reason:
                    raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", " +
                                            disapproval_status_reason["error"]))
                row[3] = disapproval_status_reason['data']
            else:
                row[3] = None

            form_data_list.append(row)
        return form_data_list


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

class PosShopUserMappingForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(pos_enabled=True).all(),
        widget=autocomplete.ModelSelect2(url='admin:pos-shop-complete',)
    )
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        widget=autocomplete.ModelSelect2(url='admin:user-autocomplete', )
    )

    class Meta:
        model = PosShopUserMapping
        fields = ('shop', 'user', 'user_type', 'is_delivery_person', 'status',)

class ShopUserMappingCsvViewForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
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


class BeatPlanningAdminForm(forms.ModelForm):
    """
    Beat Planning Admin Form
    """
    class Meta:
        model = BeatPlanning
        fields = ('executive',)

    def __init__(self, *args, **kwargs):
        """

        :param args: non-keyword arguments
        :param kwargs: keyword arguments
        """
        super(BeatPlanningAdminForm, self).__init__(*args, **kwargs)
        # get manager object
        # shop_mapping_object = (ShopUserMapping.objects.filter(
        #     employee=self.current_user.shop_employee.instance,
        #     employee_group__permissions__codename='can_sales_manager_add_shop', status=True).last())
        # condition to check the current user is super user  or manager
        if self.current_user.shop_employee.instance.is_superuser:
            self.fields['executive'] = forms.ModelChoiceField(
                queryset=get_user_model().objects.filter(user_type=6, is_active=True),
                widget=autocomplete.ModelSelect2(url='admin:user-autocomplete',))
        else:
            self.fields['executive'] = forms.ModelChoiceField(queryset=ShopUserMapping.objects.filter(
                manager__in=ShopUserMapping.objects.filter(employee=self.current_user, status=True),
                status=True).order_by(
                'employee').distinct('employee'), widget=autocomplete.ModelSelect2())


class BeatUserMappingCsvViewForm(forms.Form):
    """
    This Form class is used to upload csv for particular sales executive in Beat Planning
    """
    file = forms.FileField()

    def clean_file(self):
        """

        :return: Form is valid otherwise validation error message
        """

        # Validate to check the file format, It should be csv file.
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted.")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        # list which contains csv data and pass into the view file
        form_data_list = []
        for row_id, row in enumerate(reader):

            # validation for shop id, it should be numeric.
            if not row[2] or not re.match("^[\d]*$", row[2]):
                raise ValidationError(_('INVALID_SHOP_ID at Row number [%(value)s]. It should be numeric.'),
                                      params={'value': row_id+1},)

            # validation for shop id to check that is exist or not in the database
            if not Shop.objects.filter(pk=row[2]).exists():
                raise ValidationError(_('INVALID_SHOP_ID at Row number [%(value)s]. Shop Id not exists.'),
                                      params={'value': row_id+1},)

            # validation for executive to check that is exist or not in the database
            if not get_user_model().objects.filter(phone_number=row[0].split('-')[0].split(' ')[0]).exists():
                raise ValidationError(_('INVALID_EMPLOYEE_NO at Row number [%(value)s]. Employee is not exists.'),
                                      params={'value': row_id+1},)

            # validation for shop id is associate with executive
            if not ShopUserMapping.objects.filter(employee__phone_number=row[0].split('-')[0].split(' ')[0],
                                                  shop__shop_user__shop_id=row[2]).distinct().exists():
                raise ValidationError(_('Row number [%(value)s] | Shop not mapped to the selected Sales executive.'),
                                      params={'value': row_id+1},)

            # validation for category name
            if not row[6] in ['P1', 'P2', 'P3']:
                raise ValidationError(_('INVALID Priority at Row number [%(value)s]. It should be only P1, P2 and P3.'),
                                      params={'value': row_id+1},)

            # validation to check that date is not empty
            if row[7] is '':
                raise ValidationError(_('Row number [%(value)s] | Date is not entered.'),
                                      params={'value': row_id+1},)

            # validation to check the day is not sunday
            if not row[7] is '':
                try:
                    # row[7] = '04/07/2020'
                    if datetime.strptime(row[7], '%d/%m/%y'):
                        row_date = datetime.strptime(row[7], '%d/%m/%y')
                        if row_date.date() < (datetime.today() + timedelta(days=1)).date():
                            raise ValidationError(_('Row number [%(value)s] | Date should be greater then Current Date.'),
                                                  params={'value': row_id + 1}, )
                except Exception as e:
                    try:
                        if datetime.strptime(row[7], '%d/%m/%Y'):
                            row_date = datetime.strptime(row[7], '%d/%m/%Y')
                            if row_date.date() < (datetime.today() + timedelta(days=1)).date():
                                raise ValidationError(_('Row number [%(value)s] | Date should be greater then Current Date.'),
                                                      params={'value': row_id + 1}, )
                        else:
                            raise ValidationError(_('Row number [%(value)s] | Date Format is not correct.'),
                                                  params={'value': row_id + 1}, )
                    except Exception as e:
                        raise ValidationError(_('Issue in Row number [%(value)s] | Reason could be the Date Format or '
                                                'Date is not greater then Current Date.'),
                                              params={'value': row_id + 1}, )

            # append csv date in a list
            form_data_list.append(row)

        # return list
        return form_data_list


class DispatchCenterCityMappingForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        widget=autocomplete.ModelSelect2(url='dispatch-center-cities-autocomplete'),
        required=True
    )

    class Meta:
        model = DispatchCenterCityMapping
        fields = ('city', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DispatchCenterCityMappingInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(DispatchCenterCityMappingInlineFormSet, self).clean()
        flag = 0
        address_form = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['city']:
                # if form.cleaned_data['city'].city_center_mapping.last() is not None:
                #     raise forms.ValidationError('City is already mapped with another dispatch center')
                address_form.append(form.cleaned_data.get('DELETE'))
                flag = 1

        if self.instance.shop_type and self.instance.shop_type.shop_type == 'dc':
            if address_form and all(address_form):
                raise forms.ValidationError('You cant delete all cities of dispatch center')
            elif flag == 0:
                raise forms.ValidationError('Please add at least one city of dispatch center')


class DispatchCenterPincodeMappingForm(forms.ModelForm):
    pincode = forms.ModelChoiceField(
        queryset=Pincode.objects.all(),
        widget=autocomplete.ModelSelect2(url='dispatch-center-pincodes-autocomplete'),
        required=True
    )

    class Meta:
        model = DispatchCenterPincodeMapping
        fields = ('pincode', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DispatchCenterPincodeMappingInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super(DispatchCenterPincodeMappingInlineFormSet, self).clean()
        flag = 0
        address_form = []
        for form in self.forms:
            if form.cleaned_data and form.cleaned_data['pincode']:
                # if form.cleaned_data['pincode'].pincode_center_mapping.last() is not None:
                #     raise forms.ValidationError('Pincode is already mapped with another dispatch center')
                address_form.append(form.cleaned_data.get('DELETE'))
                flag = 1

        if self.instance.shop_type and self.instance.shop_type.shop_type == 'dc':
            if address_form and all(address_form):
                raise forms.ValidationError('You cant delete all pincodes of dispatch center')
            elif flag == 0:
                raise forms.ValidationError('Please add at least one pincode of dispatch center')

class FOFOShopConfigForm(forms.ModelForm):
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(online_inventory_enabled=True,
                                     shop_type__shop_sub_type__retailer_type_name='fofo').all(),
        widget=autocomplete.ModelSelect2(url='admin:pos-online_inventory_enabled-shop-complete',)
    )

    class Meta:
        model = FOFOConfigurations
        fields = ('shop', 'key', 'value')
