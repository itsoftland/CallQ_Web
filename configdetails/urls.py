from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet)
router.register(r'mappings', views.MappingViewSet)
router.register(r'profiles', views.EmbeddedProfileViewSet)
router.register(r'counters', views.CounterConfigViewSet)
router.register(r'tv-counter-mappings', views.TVCounterMappingViewSet)
router.register(r'counter-dispenser-mappings', views.CounterTokenDispenserMappingViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('device/<int:device_id>/config/', views.device_config, name='device_config'),
    path('devices/', views.device_list, name='device_list'),
    path('device/register/', views.device_register, name='device_register'),
    path('api/device/<int:device_id>/check-status/', views.check_device_status_api, name='check_device_status'),
    path('device/<int:device_id>/assign_branch/', views.assign_device_branch, name='assign_device_branch'),
    path('api/android/config', views.get_android_tv_config, name='get_android_tv_config'),
    path('tv/<int:tv_id>/config/', views.tv_config, name='tv_config'),
    path('mapping/', views.mapping_view, name='mapping_view'),
    path('mapping/list/', views.mapping_list_view, name='mapping_list'),
    # Wizard URLs commented out - using automatic button mapping instead
    # path('mapping/<int:group_id>/button-wizard/', views.button_mapping_wizard, name='button_mapping_wizard'),
    path('api/mapping/group/<int:group_id>/button-mappings/', views.get_group_button_mappings_api, name='get_group_button_mappings_api'),
    path('api/mapping/group/<int:group_id>/button-mappings/save/', views.save_group_button_mappings_api, name='save_group_button_mappings_api'),
    path('api/mapping/devices/', views.get_available_devices_api, name='get_available_devices_api'),
    # Device-to-Customer Mapping
    path('mapping/map-device/', views.map_device_to_customer, name='map_device_to_customer'),
    path('mapping/unmap-device/', views.unmap_device, name='unmap_device'),
    # Device Management
    path('device/<int:device_id>/delete/', views.device_delete, name='device_delete'),
    path('device/<int:device_id>/change-branch/', views.change_device_branch, name='change_device_branch'),
    path('device/<int:device_id>/change-owner/', views.change_device_owner, name='change_device_owner'),
    path('api/device/<int:device_id>/authenticate/', views.device_authenticate_api, name='device_authenticate'),
    # Mapping APIs
    path('api/branch/<int:branch_id>/devices/', views.get_branch_devices_api, name='get_branch_devices_api_v2'),
    path('api/mapping/button/save/', views.save_button_mapping_api, name='save_button_mapping_api'),
    path('api/branch/<int:branch_id>/mappings/', views.get_branch_mappings_api, name='get_branch_mappings_api'),
    path('api/branch/<int:branch_id>/group-mapping/', views.get_branch_group_mapping_api, name='get_branch_group_mapping_api'),
    path('api/mapping/button/<int:mapping_id>/delete/', views.delete_button_mapping_api, name='delete_button_mapping_api'),
    path('api/mapping/family/<int:family_id>/delete/', views.delete_family_mapping_api, name='delete_family_mapping_api'),
    path('api/mapping/group/<int:group_id>/devices/', views.get_group_devices_api, name='get_group_devices_api'),
    path('api/mapping/group/<int:group_id>/update-devices/', views.update_group_devices_api, name='update_group_devices_api'),
    
    # Dealer Customer APIs
    path('api/dealer-customer/<int:customer_id>/devices/', views.get_dealer_customer_devices_api, name='get_dealer_customer_devices_api'),
    path('api/dealer-customer/<int:customer_id>/mappings/', views.get_dealer_customer_mappings_api, name='get_dealer_customer_mappings_api'),

    # Embedded Profile Templates
    path('embedded-profiles/', views.embedded_profile_list, name='embedded_profile_list'),
    path('embedded-profiles/create/', views.embedded_profile_create, name='embedded_profile_create'),
    path('embedded-profiles/<int:pk>/edit/', views.embedded_profile_edit, name='embedded_profile_edit'),
    path('embedded-profiles/<int:pk>/delete/', views.embedded_profile_delete, name='embedded_profile_delete'),
    path('embedded-profiles/<int:pk>/allocate/', views.embedded_profile_allocate, name='embedded_profile_allocate'),

    # Device Config Profile (no scheduling)
    path('config-profiles/', views.config_profile_list, name='config_profile_list'),
    path('config-profiles/create/', views.config_profile_create, name='config_profile_create'),
    path('config-profiles/<int:pk>/edit/', views.config_profile_edit, name='config_profile_edit'),
    path('config-profiles/<int:pk>/delete/', views.config_profile_delete, name='config_profile_delete'),
    path('config-profiles/<int:pk>/allocate/', views.config_profile_allocate, name='config_profile_allocate'),

    
    # Device Approvals
    path('approvals/', views.device_approval_list, name='device_approval_list'),
    path('approvals/<int:device_id>/approve/', views.approve_device_request, name='approve_device_request'),
    path('approvals/<int:device_id>/reject/', views.reject_device_request, name='reject_device_request'),
    
    # Ad Management
    path('ad/<int:ad_id>/delete/', views.delete_ad, name='delete_ad'),
    path('devices/assign-branch/', views.assign_devices_to_branch, name='assign_devices_to_branch'),
    path('production-batch/upload/', views.production_batch_upload, name='production_batch_upload'),
    path('production-batch/download/<int:batch_id>/<str:file_format>/', views.batch_download, name='batch_download'),
    path('production/report/', views.production_report_view, name='production_report'),
    
    # API for available serial numbers
    path('api/available-serial-numbers/', views.get_available_serial_numbers_api, name='get_available_serial_numbers_api'),
    path('api/embedded/get-config', views.get_embedded_config, name='get_embedded_config'),
    
    # Counter-Wise Configuration APIs
    path('api/counters/', views.get_counters_api, name='get_counters_api'),
    path('api/counters/create/', views.create_counter_api, name='create_counter_api'),
    path('api/counters/<int:counter_id>/update/', views.update_counter_api, name='update_counter_api'),
    path('api/counters/<int:counter_id>/delete/', views.delete_counter_api, name='delete_counter_api'),
    path('api/tv/<int:tv_id>/counters/', views.get_tv_counter_mappings_api, name='get_tv_counter_mappings_api'),
    path('api/tv/<int:tv_id>/counters/map/', views.map_tv_counters_api, name='map_tv_counters_api'),
    path('api/tv/<int:tv_id>/dispensers/', views.get_tv_dispenser_mappings_api, name='get_tv_dispenser_mappings_api'),
    path('api/tv/<int:tv_id>/dispensers/map/', views.map_tv_dispensers_api, name='map_tv_dispensers_api'),
    path('api/tv/<int:tv_id>/keypads/', views.get_tv_keypad_mappings_api, name='get_tv_keypad_mappings_api'),
    path('api/tv/<int:tv_id>/keypads/map/', views.map_tv_keypads_api, name='map_tv_keypads_api'),
    path('api/counter/<int:counter_id>/dispensers/', views.get_counter_dispenser_mappings_api, name='get_counter_dispenser_mappings_api'),
    path('api/counter/<int:counter_id>/dispenser/map/', views.map_counter_dispenser_api, name='map_counter_dispenser_api'),
    path('api/counter/<int:counter_id>/dispenser/<int:dispenser_id>/unmap/', views.unmap_counter_dispenser_api, name='unmap_counter_dispenser_api'),
    
    # External API for device-counter mapping
    path('api/external/device-counter', views.external_device_counter_api, name='external_device_counter_api'),
    
    # External API for device registration
    path('api/external/register-device', views.register_device_api, name='register_device_api'),

    # Counter Management UI
    path('counters/', views.counter_list, name='counter_list'),
    path('counters/create/', views.counter_create, name='counter_create'),
    path('counters/<int:counter_id>/edit/', views.counter_edit, name='counter_edit'),
    path('counters/<int:counter_id>/delete/', views.counter_delete, name='counter_delete'),
    
    # Log Viewing
    path('logs/', views.log_list, name='log_list'),
    path('logs/<str:year>/<str:month>/<str:day>/<str:log_type>/', views.log_view, name='log_view'),

    # Token Report Page
    path('token-report/', views.token_report_list, name='token_report_list'),
]