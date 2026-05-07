from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import dealer_customer_views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet)

urlpatterns = [
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logs/', views.activity_log_list, name='activity_log_list'),
    path('api/', include(router.urls)),
    
    # Master API Flow Endpoints
    path('api/customer_register/', views.CompanyViewSet.as_view({'post': 'customer_register_external'}), name='api_customer_register'),
    path('api/customer-registration/save/<int:pk>/', views.CompanyViewSet.as_view({'patch': 'save_registration'}), name='api_save_registration'),
    path('api/customer_authentication/', views.CompanyViewSet.as_view({'post': 'customer_authentication_external_standalone'}), name='api_customer_authentication'),
    path('api/save_product_authentication/<int:pk>/', views.CompanyViewSet.as_view({'patch': 'save_authentication'}), name='api_save_authentication'),
    
    path('customer-list/', views.customer_list, name='customer_list'),
    path('dealers/', views.dealer_list, name='dealer_list'),
    path('customer-register/', views.customer_registration, name='customer_register'),
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/create/', views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('customer/validate/<int:pk>/', views.validate_license_view, name='validate_license'),
    path('customer/ajax-authenticate/<int:pk>/', views.ajax_authenticate_customer, name='ajax_authenticate_customer'),
    path('customer/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customer/<int:pk>/toggle-ads/', views.customer_toggle_ads, name='customer_toggle_ads'),
    path('customer/ajax-status/<int:pk>/', views.ajax_check_customer_status, name='ajax_check_customer_status'),
    path('api/company-branches/<int:company_id>/', views.ajax_get_company_branches, name='ajax_get_company_branches'),
    path('api/get-states/', views.get_states, name='get_states'),
    path('api/get-districts/', views.get_districts, name='get_districts'),
    path('location-management/', views.location_management, name='location_management'),
    
    # Dealer Customer Management
    path('dealer-customers/', dealer_customer_views.dealer_customer_list, name='dealer_customer_list'),
    path('dealer-customers/create/', dealer_customer_views.dealer_customer_create, name='dealer_customer_create'),
    path('dealer-customers/<int:pk>/edit/', dealer_customer_views.dealer_customer_edit, name='dealer_customer_edit'),
    path('dealer-customers/<int:pk>/delete/', dealer_customer_views.dealer_customer_delete, name='dealer_customer_delete'),
    path('dealer-customers/<int:pk>/toggle-status/', dealer_customer_views.dealer_customer_toggle_status, name='dealer_customer_toggle_status'),
    
    # Reports
    path('reports/devices/', views.device_report, name='device_report'),
    path('customer/export/<int:company_id>/<str:file_format>/', views.customer_export, name='customer_export'),
]