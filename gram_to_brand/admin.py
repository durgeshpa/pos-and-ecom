from django.contrib import admin
from .models import Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,OrderItem
from products.models import Product
from django import forms

class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)
    autocomplete_fields = ('cart_product',)

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status','last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('order_id', 'cart_status')


    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        flag = 0
        new_order = ''
        for instance in instances:

            instance.last_modified_by = request.user
            instance.save()
            print(instance.cart)
            #Save Order
            #order,_ = Order.objects.get_or_create(ordered_cart=instance.cart)
            order,_ = Order.objects.get_or_create(ordered_cart=instance.cart,order_no=instance.cart.order_id)
            order.ordered_by=request.user
            order.last_modified_by=request.user
            order.save()

            #Save OrderItem
            if OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).exists():
                OrderItem.objects.filter(order=order,ordered_product=instance.cart_product).delete()

            order_item = OrderItem()
            order_item.ordered_product = instance.cart_product
            order_item.ordered_qty = instance.qty
            order_item.ordered_price = instance.price

            order_item.order = order
            order_item.last_modified_by = request.user
            order_item.save()

            #instance.order_brand.ordered_by = request.user
            #instance.order_brand.order_status = 'ordered_to_brand'
            #nstance.order_brand.brand_order_id = 'BRAND/ORDER/' + str(instance.order_brand.id)
            #new_order = instance.order_brand

            #Order.objects.get_or_create('ordered_cart'=instance.cart_list)
            #instance.order_brand.save()
            #instance.cart_id = 'BRAND-' + "{%Y%m%d}".format(today) + "-" + instance.id
            #instance.shop = Shop.objects.get(name='Gramfactory')

        # if request.user.groups.filter(name='grn_brand_to_gram_group').exists():
        #     if new_order and CartToBrand.objects.filter(order_brand=new_order):
        #         new_order.order_status = 'partially_delivered'
        #     elif new_order:
        #         new_order.order_status = 'delivered'
        #     new_order.save()
        formset.save_m2m()

admin.site.register(Cart,CartAdmin)

class GRNOrderProductMappingAdmin(admin.TabularInline):
    model = GRNOrderProductMapping
    exclude = ('last_modified_by',)

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order','ordered_product','ordered_qty')



class GRNOrderAdmin(admin.ModelAdmin):
    inlines = [GRNOrderProductMappingAdmin]
    autocomplete_fields = ('order',)
    exclude = ('order_item','grn_id','last_modified_by',)
    list_display = ('order','invoice_no','grn_id','created_at')

    def get_form(self, request, obj=None, **kwargs):
        #request.current_object = obj
        return super(GRNOrderAdmin, self).get_form(request, obj, **kwargs)


class OrderAdmin(admin.ModelAdmin):
    search_fields = ('order',)

admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)


from django.utils.functional import curry
from django.forms import formset_factory
#from django import OrderShipmentFrom
from django.forms import BaseFormSet
from django.forms.models import BaseModelFormSet ,BaseInlineFormSet
#from .forms import OrderShipmentFrom





