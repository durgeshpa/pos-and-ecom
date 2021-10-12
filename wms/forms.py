import logging
import collections
import re
import csv
import codecs
from itertools import chain

from django import forms
from datetime import datetime

from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Permission, Group
from tempus_dominus.widgets import DateTimePicker

from accounts.models import User
from .models import Bin, In, Putaway, PutawayBinInventory, BinInventory, Out, Pickup, StockMovementCSVUpload, \
    InventoryType, InventoryState, BIN_TYPE_CHOICES, Audit, Zone, WarehouseAssortment, QCArea, Crate
from products.models import Product, ProductPrice, ParentProduct
from shops.models import Shop
from gram_to_brand.models import GRNOrderProductMapping
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from .common_functions import create_batch_id
from global_config.views import get_config
from retailer_to_sp.models import OrderedProduct
from django.db import transaction
from .common_functions import cancel_ordered, cancel_shipment, cancel_returned, putaway_repackaging
from dal import autocomplete
from accounts.middlewares import get_current_user
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
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
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
                    warehouse_obj = warehouse.last()
                    """
                        Single virtual bin auto created for franchise shops when shop is approved. More bins cannot be created.
                    """
                    if warehouse_obj.shop_type.shop_type == 'f':
                        raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + ", Bin cannot be added for Franchise Shop."))
                    if Bin.objects.filter(warehouse=warehouse_obj, bin_id=row[3]).exists():
                        raise ValidationError(_("Issue in Row" + " " + str(row_id + 1) + "," + 'Same Bin ID is exists in a system with same Warehouse. Please re-verify at your end.'))

            info_logger.info("Validation of File format successfully passed.")
            form_data_list.append(row)
        return form_data_list


