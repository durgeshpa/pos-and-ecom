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


# class ItemInlineFormSet(BaseInlineFormSet):
#    def clean(self):
#         super(ItemInlineFormSet, self).clean()
#         total = 0
#         for form in self.forms:
#             if not form.is_valid():
#                 return #other errors exist, so don't bother
#             if form.cleaned_data and not form.cleaned_data.get('DELETE'):
#                 total += form.cleaned_data['delivered_qty']
#         self.instance.__total__ = total
#         print(self.instance.__total__)

# class OrderShipmentAdmin(admin.TabularInline):
#     model = OrderShipment
#     extra = 3
#     readonly_fields = ('car_order_shipment_mapping',)
#     #exclude = ()

# class CarOrderShipmentMappingAdmin(admin.ModelAdmin):
#     inlines = [OrderShipmentAdmin]
    #fk_name = 'cart'
    #exclude = ('ordered_shipment',)
    #list_display = ('')

    # def get_form(self, request, obj=None, **kwargs):
    #     print(self)
    #     cart = request.GET.get('cart', '')
    #
    #     #request.current_object = obj
    #     return super(CarOrderShipmentMappingAdmin, self).get_form(request, obj, **kwargs)


#admin.site.register(CarOrderShipmentMapping,CarOrderShipmentMappingAdmin)
#admin.site.register(Order,CarOrderShipmentMappingAdmin)



# class CartOrderMappingAdmin(admin.StackedInline):
#    #model = Cart.order.through
#    model = Order.ordered_cart.through
#
# class OrderShipmentMappingAdmin(admin.StackedInline):
#     model = Order.ordered_shipment.through
#
# class CartAdmin(admin.ModelAdmin):
#     inlines = [CartOrderMappingAdmin]
#
# class OrderAdmin(admin.ModelAdmin):
#     inlines = [CartOrderMappingAdmin,OrderShipmentMappingAdmin]
#     filter_horizontal = ['ordered_shipment']
#     #model = Order
#
# admin.site.register(Order,OrderAdmin)
#admin.site.register(CartAdmin,OrderAdmin)


# class OrderCartAdmin(admin.TabularInline):
#     model = Order
#
# class CartAdmin(admin.ModelAdmin):
#     inlines = [OrderCartAdmin]
#
# admin.site.register(Cart,CartAdmin)
# from django.contrib import admin
# from django.contrib.admin.views.main import ChangeList
# from .models import Order
# from .forms import OrderMappingForm
#
# class OrderChangeList(ChangeList):
#
#     def __init__(self, request, model, list_display,
#         list_display_links, list_filter, date_hierarchy,
#         search_fields, list_select_related, list_per_page,
#         list_max_show_all,list_editable, model_admin):
#
#         super(OrderChangeList, self).__init__(request, model,
#             list_display, list_display_links, list_filter,
#             date_hierarchy, search_fields, list_select_related,
#             list_per_page, list_max_show_all,list_editable, model_admin)
#
#         # these need to be defined here, and not in MovieAdmin
#         self.list_display = ['action_checkbox', 'ordered_shipment']
#         self.list_display_links = ['total_mrp']
#         self.list_editable = ['ordered_shipment',]
#
#     list_editable = ('ordered_shipment',)
#
# class OrderAdmin(admin.ModelAdmin):
#
#     def get_changelist_instance(self,request, **kwargs):
#         return OrderChangeList
#
#     def get_changelist(self, request, **kwargs):
#         return OrderChangeList
#
#     def get_changelist_form(self, request, **kwargs):
#         return OrderMappingForm
#
#
# admin.site.register(Order, OrderAdmin)
#




