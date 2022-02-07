#from dal import autocomplete_light

from django.contrib import admin
from django.db.models import Case, CharField, Value, When, F, Sum, Q
from retailer_backend.admin import InputFilter

from .models import *
from .forms import ShipmentPaymentForm, ShipmentPaymentInlineForm, \
    PaymentForm, OrderPaymentForm, PaymentApprovalForm, ShipmentPaymentInlineFormFactory
from .views import UserWithNameAutocomplete

#from .forms import ShipmentPaymentApprovalForm
from django.utils.safestring import mark_safe
from django.forms.models import BaseInlineFormSet

from retailer_to_sp.models import Shipment, Trip


# Register your models here.


class PermissionMixin:

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def has_add_permission(self, request):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False


# class OnlinePaymentInlineAdmin(admin.TabularInline):
#     model = OnlinePayment
#     form = OnlinePaymentInlineForm


class OrderNoSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            if order_no is None:
                return
            return queryset.filter(
                Q(order__order_no__icontains=order_no)
            )


class OrderPaymentAdmin(admin.ModelAdmin, PermissionMixin):
    model = OrderPayment
    form  = OrderPaymentForm
    list_per_page = 25
    #autocomplete_fields = ('order', 'parent_payment', 'created_by', 'updated_by',)
    search_fields = ('order__order_no', 'parent_payment__payment_id')
    readonly_fields = (
       "payment_id",
    )
    list_filter = (OrderNoSearch,  'parent_payment__payment_mode_name', )


class ReferenceNoSearch(InputFilter):
    parameter_name = 'reference_no'
    title = 'Reference No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            reference_no = self.value()
            if reference_no is None:
                return
            return queryset.filter(
                Q(reference_no__icontains=reference_no)
            )


class PaymentImageAdmin(admin.ModelAdmin, PermissionMixin):
    # inlines = [OnlinePaymentInlineAdmin]
    model = PaymentImage


class PaymentAdmin(admin.ModelAdmin, PermissionMixin):
    # inlines = [OnlinePaymentInlineAdmin]
    model = Payment
    list_per_page = 25
    autocomplete_fields = ('paid_by',)
    search_fields = ('paid_amount', "paid_by__phone_number", "payment_id",)
    form  = PaymentForm
    list_display = (
        "paid_by", "paid_amount", "payment_mode_name",  "online_payment_type", "reference_no", "description",
        "payment_id", "order_number", "invoice_number"            
        )
    fields = (
        "paid_by", "paid_amount", "payment_mode_name", "reference_no", "description",
        "online_payment_type", "payment_id", "payment_screenshot", "processed_by"
    )
    list_filter = ("payment_mode_name",  "online_payment_type", ReferenceNoSearch, )

    readonly_fields = (
       "payment_id",
    )

    def order_number(self,obj):
        return obj.orders()
    order_number.short_description = 'Order Nos'

    def invoice_number(self,obj):
        return obj.shipments()
    invoice_number.short_description = 'Invoice Nos'

    # def get_inline_instances(self, request, obj=None):
    #     if not obj or obj.payment_mode_name != "online_payment": return []
    #     return super(PaymentAdmin, self).get_inline_instances(request, obj)

    def get_urls(self):
        from django.conf.urls import url
        urls = super(PaymentAdmin, self).get_urls()
        urls = [
            url(
                r'^userwithname-autocomplete/$',
                self.admin_site.admin_view(UserWithNameAutocomplete.as_view()),
                name="userwithname-autocomplete"
            ),
        ] + urls
        return urls

    class Media:
        js = ('admin/js/hide_admin_fields_payment.js',)



class PaymentModeAdmin(admin.ModelAdmin):
    model = PaymentMode


class ShipmentOrderNoSearch(InputFilter):
    parameter_name = 'order_no'
    title = 'Order No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            order_no = self.value()
            if order_no is None:
                return
            return queryset.filter(
                Q(shipment__order__order_no__icontains=order_no)
            )


class InvoiceNoSearch(InputFilter):
    parameter_name = 'invoice_no'
    title = 'Invoice No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            invoice_no = self.value()
            if invoice_no is None:
                return
            return queryset.filter(
                Q(shipment__invoice__invoice_no__icontains=invoice_no)
            )

class DispatchNoSearch(InputFilter):
    parameter_name = 'dispatch_no'
    title = 'Dispatch No.'

    def queryset(self, request, queryset):
        if self.value() is not None:
            dispatch_no = self.value()
            if dispatch_no is None:
                return
            return queryset.filter(
                Q(shipment__trip__dispatch_no__icontains=invoice_no)
            )