class BinForm(forms.ModelForm):
    info_logger.info("Bin Form has been called.")
    bin_id = forms.CharField(required=True, max_length=16)
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices)
    bin_type = forms.ChoiceField(choices=BIN_TYPE_CHOICES)
    zone = forms.ModelChoiceField(queryset=Zone.objects.all(), required=True,
                                  widget=autocomplete.ModelSelect2(url='zone-autocomplete', forward=('warehouse',)))

    class Meta:
        model = Bin
        fields = ['warehouse', 'bin_id', 'bin_type', 'is_active', 'zone']

    def clean_bin_id(self):
        bin_validation, message = bin_id_validation(self.cleaned_data['bin_id'], self.data['bin_type'])
        if bin_validation is False:
            raise ValidationError(_(message))
        if self.instance.bin_id is None:
            bin_obj = Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id=self.cleaned_data['bin_id'])
        else:
            bin_obj = Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id=self.instance.bin_id)
        if Bin.objects.filter(warehouse__id=self.data['warehouse'], bin_id=self.cleaned_data['bin_id']).exists():
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

    def clean_zone(self):
        if self.cleaned_data['zone']:
            if int(self.cleaned_data['zone'].warehouse.id) != int(self.data['warehouse']):
                raise ValidationError(_("Invalid zone for selected warehouse."))
        return self.cleaned_data['zone']

    def __init__(self, *args, **kwargs):
        super(BinForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance:
            if instance.is_active is True and 'is_active' in self.fields:
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
                if instance.bin:
                    self.fields['bin_id'].initial = instance.bin.bin.bin_id
                self.fields['bin_id'].disabled = True
                if instance.bin:
                    self.fields['bin'].initial = instance.bin.bin.bin_id
                self.fields['bin'].disabled = True
            if instance.putaway_status is False:
                if instance.bin:
                    self.fields['bin_id'].initial = instance.bin.bin.bin_id
                self.fields['bin_id'].disabled = True
                self.fields['bin'] = forms.ModelChoiceField(queryset=Bin.objects.filter(
                    warehouse=instance.warehouse, is_active=True).distinct(), widget=autocomplete.ModelSelect2())
            if not instance.bin:
                self.fields['bin_id'].required = False
    def clean_bin(self):
        if self.instance.putaway_status is True:
            self.fields['putaway_status'].disabled = True
            if self.instance.bin:
                self.fields['bin_id'].initial = self.instance.bin.bin.bin_id
            self.fields['bin_id'].disabled = True
            if self.instance.bin:
                self.fields['bin'].initial = self.instance.bin.bin.bin_id
            self.fields['bin'].disabled = True
        warehouse = self.instance.warehouse
        if self.instance.putaway_status is False:
            if self.instance.bin:
                self.fields['bin_id'].initial = self.instance.bin.bin.bin_id
            self.fields['bin_id'].disabled = True
            self.fields['bin'] = forms.ModelChoiceField(queryset=Bin.objects.filter(
                warehouse=warehouse).distinct(), widget=autocomplete.ModelSelect2())
        inventory_type = self.instance.putaway.inventory_type
        bin_selected = self.cleaned_data['bin']
        bin_obj = BinInventory.objects.filter(bin=Bin.objects.filter(bin_id=bin_selected, warehouse=warehouse).last(),
                                              warehouse=warehouse,
                                              inventory_type=inventory_type).last()
        if bin_obj:
            return bin_obj
        else:
            product = Product.objects.filter(product_sku=self.instance.sku_id).last()
            bin_exp_obj = BinInventory.objects.filter(warehouse=warehouse,
                                                      bin=Bin.objects.filter(
                                                          bin_id=bin_selected.bin_id,
                                                      warehouse=warehouse).last(),
                                                      sku=product,
                                                      batch_id=self.instance.batch_id)
            if not bin_exp_obj.exists():
                product_ids = [product.id]
                if product.discounted_sku:
                    product_ids.append(product.discounted_sku.id)
                bin_in_obj = BinInventory.objects.filter(warehouse=warehouse,
                                                         sku__id__in=product_ids)
                for bin_in in bin_in_obj:
                    if not (bin_in.batch_id == self.instance.batch_id):
                        if bin_in.bin.bin_id == bin_selected.bin_id:
                            qty_present_in_bin = bin_in.quantity + bin_in.to_be_picked_qty
                            if qty_present_in_bin == 0:
                                pass
                            else:
                                raise forms.ValidationError(" You can't perform this action,"
                                                            " Non zero qty of more than one Batch ID of a single"
                                                            " SKU can’t be saved in the same Bin ID.")
                with transaction.atomic():
                    # initial_type = InventoryType.objects.filter(inventory_type='normal').last(),
                    bin_obj, created = BinInventory.objects.get_or_create(warehouse=warehouse, bin=bin_selected,
                                                                          sku=product,
                                                                          batch_id=self.instance.batch_id,
                                                                          inventory_type=inventory_type,
                                                                          quantity=int(0),
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
            # if self.cleaned_data['bin'].bin.bin_id == 'V2VZ01SR001-0001':
            #     raise forms.ValidationError("You can't assign this BIN ID, This is a Virtual Bin ID.")
            if self.cleaned_data['putaway_status'] is False:
                raise forms.ValidationError("You can't perform this action, Please mark PutAway status is Active.")
            if PutawayBinInventory.objects.filter(id=self.instance.id)[0].putaway_status is True:
                raise forms.ValidationError("You can't perform this action, PutAway has already done.")
            else:
                product = Product.objects.filter(product_sku=self.instance.sku_id).last()

                product_ids = [product.id]
                if product.discounted_sku:
                    product_ids.append(product.discounted_sku.id)
                bin_in_obj = BinInventory.objects.filter(warehouse=self.instance.warehouse,
                                                         sku__id__in=product_ids)
                for bin_in in bin_in_obj:
                    if not (bin_in.batch_id == self.instance.batch_id):
                        if bin_in.bin.bin_id == self.cleaned_data['bin'].bin.bin_id:
                            qty_present_in_bin = bin_in.quantity + bin_in.to_be_picked_qty
                            if qty_present_in_bin == 0:
                                pass
                            else:
                                raise forms.ValidationError(" You can't perform this action,"
                                                            " Non zero qty of more than one Batch ID of a single"
                                                            " SKU can’t be saved in the same Bin ID.")
                bin_id = self.cleaned_data['bin']
                putaway_inventory_type = self.instance.putaway.inventory_type
                putaway_product = self.instance.sku
                if self.instance.putaway_type == 'Order_Cancelled':
                    initial_stage = InventoryState.objects.filter(inventory_state='ordered').last(),
                    cancel_ordered(self.request.user, self.instance, initial_stage, bin_id)

                elif self.instance.putaway_type in ['picking_cancelled', 'Pickup_Cancelled']:
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(self.request.user, self.instance, initial_stage, bin_id)

                elif self.instance.putaway_type == 'Shipment_Cancelled':
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last(),
                    cancel_ordered(self.request.user, self.instance, initial_stage, bin_id)

                elif self.instance.putaway_type == 'PAR_SHIPMENT':
                    initial_stage = InventoryState.objects.filter(inventory_state='picked').last()
                    shipment_object = OrderedProduct.objects.filter(order__order_no=self.instance.putaway.putaway_type_id)[0]
                    shipment_product = shipment_object.rt_order_product_order_product_mapping.all()
                    cancel_shipment(self.request.user, self.instance, initial_stage, shipment_product,
                                    bin_id, putaway_inventory_type)

                elif self.instance.putaway_type == 'RETURNED':
                    initial_stage = InventoryState.objects.filter(inventory_state='shipped').last()
                    shipment_product = OrderedProduct.objects.filter(
                        invoice__invoice_no=self.instance.putaway.putaway_type_id)[0].rt_order_product_order_product_mapping.all()
                    cancel_returned(self.request.user, self.instance, initial_stage, shipment_product,
                                    bin_id, putaway_inventory_type)
                elif self.instance.putaway_type == 'REPACKAGING':
                    initial_stage = InventoryState.objects.filter(inventory_state='new').last(),
                    putaway_repackaging(self.request.user, self.instance, initial_stage, bin_id)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inventory_movement_type'].choices = StockMovementCSVUpload.upload_inventory_type[:-1]

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
        user = get_current_user()
        if self.data['inventory_movement_type'] == '2':
            data = validation_bin_stock_movement(self.cleaned_data['file'], user)

        elif self.data['inventory_movement_type'] == '3':
            data = validation_stock_correction(self.cleaned_data['file'], user)

        elif self.data['inventory_movement_type'] == '4':
            data = validation_warehouse_inventory(self.cleaned_data['file'], user)
        else:
            raise forms.ValidationError("Inventory movement type is not correct, Please re-verify it at"
                                        " your end .")

        return data


def validation_bin_stock_movement(file, user):
    reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
    first_row = next(reader)
    # list which contains csv data and pass into the view file
    form_data_list = []
    for row_id, row in enumerate(reader):

        # validation for shop id, it should be numeric.
        if not row[0] or not re.match("^[\d]*$", row[0]):
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        # validation for shop id to check that is exist or not in the database
        check_shop = Shop.objects.filter(pk=row[0]).last()
        if not check_shop:
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1},)
        elif check_shop.shop_type.shop_type == 'f' and not user.is_superuser:
            """
                Single virtual bin present for all products in a franchise shop. This stock correction does not apply to Franchise shops.
            """
            raise ValidationError(_('The warehouse/shop is of type Franchise. Stock changes not allowed'),
                                  params={'value': row_id + 1}, )

        # validate for product sku
        if not row[1]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1},)

        # validate for product sku is exist or not
        if not Product.objects.filter(product_sku=row[1], repackaging_type__in=['none', 'source', 'destination']).exists():
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


