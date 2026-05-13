from django.db import models
from django.core.validators import FileExtensionValidator
from companydetails.models import Company, Branch

# ---------------------------------------------------------------------------
# ASCII Button-Index Constants
# ---------------------------------------------------------------------------
# button_index is a single ASCII character.
# The sequence runs from hex 0x31 ('1') to hex 0x7A ('z') — 74 slots:
#   Slot 1  → chr(0x31) = '1'
#   Slot 2  → chr(0x32) = '2'
#   …
#   Slot 9  → chr(0x39) = '9'
#   Slot 10 → chr(0x3A) = ':'
#   …
#   Slot 74 → chr(0x7A) = 'z'
# The list is ordered by ASCII code-point so CharField ordering is correct.
BUTTON_INDEX_START = 0x31          # ord('1')
BUTTON_INDEX_END   = 0x7A          # ord('z')
BUTTON_INDEX_MAX_SLOTS = BUTTON_INDEX_END - BUTTON_INDEX_START + 1  # 74
BUTTON_INDEX_SEQUENCE = [chr(BUTTON_INDEX_START + i) for i in range(BUTTON_INDEX_MAX_SLOTS)]


def get_button_index_char(position: int) -> str:
    """
    Convert a 1-based slot position to its ASCII button-index character.

    Args:
        position: 1-based slot number (1 → '1' / 0x31, …, 74 → 'z' / 0x7A)

    Returns:
        Single ASCII character representing the button index.

    Raises:
        ValueError: if position is outside [1, BUTTON_INDEX_MAX_SLOTS].
    """
    if not (1 <= position <= BUTTON_INDEX_MAX_SLOTS):
        raise ValueError(
            f"Button position {position!r} is out of range "
            f"[1, {BUTTON_INDEX_MAX_SLOTS}]."
        )
    return chr(BUTTON_INDEX_START + position - 1)

