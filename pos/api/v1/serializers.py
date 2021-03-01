from rest_framework import serializers

from products.models import Product, ProductImage
from pos.models import RetailerProduct, RetailerProductImage

class ProductImageSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductImage
      fields = ('image_name', 'image_alt_text', 'image')


class RetailerProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerProductImage
        fields = ('image_name', 'image_alt_text', 'image')


class ProductDetailSerializer(serializers.ModelSerializer):
    product_pro_image = ProductImageSerializer(many=True)

    class Meta:
        model = Product
        fields = ('product_name','product_short_description','product_mrp', 'product_pro_image')


class RetailerProductsSearchSerializer(serializers.ModelSerializer):
    """
        Serializer for Cart Products, RetailerProduct data for BASIC cart
    """
    product_pro_image = serializers.SerializerMethodField('product_pro_image_dt')
    product_opt_product = serializers.SerializerMethodField('product_opt_product_dt')
    product_case_size_picies = serializers.SerializerMethodField('product_case_size_picies_dt')
    margin = serializers.SerializerMethodField('margin_dt')
    loyalty_discount = serializers.SerializerMethodField('loyalty_discount_dt')
    cash_discount = serializers.SerializerMethodField('cash_discount_dt')

    def product_pro_image_dt(self, obj):
        """
            Image field to keep cart response same for all types
        """
        qs = RetailerProductImage.objects.filter(product=obj)
        return RetailerProductImageSerializer(qs, many=True).data

    def product_case_size_picies_dt(self, obj):
        """
            returning product pieces - 1 for now
        """
        return str(int(obj.product_inner_case_size) * int(obj.product_case_size))

    def loyalty_discount_dt(self, obj):
        return 0

    def cash_discount_dt(self, obj):
        return 0

    def margin_dt(self, obj):
        return ((obj.mrp - obj.selling_price) / obj.mrp) * 100

    def product_opt_product_dt(self, obj):
        return []

    class Meta:
        model = RetailerProduct
        fields = ('id','product_name','product_slug','product_short_description','product_long_description','product_sku',
                  'product_mrp', 'product_ean_code','created_at','modified_at','status','product_pro_image',
                  'product_opt_product','product_price','product_inner_case_size','product_case_size','product_case_size_picies',
                  'margin', 'loyalty_discount', 'cash_discount')