def validation_stock_correction(file, user, type=''):
    reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
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
        check_shop = Shop.objects.filter(pk=row[0]).last()
        if not check_shop:
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 2}, )
        elif check_shop.shop_type.shop_type == 'f' and not user.is_superuser:
            """
                Single virtual bin present for all products in a franchise shop. This stock correction does not apply to Franchise shops.
            """
            raise ValidationError(_('The warehouse/shop is of type Franchise. Stock changes not allowed'),
                                  params={'value': row_id + 1}, )

        # validate for product name
        if not row[1]:
            raise ValidationError(_('Product Name can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 2}, )

        # validate for product sku
        if not row[2]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 2}, )

        # validate for product sku is exist or not
        if not Product.objects.filter(product_sku=row[2], repackaging_type__in=['none', 'source', 'destination']).exists():
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
                                                  bin=Bin.objects.filter(bin_id=row[4], warehouse=row[0]).last(),
                                                  sku=Product.objects.filter(
                                                      product_sku=row[2]).last(),
                                                  batch_id=batch_id)
        # if combination of expiry date and sku is not exist in GRN Order Product Mapping
        if not bin_exp_obj.exists() and check_shop.shop_type.shop_type != 'f':
            bin_in_obj = BinInventory.objects.filter(
                warehouse=row[0], sku=Product.objects.filter(product_sku=row[2]).last())
            for bin_in in bin_in_obj:
                sku = row[1]
                # create batch id
                if not (bin_in.batch_id == create_batch_id(sku, row[3])):
                    if bin_in.bin.bin_id == row[4]:
                        physical_qty_in_bin = bin_in.quantity + bin_in.to_be_picked_qty
                        if physical_qty_in_bin == 0:
                            pass
                        else:
                            raise ValidationError(_(
                                "Issue in Row" + " " + str(row_id + 2) + "," + "Non zero qty of 2 Different"
                                                                               " Batch ID/Expiry date for same SKU"
                                                                               " can’t save in the same Bin."))
        # else:
        #     type_normal = InventoryType.objects.filter(inventory_type='normal').last()
        #     normal_bin_inventory_object = bin_exp_obj.filter(inventory_type=type_normal).last()
        #     physical_qty_in_bin = normal_bin_inventory_object.quantity + normal_bin_inventory_object.to_be_picked_qty
        #     if physical_qty_in_bin == 0:
        #         pass
        #     else:
        #         raise ValidationError(_(
        #             "Issue in Row" + " " + str(row_id + 2) + "," + "Non zero qty of 2 Different"
        #                                                            " Batch ID/Expiry date for same SKU"
        #                                                            " can’t save in the same Bin."))

        form_data_list.append(row)
        unique_data_list.append(row[0] + row[2] + row[3] + row[4])
    duplicate_data_list = ([item for item, count in collections.Counter(unique_data_list).items() if count > 1])
    if len(duplicate_data_list) > 0 and type != 'f':
        raise ValidationError(_(
            "Alert ! Duplicate Data. Same SKU, Expiry Date, Bin ID and Inventory Movement Type is exist in the csv,"
            " please re-verify at your end."))

    return form_data_list


