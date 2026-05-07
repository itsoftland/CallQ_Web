from rest_framework import serializers
from ..models import Company, Branch, AuthenticationLog

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class AuthenticationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthenticationLog
        fields = '__all__'
