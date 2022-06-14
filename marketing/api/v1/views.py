from rest_framework.generics import GenericAPIView
from rest_framework import status
import logging
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_auth.authentication import TokenAuthentication
from django.core.exceptions import ObjectDoesNotExist
from products.common_function import get_response

from marketing.models import RewardPoint, Profile, UserRating, UserWishlist
from products.models import Product
from shops.models import Shop
from marketing.serializers import RewardsSerializer, ProfileUploadSerializer, UserWishlistSerializer
info_logger = logging.getLogger('file-info')


class RewardsDashboard(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def get(self, request):
        """
            All Reward Credited/Used Details For User
        """
        user = self.request.user
        user_name = user.first_name if user.first_name else ''
        try:
            rewards_obj = RewardPoint.objects.get(reward_user=user)
        except ObjectDoesNotExist:
            data = {"direct_users_count": '0', "indirect_users_count": '0', "direct_earned_points": '0',
                    "indirect_earned_points": '0', "total_earned_points": '0', 'total_points_used': '0',
                    'remaining_points': '0', 'welcome_reward_point': '0', "discount_point": '0'}
        else:
            data = RewardsSerializer(rewards_obj).data
        data['name'] = user_name.capitalize()
        return Response({'is_success': True, 'message': ['Success'], 'response_data': data}, status=status.HTTP_200_OK)


class UploadProfile(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ProfileUploadSerializer

    def post(self, request):
        """
            Update User Profile
        """
        try:
            profile = Profile.objects.get(profile_user=self.request.user)
        except ObjectDoesNotExist:
            return Response({'is_success': False, 'message': ['User Profile Not Found'], 'response_data': None},
                            status=status.HTTP_200_OK)

        serializer = ProfileUploadSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'is_success': True, 'message': ['Successfully Updated Profile'],
                             'response_data': serializer.data}, status=status.HTTP_200_OK)
        else:
            errors = self.serializer_errors(serializer.errors)
            msg = {'is_success': False, 'message': [error for error in errors], 'response_data': None}
            return Response(msg, status=status.HTTP_406_NOT_ACCEPTABLE)

    @staticmethod
    def serializer_errors(serializer_errors):
        errors = []
        for field in serializer_errors:
            for error in serializer_errors[field]:
                if 'non_field_errors' in field:
                    result = error
                else:
                    result = ''.join('{} : {}'.format(field, error))
                errors.append(result)
        return errors


class RatingFeedback(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        """
            Store ratings given by user
        """
        user = self.request.user
        pop_up = self.request.data.get("pop_up")
        rating = self.request.data.get("rating")
        code = 1
        msg = ""
        try:
            if pop_up:
                ratingobj = UserRating.objects.filter(user=user).last()
                if not ratingobj or ratingobj.rating < 4:
                    msg = "Show PopUp Rating Screen"
                    code = 2
                    return get_response(msg, data=code)
                msg = "Don't Show PopUp Rating Screen"
                return get_response(msg, data=code)
            else:
                if int(rating) > 3:
                    ratingobj = UserRating.objects.filter(user=user).last()
                    if not ratingobj or ratingobj.rating < 4:
                        msg = "We are glad you're enjoying our app. Please rate us on Playstore"
                        code = 2
                else:
                    msg = "Oh! Help us to assist you better!"
                    code = 3
                if code != 1:
                    UserRating.objects.create(
                        user=user,
                        rating=int(rating),
                    )
                    return get_response(msg, data=code)
                return get_response(msg, data=code)
        except:
            info_logger.info("User rating not created for user :: {}".format(user))


    def put(self, request):
        """
            Update feedback given by user
        """
        user = self.request.user
        feedback = self.request.data.get("feedback")
        try:
            if feedback:
                ratingobj = UserRating.objects.filter(user=user).last()
                if ratingobj:
                    ratingobj.feedback = feedback
                    ratingobj.save()
                return get_response("Feedback updated")

        except:
            info_logger.info("User feedback not created for user :: {} with id :: {}".format(user, ratingobj.id))


def api_response(msg, data=None, status_code=status.HTTP_406_NOT_ACCEPTABLE, success=False, extra_params=None):
    ret = {"is_success": success, "message": msg, "response_data": data}
    if extra_params:
        ret.update(extra_params)
    return Response(ret, status=status_code)


class Wishlist(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = UserWishlistSerializer

    def post(self, request):
        """
            Add products to wishlist
        """
        user = self.request.user
        product_id = int(self.request.data.get("id"))
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')

        if app_type == '4':
            productobj = Product.objects.filter(id=product_id).last()
            if productobj:
                try:
                    wishobj = UserWishlist.objects.get(user=user, gf_prod_id=productobj, app_type=app_type)
                    if wishobj:
                        wishobj.is_active = True
                        wishobj.save()
                    return get_response("Product saved to wishlist", success=True)
                except:
                    gf_prod_id = productobj
                    UserWishlist.objects.create(
                        user=user,
                        app_type=app_type,
                        gf_prod_id=gf_prod_id
                    )
                    msg = "Added to Wishlist"
                    return get_response(msg, success=True)




    def get(self, request):
        """
            Get all wishlist products for any user
        """
        user = self.request.user
        offset = int(self.request.GET.get('offset', 0))
        pro_count = int(self.request.GET.get('pro_count', 10))
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')

        try:
            shop = Shop.objects.get(id=request.META.get('HTTP_SHOP_ID', None), shop_type__shop_type='f', status=True,
                                    approval_status=2, pos_enabled=1)
        except:
            return api_response("Shop not available!")
        parent_shop_id = shop.get_shop_parent
        if not parent_shop_id:
            return api_response("shop parent not mapped")
        parent_shop_id = parent_shop_id.id

        if app_type == '4':
            wishobj = UserWishlist.objects.filter(user=user, app_type=app_type, is_active=True)[offset:offset+pro_count]
            if wishobj:
                data = UserWishlistSerializer(wishobj, many=True, context={'parent_shop_id': parent_shop_id}).data
                msg = "Product count : " + str(wishobj.count())
                return Response({'is_success': True, 'message': msg, 'response_data': data},
                                status=status.HTTP_200_OK)
            else:
                msg = "Oh no!, Your Wishlist is empty! Just click <3 on products to save them to your wishlist"
                return Response({'is_success': True, 'message': msg},
                                status=status.HTTP_200_OK)


    def put(self, request):
        """
            Removes product from wishlist
            Set is_active = False
        """
        user = self.request.user
        product_id = int(self.request.data.get("id"))
        app_type = self.request.META.get('HTTP_APP_TYPE', '1')
        try:
            if app_type == '4':
                if product_id:
                    wishobj = UserWishlist.objects.filter(user=user, gf_prod_id__id=product_id, app_type=app_type).last()
                    if wishobj:
                        wishobj.is_active = False
                        wishobj.save()
                    return get_response("Product removed from wishlist", success=True)
        except Exception as e:
            info_logger.error("Wishlist item not removed :: {}".format(e))
