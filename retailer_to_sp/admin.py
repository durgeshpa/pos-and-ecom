from django.contrib import admin
from .models import Cart,CartProductMapping,Order,OrderedProduct,OrderedProductMapping,Note, CustomerCare, Payment
from products.models import Product
from gram_to_brand.models import GRNOrderProductMapping
from django.utils.html import format_html
from django.urls import reverse
from .forms import CustomerCareForm
from django_select2.forms import Select2MultipleWidget,ModelSelect2Widget
from dal import autocomplete
from retailer_backend.admin import InputFilter
from django.db.models import Q

# Register your models here.
class NameSearch(InputFilter):
    parameter_name = 'name'
    title = 'Name'

    def queryset(self, request, queryset):
        if self.value() is not None:
            name = self.value()
            if name is None:
                return
            return queryset.filter(
                Q(name__icontains=name)
            )

class OrderIdSearch(InputFilter):
    parameter_name = 'order_id'
    title = 'Order Id'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_id = self.value()
            if order_id is None:
                return
            return queryset.filter(
                Q(order_id__order_no__icontains=order_id)
            )

class OrderStatusSearch(InputFilter):
    parameter_name = 'order_status'
    title = 'Order Status'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_status = self.value()
            if order_status is None:
                return
            return queryset.filter(
                Q(order_status__icontains=order_status)
            )

class IssueSearch(InputFilter):
    parameter_name = 'select_issue'
    title = 'Issue'

    def queryset(self, request, queryset):
        if self.value() is not None:
            select_issue = self.value()
            if select_issue is None:
                return
            return queryset.filter(
                Q(select_issue__icontains=select_issue)
            )

class PaymentChoiceSearch(InputFilter):
    parameter_name = 'payment_choice'
    title = 'Payment Mode'

    def queryset(self, request, queryset):
        if self.value() is not None:
            payment_choice = self.value()
            if payment_choice is None:
                return
            return queryset.filter(
                Q(payment_choice__icontains=payment_choice)
            )


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

    def get_queryset(self, request):
        qs = super(OrderAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(seller_shop__related_users=request.user) |
            Q(seller_shop__shop_owner=request.user)
                )

admin.site.register(Order,OrderAdmin)

class OrderedProductMappingAdmin(admin.TabularInline):
    model = OrderedProductMapping
    exclude = ('last_modified_by',)

class OrderedProductAdmin(admin.ModelAdmin):
    inlines = [OrderedProductMappingAdmin]
    list_display = ('invoice_no','vehicle_no','shipped_by','received_by','download_invoice')
    exclude = ('shipped_by','received_by','last_modified_by',)
    autocomplete_fields = ('order',)
    search_fields=('invoice_no','vehicle_no')

    def download_invoice(self,obj):
        #request = self.context.get("request")
        return format_html("<a href= '%s' >Download Invoice</a>"%(reverse('download_invoice_sp', args=[obj.pk])))
    download_invoice.short_description = 'Download Invoice'

    def get_queryset(self, request):
        qs = super(OrderedProductAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(order__seller_shop__related_users=request.user) |
            Q(order__seller_sho__shop_owner=request.user)
                )

admin.site.register(OrderedProduct,OrderedProductAdmin)

class NoteAdmin(admin.ModelAdmin):
    list_display = ('order','ordered_product','note_type', 'amount', 'created_at')

admin.site.register(Note,NoteAdmin)

class CustomerCareAdmin(admin.ModelAdmin):
    model=CustomerCare
    form = CustomerCareForm
    fields=('email_us','contact_us','order_id','order_status','select_issue','complaint_detail')
    exclude = ('name',)
    list_display=('name','order_id', 'order_status','select_issue')
    autocomplete_fields = ('order_id',)
    search_fields = ('name',)
    list_filter = [NameSearch, OrderIdSearch, OrderStatusSearch,IssueSearch]

admin.site.register(CustomerCare,CustomerCareAdmin)

class PaymentAdmin(admin.ModelAdmin):
    model= Payment
    fields= ('order_id', 'paid_amount','payment_choice', 'neft_reference_number', 'payment_status')
    exclude = ('name',)
    list_display=('name','order_id', 'paid_amount', 'payment_choice', 'neft_reference_number')
    autocomplete_fields = ('order_id',)
    search_fields = ('name',)
    list_filter = (NameSearch, OrderIdSearch, PaymentChoiceSearch)

admin.site.register(Payment,PaymentAdmin)
