import logging
import collections
import re
import csv
import codecs
from django import forms
from datetime import datetime
from .models import Bin, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup, StockMovementCSVUpload,\
    InventoryType, InventoryState, BIN_TYPE_CHOICES, Audit
from products.models import Product, ProductPrice
from shops.models import Shop
from gram_to_brand.models import GRNOrderProductMapping
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from .common_functions import create_batch_id
from retailer_to_sp.models import OrderedProduct
from django.db import transaction
from .common_functions import cancel_ordered, cancel_shipment, cancel_returned
from dal import autocomplete
# Logger
info_logger = logging.getLogger('file-info')
error_logger = logging.getLogger('file-error')
debug_logger = logging.getLogger('file-debug')

warehouse_choices = Shop.objects.filter(shop_type__shop_type='sp')


class BulkBinUpdation(forms.Form):
    info_logger.info("Bulk Bin Update Form has been called.")
    file = forms.FileField(label='Select a file')

    def clean_file(self):
        info_logger.info("Validation for File format for Bulk Bin Upload.")
        file = self.cleaned_data['file']
        if not file.name[-4:] == '.csv':
            error_logger.error("File Format is not correct.")
            raise forms.ValidationError("Only .CSV file accepted.")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        form_data_list = []
        for row_id, row in enumerate(reader):
            info_logger.info("xls data validation has been started.")

            if len(row[0]) > 50:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + "Warehouse Name can't exceed more then 50 chars."))

            if not row[2]:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + "Bin Type must not be empty."))

            if not row[2] in ['PA', 'SR', 'HD']:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + "Bin Type must be start with PA, SR and HD."))

            # Bin ID Validation
            bin_validation, message = bin_id_validation(row[3], row[2])
            if bin_validation is False:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + message))

            if not row[1]:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + "Warehouse field must not be empty. It should be Integer."))

            if not Shop.objects.filter(pk=row[1]).exists():
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + "Warehouse id does not exist in the system."))

            else:
                warehouse = Shop.objects.filter(id=int(row[1]))
                if warehouse.exists():
                    if Bin.objects.filter(warehouse=warehouse.last(), bin_id=row[3]).exists():
                        raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + 'Same Bin ID is exists in a system with same Warehouse. Please re-verify at your end.'))

            info_logger.info("Validation of File format successfully passed.")
            form_data_list.append(row)
        return form_data_list


