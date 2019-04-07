from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import ShopType


class GetShopType(APIView):
	permission_classes = (AllowAny,)

	def get(self, *args, **kwargs):
		shop_type_id = self.request.GET.get('shop_type_id')
		if shop_type_id:
			shop_type = ShopType.objects.get(id=shop_type_id).shop_type
			return Response({
				"shop_type": shop_type,
				"success": True
			})
		return Response({
			"success": False
		})