from django.db import models
from django.conf import settings

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    def __str__(self): return self.name

class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)
    class Meta:
        unique_together = ('country', 'name')
    def __str__(self): return self.name

class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    class Meta:
        unique_together = ('state', 'name')
    def __str__(self): return self.name

class Company(models.Model):
    class CompanyType(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Direct Customer'
        DEALER = 'DEALER', 'Dealer'

    company_id = models.CharField(max_length=100, unique=True, null=True, blank=True) # From external API or dealer pattern
    company_name = models.CharField(max_length=100)
    company_type = models.CharField(max_length=20, choices=CompanyType.choices, default=CompanyType.CUSTOMER)
    parent_company = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_companies')
    is_dealer_created = models.BooleanField(default=False) # Flag to identify dealer-created customers (no external API)
    
    class BranchConfiguration(models.TextChoices):
        SINGLE = 'SINGLE', 'Single Branch'
        MULTIPLE = 'MULTIPLE', 'Multiple Branches'

    branch_configuration = models.CharField(
        max_length=20, 
        choices=BranchConfiguration.choices, 
        default=BranchConfiguration.MULTIPLE
    )
    
    company_email = models.EmailField(unique=True)
    gst_number = models.CharField(max_length=20, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    address = models.TextField()
    address_2 = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    zip_code = models.CharField(max_length=20)
    number_of_licence = models.IntegerField(default=1)
    
    # Device Counts from License
    noof_broker_devices = models.IntegerField(default=0)
    noof_token_dispensors = models.IntegerField(default=0)
    noof_keypad_devices = models.IntegerField(default=0)
    noof_television_devices = models.IntegerField(default=0)
    noof_led_devices = models.IntegerField(default=0)
    
    # Tracking
    authentication_status = models.CharField(max_length=100, null=True, blank=True)
    product_registration_id = models.IntegerField(null=True, blank=True)
    unique_identifier = models.CharField(max_length=255, null=True, blank=True)
    product_from_date = models.DateField(null=True, blank=True)
    product_to_date = models.DateField(null=True, blank=True)
    
    # Ads Feature
    ads_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} ({self.get_company_type_display()})"

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    branch_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    zip_code = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.company_name} - {self.branch_name}"

class AuthenticationLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    authentication_status = models.CharField(max_length=100)
    product_registration_id = models.IntegerField()
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    number_of_licence = models.IntegerField()
    response_json = models.JSONField(null=True, blank=True) # Store full response
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Auth Log {self.id} for {self.company.company_name}"

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255) # e.g., "Customer Created", "License Validated"
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.action} by {self.user}"

class DealerCustomer(models.Model):
    """
    Contact records for customers managed by dealers.
    These are NOT user accounts - just contact information for device mapping and notifications.
    Dealers can assign devices to these customers and send expiry notifications.
    """
    dealer = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='dealer_customers', limit_choices_to={'company_type': 'DEALER'})
    customer_id = models.CharField(max_length=100, unique=True) # Auto-generated: DEALER_ID-CUST0001
    
    company_name = models.CharField(max_length=100)
    company_email = models.EmailField(unique=True)
    gst_number = models.CharField(max_length=20, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    address = models.TextField()
    address_2 = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    zip_code = models.CharField(max_length=20)
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dealer_customers'
        verbose_name = 'Dealer Customer'
        verbose_name_plural = 'Dealer Customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company_name} (Dealer: {self.dealer.company_name})"
