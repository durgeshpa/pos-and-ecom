from django.contrib import admin
from .models import *
from .forms import ShipmentPaymentForm, ShipmentPaymentInlineForm, OnlinePaymentInlineForm, \
    PaymentForm
#from .forms import ShipmentPaymentApprovalForm
from django.utils.safestring import mark_safe
from django.forms.models import BaseInlineFormSet

from retailer_to_sp.models import Shipment
# Register your models here.

class OnlinePaymentInlineAdmin(admin.TabularInline):
    model = OnlinePayment
    form = OnlinePaymentInlineForm


class PaymentAdmin(admin.ModelAdmin):
    # inlines = [OnlinePaymentInlineAdmin]
    model = Payment
    autocomplete_fields = ('order',)

    # form  = PaymentForm
    list_display = (
        "order", "paid_amount", "payment_mode_name", "reference_no", "description"            
        )
    fields = (
        "order", "paid_amount", "payment_mode_name", "reference_no", "description",
        "online_payment_type"
    )
    
    # def get_inline_instances(self, request, obj=None):
    #     if not obj or obj.payment_mode_name != "online_payment": return []
    #     return super(PaymentAdmin, self).get_inline_instances(request, obj)

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
        "id", "order", "reference_no", "payment_approval_status", "paid_amount",
        "payment_received"
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
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent_payment":
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
                kwargs["queryset"] = Payment.objects.filter(order=parent_obj.order)
            except IndexError:
                pass
        return super(
            ShipmentPaymentInlineAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


    def has_add_permission(self, request, obj=None):
        try:
            parent_obj_id = request.resolver_match.kwargs['object_id']
            parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
            if parent_obj.trip.trip_status in ["CLOSED", "TRANSFERRED"]:
                return False
        except: 
            return True


    def has_change_permission(self, request, obj=None):
        try:
            parent_obj_id = request.resolver_match.kwargs['object_id']
            parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
            if parent_obj.trip.trip_status in ["CLOSED", "TRANSFERRED"]:
                return False
        except: 
            return True

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
    list_display = (
        'order', 'trip','invoice_no', 'invoice_amount', 'total_paid_amount','invoice_city'
        )
    list_per_page = 50
    fields = ['order', 'trip','invoice_no', 'invoice_amount', 'total_paid_amount', 'shipment_address', 'invoice_city',
        'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
    readonly_fields = ['order', 'trip', 'invoice_no', 'invoice_amount', 'total_paid_amount', 'shipment_address', 'invoice_city',
        'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
        
    def total_paid_amount(self,obj):
        return obj.total_paid_amount
    total_paid_amount.short_description = 'Total Paid Amount'

    class Media:
        js = ('admin/js/hide_save_button.js',)


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
