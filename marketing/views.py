from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from marketing.models import MLMUser


class GetUniqueReferralCode(GenericAPIView):
    def get(self, id, *args, **kwargs):
        """
        It will return the referral code of the user by checking the id
        """
        try:
            queryset = MLMUser.objects.filter(id=id).values_list('referral_code')
            if queryset[0][0]:
                referral_code = queryset[0]
                return Response(data={"message":"Success", "referral_code": referral_code}, status=status.HTTP_201_CREATED)
            else:
                return Response(data={"message":"No referral code exists! Please provide a valid ID"},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(data="Something Went Wrong" + str(e), status=status.HTTP_400_BAD_REQUEST)