class Device(models.Model):
    class DeviceType(models.TextChoices):
        TV = 'TV', 'TV'
        TOKEN_DISPENSER = 'TOKEN_DISPENSER', 'Token Dispenser'
        KEYPAD = 'KEYPAD', 'Keypad'
        BROKER = 'BROKER', 'Broker'
        LED = 'LED', 'LED'

    class TokenType(models.TextChoices):
        BUTTON_1 = '1_BUTTON', '1 Button'
        BUTTON_2 = '2_BUTTON', '2 Buttons'
        BUTTON_3 = '3_BUTTON', '3 Buttons'
        BUTTON_4 = '4_BUTTON', '4 Buttons'

    serial_number = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100, null=True, blank=True, help_text="Customer-defined name for easy identification")
    device_type = models.CharField(max_length=50, choices=DeviceType.choices)
    token_type = models.CharField(max_length=50, choices=TokenType.choices, null=True, blank=True) # Only for Token Dispenser
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='devices', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='devices', null=True, blank=True)
    
    # External License & Device Management Fields
    device_registration_id = models.CharField(max_length=100, null=True, blank=True)
    mac_address = models.CharField(max_length=100, null=True, blank=True) # Essential for TV
    batch = models.ForeignKey('licenses.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    
    # Dealer Customer Assignment (for dealers to map devices to their customers)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    
    device_model = models.CharField(max_length=100, default='PC') # e.g. PC, RaspberryPi
    licence_status = models.CharField(max_length=50, default='Pending') # Active, Inactive, Pending
    licence_active_to = models.DateField(null=True, blank=True)
    project_name = models.CharField(max_length=100, null=True, blank=True)
    apk_version = models.CharField(max_length=50, null=True, blank=True)
    product_type_id = models.IntegerField(null=True, blank=True)
    
    # Link to Reusable Profile (Scheduler)
    embedded_profile = models.ForeignKey('EmbeddedProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    # Link to Configuration Profile (no scheduling)
    config_profile = models.ForeignKey('DeviceConfigProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_devices')
    
    is_active = models.BooleanField(default=True)
    random_number = models.CharField(max_length=50, default='XXXX', help_text="Random number for token dispenser")
    fcm_token = models.TextField(null=True, blank=True, help_text="FCM registration token for push notifications (TV devices)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self):
        """Check if device license has expired"""
        from datetime import date
        if self.licence_active_to:
            return date.today() > self.licence_active_to
        return False
    
    @property
    def days_until_expiry(self):
        """Get number of days until license expires (negative if already expired)"""
        from datetime import date
        if self.licence_active_to:
            delta = self.licence_active_to - date.today()
            return delta.days
        return None
    
    @property
    def is_expiring_soon(self):
        """Check if device license is expiring within 10 days"""
        days = self.days_until_expiry
        return days is not None and 0 <= days <= 10

    @property
    def get_display_identifier(self):
        """Return display_name if set, otherwise serial_number"""
        return self.display_name if self.display_name else self.serial_number

    def __str__(self):
        return f"{self.device_type} - {self.serial_number}"

class ProductionBatch(models.Model):
    batch_id = models.CharField(max_length=100, unique=True)
    device_type = models.CharField(max_length=50, choices=Device.DeviceType.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Production Batch {self.batch_id} ({self.device_type})"

class ProductionSerialNumber(models.Model):
    batch = models.ForeignKey(ProductionBatch, on_delete=models.CASCADE, related_name='serial_numbers')
    serial_number = models.CharField(max_length=100, unique=True)
    mac_address = models.CharField(max_length=100, null=True, blank=True, help_text="Physical MAC address of the device (optional)")
    device_type = models.CharField(max_length=50, choices=Device.DeviceType.choices, default=Device.DeviceType.TV)
    is_registered = models.BooleanField(default=False)
    
    def __str__(self):
        return self.serial_number

class Mapping(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.SET_NULL, null=True, blank=True, related_name='mappings')
    
    token_dispenser = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_tvs', null=True, blank=True)
    tv = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_sources', null=True, blank=True)
    
    # Also need Keypad mappings
    keypad = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_keypads', null=True, blank=True)
    broker = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_brokers', null=True, blank=True)
    
    # Additional Keypads (Total 4 supported)
    keypad_2 = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_keypads_2', null=True, blank=True)
    keypad_3 = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_keypads_3', null=True, blank=True)
    keypad_4 = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_keypads_4', null=True, blank=True)

    # LED Display
    led = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='mapped_leds', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Mapping {self.id}"

class ButtonMapping(models.Model):
    """
    Detailed mapping for device buttons.
    Supported Flows:
    - Token Dispenser Button -> Keypad (to trigger token)
    - Keypad Button -> LED (to display)
    - Keypad Button -> Broker (to trigger)
    - Broker -> TV (to display)
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.SET_NULL, null=True, blank=True, related_name='button_mappings')
    
    source_device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='source_mappings')
    source_button = models.CharField(max_length=50) # e.g. "Button 1", "Button A"
    
    target_device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='target_mappings')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_device} {self.source_button} -> {self.target_device}"

class GroupMapping(models.Model):
    """
    Group Mapping groups devices together into named groups.
    Constraints:
    - Token Dispenser, Keypad, and LED devices can only be in ONE group
    - Broker and TV devices can be in multiple groups
    """
    group_name = models.CharField(max_length=150)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    dealer_customer = models.ForeignKey('companydetails.DealerCustomer', on_delete=models.SET_NULL, null=True, blank=True)
    
    no_of_dispensers = models.IntegerField(default=1)
    no_of_keypads = models.IntegerField(default=1)
    no_of_tvs = models.IntegerField(default=1)
    no_of_brokers = models.IntegerField(default=0)
    no_of_leds = models.IntegerField(default=0)
    
    # ManyToMany relationships for devices
    # dispensers uses a through model so each dispenser stores its group button index.
    dispensers = models.ManyToManyField(
        Device,
        through='GroupDispenserMapping',
        related_name='group_dispensers',
        limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER},
        blank=True,
    )
    keypads = models.ManyToManyField(Device, related_name='group_keypads', limit_choices_to={'device_type': Device.DeviceType.KEYPAD}, blank=True)
    tvs = models.ManyToManyField(Device, related_name='group_tvs', limit_choices_to={'device_type': Device.DeviceType.TV}, blank=True)
    brokers = models.ManyToManyField(Device, related_name='group_brokers', limit_choices_to={'device_type': Device.DeviceType.BROKER}, blank=True)
    leds = models.ManyToManyField(Device, related_name='group_leds', limit_choices_to={'device_type': Device.DeviceType.LED}, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validate that Token Dispenser, Keypad, and LED devices are only in one group"""
        from django.core.exceptions import ValidationError
        
        # This validation will be done at the view level before saving
        # since ManyToMany fields need the instance to be saved first
        pass
    
    def __str__(self):
        return self.group_name


class GroupDispenserMapping(models.Model):
    """
    Through model for GroupMapping.dispensers.

    Stores the physical button index that this dispenser occupies within its
    group (e.g. the first dispenser in the group → '1', the second → '2', …).
    Uses the same ASCII character encoding as the rest of the system
    (chr(0x31)='1' … chr(0x7A)='z', 74 slots).

    One dispenser can only belong to ONE group (enforced by unique_together).
    Each group button position is also unique per group.
    """
    group = models.ForeignKey(
        GroupMapping,
        on_delete=models.CASCADE,
        related_name='dispenser_slot_mappings',
    )
    dispenser = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='group_dispenser_slots',
        limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER},
    )
    dispenser_button_index = models.CharField(
        max_length=1,
        default=chr(BUTTON_INDEX_START),   # '1' (0x31)
        help_text=(
            "Physical button position for this dispenser within the group. "
            "ASCII character: '1' (slot 1) through 'z' (slot 74). "
            "Generated via get_button_index_char()."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('group', 'dispenser'),
            ('group', 'dispenser_button_index'),
        ]
        ordering = ['group', 'dispenser_button_index']
        verbose_name = 'Group Dispenser Mapping'
        verbose_name_plural = 'Group Dispenser Mappings'

    def __str__(self):
        return (
            f"{self.group.group_name} → {self.dispenser.serial_number} "
            f"(button {self.dispenser_button_index})"
        )

class GroupCounterButtonMapping(models.Model):
    """
    Tracks the group-wide sequential ASCII button index for every counter
    that belongs to a dispenser inside a group.

    Within a group the indices are globally unique and never reset between
    dispensers.  A 4-button dispenser whose counters are added after a
    1-button dispenser occupies the NEXT four consecutive slots, e.g.:

        Dispenser A (1 button/counter) → counter X  → button_index '1'
        Dispenser B (4 buttons)        → counter P  → button_index '2'
                                       → counter Q  → button_index '3'
                                       → counter R  → button_index '4'
                                       → counter S  → button_index '5'
        Dispenser C (1 button/counter) → counter Y  → button_index '6'

    This is the DB source of truth used by the token-dispenser config API
    to populate ``dispenser_button_index`` in every response section.
    """
    group = models.ForeignKey(
        GroupMapping,
        on_delete=models.CASCADE,
        related_name='counter_button_mappings',
    )
    dispenser = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='group_counter_button_slots',
        limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER},
    )
    counter = models.ForeignKey(
        'CounterConfig',
        on_delete=models.CASCADE,
        related_name='group_button_positions',
    )
    button_index = models.CharField(
        max_length=1,
        help_text=(
            "Group-wide sequential ASCII button index for this counter.  "
            "Starts at chr(0x31)='1' for the first counter in the group and "
            "increments through the full 74-slot sequence without resetting "
            "between dispensers.  Generated via get_button_index_char()."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('group', 'button_index'),  # No two counters share the same slot in a group
            ('group', 'counter'),       # A counter occupies exactly one slot per group
        ]
        ordering = ['group', 'button_index']
        verbose_name = 'Group Counter Button Mapping'
        verbose_name_plural = 'Group Counter Button Mappings'

    def __str__(self):
        return (
            f"{self.group.group_name} → "
            f"{self.dispenser.serial_number} / {self.counter.counter_name} "
            f"(btn {self.button_index})"
        )



class DeviceConfig(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='config')
    config_json = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for {self.device.serial_number}"

class TVConfig(models.Model):
    tv = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='tv_config')
    # Audio Params
    token_audio_file = models.FileField(upload_to='audio_files/', null=True, blank=True)
    token_music_file = models.FileField(upload_to='audio_files/', null=True, blank=True)
    audio_language = models.CharField(max_length=10, default='en')
    save_audio_external = models.BooleanField(default=False)
    enable_counter_announcement = models.BooleanField(default=False)
    enable_token_announcement = models.BooleanField(default=False)
    enable_counter_prifix = models.BooleanField(default=False)
    
    # Display Params
    show_ads = models.BooleanField(default=False)
    ad_interval = models.IntegerField(default=5) # minutes
    orientation = models.CharField(max_length=20, default='landscape')
    layout_type = models.CharField(max_length=50, default='default')
    display_rows = models.IntegerField(default=3)
    display_columns = models.IntegerField(default=4)
    counter_text_color = models.CharField(max_length=20, default='#000000')
    token_text_color = models.CharField(max_length=20, default='#000000')
    scroll_text_color = models.CharField(max_length=20, default='#000000')
    token_font_size = models.IntegerField(default=24)
    counter_font_size = models.IntegerField(default=24)
    tokens_per_counter = models.IntegerField(default=5)
    no_of_counters = models.IntegerField(default=1)
    no_of_dispensers = models.IntegerField(default=1)
    ad_placement = models.CharField(max_length=20, default='right')
    
    # Enhanced Token Config
    current_token_color = models.CharField(max_length=20, default='#000000')
    previous_token_color = models.CharField(max_length=20, default='#888888')
    blink_current_token = models.BooleanField(default=False)
    blink_seconds = models.IntegerField(default=1)
    token_format = models.CharField(max_length=10, choices=[('T1', 'T1'), ('T2', 'T2'), ('T3', 'T3')], default='T1')
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TV Config {self.tv.serial_number}"

class TVAd(models.Model):
    tv_config = models.ForeignKey(TVConfig, on_delete=models.CASCADE, related_name='ads')
    file = models.FileField(upload_to='ad_files/', null=True, blank=True)
    ad_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class LedConfig(models.Model):
    TOKEN_CALLING_CHOICES = [
        ('Single', 'Single'),
        ('Multiple', 'Multiple'),
    ]
    VOICE_CHOICES = [
        ('First', 'First'),
        ('Second', 'Second'),
    ]
    led = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='led_config')
    led_identifier_name = models.CharField(max_length=100, blank=True, null=True)
    voice_announcement = models.BooleanField(default=False)
    counter_number = models.IntegerField(default=1)
    token_calling = models.CharField(max_length=10, choices=TOKEN_CALLING_CHOICES, default='Single')
    counter_voice = models.BooleanField(default=False)
    token_voice = models.CharField(max_length=10, choices=VOICE_CHOICES, default='First')
    linked_calling_device = models.ManyToManyField(Device, related_name='linked_leds', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Led Config {self.led.serial_number}"

class TVCounter(models.Model):
    tv_config = models.ForeignKey(TVConfig, on_delete=models.CASCADE, related_name='counters')
    counter_id = models.CharField(max_length=50) # The logical ID e.g. "TD-MAC-C1"
    
    counter_name = models.CharField(max_length=100, null=True, blank=True)
    counter_code = models.CharField(max_length=20, null=True, blank=True)
    
    # Display logic for this counter on TV
    row_span = models.IntegerField(default=1)
    col_span = models.IntegerField(default=1)
    
    # Audio
    counter_audio_file = models.FileField(upload_to='counter_audios/', null=True, blank=True)
    is_enabled = models.BooleanField(default=True)
    
    unique_together = ('tv_config', 'counter_id')

    def __str__(self):
        return f"Counter {self.counter_id} for {self.tv_config.tv.serial_number}"

class Counter(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='counters')
    counter_name = models.CharField(max_length=100)
    counter_number = models.IntegerField()
    assigned_device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.counter_name

class ConfigProfile(models.Model):
    """Configuration profile with day/time scheduling for devices"""
    
    class DayChoices(models.TextChoices):
        MONDAY = 'MON', 'Monday'
        TUESDAY = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY = 'THU', 'Thursday'
        FRIDAY = 'FRI', 'Friday'
        SATURDAY = 'SAT', 'Saturday'
        SUNDAY = 'SUN', 'Sunday'
        ALL = 'ALL', 'All Days'
        WEEKDAYS = 'WKDY', 'Weekdays'
        WEEKENDS = 'WKND', 'Weekends'

    name = models.CharField(max_length=100)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='config_profiles')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='config_profiles')
    config_json = models.JSONField(default=dict)
    
    # Scheduling
    day = models.CharField(max_length=10, choices=DayChoices.choices, default='ALL')
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device', 'day', 'start_time']

    def __str__(self):
        return f"{self.name} - {self.device.serial_number} ({self.get_day_display()})"


