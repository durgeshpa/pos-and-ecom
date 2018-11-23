from django.contrib import admin
from .models import Cart,CartProductMapping,Order,OrderedProduct,OrderedProductMapping,Note
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping

# Register your models here.
class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    autocomplete_fields = ('cart_product',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        #print(db_field)
        if db_field.name == 'cart_product':
            pass
            #kwargs['queryset'] = Product.objects.filter(product_grn_order_product__delivered_qty__gt=0)
            #print(Product.objects.filter(product_grn_order_product__delivered_qty__gt=0).product_grn_order_product)
            #print(GRNOrderProductMapping.objects.filter(delivered_qty__gt=0).query)
        return super(CartProductMappingAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]
    exclude = ('order_id', 'shop', 'cart_status','last_modified_by')
    list_display = ('order_id', 'cart_status')

    change_form_template = 'admin/sp_to_gram/cart/change_form.html'

    def save_formset(self, request, form, formset, change):
        import datetime
        today = datetime.date.today()
        instances = formset.save(commit=False)
        flag = 0
        new_order = ''
        for instance in instances:

            print(instance)
            instance.last_modified_by = request.user
            instance.save()
            print(instance.cart)

            order,_ = Order.objects.get_or_create(ordered_cart=instance.cart,order_no=instance.cart.order_id)
            order.ordered_by=request.user
            order.order_status='ordered_to_gram'
            order.last_modified_by=request.user
            order.save()


        # if request.user.groups.filter(name='grn_brand_to_gram_group').exists():
        #     if new_order and CartToBrand.objects.filter(order_brand=new_order):
        #         new_order.order_status = 'partially_delivered'
        #     elif new_order:
        #         new_order.order_status = 'delivered'
        #     new_order.save()
        formset.save_m2m()

admin.site.register(Cart,CartAdmin)

class OrderAdmin(admin.ModelAdmin):
    search_fields = ('order',)
    list_display = ('order_no','order_status',)

admin.site.register(Order,OrderAdmin)

class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    exclude = ('last_modified_by',)

class OrderedProductAdmin(admin.ModelAdmin):
    inlines = [OrderedProductMappingAdmin]
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by')
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)

admin.site.register(OrderedProduct,OrderedProductAdmin)

class NoteAdmin(admin.ModelAdmin):
    list_display = ('order','ordered_product','note_type', 'amount', 'created_at')

admin.site.register(Note,NoteAdmin)
