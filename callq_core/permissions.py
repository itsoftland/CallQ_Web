from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SuperAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'SUPER_ADMIN'

class DealerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN']

class CompanyRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN', 'COMPANY_ADMIN', 'DEALER_CUSTOMER', 'BRANCH_ADMIN', 'PRODUCTION_ADMIN', 'EMPLOYEE']

class DealerCustomerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'DEALER_CUSTOMER'

def superadmin_required(user):
    return user.is_authenticated and user.role in ['SUPER_ADMIN', 'ADMIN']

def dealer_required(user):
    return user.is_authenticated and user.role in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN']

def company_required(user):
    return user.is_authenticated and user.role in ['SUPER_ADMIN', 'ADMIN', 'DEALER_ADMIN', 'COMPANY_ADMIN', 'DEALER_CUSTOMER', 'BRANCH_ADMIN', 'PRODUCTION_ADMIN', 'EMPLOYEE']

def dealer_customer_required(user):
    return user.is_authenticated and user.role == 'DEALER_CUSTOMER'

def dealer_or_customer_required(user):
    return user.is_authenticated and user.role in ['DEALER_ADMIN', 'DEALER_CUSTOMER', 'COMPANY_ADMIN']

def branch_required(user):
    return user.is_authenticated and user.role == 'BRANCH_ADMIN'