class EmbeddedProfile(models.Model):
    """
    Reusable configuration profile for embedded devices.
    Can be sourced from external API (ReadOnly) or created locally.
    """
    class DeviceType(models.TextChoices):
        TV = 'TV', 'TV'
        TOKEN_DISPENSER = 'TOKEN_DISPENSER', 'Token Dispenser'
        KEYPAD = 'KEYPAD', 'Keypad'
        BROKER = 'BROKER', 'Broker'
        LED = 'LED', 'LED'

    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50, choices=DeviceType.choices, default=DeviceType.TV)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='embedded_profiles', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='embedded_profiles', null=True, blank=True)
    config_json = models.JSONField(default=dict) # Stores full configuration payload from API
    
    # Scheduling
    class DayChoices(models.TextChoices):
        MONDAY = 'MON', 'Monday'
        TUESDAY = 'TUE', 'Tuesday'
        WEDNESDAY = 'WED', 'Wednesday'
        THURSDAY = 'THU', 'Thursday'
        FRIDAY = 'FRI', 'Friday'
        SATURDAY = 'SAT', 'Saturday'
        SUNDAY = 'SUN', 'Sunday'

    day = models.JSONField(default=list, blank=True) # Stores list of selected days
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    is_api_sourced = models.BooleanField(default=False)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ============================================================================
# Counter-Wise Configuration Module
# ============================================================================

