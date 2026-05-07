from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
import datetime

class LicenseCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for unauthenticated users or superadmins (optional, depending on requirements)
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Skip for admin interface and login page to prevent redirect loops
        if request.path.startswith('/admin/') or request.path.startswith('/accounts/login/'):
            return self.get_response(request)

        user = request.user
        
        # Check if user belongs to a company (SUPERADMIN might not have company_relation)
        if hasattr(user, 'company_relation') and user.company_relation:
            company = user.company_relation
            if company.product_to_date:
                today = timezone.now().date()
                license_expiry = company.product_to_date
                
                # Check for expiry
                if license_expiry < today:
                    logout(request)
                    messages.error(request, 'Your license has expired. Please contact support.')
                    return redirect('login')
                
                # Check for upcoming expiry (less than 10 days)
                days_remaining = (license_expiry - today).days
                if 0 <= days_remaining < 10:
                    request.license_warning = f"Your license expires in {days_remaining} day(s)!"
                    request.days_remaining = days_remaining
        
        response = self.get_response(request)
        return response
