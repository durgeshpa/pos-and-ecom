import codecs
import csv
import datetime
import logging

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.widgets import AdminDateWidget

from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping
from retailer_incentive.utils import get_active_mappings
from shops.models import Shop
from .common_function import save_scheme_shop_mapping_data
from retailer_backend.utils import isDateValid

info_logger = logging.getLogger('file-info')


class SchemeCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme
    """

    start_date = forms.DateTimeField(widget=AdminDateWidget())
    end_date = forms.DateTimeField(widget=AdminDateWidget())

    class Meta:
        model = Scheme
        fields = ['name', 'start_date', 'end_date', 'is_active']

    def __init__(self, *args, **kwargs):
        """
        args:- non keyword argument
        kwargs:- keyword argument
        """
        self.request = kwargs.pop('request', None)
        super(SchemeCreationForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        # if instance.id:
        #     self.fields['name'].disabled = True
        #     self.fields['start_date'] = forms.DateTimeField()
        #     self.fields['start_date'].disabled = True
        #     self.fields['end_date'] = forms.DateTimeField()
        #     self.fields['end_date'].disabled = True

    def clean(self):
        if not self.instance.id:
            data = self.cleaned_data
            start_date = data.get('start_date')
            end_date = data.get('end_date') + datetime.timedelta(hours=23, minutes=59, seconds=59)
            data['end_date'] = end_date
            if start_date.date() <= datetime.date.today():
                raise ValidationError('Start date cannot be equal to today or earlier than today')

            if end_date.date() <= start_date.date():
                raise ValidationError('End Date should be later than the Start Date')

            if Scheme.objects.filter(name=data.get('name'), start_date=start_date, end_date=end_date).exists():
                raise ValidationError('Duplicate Scheme')

        return self.cleaned_data


class SchemeSlabCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme Slabs
    """
    class Meta:
        model = SchemeSlab
        fields = ('min_value', 'max_value', 'discount_value', 'discount_type')


class SlabInlineFormSet(BaseInlineFormSet):
    """
        This class is used to create the Scheme Slab Forms
    """
    def clean(self):
        super(SlabInlineFormSet, self).clean()
        last_slab_end_value = 0
        last_slab_discount_value = 0
        is_first_slab = True
        counter = 1
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        non_empty_forms = non_empty_forms - len(self.deleted_forms)
        if non_empty_forms < 0:
            raise ValidationError("please add atleast one slab!")
        for form in self.forms:
            slab_data = form.cleaned_data
            if slab_data.get('min_value') is not None and \
                    slab_data.get('max_value') is not None and \
                    slab_data.get('discount_value') is not None:
                if slab_data['min_value'] < 0 or slab_data['max_value'] < 0:
                    raise ValidationError("Value should be greater than 0")
                if not is_first_slab and slab_data['min_value'] < last_slab_end_value:
                    raise ValidationError("Slab start value should be greater than or equal to the end value in earlier slab")
                if counter < non_empty_forms and slab_data['min_value'] >= slab_data['max_value']:
                    raise ValidationError("Slab end value should be greater than slab start value")
                if slab_data['discount_value'] <= last_slab_discount_value:
                    raise ValidationError("Slab discount value should be greater than last slab discount value")
                last_slab_end_value = slab_data['max_value']
                last_slab_discount_value = slab_data['discount_value']
                if counter == non_empty_forms and slab_data['max_value'] != 0:
                    raise ValidationError("For last slab max value should be zero")
                is_first_slab = False
                counter = counter + 1


class SchemeShopMappingCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme Shop Mapping
    """
    shop_choice = Shop.objects.filter(shop_type__shop_type__in=['f', 'r'])
    scheme = forms.ModelChoiceField(queryset=Scheme.objects.all())
    shop = forms.ModelChoiceField(queryset=shop_choice,
                                  widget=autocomplete.ModelSelect2(url='shop-autocomplete'))
    start_date = forms.DateTimeField(widget=AdminDateWidget())
    end_date = forms.DateTimeField(widget=AdminDateWidget())

    def clean(self):
        data = self.cleaned_data
        shop = data['shop']
        start_date = data.get('start_date')
        end_date = data.get('end_date') + datetime.timedelta(hours=23, minutes=59, seconds=59)
        active_mapping = get_active_mappings(shop.id)
        for active_map in active_mapping:
            if active_map and active_map.priority == data['priority'] and active_map.start_date == start_date \
                    and active_map.end_date == end_date:
                    raise ValidationError("Shop Id - {} already has an active {} mappings on same "
                                          "start date {} & end date {}"
                                          .format(shop.id, SchemeShopMapping.PRIORITY_CHOICE[data['priority']],
                                                  active_map.start_date.date(), active_map.end_date.date()))


            elif active_map and active_map.priority == data['priority']:
                # store previous scheme data in database & make it deactivate
                save_scheme_shop_mapping_data(active_map)
                active_map.is_active = False
                active_map.save()

        data['end_date'] = end_date
        scheme = data['scheme']
        if start_date < scheme.start_date:
            raise ValidationError('Start date cannot be earlier than scheme start date')

        if start_date.date() <= datetime.date.today():
            raise ValidationError('Start date cannot be equal to today or earlier than today')

        if start_date > scheme.end_date:
            raise ValidationError('Start date cannot be greater than scheme end date')

        if end_date > scheme.end_date:
            raise ValidationError('End Date cannot be greater than scheme end date')

        if end_date.date() <= start_date.date():
            raise ValidationError('End Date should be later than the Start Date')

        return data

    class Meta:
        model = SchemeShopMapping
        fields = ('scheme', 'shop', 'priority', 'is_active', 'start_date', 'end_date')


class UploadSchemeShopMappingForm(forms.Form):
    """
    Upload Scheme SHop Mapping Form
    """
    file = forms.FileField(label='Upload Scheme Shop Mapping CSV')

    class Meta:
        model = SchemeShopMapping

    def clean_file(self):
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        unique_data = []
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and row[5] == '' and \
                    row[6] == '':
                continue

            # Scheme ID
            if not row[0]:
                raise ValidationError(_(f"Row {row_id + 1} | Please provide 'Scheme ID'"))
            scheme = Scheme.objects.filter(id=row[0]).last()
            if not scheme:
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Scheme ID'"))
            if not scheme.is_active:
                raise ValidationError(_(f"Row {row_id + 1} | Inactive 'Scheme ID'"))
            if scheme.end_date.date() <= datetime.datetime.today().date():
                raise ValidationError(_(f"Row {row_id + 1} | Expired 'Scheme ID'. End Date Of Scheme Should Be"
                                        f" Greater Than Today"))

            # Shop
            if not row[2] or not Shop.objects.filter(id=row[2], shop_type__shop_type__in=['f', 'r']).exists():
                raise ValidationError(
                    _(f"Row {row_id + 1} | Invalid 'Shop Id', no retailer/franchise shop exists in the system with this"
                      f" ID."))

            # Priority
            if not row[4] or row[4] not in SchemeShopMapping.PRIORITY_CHOICE._identifier_map.keys():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Priority'"))

            # Start Date
            if not row[5]:
                raise ValidationError(_(f"Row {row_id + 1} | Please Provide Shop Mapping Start Date"))
            start_date = isDateValid(row[5], "%Y-%m-%d")
            if not start_date:
                raise ValidationError(_(f"Row {row_id + 1} | Please Provide A Valid Shop Mapping Start Date"))
            start_date = start_date.date()
            if start_date < scheme.start_date.date():
                raise ValidationError(_(f"Row {row_id + 1} | Shop Mapping Start Date Should Be Greater Than Or Equal To"
                                        f" Scheme Start Date"))
            if start_date <= datetime.datetime.today().date():
                raise ValidationError(_(f"Row {row_id + 1} | Shop Mapping Start Date Should Be Greater Than Today"))

            # End Date
            if not row[6]:
                raise ValidationError(_(f"Row {row_id + 1} | Please Provide Shop Mapping End Date"))
            end_date = isDateValid(row[6], "%Y-%m-%d")
            if not end_date:
                raise ValidationError(_(f"Row {row_id + 1} | Please Provide A Valid Shop Mapping End Date"))
            end_date = end_date.date()
            if end_date <= start_date:
                raise ValidationError(_(f"Row {row_id + 1} | Shop Mapping End Date Should Be Greater Than Shop Mapping"
                                        f" Start Date"))
            if end_date > scheme.end_date.date():
                raise ValidationError(_(f"Row {row_id + 1} | Shop Mapping End Date Should Be Less Than Equal To Scheme"
                                        f" End Date"))

            # Scheme Shop Mapping
            if SchemeShopMapping.objects.filter(shop_id=row[2], is_active=True,
                                                priority=SchemeShopMapping.PRIORITY_CHOICE._identifier_map[row[4]],
                                                start_date__date=start_date, end_date__date=end_date).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Shop Mapping For Shop {row[2]} Already Active For Priority"
                                        f" {row[4]}, Start Date {row[5]} and End Date {row[6]}"))

            unique_key = str(row[2]) + str(row[4])
            if unique_key in unique_data:
                raise ValidationError(
                    _(f"Row {row_id + 1} | Multiple Entries In Sheet For Shop {row[2]} And Priority {row[4]}"))

            unique_data += [unique_key]
        return self.cleaned_data['file']
