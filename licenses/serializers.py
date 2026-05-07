from rest_framework import serializers
from .models import Batch, License

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ['created_at']

    def validate(self, data):
        # Additional validation if needed, e.g. checking max limits
        return data

class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = '__all__'
        read_only_fields = ['license_key', 'created_at', 'updated_at']
