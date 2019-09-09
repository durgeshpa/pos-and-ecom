from django.contrib import admin
from .models import *
from .forms import ShipmentPaymentForm, ShipmentPaymentInlineForm
#from .forms import ShipmentPaymentApprovalForm
from django.utils.safestring import mark_safe
from django.forms.models import BaseInlineFormSet

from retailer_to_sp.models import Shipment
# Register your models here.

class PaymentAdmin(admin.ModelAdmin):
    model = Payment
    fields = (
        "order", "paid_amount", "payment_mode_name", "reference_no", "description"
    )

class PaymentModeAdmin(admin.ModelAdmin):
    model = PaymentMode


class ShipmentPaymentAdmin(admin.ModelAdmin):
    model = ShipmentPayment
    #fields = ("shipment",) #, "is_payment_approved")
    raw_id_fields = ("shipment",)


class NoDeleteAdminMixin:
    def has_delete_permission(self, request, obj=None):
        
        return False

class OnlinePaymentAdmin1(admin.ModelAdmin):
    model = OnlinePayment


class PaymentApprovalAdmin(admin.ModelAdmin):# NoDeleteAdminMixin, 
    model = PaymentApproval
    list_display = (
        "id", "order"
    )

    fields = (
        "order", "paid_amount", "payment_received", "payment_mode_name",
        "reference_no", "is_payment_approved", "payment_approval_status",
        "description"
    )
    
    readonly_fields = (
        "paid_amount", "payment_mode_name", "reference_no", "payment_approval_status",
        "order",
    )

    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    # def trip_id(self, obj):
    #     shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
    #     return shipment_payment.shipment.trip
    # trip_id.short_description = "Trip id"

    # def trip_created_date(self, obj):
    #     shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
    #     if shipment_payment.shipment.trip:
    #         return shipment_payment.shipment.trip.created_at
    # trip_created_date.short_description = "Trip Created Date"

    # def invoice_no(self, obj):
    #     shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
    #     return shipment_payment.shipment.invoice_no
    # invoice_no.short_description = "Shipment Invoice No"

    # def amount_to_be_collected(self, obj):
    #     shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
    #     return shipment_payment.shipment.cash_to_be_collected()
    # amount_to_be_collected.short_description = "Amount to be Collected"

    def order(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (order.id,
                  order.order_no)
                         )


# class PaymentEditAdmin(admin.TabularInline):# NoDeleteAdminMixin, 
#     model = Payment   
#     fields = (
#         "paid_amount", "payment_mode_name", "reference_no", "description"
#     )

class AtLeastOneFormSet(BaseInlineFormSet):
    def clean(self):
        super(AtLeastOneFormSet, self).clean()
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        if non_empty_forms - len(self.deleted_forms) < 1:
            raise ValidationError("Please fill at least one form.")



class ShipmentPaymentInlineAdmin(admin.TabularInline):
    model = ShipmentPayment
    form = ShipmentPaymentInlineForm
    formset = AtLeastOneFormSet
    fields = ("paid_amount", "parent_payment", "payment_mode_name", "reference_no", "description")
    readonly_fields = ("payment_mode_name", "reference_no",)
    # autocomplete_fields = ('parent_payment',)
    # search_fields = ('parent_payment__order__order_no')

    #autocomplete_fields = ('cart_product', 'cart_product_price')
    extra = 0

    def payment_mode_name(self,obj):
        return obj.parent_payment.payment_mode_name
    payment_mode_name.short_description = 'Payment Mode'

    def reference_no(self,obj):
        return obj.parent_payment.reference_no
    reference_no.short_description = 'Reference No'

    def description(self,obj):
        return obj.parent_payment.description
    description.short_description = 'Description'

    def has_delete_permission(self, request, obj=None):
        return False


class ShipmentPaymentDataAdmin(admin.ModelAdmin):
    inlines = [ShipmentPaymentInlineAdmin]
    model = ShipmentData
    fields = ['order', 'invoice_no', 'invoice_amount', 'shipment_address', 'invoice_city',
        'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
    readonly_fields = ['order', 'invoice_no', 'invoice_amount', 'shipment_address', 'invoice_city',
        'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']





class PaymentEditAdmin(admin.ModelAdmin):# NoDeleteAdminMixin, 
    model = PaymentEdit
    list_display = (
        "id", "invoice_no", "order", "amount_to_be_collected", "trip_id", 
        "trip_created_date",
    )

    fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", 
        "trip_created_date", "paid_amount", "payment_received", "payment_mode_name",
        "reference_no", "is_payment_approved", "payment_approval_status",
        "description",
    )
    
    readonly_fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", "trip_created_date",
        "payment_approval_status", "is_payment_approved", "payment_received",
    )

    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def trip_id(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return shipment_payment.shipment.trip
    trip_id.short_description = "Trip id"

    def trip_created_date(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        if shipment_payment.shipment.trip:
            return shipment_payment.shipment.trip.created_at
    trip_created_date.short_description = "Trip Created Date"

    def invoice_no(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return shipment_payment.shipment.invoice_no
    invoice_no.short_description = "Shipment Invoice No"

    def amount_to_be_collected(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return shipment_payment.shipment.cash_to_be_collected()
    amount_to_be_collected.short_description = "Amount to be Collected"

    def order(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (shipment_payment.shipment.order.id,
                  shipment_payment.shipment.order.order_no)
                         )


class CashPaymentAdmin(admin.ModelAdmin):
    model = CashPayment


class CreditPaymentAdmin(admin.ModelAdmin):
    model = CreditPayment        


class WalletPaymentAdmin(admin.ModelAdmin):
    model = WalletPayment                 

# payments
admin.site.register(Payment,PaymentAdmin)
admin.site.register(ShipmentPayment,ShipmentPaymentAdmin)

#payment modes
# admin.site.register(CashPayment,CashPaymentAdmin)
# admin.site.register(OnlinePayment,OnlinePaymentAdmin1)
# admin.site.register(CreditPayment,CreditPaymentAdmin)
# admin.site.register(WalletPayment,WalletPaymentAdmin)
#admin.site.register(PaymentMode,PaymentModeAdmin)

# payment edit and approvals
admin.site.register(PaymentApproval,PaymentApprovalAdmin)
# admin.site.register(PaymentEdit,PaymentEditAdmin)
admin.site.register(ShipmentData,ShipmentPaymentDataAdmin)