class ShipmentPaymentAdmin(admin.ModelAdmin, PermissionMixin):
    model = ShipmentPayment
    search_fields = ('shipment__invoice__invoice_no', 'parent_order_payment__order__order_no',)
    #fields = ("shipment",) #, "is_payment_approved")
    raw_id_fields = ("shipment",)
    list_display = (
        "shipment", "parent_order_payment", "paid_amount",            
        )
    list_select_related = ("shipment__trip",)
    # - a)Order b)Trip c)Invoice No d)Invoice city
    list_filter = (ShipmentOrderNoSearch,  InvoiceNoSearch, DispatchNoSearch, )


class NoDeleteAdminMixin:
    def has_delete_permission(self, request, obj=None):
        
        return False

# class OnlinePaymentAdmin1(admin.ModelAdmin):
#     model = OnlinePayment


class PaymentApprovalAdmin(admin.ModelAdmin, PermissionMixin):# NoDeleteAdminMixin, 
    form = PaymentApprovalForm
    model = PaymentApproval
    list_per_page = 25
    list_display = (
        "id", "reference_no", "payment_approval_status", "paid_amount",
        "retailer", "payment_mode_name", "order_number", "invoice_number" 
        #"payment_received"
    )

    fields = (
        "retailer", "processed_by", "paid_amount", "payment_mode_name",
        "reference_no", "is_payment_approved", "payment_approval_status", #"payment_received",
        "description", "payment_screenshot"
    )
    
    readonly_fields = (
        "retailer", "processed_by", "paid_amount", "payment_mode_name", 
        "reference_no", "payment_screenshot" #"payment_approval_status",
    )
    list_filter = ("payment_mode_name",  "online_payment_type", ReferenceNoSearch, )

    #list_filter = ['picking_status', PickerBoyFilter, PicklistIdFilter, OrderNumberSearch,('created_at', DateTimeRangeFilter),]
    # raw_id_fields = ("shipment",)
    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def order_number(self,obj):
        return obj.orders()
    order_number.short_description = 'Order Nos'

    def invoice_number(self,obj):
        return obj.shipments()
    invoice_number.short_description = 'Invoice Nos'

    def order(self, obj):
        shipment_payment = ShipmentPayment.objects.get(parent_payment=obj)
        return mark_safe("<a href='/admin/retailer_to_sp/order/%s/change/'>%s<a/>" % (order.id,
                  order.order_no)
                         )

    def retailer(self, obj):
        return obj.paid_by

    def get_queryset(self, request):
        qs = super(PaymentApprovalAdmin, self).get_queryset(request)
        return qs.exclude(
            Q(payment_mode_name = "cash_payment") 
                ).order_by('-created_at')


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


class ShipmentPaymentInlineAdmin(admin.TabularInline, PermissionMixin):
    model = ShipmentPayment
    form = ShipmentPaymentInlineForm
    formset = AtLeastOneFormSet
    fields = ("paid_amount", "parent_order_payment", "payment_mode_name", "reference_no", "description",
              "payment_approval_status")
    readonly_fields = ("paid_amount", "payment_mode_name", "reference_no", "payment_approval_status")
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent_order_payment":
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
                kwargs["queryset"] = OrderPayment.objects.filter(order=parent_obj.order)
            except IndexError:
                pass
        return super(
            ShipmentPaymentInlineAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request, obj=None):
        try:
            parent_obj_id = request.resolver_match.kwargs['object_id']
            parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
            if parent_obj.trip.trip_status in [Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED]:
                return False
            else: 
                return True
        except: 
            return True

    def has_change_permission(self, request, obj=None):
        try:
            parent_obj_id = request.resolver_match.kwargs['object_id']
            parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
            if parent_obj.trip.trip_status in [Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED]:
                return False
            else: 
                return True
        except: 
            return True

    def payment_approval_status(self,obj):
        return obj.parent_order_payment.parent_payment.payment_approval_status
    payment_approval_status.short_description = 'Payment Approval Status'

    def payment_mode_name(self,obj):
        return obj.parent_order_payment.parent_payment.payment_mode_name
    payment_mode_name.short_description = 'Payment Mode'

    def reference_no(self,obj):
        return obj.parent_order_payment.parent_payment.reference_no
    reference_no.short_description = 'Reference No'

    def description(self,obj):
        return obj.description
    description.short_description = 'Description'

    def has_delete_permission(self, request, obj=None):
        return False