class CounterConfig(models.Model):
    """
    Counter Management Model for Counter-Wise Configuration Module.
    Each counter is scoped to a Company (and optionally a Branch).
    Names and prefix codes only need to be unique within the same company.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='counter_configs',
        help_text="Company that owns this counter",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counter_configs',
        help_text="Optional branch scope",
    )
    counter_name = models.CharField(max_length=100, help_text="Name of the counter (unique per company)")
    counter_prefix_code = models.CharField(max_length=20, help_text="Prefix used in token generation (unique per company)")
    counter_display_name = models.CharField(max_length=150, help_text="Name shown on TV display")
    max_token_number = models.IntegerField(help_text="Maximum tokens allowed for this counter")
    status = models.BooleanField(default=True, help_text="Active / Inactive")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['counter_name']
        verbose_name = 'Counter Configuration'
        verbose_name_plural = 'Counter Configurations'
        unique_together = [
            ('company', 'counter_name'),
            ('company', 'counter_prefix_code'),
        ]

    def __str__(self):
        return f"{self.counter_name} ({self.counter_prefix_code})"


class TVCounterMapping(models.Model):
    """
    Maps counters to TV devices.
    A TV can have multiple counters, and a counter can be mapped to multiple TVs.
    """
    tv = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='tv_counter_mappings', 
                          limit_choices_to={'device_type': Device.DeviceType.TV})
    counter = models.ForeignKey(CounterConfig, on_delete=models.CASCADE, related_name='tv_mappings')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tv', 'counter')
        verbose_name = 'TV Counter Mapping'
        verbose_name_plural = 'TV Counter Mappings'
        ordering = ['tv', 'counter']

    def __str__(self):
        return f"{self.tv.serial_number} -> {self.counter.counter_name}"


class TVDispenserMapping(models.Model):
    """
    Maps dispensers to TV devices.
    A TV can have multiple dispensers, and each dispenser has a button_index based on position.
    One dispenser can only be mapped to one TV at a time.
    """
    tv = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='tv_dispenser_mappings', 
                          limit_choices_to={'device_type': Device.DeviceType.TV})
    dispenser = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='tv_mappings',
                                 limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER})
    button_index = models.CharField(
        max_length=1,
        default=chr(BUTTON_INDEX_START),  # '1' (0x31)
        help_text="Single ASCII character encoding the dispenser's slot position on this TV. "
                  "Starts at chr(0x31)='1' and increments through ASCII order (max 90 slots).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tv', 'dispenser')
        verbose_name = 'TV Dispenser Mapping'
        verbose_name_plural = 'TV Dispenser Mappings'
        ordering = ['tv', 'button_index']

    def __str__(self):
        return f"{self.tv.serial_number} -> {self.dispenser.serial_number} (Button {self.button_index})"


class TVKeypadMapping(models.Model):
    """
    Maps keypads to TV devices, with an explicit link to the token dispenser
    that handles Button A calls for each keypad slot.

    Chain: TV slot → Keypad → Dispenser → Counters (via CounterTokenDispenserMapping)

    Index field:
      - keypad_index: the keypad's slot position on this TV.
                      chr(0x31)='1' for slot 1, chr(0x32)='2' for slot 2, …
                      Generated via get_button_index_char().

    Button configuration:
      - Button A: calling button — counters resolved via the linked dispenser.
      - Buttons B, C, D: custom string IDs stored in the keypad's own config_json
        (button_b_string_id, button_c_string_id, button_d_string_id).
    """
    tv = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        related_name='tv_keypad_mappings',
        limit_choices_to={'device_type': Device.DeviceType.TV},
    )
    keypad = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        related_name='tv_keypad_tv_mappings',
        limit_choices_to={'device_type': Device.DeviceType.KEYPAD},
    )
    # The token dispenser handling Button A calls for this keypad slot.
    # Null means no dispenser is assigned yet (Button A won't call any counter).
    dispenser = models.ForeignKey(
        Device, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tv_keypad_dispenser_mappings',
        limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER},
        help_text="Token dispenser whose counters Button A on this keypad calls.",
    )
    # Slot position on the TV (ASCII, starts at chr(0x31)='1')
    keypad_index = models.CharField(
        max_length=1,
        default=chr(BUTTON_INDEX_START),
        help_text=(
            "Single ASCII character encoding this keypad's slot position on the TV. "
            "Generated via get_button_index_char() — starts at chr(0x31)='1'."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tv', 'keypad')
        verbose_name = 'TV Keypad Mapping'
        verbose_name_plural = 'TV Keypad Mappings'
        ordering = ['tv', 'keypad_index']

    def __str__(self):
        disp_sn = self.dispenser.serial_number if self.dispenser else 'no dispenser'
        return (
            f"{self.tv.serial_number} → {self.keypad.serial_number} "
            f"(slot {self.keypad_index}, dispenser: {disp_sn})"
        )



class CounterTokenDispenserMapping(models.Model):
    """
    Maps counters to token dispensers.
    Each counter must be mapped to a token dispenser.
    """
    counter = models.ForeignKey(CounterConfig, on_delete=models.CASCADE, related_name='dispenser_mappings')
    dispenser = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='dispenser_counter_mappings',
                                 limit_choices_to={'device_type': Device.DeviceType.TOKEN_DISPENSER})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('counter', 'dispenser')
        verbose_name = 'Counter Token Dispenser Mapping'
        verbose_name_plural = 'Counter Token Dispenser Mappings'
        ordering = ['counter', 'dispenser']

    def __str__(self):
        return f"{self.counter.counter_name} -> {self.dispenser.serial_number}"


class DeviceConfigProfile(models.Model):
    """
    Reusable configuration profile for devices — no day/time scheduling.
    Can be mapped directly to one or more devices of the same type.
    """
    class DeviceType(models.TextChoices):
        TV              = 'TV', 'TV'
        TOKEN_DISPENSER = 'TOKEN_DISPENSER', 'Token Dispenser'
        KEYPAD          = 'KEYPAD', 'Keypad'
        BROKER          = 'BROKER', 'Broker'
        LED             = 'LED', 'LED'

    name        = models.CharField(max_length=100)
    device_type = models.CharField(max_length=50, choices=DeviceType.choices)
    company     = models.ForeignKey(Company, on_delete=models.CASCADE,
                                    related_name='device_config_profiles',
                                    null=True, blank=True)
    branch      = models.ForeignKey(Branch, on_delete=models.CASCADE,
                                    related_name='device_config_profiles',
                                    null=True, blank=True)
    config_json = models.JSONField(default=dict)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['device_type', 'name']
        verbose_name = 'Device Config Profile'
        verbose_name_plural = 'Device Config Profiles'

    def __str__(self):
        return f"{self.name} ({self.device_type})"


class ExternalDeviceCounterLog(models.Model):
    """
    Logs external API calls for device-counter mapping.
    Stores API payloads and mapping information from external systems.
    """
    device_id = models.CharField(max_length=100, help_text="Device ID from external API (e.g., TV001)")
    counter_name = models.CharField(max_length=100, help_text="Counter name from external API")
    counter = models.ForeignKey(CounterConfig, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='external_logs', help_text="Mapped counter if found")
    api_payload = models.JSONField(default=dict, help_text="Full API request payload")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'External Device Counter Log'
        verbose_name_plural = 'External Device Counter Logs'
        indexes = [
            models.Index(fields=['device_id', '-created_at']),
            models.Index(fields=['counter_name']),
        ]

    def __str__(self):
        return f"{self.device_id} -> {self.counter_name} ({self.created_at})"


class TokenReport(models.Model):
    """
    Stores token event reports received from embedded devices.
    Each record captures a token that was issued and when it was displayed.
    """
    received_message = models.TextField(help_text="The raw token message received from the device")
    received_dateTime = models.DateTimeField(help_text="Timestamp when the message was received by the server")
    displayed_dateTime = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the token was displayed on the TV/display device")
    customerId = models.CharField(max_length=100, help_text="Customer ID (company_id or dealer customer_id)")
    mac_address = models.CharField(max_length=100, help_text="MAC address of the originating device")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_dateTime']
        verbose_name = 'Token Report'
        verbose_name_plural = 'Token Reports'
        indexes = [
            models.Index(fields=['customerId', '-received_dateTime']),
            models.Index(fields=['mac_address', '-received_dateTime']),
        ]

    def __str__(self):
        return f"TokenReport [{self.customerId}] @ {self.received_dateTime}"