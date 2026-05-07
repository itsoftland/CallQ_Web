from django.contrib import admin
from .models import Company, Branch, DealerCustomer, ActivityLog, AuthenticationLog

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_email', 'company_type', 'is_dealer_created', 'company_id', 'created_at']
    list_filter = ['company_type', 'is_dealer_created']
    search_fields = ['company_name', 'company_email', 'contact_person']

@admin.register(DealerCustomer)
class DealerCustomerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_email', 'dealer', 'customer_id', 'created_at']
    list_filter = ['dealer', 'created_at']
    search_fields = ['company_name', 'company_email', 'contact_person']
    readonly_fields = ['customer_id', 'created_at', 'updated_at']

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['branch_name', 'company', 'city', 'state', 'created_at']
    list_filter = ['company', 'state']
    search_fields = ['branch_name', 'company__company_name']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'timestamp']
    list_filter = ['timestamp', 'user']
    readonly_fields = ['timestamp']
    search_fields = ['action', 'details']

@admin.register(AuthenticationLog)
class AuthenticationLogAdmin(admin.ModelAdmin):
    list_display = ['company', 'authentication_status', 'product_registration_id', 'created_at']
    list_filter = ['authentication_status', 'created_at']
    readonly_fields = ['created_at']
