from django.contrib import admin
from .models import Order,Cart,OrderShipment,CartProductMapping,CarOrderShipmentMapping,OrderShipment
from products.models import Product
from django import forms
from django.utils.translation import ugettext_lazy as _


# class ProjectGroupMembershipInlineForm(forms.ModelForm):
#
#     class Meta:
#         model = CartProductMapping
#         fields = ('cart_products','cart_qty','cart_price',)
#
#     def __init__(self, *args, **kwargs):
#         super(ProjectGroupMembershipInlineForm, self).__init__(*args, **kwargs)
#         print(self.instance.id)
#         self.fields['cart_products'].queryset = Product.objects.exclude(id=self.instance.id)


class CartProductMappingAdmin(admin.TabularInline):
    model = CartProductMapping
    #readonly_fields = ('get_edit_link',)

class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductMappingAdmin]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(CartAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'cart_products':
            #print(db_field.name)
            if self.obj is not None:
                field.queryset = field.queryset.filter(cart_products__exact=self.obj)
            else:
                field.queryset = field.queryset.none()

        return field

    # def get_form(self, request, obj=None, **kwargs):
    #     print("mmmkkk")
    #     print(obj)
    #     request.current_object = obj
    #     return super(CartAdmin, self).get_form(request, obj, **kwargs)

admin.site.register(Cart,CartAdmin)
admin.site.register(CartProductMapping)


from django.utils.functional import curry
from django.forms import formset_factory
#from django import OrderShipmentFrom
from django.forms import BaseFormSet
from django.forms.models import BaseModelFormSet ,BaseInlineFormSet
from .forms import OrderShipmentFrom


class BaseArticleFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return
        titles = []
        for form in self.forms:
            title = form.cleaned_data['title']
            titles.append(title)

    def __init__(self):
        print(self)


class ItemInlineFormSet(BaseInlineFormSet):
   def clean(self):
        super(ItemInlineFormSet, self).clean()
        total = 0
        for form in self.forms:
            if not form.is_valid():
                return #other errors exist, so don't bother
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                total += form.cleaned_data['delivered_qty']
        self.instance.__total__ = total
        print(self.instance.__total__)

class OrderShipmentAdmin(admin.TabularInline):
    model = OrderShipment
    extra = 3


    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(OrderShipmentAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        print(db_field.name)
        print(request.POST.get('cart'))
        if db_field.name == 'cart_products':
            #print(db_field.name)
            if self.obj is not None:
                field.queryset = field.queryset.filter(cart_products__exact=self.obj)
            else:
                field.queryset = field.queryset.none()

        return field


    # def get_formset(self, request, obj=None, **kwargs):
    #     initial = []
    #     if request.method == "GET":
    #         initial.append({
    #             'delivered_qty': 2,
    #             'changed_price': 2,
    #             'manufacture_date': '1912-06-23',
    #             'expiry_date': '1912-06-23',
    #         })
    #     formset = super(OrderShipmentAdmin, self).get_formset(request, obj, **kwargs)
    #     formset.__init__ = curry(formset.__init__, initial=initial)
    #     return formset

    # def get_formset(self, request, obj=None, **kwargs):
    #     initial = []
    #     print(dir(self.parent_model))
    #     print(self)
    #     print("---111111111111-------------1111")
    #     print(dir(obj))
    #     print(obj)
    #     print("---222222222222-------------22222")
    #     print(dir(kwargs))
    #     print(kwargs.get)
    #     #print(dir(kwargs))
    #     #ArticleFormSet = formset_factory(OrderShipmentFrom, min_num=3, validate_min=True)
    #     ArticleFormSet = formset_factory(OrderShipmentFrom, formset=BaseArticleFormSet)
    #     data = {
    #         #'cart_product_ship': '2',
    #         #'car_order_shipment_mapping': '2',
    #         'delivered_qty': 2,
    #         'changed_price': 2,
    #         'manufacture_date': '1912-06-23',
    #         'expiry_date': '1912-06-23',
    #     }
    #     formset = ArticleFormSet(data)
    #     #formset.is_valid()
    #     #ArticleFormSet.clean('foo')
    #
    #     formset = super(OrderShipmentAdmin, self).get_formset(request, obj, **kwargs)
    #     formset.__init__ = curry(formset.__init__, initial=initial)
    #     return formset

class CarOrderShipmentMappingAdmin(admin.ModelAdmin):
    inlines = [OrderShipmentAdmin]

    #fk_name = 'cart'
    #exclude = ('ordered_shipment',)
    #list_display = ('')

    def get_form(self, request, obj=None, **kwargs):
        print(self)
        cart = request.GET.get('cart', '')

        #request.current_object = obj
        return super(CarOrderShipmentMappingAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(CarOrderShipmentMapping,CarOrderShipmentMappingAdmin)
#admin.site.register(Order,CarOrderShipmentMappingAdmin)

admin.site.register(Order)

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




