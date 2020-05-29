from rest_framework import serializers
from wms.models import Bin, Putaway
from shops.api.v1.serializers import ShopSerializer
from retailer_to_sp.api.v1.serializers import ProductSerializer


class BinSerializer(serializers.ModelSerializer):
    warehouse = ShopSerializer()

    class Meta:
        model = Bin
        fields = ('id','warehouse', 'bin_id', 'bin_type', 'is_active', 'bin_barcode', 'created_at', 'modified_at')


class DynamicFieldsModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            not_allowed = set(exclude)
            for exclude_name in not_allowed:
                self.fields.pop(exclude_name)


class PutAwaySerializer(DynamicFieldsModelSerializer):
    warehouse = ShopSerializer()
    sku = ProductSerializer()
    product_sku = serializers.SerializerMethodField('product_sku_dt')

    class Meta:
        model = Putaway
        fields = ('id','warehouse', 'putaway_type', 'putaway_type_id', 'sku','product_sku', 'batch_id', 'quantity', 'putaway_quantity', 'created_at', 'modified_at')

    def product_sku_dt(self, obj):
        return obj.sku.product_sku