def validation_warehouse_inventory(file, user):
    reader = csv.reader(codecs.iterdecode(file, 'utf-8', errors='ignore'))
    first_row = next(reader)
    # list which contains csv data and pass into the view file
    form_data_list = []
    for row_id, row in enumerate(reader):

        # validation for shop id, it should be numeric.
        if not row[0] or not re.match("^[\d]*$", row[0]):
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s]. It should be numeric.'),
                                  params={'value': row_id + 1}, )

        # validation for shop id to check that is exist or not in the database
        check_shop = Shop.objects.filter(pk=row[0]).last()
        if not check_shop:
            raise ValidationError(_('Invalid Warehouse id at Row number [%(value)s].'
                                    'Warehouse Id does not exists in the system.Please re-verify at your end.'),
                                  params={'value': row_id + 1}, )
        elif check_shop.shop_type.shop_type == 'f' and not user.is_superuser:
            """
                Single virtual bin present for all products in a franchise shop. This stock correction does not apply to Franchise shops.
            """
            raise ValidationError(_('The warehouse/shop is of type Franchise. Stock changes not allowed'),
                                  params={'value': row_id + 1}, )

        # validation for product sku
        if not row[1]:
            raise ValidationError(_('Product SKU can not be blank at Row number [%(value)s].'),
                                  params={'value': row_id + 1}, )

        # validation for product sku is exist or not
        if not Product.objects.filter(product_sku=row[1], repackaging_type__in=['none', 'source', 'destination']).exists():
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

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
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

        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
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
            reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
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


supervisor_perm = Permission.objects.filter(codename='can_have_zone_supervisor_permission').last()
coordinator_perm = Permission.objects.filter(codename='can_have_zone_coordinator_permission').last()
putaway_group = Group.objects.filter(name='Putaway').last()
picker_group = Group.objects.filter(name='Picker Boy').last()


