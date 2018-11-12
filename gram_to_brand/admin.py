from django.contrib import admin
from .models import Order,Cart,CartProductMapping,GRNOrder,GRNOrderProductMapping,OrderItem
from products.models import Product
from django import forms
from django.db.models import Sum
from django.utils.html import format_html


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)
    autocomplete_fields = ('cart_product',)

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status','last_modified_by')
    autocomplete_fields = ('brand',)
    list_display = ('order_id', 'cart_status')
    search_fields = ('brand__brand_name','state__state_name','supplier__shop_owner__first_name')


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
            order.order_status='ordered_to_brand'
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
    exclude = ('last_modified_by','available_qty',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        order_id = request.GET.get('odr')

        if db_field.name == 'product':
            kwargs['queryset'] = Product.objects.filter(product_order_item__order__id=order_id)

        return super(GRNOrderProductMappingAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class OrderItemAdmin(admin.ModelAdmin):
    search_fields = ('order__id','order__order_no','ordered_qty')
    date_hierarchy = 'created_at'
    list_display = ('order','ordered_product','ordered_qty','item_status','total_delivered_qty','total_returned_qty','total_damaged_qty',)

class GRNOrderAdmin(admin.ModelAdmin):
    inlines = [GRNOrderProductMappingAdmin]
    autocomplete_fields = ('order',)
    exclude = ('order_item','grn_id','last_modified_by',)
    #list_display_links = None
    list_display = ('order','invoice_no','grn_id','created_at','edit_grn_link')
    search_fields = ('order__order_no','invoice_no','grn_id')

    def edit_grn_link(self, obj):
        #return format_html("<ul class ='object-tools'><li><a href = '/admin/gram_to_brand/grnorder/add/?brand=%s' class ='addlink' > Add order</a></li></ul>"% (obj.id))
        return format_html("<a href = '/admin/gram_to_brand/grnorder/%s/change/?order=%s&odr=%s' class ='addlink' > Edit GRN</a>"% (obj.id,obj.id,obj.id))

    edit_grn_link.short_description = 'Edit GRN'
    
    def __init__(self, *args, **kwargs):
        super(GRNOrderAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    def get_form(self, request, obj=None, **kwargs):
        #request.current_object = obj
        return super(GRNOrderAdmin, self).get_form(request, obj, **kwargs)

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        order_id = 0
        for instance in instances:
            #GRNOrderProductMapping
            #Save OrderItem
            if OrderItem.objects.filter(order=instance.grn_order.order,ordered_product=instance.product).exists():
                order_item = OrderItem.objects.get(order=instance.grn_order.order, ordered_product=instance.product)
                if GRNOrderProductMapping.objects.filter(grn_order__order=instance.grn_order.order,product=instance.product).exists():
                    product_grouped_info = GRNOrderProductMapping.objects.filter(grn_order__order=instance.grn_order.order,product=instance.product)\
                        .aggregate(total_delivered_qty=Sum('delivered_qty'),total_returned_qty=Sum('returned_qty'),total_damaged_qty=Sum('damaged_qty'))

                    order_item.total_delivered_qty = product_grouped_info['total_delivered_qty']
                    order_item.total_returned_qty = product_grouped_info['total_returned_qty']
                    order_item.total_damaged_qty = product_grouped_info['total_damaged_qty']
                    if product_grouped_info['total_delivered_qty'] == order_item.ordered_qty:
                        order_item.item_status = 'delivered'
                    else:
                        order_item.item_status = 'partially_delivered'
                else:

                    order_item.total_delivered_qty = instance.delivered_qty
                    order_item.total_returned_qty = instance.returned_qty
                    order_item.total_damaged_qty = instance.damaged_qty
                    if instance.delivered_qty == order_item.ordered_qty:
                        order_item.item_status = 'delivered'
                    else:
                        order_item.item_status = 'partially_delivered'

                order_item.save()
                instance.grn_order.order.order_status='partially_delivered'
                instance.grn_order.order.save()
                order_id = instance.grn_order.order.id

                #instance.available_qty = instance.delivered_qty
                instance.save()
            #Update Order
        if order_id!= 0 and OrderItem.objects.filter(order=order_id).exists():
            order = Order.objects.get(id=order_id)
            order_item = OrderItem.objects.filter(order=order_id)
            order.order_status = 'partially_delivered' if order_item.filter(item_status='partially_delivered').count()>0 else 'delivered'
            order.save()

        formset.save_m2m()


class OrderAdmin(admin.ModelAdmin):
    search_fields = ('id','order_no')
    list_display = ('order_no','order_status','ordered_by','created_at','add_grn_link')

    def add_grn_link(self, obj):
        #return format_html("<ul class ='object-tools'><li><a href = '/admin/gram_to_brand/grnorder/add/?brand=%s' class ='addlink' > Add order</a></li></ul>"% (obj.id))
        return format_html("<a href = '/admin/gram_to_brand/grnorder/add/?order=%s&odr=%s' class ='addlink' > Add GRN</a>"% (obj.id,obj.id))

    add_grn_link.short_description = 'Do GRN'

admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(GRNOrder,GRNOrderAdmin)


from django.utils.functional import curry
from django.forms import formset_factory
#from django import OrderShipmentFrom
from django.forms import BaseFormSet
from django.forms.models import BaseModelFormSet ,BaseInlineFormSet
#from .forms import OrderShipmentFrom





