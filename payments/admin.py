from django.contrib import admin
from .models import *
#from .forms import ShipmentPaymentApprovalForm
from django.utils.safestring import mark_safe

from retailer_to_sp.models import Shipment
# Register your models here.

class PaymentAdmin(admin.ModelAdmin):
    model = Payment


class PaymentModeAdmin(admin.ModelAdmin):
    model = PaymentMode


# class ShipmentPaymentAdmin(admin.ModelAdmin):
#     model = ShipmentPayment
#     fields = ("shipment",) #, "is_payment_approved")
#     raw_id_fields = ("shipment",)


class NoDeleteAdminMixin:
    def has_delete_permission(self, request, obj=None):
        
        return False

class OnlinePaymentAdmin1(admin.ModelAdmin):
    model = OnlinePayment


class PaymentApprovalAdmin(admin.TabularInline):# NoDeleteAdminMixin, 
    model = Payment   
    fields = (
        "paid_amount", "payment_received", "payment_mode_name",
        "reference_no", "is_payment_approved", "payment_approval_status",
        "description",
    )
    readonly_fields = (
        "paid_amount", "payment_mode_name", "reference_no", "payment_approval_status",
    )


class PaymentEditAdmin(admin.TabularInline):# NoDeleteAdminMixin, 
    model = Payment   
    fields = (
        "paid_amount", "payment_mode_name", "reference_no", "description"
    )


class ShipmentPaymentEditAdmin(admin.ModelAdmin):
    inlines = [PaymentEditAdmin]
    model = ShipmentPaymentEdit
    #form = ShipmentPaymentApprovalForm
    list_display = (
        "id", "invoice_no", "order", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
        # "cash_payment_amount", "online_payment_amount", "online_payment_mode",
        #"reference_no",
    )

    fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
    )
    
    readonly_fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", "trip_created_date"
    )

    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def trip_id(self, obj):
        return obj.trip
    trip_id.short_description = "Trip id"

    def trip_created_date(self, obj):
        if obj.trip:
            return obj.trip.created_at
    trip_created_date.short_description = "Trip Created Date"

    # def invoice_no(self, obj):
    #     return obj.shipment.invoice_no
    # invoice_no.short_description = "Shipment Invoice No"

    def amount_to_be_collected(self, obj):
        return obj.cash_to_be_collected()
    amount_to_be_collected.short_description = "Amount to be Collected"

    def order(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (obj.order.id,
                  obj.order.order_no)
                         )


class ShipmentPaymentApprovalAdmin(admin.ModelAdmin):
    inlines = [PaymentApprovalAdmin]
    model = ShipmentPaymentApproval
    #form = ShipmentPaymentApprovalForm
    list_display = (
        "id", "invoice_no", "order", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
        # "cash_payment_amount", "online_payment_amount", "online_payment_mode",
        #"reference_no",
    )

    fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
    )
    
    readonly_fields = (
        "invoice_no", "amount_to_be_collected", "trip_id", "trip_created_date"
    )

    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def trip_id(self, obj):
        return obj.trip
    trip_id.short_description = "Trip id"

    def trip_created_date(self, obj):
        if obj.trip:
            return obj.trip.created_at
    trip_created_date.short_description = "Trip Created Date"

    # def invoice_no(self, obj):
    #     return obj.shipment.invoice_no
    # invoice_no.short_description = "Shipment Invoice No"

    def amount_to_be_collected(self, obj):
        return obj.cash_to_be_collected()
    amount_to_be_collected.short_description = "Amount to be Collected"

    def order(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (obj.order.id,
                  obj.order.order_no)
                         )

# class OrderPaymentApprovalAdmin(admin.ModelAdmin):
#     #inlines = [OnlinePaymentAdmin]
#     model = OrderPaymentApproval
#     #form = ShipmentPaymentApprovalForm
#     list_display = (
#         "id", "order", "cash_payment_amount", "online_payment_amount", "online_payment_mode",
#         "reference_no"
#     )

#     fields = (
#         "order", "cash_payment_amount", 
#     )
    
#     readonly_fields = (
#         "cash_payment_amount", "order", 
#     )
#     # raw_id_fields = ("shipment",)

#     def cash_payment_amount(self, obj):
#         return obj.cash_payment.paid_amount
#     cash_payment_amount.short_description = "Cash Payment Amount"

#     def online_payment_amount(self, obj):
#         return obj.online_payment.paid_amount
#     online_payment_amount.short_description = "Online Payment Amount"

#     def online_payment_mode(self, obj):
#         return obj.online_payment.online_payment_type
#     online_payment_mode.short_description = "Online Payment Mode"

#     def reference_no(self, obj):
#         return obj.online_payment.reference_no
#     reference_no.short_description = "Online Payment Reference No"

#     def order(self, obj):
#         return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (obj.shipment.order.id,
#                   obj.order.order_no)
#                          )


class CashPaymentAdmin(admin.ModelAdmin):
    model = CashPayment


class CreditPaymentAdmin(admin.ModelAdmin):
    model = CreditPayment        


class WalletPaymentAdmin(admin.ModelAdmin):
    model = WalletPayment                 


admin.site.register(Payment,PaymentAdmin)
#admin.site.register(ShipmentPayment,ShipmentPaymentAdmin)
admin.site.register(CashPayment,CashPaymentAdmin)
admin.site.register(OnlinePayment,OnlinePaymentAdmin1)
admin.site.register(CreditPayment,CreditPaymentAdmin)
admin.site.register(WalletPayment,WalletPaymentAdmin)
# admin.site.register(ShipmentPaymentApproval,ShipmentPaymentApprovalAdmin)
# admin.site.register(ShipmentPaymentEdit,ShipmentPaymentEditAdmin)
admin.site.register(PaymentMode,PaymentModeAdmin)