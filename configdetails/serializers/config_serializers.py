from rest_framework import serializers
from ..models import Device, DeviceConfig, TVConfig, Mapping, Counter, EmbeddedProfile, CounterConfig, TVCounterMapping, CounterTokenDispenserMapping, ExternalDeviceCounterLog, GroupMapping, TVDispenserMapping, TVKeypadMapping

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'

    def validate(self, data):
        company = data.get('company')
        device_type = data.get('device_type')
        
        if not company:
            return data

        # Sync live limits from API for non-dealer-created companies
        if not company.is_dealer_created and company.company_id:
            try:
                from callq_core.services import LicenseManagementService
                from companydetails.views import sync_company_license_data
                api_data = LicenseManagementService.authenticate_product(company.company_id)
                if api_data and not api_data.get('error'):
                    sync_company_license_data(company, api_data)
                    company.refresh_from_db()
            except Exception:
                pass  # Fall back to existing local limits

        # Mapping of DeviceType to Company model field
        limit_mapping = {
            Device.DeviceType.BROKER: company.noof_broker_devices,
            Device.DeviceType.TOKEN_DISPENSER: company.noof_token_dispensors,
            Device.DeviceType.KEYPAD: company.noof_keypad_devices,
            Device.DeviceType.TV: company.noof_television_devices,
            Device.DeviceType.LED: company.noof_led_devices,
        }

        limit = limit_mapping.get(device_type, 0)
        # Count ALL registered devices (not just active) for accurate limit enforcement
        current_count = Device.objects.filter(company=company, device_type=device_type).count()

        if current_count >= limit:
            device_type_display = str(device_type).replace('_', ' ').title()
            raise serializers.ValidationError(
                f"Maximum number of {device_type_display} devices reached! Allowed: {limit}, Currently registered: {current_count}."
            )

        return data

class DeviceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceConfig
        fields = '__all__'

class TVConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TVConfig
        fields = '__all__'

class MappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mapping
        fields = '__all__'

class GroupMappingSerializer(serializers.ModelSerializer):
    dispensers = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.filter(device_type=Device.DeviceType.TOKEN_DISPENSER), required=False)
    keypads = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.filter(device_type=Device.DeviceType.KEYPAD), required=False)
    tvs = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.filter(device_type=Device.DeviceType.TV), required=False)
    brokers = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.filter(device_type=Device.DeviceType.BROKER), required=False)
    leds = serializers.PrimaryKeyRelatedField(many=True, queryset=Device.objects.filter(device_type=Device.DeviceType.LED), required=False)
    
    class Meta:
        model = GroupMapping
        fields = '__all__'

class CounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = '__all__'

class EmbeddedProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmbeddedProfile
        fields = '__all__'


# Counter-Wise Configuration Serializers
class CounterConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def _get_company(self):
        """Resolve the company from the instance (edit) or request context (create)."""
        if self.instance:
            return self.instance.company
        request = self.context.get('request')
        if request and hasattr(request.user, 'company_relation') and request.user.company_relation:
            return request.user.company_relation
        return None

    def validate_counter_name(self, value):
        """Ensure counter name is unique within the same company."""
        company = self._get_company()
        qs = CounterConfig.objects.filter(counter_name=value)
        if company:
            qs = qs.filter(company=company)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Counter name must be unique within your company.")
        return value

    def validate_counter_prefix_code(self, value):
        """Ensure prefix code is unique within the same company."""
        company = self._get_company()
        qs = CounterConfig.objects.filter(counter_prefix_code=value)
        if company:
            qs = qs.filter(company=company)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Counter prefix code must be unique within your company.")
        return value

    def validate_max_token_number(self, value):
        """Ensure max token number is greater than 0"""
        if value <= 0:
            raise serializers.ValidationError("Maximum token number must be greater than 0.")
        return value


class TVCounterMappingSerializer(serializers.ModelSerializer):
    tv_serial_number = serializers.CharField(source='tv.serial_number', read_only=True)
    counter_name = serializers.CharField(source='counter.counter_name', read_only=True)

    class Meta:
        model = TVCounterMapping
        fields = '__all__'
        read_only_fields = ('created_at',)


class CounterTokenDispenserMappingSerializer(serializers.ModelSerializer):
    counter_name = serializers.CharField(source='counter.counter_name', read_only=True)
    dispenser_serial_number = serializers.CharField(source='dispenser.serial_number', read_only=True)

    class Meta:
        model = CounterTokenDispenserMapping
        fields = '__all__'
        read_only_fields = ('created_at',)


class TVDispenserMappingSerializer(serializers.ModelSerializer):
    tv_serial_number = serializers.CharField(source='tv.serial_number', read_only=True)
    dispenser_serial_number = serializers.CharField(source='dispenser.serial_number', read_only=True)
    dispenser_token_type = serializers.CharField(source='dispenser.token_type', read_only=True)
    dispenser_display_name = serializers.CharField(source='dispenser.display_name', read_only=True)
    counters = serializers.SerializerMethodField()

    class Meta:
        model = TVDispenserMapping
        fields = '__all__'
        read_only_fields = ('created_at',)

    def get_counters(self, obj):
        """Get all counters mapped to this dispenser"""
        counter_mappings = CounterTokenDispenserMapping.objects.filter(
            dispenser=obj.dispenser
        ).select_related('counter')
        
        return [
            {
                'counter_id': mapping.counter.id,
                'counter_name': mapping.counter.counter_name,
                'counter_display_name': mapping.counter.counter_display_name,
                'counter_prefix_code': mapping.counter.counter_prefix_code,
                'max_token_number': mapping.counter.max_token_number,
                'status': mapping.counter.status
            }
            for mapping in counter_mappings
        ]


class TVKeypadMappingSerializer(serializers.ModelSerializer):
    tv_serial_number = serializers.CharField(source='tv.serial_number', read_only=True)
    keypad_serial_number = serializers.CharField(source='keypad.serial_number', read_only=True)
    keypad_display_name = serializers.CharField(source='keypad.display_name', read_only=True)
    keypad_token_type = serializers.CharField(source='keypad.token_type', read_only=True)
    dispenser_serial_number = serializers.CharField(source='dispenser.serial_number', read_only=True, default=None)

    class Meta:
        model = TVKeypadMapping
        fields = [
            'id', 'tv', 'tv_serial_number',
            'keypad', 'keypad_serial_number', 'keypad_display_name', 'keypad_token_type',
            'dispenser', 'dispenser_serial_number',
            'keypad_index',
            'created_at',
        ]
        read_only_fields = ('created_at',)



class ExternalDeviceCounterLogSerializer(serializers.ModelSerializer):
    counter_display_name = serializers.CharField(source='counter.counter_display_name', read_only=True)

    class Meta:
        model = ExternalDeviceCounterLog
        fields = '__all__'
        read_only_fields = ('created_at',)