class ZoneForm(forms.ModelForm):
    info_logger.info("Zone Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))
    supervisor = forms.ModelChoiceField(queryset=User.objects.filter(
        Q(groups__permissions=supervisor_perm) | Q(user_permissions=supervisor_perm)).distinct(), required=True,
                                        widget=autocomplete.ModelSelect2(url='supervisor-autocomplete'))
    coordinator = forms.ModelChoiceField(queryset=User.objects.filter(
        Q(groups__permissions=coordinator_perm) | Q(user_permissions=coordinator_perm)).distinct(), required=True)
    # putaway_users = forms.ModelMultipleChoiceField(
    #     queryset=User.objects.filter(Q(groups=putaway_group)).distinct(),
    #     required=True,
    #     widget=FilteredSelectMultiple(
    #         verbose_name=_('Putaway users'),
    #         is_stacked=False
    #     )
    # )
    # picker_users = forms.ModelMultipleChoiceField(
    #     queryset=User.objects.filter(Q(groups=picker_group)).distinct(),
    #     required=True,
    #     widget=FilteredSelectMultiple(
    #         verbose_name=_('Picker users'),
    #         is_stacked=False
    #     )
    # )
    putaway_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(), required=True,
        widget=autocomplete.ModelSelect2Multiple(url='putaway-users-autocomplete', forward=('warehouse',)))
    picker_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(), required=True,
        widget=autocomplete.ModelSelect2Multiple(url='picker-users-autocomplete', forward=('warehouse',)))

    class Meta:
        model = Zone
        fields = ['name', 'warehouse', 'supervisor', 'coordinator', 'putaway_users', 'picker_users']

    def clean_warehouse(self):
        if not self.cleaned_data['warehouse'].shop_type.shop_type == 'sp':
            raise ValidationError(_("Invalid warehouse selected."))
        return self.cleaned_data['warehouse']

    def clean_supervisor(self):
        if not self.cleaned_data['supervisor'].has_perm('wms.can_have_zone_supervisor_permission'):
            raise ValidationError(_("Invalid supervisor selected."))
        return self.cleaned_data['supervisor']

    def clean_coordinator(self):
        if not self.cleaned_data['coordinator'].has_perm('wms.can_have_zone_coordinator_permission'):
            raise ValidationError(_("Invalid coordinator selected."))
        return self.cleaned_data['coordinator']

    def clean_putaway_users(self):
        if self.cleaned_data['putaway_users']:
            if len(self.cleaned_data['putaway_users']) <= 0 or \
                    len(self.cleaned_data['putaway_users']) > get_config('MAX_PUTAWAY_USERS_PER_ZONE'):
                raise ValidationError(_(
                    "Select up to " + str(get_config('MAX_PUTAWAY_USERS_PER_ZONE')) + " users."))
            for user in self.cleaned_data['putaway_users']:
                if (not user.groups.filter(name='Putaway').exists()) or \
                        user.shop_employee.last().shop_id != int(self.data['warehouse']):
                    raise ValidationError(_(
                        "Invalid user " + str(user) + " selected as putaway users."))
        return self.cleaned_data['putaway_users']

    def clean_picker_users(self):
        if self.cleaned_data['picker_users']:
            if len(self.cleaned_data['picker_users']) <= 0 or \
                    len(self.cleaned_data['picker_users']) > get_config('MAX_PICKER_USERS_PER_ZONE'):
                raise ValidationError(_(
                    "Select up to " + str(get_config('MAX_PICKER_USERS_PER_ZONE')) + " users."))
            for user in self.cleaned_data['picker_users']:
                if (not user.groups.filter(name='Picker Boy').exists()) or \
                        user.shop_employee.last().shop_id != int(self.data['warehouse']):
                    raise ValidationError(_(
                        "Invalid user " + str(user) + " selected as picker users."))
        return self.cleaned_data['picker_users']

    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get("warehouse")
        supervisor = cleaned_data.get("supervisor")
        coordinator = cleaned_data.get("coordinator")
        instance = getattr(self, 'instance', None)
        if instance.pk and warehouse and supervisor and coordinator:
            if Zone.objects.filter(warehouse=warehouse, supervisor=supervisor, coordinator=coordinator). \
                    exclude(id=instance.pk).exists():
                raise ValidationError("Zone already exist for selected 'warehouse', 'supervisor' and 'coordinator'")
        elif warehouse and supervisor and coordinator:
            if Zone.objects.filter(warehouse=warehouse, supervisor=supervisor, coordinator=coordinator).exists():
                raise ValidationError("Zone already exist for selected 'warehouse', 'supervisor' and 'coordinator'")

    def __init__(self, *args, **kwargs):
        super(ZoneForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        perm = Permission.objects.get(codename='can_have_zone_coordinator_permission')

        if instance.pk:
            queryset = User.objects.filter(is_active=True).filter(
                Q(groups__permissions=perm) | Q(user_permissions=perm)).exclude(coordinator_zone_user__isnull=False)
            self.fields['coordinator'].queryset = (queryset | User.objects.filter(id=instance.coordinator.pk)).distinct()
        else:
            self.fields['coordinator'].queryset = User.objects.filter(is_active=True).filter(
                Q(groups__permissions=perm) | Q(user_permissions=perm)).exclude(
                coordinator_zone_user__isnull=False).distinct()


class WarehouseAssortmentForm(forms.ModelForm):
    info_logger.info("WarehouseAssortment Form has been called.")
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))
    product = forms.ModelChoiceField(queryset=ParentProduct.objects.all(), required=True,
                                     widget=autocomplete.ModelSelect2(url='parent-product-filter'))
    zone = forms.ModelChoiceField(queryset=Zone.objects.all(), required=True,
                                  widget=autocomplete.ModelSelect2(url='zone-autocomplete', forward=('warehouse',)))

    class Meta:
        model = WarehouseAssortment
        fields = ['warehouse', 'product', 'zone']

    def clean_warehouse(self):
        if not self.cleaned_data['warehouse'].shop_type.shop_type == 'sp':
            raise ValidationError(_("Invalid warehouse selected."))
        return self.cleaned_data['warehouse']

    def clean_zone(self):
        if int(self.cleaned_data['zone'].warehouse.id) != int(self.data['warehouse']):
            raise ValidationError(_("Invalid zone selected."))
        return self.cleaned_data['zone']

    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get("warehouse")
        product = cleaned_data.get("product")
        zone = cleaned_data.get("zone")
        instance = getattr(self, 'instance', None)
        if warehouse and product and zone:
            if not instance.pk:
                if WarehouseAssortment.objects.filter(warehouse=warehouse, product=product).exists():
                    raise ValidationError("Warehouse Assortment already exist for selected warehouse and "
                                          "product, only zone updation is allowed.")
            else:
                if not WarehouseAssortment.objects.filter(
                        id=instance.pk, warehouse=warehouse, product=product).exists():
                    raise ValidationError("Only zone updation is allowed.")

    def __init__(self, *args, **kwargs):
        super(WarehouseAssortmentForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if instance.pk:
            self.fields['zone'].queryset = Zone.objects.filter(warehouse=instance.warehouse)


class WarehouseAssortmentSampleCSV(forms.ModelForm):
    """
    Warehouse Assortment Sample CSV Form
    """
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))

    class Meta:
        model = WarehouseAssortment
        fields = ('warehouse',)


