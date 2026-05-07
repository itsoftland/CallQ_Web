from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from companydetails.models import Company
from configdetails.models import (
    CounterConfig,
    CounterTokenDispenserMapping,
    Device,
    TVDispenserMapping,
    get_button_index_char,
)

class AndroidTVConfigTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('get_android_tv_config')
        
        # Create a company with id 404 (to test slicing logic "0404" -> "404")
        # Note: We can't easily force an ID in some DBs, but for SQLite/Postgres usually it works if not taken.
        # Alternatively we can just use the returned ID.
        self.company = Company.objects.create(company_name="Test Company", company_id="404")
        
        # Create a device
        self.mac_address = "AA:BB:CC:DD:EE:FF"
        self.device = Device.objects.create(
            serial_number=self.mac_address,
            device_type=Device.DeviceType.TV,
            company=self.company,
            is_active=True,
            licence_status='Active'
        )

    def test_customer_id_with_leading_zero(self):
        """
        Test that provided customer_id '0404' is processed as '404'
        """
        data = {
            "mac_address": self.mac_address,
            "customer_id": "0404",
            "Flag": "TV"
        }
        response = self.client.post(self.url, data, format='json')
        
        # Should be success because logic strips '0' -> '404', which matches self.company.company_id
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(str(response.data['device_id']), str(self.device.id))

    def test_customer_id_without_leading_zero(self):
        """
        Test that provided customer_id '404' also works as normal
        """
        data = {
            "mac_address": self.mac_address,
            "customer_id": "404",
            "Flag": "TV"
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')

    def test_invalid_customer_id(self):
        """
        Test that a truly invalid customer id fails
        """
        data = {
            "mac_address": self.mac_address,
            "customer_id": "9999",
            "Flag": "TV"
        }
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['error'], 'Invalid customer_id')


class TokenDispenserConfigApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('get_token_dispenser_config_api')
        self.company = Company.objects.create(company_name="Test Company", company_id="405")

        self.tv = Device.objects.create(
            serial_number="TV-2026-001",
            device_type=Device.DeviceType.TV,
            company=self.company,
            is_active=True,
            licence_status='Active',
        )
        self.primary_dispenser = Device.objects.create(
            serial_number="TD-2026-002",
            display_name="Primary Dispenser",
            device_type=Device.DeviceType.TOKEN_DISPENSER,
            token_type=Device.TokenType.BUTTON_2,
            company=self.company,
            is_active=True,
            licence_status='Active',
            random_number='4567',
        )
        self.secondary_dispenser = Device.objects.create(
            serial_number="TD-2026-003",
            display_name="Secondary Dispenser",
            device_type=Device.DeviceType.TOKEN_DISPENSER,
            token_type=Device.TokenType.BUTTON_1,
            company=self.company,
            is_active=True,
            licence_status='Active',
            random_number='8910',
        )

        self.primary_counter = CounterConfig.objects.create(
            counter_name="CARDIOLOGY",
            counter_prefix_code="CA",
            counter_display_name="CARDIOLOGY",
            max_token_number=150,
            status=True,
        )
        self.secondary_counter = CounterConfig.objects.create(
            counter_name="CARDIOLOGY 2",
            counter_prefix_code="C2",
            counter_display_name="CARDIOLOGY 2",
            max_token_number=100,
            status=True,
        )

        TVDispenserMapping.objects.create(
            tv=self.tv,
            dispenser=self.secondary_dispenser,
            button_index=get_button_index_char(1),  # chr(0x31) = '1'
        )
        TVDispenserMapping.objects.create(
            tv=self.tv,
            dispenser=self.primary_dispenser,
            button_index=get_button_index_char(2),  # chr(0x32) = '2'
        )

        CounterTokenDispenserMapping.objects.create(
            counter=self.primary_counter,
            dispenser=self.primary_dispenser,
        )
        CounterTokenDispenserMapping.objects.create(
            counter=self.secondary_counter,
            dispenser=self.secondary_dispenser,
        )

    def test_tv_counters_include_dispenser_serial_number(self):
        response = self.client.post(
            self.url,
            {'serial_number': self.primary_dispenser.serial_number},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')

        tv_counters = response.data['tv_counters']
        self.assertEqual(len(tv_counters), 2)

        counters_by_id = {counter['counter_id']: counter for counter in tv_counters}
        self.assertEqual(
            counters_by_id[self.primary_counter.id]['dispenser_s_no'],
            self.primary_dispenser.serial_number,
        )
        self.assertEqual(
            counters_by_id[self.secondary_counter.id]['dispenser_s_no'],
            self.secondary_dispenser.serial_number,
        )
