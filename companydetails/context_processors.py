from django.conf import settings
from datetime import date, timedelta
from django.db.models import Q
from django.urls import reverse
import logging
import traceback

logger = logging.getLogger(__name__)

def project_info(request):
    return {
        'PROJECT_NAME': getattr(settings, 'PROJECT_NAME', 'unknown'),
        'PROJECT_DISPLAY_NAME': getattr(settings, 'PROJECT_DISPLAY_NAME', 'My App'),
        'APP_VERSION': getattr(settings, 'APP_VERSION', 'dev')
    }


def notifications(request):
    """
    Generate role-based notifications for the notification bell.
    Only shows data accessible to the current user's role.
    """
    notifications_list = []
    
    if not request.user.is_authenticated:
        return {'notifications': [], 'notification_count': 0}
    
    user = request.user
    
    try:
        from configdetails.models import Device
        from .models import Company, DealerCustomer
        from licenses.models import BatchRequest, Batch
        
        # ============ SUPER_ADMIN & ADMIN Notifications ============
        if user.role in ['SUPER_ADMIN', 'ADMIN']:
            # State filter for ADMIN
            state_filter = user.assigned_state if user.role == 'ADMIN' else None
            
            # 1. License Expiring Soon (within 30 days)
            expiry_threshold = date.today() + timedelta(days=30)
            if state_filter:
                expiring_companies = Company.objects.filter(
                    state__in=state_filter,
                    product_to_date__isnull=False,
                    product_to_date__lte=expiry_threshold,
                    product_to_date__gte=date.today()
                )
            else:
                expiring_companies = Company.objects.filter(
                    product_to_date__isnull=False,
                    product_to_date__lte=expiry_threshold,
                    product_to_date__gte=date.today()
                )
            
            expiring_count = expiring_companies.count()
            if expiring_count > 0:
                notifications_list.append({
                    'type': 'warning',
                    'icon': 'fa-clock',
                    'message': f'{expiring_count} license(s) expiring within 30 days',
                    'link': reverse('customer_list')
                })
            
            # 2. Expired Licenses
            if state_filter:
                expired_companies = Company.objects.filter(
                    state__in=state_filter,
                    product_to_date__isnull=False,
                    product_to_date__lt=date.today()
                )
            else:
                expired_companies = Company.objects.filter(
                    product_to_date__isnull=False,
                    product_to_date__lt=date.today()
                )
            
            expired_count = expired_companies.count()
            if expired_count > 0:
                notifications_list.append({
                    'type': 'danger',
                    'icon': 'fa-exclamation-circle',
                    'message': f'{expired_count} license(s) have expired',
                    'link': reverse('customer_list')
                })
            
            # 3. Pending Batch Requests
            if state_filter:
                pending_requests = BatchRequest.objects.filter(
                    status=BatchRequest.Status.PENDING,
                    requester__state__in=state_filter
                ).count()
            else:
                pending_requests = BatchRequest.objects.filter(
                    status=BatchRequest.Status.PENDING
                ).count()
            
            if pending_requests > 0:
                notifications_list.append({
                    'type': 'info',
                    'icon': 'fa-file-alt',
                    'message': f'{pending_requests} pending batch request(s) awaiting approval',
                    'link': reverse('batch_list')
                })
            
            # 4. Pending Customer Approvals
            if state_filter:
                pending_customers = Company.objects.filter(
                    state__in=state_filter,
                    authentication_status__isnull=True
                ).count() + Company.objects.filter(
                    state__in=state_filter
                ).exclude(authentication_status__in=['Success', 'Approved', 'Approve']).count()
            else:
                pending_customers = Company.objects.filter(
                    authentication_status__isnull=True
                ).count()
            
            if pending_customers > 0:
                notifications_list.append({
                    'type': 'warning',
                    'icon': 'fa-user-clock',
                    'message': f'{pending_customers} customer(s) pending authentication',
                    'link': reverse('customer_list')
                })
        
        # ============ DEALER_ADMIN Notifications ============
        elif user.role == 'DEALER_ADMIN' and user.company_relation:
            dealer = user.company_relation
            
            # 1. Dealer's own license expiry warning
            if dealer.product_to_date:
                days_left = (dealer.product_to_date - date.today()).days
                if days_left <= 30 and days_left >= 0:
                    notifications_list.append({
                        'type': 'warning',
                        'icon': 'fa-clock',
                        'message': f'Your dealer license expires in {days_left} days',
                        'link': '#'
                    })
                elif days_left < 0:
                    notifications_list.append({
                        'type': 'danger',
                        'icon': 'fa-exclamation-circle',
                        'message': 'Your dealer license has expired!',
                        'link': '#'
                    })
            
            # 2. Unmapped devices (not assigned to any Customer)
            unmapped_devices = Device.objects.filter(
                Q(company=dealer) | Q(company__parent_company=dealer),
                dealer_customer__isnull=True
            ).count()
            
            if unmapped_devices > 0:
                notifications_list.append({
                    'type': 'info',
                    'icon': 'fa-link',
                    'message': f'{unmapped_devices} device(s) unmapped',
                    'link': reverse('mapping_view')
                })
            
            # 3. Devices without serial numbers assigned - REMOVED (Legacy Batch Logic)
            # devices_without_serial = Device.objects.filter(
            #     Q(company=dealer) | Q(company__parent_company=dealer),
            #     serial_number__isnull=True
            # ).count()
            
            # if devices_without_serial > 0:
            #     pass
            
            # 4. Customer expiry alerts for dealer customers
            # Note: DealerCustomer doesn't have expiry_date field, so we skip this check
            # In the future, if expiry tracking is needed, add the field to the model
        
        # ============ COMPANY_ADMIN & DEALER_CUSTOMER Notifications ============
        elif user.role in ['COMPANY_ADMIN', 'DEALER_CUSTOMER'] and user.company_relation:
            company = user.company_relation
            
            # 1. License expiry warning
            if company.product_to_date:
                days_left = (company.product_to_date - date.today()).days
                if days_left <= 30 and days_left >= 0:
                    notifications_list.append({
                        'type': 'warning',
                        'icon': 'fa-clock',
                        'message': f'Your license expires in {days_left} days',
                        'link': '#'
                    })
                elif days_left < 0:
                    notifications_list.append({
                        'type': 'danger',
                        'icon': 'fa-exclamation-circle',
                        'message': 'Your license has expired! Contact admin.',
                        'link': '#'
                    })
            
            # 2. Devices needing configuration
            unconfigured_devices = Device.objects.filter(
                company=company,
                is_active=True
            ).exclude(device_type='LED').filter(
                Q(project_name__isnull=True) | Q(project_name='')
            ).count()
            
            if unconfigured_devices > 0:
                notifications_list.append({
                    'type': 'info',
                    'icon': 'fa-cog',
                    'message': f'{unconfigured_devices} device(s) need configuration',
                    'link': reverse('device_list')
                })
        
        # ============ BRANCH_ADMIN Notifications ============
        elif user.role == 'BRANCH_ADMIN' and user.branch_relation:
            branch = user.branch_relation
            
            # Devices in branch needing attention
            branch_devices = Device.objects.filter(branch=branch, is_active=True).count()
            if branch_devices == 0:
                notifications_list.append({
                    'type': 'info',
                    'icon': 'fa-desktop',
                    'message': 'No devices assigned to your branch yet',
                    'link': reverse('device_list')
                })
    
    except Exception as e:
        # Fail silently - notifications are not critical
        logger.error(f"Notification context processor error: {e}")
        logger.error(traceback.format_exc())
    
    return {
        'notifications': notifications_list,
        'notification_count': len(notifications_list)
    }
