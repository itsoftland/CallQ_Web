from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin" # System Admin
        DEALER_ADMIN = "DEALER_ADMIN", "Dealer Admin"
        COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin"
        BRANCH_ADMIN = "BRANCH_ADMIN", "Branch Admin"
        DEALER_CUSTOMER = "DEALER_CUSTOMER", "Dealer Customer"
        PRODUCTION_ADMIN = "PRODUCTION_ADMIN", "Production Admin"
        EMPLOYEE = "EMPLOYEE", "Employee"  # System-level employee (Admin/SuperAdmin only)
        COMPANY_EMPLOYEE = "COMPANY_EMPLOYEE", "Company Employee"  # Company-level employee for Android app

    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)

    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=25, choices=Role.choices, default=Role.COMPANY_ADMIN)
    zone = models.CharField(max_length=100, null=True, blank=True)
    assigned_state = models.JSONField(null=True, blank=True)
    is_web_user = models.BooleanField(default=True, help_text="Designates whether the user can log into the web dashboard.")
    is_android_user = models.BooleanField(default=False, help_text="Designates whether the user can log into Android applications.")
    
    # Foreign Keys to other apps (Strings used to avoid circular imports during initial load)
    # Using strings 'companydetails.Company' dependent on the app name
    company_relation = models.ForeignKey(
        'companydetails.Company', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='users'
    )
    branch_relation = models.ForeignKey(
        'companydetails.Branch', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='users'
    )
    dealer_customer_relation = models.ForeignKey(
        'companydetails.DealerCustomer', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='users'
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        return self.email

class AppLoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_login_histories')
    company = models.ForeignKey('companydetails.Company', on_delete=models.CASCADE, related_name='app_login_histories')
    mac_address = models.CharField(max_length=100)
    version = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'App Login History'
        verbose_name_plural = 'App Login Histories'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.company.company_name} - {self.timestamp}"
