from django.db import transaction
from rest_framework import serializers

from accounts.models import User
from products.models import Repackaging
from retailer_to_sp.models import Order, CustomerCare, PickerDashboard, OrderedProduct
from django.core.validators import RegexValidator

from shops.models import Shop
from wms.models import QCArea, Zone


class OrderNumberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ('id', 'order_no',)


class CustomerCareSerializer(serializers.ModelSerializer):
    #order_id=OrderNumberSerializer(read_only=True)
    phone_regex = RegexValidator(regex=r'^[6-9]\d{9}$')
    phone_number = serializers.CharField(validators=[phone_regex])

    class Meta:
        model=CustomerCare
        fields=('phone_number', 'complaint_id','email_us', 'order_id', 'issue_status', 'select_issue','complaint_detail')
        read_only_fields=('complaint_id','email_us','issue_status')


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'order_no', )


class RepackagingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repackaging
        fields = ('id', 'repackaging_no', 'source_picking_status', 'created_at',)


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderedProduct
        fields = ('id', )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'phone_number',)


class QcAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = QCArea
        fields = ('id', 'area_id', 'area_type')


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', '__str__')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['warehouse'] = {
            'id': representation['id'],
            'shop': representation['__str__']
        }
        return representation['warehouse']


class ZoneSerializer(serializers.ModelSerializer):
    warehouse = WarehouseSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)
    coordinator = UserSerializer(read_only=True)
    putaway_users = UserSerializer(read_only=True, many=True)
    picker_users = UserSerializer(read_only=True, many=True)

    class Meta:
        model = Zone
        fields = ('id', 'zone_number', 'name', 'warehouse', 'supervisor', 'coordinator', 'putaway_users',
                  'picker_users')


class PickerDashboardSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    repackaging = RepackagingSerializer(read_only=True)
    shipment = ShipmentSerializer(read_only=True)
    picker_boy = UserSerializer(read_only=True)
    qc_area = QcAreaSerializer(read_only=True)
    zone = ZoneSerializer(read_only=True)

    class Meta:
        model = PickerDashboard
        fields = ('id', 'order', 'repackaging', 'shipment', 'picking_status', 'picklist_id', 'picker_boy',
                  'pick_list_pdf', 'picker_assigned_date', 'zone', 'qc_area', 'is_valid', 'refreshed_at', 'created_at',
                  'modified_at', 'completed_at', 'moved_to_qc_at', )

    def validate(self, data):
        """Validates the PickerDashboard requests"""

        if 'id' in self.initial_data and self.initial_data['id']:
            if 'picker_boy' in self.initial_data and self.initial_data['picker_boy']:
                try:
                    picker_dashboard_obj = PickerDashboard.objects.get(id=self.initial_data['id'])
                    existing_picker_boy = picker_dashboard_obj.picker_boy
                except Exception as e:
                    raise serializers.ValidationError("Invalid Putaway")
                try:
                    picker_boy = User.objects.get(id=self.initial_data['picker_boy'], groups__name='Picker Boy')
                except Exception:
                    raise serializers.ValidationError("Invalid picker boy | user not found / not a picker boy.")
                if picker_boy == existing_picker_boy:
                    raise serializers.ValidationError(f'Picker Boy {picker_boy} is already assigned.')
                elif picker_dashboard_obj.zone is None:
                    raise serializers.ValidationError(f'Zone not mapped to the selected entry.')
                elif picker_boy not in picker_dashboard_obj.zone.picker_users.all():
                    raise serializers.ValidationError(f'Invalid picker_boy | {picker_boy} is not mapped to the zone.')
                data['picker_boy'] = picker_boy
            else:
                raise serializers.ValidationError(f"Invalid Picker boy | 'picker_boy' can't be empty.")
        else:
            raise serializers.ValidationError("PickerDashboard creation is not allowed.")

        if sorted(list(self.initial_data.keys())) != ['id', 'picker_boy']:
            raise serializers.ValidationError("Only Picker boy update is allowed")

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            picker_dashboard_instance = super().update(instance, validated_data)
        except Exception as e:
            error = {'message': ",".join(e.args) if len(e.args) > 0 else 'Unknown Error'}
            raise serializers.ValidationError(error)

        return picker_dashboard_instance


class SummarySerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    moved_to_qc = serializers.IntegerField()


class OrderSummarySerializers(serializers.Serializer):
    # status_count = SummarySerializer(read_only=True)
    # order = OrderSerializer(read_only=True)
    order = serializers.SerializerMethodField()
    status = serializers.CharField()

    def get_order(self, obj):
        if obj['order']:
            return OrderSerializer(Order.objects.filter(id=obj['order']).last(), read_only=True).data
        return None
