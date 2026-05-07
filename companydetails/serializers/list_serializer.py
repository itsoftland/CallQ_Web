from rest_framework import serializers
from ..models import Company

class ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'company_id',
            'company_name',
        ]
