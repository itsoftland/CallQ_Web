from django.db import models
import uuid

class Batch(models.Model):
    name = models.CharField(max_length=50) # e.g. B1, B2
    
    # Support both regular customers and dealer customers
    customer = models.ForeignKey('companydetails.Company', on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    
    # Allowed quantities
    max_tvs = models.IntegerField(default=0)
    max_dispensers = models.IntegerField(default=0)
    max_keypads = models.IntegerField(default=0)
    max_brokers = models.IntegerField(default=0)
    max_leds = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        REJECTED = 'REJECTED', 'Rejected'

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name_plural = "Batches"

    def __str__(self):
        if self.customer:
            return f"{self.customer.company_name} - {self.name}"
        elif self.dealer_customer:
            return f"{self.dealer_customer.company_name} - {self.name}"
        return f"Batch {self.name}"
    
    def get_owner(self):
        """Returns the owner entity (Company or DealerCustomer)"""
        return self.customer if self.customer else self.dealer_customer

class License(models.Model):
    class DeviceType(models.TextChoices):
        TV = 'TV', 'TV'
        TOKEN_DISPENSER = 'TOKEN_DISPENSER', 'Token Dispenser'
        KEYPAD = 'KEYPAD', 'Keypad'
        BROKER = 'BROKER', 'Broker'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        REVOKED = 'REVOKED', 'Revoked'

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='licenses')
    device_type = models.CharField(max_length=50, choices=DeviceType.choices)
    license_key = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INACTIVE)
    
    # Device Binding
    device_uid = models.CharField(max_length=100, null=True, blank=True) # Serial or MAC
    activated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.license_key} ({self.device_type})"


class BatchRequest(models.Model):
    """
    Model to track batch requests from customers and dealers.
    Admins can approve/reject these requests.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    class RequesterType(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        DEALER = 'DEALER', 'Dealer'
        DEALER_CUSTOMER = 'DEALER_CUSTOMER', 'Dealer Customer'
    
    # Support both regular customers and dealer customers
    requester = models.ForeignKey('companydetails.Company', on_delete=models.CASCADE, related_name='batch_requests', null=True, blank=True)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.CASCADE, related_name='batch_requests', null=True, blank=True)
    requester_type = models.CharField(max_length=20, choices=RequesterType.choices)
    
    # Requested device counts (what they want to ADD)
    requested_tvs = models.IntegerField(default=0)
    requested_dispensers = models.IntegerField(default=0)
    requested_keypads = models.IntegerField(default=0)
    requested_brokers = models.IntegerField(default=0)
    requested_leds = models.IntegerField(default=0)
    
    reason = models.TextField(blank=True)  # Optional reason for request
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey('userdetails.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_batch_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)  # Admin notes when approving/rejecting
    
    # The batch created when request is approved
    approved_batch = models.OneToOneField(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_request')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Batch Request"
        verbose_name_plural = "Batch Requests"

    def __str__(self):
        requester_name = self.requester.company_name if self.requester else (self.dealer_customer.company_name if self.dealer_customer else "Unknown")
        return f"Batch Request by {requester_name} ({self.get_status_display()})"
    
    @property
    def total_requested_devices(self):
        return self.requested_tvs + self.requested_dispensers + self.requested_keypads + self.requested_brokers + self.requested_leds
    
    def get_requester(self):
        """Returns the requester entity (Company or DealerCustomer)"""
        return self.requester if self.requester else self.dealer_customer