def ShipmentPaymentInlineAdminFactory(user_id, object_id=None):
    class ShipmentPaymentInlineAdmin(admin.TabularInline, PermissionMixin):
        model = ShipmentPayment
        form = ShipmentPaymentInlineFormFactory(user_id, object_id)
        formset = AtLeastOneFormSet
        #autocomplete_fields = ("parent_order_payment",)
        fields = ("parent_order_payment", "description", "paid_amount", "payment_mode_name", "reference_no",
                  "payment_approval_status")
        # fieldsets = (
        #     (None, {'fields': ("paid_amount", "parent_order_payment", "payment_mode_name", "reference_no",
        #                        "description", "payment_approval_status")}),
        # )
        readonly_fields = ("paid_amount", "payment_mode_name", "reference_no", "payment_approval_status")
        extra = 0

        class Media:
            js = ("js/shipment_payment_add_another.js",)

        def formfield_for_foreignkey(self, db_field, request, **kwargs):
            if db_field.name == "parent_order_payment":
                try:
                    parent_obj_id = request.resolver_match.kwargs['object_id']
                    parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
                    kwargs["queryset"] = OrderPayment.objects.filter(order=parent_obj.order)
                except IndexError:
                    pass
            return super(
                ShipmentPaymentInlineAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

        def has_add_permission(self, request, obj=None):
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
                if parent_obj.trip.trip_status in [Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED]:
                    return False
                else:
                    return True
            except:
                return True

        def has_change_permission(self, request, obj=None):
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                parent_obj = OrderedProduct.objects.get(pk=parent_obj_id)
                if parent_obj.trip.trip_status in [Trip.RETURN_VERIFIED, Trip.PAYMENT_VERIFIED]:
                    return False
                else:
                    return True
            except:
                return True

        def payment_approval_status(self,obj):
            return obj.parent_order_payment.parent_payment.payment_approval_status
        payment_approval_status.short_description = 'Payment Approval Status'

        def payment_mode_name(self,obj):
            return obj.parent_order_payment.parent_payment.payment_mode_name
        payment_mode_name.short_description = 'Payment Mode'

        def reference_no(self,obj):
            return obj.parent_order_payment.parent_payment.reference_no
        reference_no.short_description = 'Reference No'

        def description(self,obj):
            return obj.description
        description.short_description = 'Description'

        def has_delete_permission(self, request, obj=None):
            return False
    return ShipmentPaymentInlineAdmin


class ShipmentPaymentDataAdmin(admin.ModelAdmin, PermissionMixin):
    inlines = [ShipmentPaymentInlineAdmin]
    model = ShipmentData
    list_display = ('order', 'trip', 'invoice_no', 'invoice_amount', 'total_paid_amount', 'invoice_city')
    list_per_page = 50
    fields = ['order', 'trip', 'trip_status', 'invoice_no', 'invoice_amount', 'total_paid_amount', 'shipment_address',
              'invoice_city', 'shipment_status', 'no_of_crates', 'no_of_packets', 'no_of_sacks']
    readonly_fields = ['order', 'trip', 'trip_status', 'invoice_no', 'invoice_amount', 'total_paid_amount',
                       'shipment_address', 'invoice_city', 'shipment_status', 'no_of_crates', 'no_of_packets',
                       'no_of_sacks']

    # we define inlines with factory to create Inline class with request inside
    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.inlines = (ShipmentPaymentInlineAdminFactory(request.user.id, object_id),)
        return super(ShipmentPaymentDataAdmin, self).change_view(request, object_id)

    # we define inlines with factory to create Inline class with request inside
    def add_view(self, request, form_url='', extra_context=None):
        self.inlines = (ShipmentPaymentInlineAdminFactory(request.user.id),)
        return super(ShipmentPaymentDataAdmin, self).add_view(request.user.id)

    def total_paid_amount(self,obj):
        return obj.total_paid_amount
    total_paid_amount.short_description = 'Total Paid Amount'

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm("payments.change_payment"):
            return True
        else:
            return False

    def has_add_permission(self, request, obj=None):
        return False

    def trip_status(self,obj):
        return obj.trip.trip_status
    trip_status.short_description = 'Trip Status'

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

# payments
admin.site.register(Payment,PaymentAdmin)
admin.site.register(OrderPayment,OrderPaymentAdmin)
admin.site.register(ShipmentPayment,ShipmentPaymentAdmin)

#admin.site.register(PaymentMode,PaymentModeAdmin)

# payment edit and approvals
admin.site.register(PaymentApproval,PaymentApprovalAdmin)
# admin.site.register(PaymentEdit,PaymentEditAdmin)
admin.site.register(ShipmentData,ShipmentPaymentDataAdmin)
admin.site.register(PaymentImage,PaymentImageAdmin)
#autocomplete_light.register(Payment, add_another_url_name='admin:payments_payment_add')