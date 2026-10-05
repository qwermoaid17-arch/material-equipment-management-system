from rest_framework import serializers
from .models import User, Site, Item, SiteInventory, TransferRequest, TransferLog, Notification


class UserSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'site', 'site_name']


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'


class SiteInventorySerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    item_unit = serializers.CharField(source='item.unit', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = SiteInventory
        fields = ['id', 'site', 'site_name', 'item', 'item_name', 'item_sku',
                  'item_unit', 'quantity_available', 'quantity_surplus']

        extra_kwargs = {'site': {'required': False}}

        validators = []

    def validate(self, attrs):
        available = attrs.get('quantity_available', getattr(self.instance, 'quantity_available', 0))
        surplus = attrs.get('quantity_surplus', getattr(self.instance, 'quantity_surplus', 0))
        if surplus > available:
            raise serializers.ValidationError('الكمية الزائدة لا يمكن أن تتجاوز الكمية المتاحة')
        return attrs


class TransferRequestSerializer(serializers.ModelSerializer):
    source_site_name = serializers.CharField(source='source_site.name', read_only=True)
    target_site_name = serializers.CharField(source='target_site.name', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TransferRequest
        fields = ['id', 'source_site', 'source_site_name', 'target_site', 'target_site_name',
                  'item', 'item_name', 'quantity', 'status', 'created_by', 'created_by_username',
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'status']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'