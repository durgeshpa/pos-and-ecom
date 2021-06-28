from django.contrib import admin
from django.utils.html import format_html
from django_admin_listfilter_dropdown.filters import ChoiceDropdownFilter
from rangefilter.filter import DateTimeRangeFilter

from franchise.models import FranchiseSales
from global_config.models import GlobalConfig
from retailer_to_sp.models import Order, OrderedProduct
from rest_auth.utils import AutoUser

from .models import Referral, RewardPoint, RewardLog, ReferralCode
from .forms import RewardPointForm, MLMUserForm
from .filters import UserFilter, MlmUserAutocomplete, ReferralToUserFilter, ReferralByUserFilter, RewardUserFilter,\
    ReferralCodeFilter


@admin.register(ReferralCode)
class MLMUserAdmin(admin.ModelAdmin):
    form = MLMUserForm
    list_display = ('user', 'email', 'referral_code', 'registered_at')
    fields = ('user', 'referral_code')
    list_filter = [UserFilter, ReferralCodeFilter]
    list_per_page = 10

    @staticmethod
    def email(obj):
        return obj.user.email if obj.user.email else '-'

    @staticmethod
    def registered_at(obj):
        return obj.created_at

    def save_model(self, request, obj, form, change):
        user_obj = AutoUser.create_update_user(form.cleaned_data.get('phone_number'),
                                               form.cleaned_data.get('email'),
                                               form.cleaned_data.get('name'))
        ReferralCode.register_user_for_mlm(user_obj, request.user, form.cleaned_data.get('referral_code'))

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referral_to_user', 'referral_by_user', 'created_at']
    fields = ('referral_to_user', 'referral_by_user')
    list_per_page = 10
    list_filter = [ReferralByUserFilter, ReferralToUserFilter]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        pass


@admin.register(RewardPoint)
class RewardPointAdmin(admin.ModelAdmin):
    form = RewardPointForm
    list_display = ("reward_user", "redeemable_reward_points", "max_available_discount_inr", "email_id", "created_at",
                    "modified_at", "direct_users", "indirect_users", "direct_earned", "indirect_earned", "points_used")
    list_filter = [RewardUserFilter]
    list_per_page = 10

    try:
        conf_obj = GlobalConfig.objects.get(key='used_reward_factor')
        used_reward_factor = int(conf_obj.value)
    except:
        used_reward_factor = 4

    @staticmethod
    def email_id(obj):
        return obj.reward_user.email if obj.reward_user.email else '-'

    def max_available_discount_inr(self, obj):
        max_av = int((obj.direct_earned + obj.indirect_earned - obj.points_used) / self.used_reward_factor)
        return format_html('<b>%s</b>' % max_av)

    @staticmethod
    def redeemable_reward_points(obj):
        rrp = obj.direct_earned + obj.indirect_earned - obj.points_used
        return format_html('<b>%s</b>' % rrp)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RewardPointAdmin, self).get_urls()
        urls = [
                   url(
                       r'^mlm-user-autocomplete/$',
                       self.admin_site.admin_view(MlmUserAutocomplete.as_view()),
                       name="mlm-user-autocomplete"
                   ),
               ] + urls
        return urls

    class Media:
        pass


@admin.register(RewardLog)
class RewardLogAdmin(admin.ModelAdmin):
    list_display = ('reward_user', 'transaction_type', 'transaction_id', 'transaction_points', 'created_at', 'discount',
                    'changed_by', 'purchase_user', 'purchase_invoice', 'user_purchase_shop_location')
    fields = list_display
    list_filter = [RewardUserFilter, ('transaction_type', ChoiceDropdownFilter), ('created_at', DateTimeRangeFilter)]
    list_per_page = 10

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def transaction_points(obj):
        return obj.points

    @staticmethod
    def purchase_user(obj):
        if obj.transaction_type in ['used_reward', 'purchase_reward', 'order_credit', 'order_debit',
                                    'order_return_credit', 'order_return_debit', 'order_cancel_credit',
                                    'order_cancel_debit']:
            return obj.reward_user
        if obj.transaction_type in ['direct_reward', 'indirect_reward']:
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.phone_number if sales_obj else '-'
        if obj.transaction_type in ['order_indirect_credit']:
            order = Order.objects.get(order_no=obj.transaction_id)
            return order.buyer
        return '-'

    @staticmethod
    def user_purchase_shop_location(obj):
        if obj.transaction_type in ['direct_reward', 'indirect_reward', 'purchase_reward']:
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.shop_loc if sales_obj else '-'
        if obj.transaction_type in ['order_indirect_credit', 'order_credit', 'order_debit',
                                    'order_cancel_credit', 'order_cancel_debit']:
            order = Order.objects.get(order_no=obj.transaction_id)
            return order.seller_shop
        if obj.transaction_type in ['order_return_credit', 'order_return_debit']:
            order = Order.objects.get(rt_return_order__id=obj.transaction_id)
            return order.seller_shop
        return '-'

    @staticmethod
    def purchase_invoice(obj):
        if obj.transaction_type in ['direct_reward', 'indirect_reward', 'purchase_reward']:
            sales_obj = FranchiseSales.objects.filter(pk=obj.transaction_id).last()
            return sales_obj.invoice_number if sales_obj else '-'
        if obj.transaction_type in ['order_indirect_credit', 'order_credit', 'order_debit',
                                    'order_cancel_credit', 'order_cancel_debit']:
            order = OrderedProduct.objects.get(order__order_no=obj.transaction_id)
            return order.invoice_no
        if obj.transaction_type in ['order_return_credit', 'order_return_debit']:
            order = OrderedProduct.objects.get(order__rt_return_order__id=obj.transaction_id)
            return order.invoice_no
        return '-'

    def get_urls(self):
        from django.conf.urls import url
        urls = super(RewardLogAdmin, self).get_urls()
        urls = [
                   url(
                       r'^mlm-user-autocomplete/$',
                       self.admin_site.admin_view(MlmUserAutocomplete.as_view()),
                       name="mlm-user-autocomplete"
                   ),
               ] + urls
        return urls

    class Media:
        pass
