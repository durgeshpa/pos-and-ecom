from django.contrib import admin
from .models import *
# Register your models here.

class OrderPaymentAdmin(admin.ModelAdmin):
    model = OrderPayment



class ShipmentPaymentAdmin(admin.ModelAdmin):
    model = ShipmentPayment




class CashPaymentAdmin(admin.ModelAdmin):
    model = CashPayment


class CreditPaymentAdmin(admin.ModelAdmin):
    model = CreditPayment        


class WalletPaymentAdmin(admin.ModelAdmin):
    model = WalletPayment        



class OnlinePaymentAdmin(admin.ModelAdmin):
    model = OnlinePayment            


admin.site.register(OrderPayment,OrderPaymentAdmin)
admin.site.register(ShipmentPayment,ShipmentPaymentAdmin)
admin.site.register(CashPayment,CashPaymentAdmin)
admin.site.register(CreditPayment,CreditPaymentAdmin)
admin.site.register(WalletPayment,WalletPaymentAdmin)
admin.site.register(OnlinePayment,OnlinePaymentAdmin)
