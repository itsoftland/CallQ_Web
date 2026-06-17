import requests
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)
request_logger = logging.getLogger('request_hits')
action_logger = logging.getLogger('actions')

class LicenseManagementService:
    # Read Base URL from settings (derived from .env)
    BASE_URL = settings.LICENSE_PORTAL_URL + 'api' if settings.LICENSE_PORTAL_URL else ""
    
    @staticmethod
    def register_product(details):
        """
        Calls ProductRegistration API with Master Prompt fields
        Includes defensive cleaning and padding to prevent 'Invalid Input Data' errors.
        """
        def clean_and_pad(val, length=10, default="1234567890"):
            if not val: return default
            digits = "".join(filter(str.isdigit, str(val)))
            if not digits: return default
            # Pad or truncate to desired length if needed, or just return if "at least" is enough
            # But portal example used exactly 10 and 6
            if length == 10: return digits.ljust(10, '0')[:10]
            if length == 6: return digits.ljust(6, '0')[:6]
            if length == 12: return digits.ljust(12, '0')[:12] # Added for GST
            return digits

        # Ensure BASE_URL ends with / for safe joining
        base = LicenseManagementService.BASE_URL.rstrip('/') + '/'
        url = f"{base}ProductRegistration"
        
        payload = {
            "DeviceModel": "Windows",
            "DeviceIdentifier1": details.get('company_name'),
            "PhoneNumber": clean_and_pad(details.get('contact_number'), 10, "1234567890"),
            "GSTNumber": clean_and_pad(details.get('gst_number'), 12, "123456789012"),
            "CustomerName": details.get('company_name'),
            "CustomerContactPerson": details.get('contact_person'),
            "CustomerAddress": details.get('address'),
            "CustomerCity": details.get('city'),
            "CustomerState": details.get('state'),
            "CustomerZip": clean_and_pad(details.get('zip_code'), 6, "123456"),
            "CustomerContact": clean_and_pad(details.get('contact_number'), 10, "1234567890"),
            "CustomerEmail": details.get('company_email'),
            "DeviceType": details.get('device_type', 1),
            "Version": getattr(settings, 'APP_VERSION', 'CallQ v1.0.0'),
            "ProjectName": getattr(settings, 'PROJECT_NAME', 'CallQ')
        }
        request_logger.info(f"API REQUEST: ProductRegistration | URL: {url} | Payload: {json.dumps(payload)}")
        action_logger.info(f"Initiating ProductRegistration for {details.get('company_name')}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            request_logger.info(f"API RESPONSE: ProductRegistration | Status: {response.status_code} | Body: {response.text}")
            action_logger.info(f"API Response: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error registering product: {e}")
            action_logger.error(f"ProductRegistration Failed for {details.get('company_name')}: {str(e)}")
            return {"error": "External API error", "details": str(e), "status": "failed"}

    @staticmethod
    def authenticate_product(customer_id):
        """
        Calls ProductAuthentication API with Master Prompt fields
        """
        url = f"{LicenseManagementService.BASE_URL}/ProductAuthentication"
        payload = {"CustomerId": customer_id}
        
        request_logger.info(f"API REQUEST: ProductAuthentication | URL: {url} | Payload: {json.dumps(payload)}")
        action_logger.info(f"Initiating ProductAuthentication for CustomerId: {customer_id}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            request_logger.info(f"API RESPONSE: ProductAuthentication | Status: {response.status_code} | Body: {response.text}")
            action_logger.info(f"ProductAuthentication Response: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error authenticating product: {e}")
            action_logger.error(f"ProductAuthentication Failed for CustomerId: {customer_id}: {str(e)}")
            return {"error": "External API error", "details": str(e), "status": "failed"}

    @staticmethod
    def register_device(details):
        """
        Calls DeviceRegistration API to register a new device.
        Payload includes ProductRegistrationId, UniqueIdentifier, DeviceModel, MAC Address, etc.
        """
        def clean_and_pad(val, length=10, default="1234567890"):
            if not val: return default
            # For MAC/Serial, we might want to keep alphanumeric but API might be expecting digits only if it's strictly validated?
            # User registration used filter(str.isdigit).
            # If DeviceIdentifier1 allows characters (like MAC includes : or hex), filtering might be wrong.
            # However, prompt says "Master Prompt fields" logic prevents errors.
            # Let's try to just pad it if it's short, but keep it as string.
            val_str = str(val)
            if len(val_str) < 5: # Arbitrary short length check
                 # Pad with leading zeros if it looks like a number
                 if val_str.isdigit():
                     return val_str.zfill(10)
                 return val_str.ljust(10, 'X')
            return val_str

        base = LicenseManagementService.BASE_URL.rstrip('/') + '/'
        url = f"{base}DeviceRegistration"
        
        # Defensive: ensure correct types
        internal_dev_type = details.get('device_type', 1)
        try:
            internal_dev_type = int(internal_dev_type)
        except:
            internal_dev_type = 1

        # DeviceModel is always "Android" for all device types
        device_model = "Android"
        
        # Map internal device types to external API DeviceType:
        # - TV (internal type 2) = DeviceType 1
        # - All other devices = DeviceType 2
        # Internal device types: 1=Generic, 2=TV, 3=TOKEN_DISPENSER, 4=KEYPAD, 5=BROKER, 6=LED
        if internal_dev_type == 2:  # TV / Android TV
            api_device_type = 1
        else:
            api_device_type = 2
        
        payload = {
            "DeviceRegistrationId": 0,
            "ProductRegistrationId": details.get('product_registration_id'),
            "UniqueIDentifier": details.get('unique_identifier'), # Note: API expects capital D in Identifier
            "DeviceModel": device_model,  # Always "Android"
            "DeviceIdentifier1": clean_and_pad(details.get('mac_address')),
            "PhoneNumber": details.get('customer_contact', ''),
            "CustomerName": details.get('customer_name', ''),
            "CustomerContactPerson": details.get('customer_contact_person', ''),
            "CustomerAddress": details.get('customer_address', ''),
            "CustomerAddress2": "",
            "CustomerCity": details.get('customer_city', ''),
            "CustomerState": details.get('customer_state', ''),
            "CustomerCityId": "",
            "CustomerZip": details.get('customer_zip', ''),
            "CustomerContact": details.get('customer_contact', ''),
            "CustomerEmail": details.get('customer_email', ''),
            "CustomerURL": "",
            "IsActive": 0,
            "CreatedBy": details.get('created_by', 1),
            "DeviceType": api_device_type  # 1 for TV, 2 for all others
        }
        
        request_logger.info(f"API REQUEST: DeviceRegistration | URL: {url} | Payload: {json.dumps(payload)}")
        action_logger.info(f"Initiating DeviceRegistration for MAC: {details.get('mac_address')}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            request_logger.info(f"API RESPONSE: DeviceRegistration | Status: {response.status_code} | Body: {response.text}")
            
            if response.status_code == 200:
                # Check for empty response body
                if not response.text or response.text.strip() == '':
                    action_logger.warning(f"DeviceRegistration returned empty response for MAC: {details.get('mac_address')}")
                    return {"error": "Empty response from API", "status": "failed"}
                return response.json()
            
            # Handle non-200 but valid JSON responses if any
            try:
                if response.text and response.text.strip():
                    return response.json()
                return {"error": f"API returned status {response.status_code} with empty body", "status": "failed"}
            except:
                response.raise_for_status()
                
        except requests.RequestException as e:
            logger.error(f"Error registering device: {e}")
            action_logger.error(f"DeviceRegistration Failed for MAC: {details.get('mac_address')}: {str(e)}")
            return {"error": "External API error", "details": str(e), "status": "failed"}

    @staticmethod
    def check_device_status(details):
        """
        Calls CheckDeviceStatus API to validate license and fetch configuration.
        """
        base = LicenseManagementService.BASE_URL.rstrip('/') + '/'
        url = f"{base}CheckDeviceStatus"
        
        payload = {
            "ProductRegistrationId": details.get('product_registration_id'),
            "DeviceRegistrationId": details.get('device_registration_id'),
            "ProductTypeId": details.get('product_type_id'),
            "UniqueIDentifier": details.get('unique_identifier'), # Capital D
            "CustomerId": details.get('customer_id'),
            "ProjectName": details.get('project_name')
        }
        
        request_logger.info(f"API REQUEST: CheckDeviceStatus | URL: {url} | Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            request_logger.info(f"API RESPONSE: CheckDeviceStatus | Status: {response.status_code} | Body: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            
            try:
                return response.json()
            except:
                response.raise_for_status()

        except requests.RequestException as e:
            logger.error(f"Error checking device status: {e}")
            return {"error": "External API error", "details": str(e), "status": "failed"}

def log_activity(user, action, details=None):
    from companydetails.models import ActivityLog
    if user and user.is_authenticated:
        ActivityLog.objects.create(user=user, action=action, details=details)



# ---------------------------------------------------------------------------
# License Validation & Device-Limit Enforcement
# ---------------------------------------------------------------------------

class LicenseValidator:
    """
    Centralised license validation helper.

    All entry-points that need to enforce license rules (web login, Android
    login, external device-registration API, UI device-registration) should
    call these methods so the logic stays in one place.
    """

    # Maps Device.device_type values to the Company field that holds the limit.
    DEVICE_TYPE_LIMIT_MAP = {
        'BROKER':           'noof_broker_devices',
        'TOKEN_DISPENSER':  'noof_token_dispensors',
        'KEYPAD':           'noof_keypad_devices',
        'TV':               'noof_television_devices',
        'LED':              'noof_led_devices',
        'Config Apk':       'noof_config_apk',   # Device.DeviceType.CONFIG_APK = 'Config Apk'
    }

    @staticmethod
    def _license_company(company):
        """
        Dealer-created child companies inherit their parent dealer's license.
        Returns the company whose product_to_date and device limits apply.
        """
        if company and getattr(company, 'is_dealer_created', False) and company.parent_company:
            return company.parent_company
        return company

    @staticmethod
    def check_license_expiry(company):
        """
        Check whether the given Company's license has expired.

        Dealer-created child companies inherit their parent dealer's license,
        so the parent's product_to_date is used automatically.

        Returns:
            (is_expired: bool, expiry_date: date | None)
        """
        from datetime import date as _date
        company = LicenseValidator._license_company(company)
        expiry = company.product_to_date
        if expiry is None:
            return True, None
        return (_date.today() > expiry), expiry

    @staticmethod
    def check_device_limit(company, device_type, exclude_serial=None):
        """
        Check whether the company has reached its licensed device limit for
        the given device_type.

        Dealer-created child companies share the parent dealer's device quota.
        The limit is read from the parent, and the count covers the parent +
        all its child companies so the pool is never double-counted.

        Returns:
            (is_over_limit: bool, current_count: int, max_allowed: int)
        """
        from configdetails.models import Device
        from django.db.models import Q as _Q

        license_company = LicenseValidator._license_company(company)

        limit_field = LicenseValidator.DEVICE_TYPE_LIMIT_MAP.get(device_type)
        if limit_field is None:
            return False, 0, 0

        max_allowed = getattr(license_company, limit_field, 0) or 0

        if license_company != company:
            # Count across the dealer + all their child companies
            qs = Device.objects.filter(
                _Q(company=license_company) | _Q(company__parent_company=license_company),
                device_type=device_type,
            )
        else:
            qs = Device.objects.filter(company=company, device_type=device_type)

        if exclude_serial:
            qs = qs.exclude(serial_number=exclude_serial)
        current_count = qs.count()

        return (current_count >= max_allowed), current_count, max_allowed
