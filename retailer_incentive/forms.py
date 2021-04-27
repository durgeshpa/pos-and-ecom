import codecs
import csv
import datetime
import logging

from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, BaseInlineFormSet
from django.utils.translation import gettext_lazy as _

from retailer_incentive.models import Scheme, SchemeSlab, SchemeShopMapping
from retailer_incentive.utils import get_active_mappings
from shops.models import Shop

info_logger = logging.getLogger('file-info')


class SchemeCreationForm(forms.ModelForm):
    """
    This class is used to create the Scheme
    """

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

        if instance.id:
            self.fields['name'].disabled = True
            self.fields['start_date'] = forms.DateTimeField()
            self.fields['start_date'].disabled = True
            self.fields['end_date'] = forms.DateTimeField()
            self.fields['end_date'].disabled = True

    def clean(self):
        data = self.cleaned_data
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date < datetime.datetime.today():
            raise ValidationError('Start date cannot be earlier than today')

        if end_date <= start_date:
            raise ValidationError('End Date should be later than the Start Date')

        if not self.instance.id:
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

    def clean(self):
        data = self.cleaned_data
        shop = data['shop']
        active_mappings = get_active_mappings(shop.id)

        for active_mapping in active_mappings:
            if active_mapping.priority == data['priority'] and active_mapping.start_date == data['start_date']\
                    and active_mapping.end_date == data['end_date']:
                raise ValidationError("Shop Id - {} already has an active {} mappings on same "
                                      "start date {} & end date {}"
                                      .format(shop.id, SchemeShopMapping.PRIORITY_CHOICE[data['priority']],
                                              active_mapping.start_date, active_mapping.end_date))
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        scheme = data['scheme']
        if start_date < scheme.start_date:
            raise ValidationError('Start date cannot be earlier than scheme start date')

        if start_date < datetime.datetime.today():
            raise ValidationError('Start date cannot be earlier than today')

        if start_date > scheme.end_date:
            raise ValidationError('Start date cannot be greater than scheme end date')

        if end_date > scheme.end_date:
            raise ValidationError('End Date cannot be greater than scheme end date')

        if end_date < start_date:
            raise ValidationError('End Date should be greater than the Start Date')

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
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '':
                continue
            if not row[0] or not Scheme.objects.filter(id=row[0], is_active=True,
                                                       end_date__gte=datetime.datetime.today()).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Scheme ID'"))
            if not row[2] or not Shop.objects.filter(id=row[2], shop_type__shop_type__in=['f','r']).exists():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Shop Id', no retailer/franchise shop exists in the system with this ID."))
            if not row[4] or row[4] not in SchemeShopMapping.PRIORITY_CHOICE._identifier_map.keys():
                raise ValidationError(_(f"Row {row_id + 1} | Invalid 'Priority'"))

            shop_id = row[2]
            priority = SchemeShopMapping.PRIORITY_CHOICE._identifier_map[row[4]]

            active_mappings = get_active_mappings(shop_id)
            if active_mappings.count() >= 2:
                info_logger.info("Shop Id - {} already has 2 active mappings".format(shop_id))
                raise ValidationError(_(f"Row {row_id + 1} | This shop already has 2 active mappings"))
            existing_active_mapping = active_mappings.last()
            if existing_active_mapping and existing_active_mapping.priority == priority:
                info_logger.info("Shop Id - {} already has an active {} mappings".format(shop_id, row[4]))
                raise ValidationError(_(f"Row {row_id + 1} | This shop already has an active {row[4]} mappings"))
            elif existing_active_mapping and existing_active_mapping.scheme_id == int(row[0]):
                info_logger.info("Shop Id - {} already mapped with scheme id {}".format(shop_id, row[0]))
                raise ValidationError(_(f"Row {row_id + 1} | This shop is already mapped with scheme id {row[0]}"))
        return self.cleaned_data['file']