class WarehouseAssortmentCsvViewForm(forms.Form):
    """
    This Form class is used to upload csv for particular sales executive in Warehouse Assortment
    """
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))
    file = forms.FileField()

    def clean_file(self):
        """
        :return: Form is valid otherwise validation error message
        """
        # Validate to check the file format, It should be csv file.
        if self.cleaned_data['file'].name[-4:] not in ('.csv'):
            raise forms.ValidationError("Sorry! Only csv file accepted.")
        reader = csv.reader(codecs.iterdecode(self.cleaned_data['file'], 'utf-8', errors='ignore'))
        first_row = next(reader)
        # list which contains csv data and pass into the view file
        form_data_list = []
        for row_id, row in enumerate(reader):

            # validation for warehouse shop id, it should be numeric.
            if not row[0] or not re.match("^[\d]*$", row[0]):
                raise ValidationError(_('INVALID_WAREHOUSE_ID at Row number [%(value)s]. It should be numeric.'),
                                      params={'value': row_id+1},)

            if int(row[0]) != self.cleaned_data['warehouse'].pk:
                raise ValidationError(_(
                    'Row number [%(value)s] | Assortment are allowed for the selected Warehouse only.'),
                                      params={'value': row_id + 1}, )

            # validation for warehouse shop id to check that is exist or not in the database
            if not Shop.objects.filter(pk=row[0], shop_type__shop_type='sp').exists():
                raise ValidationError(_('INVALID_WAREHOUSE_ID at Row number [%(value)s]. Warehouse Id not exists.'),
                                      params={'value': row_id+1},)

            # validation for product to check that is exist or not in the database
            if not row[2] or not ParentProduct.objects.filter(parent_id=row[2]).exists():
                raise ValidationError(_('INVALID_PRODUCT_ID at Row number [%(value)s]. Product is not exists.'),
                                      params={'value': row_id+1},)

            # validation for zone id, it should be numeric.
            if not row[4] or not re.match("^[\d]*$", row[4]):
                raise ValidationError(_('INVALID_ZONE_ID at Row number [%(value)s]. It should be numeric.'),
                                      params={'value': row_id + 1}, )

            # validation for product to check that is exist or not in the database
            if not row[4] or not Zone.objects.filter(id=row[4]).exists():
                raise ValidationError(_('INVALID_ZONE_ID at Row number [%(value)s]. Zone is not exists.'),
                                      params={'value': row_id+1},)

            # validation for zone id is associate with executive
            if Zone.objects.filter(id=row[4]).last().warehouse.id != int(row[0]):
                raise ValidationError(_('Row number [%(value)s] | Warehouse not mapped to the selected Zone.'),
                                      params={'value': row_id+1},)

            form_data_list.append(row)

        return self.cleaned_data['file']

    def clean(self):
        # Check logged in user permissions
        if not self.auto_id['user'].has_perm('wms.can_have_zone_warehouse_permission'):
            raise forms.ValidationError(_("Required permissions missing to perform this task."))


class QCAreaForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))

    area_id = forms.CharField(required=False, max_length=16)
    area_type = forms.ChoiceField(choices=QCArea.QC_AREA_TYPE_CHOICES)

    def __init__(self, *args, **kwargs):
        super(QCAreaForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance.id is not None:
            self.fields['warehouse'].disabled = True
            self.fields['area_type'].disabled = True
        self.fields['area_id'].disabled = True

    class Meta:
        model = QCArea
        fields = ['warehouse', 'area_id', 'area_type', 'is_active']


class CrateForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))
    zone = forms.ModelChoiceField(queryset=Zone.objects.all(), required=True,
                                  widget=autocomplete.ModelSelect2(url='zone-autocomplete', forward=('warehouse',)))
    crate_id = forms.CharField(required=False, max_length=20)
    crate_type = forms.ChoiceField(choices=Crate.CRATE_TYPE_CHOICES)

    def __init__(self, *args, **kwargs):
        super(CrateForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance.id is not None:
            self.fields['warehouse'].disabled = True
            self.fields['zone'].disabled = True
            self.fields['crate_type'].disabled = True
        self.fields['crate_id'].disabled = True

    class Meta:
        model = QCArea
        fields = ['warehouse', 'zone', 'crate_id', 'crate_type']


class BulkCrateForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(queryset=warehouse_choices, required=True,
                                       widget=autocomplete.ModelSelect2(url='warehouses-autocomplete'))
    zone = forms.ModelChoiceField(queryset=Zone.objects.all(), required=True,
                                  widget=autocomplete.ModelSelect2(url='zone-autocomplete', forward=('warehouse',)))
    crate_type = forms.ChoiceField(choices=Crate.CRATE_TYPE_CHOICES)
    quantity = forms.IntegerField(min_value=1, max_value=100)

    class Meta:
        model = Crate
        fields = ['warehouse', 'zone', 'crate_type', 'quantity']


class InOutLedgerForm(forms.Form):
    sku = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=autocomplete.ModelSelect2(url='product-sku-autocomplete', ),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Shop.objects.filter(shop_type__shop_type='sp'),
        widget=autocomplete.ModelSelect2(url='warehouses-autocomplete', ),
    )
    start_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD HH:mm:ss',
            }
        ),
    )
    end_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD HH:mm:ss',
            }
        ),
    )


class IncorrectProductBinMappingForm(forms.Form):
    start_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD HH:mm:ss',
            }
        ),
    )
    end_date = forms.DateTimeField(
        widget=DateTimePicker(
            options={
                'format': 'YYYY-MM-DD HH:mm:ss',
            }
        ),
    )
