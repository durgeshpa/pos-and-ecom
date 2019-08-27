from django.contrib import admin
from .models import *
from .forms import ShipmentPaymentApprovalForm
from django.utils.safestring import mark_safe

from retailer_to_sp.models import Shipment
# Register your models here.

class OrderPaymentAdmin(admin.ModelAdmin):
    model = OrderPayment


class PaymentModeAdmin(admin.ModelAdmin):
    model = PaymentMode


class ShipmentPaymentAdmin(admin.ModelAdmin):
    model = ShipmentPayment
    fields = ("shipment",) #, "is_payment_approved")
    raw_id_fields = ("shipment",)


class NoDeleteAdminMixin:
    def has_delete_permission(self, request, obj=None):
        return False


class OnlinePaymentAdmin(NoDeleteAdminMixin, admin.TabularInline):
    model = OnlinePayment   
    fields = (
        "paid_amount", "payment_received", "online_payment_type",
        "reference_no", "is_payment_approved", "payment_approval_status",
    )
    readonly_fields = (
        "paid_amount", "online_payment_type", "reference_no", "payment_approval_status",
    )


class ShipmentPaymentApprovalAdmin(admin.ModelAdmin):
    inlines = [OnlinePaymentAdmin]
    model = ShipmentPaymentApproval
    #form = ShipmentPaymentApprovalForm
    list_display = (
        "id", "shipment", "order", "cash_payment_amount", "online_payment_amount", "online_payment_mode",
        "reference_no", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
    )

    fields = (
        "shipment", "cash_payment_amount", "amount_to_be_collected", "trip_id", 
        "trip_created_date", #"is_payment_approved"
    )
    
    readonly_fields = (
        "cash_payment_amount", "shipment", 
        "amount_to_be_collected", "trip_id", "trip_created_date"
    )
    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_shipmentpayment"):
            return True
        else:
            return False

    def cash_payment_amount(self, obj):
        return obj.cash_payment.paid_amount
    cash_payment_amount.short_description = "Cash Payment Amount"

    def online_payment_amount(self, obj):
        return obj.online_payment.paid_amount
    online_payment_amount.short_description = "Online Payment Amount"

    def online_payment_mode(self, obj):
        return obj.online_payment.online_payment_type
    online_payment_mode.short_description = "Online Payment Mode"

    def reference_no(self, obj):
        return obj.online_payment.reference_no
    reference_no.short_description = "Online Payment Reference No"

    def trip_id(self, obj):
        return obj.shipment.trip
    trip_id.short_description = "Trip id"

    def trip_created_date(self, obj):
        return obj.shipment.trip.created_at
    trip_created_date.short_description = "Trip Created Date"

    # def invoice_no(self, obj):
    #     return obj.shipment.invoice_no
    # invoice_no.short_description = "Shipment Invoice No"

    def amount_to_be_collected(self, obj):
        return obj.shipment.cash_to_be_collected()
    amount_to_be_collected.short_description = "Amount to be Collected"

    def order(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (obj.shipment.order.id,
                  obj.shipment.order.order_no)
                         )

class OrderPaymentApprovalAdmin(admin.ModelAdmin):
    inlines = [OnlinePaymentAdmin]
    model = OrderPaymentApproval
    #form = ShipmentPaymentApprovalForm
    list_display = (
        "id", "order", "cash_payment_amount", "online_payment_amount", "online_payment_mode",
        "reference_no"
    )

    fields = (
        "order", "cash_payment_amount", 
    )
    
    readonly_fields = (
        "cash_payment_amount", "order", 
    )
    # raw_id_fields = ("shipment",)

    def cash_payment_amount(self, obj):
        return obj.cash_payment.paid_amount
    cash_payment_amount.short_description = "Cash Payment Amount"

    def online_payment_amount(self, obj):
        return obj.online_payment.paid_amount
    online_payment_amount.short_description = "Online Payment Amount"

    def online_payment_mode(self, obj):
        return obj.online_payment.online_payment_type
    online_payment_mode.short_description = "Online Payment Mode"

    def reference_no(self, obj):
        return obj.online_payment.reference_no
    reference_no.short_description = "Online Payment Reference No"

    def order(self, obj):
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (obj.shipment.order.id,
                  obj.order.order_no)
                         )


class CashPaymentAdmin(admin.ModelAdmin):
    model = CashPayment


class CreditPaymentAdmin(admin.ModelAdmin):
    model = CreditPayment        


class WalletPaymentAdmin(admin.ModelAdmin):
    model = WalletPayment                 


admin.site.register(OrderPayment,OrderPaymentAdmin)
admin.site.register(ShipmentPayment,ShipmentPaymentAdmin)
admin.site.register(CashPayment,CashPaymentAdmin)
admin.site.register(CreditPayment,CreditPaymentAdmin)
admin.site.register(WalletPayment,WalletPaymentAdmin)
#admin.site.register(OnlinePayment,OnlinePaymentAdmin)
admin.site.register(ShipmentPaymentApproval,ShipmentPaymentApprovalAdmin)
admin.site.register(PaymentMode,PaymentModeAdmin)