class BinForm(forms.ModelForm):
    info_logger.info("Bin Form has been called.")
    bin_id = forms.CharField(required=True, max_length=16)
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    bin_type = forms.ChoiceField(choices=BIN_TYPE_CHOICES)

    class Meta:
        model = Bin
        fields = ['warehouse', 'bin_id', 'bin_type', 'is_active', ]

    def clean_bin_id(self):
        bin_validation, message = bin_id_validation(self.cleaned_data['bin_id'], self.data['bin_type'])
        if bin_validation is False:
            raise ValidationError(_(message))
        if self.instance.bin_id is None:
            bin_obj = Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id=self.cleaned_data['bin_id'])
        else:
            bin_obj = Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id=self.instance.bin_id)
        if Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id = self.cleaned_data['bin_id']).exists():
            if bin_obj[0].bin_id == self.cleaned_data['bin_id']:
                try:
                    if int(bin_obj[0].id) == int(self.instance.id):
                        pass
                except:
                    raise ValidationError(
                        _("Duplicate Data ! Warehouse with same Bin Id is already exists in the system."))
            else:
                raise ValidationError(_("Duplicate Data ! Warehouse with same Bin Id is already exists in the system."))
        return self.cleaned_data['bin_id']

    def __init__(self, *args, **kwargs):
        super(BinForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance:
            if instance.is_active is True:
                self.fields['is_active'].disabled = True


def bin_id_validation(bin_id, bin_type):
    if not bin_id:
        return False, "Bin ID must not be empty."

    if not len(bin_id) == 16:
        return False, 'Bin Id min and max char limit is 16.Example:-B2BZ01SR001-0001'

    if not bin_id[0:3] in ['B2B', 'B2C']:
        return False, 'First three letter should be start with either B2B and B2C.Example:-B2BZ01SR001-0001'

    if not bin_id[3] in ['Z']:
        return False, 'Zone should be start with char Z.Example:-B2BZ01SR001-0001'

    if not bool(re.match('^[0-9]+$', bin_id[4:6]) and not bin_id[4:6] == '00'):
        return False, 'Zone number should be start in between 01 to 99.Example:-B2BZ01SR001-0001'

    if not bin_id[6:8] in ['SR', 'PA', 'HD']:
        return False, 'Rack type should be start with either SR, PA and HD only.Example:-B2BZ01SR001-0001'

    else:
        if not bin_id[6:8] == bin_type:
            return False, 'Type of Rack and Bin type should be same.'

    if not bool(re.match('^[0-9]+$', bin_id[8:11]) and not bin_id[8:11] == '000'):
        return False, 'Rack number should be start in between 000 to 999.Example:- B2BZ01SR001-0001'

    if not bin_id[11] in ['-']:
        return False, 'Only - allowed in between Rack number and Bin Number.Example:-B2BZ01SR001-0001'

    if not bool(re.match('^[0-9]+$', bin_id[12:16]) and not bin_id[12:16] == '0000'):
        return False, 'Bin number should be start in between 0000 to 9999. Example:-B2BZ01SR001-0001'

    return True, "Bin Id validation successfully passed."


class InForm(forms.ModelForm):
    info_logger.info("In Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = In
        fields = '__all__'


class PutAwayForm(forms.ModelForm):
    info_logger.info("Put Away Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Putaway
        fields = ['warehouse','putaway_type', 'putaway_type_id', 'sku', 'batch_id','quantity','putaway_quantity']

    def __init__(self, *args, **kwargs):
        super(PutAwayForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        # self.fields['putaway_quantity'].initial = 0
        # self.fields['putaway_quantity'].disabled = True


class PutAwayBinInventoryForm(forms.ModelForm):
    info_logger.info("Put Away Bin Inventory Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    bin_id = forms.CharField()

    class Meta:
        model = PutawayBinInventory
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(PutAwayBinInventoryForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance:
            # self.fields['putaway_quantity'].initial = 0
            if instance.putaway_status is True:
                self.fields['putaway_status'].disabled = True
                self.fields['bin_id'].initial = instance.bin.bin.bin_id
                self.fields['bin_id'].disabled = True
                self.fields['bin'].initial = instance.bin.bin.bin_id
                self.fields['bin'].disabled = True
            if instance.putaway_status is False:
                self.fields['bin_id'].initial = instance.bin.bin.bin_id
                self.fields['bin_id'].disabled = True
                self.fields['bin'] = forms.ModelChoiceField(queryset=Bin.objects.filter(
                    warehouse=instance.warehouse, is_active=True).distinct(), widget=autocomplete.ModelSelect2())
    def clean_bin(self):
        if self.instance.putaway_status is True:
            self.fields['putaway_status'].disabled = True
            self.fields['bin_id'].initial = self.instance.bin.bin.bin_id
            self.fields['bin_id'].disabled = True
            self.fields['bin'].initial = self.instance.bin.bin.bin_id
            self.fields['bin'].disabled = True
        if self.instance.putaway_status is False:
            self.fields['bin_id'].initial = self.instance.bin.bin.bin_id
            self.fields['bin_id'].disabled = True
            self.fields['bin'] = forms.ModelChoiceField(queryset=Bin.objects.filter(
                warehouse=self.instance.warehouse).distinct(), widget=autocomplete.ModelSelect2())
        bin_obj = BinInventory.objects.filter(
            bin=Bin.objects.filter(bin_id=self.cleaned_data['bin'], warehouse=self.instance.warehouse).last(),
            warehouse=self.instance.warehouse).last()
        if bin_obj:
            return bin_obj
        else:
            bin_exp_obj = BinInventory.objects.filter(warehouse=self.instance.warehouse,
                                                      bin=Bin.objects.filter(
                                                          bin_id=self.cleaned_data['bin'].bin_id,
                                                      warehouse=self.instance.warehouse).last(),
                                                      sku=Product.objects.filter(
                                                          product_sku=self.instance.sku_id).last(),
                                                      batch_id=self.instance.batch_id)
            if not bin_exp_obj.exists():
                bin_in_obj = BinInventory.objects.filter(warehouse=self.instance.warehouse,
                                                         sku=Product.objects.filter(
                                                             product_sku=self.instance.sku_id).last())
                for bin_in in bin_in_obj:
                    if not (bin_in.batch_id == self.instance.batch_id):
                        if bin_in.bin.bin_id == self.cleaned_data['bin'].bin_id:
                            if bin_in.quantity == 0:
                                pass
                            else:
                                raise forms.ValidationError(" You can't perform this action,"
                                                            " Non zero qty of more than one Batch ID of a single"
                                                            " SKU can’t be saved in the same Bin ID.")
                with transaction.atomic():
                    initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
                    bin_obj, created = BinInventory.objects.get_or_create(warehouse=self.instance.warehouse, bin=self.cleaned_data['bin'], sku=Product.objects.filter(
                                                      product_sku=self.instance.sku_id).last(),
                                                       batch_id=self.instance.batch_id,
                                                       inventory_type=initial_type[0], quantity=int(0),
                                                       in_stock=True)
                    if created:
                        return bin_obj


    def clean(self):
        with transaction.atomic():
            try:
                if self.cleaned_data['bin'] is None:
                    raise forms.ValidationError("You can't perform this action, Please select one of the Bin ID from drop"
                                                "down menu.")
            except:
                raise forms.ValidationError("You can't perform this action, Please select one of the Bin ID from drop"
                                            "down menu.")
            if self.cleaned_data['bin'].bin.bin_id == 'V2VZ01SR001-0001':
                raise forms.ValidationError("You can't assign this BIN ID, This is a Virtual Bin ID.")
            if self.cleaned_data['putaway_status'] is False:
                raise forms.ValidationError("You can't perform this action, Please mark PutAway status is Active.")
            if PutawayBinInventory.objects.filter(id=self.instance.id)[0].putaway_status is True:
                raise forms.ValidationError("You can't perform this action, PutAway has already done.")
            else:
                bin_in_obj = BinInventory.objects.filter(warehouse=self.instance.warehouse,
                                                         sku=Product.objects.filter(
                                                             product_sku=self.instance.sku_id).last())
                for bin_in in bin_in_obj:
                    if not (bin_in.batch_id == self.instance.batch_id):
                        if bin_in.bin.bin_id == self.cleaned_data['bin'].bin.bin_id:
                            if bin_in.quantity == 0:
                                pass
                            else:
                                raise forms.ValidationError(" You can't perform this action,"
                                                            " Non zero qty of more than one Batch ID of a single"
                                                            " SKU can’t be saved in the same Bin ID.")
                bin_id = self.cleaned_data['bin']
                if self.instance.putaway_type == 'Order_Cancelled':
                    ordered_inventory_state = 'ordered',
                    initial_stage = InventoryState.objects.filter(inventory_state='ordered').last(),
                    cancel_ordered(self.request.user, self.instance, ordered_inventory_state, initial_stage, bin_id)

                elif self.instance.putaway_type == 'Pickup_Cancelled':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(self.request.user, self.instance, ordered_inventory_state, initial_stage, bin_id)

                elif self.instance.putaway_type == 'Shipment_Cancelled':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(self.request.user, self.instance, ordered_inventory_state, initial_stage, bin_id)

                elif self.instance.putaway_type == 'PAR_SHIPMENT':
                    ordered_inventory_state = 'picked',
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    shipment_obj = OrderedProduct.objects.filter(
                        order__order_no=self.instance.putaway.putaway_type_id)[0].rt_order_product_order_product_mapping.all()
                    cancel_shipment(self.request.user, self.instance, ordered_inventory_state, initial_stage, shipment_obj,
                                    bin_id)

                elif self.instance.putaway_type == 'RETURNED':
                    ordered_inventory_state = 'shipped',
                    initial_stage = InventoryState.objects.filter(inventory_state='shipped').last(),
                    shipment_obj = OrderedProduct.objects.filter(
                        invoice__invoice_no=self.instance.putaway.putaway_type_id)[0].rt_order_product_order_product_mapping.all()
                    cancel_returned(self.request.user, self.instance, ordered_inventory_state, initial_stage, shipment_obj,
                                    bin_id)


class BinInventoryForm(forms.ModelForm):
    info_logger.info("Bin Inventory Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = BinInventory
        fields = '__all__'


class OutForm(forms.ModelForm):
    info_logger.info("Out Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)

    class Meta:
        model = Out
        fields = '__all__'


class PickupForm(forms.ModelForm):
    info_logger.info("Pickup Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    pickup_quantity = forms.IntegerField(initial=0)

    class Meta:
        model = Pickup
        fields = '__all__'


class StockMovementCSVUploadAdminForm(forms.ModelForm):
    """
      Stock Movement Admin Form
      """

    class Meta:
        model = StockMovementCSVUpload
        fields = ('inventory_movement_type',)


class StockMovementCsvViewForm(forms.Form):
    """
    This Form class is used to upload csv for different stock movement
    """
    file = forms.FileField()

    def clean_file(self):
        """

        :return: Form is valid otherwise validation error message
        """
        # Validate to check the file format, It should be csv file.
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted.")

        if self.data['inventory_movement_type'] == '2':
            data = validation_bin_stock_movement(self)

        elif self.data['inventory_movement_type'] == '3':
            data = validation_stock_correction(self)

        elif self.data['inventory_movement_type'] == '4':
            data = validation_warehouse_inventory(self)
        else:
            raise forms.ValidationError("Inventory movement type is not correct, Please re-verify it at"
                                        " your end .")

        return data


def validation_bin_stock_movement(self):
    reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
    first_row = next(reader)
    # list which contains csv data and pass into the view file
    form_data_list = []
    for row_id, row in enumerate(reader):

        # validation for shop id, it should be numeric.
        if not row[0] or not re.match("^[\d]*$", row[0]):
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        # validation for shop id to check that is exist or not in the database
        if not Shop.objects.filter(pk=row[0]).exists():
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)
        # validate for product sku
        if not row[1]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for product sku is exist or not
        if not Product.objects.filter(product_sku=row[1]).exists():
            raise ValidationError(_('Invalid Product SKU at Row number [%(value)s].'
                                    'Product SKU does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validate for Batch id
        if not row[2]:
            raise ValidationError(_('Batch Id can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for Batch id is exist or not
        if not GRNOrderProductMapping.objects.filter(batch_id=row[2]).exists():
            raise ValidationError(_('Invalid Batch Id at Row number [%(value)s].'
                                    'Batch Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validate for Initial Bin Id
        if not row[3]:
            raise ValidationError(_('Initial Bin Id can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for Initial Bin Id  is exist or not
        if not Bin.objects.filter(bin_id=row[3]).exists():
            raise ValidationError(_('Invalid Initial Bin Id at Row number [%(value)s]. '
                                    'Initial Bin Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validate for Final Bin Id
        if not row[4]:
            raise ValidationError(_('Final Bin Id can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for Final Bin Id  is exist or not
        if not Bin.objects.filter(bin_id=row[4]).exists():
            raise ValidationError(_('Invalid Final Bin Id at Row number [%(value)s]. '
                                    'Final Bin Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validate for Initial Type
        if not row[5]:
            raise ValidationError(_('Initial Type can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for Initial Type is exist or not
        if not row[5] in ['normal', 'expired', 'damaged', 'discarded', 'disposed']:
            raise ValidationError(_('Invalid Initial Type at Row number [%(value)s].'
                                    'Initial Type does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validate for Final Type
        if not row[6]:
            raise ValidationError(_('Final Type can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1}, )

        # validate for Final Type is exist or not
        if not row[6] in ['normal', 'expired', 'damaged', 'discarded', 'disposed']:
            raise ValidationError(_('Invalid Final Type at Row number [%(value)s]. '
                                    'Final Type does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )

        # validate for quantity
        if not row[7] or not re.match("^[\d]*$", row[7]):
            raise ValidationError(_('Invalid Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        # validation for Warehouse, Sku, Batch id and inventory type is exist or not in Bin Inventory model
        if not BinInventory.objects.filter(warehouse=row[0], sku=row[1], batch_id=row[2],
                                           inventory_type__inventory_type=row[5]).exists():
            raise ValidationError(_('Data is not valid for [%(value)s]. '
                                    'Initial Inventory type [%(initial_inventory_type)s] is not exist for'
                                    ' [%(warehouse)s],'' [%(sku)s],'' [%(batch_id)s].'),
                                  params={'value': row_id + 1, 'warehouse': row[0], 'sku': row[1],
                                          'batch_id': row[2], 'initial_inventory_type': row[5]},)
        else:
            # validation for quantity is greater than available quantity
            bin_inventory = BinInventory.objects.filter(warehouse=row[0], sku=row[1], batch_id=row[2],
                                                        inventory_type__inventory_type=row[5])
            quantity = bin_inventory[0].quantity
            if quantity < int(row[7]):
                raise ValidationError(_('Quantity is greater than Available Quantity [%(value)s].'
                                        ' It should be less then Available Quantity.'),
                                      params={'value': row_id + 1}, )

        form_data_list.append(row)

    return form_data_list


def validation_stock_correction(self):
    reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
    first_row = next(reader)
    # list which contains csv data and pass into the view file
    form_data_list = []
    unique_data_list = []
    for row_id, row in enumerate(reader):
        if '' in row:
            if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                    row[5] == '' and row[6] == '' and row[7] == '' and row[8] == ''):
                continue
        # validation for shop id, it should be numeric.
        if not row[0] or not re.match("^[\d]*$", row[0]):
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 2}, )

        # validation for shop id to check that is exist or not in the database
        if not Shop.objects.filter(pk=row[0]).exists():
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 2}, )

        # validate for product name
        if not row[1]:
            raise ValidationError(_('Product Name can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 2}, )

        # validate for product sku
        if not row[2]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 2}, )

        # validate for product sku is exist or not
        if not Product.objects.filter(product_sku=row[2]).exists():
            raise ValidationError(_('Invalid Product SKU at Row number [%(value)s].'
                                    'Product SKU does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 2}, )

        # validate for expiry_date
        if not row[3]:
            raise ValidationError(_(
                "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date can not be empty."))
        try:
            # if expiry date is "dd/mm/yy"
            if datetime.strptime(row[3], '%d/%m/%y'):
                pass
        except:
            try:
                # if expiry date is "dd/mm/yyyy"
                if datetime.strptime(row[3], '%d/%m/%Y'):
                    pass
                else:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date format is not correct,"
                                                                       " It should be DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY and DD-MM-YY format,"
                                                                       " Example:-11/07/2020, 11/07/20,"
                                                                       "11-07-2020 and 11-07-20."))

            except:
                try:
                    # if expiry date is "dd-mm-yy"
                    if datetime.strptime(row[3], '%d-%m-%y'):
                        pass

                except:
                    try:
                        # if expiry date is "dd-mm-yyyy"
                        if datetime.strptime(row[3], '%d-%m-%Y'):
                            pass
                    except:
                        # raise validation error
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date format is not correct,"
                                                                           " It should be DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY and DD-MM-YY format,"
                                                                           " Example:-11/07/2020, 11/07/20,"
                                                                           " 11-07-2020 and 11-07-20."))

        # validate for bin id
        if not row[4]:
            raise ValidationError(_('Bin Id can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 2}, )


        # validate for bin id exist or not
        if not Bin.objects.filter(bin_id=row[4], is_active=True, warehouse=Shop.objects.filter(pk=row[0]).last()).exists():
            raise ValidationError(_('Invalid Bin Id at Row number [%(value)s]. '
                                    'Bin Id is not associated with Warehouse .Please re-verify at your end.'),
                                  params={'value': row_id + 2}, )

        # validation for quantity
        if not row[5] or not re.match("^[\d]*$", row[5]):
            raise ValidationError(_('Invalid Normal Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 2}, )

        if not row[6] or not re.match("^[\d]*$", row[6]):
            raise ValidationError(_('Invalid Damaged Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 2}, )

        if not row[7] or not re.match("^[\d]*$", row[7]):
            raise ValidationError(_('Invalid Expired Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 2}, )

        if not row[8] or not re.match("^[\d]*$", row[8]):
            raise ValidationError(_('Invalid Missing Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 2}, )

        if int(row[5]) < 0:
            raise ValidationError(_('Invalid Normal Quantity at Row number [%(value)s]. It should be greater then 0.'),
                                  params={'value': row_id + 2}, )
        if int(row[6]) < 0:
            raise ValidationError(_('Invalid Damaged Quantity at Row number [%(value)s]. It should be greater then 0.'),
                                  params={'value': row_id + 2}, )
        if int(row[7]) < 0:
            raise ValidationError(_('Invalid Expired Quantity at Row number [%(value)s]. It should be greater then 0.'),
                                  params={'value': row_id + 2}, )
        if int(row[8]) < 0:
            raise ValidationError(_('Invalid Missing Quantity at Row number [%(value)s]. It should be greater then 0.'),
                                  params={'value': row_id + 2}, )

        # to get the date format
        try:
            expiry_date = datetime.strptime(row[3], '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            try:
                expiry_date = datetime.strptime(row[3], '%d-%m-%Y').strftime('%Y-%m-%d')
            except:
                try:
                    expiry_date = datetime.strptime(row[3], '%d-%m-%y').strftime('%Y-%m-%d')
                except:
                    expiry_date = datetime.strptime(row[3], '%d/%m/%y').strftime('%Y-%m-%d')

        # to validate normal qty for past expired date
        if expiry_date < datetime.today().strftime("%Y-%m-%d"):
            if int(row[5]) > 0:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(
                        row_id + 2) + "," + "For Past expiry date, the normal qty (final)"
                                            " should be 0."))

        # to validate normal qty for past damaged date
        if expiry_date < datetime.today().strftime("%Y-%m-%d"):
            if int(row[6]) > 0:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(
                        row_id + 2) + "," + "For Past expiry date, the damaged qty (final)"
                                            " should be 0."))

        # to validate expired qty for future expired date
        if expiry_date > datetime.today().strftime("%Y-%m-%d"):
            if int(row[7]) > 0:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "For Future expiry date, the expired qty "
                                                                   " should be 0."))

        # to get object from GRN Order Product Mapping
        sku = row[2]
        # create batch id
        batch_id = create_batch_id(sku, row[3])
        bin_exp_obj = BinInventory.objects.filter(warehouse=row[0],
                                                  bin=Bin.objects.filter(bin_id=row[4]).last(),
                                                  sku=Product.objects.filter(
                                                      product_sku=row[2]).last(),
                                                  batch_id=batch_id)
        # if combination of expiry date and sku is not exist in GRN Order Product Mapping
        if not bin_exp_obj.exists():
            bin_in_obj = BinInventory.objects.filter(
                warehouse=row[0], sku=Product.objects.filter(product_sku=row[2]).last())
            for bin_in in bin_in_obj:
                sku = row[1]
                # create batch id
                if not (bin_in.batch_id == create_batch_id(sku, row[3])):
                    if bin_in.bin.bin_id == row[4]:
                        if bin_in.quantity == 0:
                            pass
                        else:
                            raise ValidationError(_(
                                "Issue in Row" + " " + str(row_id + 2) + "," + "Non zero qty of 2 Different"
                                                                               " Batch ID/Expiry date for same SKU"
                                                                               " can’t save in the same Bin."))


        form_data_list.append(row)
        unique_data_list.append(row[0] + row[2] + row[3] + row[4])
    duplicate_data_list = ([item for item, count in collections.Counter(unique_data_list).items() if count > 1])
    if len(duplicate_data_list) > 0:
        raise ValidationError(_(
            "Alert ! Duplicate Data. Same SKU, Expiry Date, Bin ID and Inventory Movement Type is exist in the csv,"
            " please re-verify at your end."))

    return form_data_list


def validation_warehouse_inventory(self):
    reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
    first_row = next(reader)
    # list which contains csv data and pass into the view file
    form_data_list = []
    for row_id, row in enumerate(reader):

        # validation for shop id, it should be numeric.
        if not row[0] or not re.match("^[\d]*$", row[0]):
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        # validation for shop id to check that is exist or not in the database
        if not Shop.objects.filter(pk=row[0]).exists():
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )

        # validation for product sku
        if not row[1]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1}, )

        # validation for product sku is exist or not
        if not Product.objects.filter(product_sku=row[1]).exists():
            raise ValidationError(_('Invalid Product SKU at Row number [%(value)s].'
                                    'Product SKU does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )

        # validation for Initial stage
        if not row[2]:
            raise ValidationError(_('Initial State can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1}, )

        # validation for Initial stage is exist or not
        if not row[2] in ['available', 'reserved', 'shipped']:
            raise ValidationError(_('Invalid Initial State at Row number [%(value)s]. '
                                    'Initial State does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )

        # validation for Final stage
        if not row[3]:
            raise ValidationError(_('Final State can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1}, )

        # validation for Final stage is exist or not
        if not row[3] in ['available', 'reserved', 'shipped']:
            raise ValidationError(_('Invalid Final State at Row number [%(value)s].'
                                    'Final State does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )

        # validation for Inventory Type
        if not row[4]:
            raise ValidationError(_('Inventory Type can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validation for Inventory Type is exist or not
        if not row[4] in ['normal', 'expired', 'damaged', 'discarded', 'disposed']:
            raise ValidationError(_('Invalid Inventory Type at Row number [%(value)s].'
                                    'Inventory Type does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)

        # validation for quantity
        if not row[5] or not re.match("^[\d]*$", row[5]):
            raise ValidationError(_('Invalid Quantity at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        form_data_list.append(row)
    return form_data_list


class DownloadAuditAdminForm(forms.Form):
    """
      Download Audit Form
    """
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, label='Select Warehouse')
    file = forms.FileField(label='Upload CSV List for which Audit is to be performed')

    class Meta:
        model = Audit
        fields = ('warehouse',)

    def clean_file(self):
        info_logger.info("Validation for File format for Audit Download.")
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        # list which contains csv data and pass into the view file
        form_data_list = []
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if row[0] == '':
                    continue
            try:
                if not row[0]:
                    raise ValidationError(_("Issue in Row" + " " + str(row_id + 2) + "," + "SKU can not be empty."))
            except:
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 2) + "," + "SKU can not be empty."))

            if not Product.objects.filter(product_sku=row[0]):
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 2) + "," + "SKU is not valid,"
                                                                                       " Please re-verify at your end."))

            if not BinInventory.objects.filter(warehouse=self.data['warehouse'],
                                               sku=Product.objects.filter(product_sku=row[0])[0]):
                raise ValidationError(_("Issue in Row" + " " + str(row_id + 2) + "," + "SKU id is not associated"
                                                                                       " with selected warehouse."))
            form_data_list.append(row)

        return form_data_list


class UploadAuditAdminForm(forms.Form):
    """
      Upload Audit Form
    """
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, label='Select Warehouse')
    file = forms.FileField(label='Upload Audit Inventory list')

    class Meta:
        model = Audit
        fields = ('warehouse',)

    def clean_file(self):
        info_logger.info("Validation for File format for Audit Upload.")
        if not self.cleaned_data['file'].name[-4:] in ('.csv'):
            raise forms.ValidationError("Sorry! Only .csv file accepted.")

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
        first_row = next(reader)
        # list which contains csv data and pass into the view file
        form_data_list = []
        unique_data_list = []
        for row_id, row in enumerate(reader):
            if len(row) == 0:
                continue
            if '' in row:
                if (row[0] == '' and row[1] == '' and row[2] == '' and row[3] == '' and row[4] == '' and
                    row[5] == '' and row[6] == '' and row[7] == '' and row[8] == '' and row[9] == '' and
                        row[10] == '' and row[11] == '' and row[12] == ''):
                    continue
            # to validate warehouse id is empty or not
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Warehouse ID can not be empty."))

            # to validate warehouse id is exist in the database
            if not Shop.objects.filter(pk=row[0]).exists():
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Warehouse ID doesn't exist in the system."))

            # to validate sku id is empty or not
            if not row[1]:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "SKU ID can not be empty."))

            # to validate sku id is exist in the database
            if not Product.objects.filter(product_sku=row[1][-17:]).exists():
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "SKU ID is not exist in the system."))

            # to validate mrp is empty or contains the number
            if not row[2] or not re.match("^[\d]*$", row[2]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Product of MRP can not be empty or string type."))

            # if not ProductPrice.objects.filter(product__product_sku=row[1][-17:], seller_shop=row[0]).exists():
            #     raise ValidationError(_(
            #         "Issue in Row" + " " + str(row_id + 2) + "," + "This Product is not associated with this warehouse."))

            # to validate expiry date is empty or not and validate the correct format
            if not row[3]:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date can not be empty."))
            try:
                # if expiry date is "dd/mm/yy"
                if datetime.strptime(row[3], '%d/%m/%y'):
                    pass
            except:
                try:
                    # if expiry date is "dd/mm/yyyy"
                    if datetime.strptime(row[3], '%d/%m/%Y'):
                        pass
                    else:
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date format is not correct,"
                                                                           " It should be DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY and DD-MM-YY format,"
                                                                           " Example:-11/07/2020, 11/07/20,"
                                                                           "11-07-2020 and 11-07-20."))

                except:
                    try:
                        # if expiry date is "dd-mm-yy"
                        if datetime.strptime(row[3], '%d-%m-%y'):
                            pass

                    except:
                        try:
                            # if expiry date is "dd-mm-yyyy"
                            if datetime.strptime(row[3], '%d-%m-%Y'):
                                pass
                        except:
                            # raise validation error
                            raise ValidationError(_(
                                "Issue in Row" + " " + str(row_id + 2) + "," + "Expiry date format is not correct,"
                                                                               " It should be DD/MM/YYYY, DD/MM/YY, DD-MM-YYYY and DD-MM-YY format,"
                                                                               " Example:-11/07/2020, 11/07/20,"
                                                                               " 11-07-2020 and 11-07-20."))

            # to validate BIN ID is empty or not
            if not row[4]:
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Bin ID can not be empty."))

            # to validate BIN ID is exist in the database
            if not Bin.objects.filter(bin_id=row[4], is_active=True).exists():
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Bin ID is not activated in the system."))

            if not Bin.objects.filter(bin_id=row[4], warehouse=row[0]).exists():
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Bin ID is not associated with given warehouse."))

            # to validate normal initial quantity is empty or contains the number
            if not row[5] or not re.match("^[\d]*$", row[5]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Normal-Initial Qty can not be empty or string type."))

            # to validate damaged initial quantity is empty or contains the number
            if not row[6] or not re.match("^[\d]*$", row[6]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Damaged-Initial Qty can not be empty or string type."))

            # to validate expired initial quantity is empty or contains the number
            if not row[7] or not re.match("^[\d]*$", row[7]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Expired-Initial Qty can not be empty or string type."))

            # to validate missing initial quantity is empty or contains the number
            if not row[8] or not re.match("^[\d]*$", row[8]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Missing-Initial Qty can not be empty or string type."))

            # to validate normal final quantity is empty or contains the number
            if not row[9] or not re.match("^[\d]*$", row[9]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Normal-Final Qty can not be empty or string type."))

            # to validate damaged final quantity is empty or contains the number
            if not row[10] or not re.match("^[\d]*$", row[10]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Damaged-Final Qty can not be empty or string type."))

            # to validate expired final quantity is empty or contains the number
            if not row[11] or not re.match("^[\d]*$", row[11]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Expired-Final Qty can not be empty or string type."))

            # to validate missing final quantity is empty or contains the number
            if not row[12] or not re.match("^[\d]*$", row[12]):
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," + "Missing-Final Qty can not be empty or string type."))

            # to get the date format
            try:
                expiry_date = datetime.strptime(row[3], '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                try:
                    expiry_date = datetime.strptime(row[3], '%d-%m-%Y').strftime('%Y-%m-%d')
                except:
                    try:
                        expiry_date = datetime.strptime(row[3], '%d-%m-%y').strftime('%Y-%m-%d')
                    except:
                        expiry_date = datetime.strptime(row[3], '%d/%m/%y').strftime('%Y-%m-%d')

            # to validate expired qty for future expired date
            if expiry_date > datetime.today().strftime("%Y-%m-%d"):
                if int(row[11]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(row_id + 2) + "," + "For Future expiry date, the expired qty (final)"
                                                                       " should be 0."))

            # to validate normal qty for past expired date
            if expiry_date < datetime.today().strftime("%Y-%m-%d"):
                if int(row[9]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(row_id + 2) + "," + "For Past expiry date, the normal qty (final)"
                                                                       " should be 0."))

            # to validate normal qty for past damaged date
            if expiry_date < datetime.today().strftime("%Y-%m-%d"):
                if int(row[10]) > 0:
                    raise ValidationError(_(
                        "Issue in Row" + " " + str(row_id + 2) + "," + "For Past expiry date, the damaged qty (final)"
                                                                       " should be 0."))

            # to get object from GRN Order Product Mapping
            sku = row[1][-17:]
            # create batch id
            batch_id = create_batch_id(sku, row[3])
            bin_exp_obj = BinInventory.objects.filter(warehouse=row[0],
                                                      bin=Bin.objects.filter(bin_id=row[4]).last(),
                                                      sku=Product.objects.filter(
                                                          product_sku=row[1][-17:]).last(),
                                                      batch_id=batch_id)
            # if combination of expiry date and sku is not exist in GRN Order Product Mapping
            if not bin_exp_obj.exists():
                bin_in_obj = BinInventory.objects.filter(
                    warehouse=row[0], sku=Product.objects.filter(product_sku=row[1][-17:]).last())
                for bin_in in bin_in_obj:
                    sku = row[1][-17:]
                    # create batch id
                    if not (bin_in.batch_id == create_batch_id(sku, row[3])):
                        if bin_in.bin.bin_id == row[4]:
                            if bin_in.quantity == 0:
                                pass
                            else:
                                raise ValidationError(_(
                                    "Issue in Row" + " " + str(row_id + 2) + "," + "Non zero qty of 2 Different"
                                                                                   " Batch ID/Expiry date for same SKU"
                                                                                   " can’t save in the same Bin."))

            # get the sum of normal quantity
            normal = BinInventory.objects.filter(Q(warehouse__id=row[0]),
                            Q(sku__id=Product.objects.filter(product_sku=row[1][-17:])[0].id),
                            Q(inventory_type__id=InventoryType.objects.filter(inventory_type='normal')[0].id),
                            Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')
            if normal is None:
                normal = 0

            # get the sum of damaged quantity
            damaged = BinInventory.objects.filter(Q(warehouse__id=row[0]),
                            Q(sku__id=Product.objects.filter(product_sku=row[1][-17:])[0].id),
                            Q(inventory_type__id=InventoryType.objects.filter(inventory_type='damaged')[0].id),
                            Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')
            if damaged is None:
                damaged = 0

            # get the sum of expired quantity
            expired = BinInventory.objects.filter(Q(warehouse__id=row[0]),
                            Q(sku__id=Product.objects.filter(product_sku=row[1][-17:])[0].id),
                            Q(inventory_type__id=InventoryType.objects.filter(inventory_type='expired')[0].id),
                            Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')

            if expired is None:
                expired = 0

            # get the sum of missing quantity
            missing = BinInventory.objects.filter(Q(warehouse__id=row[0]),
                            Q(sku__id=Product.objects.filter(product_sku=row[1][-17:])[0].id),
                            Q(inventory_type__id=InventoryType.objects.filter(inventory_type='missing')[0].id),
                            Q(quantity__gt=0)).aggregate(total=Sum('quantity')).get('total')
            if missing is None:
                missing = 0

            # sum of initial quantities
            initial_count = normal + damaged + expired + missing
            final_count = 0
            reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8'))
            first_row = next(reader)
            # iterate the row from initial to end
            for row_id_1, row_1 in enumerate(reader):
                if row_1[1] == row[1]:
                    # to validate normal final quantity is empty or contains the number
                    if not row_1[9] or not re.match("^[\d]*$", row_1[9]):
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(
                                row_id_1 + 2) + "," + "Normal-Final Qty can not be empty or string type."))

                    # to validate damaged final quantity is empty or contains the number
                    if not row_1[10] or not re.match("^[\d]*$", row_1[10]):
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(
                                row_id_1 + 2) + "," + "Damaged-Final Qty can not be empty or string type."))

                    # to validate expired final quantity is empty or contains the number
                    if not row_1[11] or not re.match("^[\d]*$", row_1[11]):
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(
                                row_id_1 + 2) + "," + "Expired-Final Qty can not be empty or string type."))

                    # to validate missing final quantity is empty or contains the number
                    if not row_1[12] or not re.match("^[\d]*$", row_1[12]):
                        raise ValidationError(_(
                            "Issue in Row" + " " + str(
                                row_id_1 + 2) + "," + "Missing-Final Qty can not be empty or string type."))
                    count = int(row_1[9]) + int(row_1[10]) + int(row_1[11]) + int(row_1[12])
                    final_count = count + final_count
            # to validate initial count and final count is equal
            if not initial_count == final_count:
                # raise validation error
                raise ValidationError(_(
                    "Issue in Row" + " " + str(row_id + 2) + "," +
                    "Initial Qty of SKU is not equal to Final Qty of SKU."))

            form_data_list.append(row)
            unique_data_list.append(row[0]+row[1]+row[3]+row[4])
        duplicate_data_list = ([item for item, count in collections.Counter(unique_data_list).items() if count > 1])
        if len(duplicate_data_list) > 0:
            raise ValidationError(_(
                "Alert ! Duplicate Data. SKU with same Expiry Date and same Bin ID is exist in the csv,"
                " please re-verify at your end."))

        return form_data_list