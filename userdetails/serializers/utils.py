from configdetails.models import Mapping, Device
from django.db.models import Q

def serialize_company_full(company):
    if not company: return None
    return {
        "id": company.id,
        "company_id": company.company_id,
        "name": company.company_name,
        "type": company.company_type,
        "email": company.company_email,
        "gst": company.gst_number,
        "contact_person": company.contact_person,
        "contact_number": company.contact_number,
        "address": company.address,
        "address_2": company.address_2,
        "city": company.city,
        "district": company.district,
        "state": company.state,
        "zip_code": company.zip_code
    }

def serialize_dealer_customer_full(dc):
    if not dc: return None
    return {
        "id": dc.id,
        "customer_id": dc.customer_id,
        "name": dc.company_name,
        "email": dc.company_email,
        "gst": dc.gst_number,
        "contact_person": dc.contact_person,
        "contact_number": dc.contact_number,
        "address": dc.address,
        "address_2": dc.address_2,
        "city": dc.city,
        "district": dc.district,
        "state": dc.state,
        "zip_code": dc.zip_code,
        "dealer_id": dc.dealer.id,
        "dealer_name": dc.dealer.company_name
    }

def serialize_branch_full(branch):
    if not branch: return None
    return {
        "id": branch.id,
        "name": branch.branch_name,
        "address": branch.address,
        "city": branch.city,
        "state": branch.state,
        "zip_code": branch.zip_code
    }

def serialize_device_full(device):
    if not device: return None
    
    # Base device info
    data = {
        "id": device.id,
        "serial_number": device.serial_number,
        "mac_address": device.mac_address,
        "device_type": device.device_type,
        "device_model": device.device_model,
        "licence_status": device.licence_status,
        "licence_active_to": str(device.licence_active_to) if device.licence_active_to else None,
        "is_active": device.is_active,
        "branch": serialize_branch_full(device.branch) if device.branch else None,
        "config": {}
    }
    
    # Configuration
    if hasattr(device, 'config'):
        data["config"]["general"] = device.config.config_json
    
    if device.device_type == 'TV' and hasattr(device, 'tv_config'):
        tc = device.tv_config
        data["config"]["tv"] = {
            "orientation": tc.orientation,
            "layout_type": tc.layout_type,
            "display_rows": tc.display_rows,
            "display_columns": tc.display_columns,
            "token_audio_file": tc.token_audio_file.url if tc.token_audio_file else None,
            "audio_language": tc.audio_language,
            "token_format": tc.token_format,
            "no_of_counters": tc.no_of_counters,
            "ad_placement": getattr(tc, 'ad_placement', 'right'),
            "ads": [ad.file.url for ad in tc.ads.all()]
        }
        
    if device.device_type == 'LED' and hasattr(device, 'led_config'):
        lc = device.led_config
        data["config"]["led"] = {
            "identifier": lc.led_identifier_name,
            "voice_announcement": lc.voice_announcement,
            "counter_number": lc.counter_number,
            "token_calling": lc.token_calling
        }
        
    if device.embedded_profile:
        data["config"]["embedded"] = device.embedded_profile.config_json

    # Mappings
    mappings = Mapping.objects.filter(Q(tv=device) | Q(token_dispenser=device) | Q(keypad=device) | Q(broker=device) | Q(led=device))
    data["mappings"] = []
    for m in mappings:
        m_data = {
            "id": m.id,
            "tv": m.tv.serial_number if m.tv else None,
            "token_dispenser": m.token_dispenser.serial_number if m.token_dispenser else None,
            "keypad": m.keypad.serial_number if m.keypad else None,
            "broker": m.broker.serial_number if m.broker else None,
            "led": m.led.serial_number if m.led else None
        }
        data["mappings"].append(m_data)

    return data
